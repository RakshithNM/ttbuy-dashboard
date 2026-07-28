from dataclasses import dataclass
from typing import Any, Callable, List, Optional

# parse(content, source_url) -> {Rate_Date, Published_At, TT_Buy, Raw_Data_Row} | None
# content is decoded HTML text for kind="html", raw bytes for kind="pdf".
ParseFn = Callable[[Any, str], Optional[dict]]


@dataclass
class BankPlugin:
    name: str
    slug: str
    live_url: str
    wayback_urls: List[str]
    parse: ParseFn
    kind: str = "html"  # "html" or "pdf" — selects how content is fetched
