import io
import re

import pdfplumber

from .base import FeePlugin

KOTAK_FEE_URL = "https://images.kotak.bank.in/bank/mailers/2026/files/811_GSFC_Apr_26.pdf"


def parse(pdf_bytes, source_url):
    """Kotak's 811 savings schedule doesn't list a separate charge for the
    inward remittance credit itself (consistent with several peer banks
    that charge Nil) — the only explicit line item is the FIRC certificate
    fee, which is what's actually published and verifiable."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)

    match = re.search(r"Remittance Certificate \(FIRC\)\s*-\s*(?:₹|Rs\.?)\s*([\d,]+)/", text)
    if not match:
        return None

    return {
        "rules": [{"label": "FIRC certificate (if requested)", "charge": f"Rs.{match.group(1)}"}],
        "note": "No separate charge for the inward remittance credit itself was found in Kotak's published schedule.",
        # Absence of a stated fee isn't the same as a confirmed "Nil" (unlike
        # banks that explicitly say Free/No Charge/Nil) — leave unknown
        # rather than assume free.
        "fee_inr": None,
    }


PLUGIN = FeePlugin(
    name="Kotak Mahindra Bank",
    slug="kotak",
    source_url=KOTAK_FEE_URL,
    parse=parse,
    kind="pdf",
)
