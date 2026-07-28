import re

from bs4 import BeautifulSoup

from ..core import normalize_date
from .base import BankPlugin

BOB_URL = "https://bankofbaroda.bank.in/business-banking/treasury/forex-card-rates"


def parse(html, source_url):
    """BoB table columns: Currency, TTSell, BillSell, TTBuy, BillBuy, TCBuy, TCSell, CNBuy, CNSell."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    match = re.search(r"Card Rates at\s+([0-9:]+\s*[AP]M)\s+(\d{2}\.\d{2}\.\d{4})", text, re.I)
    published_at = match.group(1).strip() if match else None
    rate_date = normalize_date(match.group(2)) if match else None

    for row in soup.find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
        if len(cells) <= 3 or cells[0].upper() != "USD":
            continue

        return {
            "Rate_Date": rate_date,
            "Published_At": published_at,
            "TT_Buy": cells[3],
            "Raw_Data_Row": cells,
        }
    return None


PLUGIN = BankPlugin(
    name="Bank of Baroda",
    slug="bob",
    live_url=BOB_URL,
    wayback_urls=[BOB_URL],
    parse=parse,
)
