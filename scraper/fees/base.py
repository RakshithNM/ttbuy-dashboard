from dataclasses import dataclass
from typing import Any, Callable, Optional

# parse(content, source_url) -> {
#   "rules": [{"label": str, "charge": str}, ...],  # one entry per case the
#     bank actually publishes — banks split this differently (individual vs
#     trade, savings vs current, credited-to-own-account vs not, ...), so
#     this stays a flat label/charge list rather than forcing every bank into
#     the same axis. Free text, not meant to be parsed back into numbers.
#   "note": str | None,  # extra context that doesn't fit a single rule row
#   "fee_inr": float | None,  # a single approximate flat rupee figure for
#     the standard/individual case (the one most people receiving a personal
#     remittance would pay), used to net the fee out of the amount calculator
#     on the site. 0 means confirmed free; None means we don't know (no
#     published figure, or the real charge is too conditional — segment
#     tiers, min/max caps — to responsibly collapse into one number).
#     Deliberately separate from "rules" above, which stays free text.
# } | None
ParseFn = Callable[[Any, str], Optional[dict]]


@dataclass
class FeePlugin:
    name: str
    slug: str
    source_url: str
    parse: ParseFn
    kind: str = "html"  # "html" (decoded text), "pdf" (raw bytes), or
    # "browser" (Playwright-rendered HTML, for pages whose content loads via
    # client-side JS)
