import re

from bs4 import BeautifulSoup

from ..core import normalize_date
from .base import BankPlugin

DBS_URL = "https://www.dbs.bank.in/in/treasures/rates-online/foreign-currency-foreign-exchange.page"


def parse(html, source_url):
    """DBS's rates load client-side. The page repeats each currency as its
    own small vertical table AND has one combined horizontal table with
    columns Currency, Selling TT, Selling Cash, Buying TT, Buying Cash — use
    the combined one since it's simplest to column-index. TT Buy is index 3."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    match = re.search(r"Effective Date\s*:\s*(\d{2}/\d{2}/\d{4})\s*Last Updated\s*:\s*([\d:]+\s*[AP]M)", text)
    rate_date = normalize_date(match.group(1)) if match else None
    published_at = match.group(2) if match else None

    for table in soup.find_all("table"):
        header_text = table.get_text(" ", strip=True)
        if "Selling TT" not in header_text or "Buying TT" not in header_text:
            continue

        for row in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
            if len(cells) <= 3 or cells[0] != "US Dollar":
                continue

            return {
                "Rate_Date": rate_date,
                "Published_At": published_at,
                "TT_Buy": cells[3],
                "Raw_Data_Row": cells,
            }
    return None


PLUGIN = BankPlugin(
    name="DBS Bank India",
    slug="dbs",
    live_url=DBS_URL,
    wayback_urls=[],
    parse=parse,
    kind="browser",
)
