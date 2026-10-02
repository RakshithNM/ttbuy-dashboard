<script setup lang="ts">
import { computed, ref } from "vue";
import type { BankSeries, FeesByBank, FeeSlab } from "../types";
import { brandColor, shortName } from "../bankPalette";
import { currencySymbol } from "../currencies";
const props = defineProps<{
  series: BankSeries[];
  fees: FeesByBank;
  currency: string;
  amount: number;
}>();

const myBank = defineModel<string>("myBank", { default: "" });

function feeFromSlabs(slabs: FeeSlab[], grossInr: number): number {
  for (const s of slabs) {
    if (s.up_to === null || grossInr <= s.up_to) return s.fee_inr;
  }
  return 0;
}

const safeAmount = computed(() => {
  const n = Number(props.amount);
  return Number.isFinite(n) && n > 0 ? n : 0;
});

function formatInr(n: number): string {
  return Math.round(n).toLocaleString("en-IN");
}

function fmtDate(iso: string): string {
  const [, m, d] = iso.split("-").map(Number);
  return `${["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][m - 1]} ${d}`;
}

// Most recent date among all bank series (excludes platforms and benchmarks)
const latestDate = computed(() => {
  let d = "";
  for (const s of props.series) {
    if (s.category !== "bank" || !s.points.length) continue;
    const last = s.points.at(-1)!.date;
    if (last > d) d = last;
  }
  return d;
});

interface BankSnap {
  name: string;
  color: string;
  ttbuy: number;
  date: string;
  netInr: number;
  feeUnknown: boolean;
}

// Every bank's latest known rate, ranked by net receive. This matches the
// "Best value today" table, which also ranks each bank's last reading — on a
// holiday most banks are a day old, and filtering to only today's date made
// this panel name a different "best" bank than the table right below it.
const rankedBanks = computed<BankSnap[]>(() => {
  if (!safeAmount.value || !latestDate.value) return [];
  const out: BankSnap[] = [];
  for (const s of props.series) {
    if (s.category !== "bank" || !s.points.length) continue;
    const last = s.points.at(-1)!;
    const gross = last.ttbuy * safeAmount.value;
    const fee = props.fees[s.name];
    const feeUnknown = !fee?.fee_slabs && fee?.fee_inr == null;
    const feeInr = fee?.fee_slabs ? feeFromSlabs(fee.fee_slabs, gross) : (fee?.fee_inr ?? 0);
    out.push({ name: s.name, color: brandColor(s.name), ttbuy: last.ttbuy, date: last.date, netInr: gross - feeInr, feeUnknown });
  }
  return out.sort((a, b) => b.netInr - a.netInr);
});

// My bank's last known snapshot (may be stale)
const mySnap = computed<BankSnap | null>(() => {
  if (!myBank.value) return null;
  const s = props.series.find(s => s.name === myBank.value);
  if (!s || !s.points.length) return null;
  const last = s.points.at(-1)!;
  const gross = last.ttbuy * safeAmount.value;
  const fee = props.fees[myBank.value];
  const feeUnknown = !fee?.fee_slabs && fee?.fee_inr == null;
  const feeInr = fee?.fee_slabs ? feeFromSlabs(fee.fee_slabs, gross) : (fee?.fee_inr ?? 0);
  return { name: myBank.value, color: brandColor(myBank.value), ttbuy: last.ttbuy, date: last.date, netInr: gross - feeInr, feeUnknown };
});

const isStale = computed(() =>
  !!mySnap.value && !!latestDate.value && mySnap.value.date < latestDate.value
);

const staleDays = computed(() => {
  if (!mySnap.value || !latestDate.value || !isStale.value) return null;
  return Math.round((new Date(latestDate.value).getTime() - new Date(mySnap.value.date).getTime()) / 86_400_000);
});

const myRank = computed<number | null>(() => {
  if (!myBank.value || isStale.value) return null;
  const i = rankedBanks.value.findIndex(b => b.name === myBank.value);
  return i >= 0 ? i + 1 : null;
});

