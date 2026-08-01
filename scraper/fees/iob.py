import io
import re

import pdfplumber

from .base import FeePlugin

IOB_FEE_URL = "https://www.iob.bank.in/documents/d/guest/schedule-forex-service-charges-01092015"


def parse(pdf_bytes, source_url):
    """IOB's forex service charges PDF splits inward remittance charges by
    purpose (individual/non-trade vs trade), not by account type. The
    "Inward Remittances" section is a two-column table where the two rate
    lines share one cell — table extraction (not flat text) keeps that cell
    intact, since the page is laid out in two side-by-side columns that flat
    text extraction interleaves out of order."""
    cell = None
    fc_payout_cell = None
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for r in table:
                    if not r:
                        continue
                    if any(c and "Payments effected under instructions from foreign" in c for c in r):
                        cell = r[-1] or ""
                    if any(c and "paid in foreign" in c and "DD/MT/PO/TT" in c for c in r):
                        fc_payout_cell = r[-1] or ""

    if cell is None:
        return None

    individual = re.search(r"For Individuals/Non Trade:\s*Rs\.?\s*([\d,]+)", cell, re.S)
    trade = re.search(
        r"For Trade:\s*([\d.]+%\s*Min\s*Rs\.?\s*[\d,]+\s*and\s*Max\s*Rs\.?\s*[\d,]+/?-?)", cell, re.S
    )
    fc_payout = re.search(r"Rs\.?\s*([\d,]+)\+\s*SWIFT charges", fc_payout_cell or "")

    if not individual and not trade:
        return None

    rules = []
    if individual:
        rules.append({"label": "Individual / Non-Trade", "charge": f"Flat Rs.{individual.group(1)}"})
    if trade:
        rules.append({"label": "Trade", "charge": re.sub(r"\s+", " ", trade.group(1)).strip()})

    note = None
    if fc_payout:
        note = f"If paid out in foreign currency (DD/MT/PO/TT): Rs.{fc_payout.group(1)} + SWIFT charges"

    # fee_inr uses the individual/non-trade figure — the case that applies to
    # someone receiving a personal remittance, not the trade tier.
    fee_inr = float(individual.group(1).replace(",", "")) if individual else None
    return {"rules": rules, "note": note, "fee_inr": fee_inr}


PLUGIN = FeePlugin(
    name="Indian Overseas Bank",
    slug="iob",
    source_url=IOB_FEE_URL,
    parse=parse,
    kind="pdf",
)
