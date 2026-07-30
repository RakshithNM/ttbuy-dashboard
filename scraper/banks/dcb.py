import re

from bs4 import BeautifulSoup

from ..core import TARGET_CURRENCIES, normalize_date
from .base import BankPlugin

DCB_URL = "https://www.dcb.bank.in/rates/forex-rates"


def parse(html, source_url):
    """DCB's rates load client-side. Table columns: Units, Currency, then
    paired Sell/Buy for TT, Bills, Travel Card, CN. TT Buy is index 3
    (TT-Sell is index 2 — the pair is Sell-before-Buy, unlike most banks)."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    match = re.search(r"Rates updated as on\s+(\d{1,2}-[A-Za-z]+-\d{4})\s+([\d:]+)", text)
    rate_date = normalize_date(match.group(1)) if match else None
    published_at = match.group(2) if match else None

    results = {}
    for table in soup.find_all("table"):
        if "Travel Card" not in table.get_text(" ", strip=True):
            continue

        for row in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
            if len(cells) <= 3:
                continue
            code = cells[1].upper()
            if code not in TARGET_CURRENCIES or code in results:
                continue

            results[code] = {
                "Rate_Date": rate_date,
                "Published_At": published_at,
                "TT_Buy": cells[3],
                "Raw_Data_Row": cells,
            }
    return results or None


PLUGIN = BankPlugin(
    name="DCB Bank",
    slug="dcb",
    live_url=DCB_URL,
    wayback_urls=[],  # JS-rendered; archived HTML wouldn't contain the data
    parse=parse,
    kind="browser",
)
