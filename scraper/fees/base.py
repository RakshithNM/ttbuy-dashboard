from dataclasses import dataclass
from typing import Any, Callable, Optional

# parse(content, source_url) -> {
#   "rules": [{"label": str, "charge": str}, ...],  # one entry per case the
#     bank actually publishes — banks split this differently (individual vs
#     trade, savings vs current, credited-to-own-account vs not, ...), so
#     this stays a flat label/charge list rather than forcing every bank into
#     the same axis.
#   "note": str | None,  # extra context that doesn't fit a single rule row
# } | None
ParseFn = Callable[[Any, str], Optional[dict]]


@dataclass
class FeePlugin:
    name: str
    slug: str
    source_url: str
    parse: ParseFn
    kind: str = "html"  # "html" (decoded text) or "pdf" (raw bytes)
