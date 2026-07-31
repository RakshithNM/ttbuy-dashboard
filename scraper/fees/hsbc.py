import re

from bs4 import BeautifulSoup

from .base import FeePlugin

HSBC_FEE_URL = "https://www.hsbc.co.in/international/remittance-fees-and-charges/"


def parse(html, source_url):
    """HSBC's remittance fees page splits inward wire processing by customer
    tier (NR/Premier get it free), not by individual/trade or account type."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    match = re.search(
        r"Inward wire transfer processing\s*(?:Charge amount\s*)?"
        r"INR\s*([\d,]+)\s*\+\s*applicable taxes[^.]*\.\s*Free for HSBC NR and Premier customers",
        text,
    )
    if not match:
        return None

    return {
        "rules": [
            {"label": "Standard", "charge": f"Rs.{match.group(1)} + taxes"},
            {"label": "HSBC NR / Premier customers", "charge": "Free"},
        ],
        "note": None,
    }


PLUGIN = FeePlugin(
    name="HSBC",
    slug="hsbc",
    source_url=HSBC_FEE_URL,
    parse=parse,
    kind="html",
)
