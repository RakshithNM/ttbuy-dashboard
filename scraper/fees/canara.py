import io
import re

import pdfplumber

from .base import FeePlugin

CANARA_FEE_URL = "https://www.canarabank.bank.in/documents/d/guest/forex-20service-20charges-20annex-20wef-2002022026"


def parse(pdf_bytes, source_url):
    """Canara's forex charges PDF has two different "inward" sections — the
    one under "4. CLEAN INSTRUMENTS" is for cheque/DD/money-order
    encashment, not a SWIFT wire; the right one is "C.2 SWIFT Inward
    Remittances in Rupees" under the SWIFT section, split by whether the
    recipient holds a Canara account. Table extraction (not flat text)
    keeps the cell intact, since the page's column layout otherwise
    interleaves it with the adjacent Sl.No./Nature-of-charges columns."""
    cell = None
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            if "SWIFT Inward Remittances" not in (page.extract_text() or ""):
                continue
            for table in page.extract_tables():
                for row in table:
                    if row and row[1] and "SWIFT Inward Remittances" in row[1]:
                        cell = row[2] or ""

    if cell is None:
        return None

    our_customers = re.search(r"For our customers\s*Rs\.?\s*([\d,]+)", cell)
    others = re.search(r"For others\s*Rs\.?\s*([\d,]+)", cell)
    correspondent = re.search(r"Alrajhi\s*Banking and Investment Corp:\s*Rs\.?\s*([\d,]+)", cell, re.S)

    if not our_customers and not others:
        return None

    rules = []
    if our_customers:
        rules.append({"label": "Canara account holders", "charge": f"Rs.{our_customers.group(1)}"})
    if others:
        rules.append({"label": "No Canara account", "charge": f"Rs.{others.group(1)}"})

    note = None
    if correspondent:
        note = f"Rs.{correspondent.group(1)} instead if the remittance is routed via Alrajhi Banking and Investment Corp."

    return {
        "rules": rules,
        "note": note,
        # fee_inr uses the "our customers" figure — the relevant case for
        # someone deciding whether to receive money at Canara.
        "fee_inr": float(our_customers.group(1).replace(",", "")) if our_customers else None,
    }


PLUGIN = FeePlugin(
    name="Canara Bank",
    slug="canara",
    source_url=CANARA_FEE_URL,
    parse=parse,
    kind="pdf",
)
