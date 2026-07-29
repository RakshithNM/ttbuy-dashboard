<script setup lang="ts">
import { computed } from "vue";
import type { BankSeries } from "../types";
import { shortName } from "../bankPalette";

const props = defineProps<{
  series: BankSeries[];
}>();

interface Row {
  bank: string;
  color: string;
  wrapped: boolean;
  ttbuy: number;
  date: string;
}

const rows = computed<Row[]>(() => {
  const latest = props.series
    .map((s) => {
      const last = s.points[s.points.length - 1];
      if (!last) return null;
      return { bank: s.name, color: s.color, wrapped: s.wrapped, ttbuy: last.ttbuy, date: last.date };
    })
    .filter((r): r is Row => r !== null);

  return latest.sort((a, b) => b.ttbuy - a.ttbuy);
});

const bestBank = computed(() => rows.value[0]?.bank ?? null);
</script>

<template>
  <table class="best-rate-table">
    <caption>USD TT Buy rate by bank — most recent published rate per bank</caption>
    <thead>
      <tr>
        <th scope="col">Bank</th>
        <th scope="col" class="num">TT Buy (₹ / USD)</th>
        <th scope="col">As of</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="row in rows" :key="row.bank" :class="{ best: row.bank === bestBank }">
        <th scope="row">
          <span
            class="key"
            :class="{ wrapped: row.wrapped }"
            :style="{ background: `var(${row.color})` }"
            aria-hidden="true"
          ></span>
          <span class="bank-name">{{ shortName(row.bank) }}</span>
          <span v-if="row.bank === bestBank" class="badge">
            <svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
              <path d="M3 8.5l3 3 7-7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span class="badge-text">Best rate</span>
          </span>
        </th>
        <td class="num">{{ row.ttbuy.toFixed(2) }}</td>
        <td class="muted">{{ row.date }}</td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped lang="scss">
.best-rate-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;

  caption {
    text-align: left;
    color: var(--text-secondary);
    font-size: 13px;
    margin-bottom: 8px;
  }

  th,
  td {
    padding: 10px 12px;
    text-align: left;
    border-bottom: 1px solid var(--gridline);
    white-space: nowrap;
  }

  thead th {
    color: var(--text-muted);
    font-weight: 500;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  tbody th {
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .bank-name {
    flex: 0 1 auto;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .num {
    font-variant-numeric: tabular-nums;
    text-align: right;
  }

  .muted {
    color: var(--text-muted);
  }

  @media (max-width: 480px) {
    font-size: 13px;

    th,
    td {
      padding: 8px 6px;
    }

    .badge-text {
      display: none;
    }
  }

  .key {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 999px;
    flex: none;

    &.wrapped {
      outline: 1px dashed var(--text-muted);
      outline-offset: 2px;
    }
  }

  .badge {
    display: inline-flex;
    align-items: center;
    flex: none;
    gap: 4px;
    color: var(--success-text);
    font-size: 12px;
    font-weight: 600;
    margin-left: 4px;
  }

  tr.best {
    background: color-mix(in srgb, var(--status-good) 8%, transparent);
  }
}
</style>
