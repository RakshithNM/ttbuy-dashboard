<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { BankSeries } from "../types";
import { shortName } from "../bankPalette";
import { bisectNearest, createLinearScale, createTimeScale, downsampleDates, linePathFor, splitByGap } from "../chartScales";

const props = defineProps<{
  series: BankSeries[];
  currency: string;
}>();

type RangeKey = "30d" | "90d";
const RANGES: { key: RangeKey; label: string; days: number }[] = [
  { key: "30d", label: "30 days", days: 30 },
  { key: "90d", label: "90 days", days: 90 },
];
// Controlled by the parent, which renders the range buttons next to the
// panel title — same pattern as LineChart's `v-model:show-table`.
const range = defineModel<RangeKey>("range", { default: "30d" });

const MAX_COMPARE = 5;
const MIN_COMPARE = 2; // ranking is meaningless with fewer than two banks

const bankSeries = computed(() => props.series.filter(s => s.category === "bank" && s.points.length > 0));

const cutoffStr = computed(() => {
  const opt = RANGES.find(o => o.key === range.value)!;
  const d = new Date();
  d.setDate(d.getDate() - opt.days);
  return d.toISOString().slice(0, 10);
});

interface BankAvg { name: string; color: string; avgRate: number; }

// All banks with data in range, sorted by average rate — drives both the
// picker chip order and the default top-5 selection.
const bankAverages = computed<BankAvg[]>(() => {
  const cutoff = cutoffStr.value;
  return bankSeries.value
    .map(s => {
      const pts = s.points.filter(p => p.date >= cutoff);
      if (!pts.length) return null;
      const avgRate = pts.reduce((sum, p) => sum + p.ttbuy, 0) / pts.length;
      return { name: s.name, color: s.color, avgRate };
    })
    .filter((b): b is BankAvg => b !== null)
    .sort((a, b) => b.avgRate - a.avgRate);
});

const selected = ref<Set<string>>(new Set());

watch(bankAverages, (banks) => {
  // Auto-select top 5 whenever data changes (range switch, currency switch)
  const top = banks.slice(0, MAX_COMPARE).map(b => b.name);
  selected.value = new Set(top);
}, { immediate: true });

watch(() => props.currency, () => { selected.value = new Set(); });

function toggleBank(name: string) {
  const next = new Set(selected.value);
  if (next.has(name)) {
    if (next.size > MIN_COMPARE) next.delete(name);
  } else if (next.size < MAX_COMPARE) {
    next.add(name);
  }
  selected.value = next;
}

const selectedSeries = computed(() => bankSeries.value.filter(s => selected.value.has(s.name)));

// date -> entries reporting that day, from ALL banks (not just the ones
// currently shown) — rank has to be each bank's true standing among every
// bank that reported, not just among whichever subset happens to be picked.
const dailyEntries = computed(() => {
  const cutoff = cutoffStr.value;
  const byDate = new Map<string, { name: string; color: string; rate: number }[]>();
  for (const s of bankSeries.value) {
    for (const pt of s.points) {
      if (pt.date < cutoff) continue;
      const list = byDate.get(pt.date) ?? [];
      list.push({ name: s.name, color: s.color, rate: pt.ttbuy });
      byDate.set(pt.date, list);
    }
  }
  return byDate;
});

// A date only counts toward ranking if a majority of all banks reported —
// same quorum convention as AllTimeLeaderboard.vue/MyBankPanel.vue, so a
// rank isn't computed from a handful of stragglers.
const majorityThreshold = computed(() => Math.floor(bankSeries.value.length / 2) + 1);

const qualifyingDates = computed<string[]>(() =>
  [...dailyEntries.value.entries()]
    .filter(([, entries]) => entries.length >= majorityThreshold.value)
    .map(([date]) => date)
    .sort()
);

interface RankPoint { date: string; rank: number; rate: number; }

// Absolute rank among all reporting banks that day.
const rankPointsByBank = computed<Map<string, RankPoint[]>>(() => {
  const out = new Map<string, RankPoint[]>();
  for (const date of qualifyingDates.value) {
    const entries = [...dailyEntries.value.get(date)!].sort((a, b) => b.rate - a.rate);
    entries.forEach((e, i) => {
      const arr = out.get(e.name) ?? [];
      arr.push({ date, rank: i + 1, rate: e.rate });
      out.set(e.name, arr);
    });
  }
  return out;
});

