import io
import re

import pdfplumber

from .base import FeePlugin

SBI_FEE_URL = "https://sbi.bank.in/webfiles/uploads/nri/NRI_SERVICE%20CHARGES.pdf"


def parse(pdf_bytes, source_url):
    """SBI's NRI service charges PDF has an "Inward Remittance to India"
    section; the generic SWIFT/Wire Transfer charge isn't split by account
    type or purpose. Separate branded "Express Remit" corridors (UK/Canada/
    Worldwide) have their own fee structure, called out as a note rather
    than parsed in full — they're a specific product, not the general case."""
    fee = None
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if "Inward Remittance to India" not in text:
                continue
            # The PDF's two-column layout means the figure (₹25/-) appears
            # between "SWIFT /" and "Wire Transfer mechanism" in flat text,
            # not after it — anchor on the SWIFT phrase, not the full label.
            match = re.search(r"Funds transfer through SWIFT\s*/?\s*Rs\.?\s*([\d,]+)/?-?", text.replace("₹", "Rs."))
            if match:
                fee = match.group(1)
            break

    if fee is None:
        return None

    return {
        "rules": [{"label": "Inward remittance via SWIFT / Wire Transfer", "charge": f"Rs.{fee}"}],
        "note": (
            "SBI's branded Express Remit corridors (UK/Canada/Worldwide) have a "
            "separate fee structure for specific remittance products."
        ),
        "fee_inr": float(fee.replace(",", "")),
    }


PLUGIN = FeePlugin(
    name="State Bank of India",
    slug="sbi",
    source_url=SBI_FEE_URL,
    parse=parse,
    kind="pdf",
)
