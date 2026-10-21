#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

BANKS="${BANKS:-axis,iob,bob,canara,icici,sbi,hdfc,kotak,idbi,bandhan,cityunion,hsbc,jkbank,kvb,citibank,ujjivan,dcb,idfcfirst,dbs,pnb,rbl,unionbank,skydo,remitly}"

BANKS="$BANKS" \
MAX_SNAPSHOTS=0 \
INCLUDE_LIVE=1 \
.venv/bin/python3 -m scraper.main

.venv/bin/python3 -m scraper.benchmarks
.venv/bin/python3 -m scraper.export_json
cp data/rates.json site/public/data/rates.json
cp data/benchmarks.json site/public/data/benchmarks.json
