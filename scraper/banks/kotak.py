from bs4 import BeautifulSoup

from .base import BankPlugin

KOTAK_URL = "https://www.kotak.bank.in/en/rates/forex-rates.html"


def parse(html, source_url):
    """Kotak's rates are loaded client-side (nothing in the raw HTTP response),
    so `html` here is already fully rendered by Playwright. The page has
    separate 'We Buy' / 'We Sell' tables; the Buying table's columns are
    Currency, Cash, Forex Card, Bills, Telegraphic Transfer — TT Buy is the
    last column (index 4). No 'as of' timestamp is shown anywhere on the page,
    so Rate_Date is left for the caller to fall back to the scrape date."""
    soup = BeautifulSoup(html, "html.parser")

    for table in soup.find_all("table"):
        text = table.get_text(" ", strip=True)
        if "We Buy" not in text or "Telegraphic Transfer" not in text:
            continue

        for row in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["td", "th"])]
            if len(cells) <= 4 or cells[0].upper() != "USD":
                continue

            return {
                "Rate_Date": None,
                "Published_At": None,
                "TT_Buy": cells[4],
                "Raw_Data_Row": cells,
            }
    return None


PLUGIN = BankPlugin(
    name="Kotak Mahindra Bank",
    slug="kotak",
    live_url=KOTAK_URL,
    wayback_urls=[],  # JS-rendered; archived HTML snapshots wouldn't contain the data anyway
    parse=parse,
    kind="browser",
)
