import re

import pdfplumber
import io

from .base import FeePlugin

CANARA_FEE_URL = "https://www.canarabank.bank.in/documents/d/guest/forex-20service-20charges-20annex-20wef-2002022026"


def parse(pdf_bytes, source_url):
    """Canara's forex charges PDF splits inward (non-export) remittance
    charges by individual vs non-individual (trade), not account type."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)

    section = re.search(
        r"Inward Remittances \(Non-Export\).*?(?=\n[A-Z]\.\d|\nB\.|\Z)", text, re.S
    )
    if not section:
        return None
    block = section.group(0)

    individual = re.search(r"For Individuals:\s*(Nil|Rs\.?\s*[\d,.]+)", block)
    trade = re.search(
        r"For other than Individuals:\s*Flat Rs\.?\s*([\d,.]+)/?-?\s*per\s*payment", block, re.S
    )

    if not individual and not trade:
        return None

    rules = []
    if individual:
        rules.append({"label": "Individual", "charge": individual.group(1).strip()})
    if trade:
        rules.append({"label": "Non-Individual / Trade", "charge": f"Flat Rs.{trade.group(1)} per payment"})

    note = None
    if "commission in lieu of exchange" in block.lower():
        note = "If the remittance is paid out in foreign currency, commission in lieu of exchange is charged in addition."

    return {"rules": rules, "note": note}


PLUGIN = FeePlugin(
    name="Canara Bank",
    slug="canara",
    source_url=CANARA_FEE_URL,
    parse=parse,
    kind="pdf",
)
