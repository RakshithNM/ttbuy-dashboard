<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { RatesByCurrency, FeesByBank, FeeSlab } from "../types";
import { brandColor, isPlatform, shortName, sortByBankOrder } from "../bankPalette";
import { currencySymbol } from "../currencies";

const props = defineProps<{
  rawRates: RatesByCurrency;
  fees: FeesByBank;
  currencies: string[];
}>();

const DEFAULT_AMOUNTS: Record<string, number> = {
  USD: 1000, GBP: 800, EUR: 900, AED: 3600,
};

function feeFromSlabs(slabs: FeeSlab[], grossInr: number): number {
  for (const s of slabs) {
    if (s.up_to === null || grossInr <= s.up_to) return s.fee_inr;
  }
  return 0;
}

const allBanks = computed(() => {
  const set = new Set<string>();
  for (const c of props.currencies) {
    for (const [bank, pts] of Object.entries(props.rawRates[c] ?? {})) {
      if (!isPlatform(bank) && pts.length > 0) set.add(bank);
    }
  }
  return sortByBankOrder([...set]);
});

const bankA = ref("");
const bankB = ref("");

watch(
  allBanks,
  (banks) => {
    if (!bankA.value) {
      bankA.value = banks.includes("Punjab National Bank") ? "Punjab National Bank" : (banks[0] ?? "");
    }
    if (!bankB.value) {
      bankB.value = banks.includes("Indian Overseas Bank") ? "Indian Overseas Bank" : (banks[1] ?? "");
    }
  },
  { immediate: true }
);

const colorA = computed(() => (bankA.value ? brandColor(bankA.value) : "var(--text-muted)"));
const colorB = computed(() => (bankB.value ? brandColor(bankB.value) : "var(--text-muted)"));

interface BankData {
  ttbuy: number;
  feeUnknown: boolean;
  netInr: number;
}

function getBankData(bank: string, currency: string): BankData | null {
  const pts = (props.rawRates[currency] ?? {})[bank];
  if (!pts?.length) return null;
  const latest = pts[pts.length - 1];
  const amount = DEFAULT_AMOUNTS[currency] ?? 1000;
  const grossInr = latest.ttbuy * amount;
  const fee = props.fees[bank];
  const feeUnknown = !fee?.fee_slabs && fee?.fee_inr == null;
  const feeInr = fee?.fee_slabs
    ? feeFromSlabs(fee.fee_slabs, grossInr)
    : (fee?.fee_inr ?? 0);
  return { ttbuy: latest.ttbuy, feeUnknown, netInr: grossInr - feeInr };
}

interface CompareRow {
  currency: string;
  symbol: string;
  amount: number;
  a: BankData | null;
  b: BankData | null;
  winner: "a" | "b" | "tie" | null;
  marginInr: number;
}

const rows = computed<CompareRow[]>(() =>
  props.currencies.map((currency) => {
    const symbol = currencySymbol(currency);
    const amount = DEFAULT_AMOUNTS[currency] ?? 1000;
    const a = bankA.value ? getBankData(bankA.value, currency) : null;
    const b = bankB.value ? getBankData(bankB.value, currency) : null;

    let winner: CompareRow["winner"] = null;
    let marginInr = 0;
    if (a && b) {
      const diff = a.netInr - b.netInr;
      marginInr = Math.abs(diff);
      winner = marginInr < 1 ? "tie" : diff > 0 ? "a" : "b";
    }
    return { currency, symbol, amount, a, b, winner, marginInr };
  })
);

function formatInr(n: number): string {
  return Math.round(n).toLocaleString("en-IN");
}

function joinCurrencies(list: string[]): string {
  if (list.length === 0) return "";
  if (list.length === 1) return list[0];
  if (list.length === 2) return `${list[0]} and ${list[1]}`;
  return `${list.slice(0, -1).join(", ")}, and ${list[list.length - 1]}`;
}

const verdict = computed(() => {
  if (!bankA.value || !bankB.value) return null;
  const nameA = shortName(bankA.value);
  const nameB = shortName(bankB.value);
  const dataRows = rows.value.filter((r) => r.a !== null && r.b !== null);
  if (!dataRows.length) return null;

  const aW = dataRows.filter((r) => r.winner === "a").map((r) => r.currency);
  const bW = dataRows.filter((r) => r.winner === "b").map((r) => r.currency);
  const tied = dataRows.filter((r) => r.winner === "tie").map((r) => r.currency);

  if (aW.length === dataRows.length) return `${nameA} wins all ${dataRows.length} currencies.`;
  if (bW.length === dataRows.length) return `${nameB} wins all ${dataRows.length} currencies.`;
  if (tied.length === dataRows.length) return "Both banks give essentially the same rates.";

  const parts: string[] = [];
  if (aW.length) parts.push(`${nameA} wins ${joinCurrencies(aW)}`);
  if (bW.length) parts.push(`${nameB} wins ${joinCurrencies(bW)}`);
  if (tied.length) {
    const verb = tied.length === 1 ? "is" : "are";
    parts.push(`${joinCurrencies(tied)} ${verb} tied`);
  }
  return parts.join(". ") + ".";
});

function swapBanks() {
  [bankA.value, bankB.value] = [bankB.value, bankA.value];
}
</script>

