<script setup lang="ts">
import { computed, ref } from "vue";
import type { BankSeries } from "../types";
import { shortName } from "../bankPalette";

const props = defineProps<{
  series: BankSeries[];
  hidden: Set<string>;
}>();
const emit = defineEmits<{ (e: "toggle", bank: string): void }>();

const svgRef = ref<SVGSVGElement | null>(null);
const showTable = ref(true);

const W = 960;
const H = 380;
const MARGIN = { top: 16, right: 16, bottom: 30, left: 46 };
const plotW = W - MARGIN.left - MARGIN.right;
const plotH = H - MARGIN.top - MARGIN.bottom;

const visibleSeries = computed(() =>
  props.series.filter((s) => !props.hidden.has(s.name) && s.points.length > 0)
);

const allDates = computed(() => {
  const set = new Set<string>();
  for (const s of visibleSeries.value) for (const p of s.points) set.add(p.date);
  return Array.from(set).sort();
});

const xDomain = computed<[number, number]>(() => {
  if (allDates.value.length === 0) return [0, 1];
  const times = allDates.value.map((d) => new Date(d).getTime());
  return [Math.min(...times), Math.max(...times)];
});

function niceNum(range: number, round: boolean): number {
  const safeRange = range || 1;
  const exponent = Math.floor(Math.log10(safeRange));
  const fraction = safeRange / Math.pow(10, exponent);
  let niceFraction: number;
  if (round) {
    if (fraction < 1.5) niceFraction = 1;
    else if (fraction < 3) niceFraction = 2;
    else if (fraction < 7) niceFraction = 5;
    else niceFraction = 10;
  } else {
    if (fraction <= 1) niceFraction = 1;
    else if (fraction <= 2) niceFraction = 2;
    else if (fraction <= 5) niceFraction = 5;
    else niceFraction = 10;
  }
  return niceFraction * Math.pow(10, exponent);
}

const yDomain = computed<[number, number]>(() => {
  const values = visibleSeries.value.flatMap((s) => s.points.map((p) => p.ttbuy));
  if (values.length === 0) return [0, 1];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const pad = (max - min) * 0.15 || max * 0.05 || 1;
  const step = niceNum((max + pad - (min - pad)) / 4, true);
  return [Math.floor((min - pad) / step) * step, Math.ceil((max + pad) / step) * step];
});

const yTicks = computed<number[]>(() => {
  const [min, max] = yDomain.value;
  const step = niceNum((max - min) / 4, true) || 1;
  const ticks: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) {
    ticks.push(Math.round(v * 100) / 100);
  }
  return ticks;
});

const xTicks = computed<string[]>(() => {
  if (allDates.value.length === 0) return [];
  const [d0, d1] = xDomain.value;
  if (d0 === d1) return [allDates.value[0]];

  // Space ticks evenly across the time domain (not by data-point index) so
  // labels never cluster where points happen to be dense.
  const count = 6;
  const ticks: string[] = [];
  for (let i = 0; i < count; i++) {
    const t = d0 + (i * (d1 - d0)) / (count - 1);
    ticks.push(new Date(t).toISOString().slice(0, 10));
  }
  return ticks;
});

function formatShortDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
}

function xScale(dateStr: string): number {
  const [d0, d1] = xDomain.value;
  const t = new Date(dateStr).getTime();
  if (d1 === d0) return MARGIN.left + plotW / 2;
  return MARGIN.left + ((t - d0) / (d1 - d0)) * plotW;
}
function yScale(value: number): number {
  const [v0, v1] = yDomain.value;
  if (v1 === v0) return MARGIN.top + plotH / 2;
  return MARGIN.top + plotH - ((value - v0) / (v1 - v0)) * plotH;
}

function linePath(points: { date: string; ttbuy: number }[]): string {
  const sorted = [...points].sort((a, b) => a.date.localeCompare(b.date));
  return sorted
    .map((p, i) => `${i === 0 ? "M" : "L"}${xScale(p.date).toFixed(1)},${yScale(p.ttbuy).toFixed(1)}`)
    .join(" ");
}

function lastPoint(s: BankSeries) {
  return [...s.points].sort((a, b) => a.date.localeCompare(b.date)).at(-1) ?? null;
}

const showEndLabels = computed(() => visibleSeries.value.length <= 4);

// End labels default to the right of the point, but the last point is often
// at (or near) the right edge of the plot — flip to the left, right-anchored,
// when there isn't enough room, so the label never gets clipped by the viewBox.
const LABEL_RESERVE = 90;
function endLabelProps(x: number): { x: number; anchor: "start" | "end" } {
  if (x > MARGIN.left + plotW - LABEL_RESERVE) {
    return { x: x - 8, anchor: "end" };
  }
  return { x: x + 8, anchor: "start" };
}

