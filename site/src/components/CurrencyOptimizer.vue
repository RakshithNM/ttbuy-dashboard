<script setup lang="ts">
import { computed, ref } from "vue";
import type { RatesByCurrency, FeesByBank, FeeSlab } from "../types";
import { brandColor, isPlatform, shortName } from "../bankPalette";
import { currencySymbol } from "../currencies";

const props = defineProps<{
  rawRates: RatesByCurrency;
  fees: FeesByBank;
  currencies: string[];
}>();

const DEFAULT_AMOUNTS: Record<string, number> = {
  USD: 1000, GBP: 800, EUR: 900, AED: 3600,
};

const amounts = ref<Record<string, string>>(
  Object.fromEntries(props.currencies.map(c => [c, String(DEFAULT_AMOUNTS[c] ?? 1000)]))
);

function feeFromSlabs(slabs: FeeSlab[], grossInr: number): number {
  for (const s of slabs) {
    if (s.up_to === null || grossInr <= s.up_to) return s.fee_inr;
  }
  return 0;
}

interface CurrencyBest {
  currency: string;
  symbol: string;
  inputAmount: number;
  bank: string;
  color: string;
  category: "bank" | "platform";
  ttbuy: number;
  feeInr: number;
  feeUnknown: boolean;
  netInr: number;
  alsoWins: string[];
}

const activeCurrencies = computed(() =>
  props.currencies.filter(c => {
    const v = parseFloat(amounts.value[c] ?? "");
    return Number.isFinite(v) && v > 0;
  })
);

const perCurrencyBest = computed<CurrencyBest[]>(() => {
  const bests: Omit<CurrencyBest, "alsoWins">[] = [];

  for (const currency of activeCurrencies.value) {
    const amt = parseFloat(amounts.value[currency] ?? "");
    if (!Number.isFinite(amt) || amt <= 0) continue;

    const bankRates = props.rawRates[currency] ?? {};
    let best: Omit<CurrencyBest, "alsoWins"> | null = null;

    for (const [bank, points] of Object.entries(bankRates)) {
      if (!points.length || isPlatform(bank)) continue;
      const latest = points[points.length - 1];
      const grossInr = latest.ttbuy * amt;
      const fee = props.fees[bank];
      const feeUnknown = !fee?.fee_slabs && fee?.fee_inr == null;
      const feeInr = fee?.fee_slabs ? feeFromSlabs(fee.fee_slabs, grossInr) : (fee?.fee_inr ?? 0);
      const netInr = grossInr - feeInr;

      if (!best || netInr > best.netInr) {
        best = {
          currency,
          symbol: currencySymbol(currency),
          inputAmount: amt,
          bank,
          color: brandColor(bank),
          category: "bank",
          ttbuy: latest.ttbuy,
          feeInr,
          feeUnknown,
          netInr,
        };
      }
    }

    if (best) bests.push(best);
  }

  const bankWins = new Map<string, string[]>();
  for (const b of bests) {
    if (!bankWins.has(b.bank)) bankWins.set(b.bank, []);
    bankWins.get(b.bank)!.push(b.currency);
  }

  return bests.map(b => ({
    ...b,
    alsoWins: (bankWins.get(b.bank) ?? []).filter(c => c !== b.currency),
  }));
});


const mode = ref<"forward" | "reverse">("forward");
const targetInr = ref("150000");

interface ReverseResult {
  currency: string;
  symbol: string;
  bank: string;
  color: string;
  ttbuy: number;
  feeInr: number;
  feeUnknown: boolean;
  foreignAmount: number;
}

const reverseResults = computed<ReverseResult[]>(() => {
  const target = parseFloat(targetInr.value);
  if (!Number.isFinite(target) || target <= 0) return [];

  const results: ReverseResult[] = [];
  for (const currency of props.currencies) {
    const bankRates = props.rawRates[currency] ?? {};
    let best: { bank: string; color: string; ttbuy: number; feeInr: number; feeUnknown: boolean; foreignAmount: number } | null = null;

    for (const [bank, points] of Object.entries(bankRates)) {
      if (!points.length || isPlatform(bank)) continue;
      const latest = points[points.length - 1];
      const fee = props.fees[bank];
      const feeUnknown = !fee?.fee_slabs && fee?.fee_inr == null;
      const feeInr = fee?.fee_slabs ? feeFromSlabs(fee.fee_slabs, target) : (fee?.fee_inr ?? 0);
      const foreignAmount = (target + feeInr) / latest.ttbuy;

      if (!best || foreignAmount < best.foreignAmount) {
        best = { bank, color: brandColor(bank), ttbuy: latest.ttbuy, feeInr, feeUnknown, foreignAmount };
      }
    }

    if (best) results.push({ currency, symbol: currencySymbol(currency), ...best });
  }
  return results;
});

