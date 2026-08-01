import io
import re

import pdfplumber

from ..core import TARGET_CURRENCIES, normalize_date
from .base import BankPlugin

# Stable homepage download link for "Daily Foreign Exchange Rates" — the
# server-side fid token always resolves to today's card rate PDF, so the URL
# itself doesn't need to change.
PNB_URL = "https://pnb.bank.in/downloadprocess.aspx?fid=A+rrvZeJc+PIaxfEqVTIQQ=="


def parse(pdf_bytes, source_url):
    """PNB's card-rate PDF has one table with a two-row header:
    row 0 — column-group labels (TT CARD RATE, TC CARD RATE, …)
    row 1 — sub-headers (TT BUY, TT SELL, TC BUY, …)
    row 2+ — data rows: S.NO, CURRENCY, CPC, WTCS, TT BUY, TT SELL, …
    TT BUY is at index 1 (after the currency name at index 0, skipping the
    two S.NO/CPC/WTCS columns that appear only in the text layer)."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = pdf.pages[0].extract_text() or ""
        tables = pdf.pages[0].extract_tables()

    date_match = re.search(r"Card Rate dated (\d{2}/\d{2}/\d{4})", text)
    time_match = re.search(r"Card Rate dated \d{2}/\d{2}/\d{4} (\d{2}:\d{2})", text)
    rate_date = normalize_date(date_match.group(1)) if date_match else None
    published_at = time_match.group(1) if time_match else None

    results = {}
    for table in tables:
        for row in table:
            if not row or len(row) < 2:
                continue
            code = row[0]
            if code not in TARGET_CURRENCIES or code in results:
                continue
            results[code] = {
                "Rate_Date": rate_date,
                "Published_At": published_at,
                "TT_Buy": row[1],
                "Raw_Data_Row": row,
            }
    return results or None


PLUGIN = BankPlugin(
    name="Punjab National Bank",
    slug="pnb",
    live_url=PNB_URL,
    wayback_urls=[PNB_URL],
    parse=parse,
    kind="pdf",
)
