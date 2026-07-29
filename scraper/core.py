import gzip
import os
import re
import time
from datetime import datetime

import requests

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    ),
    "Connection": "close",
    "Accept-Encoding": "gzip, deflate",
}
REQUEST_DELAY_SECONDS = float(os.environ.get("WAYBACK_DELAY_SECONDS", "5"))


def normalize_date(value):
    if not value:
        return None

    value = re.sub(r",\s*", ",", str(value).strip())
    for date_format in (
        "%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%b %d,%Y", "%B %d,%Y", "%d/%b/%y", "%d-%b-%y",
        "%d %B %Y", "%d %b %Y", "%d-%m-%y", "%d-%B-%Y",
    ):
        try:
            return datetime.strptime(value, date_format).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return str(value).strip()


def get_with_retries(url, attempts=5, backoff=10, **kwargs):
    last_error = None
    headers = DEFAULT_HEADERS | kwargs.pop("headers", {})

    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(url, headers=headers, **kwargs)
            if response.status_code not in {429, 500, 502, 503, 504}:
                return response
            last_error = requests.HTTPError(f"{response.status_code} response from {url}")
        except requests.RequestException as e:
            last_error = e

        if attempt < attempts:
            sleep_for = min(backoff * attempt, 60)
            print(f"Retrying {url} in {sleep_for}s ({attempt}/{attempts})...")
            time.sleep(sleep_for)

    raise last_error


def fetch_html(url, is_wayback=False):
    """Fetch a URL and return decoded HTML text.

    Wayback snapshot URLs need the 'id_' infix to get the raw archived HTML
    without the replay toolbar injected; some archived responses are gzip
    even though requests already decompressed the transport encoding.
    """
    fetch_url = url.replace("/http", "id_/http") if is_wayback else url
    res = get_with_retries(fetch_url, timeout=20)

    content = res.content
    if content[:2] == b"\x1f\x8b":
        content = gzip.decompress(content)

    return content.decode(res.encoding or "utf-8", errors="replace")


def fetch_bytes(url, is_wayback=False):
    """Fetch a URL and return raw bytes, decompressing gzip if needed (some
    archived responses are gzip even though requests already handled
    transport-level Content-Encoding)."""
    fetch_url = url.replace("/http", "id_/http") if is_wayback else url
    res = get_with_retries(fetch_url, timeout=20)

    content = res.content
    if content[:2] == b"\x1f\x8b":
        content = gzip.decompress(content)
    return content


def fetch_rendered_html(url, timeout_ms=30000, settle_ms=2000):
    """Fetch a URL with a headless browser and return the fully rendered HTML.

    Only for banks whose rate page has no data in the raw HTTP response (the
    rate table is populated by client-side JS/AJAX after load). Playwright is
    imported lazily so it stays an optional dependency for everyone else.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(user_agent=DEFAULT_HEADERS["User-Agent"])
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            page.wait_for_timeout(settle_ms)
            html = page.content()
        finally:
            browser.close()
    return html


def get_wayback_snapshots(target_url, start_date, end_date):
    """Retrieves historical snapshot URLs from the Wayback Machine CDX API.

    Dates are formatted as YYYYMMDD.
    """
    cdx_url = "https://web.archive.org/cdx/search/cdx"
    params = {
        "url": target_url,
        "output": "json",
        "from": start_date,
        "to": end_date,
        "fl": "timestamp,original",
        "collapse": "timestamp:8",  # one snapshot per day
    }

    response = get_with_retries(cdx_url, params=params, timeout=20)
    if response.status_code == 200:
        data = response.json()
        if len(data) > 1:
            return data[1:]  # skip header row
    return []
