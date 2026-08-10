<script setup lang="ts">
import { computed, ref } from "vue";
import type { BankSeries } from "../types";
import { shortName, brandColor } from "../bankPalette";

const props = defineProps<{
  series: BankSeries[];
  currency: string;
}>();

type Period = "30d" | "90d";
const period = ref<Period>("90d");
type SortKey = "percentile" | "rate" | "bank";
const sortKey = ref<SortKey>("percentile");

const bankSeries = computed(() => props.series.filter(s => s.category === "bank" && s.points.length > 0));

const rows = computed(() => {
  const days = period.value === "30d" ? 30 : 90;
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - days);
  const cutoffStr = cutoff.toISOString().slice(0, 10);

  const result = bankSeries.value
    .map(s => {
      const inPeriod = s.points.filter(p => p.date >= cutoffStr);
      if (inPeriod.length < 5) return null;

      const today = s.points.at(-1);
      if (!today) return null;

      const rates = inPeriod.map(p => p.ttbuy).sort((a, b) => a - b);
      const todayRate = today.ttbuy;

      // Midpoint ranking for ties
      const below = rates.filter(r => r < todayRate).length;
      const equal = rates.filter(r => r === todayRate).length;
      const percentile = ((below + equal / 2) / rates.length) * 100;

      return {
        name: s.name,
        color: brandColor(s.name),
        todayRate,
        percentile,
        min: rates[0],
        max: rates[rates.length - 1],
        median: rates[Math.floor(rates.length / 2)],
        n: rates.length,
      };
    })
    .filter((r): r is NonNullable<typeof r> => r !== null);

  return [...result].sort((a, b) => {
    if (sortKey.value === "percentile") return b.percentile - a.percentile;
    if (sortKey.value === "rate") return b.todayRate - a.todayRate;
    return a.name.localeCompare(b.name);
  });
});

function signal(pct: number): { text: string; cls: string } {
  if (pct >= 85) return { text: "Unusually high", cls: "sig-high" };
  if (pct >= 60) return { text: "Above average", cls: "sig-above" };
  if (pct >= 40) return { text: "Average", cls: "sig-avg" };
  if (pct >= 15) return { text: "Below average", cls: "sig-below" };
  return { text: "Unusually low", cls: "sig-low" };
}

function barColor(pct: number): string {
  if (pct >= 85) return "var(--status-good)";
  if (pct >= 60) return "var(--series-3)";
  if (pct >= 40) return "var(--baseline)";
  if (pct >= 15) return "var(--status-serious)";
  return "var(--status-critical)";
}

function setSort(k: SortKey) {
  sortKey.value = k;
}
</script>

<template>
  <div class="pct-wrap">
    <div class="pct-header">
      <div class="sort-group" role="group" aria-label="Sort by">
        <span class="sort-label">Sort:</span>
        <button type="button" class="sort-btn" :class="{ active: sortKey === 'percentile' }" @click="setSort('percentile')">Percentile</button>
        <button type="button" class="sort-btn" :class="{ active: sortKey === 'rate' }" @click="setSort('rate')">Today's rate</button>
        <button type="button" class="sort-btn" :class="{ active: sortKey === 'bank' }" @click="setSort('bank')">Name</button>
      </div>
      <div class="period-group" role="group" aria-label="Period">
        <button type="button" class="period-btn" :class="{ active: period === '30d' }" @click="period = '30d'">30 days</button>
        <button type="button" class="period-btn" :class="{ active: period === '90d' }" @click="period = '90d'">90 days</button>
      </div>
    </div>

    <div v-if="!rows.length" class="empty">Not enough data yet — banks need at least 5 qualifying days in the selected period.</div>
    <div v-else class="table-scroll">
      <table class="pct-table">
        <thead>
          <tr>
            <th class="th-bank">Bank</th>
            <th class="th-rate">Today</th>
            <th class="th-bar">Position in {{ period }} history</th>
            <th class="th-range">{{ period }} range</th>
            <th class="th-signal">Signal</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.name">
            <td class="td-bank">
              <span class="dot" :style="{ background: row.color }"></span>
              {{ shortName(row.name) }}
            </td>
            <td class="td-rate num">₹{{ row.todayRate.toFixed(2) }}</td>
            <td class="td-bar">
              <div class="bar-row">
                <div class="bar-track">
                  <div
                    class="bar-fill"
                    :style="{ width: row.percentile.toFixed(1) + '%', background: barColor(row.percentile) }"
                  ></div>
                </div>
                <span class="pct-num" :style="{ color: barColor(row.percentile) }">
                  {{ Math.round(row.percentile) }}th pct
                </span>
              </div>
            </td>
            <td class="td-range num">₹{{ row.min.toFixed(2) }} – ₹{{ row.max.toFixed(2) }}</td>
            <td class="td-signal">
              <span class="sig-chip" :class="signal(row.percentile).cls">{{ signal(row.percentile).text }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="footnote">
      Percentile is where today's rate sits within the bank's own {{ period === "30d" ? "30-day" : "90-day" }} history.
      Banks with fewer than 5 qualifying days are excluded.
    </p>
  </div>
</template>

<style scoped lang="scss">
.pct-wrap {
  .pct-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 14px;
  }

  .sort-group,
  .period-group {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .sort-label {
    font-size: 12px;
    color: var(--text-muted);
    margin-right: 2px;
  }

  .sort-btn,
  .period-btn {
    background: none;
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
    font-family: inherit;
    color: var(--text-secondary);
    cursor: pointer;
    transition: background 80ms ease, border-color 80ms ease, color 80ms ease;

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

  .table-scroll {
    overflow-x: auto;
  }

  .pct-table {
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
      padding: 0 10px 8px 0;
      white-space: nowrap;
      border-bottom: 1px solid var(--gridline);
    }

    td {
      padding: 9px 10px 9px 0;
      border-bottom: 1px solid var(--gridline);
      vertical-align: middle;

      &:last-child { padding-right: 0; }
    }

    tr:last-child td { border-bottom: none; }
  }

  .th-bar,
  .td-bar { min-width: 200px; }

  .th-range,
  .td-range { white-space: nowrap; }

  .td-bank {
    display: flex;
    align-items: center;
    gap: 7px;
    white-space: nowrap;
    font-weight: 500;
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .num { font-variant-numeric: tabular-nums; }

  .bar-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .bar-track {
    flex: 1;
    height: 6px;
    background: var(--gridline);
    border-radius: 3px;
    overflow: hidden;
    min-width: 100px;
  }

  .bar-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 300ms ease;
  }

  .pct-num {
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
    min-width: 52px;
    font-variant-numeric: tabular-nums;
  }

  .sig-chip {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 500;
    white-space: nowrap;

    &.sig-high   { background: color-mix(in srgb, var(--status-good) 15%, transparent); color: var(--status-good); }
    &.sig-above  { background: color-mix(in srgb, var(--series-3) 15%, transparent);    color: var(--series-3); }
    &.sig-avg    { background: color-mix(in srgb, var(--text-muted) 12%, transparent);  color: var(--text-muted); }
    &.sig-below  { background: color-mix(in srgb, var(--status-serious) 15%, transparent); color: var(--status-serious); }
    &.sig-low    { background: color-mix(in srgb, var(--status-critical) 15%, transparent); color: var(--status-critical); }
  }

  .empty {
    padding: 24px 0;
    text-align: center;
    font-size: 13px;
    color: var(--text-muted);
  }

  .footnote {
    margin: 8px 0 0;
    font-size: 11px;
    color: var(--text-muted);
    opacity: 0.8;
  }
}
</style>
