<script setup lang="ts">
import { computed, ref } from "vue";
import type { BankSeries } from "../types";
import { shortName, brandColor } from "../bankPalette";

const props = defineProps<{
  series: BankSeries[];
  currency: string;
}>();

type RangeKey = "30d" | "90d" | "all";
const RANGES: { key: RangeKey; label: string; days: number | null }[] = [
  { key: "30d", label: "30 days", days: 30 },
  { key: "90d", label: "90 days", days: 90 },
  { key: "all", label: "All time", days: null },
];
const range = ref<RangeKey>("all");

type SortKey = "wins" | "winPct" | "avgRate" | "bestRate" | "stdDev";
type SortDir = "desc" | "asc";
const sortKey = ref<SortKey>("wins");
const sortDir = ref<SortDir>("desc");

// Consistency sorts ascending by default (lower stddev = more consistent = better)
function setSort(k: SortKey) {
  if (sortKey.value === k) {
    sortDir.value = sortDir.value === "desc" ? "asc" : "desc";
  } else {
    sortKey.value = k;
    sortDir.value = k === "stdDev" ? "asc" : "desc";
  }
}

const bankSeries = computed(() =>
  props.series.filter(s => s.category === "bank" && s.points.length > 0)
);

interface Row {
  name: string;
  color: string;
  wins: number;
  winPct: number;
  avgRate: number;
  bestRate: number;
  stdDev: number;
  daysAppeared: number;
}

const leaderboardData = computed(() => {
  const opt = RANGES.find(o => o.key === range.value);
  const cutoffStr = opt?.days != null
    ? (() => { const d = new Date(); d.setDate(d.getDate() - opt.days!); return d.toISOString().slice(0, 10); })()
    : null;

  const bs = bankSeries.value;
  if (!bs.length) return { rows: [] as Row[], dateRange: null as null | { from: string; to: string; days: number } };

  const majority = Math.floor(bs.length / 2) + 1;
  const dateMap = new Map<string, { bank: string; rate: number }[]>();

  for (const s of bs) {
    for (const pt of s.points) {
      if (cutoffStr && pt.date < cutoffStr) continue;
      const list = dateMap.get(pt.date) ?? [];
      list.push({ bank: s.name, rate: pt.ttbuy });
      dateMap.set(pt.date, list);
    }
  }

  const wins: Record<string, number> = {};
  const sumRate: Record<string, number> = {};
  const cntRate: Record<string, number> = {};
  const bestMap: Record<string, number> = {};
  const rateValues: Record<string, number[]> = {};
  let qualifyingDays = 0;
  const qualDates: string[] = [];

  for (const [date, entries] of [...dateMap.entries()].sort(([a], [b]) => a.localeCompare(b))) {
    if (entries.length < majority) continue;
    qualifyingDays++;
    qualDates.push(date);
    const best = entries.reduce((a, b) => a.rate >= b.rate ? a : b);
    wins[best.bank] = (wins[best.bank] ?? 0) + 1;
    for (const e of entries) {
      sumRate[e.bank] = (sumRate[e.bank] ?? 0) + e.rate;
      cntRate[e.bank] = (cntRate[e.bank] ?? 0) + 1;
      if (!bestMap[e.bank] || e.rate > bestMap[e.bank]) bestMap[e.bank] = e.rate;
      if (!rateValues[e.bank]) rateValues[e.bank] = [];
      rateValues[e.bank].push(e.rate);
    }
  }

  function popStdDev(vals: number[]): number {
    if (vals.length < 2) return 0;
    const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
    const variance = vals.reduce((s, v) => s + (v - mean) ** 2, 0) / vals.length;
    return Math.sqrt(variance);
  }

  const rows: Row[] = bs
    .map(s => ({
      name: s.name,
      color: brandColor(s.name),
      wins: wins[s.name] ?? 0,
      winPct: qualifyingDays > 0 ? ((wins[s.name] ?? 0) / qualifyingDays) * 100 : 0,
      avgRate: cntRate[s.name] ? sumRate[s.name] / cntRate[s.name] : 0,
      bestRate: bestMap[s.name] ?? 0,
      stdDev: rateValues[s.name] ? popStdDev(rateValues[s.name]) : 0,
      daysAppeared: cntRate[s.name] ?? 0,
    }))
    .filter(r => r.daysAppeared > 0);

  return {
    rows,
    dateRange: qualDates.length >= 2
      ? { from: qualDates[0], to: qualDates[qualDates.length - 1], days: qualifyingDays }
      : null,
  };
});

const sortedRows = computed(() => {
  const dir = sortDir.value === "desc" ? -1 : 1;
  return [...leaderboardData.value.rows].sort((a, b) => (a[sortKey.value] - b[sortKey.value]) * dir);
});

const maxWins = computed(() => Math.max(...sortedRows.value.map(r => r.wins), 1));

const MONTHS_SHORT = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
function fmtDate(d: string) {
  const [, m, day] = d.split("-").map(Number);
  return `${MONTHS_SHORT[m - 1]} ${day}`;
}

function sortIcon(k: SortKey) {
  if (sortKey.value !== k) return "↕";
  return sortDir.value === "desc" ? "↓" : "↑";
}
</script>

