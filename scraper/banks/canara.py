import re

from bs4 import BeautifulSoup

from ..core import TARGET_CURRENCIES, normalize_date
from .base import BankPlugin

CANARA_URL = "https://www.canarabank.bank.in/pages/forex-card-rates"


def parse(html, source_url):
    """Canara's card-rate table has a two-tier header: a 'SELLING RATES' group
    (Currency, TT/DDS, BILL) followed by a 'BUYING RATES' group (TT/CHQ, BILL) —
    confirmed via each header cell's colspan. TT Buy for inward remittance is
    TT/CHQ, i.e. the first column of the BUYING RATES group (index 3). Currency
    cells are formatted like 'USD/INR'.

    The page also has a separate 'International Prepaid' cash-rate table with
    its own currency rows; restrict to the table containing 'TT/CHQ' so that
    one is never mistaken for the card-rate table.
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    match = re.search(r"RATEX DATE\s*:\s*(\d{1,2}/[A-Za-z]{3}/\d{2})", text)
    rate_date = normalize_date(match.group(1)) if match else None

    results = {}
    for table in soup.find_all("table"):
        if "TT/CHQ" not in table.get_text(" ", strip=True):
            continue

        for row in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
            if len(cells) <= 3:
                continue
            code = next((c for c in TARGET_CURRENCIES if cells[0].upper().startswith(c)), None)
            if code is None or code in results:
                continue

            results[code] = {
                "Rate_Date": rate_date,
                "Published_At": None,
                "TT_Buy": cells[3],
                "Raw_Data_Row": cells,
            }
    return results or None


PLUGIN = BankPlugin(
    name="Canara Bank",
    slug="canara",
    live_url=CANARA_URL,
    wayback_urls=[CANARA_URL],
    parse=parse,
)
