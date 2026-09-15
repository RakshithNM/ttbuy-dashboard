<script setup lang="ts">
import { computed, ref } from "vue";
import type { BankSeries } from "../types";
import { shortName, brandColor } from "../bankPalette";

const props = defineProps<{
  series: BankSeries[];
  currency: string;
}>();

type ViewKey = "aggregate" | "by-bank";
const view = ref<ViewKey>("aggregate");

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"];
// JS Date.getDay(): 0=Sun, 1=Mon … 5=Fri, 6=Sat
const DOW_JS = [1, 2, 3, 4, 5];

const bankSeries = computed(() =>
  props.series.filter(s => s.category === "bank" && s.points.length > 0)
);

function parseDow(dateStr: string): number {
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d).getDay();
}

// ── Aggregate: best available rate across all banks per calendar date ──────

const aggregate = computed(() => {
  const bestByDate = new Map<string, number>();
  for (const s of bankSeries.value) {
    for (const pt of s.points) {
      const cur = bestByDate.get(pt.date);
      if (cur == null || pt.ttbuy > cur) bestByDate.set(pt.date, pt.ttbuy);
    }
  }

  const sums = new Array(7).fill(0);
  const counts = new Array(7).fill(0);
  for (const [date, rate] of bestByDate) {
    const dow = parseDow(date);
    sums[dow] += rate;
    counts[dow]++;
  }

  const rows = DOW_JS.map((dow, i) => ({
    label: DAYS[i],
    avg: counts[dow] > 0 ? sums[dow] / counts[dow] : null,
    count: counts[dow],
  }));

  const validAvgs = rows.filter(r => r.avg != null).map(r => r.avg!);
  const weekMean = validAvgs.length
    ? validAvgs.reduce((a, b) => a + b, 0) / validAvgs.length
    : 0;

  const withDelta = rows.map(r => ({
    ...r,
    delta: r.avg != null ? r.avg - weekMean : null,
  }));

  const maxAbs = Math.max(...withDelta.map(r => Math.abs(r.delta ?? 0)), 0.001);
  const totalDays = rows.reduce((s, r) => s + r.count, 0);
  const bestIdx = withDelta.reduce(
    (best, r, i) => (r.delta != null && (best === -1 || r.delta > withDelta[best].delta!)) ? i : best,
    -1
  );

  return { rows: withDelta, weekMean, maxAbs, totalDays, bestIdx };
});

// ── By-bank: each bank's average deviation from its own weekly mean ────────

interface BankDowRow {
  name: string;
  color: string;
  deltas: (number | null)[];  // index 0=Mon … 4=Fri
  counts: number[];
}

const byBank = computed<BankDowRow[]>(() => {
  return bankSeries.value.map(s => {
    const sums = new Array(7).fill(0);
    const counts = new Array(7).fill(0);
    for (const pt of s.points) {
      const dow = parseDow(pt.date);
      sums[dow] += pt.ttbuy;
      counts[dow]++;
    }

    const rowAvgs = DOW_JS.map(dow =>
      counts[dow] >= 3 ? sums[dow] / counts[dow] : null
    );
    const validAvgs = rowAvgs.filter((v): v is number => v != null);
    if (validAvgs.length < 2) return null;
    const mean = validAvgs.reduce((a, b) => a + b, 0) / validAvgs.length;

    return {
      name: s.name,
      color: brandColor(s.name),
      deltas: rowAvgs.map(v => (v != null ? v - mean : null)),
      counts: DOW_JS.map(dow => counts[dow]),
    };
  }).filter((r): r is BankDowRow => r !== null)
    .sort((a, b) => {
      // sort by the sum of valid deltas variance (most pattern first)
      const va = a.deltas.filter((d): d is number => d != null);
      const vb = b.deltas.filter((d): d is number => d != null);
      const varA = va.length ? Math.max(...va.map(Math.abs)) : 0;
      const varB = vb.length ? Math.max(...vb.map(Math.abs)) : 0;
      return varB - varA;
    });
});

const byBankMaxAbs = computed(() => {
  let max = 0.001;
  for (const row of byBank.value) {
    for (const d of row.deltas) {
      if (d != null && Math.abs(d) > max) max = Math.abs(d);
    }
  }
  return max;
});

function cellOpacity(delta: number | null, maxAbs: number): number {
  if (delta == null) return 0;
  return 0.12 + (Math.abs(delta) / maxAbs) * 0.72;
}

function cellBg(delta: number | null, maxAbs: number): string {
  if (delta == null) return "transparent";
  const op = cellOpacity(delta, maxAbs);
  return delta > 0
    ? `color-mix(in srgb, var(--status-good) ${Math.round(op * 100)}%, transparent)`
    : `color-mix(in srgb, var(--series-2) ${Math.round(op * 100)}%, transparent)`;
}

function sign(n: number): string {
  return n >= 0 ? `+${n.toFixed(2)}` : n.toFixed(2);
}
</script>

