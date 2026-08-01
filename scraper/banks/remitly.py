import re
from datetime import datetime

import requests

from ..core import TARGET_CURRENCIES
from .base import BankPlugin

# Each Remitly corridor has its own page — USD is the primary (fetched by the
# pipeline via live_url); GBP and EUR are fetched inside parse itself.
_CURRENCY_URLS = {
    "USD": "https://www.remitly.com/us/en/india",
    "GBP": "https://www.remitly.com/gb/en/india",
    "EUR": "https://www.remitly.com/de/en/india",
    # AED is not a Remitly corridor — no UAE → India page exists.
}

_RATE_RE = re.compile(r'"effectiveRateAsLowAs":"(\d+\.\d+)"')
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}


def _parse_one(html, ccy):
    m = _RATE_RE.search(html)
    if not m:
        return None
    rate = m.group(1)
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "Rate_Date": today,
        "Published_At": datetime.now().strftime("%H:%M"),
        "TT_Buy": rate,
        "Raw_Data_Row": {"currency": ccy, "effectiveRateAsLowAs": rate},
    }


def parse(html, source_url):
    results = {}

    # USD — pipeline already fetched this page
    row = _parse_one(html, "USD")
    if row:
        results["USD"] = row

    # GBP and EUR each live on their own page
    for ccy in ("GBP", "EUR"):
        if ccy not in TARGET_CURRENCIES:
            continue
        try:
            r = requests.get(_CURRENCY_URLS[ccy], headers=_HEADERS, timeout=20)
            if r.ok:
                row = _parse_one(r.text, ccy)
                if row:
                    results[ccy] = row
        except Exception:
            pass

    return results or None


PLUGIN = BankPlugin(
    name="Remitly",
    slug="remitly",
    live_url=_CURRENCY_URLS["USD"],
    wayback_urls=[],
    parse=parse,
    kind="html",
    category="platform",
)