const bestSnap = computed(() => rankedBanks.value[0] ?? null);

const gapToBest = computed<number | null>(() => {
  if (!mySnap.value || !bestSnap.value || isStale.value) return null;
  return bestSnap.value.netInr - mySnap.value.netInr;
});

type StateKind = "leading" | "competitive" | "behind" | "lagging" | "stale" | "no_data";

const stateKind = computed<StateKind>(() => {
  if (!myBank.value || !mySnap.value) return "no_data";
  if (isStale.value) return "stale";
  const rank = myRank.value;
  if (rank === null) return "no_data";
  const gap = gapToBest.value ?? 0;
  if (rank === 1) return "leading";
  if (gap < 150) return "competitive";
  if (gap < 700) return "behind";
  return "lagging";
});

// How often my bank has led in the last 30 qualifying days
const leadCount = computed<{ led: number; total: number } | null>(() => {
  if (!myBank.value) return null;
  const bankSeries = props.series.filter(s => s.category === "bank" && s.points.length > 0);
  const threshold = Math.floor(bankSeries.length / 2) + 1;
  const byDate = new Map<string, { bank: string; rate: number }[]>();
  for (const s of bankSeries) {
    for (const pt of s.points) {
      const list = byDate.get(pt.date) ?? [];
      list.push({ bank: s.name, rate: pt.ttbuy });
      byDate.set(pt.date, list);
    }
  }
  const dates = [...byDate.keys()].sort().slice(-30);
  let led = 0, total = 0;
  for (const d of dates) {
    const entries = byDate.get(d)!;
    if (entries.length < threshold) continue;
    total++;
    const best = entries.reduce((a, b) => a.rate >= b.rate ? a : b);
    if (best.bank === myBank.value) led++;
  }
  return total > 0 ? { led, total } : null;
});

const allBanks = computed(() =>
  [...new Set(
    props.series.filter(s => s.category === "bank" && s.points.length > 0).map(s => s.name)
  )].sort()
);

const myColor = computed(() => myBank.value ? brandColor(myBank.value) : "var(--text-muted)");

// Negotiation card export — a static PNG a user can send to their bank's
// forex officer as evidence for a better rate. Only worth offering when
// there's an actual gap to point to (not when already leading, and not on
// stale/missing data, which wouldn't be credible evidence).
const showNegotiationExport = computed(() =>
  !!mySnap.value && !!bestSnap.value &&
  (stateKind.value === "competitive" || stateKind.value === "behind" || stateKind.value === "lagging")
);

// Top 5 by net receive, with my bank pinned at the end if it fell outside that.
const leaderboardRows = computed<BankSnap[]>(() => {
  const top = rankedBanks.value.slice(0, 5);
  if (!mySnap.value || top.some(b => b.name === mySnap.value!.name)) return top;
  return [...top, mySnap.value];
});

function fmtLongDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return `${["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][m - 1]} ${d}, ${y}`;
}

// Rendered as a fixed-layout hidden SVG — independent of the site's own
// theme (always light, since it's meant to be read/printed by someone else)
// — then rasterized to PNG via canvas on click. Serialize -> Blob -> Image ->
// canvas is a dependency-free way to export an SVG as PNG, so this doesn't
// need an image-export library.
const CARD_W = 1200;
const CARD_H = 675;
const negotiationSvgRef = ref<SVGSVGElement | null>(null);
const exportingCard = ref(false);

