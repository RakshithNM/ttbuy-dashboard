import io
import re

import pdfplumber

from .base import FeePlugin

UJJIVAN_FEE_URL = (
    "https://www.ujjivansfb.bank.in/assets/"
    "Schedule_of_charges_Fx_Services_Outward_and_Inward_Remittances_374aaed10c.pdf"
)


def parse(pdf_bytes, source_url):
    """Ujjivan's FX services schedule has a flat "Inward Remittance" transfer
    fee plus a currency-conversion GST slab — not split by individual/trade
    or account type."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)

    match = re.search(r"Inward Remittance.*?Transfer fee\s*INR\s*([\d,]+)\s*\+\s*([\d]+)%\s*GST", text, re.S)
    if not match:
        return None

    fee_inr = round(float(match.group(1).replace(",", "")) * (1 + float(match.group(2)) / 100), 2)
    return {
        "rules": [{"label": "Inward remittance transfer fee", "charge": f"Rs.{match.group(1)} + {match.group(2)}% GST"}],
        "note": "Currency conversion also attracts GST on a separate slab based on the transaction amount.",
        "fee_inr": fee_inr,
    }


PLUGIN = FeePlugin(
    name="Ujjivan Small Finance Bank",
    slug="ujjivan",
    source_url=UJJIVAN_FEE_URL,
    parse=parse,
    kind="pdf",
)
