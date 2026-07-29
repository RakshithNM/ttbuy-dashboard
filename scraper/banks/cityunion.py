import re

from bs4 import BeautifulSoup

from ..core import normalize_date
from .base import BankPlugin

CUB_URL = "https://cityunionbank.bank.in/foreign-exchange-rates"


def parse(html, source_url):
    """City Union's table has a two-tier header: group row (Telegraph
    Transfer, Bills, Travel Card, Currency) each spanning Buying/Selling sub-
    columns. TT Buy is the first data column, index 1."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    match = re.search(r"for Date\s+(\d{2}\.\d{2}\.\d{4})\s+Time\s+([\d:]+\s*[AP]M)", text)
    rate_date = normalize_date(match.group(1)) if match else None
    published_at = match.group(2).strip() if match else None

    for table in soup.find_all("table"):
        if "Telegraph Transfer" not in table.get_text(" ", strip=True):
            continue

        for row in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
            if len(cells) <= 1 or cells[0].upper() != "USD":
                continue

            return {
                "Rate_Date": rate_date,
                "Published_At": published_at,
                "TT_Buy": cells[1],
                "Raw_Data_Row": cells,
            }
    return None


PLUGIN = BankPlugin(
    name="City Union Bank",
    slug="cityunion",
    live_url=CUB_URL,
    wayback_urls=[CUB_URL],
    parse=parse,
)
