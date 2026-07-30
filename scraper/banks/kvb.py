import io
import re

import pdfplumber

from ..core import TARGET_CURRENCIES, normalize_date
from .base import BankPlugin

KVB_URL = "https://kvb.bank.in/manager/fx-card-rate/pdf/fx_card_rates.pdf"


def parse(pdf_bytes, source_url):
    """Karur Vysya's card-rate PDF has a two-tier header: SELLING RATES
    (TT, BILL, TC) then a gap column then BUYING RATES (TT, BILL, CHQS, TC).
    TT Buy is the first column of the Buying group, index 5. Currency cells
    look like '( USD ) US DOLLAR'."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = pdf.pages[0].extract_text() or ""
        tables = pdf.pages[0].extract_tables()

    date_match = re.search(r"CARD RATES AS ON\s+(\d{2}-\d{2}-\d{4})", text, re.I)
    time_match = re.search(r"Time\s*:\s*([\d:]+)", text)
    rate_date = normalize_date(date_match.group(1)) if date_match else None
    published_at = time_match.group(1) if time_match else None

    results = {}
    for table in tables:
        for row in table:
            if not row or len(row) <= 5 or not row[0]:
                continue
            code = next((c for c in TARGET_CURRENCIES if f"( {c} )" in row[0].upper()), None)
            if code is None or code in results:
                continue

            results[code] = {
                "Rate_Date": rate_date,
                "Published_At": published_at,
                "TT_Buy": row[5],
                "Raw_Data_Row": row,
            }
    return results or None


PLUGIN = BankPlugin(
    name="Karur Vysya Bank",
    slug="kvb",
    live_url=KVB_URL,
    wayback_urls=[KVB_URL],
    parse=parse,
    kind="pdf",
)
