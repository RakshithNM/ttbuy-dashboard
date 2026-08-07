<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { RatesByCurrency, FeesByBank, FeeSlab } from "../types";
import { brandColor, isPlatform, shortName } from "../bankPalette";
import { currencySymbol } from "../currencies";

const props = defineProps<{
  rawRates: RatesByCurrency;
  fees: FeesByBank;
  currencies: string[];
}>();

const DEFAULT_AMOUNTS: Record<string, number> = {
  USD: 1000, GBP: 800, EUR: 900, AED: 3600,
};

const MONTHS = [
  "January","February","March","April","May","June",
  "July","August","September","October","November","December",
];

const currency = ref(props.currencies[0] ?? "USD");
const amountStr = ref(String(DEFAULT_AMOUNTS[currency.value] ?? 1000));
const selectedDate = ref("");

function feeFromSlabs(slabs: FeeSlab[], grossInr: number): number {
  for (const s of slabs) {
    if (s.up_to === null || grossInr <= s.up_to) return s.fee_inr;
  }
  return 0;
}

const amount = computed(() => {
  const n = parseFloat(amountStr.value);
  return Number.isFinite(n) && n > 0 ? n : null;
});

// All dates where at least one bank has data for the selected currency
const availableDates = computed(() => {
  const set = new Set<string>();
  for (const pts of Object.values(props.rawRates[currency.value] ?? {})) {
    for (const p of pts) set.add(p.date);
  }
  return [...set].sort();
});

const minDate = computed(() => availableDates.value[0] ?? "");
const latestDate = computed(() => availableDates.value[availableDates.value.length - 1] ?? "");

// Dates where ≥8 non-platform banks have data — used to pick a meaningful default
const wellCoveredDates = computed(() => {
  const coverage = new Map<string, number>();
  for (const [bank, pts] of Object.entries(props.rawRates[currency.value] ?? {})) {
    if (isPlatform(bank)) continue;
    for (const p of pts) coverage.set(p.date, (coverage.get(p.date) ?? 0) + 1);
  }
  return [...coverage.entries()]
    .filter(([, n]) => n >= 8)
    .map(([dt]) => dt)
    .sort();
});

// Default: 5th-most-recent well-covered date (gives a ~5-7 day old comparison)
watch(wellCoveredDates, (dates) => {
  if (selectedDate.value || !dates.length) return;
  // at(-5) gives a date with ~5 well-covered days before today — enough to be
  // meaningfully "in the past" while still having rich bank coverage.
  selectedDate.value = dates.at(-5) ?? dates.at(-2) ?? dates[0];
}, { immediate: true });

// Reset amount when currency changes
watch(currency, (c) => {
  amountStr.value = String(DEFAULT_AMOUNTS[c] ?? 1000);
});

interface SnapshotRow {
  bank: string;
  color: string;
  ttbuy: number;
  feeUnknown: boolean;
  netInr: number;
}

function buildRows(dateStr: string): SnapshotRow[] {
  if (!dateStr || !amount.value) return [];
  const bankRates = props.rawRates[currency.value] ?? {};
  const rows: SnapshotRow[] = [];
  for (const [bank, pts] of Object.entries(bankRates)) {
    if (isPlatform(bank)) continue;
    const pt = pts.find((p) => p.date === dateStr);
    if (!pt) continue;
    const grossInr = pt.ttbuy * amount.value!;
    const fee = props.fees[bank];
    const feeUnknown = !fee?.fee_slabs && fee?.fee_inr == null;
    const feeInr = fee?.fee_slabs
      ? feeFromSlabs(fee.fee_slabs, grossInr)
      : (fee?.fee_inr ?? 0);
    rows.push({ bank, color: brandColor(bank), ttbuy: pt.ttbuy, feeUnknown, netInr: grossInr - feeInr });
  }
  return rows.sort((a, b) => b.netInr - a.netInr);
}

const ratesOnDate = computed(() => buildRows(selectedDate.value));
const bestOnDate = computed(() => ratesOnDate.value[0] ?? null);

