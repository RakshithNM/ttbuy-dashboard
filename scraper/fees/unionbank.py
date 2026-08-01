import io
import re

import pdfplumber

from .base import FeePlugin

# Union Bank's "Forex Service Charges" PDF, linked from their fees-and-services
# page under "Service Charges Relating to Foreign Exchange Transactions".
UNIONBANK_FEE_URL = "https://www.unionbankofindia.bank.in/pdf/forex-service-charges.pdf"


def parse(pdf_bytes, source_url):
    """Union Bank Section 5 — INWARD REMITTANCES:
    5.1 Remittance Commission (Non Trade / Personal): Rs. 250/- flat, irrespective of amount
    5.2 Remittance Commission (Trade): Rs. 500/- (≤USD 10k) / Rs. 1500/- (>USD 10k)"""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)

    # The PDF layout: "5.1 Remittance Commission (Non Trade) (Personal  Rs. 250/- Flat …\nRemittances)"
    # The charge lands on the same line as "(Personal", before the word wrap to "Remittances)".
    m_personal = re.search(
        r"5\.1\s+Remittance Commission.*?\(Personal\s+(Rs\.?\s*[\d,]+/?-?\s*Flat[^\n]*)",
        text,
        re.S | re.I,
    )
    m_trade = re.search(
        r"5\.2\s+Remittance Commission \(Trade\)\s+"
        r"(Upto USD[^\n]+\n[^\n]+)",
        text,
        re.I,
    )

    if not m_personal:
        return None

    personal_charge = re.sub(r"\s+", " ", m_personal.group(1)).strip()
    # Strip trailing "Remittances)" that might be included if there's no newline
    personal_charge = re.sub(r"\s*Remittances\).*$", "", personal_charge, flags=re.I).strip()

    rules = [
        {"label": "Non-trade / personal remittance", "charge": personal_charge},
    ]
    if m_trade:
        trade_raw = re.sub(r"\s+", " ", m_trade.group(1)).strip()
        trade_parts = re.findall(r"(?:Upto|More than)[^=]+=\s*Rs\s*[\d,/?]+", trade_raw, re.I)
        if trade_parts:
            for part in trade_parts[:2]:
                rules.append({"label": "Trade remittance", "charge": part.strip()})
        else:
            rules.append({"label": "Trade remittance", "charge": trade_raw[:120]})

    m_amt = re.search(r"[\d,]+", personal_charge)
    fee_inr = float(m_amt.group().replace(",", "")) if m_amt else None

    return {
        "rules": rules,
        "note": "Trade tier applies to export/import-linked remittances. Personal remittance is the flat Rs. 250 figure.",
        "fee_inr": fee_inr,
    }


PLUGIN = FeePlugin(
    name="Union Bank of India",
    slug="unionbank",
    source_url=UNIONBANK_FEE_URL,
    parse=parse,
    kind="pdf",
)
