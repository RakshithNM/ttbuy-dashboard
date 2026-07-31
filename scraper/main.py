import os

from .banks import REGISTRY
from .pipeline import add_live_row, get_bank_snapshots, scrape_bank_history, write_combined_outputs


def main():
    start_date = os.environ.get("START_DATE", "20250530")
    end_date = os.environ.get("END_DATE", "20260530")
    max_snapshots = os.environ.get("MAX_SNAPSHOTS")
    max_snapshot_count = int(max_snapshots) if max_snapshots is not None else None
    include_live = os.environ.get("INCLUDE_LIVE", "1") != "0"
    requested_banks = {
        bank.strip().lower()
        for bank in os.environ.get("BANKS", "axis,iob").split(",")
        if bank.strip()
    }

    for slug in requested_banks:
        plugin = REGISTRY.get(slug)
        if not plugin:
            print(f"Unknown bank slug: {slug} (known: {', '.join(REGISTRY)})")
            continue

        try:
            snapshots = [] if max_snapshot_count == 0 else get_bank_snapshots(plugin, start_date, end_date)
            if max_snapshot_count:
                snapshots = snapshots[:max_snapshot_count]

            scrape_bank_history(plugin, snapshots)
            if include_live:
                add_live_row(plugin)
        except Exception as e:
            print(f"Skipping {plugin.name} after unrecoverable error: {e}")

    write_combined_outputs()
    print("\nSaved forex_TTBuy.csv")


if __name__ == "__main__":
    main()
