import io
import re

import pdfplumber

from ..core import TARGET_CURRENCIES, normalize_date
from .base import BankPlugin

RBL_API_URL = "https://www.rbl.bank.in/fxadmin_getfx"
RBL_PDF_BASE = "https://webassets.rbl.bank.in/fxadmin/homepagefxrate/"


def resolve_url(api_response):
    """The /fxadmin_getfx endpoint returns the current PDF filename as a
    JSON-quoted string, e.g. "CardRate-EXIM-CardRate-31-Jul-26T09_20_10.pdf".
    Strip the quotes and prepend the CDN base URL."""
    filename = api_response.strip().strip('"')
    if not filename.endswith(".pdf"):
        return None
    return RBL_PDF_BASE + filename


def parse(pdf_bytes, source_url):
    """RBL's card-rate PDF has a single header row followed by data rows:
    FCY | TT Buy | Bill Buy | Forex Card Offload | Currency Notes - Buy | …
    TT Buy is at index 1."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = pdf.pages[0].extract_text() or ""
        tables = pdf.pages[0].extract_tables()

    date_match = re.search(r"FOREX RATES FOR ([\d\w-]+) as of ([\d:]+\s*[AP]M)", text, re.I)
    rate_date = normalize_date(date_match.group(1)) if date_match else None
    published_at = date_match.group(2).strip() if date_match else None

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
    name="RBL Bank",
    slug="rbl",
    live_url=RBL_API_URL,
    wayback_urls=[],
    parse=parse,
    kind="pdf_discover",
    resolve_url=resolve_url,
)
