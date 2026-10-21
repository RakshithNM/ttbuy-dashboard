"""Save each plugin's live page as a test fixture and record what parse() reads.

Run this when a bank changes its page format and you have fixed the parser:

    .venv/bin/python3 -m scraper.tests.save_fixtures [slug ...]

Check the printed rates against the bank's page before you commit, because
test_parsers.py treats expected.json as the truth.
"""
import gzip
import json
import os
import sys

import requests

from ..banks import REGISTRY, remitly
from ..pipeline import fetch_content

TESTS_DIR = os.path.dirname(__file__)
FIXTURES_DIR = os.path.join(TESTS_DIR, "fixtures")
EXPECTED_PATH = os.path.join(TESTS_DIR, "expected.json")

# Remitly's parse() fetches these corridors itself, so they get their own fixtures.
REMITLY_EXTRA_CURRENCIES = ("GBP", "EUR")

# Remitly's page carries no date, so parse() stamps today's date.
UNDATED = {"remitly"}


def fixture_path(plugin, suffix=""):
    # Gzipped: the saved pages are several MB as plain files.
    extension = "pdf" if plugin.kind in ("pdf", "pdf_discover") else "html"
    return os.path.join(FIXTURES_DIR, f"{plugin.slug}{suffix}.{extension}.gz")


def expected_rows(plugin, parsed):
    return {
        currency: {
            "Rate_Date": None if plugin.slug in UNDATED else row["Rate_Date"],
            "TT_Buy": str(row["TT_Buy"]),
        }
        for currency, row in sorted(parsed.items())
    }


def save(plugin):
    content = fetch_content(plugin, plugin.live_url)
    if not content:
        raise RuntimeError("no content fetched")

    if isinstance(content, bytes):
        opened = gzip.open(fixture_path(plugin), "wb")
    else:
        opened = gzip.open(fixture_path(plugin), "wt", encoding="utf-8")
    with opened as f:
        f.write(content)

    if plugin.slug == "remitly":
        for currency in REMITLY_EXTRA_CURRENCIES:
            res = requests.get(remitly._CURRENCY_URLS[currency], headers=remitly._HEADERS, timeout=20)
            res.raise_for_status()
            with gzip.open(fixture_path(plugin, f"_{currency}"), "wt", encoding="utf-8") as f:
                f.write(res.text)

    parsed = plugin.parse(content, plugin.live_url)
    if not parsed:
        raise RuntimeError("parse() found no rates in the fetched page")
    return expected_rows(plugin, parsed)


def main():
    slugs = sys.argv[1:] or list(REGISTRY)
    os.makedirs(FIXTURES_DIR, exist_ok=True)

    expected = {}
    if os.path.exists(EXPECTED_PATH):
        with open(EXPECTED_PATH) as f:
            expected = json.load(f)

    failed = []
    for slug in slugs:
        plugin = REGISTRY[slug]
        try:
            expected[slug] = save(plugin)
        except Exception as e:
            print(f"{slug}: FAILED ({e})")
            failed.append(slug)
            continue
        rates = ", ".join(f"{c} {r['TT_Buy']} ({r['Rate_Date']})" for c, r in expected[slug].items())
        print(f"{slug}: {rates}")

    with open(EXPECTED_PATH, "w") as f:
        json.dump(dict(sorted(expected.items())), f, indent=2)
        f.write("\n")

    if failed:
        sys.exit(f"Could not save: {', '.join(failed)}")


if __name__ == "__main__":
    main()