const hoverDate = ref<string | null>(null);

function onPointerMove(evt: PointerEvent) {
  const svg = svgRef.value;
  if (!svg || allDates.value.length === 0) return;
  const pt = svg.createSVGPoint();
  pt.x = evt.clientX;
  pt.y = evt.clientY;
  const ctm = svg.getScreenCTM();
  if (!ctm) return;
  const loc = pt.matrixTransform(ctm.inverse());

  let nearest = allDates.value[0];
  let best = Infinity;
  for (const d of allDates.value) {
    const dx = Math.abs(xScale(d) - loc.x);
    if (dx < best) {
      best = dx;
      nearest = d;
    }
  }
  hoverDate.value = nearest;
}
function onPointerLeave() {
  hoverDate.value = null;
}

const tooltipRows = computed(() => {
  if (!hoverDate.value) return [];
  const d = hoverDate.value;
  return visibleSeries.value
    .map((s) => {
      const point = s.points.find((p) => p.date === d);
      return point ? { name: s.name, color: s.color, value: point.ttbuy } : null;
    })
    .filter((r): r is { name: string; color: string; value: number } => r !== null)
    .sort((a, b) => b.value - a.value);
});

const tooltipX = computed(() => (hoverDate.value ? xScale(hoverDate.value) : 0));
const tooltipSide = computed(() => (tooltipX.value > MARGIN.left + plotW * 0.6 ? "left" : "right"));

const tableRows = computed(() =>
  allDates.value
    .map((date) => ({
      date,
      values: visibleSeries.value.map((s) => ({
        name: s.name,
        value: s.points.find((p) => p.date === date)?.ttbuy ?? null,
      })),
    }))
    .reverse()
);
</script>

