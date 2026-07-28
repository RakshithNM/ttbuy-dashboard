import re

from bs4 import BeautifulSoup

from ..core import normalize_date
from .base import BankPlugin

AXIS_URL = "https://application.axis.bank.in/webforms/corporatecardrate/index.aspx"


def parse(html, source_url):
    """Axis table columns: Currency, Code, TT Buy, TT Sell, Bill Buy, Bill Sell,
    TC Buy, TC Sell, CCY Buy, CCY Sell."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    published_date = None
    published_at = None
    match = re.search(
        r"published on\s+([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})\s+at\s+([0-9:]+\s*[AP]M)",
        text,
        re.I,
    )
    if match:
        published_date = normalize_date(match.group(1))
        published_at = match.group(2).strip()

    for row in soup.find_all("tr"):
        cells = [
            cell.get_text(" ", strip=True)
            for cell in row.find_all(["td", "th"])
            if cell.get_text(" ", strip=True)
        ]
        if "USD" not in cells:
            continue

        usd_index = cells.index("USD")
        if len(cells) <= usd_index + 1:
            continue

        return {
            "Rate_Date": published_date,
            "Published_At": published_at,
            "TT_Buy": cells[usd_index + 1],
            "Raw_Data_Row": cells,
        }
    return None


PLUGIN = BankPlugin(
    name="Axis Bank",
    slug="axis",
    live_url=AXIS_URL,
    wayback_urls=[AXIS_URL],
    parse=parse,
)
