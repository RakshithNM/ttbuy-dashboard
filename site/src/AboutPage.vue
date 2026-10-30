<script setup lang="ts">
import { computed } from "vue";
import { useHead } from "@unhead/vue";
import { SOURCE_URLS, isPlatform, shortName, sortByBankOrder } from "./bankPalette";
import { BANK_PAGES, SITE_URL, bankPagePath } from "./bankPages";
import { sortByCurrencyOrder } from "./currencies";
import type { FeesByBank, RatesByCurrency } from "./types";
import rawRatesData from "../public/data/rates.json";
import feesData from "../public/data/fees.json";

const rates = rawRatesData as unknown as RatesByCurrency;
const fees = feesData as unknown as FeesByBank;

const REPO_URL = "https://github.com/RakshithNM/ttbuy-dashboard";

const url = `${SITE_URL}/about`;
const title = "About TTBuy Rates: how the rates are collected and ranked";
const description =
  "Who runs TTBuy Rates, where each bank's TT Buy rate comes from, when it is collected, how banks are ranked after fees, and what the data cannot tell you.";
useHead({
  title,
  link: [{ rel: "canonical", href: url }],
  meta: [
    { name: "description", content: description },
    { property: "og:title", content: title },
    { property: "og:description", content: description },
    { property: "og:url", content: url },
    { name: "twitter:title", content: title },
    { name: "twitter:description", content: description },
  ],
});

function fmtLongDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  const MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];
  return `${MONTHS[m - 1]} ${d}, ${y}`;
}

// One row per tracked source: where its rate is read from, where its fee
// schedule is, and the newest date we have a rate for (any currency).
interface SourceRow { name: string; rateUrl: string; feeUrl: string | null; latest: string | null }

const sources = computed<SourceRow[]>(() =>
  sortByBankOrder(Object.keys(SOURCE_URLS)).map((name) => {
    let latest: string | null = null;
    for (const byBank of Object.values(rates)) {
      const d = byBank[name]?.at(-1)?.date;
      if (d && (!latest || d > latest)) latest = d;
    }
    return { name, rateUrl: SOURCE_URLS[name], feeUrl: fees[name]?.source_url ?? null, latest };
  })
);

const bankCount = computed(() => sources.value.filter((s) => !isPlatform(s.name)).length);
const currencies = sortByCurrencyOrder(Object.keys(rates));

const firstDate = computed(() => {
  let first = "";
  for (const byBank of Object.values(rates))
    for (const points of Object.values(byBank)) {
      const d = points[0]?.date;
      if (d && (!first || d < first)) first = d;
    }
  return first;
});
</script>

