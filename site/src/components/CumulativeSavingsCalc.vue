<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { BankSeries, FeesByBank } from "../types";
import { shortName } from "../bankPalette";

const props = defineProps<{
  series: BankSeries[];
  fees: FeesByBank;
  currency: string;
  amount: number;
  myBank?: string;
}>();

type RangeKey = "30d" | "90d" | "all";
const RANGES: { key: RangeKey; label: string; days: number | null }[] = [
  { key: "30d", label: "30 days", days: 30 },
  { key: "90d", label: "90 days", days: 90 },
  { key: "all", label: "All time", days: null },
];
const range = ref<RangeKey>("90d");

const bankSeries = computed(() => props.series.filter(s => s.category === "bank" && s.points.length > 0));
const bankNames = computed(() => bankSeries.value.map(s => s.name).sort((a, b) => a.localeCompare(b)));

const bankA = ref<string>(props.myBank ?? "");
const bankB = ref<string>("__best__");

watch(() => props.myBank, (val) => {
  if (!bankA.value && val) bankA.value = val;
}, { immediate: true });

watch(bankNames, (names) => {
  if (bankA.value && !names.includes(bankA.value)) bankA.value = "";
  if (bankB.value !== "__best__" && !names.includes(bankB.value)) bankB.value = "__best__";
});

watch(() => props.currency, () => {
  bankB.value = "__best__";
});

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

const qualifyingDays = computed(() => {
  const opt = RANGES.find(o => o.key === range.value);
  const cutoffStr = opt?.days != null
    ? (() => { const d = new Date(); d.setDate(d.getDate() - opt.days!); return d.toISOString().slice(0, 10); })()
    : null;

  const bs = bankSeries.value;
  const majorityThreshold = Math.floor(bs.length / 2) + 1;
  const dateMap = new Map<string, { bank: string; net: number }[]>();

  for (const s of bs) {
    for (const pt of s.points) {
      if (cutoffStr && pt.date < cutoffStr) continue;
      const entries = dateMap.get(pt.date) ?? [];
      entries.push({ bank: s.name, net: netReceive(s.name, pt.ttbuy, props.amount) });
      dateMap.set(pt.date, entries);
    }
  }

  return [...dateMap.entries()]
    .filter(([, entries]) => entries.length >= majorityThreshold)
    .map(([date, entries]) => ({
      date,
      entries,
      bestNet: Math.max(...entries.map(e => e.net)),
    }))
    .sort((a, b) => a.date.localeCompare(b.date));
});

const cumulativeData = computed(() => {
  if (!bankA.value) return [];
  let cumulative = 0;
  const result: { date: string; daily: number; cumulative: number }[] = [];

  for (const day of qualifyingDays.value) {
    const aEntry = day.entries.find(e => e.bank === bankA.value);
    if (!aEntry) continue;

    let bNet: number;
    if (bankB.value === "__best__") {
      bNet = day.bestNet;
    } else {
      const bEntry = day.entries.find(e => e.bank === bankB.value);
      if (!bEntry) continue;
      bNet = bEntry.net;
    }

    cumulative += bNet - aEntry.net;
    result.push({ date: day.date, daily: bNet - aEntry.net, cumulative });
  }
  return result;
});

const totalGain = computed(() => cumulativeData.value.at(-1)?.cumulative ?? 0);
const dayCount = computed(() => cumulativeData.value.length);
const perTransferAvg = computed(() => dayCount.value > 0 ? totalGain.value / dayCount.value : 0);

// SVG
const W = 960;
const H = 180;
const MARGIN = { top: 12, right: 16, bottom: 28, left: 64 };
const plotW = W - MARGIN.left - MARGIN.right;
const plotH = H - MARGIN.top - MARGIN.bottom;

const xDomain = computed<[number, number]>(() => {
  if (!cumulativeData.value.length) return [0, 1];
  const times = cumulativeData.value.map(d => new Date(d.date).getTime());
  return [Math.min(...times), Math.max(...times)];
});

const yDomain = computed<[number, number]>(() => {
  if (!cumulativeData.value.length) return [0, 1000];
  const vals = cumulativeData.value.map(d => d.cumulative);
  const min = Math.min(0, ...vals);
  const max = Math.max(0, ...vals);
  const absMax = Math.max(Math.abs(min), Math.abs(max)) || 1000;
  const step = absMax < 1000 ? 200 : absMax < 5000 ? 1000 : absMax < 20000 ? 5000 : absMax < 100000 ? 20000 : 50000;
  return [Math.floor((min * 1.15) / step) * step, Math.ceil((max * 1.15) / step) * step || step];
});

function xPos(date: string): number {
  const [min, max] = xDomain.value;
  const t = new Date(date).getTime();
  return max === min ? 0 : ((t - min) / (max - min)) * plotW;
}

function yPos(value: number): number {
  const [min, max] = yDomain.value;
  return max === min ? plotH / 2 : plotH - ((value - min) / (max - min)) * plotH;
}

const linePath = computed(() =>
  cumulativeData.value.map((pt, i) => `${i === 0 ? "M" : "L"}${xPos(pt.date).toFixed(1)},${yPos(pt.cumulative).toFixed(1)}`).join(" ")
);

