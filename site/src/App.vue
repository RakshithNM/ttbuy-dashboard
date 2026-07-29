<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import LineChart from "./components/LineChart.vue";
import BestRateTable from "./components/BestRateTable.vue";
import { isWrappedSlot, slotForBank, sortByBankOrder } from "./bankPalette";
import type { BankSeries, RatesByBank } from "./types";

const rawRates = ref<RatesByBank>({});
const loading = ref(true);
const loadError = ref<string | null>(null);
const hidden = ref<Set<string>>(new Set());

type RangeKey = "30d" | "90d" | "1y" | "all";
const range = ref<RangeKey>("90d");
const RANGE_OPTIONS: { key: RangeKey; label: string; days: number | null }[] = [
  { key: "30d", label: "Last 30 days", days: 30 },
  { key: "90d", label: "Last 90 days", days: 90 },
  { key: "1y", label: "Last 1 year", days: 365 },
  { key: "all", label: "All time", days: null },
];

onMounted(async () => {
  try {
    const res = await fetch(`${import.meta.env.BASE_URL}data/rates.json`);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    rawRates.value = await res.json();
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : "Failed to load rate data";
  } finally {
    loading.value = false;
  }
});

const allSeries = computed<BankSeries[]>(() => {
  const banks = sortByBankOrder(Object.keys(rawRates.value));
  return banks.map((name) => ({
    name,
    color: slotForBank(name),
    wrapped: isWrappedSlot(name),
    points: rawRates.value[name] ?? [],
  }));
});

const filteredSeries = computed<BankSeries[]>(() => {
  const opt = RANGE_OPTIONS.find((o) => o.key === range.value);
  if (!opt || opt.days === null) return allSeries.value;

  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - opt.days);
  const cutoffStr = cutoff.toISOString().slice(0, 10);

  return allSeries.value.map((s) => ({
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
    <h1>USD TT Buy rate by Indian bank</h1>
    <p class="lede">
      TT Buy is the rate a bank credits you at when you receive a foreign inward
      (telegraphic transfer) remittance — a higher TT Buy means more rupees for the
      same dollar amount. Rates below are scraped directly from each bank's public
      forex rate page.
    </p>
    <p v-if="lastUpdated" class="updated">
      Data last updated {{ lastUpdated }}. Collected daily once at 11 AM IST, starting 28 July 2026.
    </p>
  </header>

  <main v-if="!loading && !loadError">
    <section class="panel">
      <h2>Best rate today</h2>
      <BestRateTable :series="allSeries" />
    </section>

    <section class="panel">
      <div class="panel-header">
        <h2>Historical TT Buy rate</h2>
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
      <LineChart :series="filteredSeries" :hidden="hidden" @toggle="toggleBank" />
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

.range-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 16px;
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
