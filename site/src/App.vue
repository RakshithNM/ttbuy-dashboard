<script setup lang="ts">
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref, watch } from "vue";
import BestRateTable from "./components/BestRateTable.vue";
import MyBankPanel from "./components/MyBankPanel.vue";
const LineChart = defineAsyncComponent(() => import("./components/LineChart.vue"));
const CalendarHeatmap = defineAsyncComponent(() => import("./components/CalendarHeatmap.vue"));
const CurrencyOptimizer = defineAsyncComponent(() => import("./components/CurrencyOptimizer.vue"));
const BankHeadToHead = defineAsyncComponent(() => import("./components/BankHeadToHead.vue"));
const WhatIfMachine = defineAsyncComponent(() => import("./components/WhatIfMachine.vue"));
const OpportunityCostChart = defineAsyncComponent(() => import("./components/OpportunityCostChart.vue"));
const CumulativeSavingsCalc = defineAsyncComponent(() => import("./components/CumulativeSavingsCalc.vue"));
const RatePercentileTable = defineAsyncComponent(() => import("./components/RatePercentileTable.vue"));
const AllTimeLeaderboard = defineAsyncComponent(() => import("./components/AllTimeLeaderboard.vue"));
const RankBumpChart = defineAsyncComponent(() => import("./components/RankBumpChart.vue"));
const MarkupTrendChart = defineAsyncComponent(() => import("./components/MarkupTrendChart.vue"));
const DayOfWeekChart = defineAsyncComponent(() => import("./components/DayOfWeekChart.vue"));
import { brandColor, isPlatform, isBenchmark, shortName, sortByBankOrder } from "./bankPalette";
import { CREDIT_TIMES } from "./creditTime";
import { currencySymbol, sortByCurrencyOrder } from "./currencies";
import type { BankSeries, FeesByBank, RatesByCurrency, BenchmarksByCurrency } from "./types";
import { useHead } from "@unhead/vue";
import { BANK_PAGES, SITE_URL, bankPagePath } from "./bankPages";

// Set on a bank's own page (see bankPages.ts): the same dashboard, with the
// header, hero and FAQ about this bank instead of the market as a whole.
const props = defineProps<{ bank?: string }>();

import rawRatesData from "../public/data/rates.json";
import holidaysData from "../public/data/holidays.json";
import feesData from "../public/data/fees.json";
import benchmarksData from "../public/data/benchmarks.json";

const rawRates = ref<RatesByCurrency>(rawRatesData as any);
const fees = ref<FeesByBank>(feesData as any);
const benchmarks = ref<BenchmarksByCurrency>(benchmarksData as any);
const loading = ref(false);
const loadError = ref<string | null>(null);
const hidden = ref<Set<string>>(new Set());
const bankQuery = ref("");

type RangeKey = "7d" | "30d" | "90d" | "1y" | "all";
const RANGE_OPTIONS: { key: RangeKey; label: string; days: number | null }[] = [
  { key: "7d", label: "Last 7 days", days: 7 },
  { key: "30d", label: "Last 30 days", days: 30 },
  { key: "90d", label: "Last 90 days", days: 90 },
  { key: "1y", label: "Last 1 year", days: 365 },
  { key: "all", label: "All time", days: null },
];

// Remember the date range and table/chart toggle across visits. localStorage
// can throw (private browsing, disabled storage) — this is a nice-to-have,
// never worth breaking the page over, so every access is best-effort.
const VIEW_STORAGE_KEY = "ttbuy-dashboard:view";
const THEME_STORAGE_KEY = "ttbuy-dashboard:theme";

// Apply stored theme before first paint so there's no flash of wrong theme.
const _storedTheme = (() => {
  try { return localStorage.getItem(THEME_STORAGE_KEY) as "light" | "dark" | null; } catch { return null; }
})();
if (_storedTheme) document.documentElement.setAttribute("data-theme", _storedTheme);
const isDark = ref(
  _storedTheme !== null
    ? _storedTheme === "dark"
    : (typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches)
);

function setThemeColor(dark: boolean) {
  if (typeof document !== "undefined") {
    document.querySelector('meta[name="theme-color"]')
      ?.setAttribute("content", dark ? "#0d0d0d" : "#f9f9f7");
  }
}
setThemeColor(isDark.value);

// Wraps a state change in a View Transition when the browser supports it
// (Firefox doesn't yet) — falls back to applying the change directly.
// prefers-reduced-motion is handled in style.scss, not here, since the
// transition still needs to run to swap the DOM; only its animation is
// disabled for that preference.
function withViewTransition(apply: () => void) {
  if (typeof document !== "undefined" && "startViewTransition" in document) {
    document.startViewTransition(apply);
  } else {
    apply();
  }
}

function toggleTheme() {
  withViewTransition(() => {
    isDark.value = !isDark.value;
    const t = isDark.value ? "dark" : "light";
    if (typeof document !== "undefined") {
      document.documentElement.setAttribute("data-theme", t);
    }
    setThemeColor(isDark.value);
    try { localStorage.setItem(THEME_STORAGE_KEY, t); } catch {}
  });
}

interface StoredView {
  range?: RangeKey;
  showTable?: boolean;
  currency?: string;
  amount?: number;
  deduction?: number;
}

function loadStoredView(): StoredView {
  try {
    const raw = localStorage.getItem(VIEW_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as StoredView) : {};
  } catch {
    return {};
  }
}

// A shared link's query string wins over whatever the visitor had saved
// locally — someone opening a link expects to see the sender's view, not
// their own last one.
function loadQueryView(): StoredView {
  if (typeof window === "undefined") return {};
  const params = new URLSearchParams(window.location.search);
  const view: StoredView = {};

  const range = params.get("range");
  if (range && RANGE_OPTIONS.some((o) => o.key === range)) view.range = range as RangeKey;

  const currency = params.get("currency");
  if (currency) view.currency = currency;

  const shown = params.get("view");
  if (shown === "table" || shown === "chart") view.showTable = shown === "table";

  const amount = params.get("amount");
  if (amount !== null && Number.isFinite(Number(amount)) && Number(amount) >= 0) view.amount = Number(amount);

  const deduct = params.get("deduct");
  if (deduct !== null && Number.isFinite(Number(deduct)) && Number(deduct) >= 0) view.deduction = Number(deduct);

  return view;
}

const storedView = loadStoredView();
const queryView = loadQueryView();

const range = ref<RangeKey>(
  queryView.range ??
    (storedView.range && RANGE_OPTIONS.some((o) => o.key === storedView.range) ? storedView.range : "7d")
);
const showTable = ref(
  queryView.showTable ?? (typeof storedView.showTable === "boolean" ? storedView.showTable : true)
);
const currency = ref<string>(queryView.currency ?? storedView.currency ?? "USD");
const amount = ref<number>(queryView.amount ?? storedView.amount ?? 1000);
// A link that carries an amount but no deduct= means "no deduction", not the
// visitor's own saved one.
const deduction = ref<number>(
  queryView.deduction ?? (queryView.amount !== undefined ? 0 : storedView.deduction ?? 0)
);
// What reaches an Indian bank after sending/intermediary bank fees.
const bankAmount = computed(() => Math.max(0, amount.value - (Number(deduction.value) || 0)));

function setCurrency(code: string) {
  withViewTransition(() => { currency.value = code; });
}

function toggleTableView() {
  withViewTransition(() => { showTable.value = !showTable.value; });
}

// Not persisted — this panel's own range toggle, rendered here so it can
// share a row with the panel title.
const rankRange = ref<"30d" | "90d">("30d");

const MY_BANK_KEY = "ttbuy-dashboard:mybank";
const myBank = ref<string>((() => { try { return localStorage.getItem(MY_BANK_KEY) ?? ""; } catch { return ""; } })());
watch(myBank, (b) => { try { if (b) localStorage.setItem(MY_BANK_KEY, b); else localStorage.removeItem(MY_BANK_KEY); } catch {} });

watch(currency, (c) => {
  // A bank page's title is owned by useHead below.
  if (props.bank) return;
  if (typeof document !== "undefined") {
    document.title = `${c} TT Buy Rate | TTBuy Rates`;
  }
}, { immediate: true });

if (props.bank) {
  const short = shortName(props.bank);
  const url = SITE_URL + bankPagePath(BANK_PAGES.find(b => b.name === props.bank)!.slug);
  const title = `${short} TT Buy Rate Today (USD, GBP, EUR, AED) | TTBuy Rates`;
  const description = `Today's ${props.bank} TT Buy rate for USD, GBP, EUR and AED inward remittances, its fee, and how it ranks against 22+ Indian banks. Updated daily at 11 AM IST.`;
  useHead({
    title,
    link: [{ rel: "canonical", href: url }],
    meta: [
      { name: "description", content: description },
      { property: "og:title", content: title },
      { property: "og:description", content: description },
      { property: "og:url", content: url },
      { name: "twitter:title", content: title },
      { name: "twitter:description", content: description },
    ],
  });
}

