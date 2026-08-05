<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import LineChart from "./components/LineChart.vue";
import BestRateTable from "./components/BestRateTable.vue";
import { brandColor, isPlatform, shortName, sortByBankOrder } from "./bankPalette";
import { currencyName, sortByCurrencyOrder } from "./currencies";
import type { BankSeries, FeesByBank, RatesByCurrency } from "./types";

const rawRates = ref<RatesByCurrency>({});
const fees = ref<FeesByBank>({});
const loading = ref(true);
const loadError = ref<string | null>(null);
const hidden = ref<Set<string>>(new Set());
const bankQuery = ref("");

type RangeKey = "7d" | "30d" | "90d" | "1y" | "all";
const RANGE_OPTIONS: { key: RangeKey; label: string; days: number | null }[] = [
  { key: "7d", label: "Last 7 days", days: 7 },
  { key: "30d", label: "Last 30 days", days: 30 },
  { key: "90d", label: "Last 90 days", days: 90 },
  { key: "1y", label: "Last 1 year", days: 365 },
  { key: "all", label: "All time", days: null },
];

// Remember the date range and table/chart toggle across visits. localStorage
// can throw (private browsing, disabled storage) — this is a nice-to-have,
// never worth breaking the page over, so every access is best-effort.
const VIEW_STORAGE_KEY = "ttbuy-dashboard:view";
const THEME_STORAGE_KEY = "ttbuy-dashboard:theme";

// Apply stored theme before first paint so there's no flash of wrong theme.
const _storedTheme = (() => {
  try { return localStorage.getItem(THEME_STORAGE_KEY) as "light" | "dark" | null; } catch { return null; }
})();
if (_storedTheme) document.documentElement.setAttribute("data-theme", _storedTheme);
const isDark = ref(
  _storedTheme !== null
    ? _storedTheme === "dark"
    : window.matchMedia("(prefers-color-scheme: dark)").matches
);
function toggleTheme() {
  isDark.value = !isDark.value;
  const t = isDark.value ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", t);
  try { localStorage.setItem(THEME_STORAGE_KEY, t); } catch {}
}

interface StoredView {
  range?: RangeKey;
  showTable?: boolean;
  currency?: string;
  amount?: number;
}

function loadStoredView(): StoredView {
  try {
    const raw = localStorage.getItem(VIEW_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as StoredView) : {};
  } catch {
    return {};
  }
}

// A shared link's query string wins over whatever the visitor had saved
// locally — someone opening a link expects to see the sender's view, not
// their own last one.
function loadQueryView(): StoredView {
  const params = new URLSearchParams(window.location.search);
  const view: StoredView = {};

  const range = params.get("range");
  if (range && RANGE_OPTIONS.some((o) => o.key === range)) view.range = range as RangeKey;

  const currency = params.get("currency");
  if (currency) view.currency = currency;

  const shown = params.get("view");
  if (shown === "table" || shown === "chart") view.showTable = shown === "table";

  const amount = params.get("amount");
  if (amount !== null && Number.isFinite(Number(amount)) && Number(amount) >= 0) view.amount = Number(amount);

  return view;
}

const storedView = loadStoredView();
const queryView = loadQueryView();

const range = ref<RangeKey>(
  queryView.range ??
    (storedView.range && RANGE_OPTIONS.some((o) => o.key === storedView.range) ? storedView.range : "7d")
);
const showTable = ref(
  queryView.showTable ?? (typeof storedView.showTable === "boolean" ? storedView.showTable : true)
);
const currency = ref<string>(queryView.currency ?? storedView.currency ?? "USD");
const amount = ref<number>(queryView.amount ?? storedView.amount ?? 1000);

