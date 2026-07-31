from bs4 import BeautifulSoup

from .base import FeePlugin

ICICI_INFO_URL = "https://www.icici.bank.in/nri-banking/service-charges"


def parse(html, source_url):
    """No public page or PDF states an inward remittance fee for ICICI —
    checked their outward-remittance schedule (wrong direction), general
    service-charges page, 8+ NRI account-tier PDFs (Savings/Premium/Select/
    Pro/Premia/Regular), and their NRI FAQ page. None mention a figure, so
    it's likely disclosed only via app/net banking or branch. This surfaces
    that context instead of a number; parse() still checks the page loads
    correctly so a future site restructure doesn't leave a silently stale
    note in place."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    if "Service Charges" not in text:
        return None

    return {
        "rules": [],
        "note": (
            "ICICI doesn't publish an inward remittance fee on any public page or PDF we could find "
            "(checked their service charges pages and 8+ NRI account-tier documents) — it may only be "
            "disclosed via net banking/app or at a branch."
        ),
    }


PLUGIN = FeePlugin(
    name="ICICI Bank",
    slug="icici",
    source_url=ICICI_INFO_URL,
    parse=parse,
    kind="html",
)