watch([range, showTable, currency, amount, deduction], ([r, t, c, a, d]) => {
  try {
    localStorage.setItem(VIEW_STORAGE_KEY, JSON.stringify({ range: r, showTable: t, currency: c, amount: a, deduction: d }));
  } catch {
    // Persistence is best-effort; nothing to do if storage is unavailable.
  }

  // Keep the address bar in sync so the current view is shareable just by
  // copying the URL, not only via the explicit "Copy link" button.
  if (typeof history !== "undefined" && typeof window !== "undefined") {
    const params = new URLSearchParams();
    params.set("currency", c);
    params.set("range", r);
    params.set("view", t ? "table" : "chart");
    params.set("amount", String(a));
    if (Number(d) > 0) params.set("deduct", String(d));
    history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);
  }
}, { immediate: true });

const copied = ref(false);
let copiedTimer: ReturnType<typeof setTimeout> | null = null;
const canNativeShare = typeof navigator !== "undefined" && typeof navigator.share === "function";

async function copyShareLink() {
  if (canNativeShare) {
    try {
      await navigator.share({ title: document.title, url: window.location.href });
    } catch (e) {
      // AbortError = user cancelled the sheet — not an error worth handling.
      // Any other failure falls through to the clipboard path below.
      if (e instanceof Error && e.name === "AbortError") return;
      try { await navigator.clipboard.writeText(window.location.href); } catch {}
    }
    return;
  }
  try {
    await navigator.clipboard.writeText(window.location.href);
    copied.value = true;
    if (copiedTimer) clearTimeout(copiedTimer);
    copiedTimer = setTimeout(() => (copied.value = false), 1800);
  } catch {
    // Clipboard access can fail (permissions, insecure context) — the URL
    // bar already reflects the current view, so this is a convenience on
    // top of that, not the only way to share it.
  }
}

onMounted(async () => {
  // Ensure the currency value is valid on load (in case of cached invalid currency)
  if (!(currency.value in rawRates.value)) {
    currency.value = sortByCurrencyOrder(Object.keys(rawRates.value))[0] ?? "USD";
  }

  // FAQ accordion: only one item open at a time
  if (typeof window !== "undefined") {
    const faqItems = Array.from(document.querySelectorAll<HTMLDetailsElement>(".faq-item"));
    faqItems.forEach(item => {
      item.addEventListener("toggle", () => {
        if (item.open) {
          faqItems.forEach(other => { if (other !== item) other.open = false; });
        }
      });
    });
  }

  // Fade-in panels that start below the fold
  if (typeof window !== "undefined" && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    const vh = window.innerHeight;
    const panels = Array.from(document.querySelectorAll<HTMLElement>(".panel"));
    const belowFold = panels.filter(p => p.getBoundingClientRect().top > vh + 40);
    belowFold.forEach(p => {
      p.style.opacity = "0";
      p.style.transform = "translateY(12px)";
      p.style.transition = "opacity 380ms ease, transform 380ms ease";
    });
    if (belowFold.length > 0) {
      const observer = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            if (entry.isIntersecting) {
              const el = entry.target as HTMLElement;
              el.style.opacity = "";
              el.style.transform = "";
              observer.unobserve(entry.target);
            }
          }
        },
        { threshold: 0.06 }
      );
      belowFold.forEach(p => observer.observe(p));
    }
  }
});

const availableCurrencies = computed(() => sortByCurrencyOrder(Object.keys(rawRates.value)));

const bankRates = computed(() => rawRates.value[currency.value] ?? {});

const allSeries = computed<BankSeries[]>(() => {
  const banks = sortByBankOrder(Object.keys(bankRates.value));
  const raw = banks.map((name) => ({
    name,
    color: brandColor(name),
    wrapped: false,
    points: bankRates.value[name] ?? [],
    category: (isBenchmark(name) ? "benchmark" : isPlatform(name) ? "platform" : "bank") as "bank" | "platform" | "benchmark",
  }));

  // Find the first date where ≥11 banks reported — everything before that is
  // sparse Wayback backfill and is trimmed so all series start from the same
  // epoch and cross-bank comparisons are apples-to-apples.
  const dateCount = new Map<string, number>();
  for (const s of raw) {
    if (s.category !== "bank") continue;
    for (const p of s.points) dateCount.set(p.date, (dateCount.get(p.date) ?? 0) + 1);
  }
  const fullDataStart = [...dateCount.entries()]
    .filter(([, n]) => n >= 11)
    .map(([d]) => d)
    .sort()[0] ?? null;

  if (!fullDataStart) return raw;
  return raw.map((s) => ({
    ...s,
    points: s.points.filter((p) => p.date >= fullDataStart),
  }));
});

// Matches against both the full and short bank name, so "SBI" finds
// "State Bank of India" and vice versa.
const searchedSeries = computed<BankSeries[]>(() => {
  const q = bankQuery.value.trim().toLowerCase();
  if (!q) return allSeries.value;
  return allSeries.value.filter(
    (s) => s.name.toLowerCase().includes(q) || shortName(s.name).toLowerCase().includes(q)
  );
});

const filteredSeries = computed<BankSeries[]>(() => {
  const opt = RANGE_OPTIONS.find((o) => o.key === range.value);
  if (!opt || opt.days === null) return searchedSeries.value;

  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - opt.days);
  const cutoffStr = cutoff.toISOString().slice(0, 10);

  return searchedSeries.value.map((s) => ({
    ...s,
    points: s.points.filter((p) => p.date >= cutoffStr),
  }));
});

function toggleBank(name: string) {
  const next = new Set(hidden.value);
  if (next.has(name)) next.delete(name);
  else next.add(name);
  hidden.value = next;
}

const MAX_COMPARE = 4;
const compareMode = ref(false);
const compareSelected = ref<Set<string>>(new Set());

// Date-range filtered (no search filter) — chart base for compare mode so
// users can pick any bank regardless of what's in the search box.
const dateFilteredSeries = computed<BankSeries[]>(() => {
  const opt = RANGE_OPTIONS.find(o => o.key === range.value);
  if (!opt || opt.days === null) return allSeries.value;
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - opt.days);
  const cutoffStr = cutoff.toISOString().slice(0, 10);
  return allSeries.value.map(s => ({
    ...s,
    points: s.points.filter(p => p.date >= cutoffStr),
  }));
});

// All series sorted by most recent rate for the compare picker chip list.
const comparableSeriesSorted = computed(() =>
  allSeries.value.slice().sort((a, b) => {
    const aRate = a.points.at(-1)?.ttbuy ?? 0;
    const bRate = b.points.at(-1)?.ttbuy ?? 0;
    return bRate - aRate;
  })
);

// Series fed to the chart — normal mode uses the search+date filtered set;
// compare mode uses date-filtered only, restricted to the selected banks.
const chartSeries = computed<BankSeries[]>(() => {
  if (!compareMode.value || compareSelected.value.size === 0) return filteredSeries.value;
  return dateFilteredSeries.value.filter(s => compareSelected.value.has(s.name));
});

// In compare mode the hidden set is irrelevant — the picker is the selector.
const chartHidden = computed(() => compareMode.value ? new Set<string>() : hidden.value);

function enterCompareMode() {
  const top3 = dateFilteredSeries.value
    .filter(s => s.category === "bank" && s.points.length > 0)
    .sort((a, b) => (b.points.at(-1)?.ttbuy ?? 0) - (a.points.at(-1)?.ttbuy ?? 0))
    .slice(0, 3)
    .map(s => s.name);
  compareSelected.value = new Set(top3);
  compareMode.value = true;
}

function exitCompareMode() {
  compareMode.value = false;
  compareSelected.value = new Set();
}

// Only the direct user click gets a transition — enterCompareMode/
// exitCompareMode are also called from the currency-change watch below,
// which already runs inside setCurrency's own transition; nesting a second
// startViewTransition into that would fight the first one.
function toggleCompareMode() {
  withViewTransition(() => {
    if (compareMode.value) exitCompareMode(); else enterCompareMode();
  });
}

function toggleCompareBank(name: string) {
  const next = new Set(compareSelected.value);
  if (next.has(name)) next.delete(name);
  else if (next.size < MAX_COMPARE) next.add(name);
  compareSelected.value = next;
}

// Reset compare state when currency changes — selected banks are currency-specific.
watch(currency, () => { if (compareMode.value) exitCompareMode(); });

interface DowInsight { day: string; diffPaise: number; }

