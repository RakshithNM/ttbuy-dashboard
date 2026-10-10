import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from .banks import REGISTRY

DATA_DIR = os.environ.get("TTBUY_DATA_DIR", "data")

# A bank's scraper fails quietly (main.py logs the error and moves on), so a
# broken parser shows up only as a rate that stops advancing. 3 days covers a
# normal weekend; raise STALE_DAYS if long weekends cause false alarms.
STALE_DAYS = int(os.environ.get("STALE_DAYS", "3"))


def find_stale(today):
    """Return [(bank name, currency, newest date or None, age in days or None)]
    for every bank/currency pair whose newest row is older than STALE_DAYS."""
    requested = [slug.strip().lower() for slug in os.environ.get("BANKS", "").split(",") if slug.strip()]
    stale = []
    for slug in requested or list(REGISTRY):
        plugin = REGISTRY.get(slug)
        if not plugin:
            continue

        path = os.path.join(DATA_DIR, f"{slug}_TTBuy.csv")
        if not os.path.exists(path):
            stale.append((plugin.name, "all", None, None))
            continue

        df = pd.read_csv(path, dtype=str)
        if "Currency" not in df.columns:
            df["Currency"] = "USD"
        df["Currency"] = df["Currency"].fillna("USD").replace("", "USD")
        df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m-%d", errors="coerce")
        df = df.dropna(subset=["Date"])
        if df.empty:
            stale.append((plugin.name, "all", None, None))
            continue

        for currency, newest in df.groupby("Currency")["Date"].max().items():
            age = (today - newest.date()).days
            if age > STALE_DAYS:
                stale.append((plugin.name, currency, newest.date().isoformat(), age))
    return stale


def main():
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    stale = find_stale(today)
    if not stale:
        print(f"All bank rates are at most {STALE_DAYS} days old.")
        return

    lines = [
        f"{bank} {currency}: " + (f"newest rate is {newest} ({age} days old)" if newest else "no data")
        for bank, currency, newest, age in stale
    ]
    for line in lines:
        # ::error:: makes the line an annotation on the GitHub Actions run page.
        print(f"::error title=Stale TT Buy rate::{line}")

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as summary:
            summary.write(f"### Stale TT Buy rates (older than {STALE_DAYS} days)\n\n")
            summary.writelines(f"- {line}\n" for line in lines)

    sys.exit(1)


if __name__ == "__main__":
    main()
