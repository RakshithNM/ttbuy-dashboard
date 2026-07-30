import io
import re

import pdfplumber

from ..core import TARGET_CURRENCIES, normalize_date
from .base import BankPlugin

UJJIVAN_LANDING_URL = "https://www.ujjivansfb.bank.in/forex-rates"


def resolve_url(html):
    """The actual rate PDF's filename has an opaque rotating hash
    (forex_rates_<hash>.pdf); this stable landing page always links to the
    current one."""
    match = re.search(r'href="(/assets/forex_rates_[a-f0-9]+\.pdf)"', html)
    if not match:
        return None
    return "https://www.ujjivansfb.bank.in" + match.group(1)


def parse(pdf_bytes, source_url):
    """Ujjivan's PDF table header: Currency Type, Currency in Rs, TT Buy
    (Inward remit), TT Sell (Outward remit) — TT Buy is explicitly labeled
    for inward remittance, index 2."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = pdf.pages[0].extract_text() or ""
        table = pdf.pages[0].extract_tables()[0] if pdf.pages[0].extract_tables() else []

    date_match = re.search(r"Date\s+(\d{2}-\d{2}-\d{2})", text)
    time_match = re.search(r"Time\s+([\d.]+\s*[ap]m)", text, re.I)
    rate_date = normalize_date(date_match.group(1)) if date_match else None
    published_at = time_match.group(1).strip() if time_match else None

    results = {}
    for row in table:
        if not row or len(row) <= 2:
            continue
        code = row[1]
        if code not in TARGET_CURRENCIES or code in results:
            continue

        results[code] = {
            "Rate_Date": rate_date,
            "Published_At": published_at,
            "TT_Buy": row[2],
            "Raw_Data_Row": row,
        }
    return results or None


PLUGIN = BankPlugin(
    name="Ujjivan Small Finance Bank",
    slug="ujjivan",
    live_url=UJJIVAN_LANDING_URL,
    wayback_urls=[UJJIVAN_LANDING_URL],
    parse=parse,
    kind="pdf_discover",
    resolve_url=resolve_url,
)
