import io
import re

import pdfplumber

from ..core import TARGET_CURRENCIES, normalize_date
from .base import BankPlugin

JKBANK_URL = "https://eapp.jkb.bank.in/eintraweb/forex-rates"


def parse(pdf_bytes, source_url):
    """J&K Bank's card-rate PDF has two tables: page 1 covers major
    currencies (SL.NO, CURRENCY, then paired Buy/Sell columns for TT, TC,
    BILL, CPC, CN — TT Buy at index 2); AED isn't in that table, it's on
    page 2 in a simpler table (S.No, 'AED Arab Emirate Dirham', Buying Rate,
    Selling Rate) with only one buy rate, which we use as TT Buy."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = pdf.pages[0].extract_text() or ""
        tables = [t for page in pdf.pages for t in page.extract_tables()]

    date_match = re.search(r"Date:\s*(\d{2}-\d{2}-\d{2})", text)
    time_match = re.search(r"Time:\s*([\d.]+)", text)
    rate_date = normalize_date(date_match.group(1)) if date_match else None
    published_at = time_match.group(1) if time_match else None

    results = {}
    for table in tables:
        for row in table:
            if not row or len(row) <= 2 or not row[1]:
                continue
            if row[1].upper() in TARGET_CURRENCIES:
                code = row[1].upper()
                tt_buy = row[2]
            else:
                code = next((c for c in TARGET_CURRENCIES if row[1].upper().startswith(c)), None)
                tt_buy = row[2]
            if code is None or code in results:
                continue

            results[code] = {
                "Rate_Date": rate_date,
                "Published_At": published_at,
                "TT_Buy": tt_buy,
                "Raw_Data_Row": row,
            }
    return results or None


PLUGIN = BankPlugin(
    name="Jammu & Kashmir Bank",
    slug="jkbank",
    live_url=JKBANK_URL,
    wayback_urls=[JKBANK_URL],
    parse=parse,
    kind="pdf",
)
