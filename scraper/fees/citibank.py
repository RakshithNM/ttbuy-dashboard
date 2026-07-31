from .base import FeePlugin

CITIBANK_INFO_URL = "https://www.axis.bank.in/forward-together"


def parse(html, source_url):
    """Citi's retail/consumer banking business in India (savings accounts,
    cards, loans) was fully migrated to Axis Bank by July 2024, confirmed on
    Axis's own migration page — individuals can no longer open a new
    Citibank account. The TT Buy rate we still scrape for "Citibank" is
    published by Citi's separate institutional/corporate banking arm, which
    has no public retail fee schedule, so this surfaces that context instead
    of numeric fee data."""
    if "Citi Migration" not in html and "Forward Together" not in html:
        return None

    return {
        "rules": [],
        "note": (
            "Citi's retail banking business in India (savings accounts, cards, loans) was fully "
            "migrated to Axis Bank by July 2024 — individuals can no longer open a new Citibank "
            "account here. The TT Buy rate shown is still published by Citi's separate "
            "institutional/corporate banking arm, so it doesn't reflect a personal account you can open."
        ),
    }


PLUGIN = FeePlugin(
    name="Citibank",
    slug="citibank",
    source_url=CITIBANK_INFO_URL,
    parse=parse,
    kind="html",
)
