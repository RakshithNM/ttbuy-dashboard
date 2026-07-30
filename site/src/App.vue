<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import LineChart from "./components/LineChart.vue";
import BestRateTable from "./components/BestRateTable.vue";
import { isWrappedSlot, shortName, slotForBank, sortByBankOrder } from "./bankPalette";
import { currencyName, sortByCurrencyOrder } from "./currencies";
import type { BankSeries, RatesByCurrency } from "./types";

const rawRates = ref<RatesByCurrency>({});
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

interface StoredView {
  range?: RangeKey;
  showTable?: boolean;
  currency?: string;
}

function loadStoredView(): StoredView {
  try {
    const raw = localStorage.getItem(VIEW_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as StoredView) : {};
  } catch {
    return {};
  }
}

const storedView = loadStoredView();

const range = ref<RangeKey>(
  storedView.range && RANGE_OPTIONS.some((o) => o.key === storedView.range) ? storedView.range : "7d"
);
const showTable = ref(typeof storedView.showTable === "boolean" ? storedView.showTable : true);
const currency = ref<string>(storedView.currency ?? "USD");

watch([range, showTable, currency], ([r, t, c]) => {
  try {
    localStorage.setItem(VIEW_STORAGE_KEY, JSON.stringify({ range: r, showTable: t, currency: c }));
  } catch {
    // Persistence is best-effort; nothing to do if storage is unavailable.
  }
});

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
});

const availableCurrencies = computed(() => sortByCurrencyOrder(Object.keys(rawRates.value)));

const bankRates = computed(() => rawRates.value[currency.value] ?? {});

const allSeries = computed<BankSeries[]>(() => {
  const banks = sortByBankOrder(Object.keys(bankRates.value));
  return banks.map((name) => ({
    name,
    color: slotForBank(name),
    wrapped: isWrappedSlot(name),
    points: bankRates.value[name] ?? [],
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
</script>

<template>
  <header class="page-header">
    <p class="eyebrow">Inward remittance rates</p>
    <h1>{{ currency }} TT Buy rate by Indian bank</h1>
    <p class="lede">
      TT Buy is the rate a bank credits you at when you receive a foreign inward
      (telegraphic transfer) remittance — a higher TT Buy means more rupees for the
      same {{ currencyName(currency) }} amount. Rates below are scraped directly from
      each bank's public forex rate page.
    </p>
    <p v-if="lastUpdated" class="updated">
      Data last updated {{ lastUpdated }}. Collected daily once at 11 AM IST, starting 28 July 2026.
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
    </div>
    <p v-if="bankQuery && searchedSeries.length === 0" class="no-results">No banks match "{{ bankQuery }}".</p>

    <section class="panel">
      <h2>Best rate today</h2>
      <BestRateTable :series="searchedSeries" :currency="currency" />
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

  &.active {
    background: var(--series-1);
    border-color: var(--series-1);
    color: #fff;
  }
}

.bank-search {
  display: flex;
  align-items: center;
  gap: 6px;
  max-width: 280px;
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

  &.active {
    background: var(--series-1);
    border-color: var(--series-1);
    color: #fff;
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
