<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { BankSeries } from "../types";
import { shortName, brandColor } from "../bankPalette";

const props = defineProps<{
  series: BankSeries[];
  currency: string;
}>();

type RangeKey = "30d" | "90d";
const RANGES: { key: RangeKey; label: string; days: number }[] = [
  { key: "30d", label: "30 days", days: 30 },
  { key: "90d", label: "90 days", days: 90 },
];
const range = ref<RangeKey>("90d");

const MAX_COMPARE = 5;

const midMarket = computed(() => props.series.find(s => s.name === "Mid-market"));
const bankSeries = computed(() => props.series.filter(s => s.category === "bank" && s.points.length > 0));

// Mid-market lookup: date → rate
const midLookup = computed(() => {
  const m = new Map<string, number>();
  for (const pt of midMarket.value?.points ?? []) m.set(pt.date, pt.ttbuy);
  return m;
});

const cutoffStr = computed(() => {
  const opt = RANGES.find(o => o.key === range.value)!;
  const d = new Date();
  d.setDate(d.getDate() - opt.days);
  return d.toISOString().slice(0, 10);
});

// Gap per bank per day: midmarket - bank (lower = more competitive)
interface GapPoint { date: string; gap: number; }
interface BankGap { name: string; color: string; points: GapPoint[]; avgGap: number; }

const bankGaps = computed<BankGap[]>(() => {
  const cutoff = cutoffStr.value;
  const mid = midLookup.value;
  if (!mid.size) return [];

  return bankSeries.value
    .map(s => {
      const points: GapPoint[] = [];
      for (const pt of s.points) {
        if (pt.date < cutoff) continue;
        const mRate = mid.get(pt.date);
        if (mRate == null) continue;
        points.push({ date: pt.date, gap: mRate - pt.ttbuy });
      }
      if (points.length < 3) return null;
      const avgGap = points.reduce((sum, p) => sum + p.gap, 0) / points.length;
      return { name: s.name, color: brandColor(s.name), points, avgGap };
    })
    .filter((b): b is BankGap => b !== null)
    .sort((a, b) => a.avgGap - b.avgGap); // best (smallest gap) first
});

// Compare mode: default to top 5 by smallest avg gap
const selected = ref<Set<string>>(new Set());

watch(bankGaps, (gaps) => {
  // Auto-select top 5 whenever data changes (range switch, currency switch)
  const top = gaps.slice(0, MAX_COMPARE).map(b => b.name);
  selected.value = new Set(top);
}, { immediate: true });

watch(() => props.currency, () => { selected.value = new Set(); });

function toggleBank(name: string) {
  const next = new Set(selected.value);
  if (next.has(name)) {
    if (next.size > 1) next.delete(name); // keep at least one
  } else if (next.size < MAX_COMPARE) {
    next.add(name);
  }
  selected.value = next;
}

const visibleGaps = computed(() =>
  bankGaps.value.filter(b => selected.value.has(b.name))
);

// SVG geometry
const W = 960;
const H = 280;
const MARGIN = { top: 16, right: 16, bottom: 30, left: 56 };
const plotW = W - MARGIN.left - MARGIN.right;
const plotH = H - MARGIN.top - MARGIN.bottom;

const allDates = computed(() => {
  const set = new Set<string>();
  for (const b of visibleGaps.value) for (const p of b.points) set.add(p.date);
  return [...set].sort();
});

const xDomain = computed<[number, number]>(() => {
  if (!allDates.value.length) return [0, 1];
  const times = allDates.value.map(d => new Date(d).getTime());
  return [Math.min(...times), Math.max(...times)];
});