const dowInsight = computed<DowInsight | null>(() => {
  const bankSeries = allSeries.value.filter(s => s.category === "bank");
  if (!bankSeries.length) return null;

  // Track both the peak rate and the number of reporting banks per date.
  // We want to ignore early sparse data (e.g. before July 28) when calculating trends.
  const dateEntries = new Map<string, number>();
  const dateMax = new Map<string, number>();
  for (const s of bankSeries) {
    for (const p of s.points) {
      dateEntries.set(p.date, (dateEntries.get(p.date) ?? 0) + 1);
      const curr = dateMax.get(p.date) ?? 0;
      if (p.ttbuy > curr) dateMax.set(p.date, p.ttbuy);
    }
  }

  const majorityThreshold = Math.floor(bankSeries.length / 2) + 1;
  const sortedDates = [...dateEntries.keys()].sort();
  const firstValidDate = sortedDates.find(d => dateEntries.get(d)! >= majorityThreshold);

  if (!firstValidDate) return null;

  for (const date of dateMax.keys()) {
    if (date < firstValidDate) {
      dateMax.delete(date);
    }
  }

  if (dateMax.size < 14) return null;

  const DAY_NAMES = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];
  const totals = new Array(7).fill(0);
  const counts = new Array(7).fill(0);
  for (const [date, rate] of dateMax) {
    const [y, m, d] = date.split("-").map(Number);
    totals[new Date(y, m - 1, d).getDay()] += rate;
    counts[new Date(y, m - 1, d).getDay()]++;
  }

  const avgs = totals.map((t, i) => counts[i] >= 4 ? t / counts[i] : null);
  const valid = avgs.filter((a): a is number => a !== null);
  if (valid.length < 4) return null;

  const overallAvg = valid.reduce((a, b) => a + b) / valid.length;
  let bestDay = -1, bestAvg = -Infinity;
  avgs.forEach((a, i) => { if (a !== null && a > bestAvg) { bestAvg = a; bestDay = i; } });
  if (bestDay === -1) return null;

  const diff = bestAvg - overallAvg;
  if (diff < 0.02) return null;
  return { day: DAY_NAMES[bestDay], diffPaise: Math.round(diff * 100) };
});

interface WeekInsight { week: 1 | 2 | 3 | 4; diffPaise: number; }

// Groups qualifying days by week-of-month (W1=days 1–7, W2=8–14, W3=15–21,
// W4=22+) and surfaces the week that averages highest. Requires 60 qualifying
// days (~3 full months) AND 3+ occurrences in every week slot so each bucket
// is statistically comparable. Will be silent until roughly end of October.
const weekInsight = computed<WeekInsight | null>(() => {
  const bankSeries = allSeries.value.filter(s => s.category === "bank");
  if (!bankSeries.length) return null;

  const majorityThreshold = Math.floor(bankSeries.length / 2) + 1;
  const dateEntries = new Map<string, number>();
  const dateMax = new Map<string, number>();
  for (const s of bankSeries) {
    for (const p of s.points) {
      dateEntries.set(p.date, (dateEntries.get(p.date) ?? 0) + 1);
      const curr = dateMax.get(p.date) ?? 0;
      if (p.ttbuy > curr) dateMax.set(p.date, p.ttbuy);
    }
  }

  const sortedDates = [...dateEntries.keys()].sort();
  const firstValidDate = sortedDates.find(d => dateEntries.get(d)! >= majorityThreshold);
  if (!firstValidDate) return null;
  for (const date of dateMax.keys()) {
    if (date < firstValidDate) dateMax.delete(date);
  }

  if (dateMax.size < 60) return null;

  const totals = [0, 0, 0, 0];
  const counts = [0, 0, 0, 0];
  for (const [date, rate] of dateMax) {
    const day = Number(date.split("-")[2]);
    const slot = Math.min(Math.floor((day - 1) / 7), 3);
    totals[slot] += rate;
    counts[slot]++;
  }

  if (counts.some(c => c < 3)) return null;

  const avgs = totals.map((t, i) => t / counts[i]);
  const overallAvg = avgs.reduce((a, b) => a + b) / 4;
  let bestSlot = 0;
  for (let i = 1; i < 4; i++) {
    if (avgs[i] > avgs[bestSlot]) bestSlot = i;
  }

  const diff = avgs[bestSlot] - overallAvg;
  if (diff < 0.02) return null;
  return { week: (bestSlot + 1) as 1 | 2 | 3 | 4, diffPaise: Math.round(diff * 100) };
});

function exportCsv() {
  const base = dateFilteredSeries.value.filter(s => s.category === "bank");
  const series = compareMode.value && compareSelected.value.size > 0
    ? base.filter(s => compareSelected.value.has(s.name))
    : base;
  if (!series.length) return;

  const dates = [...new Set(series.flatMap(s => s.points.map(p => p.date)))].sort();
  const lookup: Record<string, Record<string, number | undefined>> = {};
  for (const s of series) {
    lookup[s.name] = {};
    for (const p of s.points) lookup[s.name][p.date] = p.ttbuy;
  }

  const header = ["Date", ...series.map(s => s.name)].join(",");
  const rows = dates.map(d => [d, ...series.map(s => lookup[s.name][d] ?? "")].join(","));
  const csv = [header, ...rows].join("\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `ttbuy-${currency.value}-${range.value}-rates.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

const lastUpdated = computed(() => {
  const dates = allSeries.value.flatMap((s) => s.points.map((p) => p.date));
  if (dates.length === 0) return null;
  return dates.sort().at(-1) ?? null;
});

const lastUpdatedFormatted = computed(() => {
  if (!lastUpdated.value) return null;
  const [year, month, day] = lastUpdated.value.split("-").map(Number);
  const MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];
  return `${MONTHS[month - 1]} ${day}, ${year}`;
});

const holidayMap = Object.fromEntries(
  (holidaysData.holidays as { date: string; name: string }[]).map(h => [h.date, h.name])
);

const stalenessReason = computed(() => {
  if (!lastUpdated.value) return null;
  const today = new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });

  // Always surface holidays — even if some banks updated, coverage may be partial
  if (holidayMap[today]) {
    return { type: "holiday" as const, name: holidayMap[today], partial: lastUpdated.value >= today };
  }

  if (lastUpdated.value >= today) return null;

  const d = new Date(today + "T00:00:00");
  const dow = d.getDay();
  if (dow === 0) return { type: "sunday" as const, partial: false };
  if (dow === 6 && [2, 4].includes(Math.ceil(d.getDate() / 7))) return { type: "bank-saturday" as const, partial: false };

  return null;
});

// Hero summary: best bank by net receive, using each bank's latest reading
// (the same ranking as the "Best value today" table), compared against the
// user's own bank when set, otherwise against the average bank.
interface HeroSummary {
  best: { name: string; color: string; ttbuy: number; net: number; date: string };
  compare:
    | { kind: "mine"; name: string; gain: number }
    | { kind: "is-mine" }
    | { kind: "average"; gain: number };
  isStale: boolean;
}

interface NetRow { name: string; color: string; ttbuy: number; net: number; date: string }

// Every bank's latest reading, ranked by net receive (best first).
const netRows = computed<NetRow[]>(() => {
  return allSeries.value
    .filter(s => s.category === "bank" && s.points.length > 0)
    .map(s => {
      const pt = s.points.at(-1)!;
      const gross = pt.ttbuy * bankAmount.value;
      const fee = fees.value[s.name];
      let feeInr = 0;
      if (fee?.fee_slabs) {
        for (const sl of fee.fee_slabs) {
          if (sl.up_to === null || gross <= sl.up_to) { feeInr = sl.fee_inr; break; }
        }
      } else {
        feeInr = fee?.fee_inr ?? 0;
      }
      return { name: s.name, color: brandColor(s.name), ttbuy: pt.ttbuy, net: gross - feeInr, date: pt.date };
    })
    .sort((a, b) => b.net - a.net);
});

const heroSummary = computed<HeroSummary | null>(() => {
  const rows = netRows.value;
  if (rows.length < 2 || !(amount.value > 0)) return null;
  const best = rows[0];
  const latest = rows.reduce((d, r) => (r.date > d ? r.date : d), "");

  let compare: HeroSummary["compare"];
  const mine = myBank.value ? rows.find(r => r.name === myBank.value) : undefined;
  if (mine && mine.name === best.name) {
    compare = { kind: "is-mine" };
  } else if (mine) {
    compare = { kind: "mine", name: mine.name, gain: best.net - mine.net };
  } else {
    const avg = rows.reduce((sum, r) => sum + r.net, 0) / rows.length;
    compare = { kind: "average", gain: best.net - avg };
  }

  return { best, compare, isStale: best.date < latest };
});

// Hero on a bank page: this bank's latest reading, its rank, and the gap to
// the best bank.
interface BankHero { me: NetRow; rank: number; total: number; best: NetRow; isStale: boolean }

const bankHero = computed<BankHero | null>(() => {
  if (!props.bank || !(amount.value > 0)) return null;
  const rows = netRows.value;
  const i = rows.findIndex(r => r.name === props.bank);
  if (i < 0 || rows.length < 2) return null;
  const latest = rows.reduce((d, r) => (r.date > d ? r.date : d), "");
  return { me: rows[i], rank: i + 1, total: rows.length, best: rows[0], isStale: rows[i].date < latest };
});

// Plain-text answers about this bank across all currencies, for the FAQ.
// Built from the raw data so they don't follow the currency toggle.
interface BankRateFact { code: string; ttbuy: number; date: string; best: { name: string; ttbuy: number } | null }

