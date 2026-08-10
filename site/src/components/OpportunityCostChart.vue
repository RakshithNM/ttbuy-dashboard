<script setup lang="ts">
import { computed, ref } from "vue";
import type { BankSeries, FeesByBank } from "../types";

const props = defineProps<{
  series: BankSeries[];
  currency: string;
  fees: FeesByBank;
  amount: number;
}>();

type RangeKey = "30d" | "90d" | "all";
const RANGES: { key: RangeKey; label: string; days: number | null }[] = [
  { key: "30d", label: "30 days", days: 30 },
  { key: "90d", label: "90 days", days: 90 },
  { key: "all", label: "All time", days: null },
];
const range = ref<RangeKey>("90d");

function netReceive(bankName: string, rate: number, amt: number): number {
  const gross = rate * amt;
  const fee = props.fees[bankName];
  let feeInr = 0;
  if (fee?.fee_slabs) {
    for (const sl of fee.fee_slabs) {
      if (sl.up_to === null || gross <= sl.up_to) { feeInr = sl.fee_inr; break; }
    }
  } else {
    feeInr = fee?.fee_inr ?? 0;
  }
  return gross - feeInr;
}

const bankSeries = computed(() => props.series.filter(s => s.category === "bank"));

const chartData = computed(() => {
  const opt = RANGES.find(o => o.key === range.value);
  const cutoffStr = opt?.days != null
    ? (() => { const d = new Date(); d.setDate(d.getDate() - opt.days!); return d.toISOString().slice(0, 10); })()
    : null;

  const bs = bankSeries.value;
  if (!bs.length) return [];

  const majorityThreshold = Math.floor(bs.length / 2) + 1;
  const dateMap = new Map<string, number[]>();

  for (const s of bs) {
    for (const pt of s.points) {
      if (cutoffStr && pt.date < cutoffStr) continue;
      const nets = dateMap.get(pt.date) ?? [];
      nets.push(netReceive(s.name, pt.ttbuy, props.amount));
      dateMap.set(pt.date, nets);
    }
  }

  return [...dateMap.entries()]
    .filter(([, nets]) => nets.length >= majorityThreshold)
    .map(([date, nets]) => ({ date, spread: Math.max(...nets) - Math.min(...nets) }))
    .sort((a, b) => a.date.localeCompare(b.date));
});

const W = 960;
const H = 220;
const MARGIN = { top: 16, right: 16, bottom: 30, left: 56 };
const plotW = W - MARGIN.left - MARGIN.right;
const plotH = H - MARGIN.top - MARGIN.bottom;

const xDomain = computed<[number, number]>(() => {
  if (!chartData.value.length) return [0, 1];
  const times = chartData.value.map(d => new Date(d.date).getTime());
  return [Math.min(...times), Math.max(...times)];
});

const yDomain = computed<[number, number]>(() => {
  if (!chartData.value.length) return [0, 100];
  const max = Math.max(...chartData.value.map(d => d.spread));
  const step = max <= 200 ? 50 : max <= 500 ? 100 : max <= 1000 ? 200 : 500;
  return [0, Math.ceil((max * 1.15) / step) * step];
});

function xPos(date: string): number {
  const [min, max] = xDomain.value;
  const t = new Date(date).getTime();
  return max === min ? 0 : ((t - min) / (max - min)) * plotW;
}

function yPos(value: number): number {
  const [min, max] = yDomain.value;
  return max === min ? plotH : plotH - ((value - min) / (max - min)) * plotH;
}

const linePath = computed(() =>
  chartData.value.map((pt, i) => `${i === 0 ? "M" : "L"}${xPos(pt.date).toFixed(1)},${yPos(pt.spread).toFixed(1)}`).join(" ")
);

const areaPath = computed(() => {
  if (!chartData.value.length) return "";
  const line = chartData.value.map((pt, i) => `${i === 0 ? "M" : "L"}${xPos(pt.date).toFixed(1)},${yPos(pt.spread).toFixed(1)}`).join(" ");
  const last = chartData.value[chartData.value.length - 1];
  const first = chartData.value[0];
  return `${line} L${xPos(last.date).toFixed(1)},${plotH} L${xPos(first.date).toFixed(1)},${plotH} Z`;
});

const yTicks = computed<number[]>(() => {
  const [, max] = yDomain.value;
  const step = max <= 200 ? 50 : max <= 500 ? 100 : max <= 1000 ? 200 : 500;
  const ticks: number[] = [];
  for (let v = 0; v <= max + 1e-9; v += step) ticks.push(v);
  return ticks;
});

const xTicks = computed<string[]>(() => {
  const data = chartData.value;
  if (!data.length) return [];
  if (data.length <= 5) return data.map(d => d.date);
  const step = Math.floor(data.length / 5);
  const ticks: string[] = [];
  for (let i = 0; i < data.length; i += step) ticks.push(data[i].date);
  if (ticks[ticks.length - 1] !== data[data.length - 1].date) ticks.push(data[data.length - 1].date);
  return ticks;
});

function formatDate(dateStr: string): string {
  const [, m, d] = dateStr.split("-").map(Number);
  return `${["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][m - 1]} ${d}`;
}

const avgSpread = computed(() =>
  chartData.value.length ? chartData.value.reduce((s, d) => s + d.spread, 0) / chartData.value.length : 0
);
const todaySpread = computed(() => chartData.value.at(-1)?.spread ?? null);
const maxSpread = computed(() => chartData.value.length ? Math.max(...chartData.value.map(d => d.spread)) : 0);

const tooltip = ref<{ x: number; y: number; date: string; spread: number } | null>(null);

