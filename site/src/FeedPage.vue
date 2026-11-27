<script setup lang="ts">
import { useHead } from "@unhead/vue";
import { shortName } from "./bankPalette";
import { BANK_PAGES, SITE_URL, bankPagePath } from "./bankPages";
import { feedDays, fmtChange, fmtFeedDate } from "./feed";
import type { RatesByCurrency } from "./types";
import rawRatesData from "../public/data/rates.json";

// The readable twin of /feed.xml: the same daily entries, as a normal page
// that works in every browser (Chrome no longer runs the feed's XSLT).
const days = feedDays(rawRatesData as unknown as RatesByCurrency);
const FEED_URL = `${SITE_URL}/feed.xml`;

const url = `${SITE_URL}/feed`;
const title = "Daily best TT Buy rate by Indian banks | TTBuy Rates";
const description =
  "The highest bank TT Buy rate for USD, GBP, EUR and AED each day, with the change from the previous day and the 7-day average. Also available as an Atom feed.";
useHead({
  title,
  link: [
    { rel: "canonical", href: url },
    { rel: "alternate", type: "application/atom+xml", href: "/feed.xml", title: "TTBuy Rates: daily best rate" },
  ],
  meta: [
    { name: "description", content: description },
    { property: "og:title", content: title },
    { property: "og:description", content: description },
    { property: "og:url", content: url },
    { name: "twitter:title", content: title },
    { name: "twitter:description", content: description },
  ],
});
</script>

<template>
  <header class="page-header">
    <p class="eyebrow"><a href="/" class="eyebrow-link">All banks</a> / Daily rates</p>
    <h1>Daily best TT Buy rate</h1>
    <p class="lede">
      The bank with the highest TT Buy rate for each currency, every day, for the last
      {{ days.length }} days with data. Rankings by the rupees you receive after fees are on the
      <a href="/">main page</a>.
    </p>
  </header>

  <main>
    <section class="panel howto">
      <p>
        <strong>Follow in a feed reader.</strong> Copy this address into Feedly, Inoreader,
        NetNewsWire or any other feed reader: <code>{{ FEED_URL }}</code>
      </p>
      <p>A day is listed only when most banks published a rate that day.</p>
    </section>

    <article v-for="day in days" :id="`d-${day.date}`" :key="day.date" class="panel day">
      <h2><a :href="`#d-${day.date}`">{{ fmtFeedDate(day.date) }}</a></h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">Currency</th>
              <th scope="col">Best bank</th>
              <th scope="col" class="num">TT Buy</th>
              <th scope="col" class="num">vs previous day</th>
              <th scope="col" class="num">vs 7-day avg</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="l in day.lines" :key="l.code">
              <th scope="row">{{ l.code }}</th>
              <td>{{ l.bank }}</td>
              <td class="num">₹{{ l.ttbuy.toFixed(2) }}</td>
              <td class="num" :class="l.prev ? (l.prev.change >= 0 ? 'up' : 'down') : 'muted'">
                {{ l.prev ? fmtChange(l.prev.change) : "—" }}
              </td>
              <td class="num" :class="l.avg ? (l.avg.change >= 0 ? 'up' : 'down') : 'muted'">
                {{ l.avg ? fmtChange(l.avg.change) : "—" }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </article>
  </main>

  <footer class="site-footer">
    <nav class="footer-banks" aria-label="Bank pages">
      <a href="/">All banks</a>
      <template v-for="b in BANK_PAGES" :key="b.slug">
        <span class="footer-sep" aria-hidden="true">·</span>
        <a :href="bankPagePath(b.slug)">{{ shortName(b.name) }} TT Buy rate</a>
      </template>
      <span class="footer-sep" aria-hidden="true">·</span>
      <a href="/about">About</a>
    </nav>
  </footer>
</template>

<style scoped lang="scss">
.page-header {
  margin-bottom: 24px;

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
  margin-bottom: 16px;

  p {
    font-size: 14px;
    color: var(--text-secondary);
    line-height: 1.6;
    margin: 0 0 8px;
  }
  p:last-child { margin-bottom: 0; }
  strong { color: var(--text-primary); font-weight: 500; }

  @media (max-width: 480px) {
    padding: 14px;
  }
}

.howto code {
  font-size: 13px;
  padding: 1px 6px;
  border-radius: 6px;
  background: var(--page-plane);
  border: 1px solid var(--border);
  // Inline-block moves the whole URL to its own line when it doesn't fit;
  // overflow-wrap only splits it on screens narrower than the URL itself.
  display: inline-block;
  overflow-wrap: anywhere;
}

.day {
  scroll-margin-top: 16px;

  h2 {
    font-size: 16px;
    margin: 0;
    a {
      color: var(--text-primary);
      text-decoration: none;
      &:hover { text-decoration: underline; }
    }
  }
}

.table-wrap {
  overflow-x: auto;
  margin-top: 8px;
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
  tbody tr:last-child > * { border-bottom: none; }
  thead th {
    color: var(--text-muted);
    font-weight: 500;
  }
  tbody th { font-weight: 600; }
  td { color: var(--text-primary); }
  .num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
  .up { color: var(--success-text); }
  .down { color: var(--status-critical); }
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
