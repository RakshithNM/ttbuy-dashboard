import re

from bs4 import BeautifulSoup

from ..core import TARGET_CURRENCIES, normalize_date
from .base import BankPlugin

BANDHAN_URL = "https://bandhan.bank.in/rates-charges"


def parse(html, source_url):
    """Bandhan's card-rate table has header ['Currency','Card Rate'] then a
    sub-header ['TT Buy Rate','TT Sell Rate','Bill Buy Rate','Bill Sell Rate'].
    TT Buy is index 1, right after the currency code."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    date_match = re.search(r"Forex Rates for\s+([A-Za-z]+\s+\d{1,2},\s*\d{4})", text)
    time_match = re.search(r"Rates as on\s+([\d:]+)\s*IST", text)
    rate_date = normalize_date(date_match.group(1)) if date_match else None
    published_at = f"{time_match.group(1)} IST" if time_match else None

    results = {}
    for table in soup.find_all("table"):
        if "TT Buy Rate" not in table.get_text(" ", strip=True):
            continue

        for row in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
            if len(cells) <= 1:
                continue
            code = cells[0].upper()
            if code not in TARGET_CURRENCIES or code in results:
                continue

            results[code] = {
                "Rate_Date": rate_date,
                "Published_At": published_at,
                "TT_Buy": cells[1],
                "Raw_Data_Row": cells,
            }
    return results or None


PLUGIN = BankPlugin(
    name="Bandhan Bank",
    slug="bandhan",
    live_url=BANDHAN_URL,
    wayback_urls=[BANDHAN_URL],
    parse=parse,
)
