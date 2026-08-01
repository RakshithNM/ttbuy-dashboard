from bs4 import BeautifulSoup

from .base import FeePlugin

IDFCFIRST_FEE_URL = "https://www.idfcfirst.bank.in/personal-banking/forex/inward-remittance"

MARKER = "Zero processing fees"


def parse(html, source_url):
    """IDFC FIRST's inward remittance page advertises zero processing fees
    (unlike the TT rate page, this one is plain HTML, no browser needed)."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    if MARKER not in text:
        return None

    return {
        "rules": [{"label": "Inward remittance", "charge": "Zero processing fees"}],
        "note": "Correspondent/intermediary banks may still levy their own charges before the funds reach IDFC FIRST.",
        "fee_inr": 0,
    }


PLUGIN = FeePlugin(
    name="IDFC FIRST Bank",
    slug="idfcfirst",
    source_url=IDFCFIRST_FEE_URL,
    parse=parse,
    kind="html",
)
