<script setup lang="ts">
import { computed, ref } from "vue";
import type { BankSeries, FeesByBank, FeeSlab } from "../types";
import { shortName, sourceUrl } from "../bankPalette";
import { currencySymbol } from "../currencies";

const props = defineProps<{
  series: BankSeries[];
  currency: string;
  fees: FeesByBank;
  consistency: { bank: string; count: number; total: number; since: string | null } | null;
  dowInsight: { day: string; diffPaise: number } | null;
  range: string;
  todaySignal: {
    todayBest: number;
    avgBest: number;
    daysCount: number;
    direction: "above" | "below" | "near";
    trend: "up" | "down" | "flat";
  } | null;
  stableBank: {
    bank: string;
    color: string;
    variation: number;
    runner: { bank: string; variation: number } | null;
    topN: number;
  } | null;
}>();

const statPrefix = computed(() => {
  const map: Record<string, string> = {
    "7d": "7D", "30d": "30D", "90d": "90D", "1y": "1Y", "all": "All-time",
  };
  return map[props.range] ?? "Period";
});

const MONTHS_SHORT = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const sinceLabel = computed(() => {
  const since = props.consistency?.since;
  if (!since) return null;
  const [, m, d] = since.split("-").map(Number);
  return `${MONTHS_SHORT[m - 1]} ${d}`;
});

const amount = defineModel<number>("amount", { default: 1000 });
const safeAmount = computed(() => {
  const n = Number(amount.value);
  return Number.isFinite(n) && n > 0 ? n : 0;
});

interface DataRow {
  bank: string;
  color: string;
  wrapped: boolean;
  category: "bank" | "platform";
  hasData: true;
  ttbuy: number;
  date: string;
  // Straight rate × amount conversion, before any fee.
  grossReceive: number;
  // Approximate flat fee for the standard/individual case, in rupees — 0
  // when confirmed free or when unknown (see feeUnknown).
  feeInr: number;
  // True when we don't have a confirmed fee for this bank — netReceive is
  // then just grossReceive (best case, not a guarantee), and the UI marks
  // it as approximate rather than silently treating "unknown" as "free".
  feeUnknown: boolean;
  netReceive: number;
  // Change vs the previous calendar day's rate; null when the previous
  // scraped point isn't from the day right before (a bank missed a day, or
  // this is the first point on record) — showing a delta across a gap would
  // misrepresent it as a single day's move.
  delta: number | null;
  // Rupees you'd net less than the best bank, at the chosen amount — 0 for
  // the best bank itself. Based on netReceive, not the raw TT Buy rate, so
  // a better rate can still lose to a lower-fee bank here.
  gapToBest: number;
}

interface EmptyRow {
  bank: string;
  color: string;
  wrapped: boolean;
  category: "bank" | "platform";
  hasData: false;
}

type Row = DataRow | EmptyRow;

function formatDate(iso: string): string {
  const [, month, day] = iso.split("-").map(Number);
  const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return `${MONTHS[month - 1]} ${day}`;
}

const hasInvalidAmount = computed(() => {
  const n = Number(amount.value);
  return !Number.isFinite(n) || n <= 0;
});

function feeFromSlabs(slabs: FeeSlab[], grossInr: number): number {
  for (const s of slabs) {
    if (s.up_to === null || grossInr <= s.up_to) return s.fee_inr;
  }
  return 0;
}

function isPreviousCalendarDay(earlierDate: string, laterDate: string): boolean {
  const earlier = new Date(`${earlierDate}T00:00:00Z`);
  const later = new Date(`${laterDate}T00:00:00Z`);
  const diffDays = (later.getTime() - earlier.getTime()) / 86_400_000;
  return diffDays === 1;
}