function onMouseMove(e: MouseEvent, svg: SVGSVGElement) {
  const rect = svg.getBoundingClientRect();
  const plotX = ((e.clientX - rect.left) / rect.width) * W - MARGIN.left;
  if (plotX < 0 || plotX > plotW || !chartData.value.length) { tooltip.value = null; return; }
  const [min, max] = xDomain.value;
  const targetTime = min + (plotX / plotW) * (max - min);
  let closest = chartData.value[0];
  let minDist = Infinity;
  for (const pt of chartData.value) {
    const dist = Math.abs(new Date(pt.date).getTime() - targetTime);
    if (dist < minDist) { minDist = dist; closest = pt; }
  }
  tooltip.value = { x: MARGIN.left + xPos(closest.date), y: MARGIN.top + yPos(closest.spread), date: closest.date, spread: closest.spread };
}

function onMouseLeave() { tooltip.value = null; }

const TOOLTIP_W = 148;
const TOOLTIP_H = 44;
</script>

<template>
  <div class="opp-cost">
    <div class="opp-header">
      <div class="opp-stats">
        <div v-if="todaySpread !== null" class="stat">
          <span class="stat-label">Today's spread</span>
          <span class="stat-value">₹{{ Math.round(todaySpread).toLocaleString('en-IN') }}</span>
        </div>
        <div v-if="avgSpread > 0" class="stat">
          <span class="stat-label">Period average</span>
          <span class="stat-value muted">₹{{ Math.round(avgSpread).toLocaleString('en-IN') }}</span>
        </div>
        <div v-if="maxSpread > 0" class="stat">
          <span class="stat-label">Peak spread</span>
          <span class="stat-value muted">₹{{ Math.round(maxSpread).toLocaleString('en-IN') }}</span>
        </div>
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

    <div v-if="!chartData.length" class="empty">Not enough data yet.</div>
    <div v-else class="chart-frame">
      <svg
        :viewBox="`0 0 ${W} ${H}`"
        :width="W"
        :height="H"
        style="display:block"
        @mousemove="e => onMouseMove(e, e.currentTarget as SVGSVGElement)"
        @mouseleave="onMouseLeave"
      >
        <defs>
          <linearGradient id="occ-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="var(--series-2)" stop-opacity="0.3" />
            <stop offset="100%" stop-color="var(--series-2)" stop-opacity="0.02" />
          </linearGradient>
        </defs>
        <g :transform="`translate(${MARGIN.left},${MARGIN.top})`">
          <line
            v-for="tick in yTicks"
            :key="tick"
            x1="0" :x2="plotW"
            :y1="yPos(tick)" :y2="yPos(tick)"
            stroke="var(--gridline)" stroke-width="1"
          />
          <text
            v-for="tick in yTicks"
            :key="'y' + tick"
            x="-6" :y="yPos(tick)"
            text-anchor="end" dominant-baseline="middle"
            font-size="11" fill="var(--text-muted)"
          >₹{{ tick }}</text>
          <text
            v-for="date in xTicks"
            :key="'x' + date"
            :x="xPos(date)" :y="plotH + 18"
            text-anchor="middle" font-size="11" fill="var(--text-muted)"
          >{{ formatDate(date) }}</text>
          <!-- avg dashed reference -->
          <line
            :x1="0" :x2="plotW"
            :y1="yPos(avgSpread)" :y2="yPos(avgSpread)"
            stroke="var(--text-muted)" stroke-width="1" stroke-dasharray="4 3"
          />
          <path :d="areaPath" fill="url(#occ-fill)" />
          <path :d="linePath" fill="none" stroke="var(--series-2)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
          <template v-if="tooltip">
            <line
              :x1="tooltip.x - MARGIN.left" :x2="tooltip.x - MARGIN.left"
              y1="0" :y2="plotH"
              stroke="var(--text-muted)" stroke-width="1" stroke-dasharray="3 2"
            />
            <circle
              :cx="tooltip.x - MARGIN.left" :cy="tooltip.y - MARGIN.top"
              r="4" fill="var(--series-2)" stroke="var(--surface-1)" stroke-width="2"
            />
          </template>
        </g>
        <template v-if="tooltip">
          <g :transform="`translate(${tooltip.x + 10 > W - TOOLTIP_W - 4 ? tooltip.x - TOOLTIP_W - 8 : tooltip.x + 10},${Math.max(4, tooltip.y - 26)})`">
            <rect :width="TOOLTIP_W" :height="TOOLTIP_H" rx="6" fill="var(--surface-1)" stroke="var(--border)" />
            <text x="8" y="15" font-size="11" fill="var(--text-muted)">{{ formatDate(tooltip.date) }}</text>
            <text x="8" y="33" font-size="13" font-weight="600" fill="var(--text-primary)">₹{{ Math.round(tooltip.spread).toLocaleString('en-IN') }} spread</text>
          </g>
        </template>
      </svg>
    </div>
    <p class="footnote">Fee-adjusted spread on {{ currency }} {{ amount.toLocaleString('en-IN') }}. Dashed line = period average. Days with fewer than half of banks reporting are excluded.</p>
  </div>
</template>

<style scoped lang="scss">
.opp-cost {
  .opp-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }

  .opp-stats {
    display: flex;
    gap: 24px;
    flex-wrap: wrap;
  }

  .stat {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .stat-label {
    font-size: 11px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .stat-value {
    font-size: 20px;
    font-weight: 700;
    color: var(--text-primary);

    &.muted {
      font-size: 16px;
      font-weight: 500;
      color: var(--text-secondary);
    }
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
    padding: 5px 10px;
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

  .chart-frame {
    overflow-x: auto;
  }

  .empty {
    padding: 32px 0;
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
