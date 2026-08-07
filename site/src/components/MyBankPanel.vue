<script setup lang="ts">
import { computed } from "vue";
import type { BankSeries, FeesByBank, FeeSlab } from "../types";
import { brandColor, isPlatform, shortName } from "../bankPalette";
import { currencySymbol } from "../currencies";

const props = defineProps<{
  series: BankSeries[];
  fees: FeesByBank;
  currency: string;
  amount: number;
}>();

const myBank = defineModel<string>("myBank", { default: "" });

function feeFromSlabs(slabs: FeeSlab[], grossInr: number): number {
  for (const s of slabs) {
    if (s.up_to === null || grossInr <= s.up_to) return s.fee_inr;
  }
  return 0;
}

const safeAmount = computed(() => {
  const n = Number(props.amount);
  return Number.isFinite(n) && n > 0 ? n : 0;
});

function formatInr(n: number): string {
  return Math.round(n).toLocaleString("en-IN");
}

function fmtDate(iso: string): string {
  const [, m, d] = iso.split("-").map(Number);
  return `${["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][m - 1]} ${d}`;
}

// Most recent date among all non-platform banks
const latestDate = computed(() => {
  let d = "";
  for (const s of props.series) {
    if (isPlatform(s.name) || !s.points.length) continue;
    const last = s.points.at(-1)!.date;
    if (last > d) d = last;
  }
  return d;
});

interface BankSnap {
  name: string;
  color: string;
  ttbuy: number;
  date: string;
  netInr: number;
}

// All banks with today's data, ranked by net receive
const rankedBanks = computed<BankSnap[]>(() => {
  if (!safeAmount.value || !latestDate.value) return [];
  const out: BankSnap[] = [];
  for (const s of props.series) {
    if (isPlatform(s.name) || !s.points.length) continue;
    const last = s.points.at(-1)!;
    if (last.date !== latestDate.value) continue;
    const gross = last.ttbuy * safeAmount.value;
    const fee = props.fees[s.name];
    const feeInr = fee?.fee_slabs ? feeFromSlabs(fee.fee_slabs, gross) : (fee?.fee_inr ?? 0);
    out.push({ name: s.name, color: brandColor(s.name), ttbuy: last.ttbuy, date: last.date, netInr: gross - feeInr });
  }
  return out.sort((a, b) => b.netInr - a.netInr);
});

// My bank's last known snapshot (may be stale)
const mySnap = computed<BankSnap | null>(() => {
  if (!myBank.value) return null;
  const s = props.series.find(s => s.name === myBank.value);
  if (!s || !s.points.length) return null;
  const last = s.points.at(-1)!;
  const gross = last.ttbuy * safeAmount.value;
  const fee = props.fees[myBank.value];
  const feeInr = fee?.fee_slabs ? feeFromSlabs(fee.fee_slabs, gross) : (fee?.fee_inr ?? 0);
  return { name: myBank.value, color: brandColor(myBank.value), ttbuy: last.ttbuy, date: last.date, netInr: gross - feeInr };
});

const isStale = computed(() =>
  !!mySnap.value && !!latestDate.value && mySnap.value.date < latestDate.value
);

const staleDays = computed(() => {
  if (!mySnap.value || !latestDate.value || !isStale.value) return null;
  return Math.round((new Date(latestDate.value).getTime() - new Date(mySnap.value.date).getTime()) / 86_400_000);
});

const myRank = computed<number | null>(() => {
  if (!myBank.value || isStale.value) return null;
  const i = rankedBanks.value.findIndex(b => b.name === myBank.value);
  return i >= 0 ? i + 1 : null;
});

const bestSnap = computed(() => rankedBanks.value[0] ?? null);

const gapToBest = computed<number | null>(() => {
  if (!mySnap.value || !bestSnap.value || isStale.value) return null;
  return bestSnap.value.netInr - mySnap.value.netInr;
});

type StateKind = "leading" | "competitive" | "behind" | "lagging" | "stale" | "no_data";

