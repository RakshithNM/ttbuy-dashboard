from bs4 import BeautifulSoup

from .base import FeePlugin

DBS_FEE_URL = "https://www.dbs.bank.in/digibank/in/banking/remittance/remittance-fees-and-charges"


def parse(html, source_url):
    """DBS's remittance fees page is JS-rendered (same as its TT rate page)
    — nothing in the raw HTTP response, hence kind="browser". It advertises
    zero fees for inward/outward remittance to specific countries."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    if "charges zero remittance fees for both inward and outward remittances" not in text:
        return None

    return {
        "rules": [{"label": "Inward remittance (specific countries)", "charge": "Zero fees"}],
        "note": "Correspondent/intermediary banks may still levy their own charges before the funds reach DBS.",
    }


PLUGIN = FeePlugin(
    name="DBS Bank India",
    slug="dbs",
    source_url=DBS_FEE_URL,
    parse=parse,
    kind="browser",
)
