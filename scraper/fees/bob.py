import re

from bs4 import BeautifulSoup

from .base import FeePlugin

BOB_FEE_URL = "https://bankofbaroda.bank.in/interest-rate-and-service-charges/service-charges"


def parse(html, source_url):
    """BOB's schedule of charges page has an 'Inward Remittances other than
    Exports' table; the charge is Nil when credited to a BOB account, a flat
    fee otherwise — not split by individual/trade or account type."""
    soup = BeautifulSoup(html, "html.parser")

    for table in soup.find_all("table"):
        text = table.get_text(" ", strip=True)
        if "Inward Remittance" not in text:
            continue

        for row in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
            if len(cells) < 3 or "Inward Remittance" not in cells[1]:
                continue

            charge_cell = cells[-1]
            match = re.search(
                r"Nil where proceeds are to be credited to our account\.?\s*"
                r"In all other cases\s*-?\s*Rs\.?\s*([\d,.]+)",
                charge_cell,
            )
            if match:
                return {
                    "rules": [
                        {"label": "Credited to a Bank of Baroda account", "charge": "Nil"},
                        {"label": "Otherwise (e.g. paid out elsewhere)", "charge": f"Rs.{match.group(1)}"},
                    ],
                    "note": None,
                    # fee_inr uses the "credited to a BOB account" case — the
                    # relevant one for someone deciding whether to receive
                    # money at BOB.
                    "fee_inr": 0,
                }
    return None


PLUGIN = FeePlugin(
    name="Bank of Baroda",
    slug="bob",
    source_url=BOB_FEE_URL,
    parse=parse,
    kind="html",
)