watch([range, showTable, currency, amount], ([r, t, c, a]) => {
  document.title = `${c} TT Buy Rate | TTBuy Rates`;
  try {
    localStorage.setItem(VIEW_STORAGE_KEY, JSON.stringify({ range: r, showTable: t, currency: c, amount: a }));
  } catch {
    // Persistence is best-effort; nothing to do if storage is unavailable.
  }

  // Keep the address bar in sync so the current view is shareable just by
  // copying the URL, not only via the explicit "Copy link" button.
  const params = new URLSearchParams();
  params.set("currency", c);
  params.set("range", r);
  params.set("view", t ? "table" : "chart");
  params.set("amount", String(a));
  history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);
}, { immediate: true });

const copied = ref(false);
let copiedTimer: ReturnType<typeof setTimeout> | null = null;

async function copyShareLink() {
  try {
    await navigator.clipboard.writeText(window.location.href);
    copied.value = true;
    if (copiedTimer) clearTimeout(copiedTimer);
    copiedTimer = setTimeout(() => (copied.value = false), 1800);
  } catch {
    // Clipboard access can fail (permissions, insecure context) — the URL
    // bar already reflects the current view, so this is a convenience on
    // top of that, not the only way to share it.
  }
}

onMounted(async () => {
  try {
    const res = await fetch(`${import.meta.env.BASE_URL}data/rates.json`);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    rawRates.value = await res.json();
    if (!(currency.value in rawRates.value)) {
      currency.value = sortByCurrencyOrder(Object.keys(rawRates.value))[0] ?? "USD";
    }
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : "Failed to load rate data";
  } finally {
    loading.value = false;
  }

  // Fee data only covers a handful of banks so far and is a nice-to-have —
  // never worth failing the whole page load over.
  try {
    const res = await fetch(`${import.meta.env.BASE_URL}data/fees.json`);
    if (res.ok) fees.value = await res.json();
  } catch {
    // No fee info shown for any bank is an acceptable degraded state.
  }
});

const availableCurrencies = computed(() => sortByCurrencyOrder(Object.keys(rawRates.value)));

const bankRates = computed(() => rawRates.value[currency.value] ?? {});

const allSeries = computed<BankSeries[]>(() => {
  const banks = sortByBankOrder(Object.keys(bankRates.value));
  return banks.map((name) => ({
    name,
    color: brandColor(name),
    wrapped: false,
    points: bankRates.value[name] ?? [],
    category: isPlatform(name) ? "platform" : "bank",
  }));
});

// Matches against both the full and short bank name, so "SBI" finds
// "State Bank of India" and vice versa.
const searchedSeries = computed<BankSeries[]>(() => {
  const q = bankQuery.value.trim().toLowerCase();
  if (!q) return allSeries.value;
  return allSeries.value.filter(
    (s) => s.name.toLowerCase().includes(q) || shortName(s.name).toLowerCase().includes(q)
  );
});

const filteredSeries = computed<BankSeries[]>(() => {
  const opt = RANGE_OPTIONS.find((o) => o.key === range.value);
  if (!opt || opt.days === null) return searchedSeries.value;

  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - opt.days);
  const cutoffStr = cutoff.toISOString().slice(0, 10);

  return searchedSeries.value.map((s) => ({
    ...s,
    points: s.points.filter((p) => p.date >= cutoffStr),
  }));
});

function toggleBank(name: string) {
  const next = new Set(hidden.value);
  if (next.has(name)) next.delete(name);
  else next.add(name);
  hidden.value = next;
}

const lastUpdated = computed(() => {
  const dates = allSeries.value.flatMap((s) => s.points.map((p) => p.date));
  if (dates.length === 0) return null;
  return dates.sort().at(-1) ?? null;
});

const lastUpdatedFormatted = computed(() => {
  if (!lastUpdated.value) return null;
  const [year, month, day] = lastUpdated.value.split("-").map(Number);
  const MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];
  return `${MONTHS[month - 1]} ${day}, ${year}`;
});
</script>