const rows = computed<Row[]>(() => {
  const bankDataRows: Omit<DataRow, "gapToBest">[] = [];
  const bankEmptyRows: EmptyRow[] = [];
  const platformDataRows: Omit<DataRow, "gapToBest">[] = [];
  const platformEmptyRows: EmptyRow[] = [];

  for (const s of props.series) {
    const isPlatformRow = s.category === "platform";
    const last = s.points[s.points.length - 1];
    if (!last) {
      const emptyRow: EmptyRow = { bank: s.name, color: s.color, wrapped: s.wrapped, category: s.category, hasData: false };
      if (isPlatformRow) platformEmptyRows.push(emptyRow);
      else bankEmptyRows.push(emptyRow);
      continue;
    }
    const prev = s.points.length >= 2 ? s.points[s.points.length - 2] : null;
    const showDelta = prev !== null && isPreviousCalendarDay(prev.date, last.date);
    // Platforms credit the full converted amount to the recipient (sender pays
    // the platform fee on their side), so feeInr=0 and feeUnknown=false.
    const fee = isPlatformRow ? null : props.fees[s.name];
    const grossReceive = last.ttbuy * safeAmount.value;
    const feeUnknown = isPlatformRow ? false : (!fee?.fee_slabs && fee?.fee_inr == null);
    const feeInr = isPlatformRow ? 0 : (
      fee?.fee_slabs ? feeFromSlabs(fee.fee_slabs, grossReceive) : (fee?.fee_inr ?? 0)
    );
    const row: Omit<DataRow, "gapToBest"> = {
      bank: s.name,
      color: s.color,
      wrapped: s.wrapped,
      category: s.category,
      hasData: true,
      ttbuy: last.ttbuy,
      date: last.date,
      grossReceive,
      feeInr,
      feeUnknown,
      netReceive: Math.max(0, grossReceive - feeInr),
      delta: showDelta ? last.ttbuy - prev!.ttbuy : null,
    };
    if (isPlatformRow) platformDataRows.push(row);
    else bankDataRows.push(row);
  }

  // Banks: ranked by what you'd actually walk away with (rate minus fee).
  // Banks with no data sort after every bank that has a rate to show.
  bankDataRows.sort((a, b) => b.netReceive - a.netReceive);
  const bestBankNet = bankDataRows[0]?.netReceive ?? 0;
  const banksWithGap = bankDataRows.map((r) => ({ ...r, gapToBest: bestBankNet - r.netReceive }));

  // Platforms: sorted by netReceive just like banks; gapToBest is vs the best
  // bank so users can see how each platform compares to the bank leader.
  platformDataRows.sort((a, b) => b.netReceive - a.netReceive);
  const platformsWithGap = platformDataRows.map((r) => ({ ...r, gapToBest: bestBankNet - r.netReceive }));

  return [...banksWithGap, ...bankEmptyRows, ...platformsWithGap, ...platformEmptyRows];
});

const bestBank = computed(() => rows.value.find((r) => r.hasData && r.category === "bank")?.bank ?? null);
const bestPlatform = computed(() => rows.value.find((r) => r.hasData && r.category === "platform")?.bank ?? null);

// Stale = bank's last date is behind the freshest date seen across all banks.
// This fires only when some banks are behind others, not when the whole
// scraper hasn't run yet (in which case every bank shows the same old date).
const latestDate = computed(() => {
  const dates = rows.value.filter(r => r.hasData && r.category === "bank").map(r => (r as DataRow).date);
  return dates.length ? [...dates].sort().at(-1)! : null;
});

const staleBanks = computed<DataRow[]>(() => {
  if (!latestDate.value) return [];
  return rows.value.filter((r): r is DataRow => r.hasData && r.category === "bank" && r.date < latestDate.value!);
});

const rateSpread = computed(() => {
  const bankDataRows = rows.value.filter((r): r is DataRow => r.hasData && r.category === "bank");
  if (bankDataRows.length < 2) return null;
  const best = bankDataRows[0];
  const worst = bankDataRows[bankDataRows.length - 1];
  const rateGap = best.ttbuy - worst.ttbuy;
  if (rateGap <= 0.004) return null;
  const receiveGap = safeAmount.value > 0 ? best.netReceive - worst.netReceive : null;
  return { rateGap, receiveGap };
});

const firstPlatformIndex = computed(() => rows.value.findIndex((r) => r.category === "platform"));