function formatInr(n: number): string {
  return "₹" + Math.round(n).toLocaleString("en-IN");
}

function formatForeign(amount: number, symbol: string): string {
  return symbol + amount.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
</script>

<template>
  <div class="optimizer">
    <div class="optimizer-header">
      <div class="optimizer-header-top">
        <h2 class="optimizer-title">Currency optimizer</h2>
        <div class="mode-toggle" role="group" aria-label="Calculator direction">
          <button type="button" :class="{ active: mode === 'forward' }" @click="mode = 'forward'">Foreign → ₹</button>
          <button type="button" :class="{ active: mode === 'reverse' }" @click="mode = 'reverse'">₹ → Foreign</button>
        </div>
      </div>
      <p class="optimizer-sub">
        <template v-if="mode === 'forward'">Enter the amount for each currency to see which bank gives you the most rupees.</template>
        <template v-else>Enter your INR target to see the minimum your sender needs to wire in each currency.</template>
      </p>
    </div>

    <div v-if="mode === 'forward'" class="amount-row">
      <label v-for="c in currencies" :key="c" class="amount-field">
        <span class="currency-label">{{ c }}</span>
        <div class="input-wrap">
          <span class="currency-symbol">{{ currencySymbol(c) }}</span>
          <input
            v-model="amounts[c]"
            type="number"
            min="1"
            class="amount-input"
            :aria-label="`Amount in ${c}`"
            @focus="($event.target as HTMLInputElement).select()"
          />
        </div>
      </label>
    </div>

    <div v-else class="amount-row">
      <label class="amount-field reverse-target-field">
        <span class="currency-label">You need to receive</span>
        <div class="input-wrap">
          <span class="currency-symbol">₹</span>
          <input
            v-model="targetInr"
            type="number"
            min="1"
            class="amount-input reverse-amount-input"
            aria-label="Target INR amount"
            @focus="($event.target as HTMLInputElement).select()"
          />
        </div>
      </label>
    </div>

    <template v-if="mode === 'forward'">
      <div v-if="activeCurrencies.length === 0" class="empty-state">
        Enter at least one amount above to see results.
      </div>
      <template v-else>
        <div class="results-wrap summary-wrap">
          <table class="results-table">
            <thead>
              <tr>
                <th class="col-ccy">Currency</th>
                <th>Best bank</th>
                <th class="col-num">TT Buy</th>
                <th class="col-num">You receive</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="best in perCurrencyBest" :key="best.currency">
                <td class="col-ccy">
                  <span class="ccy-pill">{{ best.currency }}</span>
                  <span class="rate-detail">{{ best.symbol }}{{ best.inputAmount.toLocaleString("en-IN") }}</span>
                </td>
                <td class="col-bank">
                  <span class="bank-dot" :style="{ background: best.color }" aria-hidden="true"></span>
                  <span class="bank-name-text">{{ shortName(best.bank) }}</span>
                  <span v-if="best.alsoWins.length" class="also-wins">also best for {{ best.alsoWins.join(', ') }}</span>
                </td>
                <td class="col-num">₹{{ best.ttbuy.toFixed(2) }}</td>
                <td class="col-num col-receive">
                  {{ formatInr(best.netInr) }}
                  <span v-if="best.feeUnknown" class="approx-mark" title="Fee unknown, shown without deduction">≈</span>
                </td>
              </tr>
            </tbody>
            <tfoot>
              <tr class="total-row">
                <td colspan="3" class="total-label">Total</td>
                <td class="col-num total-value">{{ formatInr(perCurrencyBest.reduce((s, b) => s + b.netInr, 0)) }}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </template>
    </template>

    <template v-else>
      <div v-if="reverseResults.length === 0" class="empty-state">
        Enter a target amount above to see results.
      </div>
      <div v-else class="results-wrap summary-wrap">
        <table class="results-table">
          <thead>
            <tr>
              <th class="col-ccy">Currency</th>
              <th>Best bank</th>
              <th class="col-num">TT Buy</th>
              <th class="col-num col-send">Send</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in reverseResults" :key="r.currency">
              <td class="col-ccy">
                <span class="ccy-pill">{{ r.currency }}</span>
              </td>
              <td class="col-bank">
                <span class="bank-dot" :style="{ background: r.color }" aria-hidden="true"></span>
                <span class="bank-name-text">{{ shortName(r.bank) }}</span>
              </td>
              <td class="col-num">₹{{ r.ttbuy.toFixed(2) }}</td>
              <td class="col-num col-send">
                {{ formatForeign(r.foreignAmount, r.symbol) }}
                <span v-if="r.feeUnknown" class="approx-mark" title="Fee unknown, shown without deduction">≈</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped lang="scss">
.optimizer {
  font-size: 14px;
}

.optimizer-header {
  margin-bottom: 16px;
}

.optimizer-header-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}