const ratesLatest = computed(() => buildRows(latestDate.value));
const todayBest = computed(() => ratesLatest.value[0] ?? null);

const isLatestDate = computed(() => selectedDate.value === latestDate.value);

const diffInr = computed(() => {
  if (!bestOnDate.value || !todayBest.value || isLatestDate.value) return null;
  return todayBest.value.netInr - bestOnDate.value.netInr;
});

function formatInr(n: number): string {
  return Math.round(n).toLocaleString("en-IN");
}

function formatDate(dateStr: string): string {
  if (!dateStr) return "";
  const [y, m, d] = dateStr.split("-").map(Number);
  return `${MONTHS[m - 1]} ${d}, ${y}`;
}

function daysAgo(dateStr: string): string {
  if (!dateStr || !latestDate.value) return "";
  const then = new Date(dateStr);
  const latest = new Date(latestDate.value);
  const n = Math.round((latest.getTime() - then.getTime()) / 86_400_000);
  if (n === 0) return "latest data";
  return n === 1 ? "1 day ago" : `${n} days ago`;
}
</script>

<template>
  <div class="what-if">
    <div class="wif-controls">
      <input
        v-model="selectedDate"
        type="date"
        :min="minDate"
        :max="latestDate"
        class="date-input"
        aria-label="Select date"
      />
      <div v-if="currencies.length > 1" class="cur-tabs" role="group" aria-label="Currency">
        <button
          v-for="c in currencies"
          :key="c"
          type="button"
          class="cur-btn"
          :class="{ active: currency === c }"
          :aria-pressed="currency === c"
          @click="currency = c"
        >{{ c }}</button>
      </div>
      <div class="amt-block">
        <span class="amt-sym" aria-hidden="true">{{ currencySymbol(currency) }}</span>
        <input
          v-model="amountStr"
          type="number"
          min="1"
          step="100"
          class="amt-input"
          aria-label="Amount"
        />
      </div>
    </div>

    <p v-if="selectedDate && !ratesOnDate.length" class="wif-empty">
      No data for {{ formatDate(selectedDate) }}. Try a nearby weekday.
    </p>

    <template v-else-if="bestOnDate && amount">
      <div class="wif-summary">
        <!-- THEN -->
        <div class="sum-row">
          <span class="sum-epoch">{{ formatDate(selectedDate) }}<span class="sum-ago"> · {{ daysAgo(selectedDate) }}</span></span>
          <span class="sum-bank">
            <span class="sum-dot" :style="{ background: bestOnDate.color }" aria-hidden="true"></span>
            {{ shortName(bestOnDate.bank) }}
          </span>
          <span class="sum-rate">₹{{ bestOnDate.ttbuy.toFixed(2) }}</span>
          <span class="sum-arr" aria-hidden="true">→</span>
          <span class="sum-recv">₹{{ formatInr(bestOnDate.netInr) }}<span class="sum-for"> for {{ currencySymbol(currency) }}{{ amount.toLocaleString("en-IN") }}</span></span>
        </div>

        <!-- TODAY comparison -->
        <div v-if="!isLatestDate && todayBest && diffInr !== null" class="sum-row sum-today">
          <span class="sum-epoch">{{ formatDate(latestDate) }}<span class="sum-ago"> · today</span></span>
          <span class="sum-bank">
            <span class="sum-dot" :style="{ background: todayBest.color }" aria-hidden="true"></span>
            {{ shortName(todayBest.bank) }}
          </span>
          <span class="sum-rate">₹{{ todayBest.ttbuy.toFixed(2) }}</span>
          <span class="sum-arr" aria-hidden="true">→</span>
          <span class="sum-recv">₹{{ formatInr(todayBest.netInr) }}</span>
          <span class="sum-diff" :class="diffInr >= 0 ? 'diff-pos' : 'diff-neg'">
            {{ diffInr >= 0
              ? `+₹${formatInr(diffInr)} more today`
              : `-₹${formatInr(-diffInr)} more then` }}
          </span>
        </div>
      </div>

      <div class="snap-scroll">
        <table class="snap-table">
          <thead>
            <tr>
              <th>Bank</th>
              <th class="th-r">Rate (₹/{{ currency }})</th>
              <th class="th-r">You receive</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, i) in ratesOnDate"
              :key="row.bank"
              :class="{ 'is-best': i === 0 }"
            >
              <td class="td-bank">
                <span class="row-dot" :style="{ background: row.color }" aria-hidden="true"></span>
                {{ shortName(row.bank) }}
              </td>
              <td class="td-num">{{ row.ttbuy.toFixed(2) }}</td>
              <td class="td-num">₹{{ formatInr(row.netInr) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped lang="scss">
.what-if {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.wif-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.date-input {
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 13px;
  font-family: inherit;
  color: var(--text-primary);
  background: var(--surface-1);
  cursor: pointer;
  height: 32px;

  &:focus {
    outline: 2px solid var(--accent);
    outline-offset: 1px;
  }

  &::-webkit-calendar-picker-indicator {
    opacity: 0.5;
    cursor: pointer;
  }
}

.cur-tabs {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.cur-btn {
  background: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  white-space: nowrap;
  cursor: pointer;
  transition: background 80ms ease, border-color 80ms ease, color 80ms ease;
  font-family: inherit;

  &:hover:not(.active) {
    background: var(--page-plane);
    color: var(--text-primary);
  }

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

.amt-block {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface-1);
  height: 32px;

  &:focus-within {
    outline: 2px solid var(--accent);
    outline-offset: 1px;
  }
}

.amt-sym {
  font-size: 13px;
  color: var(--text-muted);
  flex: none;
}

.amt-input {
  border: none;
  background: none;
  padding: 0;
  font-size: 13px;
  font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
  color: var(--text-primary);
  width: 80px;
  min-width: 0;

  &:focus {
    outline: none;
  }

  &::-webkit-inner-spin-button,
  &::-webkit-outer-spin-button {
    -webkit-appearance: none;
  }
}

.wif-empty {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
}

// Summary

.wif-summary {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 14px;
  background: color-mix(in srgb, var(--accent) 6%, transparent);
  border-radius: 7px;
}

.sum-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 13px;
}

.sum-epoch {
  min-width: 160px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;

  .sum-ago {
    font-weight: 400;
    color: var(--text-muted);
  }
}

.sum-bank {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
}

.sum-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex: none;
}

.sum-rate {
  font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
  font-size: 13px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.sum-arr {
  color: var(--text-muted);
}

.sum-recv {
  font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;

  .sum-for {
    font-weight: 400;
    font-size: 11px;
    color: var(--text-muted);
    margin-left: 3px;
  }
}

.sum-today {
  .sum-epoch,
  .sum-bank,
  .sum-recv {
    color: var(--text-secondary);
    font-weight: 400;
  }
}

.sum-diff {
  font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
  font-size: 12px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 4px;
  white-space: nowrap;

  &.diff-pos {
    color: var(--status-good);
    background: color-mix(in srgb, var(--status-good) 12%, transparent);
  }

  &.diff-neg {
    color: var(--status-warning);
    background: color-mix(in srgb, var(--status-warning) 12%, transparent);
  }
}

// Snapshot table

.snap-scroll {
  overflow-x: auto;
}

.snap-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;

  th {
    padding: 6px 10px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
    text-align: left;
  }

  .th-r {
    text-align: right;
  }

  td {
    padding: 8px 10px;
    border-bottom: 1px solid var(--border);
    vertical-align: middle;
  }

  tbody tr:last-child td {
    border-bottom: none;
  }

  tbody tr.is-best td {
    font-weight: 600;
    color: var(--text-primary);
  }
}

.td-bank {
  display: flex;
  align-items: center;
  gap: 7px;
  white-space: nowrap;
}

.row-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex: none;
}

.td-num {
  font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
  text-align: right;
  white-space: nowrap;
  color: var(--text-secondary);

  .is-best & {
    color: var(--text-primary);
  }
}
</style>
