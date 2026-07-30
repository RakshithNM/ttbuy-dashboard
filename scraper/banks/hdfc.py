import io
import re

import pdfplumber

from ..core import TARGET_CURRENCIES, normalize_date
from .base import BankPlugin

HDFC_URL = (
    "https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/personal-banking/"
    "discover-products/interest-rates/hdfc-bank-treasury-forex-card-rates.pdf"
)


def parse(pdf_bytes, source_url):
    """HDFC's card-rate PDF table columns: CurrencyType, Currency code, Cash
    Buying, Cash Selling, BillsBuying, BillsSelling, T.T.Buying(Inw Rem),
    T.T.Selling(O/w Rem), ... TT Buying for inward remittance is index 6,
    explicitly labeled '(Inw Rem)'. A second, unrelated forward-rates table
    sometimes gets merged into the same rows past index 10 — ignored."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = pdf.pages[0].extract_text() or ""
        table = pdf.pages[0].extract_tables()[0] if pdf.pages[0].extract_tables() else []

    match = re.search(r"DATE:\s*(\d{2}-\d{2}-\d{4})\s*TIME:\s*([0-9:]+\s*[AP]M)", text, re.I)
    rate_date = normalize_date(match.group(1)) if match else None
    published_at = match.group(2).strip() if match else None

    results = {}
    for row in table:
        if not row or len(row) <= 6:
            continue
        code = row[1]
        if code not in TARGET_CURRENCIES or code in results:
            continue

        results[code] = {
            "Rate_Date": rate_date,
            "Published_At": published_at,
            "TT_Buy": row[6],
            "Raw_Data_Row": row[:11],
        }
    return results or None


PLUGIN = BankPlugin(
    name="HDFC Bank",
    slug="hdfc",
    live_url=HDFC_URL,
    wayback_urls=[HDFC_URL],
    parse=parse,
    kind="pdf",
)
