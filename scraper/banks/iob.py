import re

from bs4 import BeautifulSoup

from ..core import normalize_date
from .base import BankPlugin

IOB_LIVE_URL = "https://www.iob.bank.in/en/forex-rates"

# IOB moved forex rates between old iob.in and newer iob.bank.in pages;
# query all known official paths so Wayback backfill covers the full history.
IOB_WAYBACK_URLS = [
    "https://www.iob.in/iob_Forex-rates.aspx",
    "https://www.iob.bank.in/en/forex",
    "https://www.iob.bank.in/en/forex-rates",
]


def parse(html, source_url):
    """Old iob.in table: UNIT, CURRENCY, TTSell, BILLSSell, TTBuy, BILLSBUY.
    New iob.bank.in table: UNIT, CURRENCY, TT Buy, TT Sell, Bill Buy, Bill Sell."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    match = re.search(r"CARD RATES\s*-\s*(\d{2}[./-]\d{2}[./-]\d{4})", text)
    if not match:
        match = re.search(r"Last Updated\s*:?\s*(\d{2}[./-]\d{2}[./-]\d{4})", text, re.I)
    rate_date = normalize_date(match.group(1)) if match else None

    published_at_match = re.search(r"updated at\s+([0-9.:]+\s*[AP]M)", text, re.I)
    published_at = published_at_match.group(1).strip() if published_at_match else None

    for row in soup.find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
        if len(cells) < 5 or not any(cell.upper() == "USD" for cell in cells):
            continue

        if "iob.in" in source_url and "iob.bank.in" not in source_url:
            tt_buy = cells[4]
        else:
            tt_buy = cells[2]

        return {
            "Rate_Date": rate_date,
            "Published_At": published_at,
            "TT_Buy": tt_buy,
            "Raw_Data_Row": cells,
        }
    return None


PLUGIN = BankPlugin(
    name="IOB",
    slug="iob",
    live_url=IOB_LIVE_URL,
    wayback_urls=IOB_WAYBACK_URLS,
    parse=parse,
)
