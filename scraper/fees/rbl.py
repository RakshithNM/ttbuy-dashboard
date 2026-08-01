import io
import re

import pdfplumber

from .base import FeePlugin

# RBL's "Schedule of Charges — Domestic Trade, Foreign Trade & Cross Border
# Remittances", effective October 20, 2025. Section A, item 1: Inward
# Remittances.
RBL_FEE_URL = "https://webassets.rbl.bank.in/document/service-charges/trade-finance-schedule-of-charges.pdf"


def parse(pdf_bytes, source_url):
    """RBL Section 1 — INWARD REMITTANCES:
    1.1 Payment instructions received from foreign correspondents (Nostro credit): Free
    1.2 Clean payments via SWIFT MT 103 credited to customer account: Rs. 250/-"""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)

    # Locate the inward remittances block
    m_block = re.search(
        r"INWARD REMITTANCES.*?"
        r"correspondents.*?Nostro account\s*\n?\s*(Free)\s*"
        r".*?MT 103\).*?account.*?\n?\s*(Rs\.?\s*[\d,]+/?-?)",
        text,
        re.S | re.I,
    )
    if not m_block:
        # Fallback: just find the MT 103 line
        m_mt103 = re.search(
            r"MT 103\).*?(?:applicable\s+purpose\s+code\s+wise\)?\s*\n?\s*)?(Rs\.?\s*[\d,]+/?-?)",
            text,
            re.S | re.I,
        )
        if not m_mt103:
            return None
        swift_charge = re.sub(r"\s+", " ", m_mt103.group(1)).strip()
    else:
        swift_charge = re.sub(r"\s+", " ", m_block.group(2)).strip()

    m_amt = re.search(r"[\d,]+", swift_charge) if swift_charge else None
    amt = float(m_amt.group().replace(",", "")) if m_amt else None

    return {
        "rules": [
            {
                "label": "Payment instructions to Nostro account (correspondent bank credit)",
                "charge": "Free",
            },
            {
                "label": "Clean SWIFT MT 103 inward credited to customer account",
                "charge": swift_charge,
            },
        ],
        "note": (
            "If a single remittance carries multiple purpose codes, "
            "Rs. 250/- applies per purpose code."
        ),
        "fee_inr": amt,
    }


PLUGIN = FeePlugin(
    name="RBL Bank",
    slug="rbl",
    source_url=RBL_FEE_URL,
    parse=parse,
    kind="pdf",
)