async function downloadNegotiationCard() {
  const svgEl = negotiationSvgRef.value;
  if (!svgEl || exportingCard.value) return;
  exportingCard.value = true;
  try {
    const svgString = new XMLSerializer().serializeToString(svgEl);
    const svgUrl = URL.createObjectURL(new Blob([svgString], { type: "image/svg+xml;charset=utf-8" }));
    const img = new Image();
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve();
      img.onerror = () => reject(new Error("card render failed"));
      img.src = svgUrl;
    });
    const scale = 2; // export at 2x for a crisp, zoomable/printable image
    const canvas = document.createElement("canvas");
    canvas.width = CARD_W * scale;
    canvas.height = CARD_H * scale;
    const ctx = canvas.getContext("2d");
    URL.revokeObjectURL(svgUrl);
    if (!ctx) return;
    ctx.scale(scale, scale);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, CARD_W, CARD_H);
    ctx.drawImage(img, 0, 0, CARD_W, CARD_H);

    const pngBlob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/png"));
    if (!pngBlob) return;
    const link = document.createElement("a");
    link.href = URL.createObjectURL(pngBlob);
    link.download = `ttbuy-rate-comparison-${myBank.value.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-${props.currency}.png`;
    link.click();
    URL.revokeObjectURL(link.href);
  } catch {
    // Best-effort export — if SVG rasterization fails (unsupported browser,
    // blocked canvas), just no-op rather than surfacing a broken flow.
  } finally {
    exportingCard.value = false;
  }
}
</script>