const bankRateFacts = computed<BankRateFact[]>(() => {
  const bank = props.bank;
  if (!bank) return [];
  const facts: BankRateFact[] = [];
  for (const code of availableCurrencies.value) {
    const byBank = rawRates.value[code] ?? {};
    const pt = byBank[bank]?.at(-1);
    if (!pt) continue;
    // Best bank on the same date, so a stale reading isn't compared with a
    // fresher one.
    let best: BankRateFact["best"] = null;
    for (const [name, points] of Object.entries(byBank)) {
      if (isPlatform(name) || isBenchmark(name)) continue;
      const same = points.find(p => p.date === pt.date);
      if (same && (!best || same.ttbuy > best.ttbuy)) best = { name, ttbuy: same.ttbuy };
    }
    facts.push({ code, ttbuy: pt.ttbuy, date: pt.date, best });
  }
  return facts;
});

const bankFee = computed(() => (props.bank ? fees.value[props.bank] : undefined));

function fmtLongDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  const MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];
  return `${MONTHS[m - 1]} ${d}, ${y}`;
}

// Short reason shown in the hero's stale badge, e.g. "Oct 1 rate · Gandhi Jayanti".
const heroStaleReason = computed<string | null>(() => {
  const r = stalenessReason.value;
  if (!r) return null;
  if (r.type === "holiday") return r.name;
  if (r.type === "sunday") return "Sunday";
  return "Bank holiday";
});

// When the hero badge already explains the holiday, the separate line below
// the hero would repeat it.
const heroCoversStaleness = computed(() =>
  !!(props.bank ? bankHero.value?.isStale : heroSummary.value?.isStale) && !!heroStaleReason.value
);

// Bank name in the hero jumps to (and briefly highlights) that bank's row.
function goToBankRow(name: string) {
  const row = document.querySelector<HTMLElement>(`tr[data-bank="${CSS.escape(name)}"]`);
  if (!row) return;
  const panel = row.closest<HTMLElement>(".panel");
  if (panel) { panel.style.opacity = ""; panel.style.transform = ""; }
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  row.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "center" });
  row.classList.remove("row-flash");
  void row.offsetWidth;
  row.classList.add("row-flash");
  window.setTimeout(() => row.classList.remove("row-flash"), 1800);
}

// Whole units in the headline: "$2,524", not "$2,524.3".
const heroAmount = computed(() => Math.round(amount.value).toLocaleString("en-IN"));

function fmtShortDate(iso: string): string {
  const [, m, d] = iso.split("-").map(Number);
  return `${["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][m - 1]} ${d}`;
}

// Sticky section nav: one link per group of panels. The active link is the
// last group whose anchor has scrolled past the nav bar.
const SECTION_GROUPS = [
  { id: "today", label: "Today" },
  { id: "history", label: "History" },
  { id: "rankings", label: "Rankings" },
  { id: "trends", label: "Trends" },
  { id: "tools", label: "Tools" },
  { id: "faq", label: "FAQ" },
] as const;

const activeSection = ref<string>("today");
const NAV_OFFSET = 72;

function updateActiveSection() {
  let current: string = SECTION_GROUPS[0].id;
  for (const g of SECTION_GROUPS) {
    const el = document.getElementById(g.id);
    if (el && el.getBoundingClientRect().top - NAV_OFFSET <= 1) current = g.id;
  }
  // At the very bottom the last short group can never reach the top.
  if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2) {
    current = SECTION_GROUPS[SECTION_GROUPS.length - 1].id;
  }
  activeSection.value = current;
}

// After a jump, panels above the target finish rendering (content-visibility
// placeholders, lazy components) and push it down; scroll anchoring doesn't
// catch this. Re-align for a short window, and stop as soon as the user
// takes over the scroll.
let stopHolding: (() => void) | null = null;

function holdSectionInPlace(el: HTMLElement) {
  stopHolding?.();
  const STOP_EVENTS = ["wheel", "touchstart", "keydown", "pointerdown"] as const;
  const timers: number[] = [];
  const stop = () => {
    timers.forEach(clearTimeout);
    STOP_EVENTS.forEach(e => window.removeEventListener(e, stop));
    if (stopHolding === stop) stopHolding = null;
  };
  stopHolding = stop;
  STOP_EVENTS.forEach(e => window.addEventListener(e, stop, { passive: true }));
  const target = parseFloat(getComputedStyle(el).scrollMarginTop) || 0;
  for (const ms of [100, 300, 600, 1000, 1500]) {
    timers.push(window.setTimeout(() => {
      if (Math.abs(el.getBoundingClientRect().top - target) > 2) {
        el.scrollIntoView({ block: "start" });
      }
      if (ms === 1500) stop();
    }, ms));
  }
}

function goToSection(id: string) {
  const el = document.getElementById(id);
  if (!el) return;
  // Below-fold panels are faded in by an observer; clear that so a jump
  // never lands on an invisible panel.
  el.style.opacity = "";
  el.style.transform = "";
  // Instant jump inside a View Transition (cross-fade) instead of a smooth
  // scroll: jumps can span ~8000px, and content-visibility:auto panels only
  // have estimated heights, so a long smooth scroll can land off-target.
  // Reduced motion is handled by the ::view-transition rule in style.scss.
  // Set the active link inside the same update so the transition's "new"
  // snapshot already shows it, instead of waiting for the scroll handler.
  withViewTransition(() => {
    el.scrollIntoView({ block: "start" });
    activeSection.value = id;
  });
  holdSectionInPlace(el);
  history.replaceState(null, "", `${location.pathname}${location.search}#${id}`);
}

let navTicking = false;
function onScrollNav() {
  if (navTicking) return;
  navTicking = true;
  requestAnimationFrame(() => {
    navTicking = false;
    updateActiveSection();
  });
}

onMounted(() => {
  window.addEventListener("scroll", onScrollNav, { passive: true });
  updateActiveSection();
});

onBeforeUnmount(() => window.removeEventListener("scroll", onScrollNav));

interface ConsistencyResult { bank: string; count: number; total: number; since: string | null }

const consistencyBadge = computed<ConsistencyResult | null>(() => {
  const opt = RANGE_OPTIONS.find(o => o.key === range.value);
  const cutoffStr = opt?.days != null
    ? (() => { const d = new Date(); d.setDate(d.getDate() - opt.days!); return d.toISOString().slice(0, 10); })()
    : null;

  // Collect all entries per date across all banks (ignoring search filter).
  const bankSeries = allSeries.value.filter(s => s.category === "bank");
  const dateEntries = new Map<string, { bank: string; rate: number }[]>();
  for (const s of bankSeries) {
    for (const pt of s.points) {
      if (cutoffStr && pt.date < cutoffStr) continue;
      const list = dateEntries.get(pt.date) ?? [];
      list.push({ bank: s.name, rate: pt.ttbuy });
      dateEntries.set(pt.date, list);
    }
  }

  // Only count days where a majority of banks have data — days with only a
  // handful of scraped entries (Wayback backfill gaps, scrapers failing) would
  // make any "winner" trivially whoever showed up, not who was actually best.
  const majorityThreshold = Math.floor(bankSeries.length / 2) + 1;
  const wins: Record<string, number> = {};
  let qualifyingDays = 0;
  let firstQualifyingDate: string | null = null;

  for (const [date, entries] of [...dateEntries.entries()].sort(([a], [b]) => a.localeCompare(b))) {
    if (entries.length < majorityThreshold) continue;
    qualifyingDays++;
    if (!firstQualifyingDate) firstQualifyingDate = date;
    const best = entries.reduce((a, b) => a.rate >= b.rate ? a : b);
    wins[best.bank] = (wins[best.bank] ?? 0) + 1;
  }

  if (qualifyingDays === 0) return null;

  let topBank: string | null = null;
  let topCount = 0;
  for (const [bank, count] of Object.entries(wins)) {
    if (count > topCount) { topCount = count; topBank = bank; }
  }

  return topBank ? { bank: topBank, count: topCount, total: qualifyingDays, since: firstQualifyingDate } : null;
});

interface TodaySignal {
  todayBest: number;
  avgBest: number;
  daysCount: number;
  direction: "above" | "below" | "near";
  trend: "up" | "down" | "flat";
}

