import re

from bs4 import BeautifulSoup

from ..core import normalize_date
from .base import BankPlugin

ICICI_URL = "https://www.icici.bank.in/corporate/global-markets/forex/forex-card-rate"


def parse(html, source_url):
    """ICICI table has a two-tier header: Currency (rowspan) + 'Bank Buying
    Rate' / 'Bank Selling Rate' groups, each with 5 sub-columns (TT, Bills,
    Currency notes, Forex Prepaid card, Demand Draft). TT Buying rate is the
    first column of the Buying group, i.e. index 1 right after Currency."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    match = re.search(r"Date:\s*(\d{2}-\d{2}-\d{4})\s*Time:\s*([0-9:]+\s*[AP]M)", text, re.I)
    rate_date = normalize_date(match.group(1)) if match else None
    published_at = match.group(2).strip() if match else None

    for row in soup.find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
        if len(cells) <= 1 or "USD" not in cells[0].upper():
            continue

        return {
            "Rate_Date": rate_date,
            "Published_At": published_at,
            "TT_Buy": cells[1],
            "Raw_Data_Row": cells,
        }
    return None


PLUGIN = BankPlugin(
    name="ICICI Bank",
    slug="icici",
    live_url=ICICI_URL,
    wayback_urls=[ICICI_URL],
    parse=parse,
)