<template>
  <!-- Collapsed prompt when no bank selected -->
  <div v-if="!myBank" class="mbp-prompt">
    <span class="mbp-swatch-sm" aria-hidden="true" />
    <div class="mbp-prompt-text">
      <label class="mbp-prompt-label" for="mbp-select-empty">Set your bank</label>
      <span class="mbp-prompt-hint">See instantly how your rate compares to the best today</span>
    </div>
    <select id="mbp-select-empty" v-model="myBank" class="mbp-select-inline" aria-label="Set my bank">
      <option value="">Choose your bank…</option>
      <option v-for="bank in allBanks" :key="bank" :value="bank">{{ bank }}</option>
    </select>
  </div>

  <!-- Expanded panel when bank is selected -->
  <section v-else class="mbp panel" aria-label="My bank insights">
    <!-- Header: selector + clear -->
    <div class="mbp-header">
      <span class="mbp-swatch" :style="{ background: myColor }" aria-hidden="true" />
      <span class="mbp-label">My bank</span>
      <select v-model="myBank" name="my-bank" class="mbp-select" aria-label="Change my bank">
        <option v-for="bank in allBanks" :key="bank" :value="bank">{{ bank }}</option>
      </select>
      <button type="button" class="mbp-clear" aria-label="Clear my bank" @click="myBank = ''">✕</button>
    </div>

    <!-- State body -->
    <div v-if="mySnap" class="mbp-body" :class="stateKind">

      <!-- LEADING -->
      <template v-if="stateKind === 'leading'">
        <div class="mbp-headline">
          <svg class="st-icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M2.5 8.5l4 4 7-8"/></svg>
          <span>Your bank is <strong>today's best</strong> for {{ currency }}</span>
        </div>
        <div class="mbp-stats">
          <span class="stat-rate">₹{{ mySnap.ttbuy.toFixed(2) }}</span>
          <span class="stat-arr">→</span>
          <span class="stat-recv" :title="mySnap.feeUnknown ? 'Fee not confirmed — showing gross conversion; real amount may be lower' : undefined">{{ mySnap.feeUnknown ? '≈' : '' }}₹{{ formatInr(mySnap.netInr) }}</span>
          <span class="stat-for">on {{ currencySymbol(currency) }}{{ formatInr(safeAmount) }}</span>
        </div>
        <div v-if="leadCount && leadCount.led > 0" class="mbp-sub">
          Led {{ leadCount.led }} of {{ leadCount.total }} days in the last month
        </div>
      </template>

      <!-- COMPETITIVE -->
      <template v-else-if="stateKind === 'competitive'">
        <div class="mbp-headline">
          <svg class="st-icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M2 8h12"/><path d="M2 5h12" opacity="0.35"/><path d="M2 11h12" opacity="0.35"/></svg>
          <span>Your bank is <strong>close to the top</strong>, #{{ myRank }} of {{ rankedBanks.length }}</span>
        </div>
        <div class="mbp-stats">
          <span class="stat-rate">₹{{ mySnap.ttbuy.toFixed(2) }}</span>
          <span class="stat-arr">→</span>
          <span class="stat-recv" :title="mySnap.feeUnknown ? 'Fee not confirmed — showing gross conversion; real amount may be lower' : undefined">{{ mySnap.feeUnknown ? '≈' : '' }}₹{{ formatInr(mySnap.netInr) }}</span>
          <span class="stat-for">on {{ currencySymbol(currency) }}{{ formatInr(safeAmount) }}</span>
          <span class="stat-gap">· ₹{{ formatInr(gapToBest!) }} less than {{ shortName(bestSnap!.name) }}</span>
        </div>
        <div v-if="leadCount && leadCount.led > 0" class="mbp-sub">
          Led {{ leadCount.led }} of {{ leadCount.total }} days in the last month
        </div>
      </template>

      <!-- BEHIND -->
      <template v-else-if="stateKind === 'behind'">
        <div class="mbp-headline">
          <svg class="st-icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3v8"/><path d="M5 8l3 3 3-3"/></svg>
          <span>Your bank is <strong>mid-table</strong>, #{{ myRank }} of {{ rankedBanks.length }} today</span>
        </div>
        <div class="mbp-stats">
          <span class="stat-rate">₹{{ mySnap.ttbuy.toFixed(2) }}</span>
          <span class="stat-arr">→</span>
          <span class="stat-recv" :title="mySnap.feeUnknown ? 'Fee not confirmed — showing gross conversion; real amount may be lower' : undefined">{{ mySnap.feeUnknown ? '≈' : '' }}₹{{ formatInr(mySnap.netInr) }}</span>
          <span class="stat-for">on {{ currencySymbol(currency) }}{{ formatInr(safeAmount) }}</span>
          <span class="stat-gap">· ₹{{ formatInr(gapToBest!) }} less than {{ shortName(bestSnap!.name) }}</span>
        </div>
      </template>

      <!-- LAGGING -->
      <template v-else-if="stateKind === 'lagging'">
        <div class="mbp-headline">
          <svg class="st-icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 2v9"/><path d="M5 8l3 3 3-3"/><path d="M5 12l3 3 3-3"/></svg>
          <span>Your bank is <strong>near the bottom</strong>, #{{ myRank }} of {{ rankedBanks.length }}</span>
        </div>
        <div class="mbp-stats">
          <span class="stat-rate">₹{{ mySnap.ttbuy.toFixed(2) }}</span>
          <span class="stat-arr">→</span>
          <span class="stat-recv" :title="mySnap.feeUnknown ? 'Fee not confirmed — showing gross conversion; real amount may be lower' : undefined">{{ mySnap.feeUnknown ? '≈' : '' }}₹{{ formatInr(mySnap.netInr) }}</span>
          <span class="stat-for">on {{ currencySymbol(currency) }}{{ formatInr(safeAmount) }}</span>
        </div>
        <div class="mbp-sub">
          ₹{{ formatInr(gapToBest!) }} less than {{ shortName(bestSnap!.name) }}. Switching banks would make a meaningful difference.
        </div>
      </template>

      <!-- STALE -->
      <template v-else-if="stateKind === 'stale'">
        <div class="mbp-headline">
          <svg class="st-icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"><path d="M8 1.5L1.5 13h13L8 1.5z" stroke-linejoin="round"/><line x1="8" y1="6" x2="8" y2="9.5"/><circle cx="8" cy="11.5" r="0.75" fill="currentColor" stroke="none"/></svg>
          <span>Rate is <strong>{{ staleDays }} {{ staleDays === 1 ? 'day' : 'days' }} old</strong> ({{ fmtDate(mySnap.date) }}), may not reflect today</span>
        </div>
        <div class="mbp-stats">
          <span class="stat-rate">₹{{ mySnap.ttbuy.toFixed(2) }}</span>
          <span class="stat-arr">→</span>
          <span class="stat-recv" :title="mySnap.feeUnknown ? 'Fee not confirmed — showing gross conversion; real amount may be lower' : undefined">{{ mySnap.feeUnknown ? '≈' : '' }}₹{{ formatInr(mySnap.netInr) }}</span>
          <span class="stat-for">on {{ currencySymbol(currency) }}{{ formatInr(safeAmount) }}</span>
          <span v-if="bestSnap && bestSnap.name !== mySnap.name" class="stat-gap">· current best is {{ shortName(bestSnap.name) }} at ₹{{ bestSnap.ttbuy.toFixed(2) }}</span>
        </div>
      </template>

      <!-- NO_DATA -->
      <template v-else>
        <div class="mbp-headline">
          <svg class="st-icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"><circle cx="8" cy="8" r="6"/><line x1="8" y1="5" x2="8" y2="9"/><circle cx="8" cy="11.2" r="0.75" fill="currentColor" stroke="none"/></svg>
          <span>No rate data for <strong>{{ shortName(myBank) }}</strong> today</span>
        </div>
        <div v-if="bestSnap" class="mbp-sub">
          Current best is {{ shortName(bestSnap.name) }} at ₹{{ bestSnap.ttbuy.toFixed(2) }}
        </div>
      </template>
    </div>

    <div v-if="showNegotiationExport" class="mbp-negotiate">
      <button type="button" class="mbp-negotiate-btn" :disabled="exportingCard" @click="downloadNegotiationCard">
        <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 2v8"/><path d="M4.5 7l3.5 3 3.5-3"/><path d="M2.5 12.5h11"/></svg>
        {{ exportingCard ? "Preparing…" : "Download comparison to show your bank" }}
      </button>

      <!-- Export-only card, rasterized to PNG on click — never shown on screen. -->
      <svg
        ref="negotiationSvgRef"
        :viewBox="`0 0 ${CARD_W} ${CARD_H}`"
        :width="CARD_W"
        :height="CARD_H"
        style="display: none"
        aria-hidden="true"
      >
        <rect width="100%" height="100%" fill="#ffffff" />

        <text x="48" y="50" font-size="26" font-weight="700" fill="#111827" font-family="system-ui, sans-serif">TT Buy Rate Comparison</text>
        <text x="1152" y="50" font-size="14" fill="#6b7280" text-anchor="end" font-family="system-ui, sans-serif">{{ currency }} · as of {{ fmtLongDate(latestDate) }}</text>
        <line x1="48" y1="72" x2="1152" y2="72" stroke="#e5e7eb" stroke-width="1.5" />

        <g v-if="mySnap">
          <rect x="48" y="96" width="536" height="160" rx="10" fill="#f9fafb" stroke="#e5e7eb" stroke-width="1.5" />
          <text x="72" y="124" font-size="12" font-weight="700" letter-spacing="1" fill="#6b7280" font-family="system-ui, sans-serif">YOUR BANK</text>
          <text x="72" y="158" font-size="20" font-weight="700" fill="#111827" font-family="system-ui, sans-serif">{{ mySnap.name }}</text>
          <text x="72" y="204" font-size="32" font-weight="700" fill="#111827" font-family="system-ui, sans-serif">₹{{ mySnap.ttbuy.toFixed(2) }}</text>
          <text x="72" y="236" font-size="14" fill="#6b7280" font-family="system-ui, sans-serif">{{ mySnap.feeUnknown ? "≈" : "" }}₹{{ formatInr(mySnap.netInr) }} net on {{ currencySymbol(currency) }}{{ formatInr(safeAmount) }}</text>
        </g>

        <g v-if="bestSnap">
          <rect x="616" y="96" width="536" height="160" rx="10" fill="#f0fdf4" stroke="#86efac" stroke-width="1.5" />
          <text x="640" y="124" font-size="12" font-weight="700" letter-spacing="1" fill="#15803d" font-family="system-ui, sans-serif">BEST RATE TODAY</text>
          <text x="640" y="158" font-size="20" font-weight="700" :fill="brandColor(bestSnap.name)" font-family="system-ui, sans-serif">{{ bestSnap.name }}</text>
          <text x="640" y="204" font-size="32" font-weight="700" fill="#111827" font-family="system-ui, sans-serif">₹{{ bestSnap.ttbuy.toFixed(2) }}</text>
          <text x="640" y="236" font-size="14" fill="#6b7280" font-family="system-ui, sans-serif">{{ bestSnap.feeUnknown ? "≈" : "" }}₹{{ formatInr(bestSnap.netInr) }} net on {{ currencySymbol(currency) }}{{ formatInr(safeAmount) }}</text>
        </g>

        <text v-if="gapToBest !== null" x="600" y="290" font-size="17" font-weight="600" fill="#111827" text-anchor="middle" font-family="system-ui, sans-serif">+₹{{ formatInr(gapToBest) }} more at {{ shortName(bestSnap!.name) }} on the same {{ currencySymbol(currency) }}{{ formatInr(safeAmount) }} transfer</text>

        <text x="48" y="326" font-size="15" font-weight="700" fill="#111827" font-family="system-ui, sans-serif">Today's rates, ranked</text>
        <text x="48" y="350" font-size="11" font-weight="700" fill="#6b7280" font-family="system-ui, sans-serif">#</text>
        <text x="90" y="350" font-size="11" font-weight="700" fill="#6b7280" font-family="system-ui, sans-serif">BANK</text>
        <text x="760" y="350" font-size="11" font-weight="700" fill="#6b7280" text-anchor="end" font-family="system-ui, sans-serif">TT BUY</text>
        <text x="1152" y="350" font-size="11" font-weight="700" fill="#6b7280" text-anchor="end" font-family="system-ui, sans-serif">YOU RECEIVE</text>
        <line x1="48" y1="360" x2="1152" y2="360" stroke="#e5e7eb" stroke-width="1" />

        <g v-for="(row, i) in leaderboardRows" :key="row.name">
          <rect v-if="row.name === myBank" x="40" :y="380 + i * 30 - 20" width="1120" height="26" rx="6" fill="#eff6ff" />
          <circle cx="60" :cy="380 + i * 30 - 5" r="8" :fill="brandColor(row.name)" />
          <text x="60" :y="380 + i * 30 - 2" font-size="10" font-weight="700" fill="#ffffff" text-anchor="middle" font-family="system-ui, sans-serif">{{ i + 1 }}</text>
          <text x="90" :y="380 + i * 30" font-size="14" :font-weight="row.name === myBank ? 700 : 500" fill="#111827" font-family="system-ui, sans-serif">{{ shortName(row.name) }}{{ row.name === myBank ? " (you)" : "" }}</text>
          <text x="760" :y="380 + i * 30" font-size="14" fill="#111827" text-anchor="end" font-family="system-ui, sans-serif">₹{{ row.ttbuy.toFixed(2) }}</text>
          <text x="1152" :y="380 + i * 30" font-size="14" font-weight="600" fill="#111827" text-anchor="end" font-family="system-ui, sans-serif">{{ row.feeUnknown ? "≈" : "" }}₹{{ formatInr(row.netInr) }}</text>
        </g>

        <line x1="48" y1="575" x2="1152" y2="575" stroke="#e5e7eb" stroke-width="1" />
        <text x="48" y="598" font-size="12" fill="#6b7280" font-family="system-ui, sans-serif">Rates scraped directly from each bank's public forex page, updated daily. Confirm today's rate before transacting.</text>
        <text x="48" y="618" font-size="12" font-weight="600" fill="#111827" font-family="system-ui, sans-serif">ttbuyrates.rakshithnettar.com</text>
      </svg>
    </div>

  </section>