const todaySignal = computed<TodaySignal | null>(() => {
  const bankSeries = allSeries.value.filter(s => s.category === "bank");
  if (!bankSeries.length) return null;

  const majorityThreshold = Math.floor(bankSeries.length / 2) + 1;

  const dateEntries = new Map<string, number[]>();
  for (const s of bankSeries) {
    for (const pt of s.points) {
      const arr = dateEntries.get(pt.date) ?? [];
      arr.push(pt.ttbuy);
      dateEntries.set(pt.date, arr);
    }
  }

  const qualifyingDates = [...dateEntries.entries()]
    .filter(([, rates]) => rates.length >= majorityThreshold)
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-7);

  if (qualifyingDates.length < 2) return null;

  const dailyBests = qualifyingDates.map(([, rates]) => Math.max(...rates));
  const todayBest = dailyBests[dailyBests.length - 1];
  const avgBest = dailyBests.reduce((s, v) => s + v, 0) / dailyBests.length;

  const diff = todayBest - avgBest;
  const threshold = 0.05;
  const direction: TodaySignal["direction"] = diff > threshold ? "above" : diff < -threshold ? "below" : "near";

  const trendDiff = dailyBests[dailyBests.length - 1] - dailyBests[0];
  const trend: TodaySignal["trend"] = trendDiff > threshold ? "up" : trendDiff < -threshold ? "down" : "flat";

  return { todayBest, avgBest, daysCount: dailyBests.length, direction, trend };
});

interface StableBankResult {
  bank: string;
  color: string;
  variation: number;
  runner: { bank: string; variation: number } | null;
  topN: number;
}

// Among the top-N banks by average rate in the current period, find which had
// the narrowest rate range (max - min). Only compares banks that actually
// rated in the top tier — avoids naming a stable bank whose rates are low.
const stableBank = computed<StableBankResult | null>(() => {
  const bankSeries = filteredSeries.value.filter(
    s => s.category === "bank" && s.points.length >= 3
  );
  if (bankSeries.length < 3) return null;

  const topN = Math.min(5, bankSeries.length);
  const candidates = [...bankSeries]
    .map(s => ({
      name: s.name,
      color: s.color,
      avg: s.points.reduce((sum, p) => sum + p.ttbuy, 0) / s.points.length,
    }))
    .sort((a, b) => b.avg - a.avg)
    .slice(0, topN)
    .map(({ name, color }) => {
      const pts = bankSeries.find(b => b.name === name)!.points.map(p => p.ttbuy);
      return { bank: name, color, variation: Math.max(...pts) - Math.min(...pts) };
    })
    .sort((a, b) => a.variation - b.variation);

  if (candidates.length < 2) return null;
  return {
    bank: candidates[0].bank,
    color: candidates[0].color,
    variation: candidates[0].variation,
    runner: candidates[1],
    topN,
  };
});
</script>