const yDomain = computed<[number, number]>(() => {
  const vals = visibleGaps.value.flatMap(b => b.points.map(p => p.gap));
  if (!vals.length) return [-0.5, 2];
  const min = Math.min(0, ...vals);
  const max = Math.max(...vals);
  const pad = (max - min) * 0.15 || 0.5;
  const step = (max - min) < 1 ? 0.25 : (max - min) < 3 ? 0.5 : 1;
  return [Math.floor((min - pad) / step) * step, Math.ceil((max + pad) / step) * step];
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

function linePath(b: BankGap): string {
  return b.points.map((p, i) => `${i === 0 ? "M" : "L"}${xPos(p.date).toFixed(1)},${yPos(p.gap).toFixed(1)}`).join(" ");
}

const yStep = computed(() => {
  const [min, max] = yDomain.value;
  const r = max - min;
  return r < 1 ? 0.25 : r < 3 ? 0.5 : r < 8 ? 1 : 2;
});

const yTicks = computed<number[]>(() => {
  const [min, max] = yDomain.value;
  const step = yStep.value;
  const ticks: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) {
    ticks.push(Math.round(v * 100) / 100);
  }
  return ticks;
});

const xTicks = computed<string[]>(() => {
  const dates = allDates.value;
  if (!dates.length) return [];
  if (dates.length <= 6) return dates;
  const step = Math.floor(dates.length / 5);
  const ticks: string[] = [];
  for (let i = 0; i < dates.length; i += step) ticks.push(dates[i]);
  if (ticks[ticks.length - 1] !== dates[dates.length - 1]) ticks.push(dates[dates.length - 1]);
  return ticks;
});

const zeroY = computed(() => yPos(0));

function formatDate(d: string): string {
  const [, m, day] = d.split("-").map(Number);
  return `${["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][m - 1]} ${day}`;
}

// Tooltip
const tooltip = ref<{ x: number; y: number; date: string; items: { name: string; color: string; gap: number }[] } | null>(null);

function onMouseMove(e: MouseEvent, svg: SVGSVGElement) {
  const rect = svg.getBoundingClientRect();
  const plotX = ((e.clientX - rect.left) / rect.width) * W - MARGIN.left;
  const dates = allDates.value;
  if (plotX < 0 || plotX > plotW || !dates.length) { tooltip.value = null; return; }

  const [min, max] = xDomain.value;
  const targetTime = min + (plotX / plotW) * (max - min);
  let closestDate = dates[0];
  let minDist = Infinity;
  for (const d of dates) {
    const dist = Math.abs(new Date(d).getTime() - targetTime);
    if (dist < minDist) { minDist = dist; closestDate = d; }
  }

  const items = visibleGaps.value
    .map(b => {
      const pt = b.points.find(p => p.date === closestDate);
      return pt ? { name: b.name, color: b.color, gap: pt.gap } : null;
    })
    .filter((i): i is { name: string; color: string; gap: number } => i !== null)
    .sort((a, b) => a.gap - b.gap);

  if (!items.length) { tooltip.value = null; return; }

  const avgGapY = items.reduce((s, i) => s + yPos(i.gap), 0) / items.length;
  tooltip.value = { x: MARGIN.left + xPos(closestDate), y: MARGIN.top + avgGapY, date: closestDate, items };
}

function onMouseLeave() { tooltip.value = null; }

const TOOLTIP_W = 170;
</script>

<template>
  <div class="markup-trend">
    <div v-if="!midMarket" class="empty">Mid-market data not available yet.</div>
    <template v-else>
      <div class="mt-header">
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

      <div v-if="!bankGaps.length" class="empty">No days with both bank and mid-market data in this period.</div>
      <template v-else>
        <!-- Bank picker chips -->
        <div class="picker-row">
          <span class="picker-label">Banks shown ({{ selected.size }}/{{ MAX_COMPARE }}):</span>
          <div class="chips" role="group" aria-label="Select banks">
            <button
              v-for="b in bankGaps"
              :key="b.name"
              type="button"
              class="chip"
              :class="{
                selected: selected.has(b.name),
                maxed: !selected.has(b.name) && selected.size >= MAX_COMPARE,
              }"
              :style="selected.has(b.name) ? { '--chip-color': b.color } : {}"
              :disabled="!selected.has(b.name) && selected.size >= MAX_COMPARE"
              :aria-pressed="selected.has(b.name)"
              @click="toggleBank(b.name)"
            >
              <span class="chip-dot" :style="{ background: b.color }"></span>
              {{ shortName(b.name) }}
              <span class="chip-avg">₹{{ b.avgGap.toFixed(2) }}</span>
            </button>
          </div>
        </div>

        <div v-if="!visibleGaps.length" class="empty">Select at least one bank.</div>
        <div v-else class="chart-frame">
          <svg
            :viewBox="`0 0 ${W} ${H}`"
            :width="W"
            :height="H"
            style="display:block"
            @mousemove="e => onMouseMove(e, e.currentTarget as SVGSVGElement)"
            @mouseleave="onMouseLeave"
          >
            <g :transform="`translate(${MARGIN.left},${MARGIN.top})`">
              <!-- Gridlines -->
              <line
                v-for="tick in yTicks"
                :key="tick"
                x1="0" :x2="plotW"
                :y1="yPos(tick)" :y2="yPos(tick)"
                stroke="var(--gridline)" stroke-width="1"
              />
              <!-- Zero baseline = on par with mid-market -->
              <line
                x1="0" :x2="plotW"
                :y1="zeroY" :y2="zeroY"
                stroke="var(--baseline)" stroke-width="1.5"
              />
              <text
                :x="-4" :y="zeroY"
                text-anchor="end" dominant-baseline="middle"
                font-size="10" fill="var(--text-muted)"
              >0</text>
              <!-- Y labels -->
              <text
                v-for="tick in yTicks.filter(t => t !== 0)"
                :key="'y' + tick"
                x="-6" :y="yPos(tick)"
                text-anchor="end" dominant-baseline="middle"
                font-size="11" fill="var(--text-muted)"
              >₹{{ tick }}</text>
              <!-- X labels -->
              <text
                v-for="date in xTicks"
                :key="'x' + date"
                :x="xPos(date)" :y="plotH + 18"
                text-anchor="middle" font-size="11" fill="var(--text-muted)"
              >{{ formatDate(date) }}</text>
              <!-- Bank lines -->
              <path
                v-for="b in visibleGaps"
                :key="b.name"
                :d="linePath(b)"
                fill="none"
                :stroke="b.color"
                stroke-width="2"
                stroke-linejoin="round"
                stroke-linecap="round"
                opacity="0.85"
              />
              <!-- Crosshair -->
              <template v-if="tooltip">
                <line
                  :x1="tooltip.x - MARGIN.left" :x2="tooltip.x - MARGIN.left"
                  y1="0" :y2="plotH"
                  stroke="var(--text-muted)" stroke-width="1" stroke-dasharray="3 2"
                />
              </template>
            </g>
            <!-- Tooltip -->
            <template v-if="tooltip">
              <g :transform="`translate(${tooltip.x + 10 > W - TOOLTIP_W - 4 ? tooltip.x - TOOLTIP_W - 8 : tooltip.x + 10},${Math.max(4, tooltip.y - (tooltip.items.length * 16 + 20) / 2)})`">
                <rect
                  :width="TOOLTIP_W"
                  :height="tooltip.items.length * 18 + 22"
                  rx="6"
                  fill="var(--surface-1)"
                  stroke="var(--border)"
                />
                <text x="8" y="15" font-size="11" fill="var(--text-muted)">{{ formatDate(tooltip.date) }}</text>
                <g v-for="(item, idx) in tooltip.items" :key="item.name" :transform="`translate(0,${20 + idx * 18})`">
                  <circle cx="14" cy="8" r="4" :fill="item.color" />
                  <text x="24" y="12" font-size="12" fill="var(--text-primary)">
                    {{ shortName(item.name) }}: ₹{{ item.gap.toFixed(2) }}
                  </text>
                </g>
              </g>
            </template>
          </svg>
        </div>
        <p class="footnote">
          Gap = mid-market rate − bank's TT Buy rate. Lower gap means the bank offers a more competitive rate.
          Zero line = on par with mid-market. Only days where mid-market data is available are plotted.
        </p>
      </template>
    </template>
  </div>
