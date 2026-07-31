from .base import FeePlugin

BANDHAN_FEE_PDF_URL = (
    "https://bandhan.bank.in/sites/default/files/2026-01/"
    "Non-Trade-Inward-Remittances-Brochure-28012026.pdf"
)


def parse(pdf_bytes, source_url):
    """Bandhan does publish a fee brochure for non-trade inward remittances,
    but it's built from vector paths (text converted to outlines) rather
    than real text/images — pdfplumber extracts zero characters and zero
    images from it, so it can't be parsed without OCR. A human can still
    open the PDF and read it visually, which is why we still link to it."""
    if not pdf_bytes.startswith(b"%PDF"):
        return None

    return {
        "rules": [],
        "note": (
            "Bandhan publishes a fee brochure for this, but it's built from vector graphics rather "
            "than extractable text, so we can't parse the actual numbers automatically. Open the PDF "
            "below to read it directly."
        ),
    }


PLUGIN = FeePlugin(
    name="Bandhan Bank",
    slug="bandhan",
    source_url=BANDHAN_FEE_PDF_URL,
    parse=parse,
    kind="pdf",
)
