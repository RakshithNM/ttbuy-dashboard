<script setup lang="ts">
import { computed, ref } from "vue";
import type { BankSeries, FeesByBank, FeeSlab } from "../types";
import { shortName, sourceUrl } from "../bankPalette";
import { currencySymbol } from "../currencies";

const props = defineProps<{
  series: BankSeries[];
  currency: string;
  fees: FeesByBank;
  consistency: { bank: string; count: number; total: number } | null;
}>();

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

    <p v-if="consistency" class="consistency-summary">
      <span class="consistency-bank">{{ shortName(consistency.bank) }}</span>
      had the best {{ currency }} rate most often in this period — {{ consistency.count }} of {{ consistency.total }} {{ consistency.total === 1 ? 'day' : 'days' }}
    </p>

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
            <tr :class="{ best: row.bank === bestBank }">
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
                <td class="muted">{{ formatDate(row.date) }}</td>
              </template>
              <td v-else colspan="4" class="no-data">No data for this bank</td>
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

.consistency-summary {
  margin: 0 0 10px;
  font-size: 12px;
  color: var(--text-secondary);

  .consistency-bank {
    font-weight: 600;
    color: var(--text-primary);
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
    font-size: 10px;
    font-weight: 400;
    color: var(--text-muted);
    white-space: nowrap;
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
</style>
