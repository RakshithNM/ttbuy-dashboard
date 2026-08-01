import io
import re

import pdfplumber

from .base import FeePlugin

HDFC_FEE_URL = (
    "https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/pdf/notice-board/"
    "rates-and-charges/feesandchargesforforexservicesenglish.pdf"
)


def parse(pdf_bytes, source_url):
    """HDFC's forex services fee sheet: inward remittance itself is free,
    but a FIRC certificate (often needed as proof of the remittance) costs
    separately. No individual/trade or account-type split published."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)

    if not re.search(r"Remittance Inward\s*No Charge", text):
        return None

    firc = re.search(r"FIRC Charge for Inward Remittance[^\n]*\n?\s*Rs\.?\s*([\d,]+)/?-?\s*per FIRC", text)

    return {
        "rules": [{"label": "Inward remittance", "charge": "No Charge"}],
        "note": f"FIRC certificate (if needed): Rs.{firc.group(1)} per FIRC" if firc else None,
        "fee_inr": 0,
    }


PLUGIN = FeePlugin(
    name="HDFC Bank",
    slug="hdfc",
    source_url=HDFC_FEE_URL,
    parse=parse,
    kind="pdf",
)