.optimizer-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.mode-toggle {
  display: flex;
  border: 1px solid var(--border);
  border-radius: 7px;
  overflow: hidden;
  flex-shrink: 0;

  button {
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 500;
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    transition: background 100ms, color 100ms;
    white-space: nowrap;

    &:not(:last-child) {
      border-right: 1px solid var(--border);
    }

    &.active {
      background: color-mix(in srgb, var(--accent) 12%, transparent);
      color: var(--accent);
    }

    &:hover:not(.active) {
      background: var(--page-plane);
      color: var(--text-secondary);
    }
  }
}

.optimizer-sub {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0;
  max-width: 620px;
}

.amount-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 20px;
}

.amount-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
  cursor: default;
  flex: 1;
}

.reverse-target-field {
  flex: 0 0 auto;
  min-width: 200px;
}

.reverse-amount-input {
  width: 140px;
}

.col-send {
  font-weight: 600;
  color: var(--text-primary);
  font-size: 14px;
}

.currency-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
}

.input-wrap {
  display: flex;
  align-items: center;
  gap: 0;
  border: 1px solid var(--border);
  border-radius: 7px;
  overflow: hidden;
  background: var(--surface-1);
  transition: border-color 100ms;

  &:focus-within {
    border-color: var(--accent);
  }
}

.currency-symbol {
  padding: 0 8px;
  font-size: 13px;
  color: var(--text-muted);
  background: var(--page-plane);
  border-right: 1px solid var(--border);
  height: 36px;
  display: flex;
  align-items: center;
  white-space: nowrap;
  user-select: none;
}

.amount-input {
  width: 90px;
  height: 36px;
  padding: 0 10px;
  border: none;
  background: transparent;
  color: var(--text-primary);
  font-size: 14px;
  font-variant-numeric: tabular-nums;
  outline: none;

  &::-webkit-inner-spin-button,
  &::-webkit-outer-spin-button { -webkit-appearance: none; }
}

.empty-state {
  color: var(--text-muted);
  font-size: 13px;
  font-style: italic;
  padding: 16px 0;
}

.results-wrap {
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.results-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;

  th, td {
    padding: 9px 12px;
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
    letter-spacing: 0.04em;
    font-weight: 500;
  }

  tbody tr:last-child td {
    border-bottom: none;
  }

  tbody tr.winner {
    background: color-mix(in srgb, var(--status-good) 7%, transparent);

    .col-receive {
      color: var(--status-good);
      font-weight: 600;
    }
  }
}

.col-num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.col-bank {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--text-primary);
  flex-wrap: wrap;
}

.bank-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex: none;
}

.bank-name-text {
  flex: none;
}

.also-wins {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 400;
}

.col-ccy {
  display: flex;
  align-items: center;
  gap: 6px;
}

.ccy-pill {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--page-plane);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  letter-spacing: 0.03em;
}

.rate-detail {
  color: var(--text-muted);
  font-size: 12px;
}

.col-receive {
  font-weight: 600;
  color: var(--text-primary);
}

.approx-mark {
  color: var(--text-muted);
  font-size: 11px;
  margin-left: 2px;
  cursor: help;
}

.summary-wrap .results-table {
  tbody td { border-bottom: none; }
  tbody tr { border-bottom: 1px solid var(--gridline); }
  tbody tr:last-child { border-bottom: none; }
}

.total-row {
  td {
    border-top: 1px solid var(--border);
    border-bottom: none;
    padding-top: 10px;
    padding-bottom: 10px;
  }
}

.total-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
}

.total-value {
  font-weight: 700;
  font-size: 14px;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

</style>
