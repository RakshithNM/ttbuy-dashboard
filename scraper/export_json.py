import json
import os
import re

import pandas as pd

DATA_DIR = os.environ.get("TTBUY_DATA_DIR", "data")

def normalize_time(val):
    if pd.isna(val) or str(val).strip() == "":
        return None
    val = str(val).replace("IST", "").replace("ist", "").strip()
    try:
        # Ujjivan, IOB and J&K Bank write the time with dots ("9.45 am",
        # "09.24.44"); pandas reads those as a decimal hour or a date and
        # drops the minutes.
        clock = re.sub(r"(?<=\d)\.(?=\d)", ":", val)
        # Typos seen in bank pages: a doubled separator (Citibank "9::05 AM")
        # and a stray third minute digit (IOB "10.397AM", read as 10:39).
        clock = re.sub(r":+", ":", clock)
        clock = re.sub(r"^(\d{1,2}:\d{2})\d+(?=\s*[ap]m$)", r"\1", clock, flags=re.I)
        # IOB has published a 24-hour time with a suffix ("16.36 PM").
        if re.match(r"(1[3-9]|2[0-3]):", clock):
            clock = re.sub(r"\s*[ap]m$", "", clock, flags=re.I)
        return pd.to_datetime(clock).strftime("%I:%M %p")
    except Exception:
        return val

def export():
    combined_path = os.path.join(DATA_DIR, "forex_TTBuy.csv")
    df = pd.read_csv(combined_path, dtype=str)
    df["TT_Buy"] = pd.to_numeric(df["TT_Buy"], errors="coerce")
    df = df.dropna(subset=["TT_Buy", "Date"])
    if "Published_At" in df.columns:
        df["Published_At"] = df["Published_At"].apply(normalize_time)
    if "Currency" not in df.columns:
        df["Currency"] = "USD"
    df["Currency"] = df["Currency"].fillna("USD").replace("", "USD")

    midmarket_path = os.path.join(DATA_DIR, "midmarket_history.csv")
    if os.path.exists(midmarket_path):
        df_mm = pd.read_csv(midmarket_path, dtype=str)
        df_mm["TT_Buy"] = pd.to_numeric(df_mm["TT_Buy"], errors="coerce")
        df_mm = df_mm.dropna(subset=["TT_Buy", "Date"])
        df = pd.concat([df, df_mm], ignore_index=True)

    # Snapshot_Timestamp sorts wayback timestamps ("202...") before live rows
    # ("live-..."), so keeping the last row per (Bank, Currency, Date) prefers
    # a live scrape over an archived one when both exist for the same date.
    df = df.sort_values(["Bank", "Currency", "Date", "Snapshot_Timestamp"])
    df = df.drop_duplicates(subset=["Bank", "Currency", "Date"], keep="last")

    result = {}
    for currency, currency_group in df.groupby("Currency"):
        currency_result = {}
        for bank, group in currency_group.groupby("Bank"):
            rows = group.sort_values("Date")[["Date", "Published_At", "TT_Buy"]].rename(
                columns={"Date": "date", "Published_At": "publishedAt", "TT_Buy": "ttbuy"}
            )
            # Safely replace pandas NaNs with Python None for standard JSON 'null'
            rows = rows.astype(object).where(pd.notna(rows), None)
            currency_result[bank] = rows.to_dict("records")
        result[currency] = currency_result

    out_path = os.path.join(DATA_DIR, "rates.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    total_rows = sum(len(v) for group in result.values() for v in group.values())
    total_banks = sum(len(group) for group in result.values())
    print(f"Wrote {out_path}: {total_rows} rows across {total_banks} bank/currency pairs ({len(result)} currencies)")


if __name__ == "__main__":
    export()
