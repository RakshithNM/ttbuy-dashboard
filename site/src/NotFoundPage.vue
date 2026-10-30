<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useHead } from "@unhead/vue";
import { brandColor, isBenchmark, isPlatform, shortName } from "./bankPalette";
import { BANK_PAGES, bankPagePath } from "./bankPages";
import { currencySymbol, sortByCurrencyOrder } from "./currencies";
import type { RatesByCurrency } from "./types";
import rawRatesData from "../public/data/rates.json";

const rates = rawRatesData as unknown as RatesByCurrency;

// Prerendered as dist/404.html, which Cloudflare Pages serves with a 404
// status for any path it has no file for. The canonical and the FAQ JSON-LD
// from index.html are stripped for this page in vite.config.ts.
useHead({
  title: "Page not found | TTBuy Rates",
  meta: [
    { name: "robots", content: "noindex" },
    { name: "description", content: "There is no page at this address on TTBuy Rates." },
  ],
});

// The prerender runs at /404, so the real address is only known in the
// browser. Filled in after mount so hydration matches the prerendered HTML.
const path = ref<string | null>(null);
onMounted(() => {
  path.value = decodeURIComponent(window.location.pathname);
});

// "/sbi", "/bank/hdfc", "/icici-rate" → that bank's page.
const suggestion = computed(() => {
  if (!path.value) return null;
  const tokens = path.value.toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);
  if (tokens.includes("about")) return { href: "/about", label: "About TTBuy Rates" };
  const bank = BANK_PAGES.find((b) => tokens.includes(b.slug));
  return bank ? { href: bankPagePath(bank.slug), label: `${shortName(bank.name)} TT Buy rate` } : null;
});

// Best bank per currency on the newest date that currency has data for.
interface BestToday { code: string; bank: string; color: string; ttbuy: number }

const bestToday = computed<BestToday[]>(() =>
  sortByCurrencyOrder(Object.keys(rates)).flatMap((code) => {
    const banks = Object.entries(rates[code]).filter(([n]) => !isPlatform(n) && !isBenchmark(n));
    const latest = banks.reduce((d, [, pts]) => {
      const last = pts.at(-1)?.date ?? "";
      return last > d ? last : d;
    }, "");
    let best: BestToday | null = null;
    for (const [name, pts] of banks) {
      const pt = pts.at(-1);
      if (pt?.date === latest && (!best || pt.ttbuy > best.ttbuy)) {
        best = { code, bank: name, color: brandColor(name), ttbuy: pt.ttbuy };
      }
    }
    return best ? [best] : [];
  })
);

// "$ USD", but just "AED" where the symbol is the code itself.
function currencyLabel(code: string): string {
  const sym = currencySymbol(code).trim();
  return sym === code ? code : `${sym} ${code}`;
}

// Sparkline: the best USD rate over the last 30 days with data, then the
// line falls off the chart to where this page should have been.
const W = 320, H = 132, FLAT_END = 228, TOP = 20, BAND = 46;

const chart = computed(() => {
  const byDate = new Map<string, number>();
  for (const [name, pts] of Object.entries(rates.USD ?? {})) {
    if (isPlatform(name) || isBenchmark(name)) continue;
    for (const p of pts) byDate.set(p.date, Math.max(byDate.get(p.date) ?? 0, p.ttbuy));
  }
  const values = [...byDate.entries()].sort(([a], [b]) => a.localeCompare(b)).slice(-30).map(([, v]) => v);
  if (values.length < 2) return null;
  const lo = Math.min(...values), hi = Math.max(...values);
  const span = hi - lo || 1;
  const pts = values.map((v, i) => [
    (i / (values.length - 1)) * FLAT_END,
    TOP + (1 - (v - lo) / span) * BAND,
  ]);
  const line = pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join("");
  const [ex, ey] = pts.at(-1)!;
  // A short ledge, then a steep curve down to the floor.
  const fall = `M${ex.toFixed(1)},${ey.toFixed(1)} C${ex + 34},${ey} ${ex + 40},${H - 14} ${W - 20},${H - 14}`;
  return { line, fall, ex, ey, last: values.at(-1)! };
});
</script>