const stateKind = computed<StateKind>(() => {
  if (!myBank.value || !mySnap.value) return "no_data";
  if (isStale.value) return "stale";
  const rank = myRank.value;
  if (rank === null) return "no_data";
  const gap = gapToBest.value ?? 0;
  if (rank === 1) return "leading";
  if (gap < 150) return "competitive";
  if (gap < 700) return "behind";
  return "lagging";
});

// How often my bank has led in the last 30 qualifying days
const leadCount = computed<{ led: number; total: number } | null>(() => {
  if (!myBank.value) return null;
  const bankSeries = props.series.filter(s => !isPlatform(s.name) && s.points.length > 0);
  const threshold = Math.floor(bankSeries.length / 2) + 1;
  const byDate = new Map<string, { bank: string; rate: number }[]>();
  for (const s of bankSeries) {
    for (const pt of s.points) {
      const list = byDate.get(pt.date) ?? [];
      list.push({ bank: s.name, rate: pt.ttbuy });
      byDate.set(pt.date, list);
    }
  }
  const dates = [...byDate.keys()].sort().slice(-30);
  let led = 0, total = 0;
  for (const d of dates) {
    const entries = byDate.get(d)!;
    if (entries.length < threshold) continue;
    total++;
    const best = entries.reduce((a, b) => a.rate >= b.rate ? a : b);
    if (best.bank === myBank.value) led++;
  }
  return total > 0 ? { led, total } : null;
});

const allBanks = computed(() =>
  [...new Set(
    props.series.filter(s => !isPlatform(s.name) && s.points.length > 0).map(s => s.name)
  )].sort()
);

const myColor = computed(() => myBank.value ? brandColor(myBank.value) : "var(--text-muted)");
</script>

