import re

import pdfplumber
import io

from .base import FeePlugin

# SBI's general (non-NRI) forex service charges notice — a revision effective
# 01.05.2025. Deliberately not the NRI-specific service charges document:
# that one covers NRI account holders, who often get preferential/waived
# treatment, so it isn't representative of the general/individual case this
# site's calculator is about.
SBI_FEE_URL = "https://sbi.bank.in/documents/16012/76239/Foreign_Exchange_Transaction_Related_Service_Charges.pdf"


def parse(pdf_bytes, source_url):
    """SBI's "8. INWARD REMITTANCE (Other than Export/FDI/FCRA)" section
    states "No Charges" for the general case — TTs/MTs/DDs credited once
    cover has reached SBI's Nostro account, which is what a plain SWIFT
    inward remittance is. Sub-items a-d cover specific edge cases (payout
    as a foreign currency instrument, foreign correspondent bank prefunded
    instructions, FCY cheque collection) rather than the general case."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)

    match = re.search(
        r"INWARD REMITTANCE \(Other than Export/FDI/FCRA\)\s*"
        r"(No Charges|Rs\.?\s*[\d,]+/?-?)[^(]*\(Out of Pocket Expenses",
        text,
    )
    if not match:
        return None

    value = match.group(1).strip()
    fee_inr = 0.0 if value == "No Charges" else float(re.sub(r"[^\d.]", "", value))

    return {
        "rules": [{"label": "Inward remittance (credited once cover reaches SBI)", "charge": value}],
        "note": (
            "Separate charges apply if you want the funds paid out as a foreign currency "
            "instrument (DD/MT/PO/TT) instead of credited to your account, or for FCY cheque collection."
        ),
        "fee_inr": fee_inr,
    }


PLUGIN = FeePlugin(
    name="State Bank of India",
    slug="sbi",
    source_url=SBI_FEE_URL,
    parse=parse,
    kind="pdf",
)