<template>
  <header class="page-header">
    <p class="eyebrow"><a href="/" class="eyebrow-link">All banks</a> / Not found</p>
    <h1>This transfer never arrived.</h1>
    <p class="lede">
      There is no page at this address. The link may be old, or part of it may be missing.
      Nothing else is lost: today's rates are one click away.
    </p>
    <div class="actions">
      <a v-if="suggestion" :href="suggestion.href" class="btn btn--primary">
        Did you mean {{ suggestion.label }}?
        <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M6 4l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </a>
      <a href="/" class="btn" :class="suggestion ? 'btn--ghost' : 'btn--primary'">
        See today's best rates
        <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M6 4l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
      </a>
      <a href="/about" class="btn btn--ghost">How this site works</a>
    </div>
  </header>

  <main>
    <section class="slip" aria-label="Remittance advice for this page">
      <div class="slip-head">
        <span class="slip-title">Inward remittance advice</span>
        <span class="slip-status"><span class="slip-status-dot" aria-hidden="true"></span>Not credited</span>
      </div>

      <div class="slip-body">
        <dl class="slip-fields">
          <div class="field field--wide">
            <dt>Beneficiary address</dt>
            <dd class="mono ref">
              <span v-if="path">{{ path }}</span>
              <span v-else class="ref-placeholder">this page</span>
            </dd>
          </div>
          <div class="field">
            <dt>Status</dt>
            <dd>Returned to sender</dd>
          </div>
          <div class="field">
            <dt>Reason code</dt>
            <dd><span class="mono">AC01</span> · Incorrect account</dd>
          </div>
          <div class="field">
            <dt>HTTP status</dt>
            <dd class="mono">404</dd>
          </div>
          <div class="field">
            <dt>Amount credited</dt>
            <dd class="amount">₹0.00</dd>
          </div>
        </dl>

        <figure v-if="chart" class="slip-chart">
          <svg :viewBox="`0 0 ${W} ${H}`" role="img" aria-label="The best USD rate over the last 30 days, then a line that falls to zero where this page should be">
            <line v-for="g in 4" :key="g" class="grid" x1="0" :x2="W" :y1="TOP - 6 + (g - 1) * 32" :y2="TOP - 6 + (g - 1) * 32" />
            <line class="floor" x1="0" :x2="W" :y1="H - 14" :y2="H - 14" />
            <path class="rate-line" :d="chart.line" pathLength="1" />
            <path class="fall-line" :d="chart.fall" />
            <circle class="pin" :cx="chart.ex" :cy="chart.ey" r="3.5" />
            <g class="lost">
              <circle class="lost-ring" :cx="W - 20" :cy="H - 14" r="9" />
              <circle class="lost-dot" :cx="W - 20" :cy="H - 14" r="4" />
            </g>
          </svg>
          <figcaption>
            <span><span class="key key--rate" aria-hidden="true"></span>Best USD rate, 30 days · ₹{{ chart.last.toFixed(2) }}</span>
            <span><span class="key key--lost" aria-hidden="true"></span>This page · ₹0</span>
          </figcaption>
        </figure>
      </div>
    </section>

    <section class="panel">
      <h2>Where your money is better spent</h2>
      <p class="panel-sub">The best published TT Buy rate today, per currency</p>
      <ul class="best-grid">
        <li v-for="b in bestToday" :key="b.code">
          <a :href="`/?currency=${b.code}`" class="best-tile">
            <span class="best-code">{{ currencyLabel(b.code) }}</span>
            <span class="best-rate">₹{{ b.ttbuy.toFixed(2) }}</span>
            <span class="best-bank"><span class="dot" :style="{ background: b.color }" aria-hidden="true"></span>{{ shortName(b.bank) }}</span>
          </a>
        </li>
      </ul>
    </section>
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
  margin-bottom: 28px;

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
    text-wrap: balance;
  }
  .lede {
    color: var(--text-secondary);
    max-width: 600px;
    line-height: 1.5;
    margin: 0;
  }
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 20px;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  transition: background 0.15s, border-color 0.15s, color 0.15s;

  svg { transition: transform 0.15s; }
  &:hover svg { transform: translateX(2px); }
  &:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

  // Same filled blue as the active currency button on the dashboard.
  &--primary {
    background: color-mix(in srgb, var(--accent), #000 18%);
    border-color: color-mix(in srgb, var(--accent), #000 18%);
    color: #fff;
    &:hover { background: color-mix(in srgb, var(--accent), #000 28%); }
  }
  &--ghost {
    color: var(--text-secondary);
    background: var(--surface-1);
    &:hover { color: var(--text-primary); border-color: color-mix(in srgb, var(--text-primary) 25%, transparent); }
  }
}

// The advice slip: a hero-style card with a perforated tear line under its
// header, made of two notches cut into the edges plus a dashed rule.
.slip {
  position: relative;
  margin-bottom: 24px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface-1);
}

.slip-head {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 16px 20px 18px;
  border-bottom: 1px dashed var(--baseline);

  &::before,
  &::after {
    content: "";
    position: absolute;
    bottom: -9px;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: var(--page-plane);
    border: 1px solid var(--border);
  }
  &::before { left: -9px; clip-path: inset(0 0 0 50%); }
  &::after { right: -9px; clip-path: inset(0 50% 0 0); }
}

.slip-title {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-secondary);
}

.slip-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  color: var(--status-critical);
  background: color-mix(in srgb, var(--status-critical) 12%, transparent);
}