<template>
  <!-- Collapsed prompt when no bank selected -->
  <div v-if="!myBank" class="mbp-prompt">
    <span class="mbp-swatch-sm" aria-hidden="true" />
    <label class="mbp-prompt-label" for="mbp-select-empty">My bank</label>
    <select id="mbp-select-empty" v-model="myBank" class="mbp-select-inline" aria-label="Set my bank">
      <option value="">Select to see personalized insights…</option>
      <option v-for="bank in allBanks" :key="bank" :value="bank">{{ bank }}</option>
    </select>
  </div>

  <!-- Expanded panel when bank is selected -->
  <section v-else class="mbp panel" aria-label="My bank insights">
    <!-- Header: selector + clear -->
    <div class="mbp-header">
      <span class="mbp-swatch" :style="{ background: myColor }" aria-hidden="true" />
      <span class="mbp-label">My bank</span>
      <select v-model="myBank" class="mbp-select" aria-label="Change my bank">
        <option v-for="bank in allBanks" :key="bank" :value="bank">{{ bank }}</option>
      </select>
      <button type="button" class="mbp-clear" aria-label="Clear my bank" @click="myBank = ''">✕</button>
    </div>

    <!-- State body -->
    <div v-if="mySnap" class="mbp-body" :class="stateKind">

      <!-- LEADING -->
      <template v-if="stateKind === 'leading'">
        <div class="mbp-headline">
          <svg class="st-icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M2.5 8.5l4 4 7-8"/></svg>
          <span>Your bank is <strong>today's best</strong> for {{ currency }}</span>
        </div>
        <div class="mbp-stats">
          <span class="stat-rate">₹{{ mySnap.ttbuy.toFixed(2) }}</span>
          <span class="stat-arr">→</span>
          <span class="stat-recv">₹{{ formatInr(mySnap.netInr) }}</span>
          <span class="stat-for">on {{ currencySymbol(currency) }}{{ formatInr(safeAmount) }}</span>
        </div>
        <div v-if="leadCount && leadCount.led > 0" class="mbp-sub">
          Led {{ leadCount.led }} of {{ leadCount.total }} days in the last month
        </div>
      </template>

      <!-- COMPETITIVE -->
      <template v-else-if="stateKind === 'competitive'">
        <div class="mbp-headline">
          <svg class="st-icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M2 8h12"/><path d="M2 5h12" opacity="0.35"/><path d="M2 11h12" opacity="0.35"/></svg>
          <span>Your bank is <strong>close to the top</strong>, #{{ myRank }} of {{ rankedBanks.length }}</span>
        </div>
        <div class="mbp-stats">
          <span class="stat-rate">₹{{ mySnap.ttbuy.toFixed(2) }}</span>
          <span class="stat-arr">→</span>
          <span class="stat-recv">₹{{ formatInr(mySnap.netInr) }}</span>
          <span class="stat-for">on {{ currencySymbol(currency) }}{{ formatInr(safeAmount) }}</span>
          <span class="stat-gap">· ₹{{ formatInr(gapToBest!) }} less than {{ shortName(bestSnap!.name) }}</span>
        </div>
        <div v-if="leadCount && leadCount.led > 0" class="mbp-sub">
          Led {{ leadCount.led }} of {{ leadCount.total }} days in the last month
        </div>
      </template>

      <!-- BEHIND -->
      <template v-else-if="stateKind === 'behind'">
        <div class="mbp-headline">
          <svg class="st-icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3v8"/><path d="M5 8l3 3 3-3"/></svg>
          <span>Your bank is <strong>mid-table</strong>, #{{ myRank }} of {{ rankedBanks.length }} today</span>
        </div>
        <div class="mbp-stats">
          <span class="stat-rate">₹{{ mySnap.ttbuy.toFixed(2) }}</span>
          <span class="stat-arr">→</span>
          <span class="stat-recv">₹{{ formatInr(mySnap.netInr) }}</span>
          <span class="stat-for">on {{ currencySymbol(currency) }}{{ formatInr(safeAmount) }}</span>
          <span class="stat-gap">· ₹{{ formatInr(gapToBest!) }} less than {{ shortName(bestSnap!.name) }}</span>
        </div>
      </template>

      <!-- LAGGING -->
      <template v-else-if="stateKind === 'lagging'">
        <div class="mbp-headline">
          <svg class="st-icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 2v9"/><path d="M5 8l3 3 3-3"/><path d="M5 12l3 3 3-3"/></svg>
          <span>Your bank is <strong>near the bottom</strong>, #{{ myRank }} of {{ rankedBanks.length }}</span>
        </div>
        <div class="mbp-stats">
          <span class="stat-rate">₹{{ mySnap.ttbuy.toFixed(2) }}</span>
          <span class="stat-arr">→</span>
          <span class="stat-recv">₹{{ formatInr(mySnap.netInr) }}</span>
          <span class="stat-for">on {{ currencySymbol(currency) }}{{ formatInr(safeAmount) }}</span>
        </div>
        <div class="mbp-sub">
          ₹{{ formatInr(gapToBest!) }} less than {{ shortName(bestSnap!.name) }}. Switching banks would make a meaningful difference.
        </div>
      </template>

      <!-- STALE -->
      <template v-else-if="stateKind === 'stale'">
        <div class="mbp-headline">
          <svg class="st-icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"><path d="M8 1.5L1.5 13h13L8 1.5z" stroke-linejoin="round"/><line x1="8" y1="6" x2="8" y2="9.5"/><circle cx="8" cy="11.5" r="0.75" fill="currentColor" stroke="none"/></svg>
          <span>Rate is <strong>{{ staleDays }} {{ staleDays === 1 ? 'day' : 'days' }} old</strong> ({{ fmtDate(mySnap.date) }}), may not reflect today</span>
        </div>
        <div class="mbp-stats">
          <span class="stat-rate">₹{{ mySnap.ttbuy.toFixed(2) }}</span>
          <span class="stat-arr">→</span>
          <span class="stat-recv">₹{{ formatInr(mySnap.netInr) }}</span>
          <span class="stat-for">on {{ currencySymbol(currency) }}{{ formatInr(safeAmount) }}</span>
          <span v-if="bestSnap" class="stat-gap">· today's best is {{ shortName(bestSnap.name) }} at ₹{{ bestSnap.ttbuy.toFixed(2) }}</span>
        </div>
      </template>

      <!-- NO_DATA -->
      <template v-else>
        <div class="mbp-headline">
          <svg class="st-icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"><circle cx="8" cy="8" r="6"/><line x1="8" y1="5" x2="8" y2="9"/><circle cx="8" cy="11.2" r="0.75" fill="currentColor" stroke="none"/></svg>
          <span>No rate data for <strong>{{ shortName(myBank) }}</strong> today</span>
        </div>
        <div v-if="bestSnap" class="mbp-sub">
          Today's best is {{ shortName(bestSnap.name) }} at ₹{{ bestSnap.ttbuy.toFixed(2) }}
        </div>
      </template>
    </div>
  </section>
