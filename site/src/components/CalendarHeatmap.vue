<script setup lang="ts">
import { computed, ref } from "vue";
import type { BankSeries } from "../types";
import { shortName } from "../bankPalette";

const props = defineProps<{
  series: BankSeries[];
  currency: string;
}>();

const today = new Date();
const todayStr = today.toISOString().slice(0, 10);
const viewYear = ref(today.getFullYear());
const viewMonth = ref(today.getMonth());

interface BestEntry { bank: string; color: string; rate: number; }

const bestByDate = computed(() => {
  const dateEntries = new Map<string, BestEntry[]>();
  for (const s of props.series) {
    if (s.category !== "bank") continue;
    for (const p of s.points) {
      if (!dateEntries.has(p.date)) {
        dateEntries.set(p.date, []);
      }
      dateEntries.get(p.date)!.push({ bank: s.name, color: s.color, rate: p.ttbuy });
    }
  }

  const map = new Map<string, BestEntry>();
  for (const [date, entries] of dateEntries.entries()) {
    if (entries.length >= 11) {
      const best = entries.reduce((prev, current) => (prev.rate > current.rate) ? prev : current);
      map.set(date, best);
    }
  }
  return map;
});

interface CalCell {
  date: string;
  day: number;
  best: BestEntry | null;
  isToday: boolean;
  isFuture: boolean;
  isBeforeData: boolean;
}