</template>

<style scoped lang="scss">
// Prompt (no bank selected) — subtle one-liner
.mbp-prompt {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 12px;
  padding: 10px 14px;
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-bottom: 24px;
}

.mbp-swatch-sm {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--border);
  border: 1px dashed var(--text-muted);
  flex: none;
}

.mbp-prompt-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.mbp-prompt-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  cursor: pointer;
}

.mbp-prompt-hint {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mbp-select-inline {
  flex: 1 1 140px;
  min-width: 0;
  border: none;
  background: none;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  font-family: inherit;

  &:focus {
    outline: 2px solid var(--accent);
    border-radius: 2px;
  }
}

// Expanded panel
.mbp.panel {
  margin-bottom: 24px;
  padding: 16px 20px;

  @media (max-width: 480px) {
    padding: 12px 14px;
  }
}

.mbp-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.mbp-swatch {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex: none;
  transition: background 150ms;
}

.mbp-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  white-space: nowrap;
}

.mbp-select {
  flex: 1;
  min-width: 0;
  border: none;
  background: none;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  cursor: pointer;
  font-family: inherit;

  &:focus {
    outline: 2px solid var(--accent);
    border-radius: 2px;
  }
}

.mbp-clear {
  flex: none;
  background: none;
  border: none;
  font-size: 11px;
  color: var(--text-muted);
  cursor: pointer;
  padding: 2px 4px;

  &:hover {
    color: var(--text-primary);
  }

  &:focus-visible {
    outline: 2px solid var(--accent);
    border-radius: 2px;
  }
}