const maxRank = computed(() =>
  Math.max(1, ...qualifyingDates.value.map(d => dailyEntries.value.get(d)!.length))
);

// Only the selected banks get a line drawn, but each line's rank values
// come from the full-universe ranking above.
const rankedLines = computed(() =>
  selectedSeries.value
    .map(s => ({ name: s.name, color: s.color, points: rankPointsByBank.value.get(s.name) ?? [] }))
    .filter(l => l.points.length > 0)
);

// SVG geometry — extra right margin reserved for end-of-line bank labels.
const W = 960;
const H = 320;
const MARGIN = { top: 16, right: 100, bottom: 30, left: 40 };
const plotW = W - MARGIN.left - MARGIN.right;
const plotH = H - MARGIN.top - MARGIN.bottom;

const xDomain = computed<[number, number]>(() => {
  if (!qualifyingDates.value.length) return [0, 1];
  const times = qualifyingDates.value.map(d => new Date(d).getTime());
  return [Math.min(...times), Math.max(...times)];
});

const xScaleD3 = computed(() => createTimeScale(xDomain.value, [0, plotW]));
// Not inverted, unlike the rate charts — rank 1 sits at the top of the plot.
const yScaleD3 = computed(() => createLinearScale([1, maxRank.value], [0, plotH]));

function xPos(date: string): number {
  const [min, max] = xDomain.value;
  return max === min ? 0 : xScaleD3.value(new Date(date).getTime());
}

function yPos(rank: number): number {
  return maxRank.value <= 1 ? plotH / 2 : yScaleD3.value(rank);
}

function linePath(points: RankPoint[]): string {
  return splitByGap(points)
    .map(seg => linePathFor(seg, (p) => xPos(p.date), (p) => yPos(p.rank)))
    .join(" ");
}

function lastPoint(points: RankPoint[]): RankPoint | null {
  return points.length ? points[points.length - 1] : null;
}

// Rank now spans every bank (up to ~20+), not just the handful shown — one
// gridline per integer would be unreadable past a single digit, so thin
// them out to every 5th once there's more than a few.
const yTicks = computed<number[]>(() => {
  const max = maxRank.value;
  if (max <= 8) return Array.from({ length: max }, (_, i) => i + 1);
  const ticks = [1];
  for (let v = 5; v < max; v += 5) ticks.push(v);
  if (ticks[ticks.length - 1] !== max) ticks.push(max);
  return ticks;
});
const xTicks = computed<string[]>(() => downsampleDates(qualifyingDates.value, 5));

function formatDate(dateStr: string): string {
  const [, m, d] = dateStr.split("-").map(Number);
  return `${["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][m - 1]} ${d}`;
}

// Tooltip
const tooltip = ref<{ x: number; y: number; date: string; items: { name: string; color: string; rank: number; rate: number }[] } | null>(null);

function onMouseMove(e: MouseEvent, svg: SVGSVGElement) {
  const rect = svg.getBoundingClientRect();
  const plotX = ((e.clientX - rect.left) / rect.width) * W - MARGIN.left;
  const dates = qualifyingDates.value;
  if (plotX < 0 || plotX > plotW || !dates.length) { tooltip.value = null; return; }

  const targetTime = xScaleD3.value.invert(plotX).getTime();
  const closestDate = bisectNearest(dates, (d) => new Date(d).getTime(), targetTime);
  if (closestDate === undefined) { tooltip.value = null; return; }

  // Only the plotted (selected) banks, each with its already-computed
  // absolute rank for this date — not every bank in the full ranking.
  const items = rankedLines.value
    .map((line) => {
      const point = line.points.find((p) => p.date === closestDate);
      return point ? { name: line.name, color: line.color, rank: point.rank, rate: point.rate } : null;
    })
    .filter((i): i is { name: string; color: string; rank: number; rate: number } => i !== null)
    .sort((a, b) => a.rank - b.rank);
  if (!items.length) { tooltip.value = null; return; }

  const midY = items.reduce((s, it) => s + yPos(it.rank), 0) / items.length;
  tooltip.value = { x: MARGIN.left + xPos(closestDate), y: MARGIN.top + midY, date: closestDate, items };
}