<template>
  <div class="line-chart">
    <div class="legend" role="group" aria-label="Toggle banks">
      <button
        v-for="s in series"
        :key="s.name"
        type="button"
        class="legend-item"
        :class="{ dim: hidden.has(s.name) }"
        :aria-pressed="!hidden.has(s.name)"
        @click="emit('toggle', s.name)"
      >
        <span
          class="key"
          :class="{ wrapped: s.wrapped }"
          :style="{ background: s.wrapped ? undefined : `var(${s.color})`, borderColor: `var(${s.color})` }"
          aria-hidden="true"
        ></span>
        {{ s.name }}
      </button>
      <button type="button" class="table-toggle" @click="showTable = !showTable">
        {{ showTable ? "Show chart" : "View as table" }}
      </button>
    </div>

    <svg
      v-if="!showTable"
      ref="svgRef"
      :viewBox="`0 0 ${W} ${H}`"
      class="chart-svg"
      role="img"
      aria-label="USD TT Buy rate over time by bank"
      @pointermove="onPointerMove"
      @pointerleave="onPointerLeave"
    >
      <!-- gridlines + y ticks -->
      <g>
        <line
          v-for="t in yTicks"
          :key="`grid-${t}`"
          :x1="MARGIN.left"
          :x2="W - MARGIN.right"
          :y1="yScale(t)"
          :y2="yScale(t)"
          class="gridline"
        />
        <text v-for="t in yTicks" :key="`ytick-${t}`" :x="MARGIN.left - 8" :y="yScale(t)" class="axis-label y-label">
          {{ t.toFixed(2) }}
        </text>
      </g>

      <!-- x axis -->
      <g>
        <line :x1="MARGIN.left" :x2="W - MARGIN.right" :y1="H - MARGIN.bottom" :y2="H - MARGIN.bottom" class="baseline" />
        <text v-for="d in xTicks" :key="`xtick-${d}`" :x="xScale(d)" :y="H - MARGIN.bottom + 18" class="axis-label x-label">
          {{ formatShortDate(d) }}
        </text>
      </g>

      <!-- series lines -->
      <g v-for="s in visibleSeries" :key="s.name">
        <path
          :d="linePath(s.points)"
          fill="none"
          :stroke="`var(${s.color})`"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          :stroke-dasharray="s.wrapped ? '6 3' : undefined"
        />
        <circle
          v-for="p in s.points"
          :key="`${s.name}-${p.date}`"
          :cx="xScale(p.date)"
          :cy="yScale(p.ttbuy)"
          r="2.5"
          :fill="`var(${s.color})`"
        />
        <template v-if="lastPoint(s)">
          <circle
            :cx="xScale(lastPoint(s)!.date)"
            :cy="yScale(lastPoint(s)!.ttbuy)"
            r="4"
            :fill="`var(${s.color})`"
            stroke="var(--surface-1)"
            stroke-width="2"
          />
          <text
            v-if="showEndLabels"
            :x="endLabelProps(xScale(lastPoint(s)!.date)).x"
            :y="yScale(lastPoint(s)!.ttbuy) + 4"
            :text-anchor="endLabelProps(xScale(lastPoint(s)!.date)).anchor"
            class="end-label"
          >
            {{ s.name }} {{ lastPoint(s)!.ttbuy.toFixed(2) }}
          </text>
        </template>
      </g>

      <!-- crosshair -->
      <g v-if="hoverDate">
        <line :x1="tooltipX" :x2="tooltipX" :y1="MARGIN.top" :y2="H - MARGIN.bottom" class="crosshair" />
      </g>
    </svg>

    <!-- tooltip -->
    <div
      v-if="!showTable && hoverDate && tooltipRows.length"
      class="tooltip"
      :class="tooltipSide"
      :style="{ left: `${(tooltipX / W) * 100}%` }"
    >
      <div class="tooltip-date">{{ formatShortDate(hoverDate) }}</div>
      <div v-for="row in tooltipRows" :key="row.name" class="tooltip-row">
        <span class="line-key" :style="{ background: `var(${row.color})` }" aria-hidden="true"></span>
        <span class="tooltip-name">{{ row.name }}</span>
        <span class="tooltip-value">{{ row.value.toFixed(2) }}</span>
      </div>
    </div>

    <div v-if="showTable" class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th scope="col">Date</th>
            <th v-for="s in visibleSeries" :key="s.name" scope="col" class="num">
              <span
                class="key"
                :class="{ wrapped: s.wrapped }"
                :style="{ background: s.wrapped ? undefined : `var(${s.color})`, borderColor: `var(${s.color})` }"
                aria-hidden="true"
              ></span>
              {{ shortName(s.name) }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in tableRows" :key="row.date">
            <th scope="row">{{ row.date }}</th>
            <td v-for="cell in row.values" :key="cell.name" class="num">
              {{ cell.value !== null ? cell.value.toFixed(2) : "—" }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped lang="scss">
.line-chart {
  position: relative;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 14px;
  margin-bottom: 12px;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: none;
  padding: 4px 2px;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;

  &.dim {
    opacity: 0.4;
  }

  .key {
    width: 14px;
    height: 3px;
    border-radius: 2px;
    display: inline-block;

    &.wrapped {
      height: 0;
      border-top: 3px dashed;
      border-radius: 0;
    }
  }
}

.table-toggle {
  margin-left: auto;
  background: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;

  &:hover {
    color: var(--text-primary);
  }
}

.chart-svg {
  width: 100%;
  height: auto;
  display: block;
  touch-action: none;
}

.gridline {
  stroke: var(--gridline);
  stroke-width: 1;
}

.baseline {
  stroke: var(--baseline);
  stroke-width: 1;
}

.crosshair {
  stroke: var(--baseline);
  stroke-width: 1;
  pointer-events: none;
}

.axis-label {
  font-size: 11px;
  fill: var(--text-muted);
}

.y-label {
  text-anchor: end;
  dominant-baseline: middle;
}

.x-label {
  text-anchor: middle;
}

.end-label {
  font-size: 11px;
  fill: var(--text-secondary);
  dominant-baseline: middle;
}

.tooltip {
  position: absolute;
  top: 8px;
  transform: translateX(12px);
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  pointer-events: none;
  min-width: 140px;

  &.left {
    transform: translateX(calc(-100% - 12px));
  }
}

.tooltip-date {
  color: var(--text-muted);
  margin-bottom: 4px;
  font-size: 11px;
}

.tooltip-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 0;
}

.line-key {
  width: 10px;
  height: 2px;
  border-radius: 1px;
  flex: none;
}

.tooltip-name {
  color: var(--text-secondary);
  flex: 1;
}

.tooltip-value {
  color: var(--text-primary);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.table-wrap {
  max-height: 420px;
  overflow: auto;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;

  th,
  td {
    padding: 8px 10px;
    border-bottom: 1px solid var(--gridline);
    text-align: left;
    white-space: nowrap;
  }

  thead th {
    position: sticky;
    top: 0;
    background: var(--surface-1);
    color: var(--text-muted);
    font-size: 11px;
    text-transform: uppercase;
  }

  .num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  thead .key {
    display: inline-block;
    width: 14px;
    height: 3px;
    border-radius: 2px;
    margin-right: 4px;
    vertical-align: middle;

    &.wrapped {
      height: 0;
      border-top: 3px dashed;
      border-radius: 0;
    }
  }
}
</style>