const areaPath = computed(() => {
  const data = cumulativeData.value;
  if (!data.length) return "";
  const line = data.map((pt, i) => `${i === 0 ? "M" : "L"}${xPos(pt.date).toFixed(1)},${yPos(pt.cumulative).toFixed(1)}`).join(" ");
  const z = yPos(0).toFixed(1);
  return `${line} L${xPos(data[data.length - 1].date).toFixed(1)},${z} L${xPos(data[0].date).toFixed(1)},${z} Z`;
});

const lineColor = computed(() => totalGain.value >= 0 ? "var(--status-good)" : "var(--status-critical)");

const yTicks = computed<number[]>(() => {
  const [min, max] = yDomain.value;
  const absMax = Math.max(Math.abs(min), Math.abs(max)) || 1000;
  const step = absMax < 1000 ? 200 : absMax < 5000 ? 1000 : absMax < 20000 ? 5000 : absMax < 100000 ? 20000 : 50000;
  const ticks: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) ticks.push(Math.round(v));
  return ticks;
});

const xTicks = computed<string[]>(() => {
  const data = cumulativeData.value;
  if (!data.length) return [];
  if (data.length <= 5) return data.map(d => d.date);
  const indices = [0, Math.floor(data.length / 3), Math.floor((2 * data.length) / 3), data.length - 1];
  return [...new Set(indices.map(i => data[i].date))];
});

function formatDate(dateStr: string): string {
  const [, m, d] = dateStr.split("-").map(Number);
  return `${["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][m - 1]} ${d}`;
}

function formatInr(val: number): string {
  return `₹${Math.round(Math.abs(val)).toLocaleString('en-IN')}`;
}

function formatTickInr(val: number): string {
  const abs = Math.abs(val);
  const sign = val < 0 ? "−" : "";
  if (abs >= 100000) return `${sign}₹${Math.round(abs / 100000)}L`;
  if (abs >= 1000) return `${sign}₹${Math.round(abs / 1000)}k`;
  return `${sign}₹${Math.round(abs)}`;
}

const tooltip = ref<{ x: number; y: number; date: string; cumulative: number; daily: number } | null>(null);

function onMouseMove(e: MouseEvent, svg: SVGSVGElement) {
  const rect = svg.getBoundingClientRect();
  const plotX = ((e.clientX - rect.left) / rect.width) * W - MARGIN.left;
  const data = cumulativeData.value;
  if (plotX < 0 || plotX > plotW || !data.length) { tooltip.value = null; return; }
  const [min, max] = xDomain.value;
  const targetTime = min + (plotX / plotW) * (max - min);
  let closest = data[0];
  let minDist = Infinity;
  for (const pt of data) {
    const dist = Math.abs(new Date(pt.date).getTime() - targetTime);
    if (dist < minDist) { minDist = dist; closest = pt; }
  }
  tooltip.value = { x: MARGIN.left + xPos(closest.date), y: MARGIN.top + yPos(closest.cumulative), date: closest.date, cumulative: closest.cumulative, daily: closest.daily };
}

function onMouseLeave() { tooltip.value = null; }

const TOOLTIP_W = 160;
const TOOLTIP_H = 56;

const bankBLabel = computed(() => {
  if (bankB.value === "__best__") return "best available";
  return shortName(bankB.value);
});
</script>

