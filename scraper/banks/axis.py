import re

from bs4 import BeautifulSoup

from ..core import TARGET_CURRENCIES, normalize_date
from .base import BankPlugin

AXIS_URL = "https://application.axis.bank.in/webforms/corporatecardrate/index.aspx"


def parse(html, source_url):
    """Axis table columns: Currency, Code, TT Buy, TT Sell, Bill Buy, Bill Sell,
    TC Buy, TC Sell, CCY Buy, CCY Sell. The code (USD/GBP/EUR/AED) is its own
    cell; TT Buy is the next cell."""
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

    results = {}
    for row in soup.find_all("tr"):
        cells = [
            cell.get_text(" ", strip=True)
            for cell in row.find_all(["td", "th"])
            if cell.get_text(" ", strip=True)
        ]
        for code in TARGET_CURRENCIES:
            if code in results or code not in cells:
                continue
            idx = cells.index(code)
            if len(cells) <= idx + 1:
                continue
            results[code] = {
                "Rate_Date": published_date,
                "Published_At": published_at,
                "TT_Buy": cells[idx + 1],
                "Raw_Data_Row": cells,
            }
    return results or None


PLUGIN = BankPlugin(
    name="Axis Bank",
    slug="axis",
    live_url=AXIS_URL,
    wayback_urls=[AXIS_URL],
    parse=parse,
)
