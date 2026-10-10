import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from .banks import REGISTRY

DATA_DIR = os.environ.get("TTBUY_DATA_DIR", "data")

# A bank's scraper fails quietly (main.py logs the error and moves on), so a
# broken parser shows up only as a rate that stops advancing. A bank is stale
# when it has missed more than STALE_DAYS publishing days.
STALE_DAYS = int(os.environ.get("STALE_DAYS", "2"))

# Weekends and bank holidays are not publishing days. There is no reliable
# holiday calendar to fetch, so the data decides: a date is a publishing day
# when at least this share of the banks have a rate for it.
PUBLISHING_DAY_SHARE = 0.5

# If no date at all qualifies for this many calendar days, the scraper itself
# is down (or every bank broke at once) and the per-bank check would stay silent.
MAX_QUIET_DAYS = 5


def load_dates(slug):
    """Return {currency: set of dates with a rate} for one bank."""
    path = os.path.join(DATA_DIR, f"{slug}_TTBuy.csv")
    if not os.path.exists(path):
        return {}

    df = pd.read_csv(path, dtype=str)
    if "Currency" not in df.columns:
        df["Currency"] = "USD"
    df["Currency"] = df["Currency"].fillna("USD").replace("", "USD")
    df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m-%d", errors="coerce")
    df = df.dropna(subset=["Date"])
    return {currency: set(group["Date"].dt.date) for currency, group in df.groupby("Currency")}


def find_stale(today):
    """Return a list of messages, one per stale bank/currency pair."""
    requested = [slug.strip().lower() for slug in os.environ.get("BANKS", "").split(",") if slug.strip()]
    plugins = [REGISTRY[slug] for slug in requested or list(REGISTRY) if slug in REGISTRY]
    dates = {plugin.slug: load_dates(plugin.slug) for plugin in plugins}

    # Platforms (Skydo, Remitly) quote every day, so only banks vote on what a
    # publishing day is.
    banks = [plugin for plugin in plugins if plugin.category == "bank"]
    votes = {}
    for plugin in banks:
        for day in set().union(*dates[plugin.slug].values()):
            votes[day] = votes.get(day, 0) + 1
    publishing_days = {day for day, count in votes.items() if count >= len(banks) * PUBLISHING_DAY_SHARE}

    messages = []
    if banks:
        last_publishing_day = max((day for day in publishing_days if day <= today), default=None)
        if not last_publishing_day or (today - last_publishing_day).days > MAX_QUIET_DAYS:
            messages.append(
                f"No day since {last_publishing_day} has a rate from at least half of the banks; "
                "the scraper may be down."
            )

    for plugin in plugins:
        if not dates[plugin.slug]:
            messages.append(f"{plugin.name}: no data")
            continue

        for currency, days in sorted(dates[plugin.slug].items()):
            newest = max(days)
            if plugin.category == "bank":
                missed = sum(1 for day in publishing_days if newest < day <= today)
            else:
                missed = (today - newest).days
            if missed > STALE_DAYS:
                unit = "publishing days" if plugin.category == "bank" else "days"
                messages.append(f"{plugin.name} {currency}: newest rate is {newest}, {missed} {unit} missed")
    return messages


def main():
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    messages = find_stale(today)
    if not messages:
        print(f"No bank has missed more than {STALE_DAYS} publishing days.")
        return

    for message in messages:
        # ::error:: makes the line an annotation on the GitHub Actions run page.
        print(f"::error title=Stale TT Buy rate::{message}")

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as summary:
            summary.write(f"### Stale TT Buy rates (more than {STALE_DAYS} publishing days missed)\n\n")
            summary.writelines(f"- {message}\n" for message in messages)

    sys.exit(1)


if __name__ == "__main__":
    main()
