import json
import os

import pandas as pd

DATA_DIR = os.environ.get("TTBUY_DATA_DIR", "data")


def export():
    combined_path = os.path.join(DATA_DIR, "forex_TTBuy.csv")
    df = pd.read_csv(combined_path, dtype=str)
    df["TT_Buy"] = pd.to_numeric(df["TT_Buy"], errors="coerce")
    df = df.dropna(subset=["TT_Buy", "Date"])

    # Snapshot_Timestamp sorts wayback timestamps ("202...") before live rows
    # ("live-..."), so keeping the last row per (Bank, Date) prefers a live
    # scrape over an archived one when both exist for the same date.
    df = df.sort_values(["Bank", "Date", "Snapshot_Timestamp"])
    df = df.drop_duplicates(subset=["Bank", "Date"], keep="last")

    result = {}
    for bank, group in df.groupby("Bank"):
        rows = group.sort_values("Date")[["Date", "TT_Buy"]].rename(
            columns={"Date": "date", "TT_Buy": "ttbuy"}
        )
        result[bank] = rows.to_dict("records")

    out_path = os.path.join(DATA_DIR, "rates.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    total_rows = sum(len(v) for v in result.values())
    print(f"Wrote {out_path}: {total_rows} rows across {len(result)} banks")


if __name__ == "__main__":
    export()