<template>
  <div class="cumulative-savings">
    <div class="controls">
      <div class="bank-selectors">
        <div class="bank-select-group">
          <label class="select-label">Your bank</label>
          <select v-model="bankA" class="bank-select">
            <option value="" disabled>Choose bank…</option>
            <option v-for="name in bankNames" :key="name" :value="name">{{ shortName(name) }}</option>
          </select>
        </div>
        <span class="vs-arrow" aria-hidden="true">→</span>
        <div class="bank-select-group">
          <label class="select-label">Compare against</label>
          <select v-model="bankB" class="bank-select">
            <option value="__best__">Best available each day</option>
            <option
              v-for="name in bankNames"
              :key="name"
              :value="name"
              :disabled="name === bankA"
            >{{ shortName(name) }}</option>
          </select>
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

    <div v-if="!bankA" class="empty">Select your bank above to see potential savings.</div>
    <div v-else-if="!cumulativeData.length" class="empty">Not enough overlapping data for these banks in this period.</div>
    <template v-else>
      <div class="summary-row">
        <div class="summary-stat main" :class="totalGain >= 0 ? 'gain' : 'loss'">
          <span class="stat-label">Extra received with {{ bankBLabel }}</span>
          <span class="stat-value" :class="totalGain >= 0 ? 'positive' : 'negative'">
            {{ totalGain >= 0 ? "+" : "−" }}{{ formatInr(totalGain) }}
          </span>
          <span class="stat-sub">over {{ dayCount }} qualifying days</span>
        </div>
        <div class="summary-stat">
          <span class="stat-label">Per transfer average</span>
          <span class="stat-value small" :class="perTransferAvg >= 0 ? 'positive' : 'negative'">
            {{ perTransferAvg >= 0 ? "+" : "−" }}{{ formatInr(perTransferAvg) }}
          </span>
          <span class="stat-sub">on {{ currency }} {{ amount.toLocaleString('en-IN') }}</span>
        </div>
      </div>

      <div class="chart-frame">
        <svg
          :viewBox="`0 0 ${W} ${H}`"
          :width="W"
          :height="H"
          style="display:block"
          @mousemove="e => onMouseMove(e, e.currentTarget as SVGSVGElement)"
          @mouseleave="onMouseLeave"
        >
          <defs>
            <linearGradient id="cum-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" :stop-color="lineColor" stop-opacity="0.22" />
              <stop offset="100%" :stop-color="lineColor" stop-opacity="0.02" />
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
            <!-- zero baseline -->
            <line
              x1="0" :x2="plotW"
              :y1="yPos(0)" :y2="yPos(0)"
              stroke="var(--baseline)" stroke-width="1.5"
            />
            <text
              v-for="tick in yTicks"
              :key="'y' + tick"
              x="-6" :y="yPos(tick)"
              text-anchor="end" dominant-baseline="middle"
              font-size="11" fill="var(--text-muted)"
            >{{ formatTickInr(tick) }}</text>
            <text
              v-for="date in xTicks"
              :key="'x' + date"
              :x="xPos(date)" :y="plotH + 18"
              text-anchor="middle" font-size="11" fill="var(--text-muted)"
            >{{ formatDate(date) }}</text>
            <path :d="areaPath" fill="url(#cum-fill)" />
            <path :d="linePath" fill="none" :stroke="lineColor" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
            <template v-if="tooltip">
              <line
                :x1="tooltip.x - MARGIN.left" :x2="tooltip.x - MARGIN.left"
                y1="0" :y2="plotH"
                stroke="var(--text-muted)" stroke-width="1" stroke-dasharray="3 2"
              />
              <circle
                :cx="tooltip.x - MARGIN.left" :cy="tooltip.y - MARGIN.top"
                r="4" :fill="lineColor" stroke="var(--surface-1)" stroke-width="2"
              />
            </template>
          </g>
          <template v-if="tooltip">
            <g :transform="`translate(${tooltip.x + 10 > W - TOOLTIP_W - 4 ? tooltip.x - TOOLTIP_W - 8 : tooltip.x + 10},${Math.max(4, tooltip.y - 32)})`">
              <rect :width="TOOLTIP_W" :height="TOOLTIP_H" rx="6" fill="var(--surface-1)" stroke="var(--border)" />
              <text x="8" y="16" font-size="11" fill="var(--text-muted)">{{ formatDate(tooltip.date) }}</text>
              <text x="8" y="34" font-size="12" font-weight="600" :fill="lineColor">
                Cumulative: {{ tooltip.cumulative >= 0 ? "+" : "−" }}{{ formatInr(tooltip.cumulative) }}
              </text>
              <text x="8" y="50" font-size="11" fill="var(--text-muted)">
                This day: {{ tooltip.daily >= 0 ? "+" : "−" }}{{ formatInr(tooltip.daily) }}
              </text>
            </g>
          </template>
        </svg>
      </div>
      <p class="footnote">
        Assumes {{ currency }} {{ amount.toLocaleString('en-IN') }} per transfer, one transfer per trading day. Fee-adjusted where data is available. Amounts not received on days where your bank had no published rate are excluded.
      </p>
    </template>
  </div>
</template>

<style scoped lang="scss">
.cumulative-savings {
  .controls {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 20px;
    flex-wrap: wrap;
  }

  .bank-selectors {
    display: flex;
    align-items: flex-end;
    gap: 10px;
    flex-wrap: wrap;
  }

  .bank-select-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .select-label {
    font-size: 11px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .bank-select {
    padding: 6px 10px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--surface-1);
    color: var(--text-primary);
    font-size: 13px;
    font-family: inherit;
    cursor: pointer;
    min-width: 180px;

    &:focus {
      outline: 2px solid var(--accent);
      outline-offset: 1px;
    }
  }

  .vs-arrow {
    font-size: 16px;
    color: var(--text-muted);
    padding-bottom: 7px;
    flex-shrink: 0;
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

  .summary-row {
    display: flex;
    gap: 32px;
    align-items: flex-start;
    margin-bottom: 20px;
    flex-wrap: wrap;
  }

  .summary-stat {
    display: flex;
    flex-direction: column;
    gap: 2px;

    &.main {
      border-left: 3px solid var(--baseline);
      padding-left: 12px;

      &.gain { border-color: var(--status-good); }
      &.loss { border-color: var(--status-critical); }
    }
  }

  .stat-label {
    font-size: 11px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .stat-value {
    font-size: 26px;
    font-weight: 700;
    line-height: 1.1;
    font-variant-numeric: tabular-nums;
    font-family: ui-monospace, "Cascadia Code", "Roboto Mono", monospace;
    &.small { font-size: 20px; }
    &.positive { color: var(--status-good); }
    &.negative { color: var(--status-critical); }
  }

  .stat-sub {
    font-size: 12px;
    color: var(--text-secondary);
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
