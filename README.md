# TTBuy Dashboard

Tracks the USD TT Buy (inward remittance) rate across Indian banks and shows the
history on a small Vite + Vue + TypeScript site.

## Layout

- `scraper/` — Python package. Each bank is a plugin in `scraper/banks/` (a
  `live_url`, optional `wayback_urls` for historical backfill, a `parse(content,
  source_url)` function, and a `kind`: `"html"` (default, decoded text),
  `"pdf"` (raw bytes, parsed with pdfplumber), `"browser"` (Playwright-
  rendered HTML, for pages whose rate table is populated by client-side JS),
  or `"pdf_discover"` (for a rate PDF whose filename rotates — `live_url` is a
  stable landing page, and `resolve_url(html)` extracts the current PDF link
  from it before fetching). `scraper/pipeline.py` handles fetching, Wayback
  Machine backfill, and CSV I/O; `scraper/main.py` is the CLI entrypoint.
- `data/` — per-bank CSV/MD outputs, a combined `forex_TTBuy.csv`/`.md`, and the
  `rates.json` the site consumes.
- `site/` — the dashboard (Vite + Vue 3 + TypeScript + SCSS).
- `.github/workflows/scrape.yml` — daily cron that re-scrapes live rates,
  regenerates `rates.json`, and commits the update (Netlify auto-deploys on push
  once connected to this repo).
- `netlify.toml` — base `site/`, publishes `dist/`.

## Running the scraper

```bash
cd ttbuy-dashboard
python3 -m venv .venv && .venv/bin/pip install -r scraper/requirements.txt

# env vars: BANKS (comma-separated slugs), START_DATE/END_DATE (Wayback range,
# YYYYMMDD), MAX_SNAPSHOTS (0 = skip Wayback backfill, live rate only), INCLUDE_LIVE
# Kotak/DCB/IDFC FIRST/DBS need a browser once: .venv/bin/playwright install chromium
BANKS=axis,iob,bob,canara,icici,sbi,hdfc,kotak,idbi,bandhan,cityunion,hsbc,jkbank,kvb,citibank,ujjivan,dcb,idfcfirst,dbs \
  MAX_SNAPSHOTS=0 .venv/bin/python3 -m scraper.main
.venv/bin/python3 -m scraper.export_json
cp data/rates.json site/public/data/rates.json
```

## Running the site

```bash
cd site
npm install
npm run dev
```

## Banks

19 banks scraped:

| Bank | Status |
|---|---|
| Axis Bank, IOB, Bank of Baroda, Canara Bank, ICICI Bank, IDBI Bank, Bandhan Bank, City Union Bank, HSBC | Scraped — plain HTML |
| SBI, HDFC Bank, Jammu & Kashmir Bank, Karur Vysya Bank, Citibank | Scraped — daily PDF, parsed with pdfplumber |
| Ujjivan Small Finance Bank | Scraped — PDF filename rotates behind an opaque hash; a stable landing page (`/forex-rates`) always links to the current one, so this is a two-step fetch (`kind="pdf_discover"`) |
| Kotak Mahindra Bank, DCB Bank, IDFC FIRST Bank, DBS Bank India | Scraped — rates load via client-side JS, rendered with Playwright. No Wayback backfill (archived HTML wouldn't contain the rendered data), so history only starts accumulating from whenever the daily cron first ran. |
| PNB, Central Bank of India, Bank of Maharashtra | Rate is on a PDF whose URL/filename changes daily behind an opaque token or dated path, with no stable landing page found linking to it during research — needs a human to click through the site and find the current link |
| Karnataka Bank | PDF-only; the landing page also has a hidden decoy HTML table with fake data — do not scrape that table if this gets implemented |
| Union Bank of India | PDF is image-based (no extractable text) — would need OCR |
| Federal Bank, Indian Bank, Dhanlaxmi Bank, Tamilnad Mercantile Bank | PDF-only or no accessible rate page found |
| South Indian Bank, Bank of India, Equitas Small Finance Bank, ESAF Small Finance Bank | Blocked by Cloudflare/Akamai bot-challenge on plain HTTP GET |
| IndusInd Bank, RBL Bank | JS/AJAX-rendered; IndusInd's widget doesn't appear to expose a public rate without a booking flow, RBL calls an internal `/fxadmin_getfx` endpoint that's undocumented and might be worth trying directly |
| AU Small Finance Bank | JS-rendered widget returns "Authentication failed" without a browser session/token we don't have |
| CSB Bank | Rate page is an image (JPG), no extractable text — would need OCR |
| UCO Bank | Rate is an Excel (.xlsx) download, not HTML/PDF |
| Nainital Bank, Jana Small Finance Bank | No retail forex/NRI presence found |
| Utkarsh Small Finance Bank | Only stale, outward-remittance-only PDFs found — no current inward TT Buy rate |
| Standard Chartered India | PDF exists but TT and Bills rates are merged into one ambiguous column — can't isolate TT Buy reliably |
| Yes Bank, Punjab & Sind Bank | Unresolved — site access was inconclusive during research (mid-domain-migration / DNS failure respectively); worth a retry |