<template>
  <div class="head-to-head">
    <div class="selectors">
      <div class="selector-block">
        <span class="bank-swatch" :style="{ background: colorA }" aria-hidden="true"></span>
        <select v-model="bankA" class="bank-select" aria-label="Bank A">
          <option v-for="bank in allBanks" :key="bank" :value="bank">{{ bank }}</option>
        </select>
      </div>

      <button type="button" class="swap-btn" @click="swapBanks" aria-label="Swap banks" title="Swap banks">
        <svg viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">
          <path d="M3 4.5h10M10 2l3 2.5-3 2.5" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M13 11.5H3M6 9l-3 2.5 3 2.5" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>

      <div class="selector-block">
        <span class="bank-swatch" :style="{ background: colorB }" aria-hidden="true"></span>
        <select v-model="bankB" class="bank-select" aria-label="Bank B">
          <option v-for="bank in allBanks" :key="bank" :value="bank">{{ bank }}</option>
        </select>
      </div>
    </div>

    <div class="table-scroll">
      <table class="compare-table">
        <thead>
          <tr>
            <th class="th-currency">Currency</th>
            <th class="th-bank">
              <span class="th-swatch" :style="{ background: colorA }" aria-hidden="true"></span>{{ shortName(bankA) || "Bank A" }}
            </th>
            <th class="th-bank">
              <span class="th-swatch" :style="{ background: colorB }" aria-hidden="true"></span>{{ shortName(bankB) || "Bank B" }}
            </th>
            <th class="th-adv">Advantage</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.currency">
            <td class="td-currency">
              <span class="cur-code">{{ row.currency }}</span>
              <span class="cur-amount">{{ row.amount.toLocaleString("en-IN") }} {{ row.symbol }}</span>
            </td>

            <td class="td-rate" :class="{ 'is-winner': row.winner === 'a' }">
              <template v-if="row.a">
                <span class="rate-val">₹{{ row.a.ttbuy.toFixed(2) }}</span>
                <span class="receive-val">₹{{ formatInr(row.a.netInr) }}</span>
              </template>
              <span v-else class="no-data">—</span>
            </td>

            <td class="td-rate" :class="{ 'is-winner': row.winner === 'b' }">
              <template v-if="row.b">
                <span class="rate-val">₹{{ row.b.ttbuy.toFixed(2) }}</span>
                <span class="receive-val">₹{{ formatInr(row.b.netInr) }}</span>
              </template>
              <span v-else class="no-data">—</span>
            </td>

            <td class="td-adv">
              <span
                v-if="row.winner === 'a'"
                class="adv-tag"
                :style="{ '--adv': colorA }"
              >+₹{{ formatInr(row.marginInr) }}</span>
              <span
                v-else-if="row.winner === 'b'"
                class="adv-tag"
                :style="{ '--adv': colorB }"
              >+₹{{ formatInr(row.marginInr) }}</span>
              <span v-else-if="row.winner === 'tie'" class="adv-tag adv-tie">Tied</span>
              <span v-else class="no-data">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <p v-if="verdict" class="hth-verdict">{{ verdict }}</p>
  </div>
</template>

<style scoped lang="scss">
.head-to-head {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.selectors {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.selector-block {
  display: flex;
  align-items: center;
  gap: 7px;
  flex: 1;
  min-width: 160px;
  padding: 0 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface-1);

  &:focus-within {
    outline: 2px solid var(--accent);
    outline-offset: 1px;
  }
}

.bank-swatch {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex: none;
  transition: background 150ms ease;
}

.bank-select {
  flex: 1;
  min-width: 0;
  border: none;
  background: none;
  padding: 8px 0;
  font-size: 13px;
  color: var(--text-primary);
  cursor: pointer;
  font-family: inherit;

  &:focus {
    outline: none;
  }

  option {
    background: var(--surface-1);
    color: var(--text-primary);
  }
}

.swap-btn {
  flex: none;
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text-muted);
  cursor: pointer;
  transition: background 80ms ease, color 80ms ease;

  &:hover {
    background: var(--page-plane);
    color: var(--text-primary);
  }

  &:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
}

.table-scroll {
  overflow-x: auto;
}

.compare-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;

  th {
    padding: 6px 10px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
    text-align: left;
  }

  td {
    padding: 9px 10px;
    border-bottom: 1px solid var(--border);
    vertical-align: top;
  }

  tbody tr:last-child td {
    border-bottom: none;
  }
}

.th-swatch {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  vertical-align: middle;
  margin-right: 4px;
  transition: background 150ms ease;
}

.td-currency {
  white-space: nowrap;

  .cur-code {
    display: block;
    font-weight: 600;
    color: var(--text-primary);
  }

  .cur-amount {
    display: block;
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 1px;
  }
}

.td-rate {
  min-width: 108px;
  white-space: nowrap;

  .rate-val {
    display: block;
    font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
    font-size: 13px;
    font-weight: 500;
    color: var(--text-secondary);
  }

  .receive-val {
    display: block;
    font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 2px;
  }

  &.is-winner {
    .rate-val {
      color: var(--text-primary);
      font-weight: 600;
    }

    .receive-val {
      color: var(--text-secondary);
    }
  }
}

.td-adv {
  white-space: nowrap;
}

.adv-tag {
  display: inline-block;
  font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
  font-size: 12px;
  font-weight: 600;
  color: var(--adv, var(--accent));
  background: color-mix(in srgb, var(--adv, var(--accent)) 13%, transparent);
  padding: 2px 7px;
  border-radius: 4px;
  line-height: 1.7;
}

.adv-tie {
  color: var(--text-muted);
  background: color-mix(in srgb, var(--text-muted) 10%, transparent);
}

.no-data {
  color: var(--text-muted);
}

.hth-verdict {
  margin: 0;
  padding: 10px 13px;
  background: color-mix(in srgb, var(--accent) 8%, transparent);
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-secondary);
}
</style>
