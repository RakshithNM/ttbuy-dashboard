import json
import os
from datetime import datetime

from ..core import fetch_bytes, fetch_html, fetch_rendered_html

DATA_DIR = os.environ.get("TTBUY_DATA_DIR", "data")


def fetch_content(plugin):
    if plugin.kind == "pdf":
        return fetch_bytes(plugin.source_url)
    if plugin.kind == "browser":
        return fetch_rendered_html(plugin.source_url)
    return fetch_html(plugin.source_url)


def scrape_fee(plugin):
    content = fetch_content(plugin)
    parsed = plugin.parse(content, plugin.source_url)
    if not parsed:
        return None

    return {
        "bank": plugin.name,
        "rules": parsed["rules"],
        "note": parsed.get("note"),
        "source_url": plugin.source_url,
        "checked_at": datetime.now().strftime("%Y-%m-%d"),
    }


def scrape_all_fees(registry):
    results = {}
    for plugin in registry.values():
        try:
            result = scrape_fee(plugin)
        except Exception as e:
            print(f"Failed to fetch/parse fees for {plugin.name}: {e}")
            result = None

        if result:
            results[plugin.name] = result
            print(f"Fetched fees for {plugin.name}")
        else:
            print(f"No fee data parsed for {plugin.name}")

    return results


def write_fees(results):
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, "fees.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Wrote {path}: {len(results)} banks")
