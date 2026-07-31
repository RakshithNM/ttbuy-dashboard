from bs4 import BeautifulSoup

from .base import FeePlugin

DCB_INFO_URL = "https://www.dcb.bank.in/fees-and-charges/non-resident-accounts"


def parse(html, source_url):
    """No page checked states an inward remittance fee for DCB — their fees
    are fragmented across many account-tier "Schedule of Benefits and Fees"
    PDFs (Basic/Special/Classic/Happy/Niyo/NRE-NRO Classic) covering only
    domestic NEFT/RTGS/DD charges, and their trade-finance, DCB Remit, and
    resident/non-resident fee pages describe inward remittance as a service
    without ever stating a number."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    if "Fees" not in text or "Charges" not in text:
        return None

    return {
        "rules": [],
        "note": (
            "DCB doesn't state an inward remittance fee on any page we could find — their published "
            "fee schedules only cover domestic transfers (NEFT/RTGS/DD), and pages describing inward "
            "remittance as a service never give a figure."
        ),
    }


PLUGIN = FeePlugin(
    name="DCB Bank",
    slug="dcb",
    source_url=DCB_INFO_URL,
    parse=parse,
    kind="html",
)
