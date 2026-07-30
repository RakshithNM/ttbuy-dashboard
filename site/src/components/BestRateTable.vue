<script setup lang="ts">
import { computed, ref } from "vue";
import type { BankSeries } from "../types";
import { shortName } from "../bankPalette";
import { currencySymbol } from "../currencies";

const props = defineProps<{
  series: BankSeries[];
  currency: string;
}>();

const amount = ref(1000);
const safeAmount = computed(() => {
  const n = Number(amount.value);
  return Number.isFinite(n) && n > 0 ? n : 0;
});

interface Row {
  bank: string;
  color: string;
  wrapped: boolean;
  ttbuy: number;
  date: string;
  youReceive: number;
  // Change vs the previous calendar day's rate; null when the previous
  // scraped point isn't from the day right before (a bank missed a day, or
  // this is the first point on record) — showing a delta across a gap would
  // misrepresent it as a single day's move.
  delta: number | null;
  // Rupees you'd receive less than the best bank, at the chosen amount —
  // 0 for the best bank itself.
  gapToBest: number;
}

function isPreviousCalendarDay(earlierDate: string, laterDate: string): boolean {
  const earlier = new Date(`${earlierDate}T00:00:00Z`);
  const later = new Date(`${laterDate}T00:00:00Z`);
  const diffDays = (later.getTime() - earlier.getTime()) / 86_400_000;
  return diffDays === 1;
}

const rows = computed<Row[]>(() => {
  const withoutGap = props.series
    .map((s) => {
      const last = s.points[s.points.length - 1];
      if (!last) return null;
      const prev = s.points.length >= 2 ? s.points[s.points.length - 2] : null;
      const showDelta = prev !== null && isPreviousCalendarDay(prev.date, last.date);
      return {
        bank: s.name,
        color: s.color,
        wrapped: s.wrapped,
        ttbuy: last.ttbuy,
        date: last.date,
        youReceive: last.ttbuy * safeAmount.value,
        delta: showDelta ? last.ttbuy - prev!.ttbuy : null,
      };
    })
    .filter((r): r is Omit<Row, "gapToBest"> => r !== null)
    // Sorting by TT Buy is equivalent to sorting by amount received (a
    // positive linear scale of it), so one sort serves both columns.
    .sort((a, b) => b.ttbuy - a.ttbuy);

  const bestTtbuy = withoutGap[0]?.ttbuy ?? 0;
  return withoutGap.map((r) => ({ ...r, gapToBest: (bestTtbuy - r.ttbuy) * safeAmount.value }));
});

const bestBank = computed(() => rows.value[0]?.bank ?? null);

function formatInr(value: number): string {
  return value.toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

function deltaDirection(delta: number): "up" | "down" | "flat" {
  if (delta > 0.004) return "up";
  if (delta < -0.004) return "down";
  return "flat";
}
</script>

<template>
  <div class="best-rate">
    <div class="amount-control">
      <label for="remit-amount">If you receive</label>
      <div class="amount-field">
        <span class="prefix">{{ currencySymbol(currency) }}</span>
        <input id="remit-amount" v-model.number="amount" type="number" min="0" step="1" inputmode="decimal" class="amount-input" />
      </div>
      <span class="suffix">{{ currency }}, here's what each bank credits you</span>
    </div>

    <div class="table-wrap">
      <table class="best-rate-table">
        <caption>{{ currency }} TT Buy rate by bank — most recent published rate per bank</caption>
        <thead>
          <tr>
            <th scope="col">Bank</th>
            <th scope="col" class="num">TT Buy (₹ / {{ currency }})</th>
            <th scope="col" class="num">You receive (₹)</th>
            <th scope="col" class="num">vs best</th>
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
            <td class="num">
              {{ row.ttbuy.toFixed(2) }}
              <span
                v-if="row.delta !== null"
                class="delta"
                :class="deltaDirection(row.delta)"
                :title="`${deltaDirection(row.delta) === 'flat' ? 'Unchanged' : deltaDirection(row.delta) === 'up' ? 'Up' : 'Down'} ${Math.abs(row.delta).toFixed(2)} vs previous rate`"
              >
                <template v-if="deltaDirection(row.delta) === 'up'">▲</template>
                <template v-else-if="deltaDirection(row.delta) === 'down'">▼</template>
                <template v-else>–</template>
                {{ Math.abs(row.delta).toFixed(2) }}
              </span>
            </td>
            <td class="num receive">₹{{ formatInr(row.youReceive) }}</td>
            <td class="num gap" :class="{ muted: row.bank === bestBank }">
              <template v-if="row.bank === bestBank">—</template>
              <template v-else>−₹{{ formatInr(row.gapToBest) }}</template>
            </td>
            <td class="muted">{{ row.date }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped lang="scss">
.amount-control {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 13px;
  color: var(--text-secondary);

  label {
    white-space: nowrap;
  }

  .suffix {
    color: var(--text-muted);
  }
}

.amount-field {
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 0 8px;
  background: var(--surface-1);

  .prefix {
    color: var(--text-muted);
    font-size: 13px;
  }
}

.amount-input {
  width: 100px;
  border: none;
  background: none;
  padding: 6px 4px;
  font-size: 13px;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;

  &:focus {
    outline: none;
  }

  // Hide the spinner so it doesn't fight with the $ prefix for space.
  &::-webkit-outer-spin-button,
  &::-webkit-inner-spin-button {
    -webkit-appearance: none;
    margin: 0;
  }
  -moz-appearance: textfield;
}

.table-wrap {
  overflow: auto;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.best-rate-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;

  caption {
    text-align: left;
    color: var(--text-secondary);
    font-size: 13px;
    padding: 10px 12px 0;
    margin-bottom: 4px;
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

  .receive {
    color: var(--text-primary);
    font-weight: 600;
  }

  .gap {
    color: var(--text-secondary);
  }

  .delta {
    display: inline-block;
    margin-left: 6px;
    font-size: 11px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;

    &.up {
      color: var(--success-text);
    }

    &.down {
      color: var(--status-critical);
    }

    &.flat {
      color: var(--text-muted);
    }
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
