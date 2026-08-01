import json
import re
from datetime import datetime

from ..core import TARGET_CURRENCIES
from .base import BankPlugin

SKYDO_URL = "https://www.skydo.com/convert-usd-to-inr?amount=1000"


def parse(html, source_url):
    nd = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not nd:
        return None
    try:
        data = json.loads(nd.group(1))
        live_fx = data["props"]["pageProps"]["initialData"]["liveFx"]
    except (json.JSONDecodeError, KeyError):
        return None

    results = {}
    for entry in live_fx:
        base = entry.get("base")
        if base not in TARGET_CURRENCIES:
            continue
        ts = entry.get("api_timestamp", "")
        try:
            dt = datetime.strptime(ts, "%b %d, %Y, %I:%M:%S %p")
        except ValueError:
            try:
                dt = datetime.strptime(ts, "%b %d, %Y, %I:%M %p")
            except ValueError:
                dt = datetime.now()
        results[base] = {
            "Rate_Date": dt.strftime("%Y-%m-%d"),
            "Published_At": dt.strftime("%H:%M"),
            "TT_Buy": str(round(entry["fx_rate"], 4)),
            "Raw_Data_Row": entry,
        }
    return results or None


PLUGIN = BankPlugin(
    name="Skydo",
    slug="skydo",
    live_url=SKYDO_URL,
    wayback_urls=[],
    parse=parse,
    kind="html",
    category="platform",
)