<template>
  <header class="page-header">
    <p class="eyebrow">Inward remittance rates</p>
    <h1>{{ currency }} TT Buy rate by Indian banks</h1>
    <p class="lede">
      TT Buy is the rate a bank credits you at when you receive a foreign inward
      (telegraphic transfer) remittance. A higher TT Buy means more rupees for the
      same {{ currencyName(currency) }} amount. Rates below are scraped directly from
      each bank's public forex rate page.
    </p>
    <p v-if="lastUpdated" class="updated">
      Data last updated {{ lastUpdatedFormatted }}. Updated daily at 11 AM IST.
    </p>
  </header>

  <main v-if="!loading && !loadError">
    <div class="toolbar">
      <div v-if="availableCurrencies.length > 1" class="currency-filter" role="group" aria-label="Currency">
        <button
          v-for="code in availableCurrencies"
          :key="code"
          type="button"
          class="currency-btn"
          :class="{ active: currency === code }"
          :aria-pressed="currency === code"
          @click="currency = code"
        >
          {{ code }}
        </button>
      </div>
      <div class="bank-search">
        <svg class="search-icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
          <circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" stroke-width="1.5" />
          <line x1="11" y1="11" x2="14.5" y2="14.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
        </svg>
        <input v-model="bankQuery" type="search" placeholder="Search banks…" aria-label="Search banks" class="bank-search-input" />
        <button v-if="bankQuery" type="button" class="clear-search" aria-label="Clear search" @click="bankQuery = ''">✕</button>
      </div>
      <button type="button" class="share-btn" :class="{ copied }" @click="copyShareLink">
        <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">
          <path
            d="M6.5 9.5l3-3M6.8 5.3l.9-.9a2.2 2.2 0 013.1 3.1l-.9.9M9.2 10.7l-.9.9a2.2 2.2 0 01-3.1-3.1l.9-.9"
            fill="none"
            stroke="currentColor"
            stroke-width="1.4"
            stroke-linecap="round"
          />
        </svg>
        {{ copied ? "Copied!" : "Copy link" }}
      </button>
      <button
        type="button"
        class="theme-toggle"
        :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
        @click="toggleTheme"
      >
        <svg v-if="isDark" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
          <circle cx="8" cy="8" r="3" fill="none" stroke="currentColor" stroke-width="1.4"/>
          <g stroke="currentColor" stroke-width="1.4" stroke-linecap="round">
            <line x1="8" y1="1.5" x2="8" y2="3"/>
            <line x1="8" y1="13" x2="8" y2="14.5"/>
            <line x1="1.5" y1="8" x2="3" y2="8"/>
            <line x1="13" y1="8" x2="14.5" y2="8"/>
            <line x1="3.4" y1="3.4" x2="4.4" y2="4.4"/>
            <line x1="11.6" y1="11.6" x2="12.6" y2="12.6"/>
            <line x1="12.6" y1="3.4" x2="11.6" y2="4.4"/>
            <line x1="4.4" y1="11.6" x2="3.4" y2="12.6"/>
          </g>
        </svg>
        <svg v-else viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
          <path d="M13 10.5a6 6 0 0 1-7.5-7.5A5.5 5.5 0 1 0 13 10.5z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>
    <p v-if="bankQuery && searchedSeries.length === 0" class="no-results">No banks match "{{ bankQuery }}".</p>

    <section class="panel">
      <h2>Best value today</h2>
      <BestRateTable v-model:amount="amount" :series="searchedSeries" :currency="currency" :fees="fees" />
    </section>

    <section class="panel">
      <div class="panel-header">
        <h2>Historical TT Buy rate</h2>
        <div class="header-controls">
          <button type="button" class="table-toggle" @click="showTable = !showTable">
            {{ showTable ? "Show chart" : "View as table" }}
          </button>
          <div class="range-filter" role="group" aria-label="Date range">
            <button
              v-for="opt in RANGE_OPTIONS"
              :key="opt.key"
              type="button"
              class="range-btn"
              :class="{ active: range === opt.key }"
              :aria-pressed="range === opt.key"
              @click="range = opt.key"
            >
              {{ opt.label }}
            </button>
          </div>
        </div>
      </div>
      <LineChart v-model:show-table="showTable" :series="filteredSeries" :hidden="hidden" :currency="currency" @toggle="toggleBank" />
    </section>
  </main>

  <p v-else-if="loadError" class="error">Couldn't load rate data: {{ loadError }}</p>
  <p v-else class="loading">Loading rates…</p>

  <footer class="site-footer">
    Built by <a href="https://rakshithnettar.com" target="_blank" rel="noopener noreferrer">Rakshith Bellare</a>
    <span class="footer-sep">·</span>
    <a href="https://bellare.gumroad.com/l/tiffp" target="_blank" rel="noopener noreferrer">Buy me a coffee</a>
  </footer>
