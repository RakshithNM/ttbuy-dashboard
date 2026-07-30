import os
import time
from datetime import datetime

import pandas as pd

from .banks import REGISTRY
from .core import (
    REQUEST_DELAY_SECONDS,
    TARGET_CURRENCIES,
    fetch_bytes,
    fetch_html,
    fetch_rendered_html,
    get_wayback_snapshots,
)


def fetch_content(plugin, url, is_wayback=False):
    if plugin.kind == "pdf":
        return fetch_bytes(url, is_wayback=is_wayback)
    if plugin.kind == "browser":
        return fetch_rendered_html(url)
    if plugin.kind == "pdf_discover":
        landing_html = fetch_html(url, is_wayback=is_wayback)
        pdf_url = plugin.resolve_url(landing_html) if plugin.resolve_url else None
        if not pdf_url:
            return None
        return fetch_bytes(pdf_url, is_wayback=False)
    return fetch_html(url, is_wayback=is_wayback)

OUTPUT_COLUMNS = [
    "Bank",
    "Currency",
    "Snapshot_Timestamp",
    "Snapshot_Date",
    "Date",
    "Rate_Date",
    "Published_At",
    "TT_Buy",
    "Source_URL",
    "Raw_Data_Row",
]

DATA_DIR = os.environ.get("TTBUY_DATA_DIR", "data")


def _csv_path(slug):
    return os.path.join(DATA_DIR, f"{slug}_TTBuy.csv")


def _md_path(slug):
    return os.path.join(DATA_DIR, f"{slug}_TTBuy.md")


def prepare_output_df(df, bank_name=None):
    if df.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    df = df.copy()
    if bank_name and "Bank" not in df.columns:
        df["Bank"] = bank_name

    for column in OUTPUT_COLUMNS:
        if column not in df.columns:
            df[column] = None

    # CSVs written before multi-currency support has no Currency column;
    # every row scraped back then was USD.
    df["Currency"] = df["Currency"].fillna("USD").replace("", "USD")

    if "Snapshot_Timestamp" in df.columns:
        df = df.sort_values("Snapshot_Timestamp")

    return df[OUTPUT_COLUMNS]


def load_existing_output(slug, bank_name):
    csv_path = _csv_path(slug)
    if not os.path.exists(csv_path):
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    df = pd.read_csv(csv_path, dtype=str)
    if "Bank" not in df.columns:
        df["Bank"] = bank_name

    return prepare_output_df(df, bank_name)


def write_bank_outputs(slug, bank_name, df):
    os.makedirs(DATA_DIR, exist_ok=True)
    df = prepare_output_df(df, bank_name)
    df.to_csv(_csv_path(slug), index=False)

    with open(_md_path(slug), "w", encoding="utf-8") as output:
        output.write("Date       | Currency | TT Buy\n")
        output.write("--------------------------------\n")
        for _, row in df.iterrows():
            output.write(f"{row['Date']} | {row['Currency']} | {row['TT_Buy']}\n")


def write_combined_outputs():
    dfs = [load_existing_output(slug, plugin.name) for slug, plugin in REGISTRY.items()]
    valid_dfs = [df for df in dfs if not df.empty]
    if not valid_dfs:
        return

    combined = pd.concat(valid_dfs, ignore_index=True)
    combined = combined.sort_values(["Bank", "Currency", "Snapshot_Timestamp"])
    os.makedirs(DATA_DIR, exist_ok=True)
    combined.to_csv(os.path.join(DATA_DIR, "forex_TTBuy.csv"), index=False)

    with open(os.path.join(DATA_DIR, "forex_TTBuy.md"), "w", encoding="utf-8") as output:
        output.write("Bank | Currency | Date | TT Buy\n")
        output.write("-------------------------------\n")
        for _, row in combined.iterrows():
            output.write(f"{row['Bank']} | {row['Currency']} | {row['Date']} | {row['TT_Buy']}\n")


def print_snapshot_coverage(bank_name, snapshots):
    if not snapshots:
        print(f"No {bank_name} snapshots found.")
        return

    first_date = datetime.strptime(snapshots[0][0], "%Y%m%d%H%M%S").strftime("%Y-%m-%d")
    last_date = datetime.strptime(snapshots[-1][0], "%Y%m%d%H%M%S").strftime("%Y-%m-%d")
    print(f"{bank_name} URL coverage found in Wayback: {first_date} to {last_date}")


def get_bank_snapshots(plugin, start_date, end_date):
    seen = set()
    snapshots = []
    for url in plugin.wayback_urls:
        for timestamp, original in get_wayback_snapshots(url, start_date, end_date):
            key = (timestamp, original)
            if key not in seen:
                snapshots.append((timestamp, original))
                seen.add(key)
    return sorted(snapshots, key=lambda row: row[0])