<template>
  <header class="page-header">
    <p class="eyebrow">
      <template v-if="bank"><a href="/" class="eyebrow-link">All banks</a> / {{ shortName(bank) }}</template>
      <template v-else>Foreign earnings in India</template>
    </p>
    <template v-if="bank">
      <h1>{{ shortName(bank) }} TT Buy rate today</h1>
      <p class="lede">
        {{ bank }} sets its own TT Buy rate when foreign currency arrives in your
        account. See today's {{ shortName(bank) }} rate for {{ currency }}, how it
        ranks against 22+ Indian banks, and how it has moved over time.
      </p>
    </template>
    <template v-else>
      <h1>Which Indian bank pays you the most for your {{ currency }} transfer?</h1>
      <p class="lede">
        Your bank sets its own rate when foreign currency arrives in your account. That
        rate varies by hundreds of rupees per $1,000 across banks. We track 22+ Indian
        banks daily so you can see who pays you the most, right now and over time.
      </p>
    </template>
    <div v-if="!loading && bank && bankHero" class="hero-card">
      <div class="hero-top">
        <span class="hero-label">{{ shortName(bank) }} right now · #{{ bankHero.rank }} of {{ bankHero.total }} banks</span>
        <span v-if="bankHero.isStale" class="hero-stale">
          {{ fmtShortDate(bankHero.me.date) }} rate<template v-if="heroStaleReason"> · {{ heroStaleReason }}</template>
        </span>
      </div>
      <div class="hero-body">
        <div class="hero-main">
          <button
            type="button"
            class="hero-bank"
            :title="`Show ${shortName(bank)} in the table`"
            @click="goToBankRow(bank)"
          >
            <span class="hero-dot" :style="{ background: bankHero.me.color }" aria-hidden="true"></span>
            {{ shortName(bank) }}
            <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
              <path d="M6 4l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
          <span class="hero-rate">₹{{ bankHero.me.ttbuy.toFixed(2) }} per {{ currency }}</span>
        </div>
        <div class="hero-figures">
          <div class="hero-figure">
            <span class="hero-figure-label">On {{ currencySymbol(currency) }}{{ heroAmount }} you get</span>
            <span class="hero-figure-value">₹{{ Math.round(bankHero.me.net).toLocaleString('en-IN') }}</span>
          </div>
          <div v-if="bankHero.rank === 1" class="hero-figure hero-figure--gain">
            <span class="hero-figure-label">Among all banks</span>
            <span class="hero-figure-value">Best today</span>
          </div>
          <div v-else-if="bankHero.best.net - bankHero.me.net >= 1" class="hero-figure hero-figure--loss">
            <span class="hero-figure-label">vs best bank ({{ shortName(bankHero.best.name) }})</span>
            <span class="hero-figure-value">−₹{{ Math.round(bankHero.best.net - bankHero.me.net).toLocaleString('en-IN') }}</span>
          </div>
        </div>
      </div>
    </div>
    <div v-else-if="!loading && !bank && heroSummary" class="hero-card">
      <div class="hero-top">
        <span class="hero-label">Best bank right now</span>
        <span v-if="heroSummary.isStale" class="hero-stale">
          {{ fmtShortDate(heroSummary.best.date) }} rate<template v-if="heroStaleReason"> · {{ heroStaleReason }}</template>
        </span>
      </div>
      <div class="hero-body">
        <div class="hero-main">
          <button
            type="button"
            class="hero-bank"
            :title="`Show ${shortName(heroSummary.best.name)} in the table`"
            @click="goToBankRow(heroSummary.best.name)"
          >
            <span class="hero-dot" :style="{ background: heroSummary.best.color }" aria-hidden="true"></span>
            {{ shortName(heroSummary.best.name) }}
            <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
              <path d="M6 4l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
          <span class="hero-rate">₹{{ heroSummary.best.ttbuy.toFixed(2) }} per {{ currency }}</span>
        </div>
        <div class="hero-figures">
          <div class="hero-figure">
            <span class="hero-figure-label">On {{ currencySymbol(currency) }}{{ heroAmount }} you get</span>
            <span class="hero-figure-value">₹{{ Math.round(heroSummary.best.net).toLocaleString('en-IN') }}</span>
          </div>
          <div v-if="heroSummary.compare.kind === 'is-mine'" class="hero-figure hero-figure--gain">
            <span class="hero-figure-label">Your bank</span>
            <span class="hero-figure-value">Best today</span>
          </div>
          <div v-else-if="heroSummary.compare.gain >= 1" class="hero-figure hero-figure--gain">
            <span class="hero-figure-label">
              <template v-if="heroSummary.compare.kind === 'mine'">vs your bank ({{ shortName(heroSummary.compare.name) }})</template>
              <template v-else>vs the average bank</template>
            </span>
            <span class="hero-figure-value">+₹{{ Math.round(heroSummary.compare.gain).toLocaleString('en-IN') }}</span>
          </div>
        </div>
      </div>
    </div>
    <p v-if="lastUpdated && !heroCoversStaleness" class="updated" :class="{ 'updated--holiday': stalenessReason?.type === 'holiday' }">
      <template v-if="stalenessReason?.type === 'holiday'">
        Today is a bank holiday ({{ stalenessReason.name }}) —
        {{ stalenessReason.partial ? 'some banks may not publish rates today.' : 'rates were last updated ' + lastUpdatedFormatted + '.' }}
      </template>
      <template v-else-if="stalenessReason?.type === 'sunday'">
        Banks are closed on Sundays — rates were last updated {{ lastUpdatedFormatted }}.
      </template>
      <template v-else-if="stalenessReason?.type === 'bank-saturday'">
        Banks close on the 2nd and 4th Saturday — rates were last updated {{ lastUpdatedFormatted }}.
      </template>
      <template v-else>
        Rates last updated {{ lastUpdatedFormatted }}. Scraped at 11 AM IST. Banks typically publish by 10 AM IST.
      </template>
    </p>
  </header>

  <nav v-if="!loading && !loadError" class="section-nav" aria-label="Page sections">
    <a
      v-for="g in SECTION_GROUPS"
      :key="g.id"
      :href="`#${g.id}`"
      class="section-nav-link"
      :class="{ active: activeSection === g.id }"
      :aria-current="activeSection === g.id ? 'true' : undefined"
      @click.prevent="goToSection(g.id)"
    >{{ g.label }}</a>
  </nav>

  <main v-if="!loading && !loadError">
    <MyBankPanel v-model:my-bank="myBank" :series="allSeries" :fees="fees" :currency="currency" :amount="amount" :deduction="deduction" />

    <div class="toolbar">
      <div v-if="availableCurrencies.length > 1" class="currency-filter" role="group" aria-label="Currency">
        <button
          v-for="code in availableCurrencies"
          :key="code"
          type="button"
          class="currency-btn"
          :class="{ active: currency === code }"
          :aria-pressed="currency === code"
          @click="setCurrency(code)"
        >
          {{ code }}
        </button>
      </div>
      <div class="bank-search">
        <svg class="search-icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
          <circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" stroke-width="1.5" />
          <line x1="11" y1="11" x2="14.5" y2="14.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
        </svg>
        <input v-model="bankQuery" type="search" name="bank-search" placeholder="Search banks…" aria-label="Search banks" class="bank-search-input" />
        <button v-if="bankQuery" type="button" class="clear-search" aria-label="Clear search" @click="bankQuery = ''">✕</button>
      </div>
      <button type="button" class="export-btn" :title="`Download ${currency} rates as CSV`" @click="exportCsv">
        <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">
          <path d="M8 2v8M5 7l3 3 3-3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M3 12h10" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        CSV
      </button>
      <button type="button" class="share-btn" :class="{ copied }" @click="copyShareLink">
        <svg v-if="canNativeShare" viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">
          <path d="M8 1v9M5 4l3-3 3 3" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M3 10v4h10v-4" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <svg v-else viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">
          <path
            d="M6.5 9.5l3-3M6.8 5.3l.9-.9a2.2 2.2 0 013.1 3.1l-.9.9M9.2 10.7l-.9.9a2.2 2.2 0 01-3.1-3.1l.9-.9"
            fill="none"
            stroke="currentColor"
            stroke-width="1.4"
            stroke-linecap="round"
          />
        </svg>
        {{ canNativeShare ? "Share" : (copied ? "Copied!" : "Copy link") }}
      </button>
      <button
        type="button"
        class="theme-toggle"
        :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
        @click="toggleTheme"
      >
        <Transition name="icon-swap" mode="out-in">
          <svg v-if="isDark" key="sun" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
            <circle cx="8" cy="8" r="3" fill="none" stroke="currentColor" stroke-width="1.4"/>
            <g stroke="currentColor" stroke-width="1.4" stroke-linecap="round">
              <line x1="8" y1="1.5" x2="8" y2="3"/>
              <line x1="8" y1="13" x2="8" y2="14.5"/>
              <line x1="1.5" y1="8" x2="3" y2="8"/>
              <line x1="13" y1="8" x2="14.5" y2="8"/>
              <line x1="3.4" y1="3.4" x2="4.4" y2="4.4"/>
              <line x1="11.6" y1="11.6" x2="12.6" y2="12.6"/>
              <line x1="12.6" y1="3.4" x2="11.6" y2="4.4"/>
              <line x1="4.4" y1="11.6" x2="3.4" y2="12.6"/>
            </g>
          </svg>
          <svg v-else key="moon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
            <path d="M13 10.5a6 6 0 0 1-7.5-7.5A5.5 5.5 0 1 0 13 10.5z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/>
          </svg>
        </Transition>
      </button>
    </div>
    <p v-if="bankQuery && searchedSeries.length === 0" class="no-results">No banks match "{{ bankQuery }}".</p>

    <section id="today" class="panel" style="--cv-size: 2000px">
      <h2>Best value today</h2>
      <BestRateTable v-model:amount="amount" v-model:deduction="deduction" :series="filteredSeries" :currency="currency" :fees="fees" :benchmarks="benchmarks" :credit-times="CREDIT_TIMES" :consistency="consistencyBadge" :dow-insight="dowInsight" :week-insight="weekInsight" :range="range" :today-signal="todaySignal" :stable-bank="stableBank" />
      <p class="panel-footnote">Published retail TT Buy rates. Corporate and HNI rates are negotiated separately and may differ.</p>
    </section>

    <section id="history" class="panel" style="--cv-size: 550px">
      <div class="panel-header">
        <h2>Historical TT Buy rate</h2>
        <div class="chart-controls">
          <div class="range-filter" role="group" aria-label="Date range">
            <button
              v-for="opt in RANGE_OPTIONS"
              :key="opt.key"
              type="button"
              class="range-btn"
              :class="{ active: range === opt.key }"
              :aria-pressed="range === opt.key"
              @click="range = opt.key"
            >
              {{ opt.label }}
            </button>
          </div>
          <button
            type="button"
            class="compare-btn"
            :class="{ active: compareMode }"
            @click="toggleCompareMode"
          >
            <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">
              <path d="M2 12l3-5 3 3 4-7" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M2 14l3-3 3 2 4-4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.5"/>
            </svg>
            {{ compareMode ? "Exit compare" : "Compare" }}
          </button>
          <button type="button" class="table-toggle" @click="toggleTableView">
            {{ showTable ? "Chart view" : "Table view" }}
          </button>
        </div>
      </div>
      <div v-if="compareMode" class="compare-picker">
        <p class="compare-meta">
          <strong>{{ compareSelected.size }}</strong> of {{ MAX_COMPARE }} selected
          <span v-if="compareSelected.size >= MAX_COMPARE" class="compare-full-hint">(deselect one to swap)</span>
        </p>
        <div class="compare-chips" role="group" aria-label="Select banks to compare">
          <button
            v-for="s in comparableSeriesSorted"
            :key="s.name"
            type="button"
            class="compare-chip"
            :class="{
              selected: compareSelected.has(s.name),
              maxed: !compareSelected.has(s.name) && compareSelected.size >= MAX_COMPARE,
            }"
            :style="compareSelected.has(s.name) ? { '--chip-color': s.color } : {}"
            :disabled="!compareSelected.has(s.name) && compareSelected.size >= MAX_COMPARE"
            :aria-pressed="compareSelected.has(s.name)"
            @click="toggleCompareBank(s.name)"
          >
            <span class="chip-dot" :style="{ background: s.color }" aria-hidden="true"></span>
            {{ shortName(s.name) }}
          </button>
        </div>
      </div>

      <LineChart v-model:show-table="showTable" :series="chartSeries" :hidden="chartHidden" :currency="currency" :compare-mode="compareMode" @toggle="toggleBank" />
    </section>

    <section class="panel" style="--cv-size: 1000px">
      <h2>Rate percentile signal</h2>
      <p class="panel-sub">Where each bank's rate today sits in its own recent history — spot who's unusually high or low right now</p>
      <RatePercentileTable :series="allSeries" :currency="currency" />
    </section>

    <section id="rankings" class="panel" style="--cv-size: 1000px">
      <h2>All-time leaderboard</h2>
      <p class="panel-sub">Ranked by wins — which {{ currency }} bank has had the best rate most often, and by how much</p>
      <AllTimeLeaderboard :series="allSeries" :currency="currency" />
    </section>

    <section class="panel" style="--cv-size: 750px">
      <div class="panel-header">
        <div style="display: flex; flex-direction: column; justify-content: center;">
          <h2>Bank ranking over time</h2>
          <p class="panel-sub">How each bank's daily rank has moved — #1 is the best {{ currency }} rate that day</p>
        </div>
        <div class="range-filter" role="group" aria-label="Date range">
          <button
            type="button"
            class="range-btn"
            :class="{ active: rankRange === '30d' }"
            @click="rankRange = '30d'"
          >30 days</button>
          <button
            type="button"
            class="range-btn"
            :class="{ active: rankRange === '90d' }"
            @click="rankRange = '90d'"
          >90 days</button>
        </div>
      </div>
      <RankBumpChart v-model:range="rankRange" :series="allSeries" :currency="currency" />
    </section>

    <section class="panel" style="--cv-size: 500px">
      <h2>Best bank per day</h2>
      <p class="panel-sub">Which bank had the highest {{ currency }} TT Buy rate each day</p>
      <CalendarHeatmap :series="allSeries" :currency="currency" :holidays="holidayMap" />
    </section>

    <section id="trends" class="panel" style="--cv-size: 450px">
      <h2>Cost of not shopping around</h2>
      <p class="panel-sub">Fee-adjusted spread between the best and worst bank on {{ currency }} transfers each day</p>
      <OpportunityCostChart :series="allSeries" :currency="currency" :fees="fees" :amount="amount" />
    </section>

    <section class="panel" style="--cv-size: 750px">
      <h2>Markup below mid-market</h2>
      <p class="panel-sub">How much each {{ currency }} bank's TT Buy rate falls below mid-market — lower gap means a more competitive rate</p>
      <MarkupTrendChart :series="allSeries" :currency="currency" />
    </section>

    <section class="panel" style="--cv-size: 400px">
      <h2>Best day to receive</h2>
      <p class="panel-sub">Average {{ currency }} TT Buy rate by day of the week — deviation from the weekly mean across all available banks</p>
      <DayOfWeekChart :series="allSeries" :currency="currency" />
    </section>

    <section id="tools" class="panel" style="--cv-size: 1100px">
      <h2>What if?</h2>
      <p class="panel-sub">Pick any past date to replay the rates and see what you'd have received</p>
      <WhatIfMachine :raw-rates="rawRates" :fees="fees" :currencies="availableCurrencies" />
    </section>

    <section v-if="availableCurrencies.length > 1" class="panel" style="--cv-size: 400px">
      <CurrencyOptimizer :raw-rates="rawRates" :fees="fees" :currencies="availableCurrencies" />
    </section>

    <section v-if="availableCurrencies.length > 1" class="panel" style="--cv-size: 500px">
      <h2>Bank head-to-head</h2>
      <p class="panel-sub">Pick two banks and see which one gives you more across all currencies</p>
      <BankHeadToHead :raw-rates="rawRates" :fees="fees" :currencies="availableCurrencies" />
    </section>
    <section class="panel" style="--cv-size: 650px">
      <h2>Cumulative savings calculator</h2>
      <p class="panel-sub">How much more you'd have received if you'd used a different bank every day</p>
      <CumulativeSavingsCalc :series="allSeries" :fees="fees" :currency="currency" :amount="amount" :my-bank="myBank" />
    </section>

  </main>

  <p v-else-if="loadError" class="error">Couldn't load rate data: {{ loadError }}</p>
  <p v-else class="loading">Loading rates…</p>

  <section id="faq" class="panel faq-panel" style="--cv-size: 300px">
    <h2>Common questions</h2>
    <template v-if="bank && bankRateFacts.length">
      <details class="faq-item">
        <summary>What is {{ shortName(bank) }}'s TT Buy rate today?</summary>
        <p>
          {{ bank }}'s latest published TT Buy rates are
          <template v-for="(f, i) in bankRateFacts" :key="f.code">₹{{ f.ttbuy.toFixed(2) }} per {{ f.code }} ({{ fmtLongDate(f.date) }}){{ i < bankRateFacts.length - 1 ? ", " : "." }}</template>
          {{ shortName(bank) }} applies this rate when foreign currency arrives in your account as a wire transfer.
        </p>
      </details>
      <details class="faq-item">
        <summary>How does {{ shortName(bank) }}'s rate compare with other banks?</summary>
        <p>
          <template v-for="f in bankRateFacts" :key="f.code">
            <template v-if="!f.best || f.best.name === bank">{{ shortName(bank) }} had the best {{ f.code }} rate of all tracked banks. </template>
            <template v-else>For {{ f.code }}, {{ shortName(f.best.name) }} paid ₹{{ f.best.ttbuy.toFixed(2) }}, ₹{{ (f.best.ttbuy - f.ttbuy).toFixed(2) }} more per {{ f.code }} than {{ shortName(bank) }}. </template>
          </template>
          Use the history chart and the leaderboard above to see if the gap is usual or a one-day change.
        </p>
      </details>
      <details class="faq-item">
        <summary>Does {{ shortName(bank) }} charge a fee to receive money from abroad?</summary>
        <p v-if="bankFee">
          <template v-for="r in bankFee.rules" :key="r.label">{{ r.label }}: {{ r.charge }}. </template>
          <template v-if="bankFee.note">{{ bankFee.note }} </template>
          Source: <a :href="bankFee.source_url" target="_blank" rel="noopener noreferrer">{{ shortName(bank) }} fee schedule</a>, checked {{ fmtLongDate(bankFee.checked_at) }}.
        </p>
        <p v-else>We could not find a published inward remittance fee schedule for {{ shortName(bank) }}. Ask your branch before the transfer.</p>
      </details>
    </template>
    <details class="faq-item">
      <summary>My bank isn't the best rate today. What should I do?</summary>
      <p>Check the historical chart to see if it's consistently low. A one-day dip is normal; a persistent gap of ₹500+ per $1,000 over weeks is worth acting on. For large one-off transfers, call your bank's forex desk before the sender initiates the transfer. Many banks will offer a better rate on request. For regular transfers, switching to a consistently higher-rated bank is the more reliable fix.</p>
    </details>
    <details class="faq-item">
      <summary>What is TT Buy rate?</summary>
      <p>TT Buy (Telegraphic Transfer Buy) is the rate your bank applies when foreign currency arrives in your account as a wire transfer. It applies whether you receive a salary from a foreign employer, client payments for freelance work, or a family remittance. Banks set this rate independently and update it daily, which is why the same $1,000 can net you ₹500 more at one bank than another.</p>
    </details>
    <details class="faq-item">
      <summary>Can I negotiate a better rate with my bank?</summary>
      <p>Yes, for larger transfers. Most banks will consider a rate improvement for transfers equivalent to roughly ₹5 lakh or more if you call the forex desk before the transfer is sent. The published rate here is the standard retail rate. Negotiated rates are not published. It helps to mention you've seen competing rates and are considering your options.</p>
    </details>
    <details class="faq-item">
      <summary>I've decided to switch — how do I actually do it?</summary>
      <p>You don't need to close your existing account — just open a new one at the bank with the better rate. For inward remittances, it helps to open at a branch authorized to handle foreign exchange (an Authorized Dealer, or "AD", branch) — for example, if you're going with IOB, ask for an AD branch that handles forex/NRI transactions. Once it's open, give that account's IFSC and SWIFT code to whoever sends you money — your employer, client, or family — for future transfers. Money already sent to your old account doesn't need to change.</p>
    </details>
    <details class="faq-item">
      <summary>How is this data collected?</summary>
      <p>An automated scraper fetches each bank's publicly published forex rate page every day at 11 AM IST. The rates are the same ones any customer would see on the bank's website. Banks typically publish by 10 AM IST. This site is not affiliated with any bank and does not have access to live or negotiated rates.</p>
    </details>
  </section>

  <footer class="site-footer">
    <nav class="footer-banks" aria-label="Bank pages">
      <span>TT Buy rate by bank:</span>
      <template v-for="(b, i) in BANK_PAGES" :key="b.slug">
        <span v-if="i > 0" class="footer-sep" aria-hidden="true">·</span>
        <a :href="bankPagePath(b.slug)" :aria-current="bank === b.name ? 'page' : undefined">{{ shortName(b.name) }}</a>
      </template>
      <template v-if="bank">
        <span class="footer-sep" aria-hidden="true">·</span>
        <a href="/">All banks</a>
      </template>
    </nav>
    <div class="footer-credits">
      <span>Built by <a href="https://rakshithnettar.com" target="_blank" rel="noopener noreferrer">Rakshith Bellare</a></span>
      <span class="footer-sep" aria-hidden="true">·</span>
      <a href="https://bellare.gumroad.com/l/tiffp" target="_blank" rel="noopener noreferrer">Buy me a coffee</a>
      <span class="footer-sep" aria-hidden="true">·</span>
      <span>Not affiliated with any bank</span>
    </div>
  </footer>
