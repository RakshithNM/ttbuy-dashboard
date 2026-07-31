import io
import re

import pdfplumber

from .base import FeePlugin

AXIS_FEE_URL = (
    "https://www.axis.bank.in/docs/default-source/default-document-library/"
    "inward-wire-schedule-of-charges.pdf"
)


def parse(pdf_bytes, source_url):
    """Axis Bank's inward wire (SWIFT) schedule tiers commission by customer
    segment (Burgundy/Priority/Others) for Resident and Non-Resident
    customers separately, but calls out one important override: individuals
    remitting into a Current Account pay a flat fee regardless of segment.
    We surface the "Others" (no special relationship) tier — the rate a
    typical customer without a premium banking relationship pays — plus the
    Current Account override, rather than every segment row."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)

    non_resident = re.search(r"Non-Resident.*?Others\s+INR\s*([\d,]+)", text, re.S)
    resident = re.search(r"(?<!Non-)Resident\s+Burgundy.*?Others\s+INR\s*([\d,]+)", text, re.S)
    current_account = re.search(
        r"individuals through Current Accounts,\s*commission\s*charges of INR\s*([\d,]+)\s*\+\s*GST",
        text,
        re.S,
    )

    if not resident and not non_resident:
        return None

    rules = []
    if resident:
        rules.append({"label": "Resident (standard tier)", "charge": f"Rs.{resident.group(1)} + GST"})
    if non_resident:
        rules.append({"label": "Non-Resident (standard tier)", "charge": f"Rs.{non_resident.group(1)} + GST"})
    if current_account:
        rules.append(
            {
                "label": "Individuals remitting into a Current Account",
                "charge": f"Flat Rs.{current_account.group(1)} + GST (regardless of segment)",
            }
        )

    note = "Premium banking segments (Burgundy/Priority) get lower or nil charges than the standard tier shown here."
    return {"rules": rules, "note": note}


PLUGIN = FeePlugin(
    name="Axis Bank",
    slug="axis",
    source_url=AXIS_FEE_URL,
    parse=parse,
    kind="pdf",
)