<template>
  <header class="page-header">
    <p class="eyebrow"><a href="/" class="eyebrow-link">All banks</a> / About</p>
    <h1>About TTBuy Rates</h1>
    <p class="lede">
      When someone abroad sends you money, your bank converts it to rupees at its own TT Buy
      rate. Each bank publishes only its own rate, on its own page, with no history. This site
      collects those rates from {{ bankCount }} Indian banks every day and puts them side by side,
      so you can see which bank pays you the most, today and over time.
    </p>
  </header>

  <main>
    <section class="panel">
      <h2>Who runs this site</h2>
      <p>
        TTBuy Rates is built and maintained by
        <a href="https://rakshithnettar.com" target="_blank" rel="noopener noreferrer">Rakshith Nettar</a>,
        an independent software developer. It is a personal project. It is not affiliated with,
        endorsed by, or paid by any bank or remittance service.
      </p>
      <p>
        The code that collects and ranks the rates is open source on
        <a :href="REPO_URL" target="_blank" rel="noopener noreferrer">GitHub</a>.
        To report a wrong rate or ask for a bank to be added,
        <a :href="`${REPO_URL}/issues`" target="_blank" rel="noopener noreferrer">open an issue</a>.
      </p>
    </section>

    <section class="panel">
      <h2>How the rates are collected</h2>
      <ul>
        <li>
          An automated scraper reads each bank's public forex rate page or rate-card PDF every
          day at 11:00 AM IST. A second run at 4:00 PM IST retries banks that had not published
          by the morning.
        </li>
        <li>
          It records the TT Buy rate for {{ currencies.join(", ") }}. This is the rate a bank uses
          when foreign currency arrives in your account by wire transfer.
        </li>
        <li>
          Rates are the standard retail rates that any customer sees on the bank's website.
          Negotiated, corporate and premium-segment rates are not published, so they are not
          included.
        </li>
        <li>
          Banks do not publish on Sundays, bank holidays, or the 2nd and 4th Saturdays. On those
          days the site shows the last published rate and marks it with its date.
        </li>
        <li>The history goes back to {{ fmtLongDate(firstDate) }}.</li>
      </ul>
    </section>

    <section class="panel">
      <h2>How banks are ranked</h2>
      <ul>
        <li>
          Banks are ranked by the rupees you receive, not by the raw rate. For each bank, we
          multiply your amount by its TT Buy rate and subtract its inward remittance fee.
        </li>
        <li>
          Fees come from each bank's published schedule of charges, which we check once a month.
          Where a bank charges by slab, the fee for your amount is used. Where we could not find a
          published fee, the bank is marked "≈" and its figure is before fees.
        </li>
        <li>
          Skydo and Remitly are shown for comparison, but they are not banks and are not in the
          bank rankings.
        </li>
      </ul>
    </section>

    <section class="panel">
      <h2>Benchmarks</h2>
      <p>
        Two reference rates show how far each bank's rate is from the wholesale price. Nobody can
        transact at either one; they are a yardstick only.
      </p>
      <ul>
        <li>
          <strong>Mid-market rate</strong> for USD, GBP and EUR, from the
          <a href="https://frankfurter.app/" target="_blank" rel="noopener noreferrer">Frankfurter API</a>,
          which uses European Central Bank reference rates.
        </li>
        <li>
          <strong>FBIL reference rate</strong> for all four currencies, from
          <a href="https://www.fbil.org.in/" target="_blank" rel="noopener noreferrer">Financial Benchmarks India Ltd</a>,
          the RBI-recognised benchmark administrator.
        </li>
      </ul>
    </section>

    <section class="panel">
      <h2>What this data cannot tell you</h2>
      <ul>
        <li>Banks can change their rate during the day. The rate on the day of your transfer can differ from the one shown here.</li>
        <li>The sending bank and intermediary banks can deduct their own charges before the money reaches India.</li>
        <li>A scraper can fail when a bank changes its website. Each rate shows its date, so an old rate is visible.</li>
        <li>This site gives information, not financial advice. Confirm the rate with your bank before a large transfer.</li>
      </ul>
    </section>

    <section class="panel">
      <h2>Sources</h2>
      <p>Every rate on this site comes from one of these public pages.</p>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>Bank</th><th>Rate source</th><th>Fee schedule</th><th>Latest rate</th></tr>
          </thead>
          <tbody>
            <tr v-for="s in sources" :key="s.name">
              <td>{{ s.name }}</td>
              <td><a :href="s.rateUrl" target="_blank" rel="noopener noreferrer">Rate page</a></td>
              <td>
                <a v-if="s.feeUrl" :href="s.feeUrl" target="_blank" rel="noopener noreferrer">Fee schedule</a>
                <span v-else class="muted">{{ isPlatform(s.name) ? "—" : "Not published" }}</span>
              </td>
              <td>{{ s.latest ? fmtLongDate(s.latest) : "—" }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </main>

  <footer class="site-footer">
    <nav class="footer-banks" aria-label="Bank pages">
      <a href="/">All banks</a>
      <template v-for="b in BANK_PAGES" :key="b.slug">
        <span class="footer-sep" aria-hidden="true">·</span>
        <a :href="bankPagePath(b.slug)">{{ shortName(b.name) }} TT Buy rate</a>
      </template>
    </nav>
  </footer>
</template>

<style scoped lang="scss">
.page-header {
  margin-bottom: 32px;

  .eyebrow {
    color: var(--text-secondary);
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin: 0 0 6px;
  }
  .eyebrow-link {
    color: inherit;
    &:hover { color: var(--text-primary); }
  }

  h1 {
    font-size: 32px;
    margin: 0 0 12px;
  }

  .lede {
    color: var(--text-secondary);
    max-width: 640px;
    line-height: 1.5;
    margin: 0;
  }
}

.panel {
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;

  h2 {
    font-size: 18px;
    margin: 0 0 12px;
  }

  p, li {
    font-size: 14px;
    color: var(--text-secondary);
    line-height: 1.6;
    max-width: 680px;
  }

  p { margin: 0 0 10px; }
  p:last-child { margin-bottom: 0; }

  ul {
    margin: 0;
    padding-left: 20px;
  }
  li + li { margin-top: 6px; }

  strong { color: var(--text-primary); font-weight: 500; }

  @media (max-width: 480px) {
    padding: 14px;
  }
}

.table-wrap {
  overflow-x: auto;
  margin-top: 12px;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;

  th, td {
    text-align: left;
    padding: 8px 12px 8px 0;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }
  th {
    color: var(--text-muted);
    font-weight: 500;
  }
  td { color: var(--text-primary); }
  .muted { color: var(--text-muted); }
}

.site-footer {
  padding: 24px 0 32px;
  font-size: 13px;
  color: var(--text-secondary);

  .footer-banks {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .footer-sep { color: var(--text-muted); }
}
</style>
