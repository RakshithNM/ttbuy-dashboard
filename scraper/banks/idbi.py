import re

from bs4 import BeautifulSoup

from ..core import normalize_date
from .base import BankPlugin

IDBI_URL = "https://idbi.bank.in/merchantrates.aspx"


def parse(html, source_url):
    """IDBI's table is a bilingual (Hindi/English) MS-Excel export. Columns:
    Currency name, code, TTS (TT Sell), TTB (TT Buy), BLS, BLB, FCS, FCB."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    match = re.search(r"Forex Card Rates for\s*:\s*(\d{1,2}-[A-Za-z]{3}-\d{2})", text)
    rate_date = normalize_date(match.group(1)) if match else None

    for table in soup.find_all("table"):
        if "TTB" not in table.get_text(" ", strip=True):
            continue

        for row in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
            if len(cells) <= 3 or cells[1].upper() != "USD":
                continue

            return {
                "Rate_Date": rate_date,
                "Published_At": None,
                "TT_Buy": cells[3],
                "Raw_Data_Row": cells,
            }
    return None


PLUGIN = BankPlugin(
    name="IDBI Bank",
    slug="idbi",
    live_url=IDBI_URL,
    wayback_urls=[IDBI_URL],
    parse=parse,
)