function onMouseLeave() { tooltip.value = null; }

const TOOLTIP_W = 190;
</script>

<template>
  <div class="rank-bump">
    <div v-if="!bankAverages.length" class="empty">Not enough data in this period.</div>
    <template v-else>
      <div class="picker-row">
        <span class="picker-label">Banks shown ({{ selected.size }}/{{ MAX_COMPARE }}):</span>
        <div class="chips" role="group" aria-label="Select banks">
          <button
            v-for="b in bankAverages"
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
          </button>
        </div>
      </div>

      <div v-if="!rankedLines.length" class="empty">Not enough overlapping data for the selected banks in this period.</div>
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
              x="-10" :y="yPos(tick)"
              text-anchor="end" dominant-baseline="middle"
              font-size="11" fill="var(--text-muted)"
            >#{{ tick }}</text>
            <text
              v-for="date in xTicks"
              :key="'x' + date"
              :x="xPos(date)" :y="plotH + 18"
              text-anchor="middle" font-size="11" fill="var(--text-muted)"
            >{{ formatDate(date) }}</text>

            <g v-for="line in rankedLines" :key="line.name">
              <path
                :d="linePath(line.points)"
                fill="none"
                :stroke="line.color"
                stroke-width="2"
                stroke-linejoin="round"
                stroke-linecap="round"
              />
              <circle
                v-for="p in line.points"
                :key="`${line.name}-${p.date}`"
                :cx="xPos(p.date)" :cy="yPos(p.rank)"
                r="3" :fill="line.color"
              />
              <template v-if="lastPoint(line.points)">
                <circle
                  :cx="xPos(lastPoint(line.points)!.date)" :cy="yPos(lastPoint(line.points)!.rank)"
                  r="4.5" :fill="line.color" stroke="var(--surface-1)" stroke-width="2"
                />
                <text
                  :x="xPos(lastPoint(line.points)!.date) + 9" :y="yPos(lastPoint(line.points)!.rank) + 4"
                  font-size="12" fill="var(--text-secondary)"
                >{{ shortName(line.name) }} #{{ lastPoint(line.points)!.rank }}</text>
              </template>
            </g>

            <template v-if="tooltip">
              <line
                :x1="tooltip.x - MARGIN.left" :x2="tooltip.x - MARGIN.left"
                y1="0" :y2="plotH"
                stroke="var(--text-muted)" stroke-width="1" stroke-dasharray="3 2"
              />
            </template>
          </g>

          <template v-if="tooltip">
            <g :transform="`translate(${tooltip.x + 10 > W - TOOLTIP_W - 4 ? tooltip.x - TOOLTIP_W - 8 : tooltip.x + 10},${Math.max(4, tooltip.y - (tooltip.items.length * 18 + 22) / 2)})`">
              <rect :width="TOOLTIP_W" :height="tooltip.items.length * 18 + 22" rx="6" fill="var(--surface-1)" stroke="var(--border)" />
              <text x="8" y="15" font-size="11" fill="var(--text-muted)">{{ formatDate(tooltip.date) }}</text>
              <g v-for="(item, idx) in tooltip.items" :key="item.name" :transform="`translate(0,${20 + idx * 18})`">
                <circle cx="14" cy="8" r="4" :fill="item.color" />
                <text x="24" y="12" font-size="12" fill="var(--text-primary)">#{{ item.rank }} {{ shortName(item.name) }} · ₹{{ item.rate.toFixed(2) }}</text>
              </g>
            </g>
          </template>
        </svg>
      </div>
      <p class="footnote">
        Rank is each bank's actual standing among all {{ bankSeries.length }} banks that day, by TT Buy rate — not just among the ones shown. A day only counts if a majority of all banks reported a rate; a bank's line breaks across days it didn't.
      </p>
    </template>
  </div>
</template>

<style scoped lang="scss">
.rank-bump {
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
