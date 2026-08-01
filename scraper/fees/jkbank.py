import io
import re

import pdfplumber

from .base import FeePlugin

JKBANK_FEE_URL = "https://www.jkbank.com/pdfs/servicecharge/forex.pdf"


def parse(pdf_bytes, source_url):
    """J&K Bank's forex service charges PDF (section B.14) — "Other
    remittances not related to exports" (B14.4) is the general personal
    inward remittance case, tiered by amount. Encashment of NRE/FCNR-bound
    instruments is separately Nil (B14.1)."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)

    other = re.search(
        r"Other remittances not related to exports\.\s*Upto Rs\.?([\d.]+) ?lacs\s*:\s*Flat Rs\.?([\d,]+)/?-?"
        r"\s*per remittance\s*Above Rs\.?([\d.]+) ?lacs:\s*Flat Rs\.?([\d,]+)/?-?",
        text,
        re.S,
    )
    if not other:
        return None

    return {
        "rules": [
            {
                "label": "Personal inward remittance (not export-related)",
                "charge": f"Rs.{other.group(2)} (up to Rs.{other.group(1)} lakh), Rs.{other.group(4)} (above)",
            }
        ],
        "note": "No commission if proceeds are deposited to an NRE/NRO/FCNR(B)/RFC/EEFC account with J&K Bank.",
        # fee_inr uses the "up to" tier — the amounts this site's calculator
        # deals with are well under the lakh-scale threshold for the higher tier.
        "fee_inr": float(other.group(2).replace(",", "")),
    }


PLUGIN = FeePlugin(
    name="Jammu & Kashmir Bank",
    slug="jkbank",
    source_url=JKBANK_FEE_URL,
    parse=parse,
    kind="pdf",
)