</template>

<style scoped lang="scss">
.page-header {
  margin-bottom: 32px;

  .eyebrow {
    color: var(--text-secondary);
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin: 0 0 6px;
  }
  .eyebrow-link {
    color: inherit;
    &:hover { color: var(--text-primary); }
  }

  h1 {
    font-size: 32px;
    margin: 0 0 12px;
  }

  .lede {
    color: var(--text-secondary);
    max-width: 640px;
    line-height: 1.5;
    margin: 0 0 8px;
  }

  .hero-card {
    margin: 20px 0 12px;
    padding: 16px 20px 18px;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: var(--surface-1);
  }

  .hero-top {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 6px;
  }

  .hero-label {
    font-size: 13px;
    color: var(--text-secondary);
  }

  .hero-stale {
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 12px;
    color: var(--warning-text);
    background: color-mix(in srgb, var(--warning-text) 12%, transparent);
  }

  .hero-body {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    justify-content: space-between;
    gap: 16px 40px;
  }

  .hero-main {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }

  .hero-bank {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 0;
    border: none;
    background: none;
    font: inherit;
    font-size: 22px;
    font-weight: 700;
    color: var(--text-primary);
    text-align: left;
    cursor: pointer;

    svg { color: var(--text-muted); transition: transform 0.15s; }
    &:hover svg { transform: translateX(2px); color: var(--text-primary); }
    &:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; border-radius: 4px; }
  }

  .hero-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .hero-rate {
    font-size: 14px;
    color: var(--text-secondary);
    font-variant-numeric: tabular-nums;
  }

  .hero-figures {
    display: flex;
    align-items: flex-end;
    gap: 12px 32px;
  }

  .hero-figure {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .hero-figure-label {
    font-size: 13px;
    color: var(--text-secondary);
  }

  .hero-figure-value {
    font-size: 28px;
    font-weight: 700;
    line-height: 1.15;
    color: var(--text-primary);
    font-variant-numeric: tabular-nums;
  }

  .hero-figure--gain .hero-figure-value,
  .hero-figure--loss .hero-figure-value {
    font-size: 18px;
    font-weight: 600;
    color: var(--success-text);
  }
  .hero-figure--loss .hero-figure-value {
    color: var(--status-critical);
  }

  @media (max-width: 600px) {
    .hero-card { padding: 14px 16px 16px; }
    .hero-bank { font-size: 19px; }
    .hero-figure-value { font-size: 24px; }
    .hero-figures { gap: 12px 20px; }
  }

  .updated {
    color: var(--text-secondary);
    font-size: 13px;
    margin: 0;

    &.updated--holiday {
      color: var(--status-warning);
    }
  }
}