</template>

<style scoped lang="scss">
// Prompt (no bank selected) — subtle one-liner
.mbp-prompt {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 24px;
}

.mbp-swatch-sm {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--border);
  border: 1px dashed var(--text-muted);
  flex: none;
}

.mbp-prompt-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.mbp-select-inline {
  flex: 1;
  min-width: 0;
  border: none;
  background: none;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  font-family: inherit;

  &:focus {
    outline: 2px solid var(--accent);
    border-radius: 2px;
  }
}

// Expanded panel
.mbp.panel {
  margin-bottom: 24px;
  padding: 16px 20px;

  @media (max-width: 480px) {
    padding: 12px 14px;
  }
}

.mbp-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.mbp-swatch {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex: none;
  transition: background 150ms;
}

.mbp-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  white-space: nowrap;
}

.mbp-select {
  flex: 1;
  min-width: 0;
  border: none;
  background: none;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  cursor: pointer;
  font-family: inherit;

  &:focus {
    outline: 2px solid var(--accent);
    border-radius: 2px;
  }
}

.mbp-clear {
  flex: none;
  background: none;
  border: none;
  font-size: 11px;
  color: var(--text-muted);
  cursor: pointer;
  padding: 2px 4px;

  &:hover {
    color: var(--text-primary);
  }

  &:focus-visible {
    outline: 2px solid var(--accent);
    border-radius: 2px;
  }
}

// State body
.mbp-body {
  padding: 10px 12px;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 5px;

  &.leading {
    background: color-mix(in srgb, var(--status-good) 10%, transparent);
    border: 1px solid color-mix(in srgb, var(--status-good) 25%, transparent);
    .st-icon { color: var(--status-good); }
  }

  &.competitive {
    background: color-mix(in srgb, var(--accent) 9%, transparent);
    border: 1px solid color-mix(in srgb, var(--accent) 22%, transparent);
    .st-icon { color: var(--accent); }
  }

  &.behind {
    background: color-mix(in srgb, var(--status-warning) 10%, transparent);
    border: 1px solid color-mix(in srgb, var(--status-warning) 28%, transparent);
    .st-icon { color: var(--status-warning); }
  }

  &.lagging {
    background: color-mix(in srgb, var(--status-serious) 10%, transparent);
    border: 1px solid color-mix(in srgb, var(--status-serious) 28%, transparent);
    .st-icon { color: var(--status-serious); }
  }

  &.stale {
    background: color-mix(in srgb, var(--status-warning) 8%, transparent);
    border: 1px solid color-mix(in srgb, var(--status-warning) 22%, transparent);
    .st-icon { color: var(--status-warning); }
  }

  &.no_data {
    background: var(--page-plane);
    border: 1px solid var(--border);
    .st-icon { color: var(--text-muted); }
  }
}

.mbp-headline {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.4;

  strong {
    color: var(--text-primary);
    font-weight: 600;
  }

  .st-icon {
    flex: none;
    margin-top: 1px;
  }
}

.mbp-stats {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 5px;
  font-size: 13px;
  padding-left: 21px; // aligns with headline text (icon width + gap)

  .stat-rate {
    font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
    font-weight: 500;
    color: var(--text-secondary);
  }

  .stat-arr {
    color: var(--text-muted);
  }

  .stat-recv {
    font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
    font-weight: 700;
    color: var(--text-primary);
  }

  .stat-for {
    font-size: 12px;
    color: var(--text-muted);
  }

  .stat-gap {
    font-size: 12px;
    color: var(--text-muted);
  }
}

.mbp-sub {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.4;
  padding-left: 21px;
}
</style>