function formatInr(value: number): string {
  return value.toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

function deltaDirection(delta: number): "up" | "down" | "flat" {
  if (delta > 0.004) return "up";
  if (delta < -0.004) return "down";
  return "flat";
}

// Fee tooltip is positioned via getBoundingClientRect + position:fixed rather
// than a plain CSS :hover reveal, so it isn't clipped by .table-wrap's
// overflow:auto (needed for horizontal scroll on narrow screens) — same
// approach LineChart.vue uses for its own tooltip for the same reason.
const activeFeeBank = ref<string | null>(null);
const feeTooltipPos = ref({ top: 0, left: 0 });
let hideFeeTimer: ReturnType<typeof setTimeout> | null = null;

function cancelHideFeeTooltip() {
  if (hideFeeTimer !== null) {
    clearTimeout(hideFeeTimer);
    hideFeeTimer = null;
  }
}

function scheduleHideFeeTooltip() {
  cancelHideFeeTooltip();
  hideFeeTimer = setTimeout(() => {
    activeFeeBank.value = null;
  }, 100);
}

function showFeeTooltip(bank: string, evt: Event) {
  cancelHideFeeTooltip();
  const target = evt.currentTarget as HTMLElement;
  const rect = target.getBoundingClientRect();
  const tooltipWidth = 280;
  const left = Math.min(rect.left, window.innerWidth - tooltipWidth - 12);
  feeTooltipPos.value = { top: rect.bottom + 6, left: Math.max(12, left) };
  activeFeeBank.value = bank;
}

// Click/tap needs its own toggle rather than relying on :focus — clicking a
// <button> doesn't reliably move keyboard focus to it (WebKit in particular
// never does), so a focus-only "open" handler leaves click/tap silently
// doing nothing. Native buttons already fire "click" on Enter/Space, so this
// alone covers keyboard activation too — no separate @focus handler needed
// (which previously caused a double-toggle: click also focusing the button
// in browsers that do focus on click, opening then immediately re-closing).
function toggleFeeTooltip(bank: string, evt: Event) {
  if (activeFeeBank.value === bank) {
    activeFeeBank.value = null;
  } else {
    showFeeTooltip(bank, evt);
  }
}

const feeTooltipStyle = computed(() => ({
  top: `${feeTooltipPos.value.top}px`,
  left: `${feeTooltipPos.value.left}px`,
}));

const activeFee = computed(() => (activeFeeBank.value ? props.fees[activeFeeBank.value] ?? null : null));

const expandedBank = ref<string | null>(null);

function toggleExpand(bank: string, evt: Event) {
  // Don't toggle if clicking the fee-info button itself (it has its own hover/click logic)
  const target = evt.target as HTMLElement;
  if (target.closest('.fee-info') || target.closest('a')) return;
  expandedBank.value = expandedBank.value === bank ? null : bank;
}

interface BankStats {
  avg: number | null;
  best: number | null;
  worst: number | null;
  sparkline: string;
}

const bankStats = computed(() => {
  const map = new Map<string, BankStats>();
  for (const s of props.series) {
    if (s.points.length === 0) continue;
    let sum = 0, min = Infinity, max = -Infinity;
    for (const p of s.points) {
      sum += p.ttbuy;
      if (p.ttbuy < min) min = p.ttbuy;
      if (p.ttbuy > max) max = p.ttbuy;
    }
    const avg = sum / s.points.length;

    const w = 120, h = 44, pad = 2;
    let sparkline = "";
    if (s.points.length > 1) {
      const yRange = max > min ? (max - min) : 1;
      const pts = s.points.map((p, i) => {
        const x = pad + (i / (s.points.length - 1)) * (w - pad * 2);
        const y = pad + (1 - (p.ttbuy - min) / yRange) * (h - pad * 2);
        return `${x},${y}`;
      });
      sparkline = `M ${pts.join(" L ")}`;
    }

    map.set(s.name, { avg, best: max, worst: min, sparkline });
  }
  return map;
});
</script>

<template>
  <div class="best-rate">
    <div class="amount-control">
      <label for="remit-amount">If you receive</label>
      <div class="amount-field" :class="{ invalid: hasInvalidAmount }">
        <span class="prefix">{{ currencySymbol(currency) }}</span>
        <input id="remit-amount" v-model.number="amount" type="number" min="1" step="1" inputmode="decimal" class="amount-input" :aria-invalid="hasInvalidAmount ? 'true' : undefined" />
      </div>
      <span class="suffix">{{ currency }}, here's what each bank credits you after fees (where known)</span>
    </div>

    <div v-if="rateSpread" class="spread-callout" role="note">
      <svg class="spread-icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
        <path d="M8 2v12M5 5l3-3 3 3M5 11l3 3 3-3" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <span>
        Best bank beats worst by
        <span class="spread-rate">₹{{ rateSpread.rateGap.toFixed(2) }}/{{ currency }}</span>
        <template v-if="rateSpread.receiveGap !== null">
          — <span class="spread-amount">₹{{ formatInr(rateSpread.receiveGap) }} more</span>
          on {{ currencySymbol(currency) }}{{ formatInr(safeAmount) }}
        </template>
      </span>
    </div>

    <div v-if="todaySignal" class="today-callout" :class="todaySignal.direction" role="note">
      <svg class="today-icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
        <polyline v-if="todaySignal.direction === 'above'" points="1,12 5,7 9,9 15,3" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
        <polyline v-else-if="todaySignal.direction === 'below'" points="1,4 5,9 9,7 15,13" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
        <polyline v-else points="1,8 5,6 9,10 15,8" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <span>
        Today's best {{ currency }} rate
        <strong>₹{{ todaySignal.todayBest.toFixed(2) }}</strong>
        is {{ todaySignal.direction === 'above' ? 'above' : todaySignal.direction === 'below' ? 'below' : 'near' }}
        the {{ todaySignal.daysCount }}-day average
        <strong>₹{{ todaySignal.avgBest.toFixed(2) }}</strong><template v-if="todaySignal.trend === 'up'"> — rates have been rising</template><template v-else-if="todaySignal.trend === 'down'"> — rates have been declining</template>
      </span>
    </div>

    <div v-if="staleBanks.length" class="stale-callout" role="alert">
      <svg class="stale-icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
        <path d="M8 1.5L1.5 13h13L8 1.5z" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/>
        <line x1="8" y1="6.5" x2="8" y2="9.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
        <circle cx="8" cy="11.5" r="0.7" fill="currentColor"/>
      </svg>
      <span>
        Rate data for
        <strong>{{ staleBanks.slice(0, 3).map(r => shortName(r.bank)).join(', ') }}<template v-if="staleBanks.length > 3"> +{{ staleBanks.length - 3 }} more</template></strong>
        is from {{ formatDate(staleBanks[0].date) }} — may not reflect today's rate
      </span>
    </div>

    <div v-if="dowInsight" class="dow-callout" role="note">
      <svg class="dow-icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
        <rect x="1.5" y="2.5" width="13" height="12" rx="2" fill="none" stroke="currentColor" stroke-width="1.3"/>
        <line x1="5" y1="1" x2="5" y2="4" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
        <line x1="11" y1="1" x2="11" y2="4" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
        <line x1="1.5" y1="6.5" x2="14.5" y2="6.5" stroke="currentColor" stroke-width="1.3"/>
        <circle cx="8" cy="10.5" r="1.2" fill="currentColor"/>
      </svg>
      <span>
        Based on history, <strong>{{ currency }} rates tend to peak on {{ dowInsight.day }}s</strong>
        — avg ₹{{ (dowInsight.diffPaise / 100).toFixed(2) }}/{{ currency }} above the weekly mean
      </span>
    </div>

    <div v-if="consistency" class="consistency-summary" role="note">
      <svg class="consistency-icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
        <path d="M4.5 2h7v5.5a3.5 3.5 0 01-7 0V2z" fill="none" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M1.5 3h3M11.5 3h3" fill="none" stroke="currentColor" stroke-width="1.25" stroke-linecap="round"/>
        <path d="M8 9.5V12" fill="none" stroke="currentColor" stroke-width="1.25" stroke-linecap="round"/>
        <path d="M5 14h6" fill="none" stroke="currentColor" stroke-width="1.25" stroke-linecap="round"/>
      </svg>
      <span>
        <span class="consistency-bank">{{ shortName(consistency.bank) }}</span>
        had the best {{ currency }} rate most often — {{ consistency.count }} of {{ consistency.total }} {{ consistency.total === 1 ? 'day' : 'days' }}<template v-if="sinceLabel"> since {{ sinceLabel }}</template>
      </span>
    </div>

    <div v-if="stableBank" class="stable-callout" role="note">
      <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="1,11 5,7 9,9 15,4"/>
        <line x1="1" y1="13" x2="15" y2="13"/>
      </svg>
      <span>
        <strong :style="{ color: stableBank.color }">{{ shortName(stableBank.bank) }}</strong>
        was the most consistent among the top {{ stableBank.topN }} banks —
        rate varied by only ₹{{ stableBank.variation.toFixed(2) }}<template v-if="stableBank.runner">
          vs {{ shortName(stableBank.runner.bank) }}'s ₹{{ stableBank.runner.variation.toFixed(2) }}</template>
      </span>
    </div>

    <div class="table-wrap">
      <table class="best-rate-table">
        <caption>
          {{ currency }} TT Buy rate by bank — ranked by what you'd actually receive after each bank's own
          inward remittance fee, not just the raw rate
        </caption>
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
          <template v-for="(row, i) in rows" :key="row.bank">
            <tr v-if="row.category === 'platform' && i === firstPlatformIndex" class="platform-divider">
              <td colspan="5" class="platform-section-header">
                Remittance platforms
                <span class="platform-section-note">Rate applied to your transfer, no deduction on recipient side</span>
              </td>
            </tr>
            <tr :class="{ best: row.bank === bestBank, expanded: expandedBank === row.bank, clickable: true }" @click="toggleExpand(row.bank, $event)">
              <th scope="row">
                <span class="row-header">
                  <span
                    class="key"
                    :class="{ wrapped: row.wrapped }"
                    :style="{ background: row.color }"
                    aria-hidden="true"
                  ></span>
                  <span class="bank-info">
                    <a
                      v-if="sourceUrl(row.bank)"
                      :href="sourceUrl(row.bank)!"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="bank-name bank-link"
                    >{{ shortName(row.bank) }}</a>
                    <span v-else class="bank-name">{{ shortName(row.bank) }}</span>
                    <span
                      v-if="consistency && row.bank === consistency.bank"
                      class="consistency-label"
                    >Best rate {{ consistency.count }} of {{ consistency.total }} {{ consistency.total === 1 ? 'day' : 'days' }}</span>
                  </span>
                  <button
                    v-if="fees[row.bank]"
                    type="button"
                    class="fee-info"
                    aria-label="Inward remittance fee info"
                    @mouseenter="showFeeTooltip(row.bank, $event)"
                    @mouseleave="scheduleHideFeeTooltip"
                    @click="toggleFeeTooltip(row.bank, $event)"
                    @blur="scheduleHideFeeTooltip"
                  >
                    <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">
                      <circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1.3" />
                      <line x1="8" y1="7" x2="8" y2="11.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" />
                      <circle cx="8" cy="4.6" r="0.9" fill="currentColor" />
                    </svg>
                  </button>
                  <span v-if="row.bank === bestBank" class="badge">
                    <svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
                      <path d="M3 8.5l3 3 7-7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                    </svg>
                    <span class="badge-text">Best value in banks</span>
                  </span>
                  <span v-if="row.bank === bestPlatform" class="badge">
                    <svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
                      <path d="M3 8.5l3 3 7-7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                    </svg>
                    <span class="badge-text">Best value in platforms</span>
                  </span>
                  <svg
                    class="expand-chevron"
                    :class="{ open: expandedBank === row.bank }"
                    viewBox="0 0 16 16"
                    width="12"
                    height="12"
                    aria-hidden="true"
                  >
                    <path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </span>
              </th>
              <template v-if="row.hasData">
                <td class="num">
                  <div class="ttbuy-inner">
                    <span class="rate-val">{{ row.ttbuy.toFixed(2) }}</span>
                    <span class="delta-slot">
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
                    </span>
                  </div>
                </td>
                <td class="num receive">
                  <span
                    v-if="row.feeUnknown"
                    :title="`Fee not confirmed for this bank — showing the gross conversion (rate × amount) with no fee deducted, so the real amount you get may be a little lower.`"
                  >
                    ≈₹{{ formatInr(row.netReceive) }}
                  </span>
                  <template v-else>₹{{ formatInr(row.netReceive) }}</template>
                  <div v-if="row.feeInr > 0" class="fee-deducted">−₹{{ formatInr(row.feeInr) }} fee</div>
                </td>
                <td class="num gap" :class="{ muted: row.bank === bestBank || row.gapToBest === 0, ahead: row.gapToBest < 0 }">
                  <template v-if="row.bank === bestBank || row.gapToBest === 0">—</template>
                  <template v-else-if="row.gapToBest < 0">+₹{{ formatInr(Math.abs(row.gapToBest)) }}</template>
                  <template v-else>−₹{{ formatInr(row.gapToBest) }}</template>
                </td>
                <td :class="{ 'stale-date': latestDate && row.date < latestDate }">
                  {{ formatDate(row.date) }}
                  <svg v-if="latestDate && row.date < latestDate" class="stale-cell-icon" viewBox="0 0 16 16" width="10" height="10" aria-label="Stale data">
                    <path d="M8 1.5L1.5 13h13L8 1.5z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
                    <line x1="8" y1="6.5" x2="8" y2="9.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                    <circle cx="8" cy="11.5" r="0.8" fill="currentColor"/>
                  </svg>
                </td>
              </template>
              <td v-else colspan="4" class="no-data">No data for this bank</td>
            </tr>
            <tr v-if="expandedBank === row.bank" class="detail-row">
              <td colspan="5">
                <div class="detail-panel">
                  <div v-if="bankStats.has(row.bank)" class="detail-stats">
                    <div class="stat-group">
                      <div class="stat-item">
                        <span class="stat-label">{{ statPrefix }} avg</span>
                        <span class="stat-val">{{ bankStats.get(row.bank)!.avg?.toFixed(2) }}</span>
                      </div>
                      <div class="stat-item">
                        <span class="stat-label">{{ statPrefix }} best</span>
                        <span class="stat-val good">{{ bankStats.get(row.bank)!.best?.toFixed(2) }}</span>
                      </div>
                      <div class="stat-item">
                        <span class="stat-label">{{ statPrefix }} worst</span>
                        <span class="stat-val bad">{{ bankStats.get(row.bank)!.worst?.toFixed(2) }}</span>
                      </div>
                    </div>
                    <div class="sparkline-wrap">
                      <svg v-if="bankStats.get(row.bank)!.sparkline" viewBox="0 0 120 44" class="sparkline-svg">
                        <path :d="bankStats.get(row.bank)!.sparkline" fill="none" :stroke="row.color" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                      </svg>
                      <span v-else class="sparkline-empty">Not enough data</span>
                    </div>
                  </div>
                  <div v-else class="detail-stats empty">
                    No historical data available for this period.
                  </div>

                  <div v-if="fees[row.bank]" class="detail-fees">
                    <p class="detail-fee-title">{{ fees[row.bank].rules.length ? "Inward remittance fee" : "Fee note" }}</p>
                    <div class="detail-fee-rules">
                      <div v-for="rule in fees[row.bank].rules" :key="rule.label" class="detail-fee-rule">
                        <span class="fee-label">{{ rule.label }}</span>
                        <span class="fee-charge">{{ rule.charge }}</span>
                      </div>
                    </div>
                    <p v-if="fees[row.bank].note" class="fee-note">{{ fees[row.bank].note }}</p>
                    <a :href="fees[row.bank].source_url" target="_blank" rel="noopener noreferrer" class="fee-source">
                      {{ fees[row.bank].rules.length ? "Bank's published schedule ↗" : "Learn more ↗" }}
                    </a>
                  </div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <div
      v-if="activeFee"
      class="fee-tooltip"
      :style="feeTooltipStyle"
      @mouseenter="cancelHideFeeTooltip"
      @mouseleave="scheduleHideFeeTooltip"
    >
      <div class="fee-tooltip-title">
        {{ shortName(activeFee.bank) }}: {{ activeFee.rules.length ? "Inward remittance fee" : "Note" }}
      </div>
      <div v-for="rule in activeFee.rules" :key="rule.label" class="fee-rule">
        <div class="fee-label">{{ rule.label }}</div>
        <div class="fee-charge">{{ rule.charge }}</div>
      </div>
      <p v-if="activeFee.note" class="fee-note">{{ activeFee.note }}</p>
      <a :href="activeFee.source_url" target="_blank" rel="noopener noreferrer" class="fee-source">
        {{ activeFee.rules.length ? "Bank's published schedule ↗" : "Learn more ↗" }}
      </a>
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

  &.invalid {
    border-color: var(--status-critical);
  }

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

.spread-callout {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin: 0 0 8px;
  padding: 8px 12px;
  background: color-mix(in srgb, var(--status-good) 8%, transparent);
  border: 1px solid color-mix(in srgb, var(--status-good) 22%, transparent);
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.4;

  .spread-icon {
    flex: none;
    color: var(--success-text);
    margin-top: 1px;
  }

  .spread-rate {
    font-weight: 600;
    color: var(--text-primary);
    font-variant-numeric: tabular-nums;
  }

  .spread-amount {
    font-weight: 700;
    color: var(--success-text);
    font-variant-numeric: tabular-nums;
  }
}

.today-callout {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin: 0 0 8px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.4;

  &.above {
    background: color-mix(in srgb, var(--status-good) 8%, transparent);
    border: 1px solid color-mix(in srgb, var(--status-good) 22%, transparent);
    .today-icon { color: var(--status-good); }
  }

  &.below {
    background: color-mix(in srgb, var(--status-warning) 10%, transparent);
    border: 1px solid color-mix(in srgb, var(--status-warning) 28%, transparent);
    .today-icon { color: var(--status-warning); }
  }

  &.near {
    background: var(--page-plane);
    border: 1px solid var(--border);
    .today-icon { color: var(--text-muted); }
  }

  .today-icon {
    flex: none;
    margin-top: 2px;
  }

  strong {
    font-weight: 600;
    color: var(--text-primary);
    font-variant-numeric: tabular-nums;
  }
}

.consistency-summary {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin: 0 0 12px;
  padding: 9px 12px;
  background: color-mix(in srgb, var(--accent) 9%, transparent);
  border-left: 2px solid var(--accent);
  border-radius: 0 6px 6px 0;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.4;

  .consistency-icon {
    flex: none;
    color: var(--accent);
    margin-top: 1px;
  }

  .consistency-bank {
    font-weight: 600;
    color: var(--text-primary);
  }
}

.stable-callout {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin: 0 0 12px;
  padding: 9px 12px;
  background: color-mix(in srgb, var(--text-muted) 8%, transparent);
  border-left: 2px solid var(--text-muted);
  border-radius: 0 6px 6px 0;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.4;

  svg {
    flex: none;
    color: var(--text-muted);
    margin-top: 1px;
  }

  strong {
    font-weight: 600;
  }
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
    transition: background 80ms ease;
  }

  tbody tr:not(.platform-divider):not(.best):hover th,
  tbody tr:not(.platform-divider):not(.best):hover td {
    background: var(--page-plane);
  }

  tbody tr:last-child th,
  tbody tr:last-child td {
    border-bottom: none;
  }
  
  tbody tr.clickable {
    cursor: pointer;

    &:not(.best):not(.platform-divider):hover .expand-chevron {
      color: var(--text-secondary);
    }
  }
  
  tbody tr.expanded th,
  tbody tr.expanded td {
    border-bottom: none;
  }
  
  tbody tr.detail-row th,
  tbody tr.detail-row td {
    padding: 0;
    border-bottom: 1px solid var(--gridline);
    background: color-mix(in srgb, var(--surface-1) 30%, var(--page-plane));
    white-space: normal;
  }

  tbody tr.detail-row:hover th,
  tbody tr.detail-row:hover td {
    background: color-mix(in srgb, var(--surface-1) 30%, var(--page-plane));
    cursor: default;
  }

  .detail-panel {
    display: flex;
    flex-wrap: wrap;
    gap: 0;
    padding: 14px 16px 18px 32px;
    box-shadow: inset 0 2px 8px -4px rgba(0,0,0,0.08);
  }

  .detail-stats {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 20px;
    flex: 1;
    min-width: 200px;
    padding-right: 20px;

    &.empty {
      color: var(--text-muted);
      font-style: italic;
      font-size: 13px;
    }
  }

  .stat-group {
    display: flex;
    gap: 20px;
  }

  .stat-item {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .stat-label {
    font-size: 11px;
    text-transform: uppercase;
    color: var(--text-muted);
    font-weight: 500;
    letter-spacing: 0.03em;
  }

  .stat-val {
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
    font-variant-numeric: tabular-nums;

    &.good { color: var(--success-text); }
    &.bad { color: var(--status-critical); }
  }

  .sparkline-wrap {
    flex: none;
    width: 120px;
    height: 44px;
    display: flex;
    align-items: center;
  }

  .sparkline-svg {
    width: 100%;
    height: 100%;
    overflow: visible;
  }

  .sparkline-empty {
    font-size: 11px;
    color: var(--text-muted);
    font-style: italic;
  }

  .detail-fees {
    flex: 1;
    min-width: 180px;
    border-left: 1px solid var(--gridline);
    padding: 0 0 0 20px;
  }

  .detail-fee-title {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--text-muted);
    margin: 0 0 8px;
  }

  .detail-fee-rules {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 8px;
  }

  .detail-fee-rule {
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    border-bottom: 1px solid var(--gridline);
    padding-bottom: 6px;

    &:last-child {
      border-bottom: none;
      padding-bottom: 0;
    }
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
    // Deliberately not display:flex on the <th> itself — that breaks its
    // table-cell box, so its border-bottom stops stretching to match the
    // row height when a sibling <td> (e.g. a fee subtext line) is taller.
    // The flex layout lives on .row-header inside it instead.
    vertical-align: middle;
  }

  .row-header {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .bank-info {
    display: flex;
    flex-direction: column;
    gap: 1px;
    flex: 0 1 auto;
    min-width: 0;
  }

  .bank-name {
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .consistency-label {
    display: inline-flex;
    align-items: center;
    font-size: 10px;
    font-weight: 500;
    color: var(--accent);
    background: color-mix(in srgb, var(--accent) 12%, transparent);
    padding: 1px 5px;
    border-radius: 3px;
    white-space: nowrap;
    letter-spacing: 0.01em;
  }

  .bank-link {
    color: inherit;
    text-decoration: none;

    &:hover {
      text-decoration: underline;
      text-underline-offset: 2px;
    }
  }

  .num {
    font-variant-numeric: tabular-nums;
    text-align: right;
  }

  .receive {
    color: var(--text-primary);
    font-weight: 600;
  }

  .fee-deducted {
    font-size: 10px;
    font-weight: 400;
    color: var(--text-muted);
    white-space: nowrap;
  }

  .gap {
    color: var(--text-secondary);

    &.ahead {
      color: var(--success-text);
    }
  }

  .ttbuy-inner {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 6px;
  }

  // Fixed-width slot so the rate-val column stays aligned regardless of
  // whether a delta indicator is present for that row.
  .delta-slot {
    flex: none;
    min-width: 52px;
  }

  .delta {
    display: inline-block;
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

  .no-data {
    color: var(--text-muted);
    font-style: italic;
    text-align: center;
  }

  tr.platform-divider td {
    padding: 6px 12px 4px;
    border-bottom: none;
    border-top: 2px solid var(--border);
    background: var(--surface-0, var(--surface-1));
  }

  .platform-section-header {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-muted);
  }

  .platform-section-note {
    font-size: 11px;
    font-weight: 400;
    text-transform: none;
    letter-spacing: 0;
    color: var(--text-muted);
    margin-left: 8px;
    font-style: italic;
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
    
    .detail-panel {
      padding: 12px 8px 16px;
      flex-direction: column;
    }

    .detail-stats {
      gap: 16px;
      padding-right: 0;
    }

    .detail-fees {
      border-left: none;
      border-top: 1px solid var(--gridline);
      padding: 12px 0 0;
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

  .expand-chevron {
    flex: none;
    margin-left: auto;
    color: var(--text-muted);
    transition: transform 200ms ease, color 100ms ease;

    &.open {
      transform: rotate(180deg);
      color: var(--text-secondary);
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

.fee-info {
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  padding: 0;
  border: none;
  border-radius: 999px;
  background: none;
  color: var(--text-muted);
  cursor: pointer;

  &:hover,
  &:focus-visible {
    color: var(--text-primary);
    background: var(--gridline);
  }
}

.fee-tooltip {
  position: fixed;
  z-index: 20;
  width: 280px;
  max-width: calc(100vw - 24px);
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  overflow-wrap: break-word;
}

.fee-tooltip-title {
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
}

// Charge descriptions can be a short word ("Nil") or a long multi-tier
// string ("Rs.500 (up to Rs.5 lakhs), Rs.1000 (up to Rs.10 Lakhs), ...") —
// stacking label above charge (rather than a space-between row) avoids
// ever having to squeeze the charge into the remaining row width.
.fee-rule {
  padding: 4px 0;
  color: var(--text-secondary);

  .fee-label {
    font-size: 11px;
  }

  .fee-charge {
    color: var(--text-primary);
    font-weight: 500;
    line-height: 1.4;
  }
}

.fee-note {
  margin: 6px 0 0;
  padding-top: 6px;
  border-top: 1px solid var(--gridline);
  color: var(--text-muted);
  line-height: 1.4;
}

.fee-source {
  display: inline-block;
  margin-top: 8px;
  color: var(--accent);
  font-size: 11px;

  &:hover {
    text-decoration: underline;
  }
}

.stale-callout {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin: 0 0 8px;
  padding: 8px 12px;
  background: color-mix(in srgb, #f59e0b 8%, transparent);
  border: 1px solid color-mix(in srgb, #f59e0b 28%, transparent);
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.4;

  .stale-icon {
    flex: none;
    color: #d97706;
    margin-top: 1px;
  }

  strong {
    color: var(--text-primary);
    font-weight: 600;
  }
}

.stale-date {
  color: #d97706;

  .stale-cell-icon {
    color: #d97706;
    vertical-align: middle;
    margin-left: 3px;
  }
}

.dow-callout {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin: 0 0 8px;
  padding: 8px 12px;
  background: color-mix(in srgb, var(--accent) 6%, transparent);
  border: 1px solid color-mix(in srgb, var(--accent) 18%, transparent);
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.4;

  .dow-icon {
    flex: none;
    color: var(--accent);
    margin-top: 1px;
  }

  strong {
    color: var(--text-primary);
    font-weight: 600;
  }
}
</style>
