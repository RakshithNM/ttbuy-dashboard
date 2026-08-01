import io
import re

import pdfplumber

from .base import FeePlugin

# PNB's forex schedule of charges — a stable server-side token that always
# resolves to the current published schedule. Found via search result snippet
# "Page 1 of 10 FOREX S No Particulars Charges 1. EXPORT 1.1."
PNB_FEE_URL = "https://pnb.bank.in/downloadprocess.aspx?fid=ecry+oz2YLsK3sJllMjEAA%3D%3D"


def parse(pdf_bytes, source_url):
    """PNB Section 5.1 — "Inward Remittances (Other than Exports)":
    encashment of TTs/MTs/DDs where cover received in Nostro.
    Slab: up to ₹10L = ₹100; above ₹10L = ₹250.
    General guideline x: NRE/NRO/FCNR/FCRA accounts — no commission."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)

    # Locate the inward remittance slab block
    m_block = re.search(
        r"Inward Remittances\s+"
        r"Up to ₹10 Lakh\s+(₹[\d,/\-]+\s*Flat)\s+"
        r"Above ₹10 Lakh\s+(₹[\d,/\-]+\s*Flat)",
        text,
    )
    if not m_block:
        return None

    upto_10l = re.sub(r"\s+", " ", m_block.group(1)).strip()   # e.g. "₹100/- Flat"
    above_10l = re.sub(r"\s+", " ", m_block.group(2)).strip()  # e.g. "₹250/- Flat"

    # Verify the NRE/NRO guideline is still present
    nro_free = bool(re.search(r"NRE/NRO/FCNR and FCRA accounts.*no commission", text, re.S))

    rules = [
        {"label": "Up to ₹10 lakh (regular account)", "charge": upto_10l},
        {"label": "Above ₹10 lakh (regular account)", "charge": above_10l},
    ]
    if nro_free:
        rules.append({"label": "NRE / NRO / FCNR / FCRA account", "charge": "Free"})

    return {
        "rules": rules,
        "note": "Charges apply to regular (resident) accounts. NRE/NRO/FCNR/FCRA accounts are exempt.",
        "fee_inr": None,  # depends on account type — can't collapse to a single number
    }


PLUGIN = FeePlugin(
    name="Punjab National Bank",
    slug="pnb",
    source_url=PNB_FEE_URL,
    parse=parse,
    kind="pdf",
)
