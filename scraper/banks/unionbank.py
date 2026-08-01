import io
import re

import pdfplumber

from ..core import TARGET_CURRENCIES, normalize_date
from .base import BankPlugin

# Previously noted as "image-based PDF" in research, but as of 2026 the PDF
# has real text layers — pdfplumber extracts cleanly.
UNIONBANK_URL = (
    "https://www.unionbankofindia.bank.in/pdf/"
    "foreign-exchange-card-rates-applicable-to-various-forex-transactions.pdf"
)


def parse(pdf_bytes, source_url):
    """Union Bank's card-rate PDF has a single header row followed by data rows:
    Currency | TT Selling | Bill Selling | TT Buying | Bill Buying | …
    TT Buying is at index 3."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)
        tables = []
        for page in pdf.pages:
            tables.extend(page.extract_tables())

    date_match = re.search(r"As On ([\d\w-]+ [\d:]+)", text)
    rate_date = normalize_date(date_match.group(1).split()[0]) if date_match else None
    published_at = date_match.group(1).split()[1] if date_match else None

    results = {}
    for table in tables:
        for row in table:
            if not row or len(row) < 4:
                continue
            code = row[0]
            if code not in TARGET_CURRENCIES or code in results:
                continue
            results[code] = {
                "Rate_Date": rate_date,
                "Published_At": published_at,
                "TT_Buy": row[3],
                "Raw_Data_Row": row,
            }
    return results or None


PLUGIN = BankPlugin(
    name="Union Bank of India",
    slug="unionbank",
    live_url=UNIONBANK_URL,
    wayback_urls=[UNIONBANK_URL],
    parse=parse,
    kind="pdf",
)
