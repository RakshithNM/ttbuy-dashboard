import io
import re

import pdfplumber

from ..core import normalize_date
from .base import BankPlugin

JKBANK_URL = "https://eapp.jkb.bank.in/eintraweb/forex-rates"


def parse(pdf_bytes, source_url):
    """J&K Bank's card-rate PDF header: SL.NO, CURRENCY, then paired
    Buy/Sell columns for TT, TC, BILL, CPC, CN. TT Buy is the first rate
    column, index 2."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = pdf.pages[0].extract_text() or ""
        table = pdf.pages[0].extract_tables()[0] if pdf.pages[0].extract_tables() else []

    date_match = re.search(r"Date:\s*(\d{2}-\d{2}-\d{2})", text)
    time_match = re.search(r"Time:\s*([\d.]+)", text)
    rate_date = normalize_date(date_match.group(1)) if date_match else None
    published_at = time_match.group(1) if time_match else None

    for row in table:
        if not row or len(row) <= 2 or row[1] != "USD":
            continue
        return {
            "Rate_Date": rate_date,
            "Published_At": published_at,
            "TT_Buy": row[2],
            "Raw_Data_Row": row,
        }
    return None


PLUGIN = BankPlugin(
    name="Jammu & Kashmir Bank",
    slug="jkbank",
    live_url=JKBANK_URL,
    wayback_urls=[JKBANK_URL],
    parse=parse,
    kind="pdf",
)
