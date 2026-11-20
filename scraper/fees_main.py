import json
import os

from .fees import REGISTRY, RETIRED
from .fees.pipeline import DATA_DIR, scrape_all_fees, write_fees


def load_retired_fees():
    """Return the last saved fee entry for each retired bank."""
    path = os.path.join(DATA_DIR, "fees.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        saved = json.load(f)
    names = {plugin.name for plugin in RETIRED.values()}
    return {name: entry for name, entry in saved.items() if name in names}


def main():
    results = load_retired_fees() | scrape_all_fees(REGISTRY)
    write_fees(results)


if __name__ == "__main__":
    main()