// State body
.mbp-body {
  padding: 10px 12px;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 5px;

  &.leading {
    background: color-mix(in srgb, var(--status-good) 10%, transparent);
    border: 1px solid color-mix(in srgb, var(--status-good) 25%, transparent);
    .st-icon { color: var(--status-good); }
  }

  &.competitive {
    background: color-mix(in srgb, var(--accent) 9%, transparent);
    border: 1px solid color-mix(in srgb, var(--accent) 22%, transparent);
    .st-icon { color: var(--accent); }
  }

  &.behind {
    background: color-mix(in srgb, var(--status-warning) 10%, transparent);
    border: 1px solid color-mix(in srgb, var(--status-warning) 28%, transparent);
    .st-icon { color: var(--status-warning); }
  }

  &.lagging {
    background: color-mix(in srgb, var(--status-serious) 10%, transparent);
    border: 1px solid color-mix(in srgb, var(--status-serious) 28%, transparent);
    .st-icon { color: var(--status-serious); }
  }

  &.stale {
    background: color-mix(in srgb, var(--status-warning) 8%, transparent);
    border: 1px solid color-mix(in srgb, var(--status-warning) 22%, transparent);
    .st-icon { color: var(--status-warning); }
  }

  &.no_data {
    background: var(--page-plane);
    border: 1px solid var(--border);
    .st-icon { color: var(--text-muted); }
  }
}

.mbp-headline {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.4;

  strong {
    color: var(--text-primary);
    font-weight: 600;
  }

  .st-icon {
    flex: none;
    margin-top: 2px;
  }
}

.mbp-stats {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 5px;
  font-size: 13px;
  padding-left: 21px; // aligns with headline text (icon width + gap)

  .stat-rate {
    font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
    font-weight: 500;
    color: var(--text-secondary);
  }

  .stat-arr {
    color: var(--text-muted);
  }

  .stat-recv {
    font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
    font-weight: 700;
    color: var(--text-primary);
  }

  .stat-for {
    font-size: 12px;
    color: var(--text-muted);
  }

  .stat-gap {
    font-size: 12px;
    color: var(--text-muted);
  }
}

.mbp-sub {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.4;
  padding-left: 21px;
}

.mbp-negotiate {
  margin-top: 12px;
}

.mbp-negotiate-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 12px;
  font-family: inherit;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 80ms ease, border-color 80ms ease, color 80ms ease;

  &:hover:not(:disabled) {
    background: var(--page-plane);
    color: var(--text-primary);
  }

  &:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }

  &:disabled {
    opacity: 0.6;
    cursor: default;
  }
}
</style>