const calendarCells = computed<(CalCell | null)[]>(() => {
  const year = viewYear.value;
  const month = viewMonth.value;
  // Mon-based: Mon=0 … Sun=6
  const rawDow = new Date(year, month, 1).getDay();
  const padding = rawDow === 0 ? 6 : rawDow - 1;
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const cells: (CalCell | null)[] = [];
  for (let i = 0; i < padding; i++) cells.push(null);

  const firstDate = firstDataDate.value ?? todayStr;
  for (let d = 1; d <= daysInMonth; d++) {
    const date = `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
    cells.push({
      date,
      day: d,
      best: bestByDate.value.get(date) ?? null,
      isToday: date === todayStr,
      isFuture: date > todayStr,
      isBeforeData: date < firstDate,
    });
  }
  return cells;
});

const monthBanks = computed(() => {
  const counts = new Map<string, { color: string; count: number }>();
  for (const cell of calendarCells.value) {
    if (!cell?.best) continue;
    const e = counts.get(cell.best.bank) ?? { color: cell.best.color, count: 0 };
    e.count++;
    counts.set(cell.best.bank, e);
  }
  return [...counts.entries()]
    .map(([bank, { color, count }]) => ({ bank, color, count }))
    .sort((a, b) => b.count - a.count);
});

const MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];
const MONTHS_SHORT = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

const monthLabel = computed(() => `${MONTHS[viewMonth.value]} ${viewYear.value}`);

const firstDataDate = computed(() => {
  const dates = [...bestByDate.value.keys()].sort();
  return dates[0] ?? null;
});

const canGoPrev = computed(() => {
  if (!firstDataDate.value) return false;
  const [fy, fm] = firstDataDate.value.split("-").map(Number);
  // Allow navigating to the month that contains the first data date.
  return viewYear.value > fy || (viewYear.value === fy && viewMonth.value > fm - 1);
});

const canGoNext = computed(() =>
  viewYear.value < today.getFullYear() ||
  (viewYear.value === today.getFullYear() && viewMonth.value < today.getMonth())
);

function prevMonth() {
  if (!canGoPrev.value) return;
  if (viewMonth.value === 0) { viewYear.value--; viewMonth.value = 11; }
  else viewMonth.value--;
}

function nextMonth() {
  if (!canGoNext.value) return;
  if (viewMonth.value === 11) { viewYear.value++; viewMonth.value = 0; }
  else viewMonth.value++;
}

const hoveredCell = ref<CalCell | null>(null);

function formatCalDate(iso: string): string {
  const [, m, d] = iso.split("-").map(Number);
  return `${MONTHS_SHORT[m - 1]} ${d}`;
}
</script>

<template>
  <div class="cal-heatmap">
    <div class="cal-nav">
      <button type="button" class="cal-nav-btn" :disabled="!canGoPrev" aria-label="Previous month" @click="prevMonth">
        <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
          <path d="M10 3L6 8l4 5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
      <span class="cal-month-label">{{ monthLabel }}</span>
      <button type="button" class="cal-nav-btn" :disabled="!canGoNext" aria-label="Next month" @click="nextMonth">
        <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
          <path d="M6 3l4 5-4 5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>

    <div class="cal-info-bar">
      <template v-if="hoveredCell?.best">
        <span class="info-date">{{ formatCalDate(hoveredCell.date) }}</span>
        <span class="info-sep">·</span>
        <span class="info-best">
          Best: <strong :style="{ color: hoveredCell.best.color }">{{ shortName(hoveredCell.best.bank) }}</strong>
          at ₹{{ hoveredCell.best.rate.toFixed(2) }}
        </span>
      </template>
      <span v-else class="info-hint">Tap or hover a day to see details</span>
    </div>

    <div class="cal-dow-row" aria-hidden="true">
      <span v-for="d in ['Mo','Tu','We','Th','Fr','Sa','Su']" :key="d" class="cal-dow">{{ d }}</span>
    </div>

    <div class="cal-grid" role="grid" :aria-label="`${currency} best bank per day — ${monthLabel}`">
      <div
        v-for="(cell, i) in calendarCells"
        :key="cell ? cell.date : `pad-${i}`"
        class="cal-cell"
        :class="{
          empty: !cell,
          'has-best': !!cell?.best,
          'no-data': cell && !cell.best && !cell.isFuture && !cell.isBeforeData,
          today: cell?.isToday,
          future: cell?.isFuture,
          'before-data': cell?.isBeforeData,
        }"
        :style="cell?.best ? { '--cell-color': cell.best.color } : {}"
        role="gridcell"
        :aria-label="cell?.best ? `${formatCalDate(cell.date)}: ${shortName(cell.best.bank)} ${cell.best.rate.toFixed(2)}` : cell ? formatCalDate(cell.date) : undefined"
        @mouseenter="cell && !cell.isFuture && !cell.isBeforeData && (hoveredCell = cell)"
        @mouseleave="hoveredCell = null"
        @click="cell && !cell.isFuture && !cell.isBeforeData && (hoveredCell = cell)"
      >
        <span v-if="cell" class="cal-day-num" aria-hidden="true">{{ cell.day }}</span>
      </div>
    </div>

    <div v-if="monthBanks.length" class="cal-legend" aria-label="Legend">
      <div
        v-for="b in monthBanks"
        :key="b.bank"
        class="legend-item"
        :title="`${shortName(b.bank)}: best on ${b.count} day${b.count !== 1 ? 's' : ''} this month`"
      >
        <span class="legend-swatch" :style="{ background: b.color }" aria-hidden="true"></span>
        <span class="legend-name">{{ shortName(b.bank) }}</span>
        <span class="legend-count">{{ b.count }}d</span>
      </div>
    </div>

    <p v-else class="cal-empty-msg">No rate data for this month.</p>
  </div>
</template>

<style scoped lang="scss">
.cal-heatmap {
  user-select: none;
}

.cal-nav {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.cal-nav-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  flex: none;
  background: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 100ms ease, color 100ms ease;

  &:not(:disabled):hover {
    background: var(--page-plane);
    color: var(--text-primary);
  }

  &:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }

  &:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
}

.cal-month-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  min-width: 130px;
  text-align: center;
}

.cal-info-bar {
  min-height: 20px;
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--text-secondary);

  .info-date {
    font-weight: 500;
    color: var(--text-primary);
  }

  .info-sep {
    margin: 0 5px;
    color: var(--text-muted);
  }

  .info-best strong {
    font-weight: 600;
  }

  .info-hint {
    color: var(--text-muted);
    font-style: italic;
  }
}

.cal-dow-row {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 3px;
  margin-bottom: 3px;
}

.cal-dow {
  text-align: center;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  padding-bottom: 2px;
}

.cal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 3px;
}

.cal-cell {
  aspect-ratio: 1;
  border-radius: 5px;
  position: relative;
  background: transparent;
  transition: opacity 80ms ease, transform 80ms ease;

  &.has-best {
    background: var(--cell-color);

    &:hover {
      opacity: 0.82;
      transform: scale(1.08);
      z-index: 1;
    }
  }

  &.no-data {
    background: color-mix(in srgb, var(--text-muted) 11%, transparent);
  }

  &.future {
    background: color-mix(in srgb, var(--text-muted) 5%, transparent);
  }

  &.before-data {
    background: color-mix(in srgb, var(--text-muted) 5%, transparent);
    opacity: 0.35;
    cursor: not-allowed;
  }

  &.today {
    box-shadow: 0 0 0 2px var(--accent);
  }
}

.cal-day-num {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.9);

  .no-data &,
  .future & {
    color: var(--text-muted);
  }
}

.cal-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--gridline);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  cursor: default;
}

.legend-swatch {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  flex: none;
}

.legend-name {
  color: var(--text-secondary);
}

.legend-count {
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
  font-size: 11px;
}

.cal-empty-msg {
  margin-top: 24px;
  text-align: center;
  font-size: 13px;
  color: var(--text-muted);
}
</style>