.slip-status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.slip-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr);
  gap: 24px 40px;
  align-items: center;
  padding: 20px;

  @media (max-width: 720px) {
    grid-template-columns: minmax(0, 1fr);
  }
  @media (max-width: 480px) {
    padding: 16px 14px;
  }
}

.slip-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px 24px;
  margin: 0;
}

.field {
  min-width: 0;
  &--wide { grid-column: 1 / -1; }

  dt {
    font-size: 12px;
    color: var(--text-muted);
    margin-bottom: 3px;
  }
  dd {
    margin: 0;
    font-size: 15px;
    font-weight: 500;
    color: var(--text-primary);
  }
}

.mono {
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  font-size: 0.94em;
}

.ref {
  overflow-wrap: anywhere;
  padding: 6px 10px;
  border-radius: 6px;
  background: var(--page-plane);
  border: 1px solid var(--border);
}

.ref-placeholder { color: var(--text-muted); }

.amount {
  font-size: 28px !important;
  font-weight: 700 !important;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
  color: var(--status-critical) !important;
}

.slip-chart {
  margin: 0;

  svg {
    display: block;
    width: 100%;
    height: auto;
    overflow: visible;
  }

  figcaption {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 16px;
    margin-top: 10px;
    font-size: 12px;
    color: var(--text-muted);
    font-variant-numeric: tabular-nums;

    > span { display: inline-flex; align-items: center; gap: 6px; }
  }
}

.grid { stroke: var(--gridline); stroke-width: 1; }
.floor { stroke: var(--baseline); stroke-width: 1; }

.rate-line {
  fill: none;
  stroke: var(--accent);
  stroke-width: 2;
  stroke-linejoin: round;
  stroke-linecap: round;
}

.fall-line {
  fill: none;
  stroke: var(--status-critical);
  stroke-width: 2;
  stroke-dasharray: 4 5;
  stroke-linecap: round;
}

.pin { fill: var(--surface-1); stroke: var(--accent); stroke-width: 2; }
.lost-dot { fill: var(--status-critical); }
.lost-ring { fill: none; stroke: var(--status-critical); stroke-width: 1.5; opacity: 0.35; transform-box: fill-box; transform-origin: center; }

.key {
  width: 14px;
  height: 0;
  border-top: 2px solid var(--accent);
  &--lost { border-top: 2px dashed var(--status-critical); }
}

// Draw the rate line, let the fall appear after it, then pulse where the
// page should be. Static for reduced motion.
@media (prefers-reduced-motion: no-preference) {
  .rate-line {
    stroke-dasharray: 1;
    stroke-dashoffset: 1;
    animation: draw 1.1s cubic-bezier(0.4, 0, 0.2, 1) 0.15s forwards;
  }
  .fall-line {
    opacity: 0;
    animation: fade-in 0.35s ease 1.2s forwards, march 1.2s linear 1.2s infinite;
  }
  .lost, .pin {
    opacity: 0;
    animation: fade-in 0.3s ease forwards;
  }
  .pin { animation-delay: 1.15s; }
  .lost { animation-delay: 1.5s; }
  .lost-ring { animation: pulse 2s ease-out 1.8s infinite; }
}

@keyframes draw { to { stroke-dashoffset: 0; } }
@keyframes fade-in { to { opacity: 1; } }
@keyframes march { to { stroke-dashoffset: -18; } }
@keyframes pulse {
  0% { transform: scale(0.6); opacity: 0.6; }
  100% { transform: scale(1.8); opacity: 0; }
}

.panel {
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;

  h2 { font-size: 18px; margin: 0 0 4px; }

  @media (max-width: 480px) { padding: 14px; }
}

.panel-sub {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0 0 16px;
}

.best-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;

  @media (max-width: 720px) { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

.best-tile {
  display: flex;
  flex-direction: column;
  gap: 4px;
  height: 100%;
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--page-plane);
  color: inherit;
  text-decoration: none;
  transition: border-color 0.15s, transform 0.15s;

  &:hover { border-color: color-mix(in srgb, var(--accent) 55%, transparent); }
  &:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  @media (prefers-reduced-motion: no-preference) {
    &:hover { transform: translateY(-2px); }
  }
}

.best-code {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  letter-spacing: 0.04em;
}

.best-rate {
  font-size: 22px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--text-primary);
}

.best-bank {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);

  .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
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
