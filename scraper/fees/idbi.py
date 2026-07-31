import io
import re

import pdfplumber

from .base import FeePlugin

IDBI_FEE_URL = "https://www.idbi.bank.in/pdf/soc/RevisedTradeFinanceScheduleofCharges2019.pdf"


def parse(pdf_bytes, source_url):
    """IDBI's trade finance schedule has a "Foreign Currency Inward
    Remittances" section that splits by individual vs non-individual, not
    account type."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)

    non_individual = re.search(r"For Customers Other than\s*Rs\.?\s*([\d,]+)/?-?\s*Flat", text, re.S)
    individual = re.search(r"For individual customers\s*(Free|Rs\.?\s*[\d,]+/?-?)", text, re.S)

    if not non_individual and not individual:
        return None

    rules = []
    if individual:
        rules.append({"label": "Individual", "charge": individual.group(1).strip()})
    if non_individual:
        rules.append({"label": "Non-Individual / Trade", "charge": f"Flat Rs.{non_individual.group(1)}"})

    return {"rules": rules, "note": None}


PLUGIN = FeePlugin(
    name="IDBI Bank",
    slug="idbi",
    source_url=IDBI_FEE_URL,
    parse=parse,
    kind="pdf",
)