.section-nav {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  gap: 4px;
  margin: 0 -8px 20px;
  padding: 8px;
  overflow-x: auto;
  scrollbar-width: none;
  // The links stay in the content column, but the backdrop and bottom line run
  // to the screen edges. A border-image outset paints outside the box without
  // adding scrollable overflow (unlike width: 100vw, which counts the scrollbar).
  border-bottom: 1px solid transparent;
  border-image:
    linear-gradient(to top, var(--border) 1px, color-mix(in srgb, var(--page-plane) 88%, transparent) 1px)
    fill 0 / 0 / 0 100vmax;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);

  &::-webkit-scrollbar { display: none; }
}

.section-nav-link {
  flex-shrink: 0;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  text-decoration: none;
  transition: background 0.15s, color 0.15s;

  &:hover { color: var(--text-primary); background: color-mix(in srgb, var(--text-primary) 6%, transparent); }
  &:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

  &.active {
    color: var(--text-primary);
    background: color-mix(in srgb, var(--accent) 22%, transparent);
  }
}

.panel[id] {
  scroll-margin-top: 64px;
}

.toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.currency-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;

  @media (max-width: 600px) {
    width: 100%;

    .currency-btn {
      flex: 1;
    }
  }
}

.currency-btn {
  flex: none;
  background: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  white-space: nowrap;
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
    background: color-mix(in srgb, var(--accent), #000 18%);
    border-color: color-mix(in srgb, var(--accent), #000 18%);
    color: #fff;
  }
}

.bank-search {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 3;
  min-width: 160px;
  margin-bottom: 0;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface-1);

  .search-icon {
    color: var(--text-muted);
    flex: none;
  }
}

.bank-search-input {
  flex: 1;
  min-width: 0;
  border: none;
  background: none;
  padding: 8px 4px;
  font-size: 13px;
  color: var(--text-primary);

  &:focus {
    outline: none;
  }

  &::placeholder {
    color: var(--text-muted);
  }

  // Hide the native cancel button — the .clear-search button replaces it
  // so it matches the rest of the app's styling.
  &::-webkit-search-cancel-button {
    -webkit-appearance: none;
  }
}

.clear-search {
  flex: none;
  background: none;
  border: none;
  padding: 4px;
  font-size: 12px;
  color: var(--text-muted);
  cursor: pointer;

  &:hover {
    color: var(--text-primary);
  }
}

.share-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  background: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  white-space: nowrap;
  cursor: pointer;
  transition: background 120ms ease, border-color 120ms ease, color 120ms ease;

  &:hover:not(.copied) {
    background: var(--page-plane);
    color: var(--text-primary);
  }

  &:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }

  &.copied {
    color: var(--success-text);
    border-color: var(--success-text);
  }
}

.no-results {
  color: var(--text-secondary);
  font-size: 13px;
  margin: -8px 0 16px;
}

.panel {
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;

  // This page is a long stack of independently-heavy sections (charts,
  // tables) that all stay live in the DOM regardless of scroll position —
  // without this, every panel keeps getting laid out/painted/composited on
  // every scroll frame even while fully off-screen. "auto" instead of a
  // fixed intrinsic size means the browser remembers each panel's real
  // height after its first visit instead of relying on the estimate below.
  //
  // A single flat guess here caused a big CLS regression: sections range
  // from ~300px to ~2000px tall, so a 600px estimate was wildly wrong for
  // most of them, and swapping in the true height as each one scrolled
  // into view produced large, visible jumps. Each <section> below sets
  // --cv-size to its own measured height so this fallback is rarely used.
  content-visibility: auto;
  contain-intrinsic-size: auto var(--cv-size, 600px);

  h2 {
    font-size: 18px;
    margin: 0 0 4px;
  }

  @media (max-width: 480px) {
    padding: 14px;
  }
}

.panel-sub {
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--text-muted);
}

.panel-footnote {
  margin: 12px 0 0;
  font-size: 11px;
  color: var(--text-secondary);
}

.faq-panel {
  h2 { margin-bottom: 12px; }
}

.faq-item {
  border-top: 1px solid var(--border);
  padding: 0;

  &:last-child {
    border-bottom: 1px solid var(--border);
  }

  summary {
    padding: 12px 0;
    font-size: 14px;
    font-weight: 500;
    color: var(--text-primary);
    cursor: pointer;
    list-style: none;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    user-select: none;

    &::after {
      content: "+";
      font-size: 16px;
      color: var(--text-muted);
      flex: none;
      display: inline-block;
      transition: transform 200ms ease;
    }

    &::-webkit-details-marker { display: none; }
    &:focus-visible { outline: 2px solid var(--accent); border-radius: 2px; }
  }

  &[open] summary::after {
    transform: rotate(45deg);
  }

  p {
    margin: 0 0 14px;
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.6;
    max-width: 640px;
  }

  @media (prefers-reduced-motion: no-preference) {
    &[open] p {
      animation: faq-reveal 200ms ease both;
    }
  }
}

@keyframes faq-reveal {
  from { opacity: 0; transform: translateY(-5px); }
  to   { opacity: 1; transform: translateY(0); }
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px 16px;
  margin-bottom: 16px;

  h2 {
    margin: 0;
  }

  @media (max-width: 480px) {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
}

.chart-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;

  @media (max-width: 711px) {
    .compare-btn,
    .table-toggle {
      flex: 1;
    }
  }
}

.table-toggle,
.export-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  flex: 1;
  background: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
  cursor: pointer;
  transition: background 120ms ease, color 120ms ease;

  &:hover {
    background: var(--page-plane);
    color: var(--text-primary);
  }

  &:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
}

.compare-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
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

.compare-picker {
  margin-bottom: 14px;
  padding: 10px 12px;
  background: color-mix(in srgb, var(--accent) 6%, transparent);
  border: 1px solid color-mix(in srgb, var(--accent) 22%, transparent);
  border-radius: 8px;
}

.compare-meta {
  margin: 0 0 10px;
  font-size: 12px;
  color: var(--text-secondary);

  strong {
    color: var(--text-primary);
  }

  .compare-full-hint {
    color: var(--text-muted);
    font-style: italic;
  }
}

.compare-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.compare-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  // Grows to fill leftover space on a wrapped row instead of leaving it
  // blank (basis: auto keeps each chip's own content-width as the
  // starting point, so growth is added on top rather than equalizing
  // short/long bank names to the same width). Capped so a chip left
  // alone on the last row doesn't stretch to the full row width.
  flex: 1 1 auto;
  max-width: 220px;
  padding: 3px 8px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: none;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  white-space: nowrap;
  transition: background 60ms ease, border-color 60ms ease, color 60ms ease, opacity 60ms ease;

  &:hover:not(:disabled) {
    background: var(--page-plane);
    color: var(--text-primary);
  }

  &:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }

  &.selected {
    border-color: var(--chip-color, var(--accent));
    background: color-mix(in srgb, var(--chip-color, var(--accent)) 14%, transparent);
    color: var(--text-primary);
    font-weight: 500;
  }

  &.maxed {
    opacity: 0.3;
    cursor: not-allowed;
  }

  .chip-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex: none;
  }
}

.range-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;

  @media (max-width: 711px) {
    width: 100%;

    .range-btn {
      flex: 1;
    }
  }
}

.range-btn {
  background: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 5px 10px;
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
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

.theme-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
  width: 30px;
  height: 30px;
  background: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 120ms ease, color 120ms ease;

  &:hover {
    background: var(--page-plane);
    color: var(--text-primary);
  }

  &:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
}

.icon-swap-enter-active { transition: opacity 100ms ease, transform 100ms ease; }
.icon-swap-leave-active { transition: opacity 80ms ease, transform 80ms ease; }
.icon-swap-enter-from   { opacity: 0; transform: scale(0.6) rotate(-20deg); }
.icon-swap-leave-to     { opacity: 0; transform: scale(0.6) rotate(20deg); }

.loading,
.error {
  color: var(--text-secondary);
}

.error {
  color: var(--status-critical);
}

.site-footer {
  position: relative;
  margin-top: 40px;
  padding-bottom: 32px;

  &::before {
    content: "";
    position: absolute;
    top: 0;
    bottom: 0;
    left: 50%;
    width: 100vw;
    background: var(--surface-1);
    transform: translateX(-50%);
    z-index: -1;
  }
}

.footer-banks,
.footer-credits {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px 10px;
  font-size: 12px;
  color: var(--text-muted);

  a {
    color: var(--text-muted);
    text-decoration: none;

    &:hover {
      color: var(--text-secondary);
    }
  }
}

.footer-banks {
  padding: 16px 0 8px;
  border-top: 1px solid var(--gridline);

  a[aria-current="page"] {
    color: var(--text-primary);
    font-weight: 600;
  }
}

.footer-sep {
  color: var(--gridline);
}
</style>