<template>
  <div class="dow-root">
    <div class="dow-toggle" role="group" aria-label="View">
      <button
        v-for="opt in ([{ key: 'aggregate', label: 'All banks' }, { key: 'by-bank', label: 'By bank' }] as const)"
        :key="opt.key"
        type="button"
        class="toggle-btn"
        :class="{ active: view === opt.key }"
        @click="view = opt.key"
      >{{ opt.label }}</button>
    </div>

    <!-- ── Aggregate bar chart ── -->
    <div v-if="view === 'aggregate'" class="agg-chart" aria-label="Average best rate by day of week">
      <div class="bar-track">
        <div
          v-for="(row, i) in aggregate.rows"
          :key="row.label"
          class="bar-col"
          :class="{ best: i === aggregate.bestIdx }"
          :title="`${row.label}: ${row.delta != null ? sign(row.delta) : 'n/a'} vs weekly avg (${row.count} days)`"
        >
          <!-- positive zone -->
          <div class="zone zone--pos">
            <div
              v-if="(row.delta ?? 0) > 0"
              class="bar bar--pos"
              :style="{ height: `${(row.delta! / aggregate.maxAbs) * 100}%` }"
            />
          </div>

          <!-- baseline -->
          <div class="bar-baseline" />

          <!-- negative zone -->
          <div class="zone zone--neg">
            <div
              v-if="(row.delta ?? 0) < 0"
              class="bar bar--neg"
              :style="{ height: `${(Math.abs(row.delta!) / aggregate.maxAbs) * 100}%` }"
            />
          </div>
        </div>
      </div>

      <!-- labels row -->
      <div class="label-row">
        <div
          v-for="(row, i) in aggregate.rows"
          :key="row.label"
          class="label-col"
          :class="{ best: i === aggregate.bestIdx }"
        >
          <span class="delta-val" :class="{ pos: (row.delta ?? 0) > 0, neg: (row.delta ?? 0) < 0 }">
            {{ row.delta != null ? sign(row.delta) : '—' }}
          </span>
          <span class="day-name">{{ row.label }}</span>
          <span class="day-count">{{ row.count }}d</span>
        </div>
      </div>

      <p class="dow-foot">
        Deviation from the weekly average best rate · {{ aggregate.totalDays }} daily observations across all banks
      </p>
    </div>

    <!-- ── By-bank heatmap ── -->
    <div v-else class="bank-grid" role="table" aria-label="Day-of-week pattern by bank">
      <div class="grid-header" role="row">
        <span class="grid-bank-cell" role="columnheader">Bank</span>
        <span v-for="d in DAYS" :key="d" class="grid-day-cell" role="columnheader">{{ d }}</span>
      </div>

      <div
        v-for="row in byBank"
        :key="row.name"
        class="grid-row"
        role="row"
      >
        <span class="grid-bank-cell" role="cell">
          <span class="bank-dot" :style="{ background: row.color }" aria-hidden="true" />
          {{ shortName(row.name) }}
        </span>
        <span
          v-for="(delta, di) in row.deltas"
          :key="di"
          class="grid-day-cell grid-val"
          role="cell"
          :style="{ background: cellBg(delta, byBankMaxAbs) }"
          :title="`${row.name} ${DAYS[di]}: ${delta != null ? sign(delta) : 'insufficient data'} vs own weekly avg (${row.counts[di]} days)`"
        >
          {{ delta != null ? sign(delta) : '—' }}
        </span>
      </div>

      <p class="dow-foot">
        Each cell: deviation from that bank's own weekly average · cells with fewer than 3 data points shown as —
      </p>
    </div>
  </div>
</template>

<style scoped lang="scss">
.dow-root {
  user-select: none;
}

// ── Toggle ──────────────────────────────────────────────────────────────────

.dow-toggle {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
}

.toggle-btn {
  padding: 4px 12px;
  border: 1px solid var(--border);
  border-radius: 20px;
  background: none;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: background 100ms, color 100ms, border-color 100ms;

  &:hover:not(.active) {
    background: var(--page-plane);
    color: var(--text-primary);
  }

  &.active {
    background: var(--accent);
    border-color: var(--accent);
    color: #fff;
    font-weight: 500;
  }

  &:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
}

// ── Aggregate chart ──────────────────────────────────────────────────────────

.bar-track {
  display: flex;
  gap: 8px;
  align-items: stretch;
  margin-bottom: 0;
}

.bar-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;

  &.best .zone--pos .bar--pos {
    background: var(--status-good);
  }
}

.zone {
  flex: 1;
  width: 100%;
  display: flex;
  align-items: flex-end;  // positive bars grow upward
  position: relative;
  min-height: 60px;

  &--neg {
    align-items: flex-start;  // negative bars grow downward
  }
}

.bar {
  width: 80%;
  margin: 0 auto;
  border-radius: 3px;
  transition: height 300ms ease;

  &--pos {
    background: var(--status-good);
    opacity: 0.82;
    border-radius: 3px 3px 0 0;
  }

  &--neg {
    background: var(--series-2);
    opacity: 0.72;
    border-radius: 0 0 3px 3px;
  }
}

.bar-baseline {
  width: 100%;
  height: 1px;
  background: var(--baseline);
  flex: none;
}

.label-row {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.label-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;

  &.best .day-name {
    font-weight: 700;
    color: var(--text-primary);
  }
}

.delta-val {
  font-size: 12px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--text-muted);

  &.pos { color: var(--success-text); }
  &.neg { color: var(--series-2); }
}

.day-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.day-count {
  font-size: 11px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

// ── By-bank heatmap ───────────────────────────────────────────────────────────

.bank-grid {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.grid-header,
.grid-row {
  display: grid;
  grid-template-columns: 130px repeat(5, 1fr);
  gap: 3px;
  margin-bottom: 3px;
  align-items: center;
}

.grid-bank-cell {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;

  .grid-header & {
    font-size: 11px;
    color: var(--text-muted);
    font-weight: 400;
  }
}

.grid-day-cell {
  text-align: center;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);

  &.grid-val {
    font-size: 11px;
    font-variant-numeric: tabular-nums;
    color: var(--text-secondary);
    padding: 4px 2px;
    border-radius: 4px;
    transition: background 200ms;
  }
}

.bank-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex: none;
}

// ── Shared footnote ──────────────────────────────────────────────────────────

.dow-foot {
  margin: 14px 0 0;
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.5;
}
</style>
