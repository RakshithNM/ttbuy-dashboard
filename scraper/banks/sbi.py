import io
import re

import pdfplumber

from ..core import TARGET_CURRENCIES, normalize_date
from .base import BankPlugin

SBI_URL = "https://sbi.bank.in/documents/16012/1400784/FOREX_CARD_RATES.pdf"


def parse(pdf_bytes, source_url):
    """SBI's card-rate PDF has one table with header:
    CURRENCY, <code>, TT BUY, TT SELL, BILL BUY, BILL SELL, FOREX TRAVEL CARD BUY/SELL, CN BUY, CN SELL.
    The code cell is formatted like 'USD/INR'; TT Buy is the first rate column (index 2)."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = pdf.pages[0].extract_text() or ""
        table = pdf.pages[0].extract_tables()[0] if pdf.pages[0].extract_tables() else []

    date_match = re.search(r"Date\s+(\d{2}-\d{2}-\d{4})", text)
    time_match = re.search(r"Time\s+([0-9:]+\s*[AP]M)", text, re.I)
    rate_date = normalize_date(date_match.group(1)) if date_match else None
    published_at = time_match.group(1).strip() if time_match else None

    results = {}
    for row in table:
        if not row or len(row) <= 2:
            continue
        code = next((c for c in TARGET_CURRENCIES if row[1] == f"{c}/INR"), None)
        if code is None or code in results:
            continue

        results[code] = {
            "Rate_Date": rate_date,
            "Published_At": published_at,
            "TT_Buy": row[2],
            "Raw_Data_Row": row,
        }
    return results or None


PLUGIN = BankPlugin(
    name="State Bank of India",
    slug="sbi",
    live_url=SBI_URL,
    wayback_urls=[SBI_URL],
    parse=parse,
    kind="pdf",
)
