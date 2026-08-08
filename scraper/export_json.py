import json
import os

import pandas as pd

DATA_DIR = os.environ.get("TTBUY_DATA_DIR", "data")


def export():
    combined_path = os.path.join(DATA_DIR, "forex_TTBuy.csv")
    df = pd.read_csv(combined_path, dtype=str)
    df["TT_Buy"] = pd.to_numeric(df["TT_Buy"], errors="coerce")
    df = df.dropna(subset=["TT_Buy", "Date"])
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
            rows = group.sort_values("Date")[["Date", "TT_Buy"]].rename(
                columns={"Date": "date", "TT_Buy": "ttbuy"}
            )
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
