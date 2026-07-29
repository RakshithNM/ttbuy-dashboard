import io
import re

import pdfplumber

from ..core import normalize_date
from .base import BankPlugin

CITI_URL = "https://www.citigroup.com/rcs/citigpa/storage/public/India/forex-rates.pdf"


def parse(pdf_bytes, source_url):
    """Citibank's PDF doesn't extract as a table (no ruled lines) — parse the
    'Currency TT Buying TT Selling' rows directly from the text, e.g.
    'US Dollar USD/INR 93.7870 97.6415'."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = pdf.pages[0].extract_text() or ""

    date_match = re.search(r"Date\s+(\d{1,2}-[A-Za-z]{3}-\d{2})", text)
    time_match = re.search(r"Time\s+([0-9:]+\s*[AP]M\s*IST)", text, re.I)
    rate_date = normalize_date(date_match.group(1)) if date_match else None
    published_at = time_match.group(1).strip() if time_match else None

    match = re.search(r"USD/INR\s+([\d.]+)\s+([\d.]+)", text)
    if not match:
        return None

    return {
        "Rate_Date": rate_date,
        "Published_At": published_at,
        "TT_Buy": match.group(1),
        "Raw_Data_Row": ["USD/INR", match.group(1), match.group(2)],
    }


PLUGIN = BankPlugin(
    name="Citibank",
    slug="citibank",
    live_url=CITI_URL,
    wayback_urls=[CITI_URL],
    parse=parse,
    kind="pdf",
)
