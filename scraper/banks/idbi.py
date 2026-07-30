import re

from bs4 import BeautifulSoup

from ..core import TARGET_CURRENCIES, normalize_date
from .base import BankPlugin

IDBI_URL = "https://idbi.bank.in/merchantrates.aspx"


def parse(html, source_url):
    """IDBI serves two different table layouts (seemingly at random/depending
    on backend state): a bilingual (Hindi/English) export with columns
    Currency name, code, TTS, TTB, BLS, BLB, FCS, FCB (code at index 1, TT
    Buy at index 3) — and a plain English layout with columns Currency code,
    T.T Sell, T.T Buy, Bill/Card Sell, Bill/Card Buy, FC Sell, FC Buy, TC Buy
    (code at index 0, TT Buy at index 2). Handle both by checking which cell
    holds the currency code."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    match = re.search(r"(?:Forex Card|Merchant) Rates for\s*:?\s*(\d{1,2}-[A-Za-z]{3}-\d{2})", text)
    rate_date = normalize_date(match.group(1)) if match else None

    results = {}
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
            if len(cells) <= 3:
                continue

            if cells[0].upper() in TARGET_CURRENCIES:
                code, tt_buy = cells[0].upper(), cells[2]
            elif cells[1].upper() in TARGET_CURRENCIES:
                code, tt_buy = cells[1].upper(), cells[3]
            else:
                continue
            if code in results:
                continue

            results[code] = {
                "Rate_Date": rate_date,
                "Published_At": None,
                "TT_Buy": tt_buy,
                "Raw_Data_Row": cells,
            }
    return results or None


PLUGIN = BankPlugin(
    name="IDBI Bank",
    slug="idbi",
    live_url=IDBI_URL,
    wayback_urls=[IDBI_URL],
    parse=parse,
)