</template>

<style scoped lang="scss">
.page-header {
  margin-bottom: 32px;

  .eyebrow {
    color: var(--text-muted);
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin: 0 0 6px;
  }

  h1 {
    font-size: 28px;
    margin: 0 0 12px;
  }

  .lede {
    color: var(--text-secondary);
    max-width: 640px;
    line-height: 1.5;
    margin: 0 0 8px;
  }

  .updated {
    color: var(--text-muted);
    font-size: 13px;
    margin: 0;
  }
}

.toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.currency-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.currency-btn {
  background: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  white-space: nowrap;
  cursor: pointer;

  &:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }

  &.active {
    background: var(--accent);
    border-color: var(--accent);
    color: #fff;
  }
}

.bank-search {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 160px;
  margin-bottom: 0;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface-1);

  .search-icon {
    color: var(--text-muted);
    flex: none;
  }
}

.bank-search-input {
  flex: 1;
  min-width: 0;
  border: none;
  background: none;
  padding: 8px 4px;
  font-size: 13px;
  color: var(--text-primary);

  &:focus {
    outline: none;
  }

  &::placeholder {
    color: var(--text-muted);
  }

  // Hide the native cancel button — the .clear-search button replaces it
  // so it matches the rest of the app's styling.
  &::-webkit-search-cancel-button {
    -webkit-appearance: none;
  }
}

.clear-search {
  flex: none;
  background: none;
  border: none;
  padding: 4px;
  font-size: 12px;
  color: var(--text-muted);
  cursor: pointer;

  &:hover {
    color: var(--text-primary);
  }
}

.share-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex: none;
  background: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  white-space: nowrap;
  cursor: pointer;

  &:hover {
    color: var(--text-primary);
  }

  &:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }

  &.copied {
    color: var(--success-text);
    border-color: var(--success-text);
  }
}

.no-results {
  color: var(--text-secondary);
  font-size: 13px;
  margin: -8px 0 16px;
}

.panel {
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;

  h2 {
    font-size: 16px;
    margin: 0 0 16px;
  }

  @media (max-width: 480px) {
    padding: 14px;
  }
}

.panel-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px 16px;

  h2 {
    margin: 0;
  }
}

.header-controls {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.table-toggle {
  background: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
  cursor: pointer;

  &:hover {
    color: var(--text-primary);
  }

  &:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
}

.range-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.range-btn {
  background: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
  cursor: pointer;

  &:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }

  &.active {
    background: var(--accent);
    border-color: var(--accent);
    color: #fff;
  }
}

.theme-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
  width: 30px;
  height: 30px;
  background: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;

  &:hover {
    color: var(--text-primary);
  }

  &:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
}

.loading,
.error {
  color: var(--text-secondary);
}

.error {
  color: var(--status-critical);
}

.site-footer {
  position: relative;
  margin-top: 40px;
  padding-top: 20px;
  color: var(--text-muted);
  font-size: 13px;
  text-align: center;

  // Full-bleed border: the footer itself is constrained to #app's max-width,
  // but this line should span the whole viewport regardless.
  &::before {
    content: "";
    position: absolute;
    top: 0;
    left: 50%;
    width: 100vw;
    height: 1px;
    background: var(--border);
    transform: translateX(-50%);
  }

  .footer-sep {
    margin: 0 6px;
  }

  a {
    color: var(--text-secondary);
    text-decoration: underline;
    text-underline-offset: 2px;

    &:hover {
      color: var(--text-primary);
    }
  }
}
</style>