def scrape_bank_history(plugin, snapshots):
    print(f"\nMining {plugin.name} snapshot history from the archive...")
    print(f"Snapshots found: {len(snapshots)}")
    print_snapshot_coverage(plugin.name, snapshots)

    existing_df = load_existing_output(plugin.slug, plugin.name)
    historical_data = existing_df.to_dict("records")
    # A snapshot only counts as "done" once every target currency has a row
    # for it — otherwise a snapshot scraped back when only USD was extracted
    # would be skipped forever and never picked up for the new currencies.
    currencies_by_snapshot = (
        existing_df.groupby("Snapshot_Timestamp")["Currency"].apply(set).to_dict()
        if not existing_df.empty
        else {}
    )
    skipped = []

    if currencies_by_snapshot:
        print(f"Resuming from {plugin.slug}_TTBuy.csv with {len(currencies_by_snapshot)} snapshots on file")

    for timestamp, orig_url in snapshots:
        have_currencies = currencies_by_snapshot.get(timestamp, set())
        if set(TARGET_CURRENCIES) <= have_currencies:
            continue

        archive_link = f"https://web.archive.org/web/{timestamp}/{orig_url}"
        snapshot_date = datetime.strptime(timestamp, "%Y%m%d%H%M%S").strftime("%Y-%m-%d")

        print(f"Scraping {plugin.name} data for {snapshot_date}...")
        try:
            content = fetch_content(plugin, archive_link, is_wayback=True)
            parsed = plugin.parse(content, orig_url)
        except Exception as e:
            print(f"Failed to fetch/parse {archive_link}: {e}")
            parsed = None

        if parsed:
            added_any = False
            for currency, parsed_row in parsed.items():
                if currency in have_currencies:
                    continue
                historical_data.append({
                    "Bank": plugin.name,
                    "Currency": currency,
                    "Snapshot_Timestamp": timestamp,
                    "Snapshot_Date": snapshot_date,
                    "Date": parsed_row["Rate_Date"] or snapshot_date,
                    "Rate_Date": parsed_row["Rate_Date"],
                    "Published_At": parsed_row.get("Published_At"),
                    "TT_Buy": parsed_row["TT_Buy"],
                    "Source_URL": orig_url,
                    "Raw_Data_Row": parsed_row["Raw_Data_Row"],
                })
                added_any = True
            if added_any:
                write_bank_outputs(plugin.slug, plugin.name, pd.DataFrame(historical_data))
        else:
            skipped.append({"Snapshot_Date": snapshot_date, "Source_URL": orig_url})
        time.sleep(REQUEST_DELAY_SECONDS)

    df = prepare_output_df(pd.DataFrame(historical_data), plugin.name)
    print(f"\n{plugin.name} rows parsed: {len(df)}")
    if not df.empty:
        write_bank_outputs(plugin.slug, plugin.name, df)
        print(f"Saved {plugin.slug}_TTBuy.csv and {plugin.slug}_TTBuy.md")

    if skipped:
        print(f"\n{plugin.name} snapshots skipped: {len(skipped)}")
        print(pd.DataFrame(skipped).to_string(index=False))

    return df


def add_live_row(plugin):
    print(f"\nFetching live {plugin.name} rate...")
    existing_df = load_existing_output(plugin.slug, plugin.name)
    historical_data = existing_df.to_dict("records")

    try:
        content = fetch_content(plugin, plugin.live_url)
        parsed = plugin.parse(content, plugin.live_url)
    except Exception as e:
        print(f"Failed to fetch/parse live {plugin.name} rate: {e}")
        parsed = None

    if not parsed:
        print(f"No live {plugin.name} TT Buy row parsed.")
        return existing_df

    now = datetime.now()
    live_timestamp = f"live-{now.strftime('%Y%m%d%H%M%S')}"
    added = 0
    for currency, parsed_row in parsed.items():
        rate_date = parsed_row["Rate_Date"] or now.strftime("%Y-%m-%d")
        existing_live = existing_df[
            (existing_df["Source_URL"] == plugin.live_url)
            & (existing_df["Date"] == rate_date)
            & (existing_df["Currency"] == currency)
        ] if not existing_df.empty else pd.DataFrame()
        if not existing_live.empty:
            print(f"Live {plugin.name} {currency} row for {rate_date} already exists.")
            continue

        historical_data.append({
            "Bank": plugin.name,
            "Currency": currency,
            "Snapshot_Timestamp": live_timestamp,
            "Snapshot_Date": now.strftime("%Y-%m-%d"),
            "Date": rate_date,
            "Rate_Date": parsed_row["Rate_Date"],
            "Published_At": parsed_row.get("Published_At"),
            "TT_Buy": parsed_row["TT_Buy"],
            "Source_URL": plugin.live_url,
            "Raw_Data_Row": parsed_row["Raw_Data_Row"],
        })
        print(f"Added live {plugin.name} {currency} row: {rate_date} TT Buy {parsed_row['TT_Buy']}")
        added += 1

    if added == 0:
        return existing_df

    df = prepare_output_df(pd.DataFrame(historical_data), plugin.name)
    write_bank_outputs(plugin.slug, plugin.name, df)
    return df
