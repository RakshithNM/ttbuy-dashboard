import io
import re

import pdfplumber

from .base import FeePlugin

KVB_FEE_URL = "https://www.kvb.bank.in/docs/forex-charges.pdf"


def parse(pdf_bytes, source_url):
    """KVB's forex charges PDF has a "Remittance Inward" table; the "Clean
    inward remittance" row is tiered by amount, waived for NRE/NRO credits —
    not split by individual/trade. Table extraction (not flat text) keeps
    the tariff cell intact, since the page's column layout otherwise
    interleaves it with the adjacent "Minimum Charges" column."""
    cell = None
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            if "Remittance Inward" not in (page.extract_text() or ""):
                continue
            for table in page.extract_tables():
                for row in table:
                    if row and row[1] and "Clean inward" in row[1]:
                        cell = row[2] or ""

    if cell is None:
        return None

    match = re.search(
        r"([\d,]+)/?-?\s*upto USD ([\d,]+)\s*Equivalent\.\s*([\d,]+)/?-?\s*Beyond",
        cell,
        re.S,
    )
    if not match:
        return None

    return {
        "rules": [
            {
                "label": "Clean inward remittance",
                "charge": f"Rs.{match.group(1)} (up to USD {match.group(2)}), Rs.{match.group(3)} (above)",
            }
        ],
        "note": "Nil if credited to an NRE/NRO account.",
        # fee_inr uses the "up to USD 2000" tier — the common case.
        "fee_inr": float(match.group(1).replace(",", "")),
    }


PLUGIN = FeePlugin(
    name="Karur Vysya Bank",
    slug="kvb",
    source_url=KVB_FEE_URL,
    parse=parse,
    kind="pdf",
)