<template>
  <div class="leaderboard">
    <div class="lb-header">
      <div v-if="leaderboardData.dateRange" class="date-range-badge">
        {{ fmtDate(leaderboardData.dateRange.from) }} – {{ fmtDate(leaderboardData.dateRange.to) }}
        &nbsp;·&nbsp; {{ leaderboardData.dateRange.days }} qualifying days
      </div>
      <div class="range-filter" role="group" aria-label="Date range">
        <button
          v-for="opt in RANGES"
          :key="opt.key"
          type="button"
          class="range-btn"
          :class="{ active: range === opt.key }"
          @click="range = opt.key"
        >{{ opt.label }}</button>
      </div>
    </div>

    <div v-if="!sortedRows.length" class="empty">Not enough qualifying data in this period.</div>
    <div v-else class="table-scroll">
      <table class="lb-table">
        <thead>
          <tr>
            <th class="th-rank">#</th>
            <th class="th-bank">Bank</th>
            <th class="th-wins sortable" @click="setSort('wins')">
              Wins <span class="sort-icon">{{ sortIcon('wins') }}</span>
            </th>
            <th class="th-winpct sortable" @click="setSort('winPct')">
              Win % <span class="sort-icon">{{ sortIcon('winPct') }}</span>
            </th>
            <th class="th-avg sortable" @click="setSort('avgRate')">
              Avg rate <span class="sort-icon">{{ sortIcon('avgRate') }}</span>
            </th>
            <th class="th-best sortable" @click="setSort('bestRate')">
              Best ever <span class="sort-icon">{{ sortIcon('bestRate') }}</span>
            </th>
            <th class="th-std sortable" @click="setSort('stdDev')"
              title="Population standard deviation of TT Buy rates in this period. Lower = more predictable.">
              Consistency <span class="sort-icon">{{ sortIcon('stdDev') }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in sortedRows" :key="row.name">
            <td class="td-rank">{{ i + 1 }}</td>
            <td class="td-bank">
              <div class="bank-cell">
                <span class="dot" :style="{ background: row.color }"></span>
                <span>{{ shortName(row.name) }}</span>
              </div>
              <div class="wins-bar-track">
                <div
                  class="wins-bar-fill"
                  :style="{ width: (row.wins / maxWins * 100).toFixed(1) + '%' }"
                ></div>
              </div>
            </td>
            <td class="td-wins num">{{ row.wins }}</td>
            <td class="td-winpct num">{{ row.winPct.toFixed(1) }}%</td>
            <td class="td-avg num">₹{{ row.avgRate.toFixed(2) }}</td>
            <td class="td-best num">₹{{ row.bestRate.toFixed(2) }}</td>
            <td class="td-std num" :class="{ 'std-best': sortKey === 'stdDev' && i === 0 }">
              ±{{ row.stdDev.toFixed(2) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="footnote">
      Wins = days with the highest {{ currency }} TT Buy rate. Only days where a majority of banks reported are counted. Click headers to sort.
    </p>
  </div>
</template>

<style scoped lang="scss">
.leaderboard {
  .lb-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 14px;
  }

  .date-range-badge {
    font-size: 12px;
    color: var(--text-muted);
  }

  .range-filter {
    display: flex;
    gap: 4px;
    flex-shrink: 0;
  }

  .range-btn {
    background: none;
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
    font-family: inherit;
    color: var(--text-secondary);
    cursor: pointer;
    transition: background 80ms ease, border-color 80ms ease, color 80ms ease;

    &:hover:not(.active) { background: var(--page-plane); color: var(--text-primary); }
    &:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
    &.active { background: var(--accent); border-color: var(--accent); color: #fff; }
  }

  .table-scroll { overflow-x: auto; }

  .lb-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;

    th {
      text-align: left;
      font-size: 11px;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      padding: 0 14px 8px 0;
      white-space: nowrap;
      border-bottom: 1px solid var(--gridline);

      &.sortable {
        cursor: pointer;
        user-select: none;
        &:hover { color: var(--text-primary); }
      }

      .sort-icon { font-size: 10px; opacity: 0.7; margin-left: 2px; }
    }

    td {
      padding: 8px 14px 8px 0;
      border-bottom: 1px solid var(--gridline);
      vertical-align: middle;
    }

    tr:last-child td { border-bottom: none; }
    tr:hover td { background: color-mix(in srgb, var(--accent) 4%, transparent); }
  }

  .th-rank, .td-rank {
    width: 28px;
    color: var(--text-muted);
    font-size: 12px;
    padding-right: 8px;
  }

  .td-bank { min-width: 150px; }

  .bank-cell {
    display: flex;
    align-items: center;
    gap: 7px;
    font-weight: 500;
    white-space: nowrap;
    margin-bottom: 4px;
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .wins-bar-track {
    height: 3px;
    background: var(--gridline);
    border-radius: 2px;
    overflow: hidden;
    max-width: 100px;
  }

  .wins-bar-fill {
    height: 100%;
    background: var(--accent);
    border-radius: 2px;
    transition: width 300ms ease;
  }

  .num {
    font-variant-numeric: tabular-nums;
    font-family: ui-monospace, "Cascadia Code", "Roboto Mono", monospace;
    white-space: nowrap;
  }

  .empty {
    padding: 24px 0;
    text-align: center;
    font-size: 13px;
    color: var(--text-muted);
  }

  .th-std { text-align: right; }
  .td-std {
    color: var(--text-secondary);
    &.std-best { color: var(--success-text); font-weight: 600; }
  }

  @media (max-width: 480px) {
    // Keep # | Bank | Wins | Win% — drop avg, best, consistency
    .th-avg, .td-avg,
    .th-best, .td-best,
    .th-std, .td-std { display: none; }
    .td-bank { min-width: 100px; }
    .wins-bar-track { display: none; }
  }

  .footnote {
    margin: 8px 0 0;
    font-size: 11px;
    color: var(--text-muted);
    opacity: 0.8;
  }
}
</style>