</template>

<style scoped lang="scss">
.markup-trend {
  .mt-header {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 14px;
  }

  .range-filter {
    display: flex;
    gap: 4px;
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

  .picker-row {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 14px;
    flex-wrap: wrap;
  }

  .picker-label {
    font-size: 12px;
    color: var(--text-muted);
    flex-shrink: 0;
    padding-top: 4px;
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 8px;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: none;
    font-size: 12px;
    font-family: inherit;
    color: var(--text-secondary);
    cursor: pointer;
    white-space: nowrap;
    transition: background 60ms ease, border-color 60ms ease, color 60ms ease, opacity 60ms ease;

    &:hover:not(:disabled) { background: var(--page-plane); color: var(--text-primary); }
    &:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

    &.selected {
      border-color: var(--chip-color, var(--accent));
      background: color-mix(in srgb, var(--chip-color, var(--accent)) 14%, transparent);
      color: var(--text-primary);
      font-weight: 500;
    }

    &.maxed { opacity: 0.3; cursor: not-allowed; }
  }

  .chip-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .chip-avg {
    font-size: 11px;
    color: var(--text-muted);
    margin-left: 2px;
  }

  .chip.selected .chip-avg { color: inherit; opacity: 0.75; }

  .chart-frame { overflow-x: auto; }

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
