import re

from bs4 import BeautifulSoup

from .base import FeePlugin

CITYUNION_FEE_URL = "https://cityunionbank.bank.in/service-charges"


def parse(html, source_url):
    """City Union's service charges page has an 'Inward Remittances (Other
    than Advance Remittance for Exports & FDI)' row split individual vs
    non-individual (tiered by amount for the latter)."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    idx = text.find("Inward Remittances")
    if idx == -1:
        return None
    block = text[idx : idx + 500]

    individual = re.search(r"For Individuals\s*[–-]\s*(Nil|Rs\.?\s*[\d,]+)", block)
    trade = re.search(
        r"For other than Individuals\s*Upto Rs\.?([\d,.]+ ?lakhs?)\s*[–-]\s*Rs\.?([\d,]+).*?"
        r"Above Rs\.?[\d,.]+ ?[Ll]akhs? upto Rs\.?([\d,.]+ ?[Ll]akhs?)\s*[–-]\s*Rs\.?([\d,]+).*?"
        r"Above Rs\.?([\d,.]+ ?[Ll]akhs?)\s*Rs\.?([\d,]+)",
        block,
        re.S,
    )

    if not individual and not trade:
        return None

    rules = []
    if individual:
        rules.append({"label": "Individual", "charge": individual.group(1).strip()})
    if trade:
        rules.append(
            {
                "label": "Non-Individual / Trade",
                "charge": (
                    f"Rs.{trade.group(2)} (up to Rs.{trade.group(1)}), "
                    f"Rs.{trade.group(4)} (up to Rs.{trade.group(3)}), "
                    f"Rs.{trade.group(6)} (above Rs.{trade.group(5)})"
                ),
            }
        )

    return {"rules": rules, "note": None}


PLUGIN = FeePlugin(
    name="City Union Bank",
    slug="cityunion",
    source_url=CITYUNION_FEE_URL,
    parse=parse,
    kind="html",
)
