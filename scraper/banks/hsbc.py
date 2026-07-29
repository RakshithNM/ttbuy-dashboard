import re

from bs4 import BeautifulSoup

from ..core import normalize_date
from .base import BankPlugin

HSBC_URL = "https://www.hsbc.co.in/nri/foreign-exchange-rates/"


def parse(html, source_url):
    """HSBC's main rate table columns: FCY, BILLS BUY, BILLS SELL, TT BUY,
    TT SELL, CURRENCY BUY, CURRENCY SELL (7 columns). The page also has a
    second, differently-shaped 'vertical' table repeating the same data —
    restrict to 7-cell rows so that one is never matched instead."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    match = re.search(r"Updated on:\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4}),\s*([\d:]+\s*[ap]m)", text, re.I)
    rate_date = normalize_date(match.group(1)) if match else None
    published_at = match.group(2).strip() if match else None

    for table in soup.find_all("table"):
        if "TT BUY" not in table.get_text(" ", strip=True).upper():
            continue

        for row in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
            if len(cells) != 7 or "USD" not in cells[0].upper():
                continue

            return {
                "Rate_Date": rate_date,
                "Published_At": published_at,
                "TT_Buy": cells[3],
                "Raw_Data_Row": cells,
            }
    return None


PLUGIN = BankPlugin(
    name="HSBC",
    slug="hsbc",
    live_url=HSBC_URL,
    wayback_urls=[HSBC_URL],
    parse=parse,
)
