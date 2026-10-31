import io
import re

import pdfplumber

from ..core import TARGET_CURRENCIES, normalize_date
from .base import BankPlugin

# Previously noted as "image-based PDF" in research, but as of 2026 the PDF
# has real text layers — pdfplumber extracts cleanly.
# The bank moved from .co.in to .bank.in in Oct 2026; the old host no longer
# accepts connections. Keep the old URL for archive (Wayback) lookups.
UNIONBANK_URL = (
    "https://www.unionbankofindia.bank.in/pdf/"
    "foreign-exchange-card-rates-applicable-to-various-forex-transactions.pdf"
)
UNIONBANK_OLD_URL = (
    "https://www.unionbankofindia.co.in/pdf/"
    "Foreign-Exchange-card-rates-applicable-to-various-forex-transactions.pdf"
)


def parse(pdf_bytes, source_url):
    """Union Bank's card-rate PDF table has TT Buying at column index 4 in both
    the old layout (None | Currency | TT Sell | Bill Sell | TT Buy | …) and the
    new layout introduced after Sep 9 2026 (Currency | SPOT | TT Sell | Bill Sell
    | TT Buy | …). The currency code moved from index 1 to index 0. Handle both
    by checking whichever cell contains a TARGET_CURRENCIES code."""
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
            if not row or len(row) < 5:
                continue
            if row[0] and str(row[0]).upper() in TARGET_CURRENCIES:
                code = str(row[0]).upper()
            elif row[1] and str(row[1]).upper() in TARGET_CURRENCIES:
                code = str(row[1]).upper()
            else:
                continue
            if code in results:
                continue
            results[code] = {
                "Rate_Date": rate_date,
                "Published_At": published_at,
                "TT_Buy": row[4],
                "Raw_Data_Row": row,
            }
    return results or None


PLUGIN = BankPlugin(
    name="Union Bank of India",
    slug="unionbank",
    live_url=UNIONBANK_URL,
    wayback_urls=[UNIONBANK_URL, UNIONBANK_OLD_URL],
    parse=parse,
    kind="pdf",
)
