import re

from bs4 import BeautifulSoup

from ..core import normalize_date
from .base import BankPlugin

IDFCFIRST_URL = "https://www.idfcfirst.bank.in/forex-rates.html"


def parse(html, source_url):
    """IDFC FIRST's rates load client-side. Table columns: Currency Pair,
    then paired Bank Buys/Bank Sells for Bills, Telegraphic Transfer (TT),
    Forex Card. TT Buy is index 3."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    match = re.search(r"Updated At \(\s*([\d-]+)\s+([\d:]+)\s*\)", text)
    rate_date = normalize_date(match.group(1)) if match else None
    published_at = match.group(2) if match else None

    for table in soup.find_all("table"):
        if "Telegraphic Transfer" not in table.get_text(" ", strip=True):
            continue

        for row in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
            if len(cells) <= 3 or cells[0].upper() != "USDINR":
                continue

            return {
                "Rate_Date": rate_date,
                "Published_At": published_at,
                "TT_Buy": cells[3],
                "Raw_Data_Row": cells,
            }
    return None


PLUGIN = BankPlugin(
    name="IDFC FIRST Bank",
    slug="idfcfirst",
    live_url=IDFCFIRST_URL,
    wayback_urls=[],
    parse=parse,
    kind="browser",
)
