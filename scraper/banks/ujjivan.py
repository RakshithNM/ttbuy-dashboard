import io
import re

import pdfplumber

from ..core import TARGET_CURRENCIES, normalize_date
from .base import BankPlugin

UJJIVAN_LANDING_URL = "https://www.ujjivansfb.bank.in/forex-rates"
NUMERIC_RE = re.compile(r"^\d+(\.\d+)?$")


def resolve_url(html):
    """The actual rate PDF's filename has an opaque rotating hash, since
    Oct 2026 prefixed with the rate date (forex_rates_<DDMMYYYY>_<hash>.pdf,
    earlier forex_rates_<hash>.pdf); this stable landing page always links to
    the current one."""
    match = re.search(r'href="(/assets/forex_rates_[A-Za-z0-9_]+\.pdf)"', html)
    if not match:
        return None
    return "https://www.ujjivansfb.bank.in" + match.group(1)


def parse(pdf_bytes, source_url):
    """Ujjivan's PDF table header: Currency Type, Currency in Rs, TT Buy
    (Inward remit), TT Sell (Outward remit) — TT Buy is explicitly labeled
    for inward remittance, the first value after the currency code. Since
    Oct 2026 the sheet has merged cells, so the rate table is no longer the
    first table and its rows carry empty padding cells; drop those rather
    than rely on fixed column positions. A row must carry both TT Buy and
    TT Sell: with only one value left we cannot tell which column it came
    from, and a TT Sell stored as TT Buy would be worse than a missing day."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = pdf.pages[0].extract_text() or ""
        tables = pdf.pages[0].extract_tables()

    date_match = re.search(r"Date\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", text)
    time_match = re.search(r"Time\s+([\d.]+\s*[ap]m)", text, re.I)
    rate_date = normalize_date(date_match.group(1)) if date_match else None
    published_at = time_match.group(1).strip() if time_match else None

    results = {}
    for table in tables:
        for raw_row in table:
            row = [cell.strip() for cell in raw_row or [] if cell and cell.strip()]
            if len(row) < 4:
                continue
            code = row[1]
            if code not in TARGET_CURRENCIES or code in results:
                continue
            if not all(NUMERIC_RE.match(value) for value in row[2:4]):
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
