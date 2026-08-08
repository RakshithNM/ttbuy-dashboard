export type CurrencyCode = "USD" | "GBP" | "EUR" | "AED";

export interface RatePoint {
  date: string; // YYYY-MM-DD
  ttbuy: number;
}

export type RatesByBank = Record<string, RatePoint[]>;
export type RatesByCurrency = Record<string, RatesByBank>;

export interface Benchmarks {
  midMarket?: number;
  rbiReference?: number;
}
export type BenchmarksByCurrency = Record<string, Benchmarks>;

export interface BankSeries {
  name: string;
  color: string;
  wrapped: boolean;
  points: RatePoint[];
  category: "bank" | "platform";
}

export interface FeeRule {
  label: string;
  charge: string;
}

export interface FeeSlab {
  up_to: number | null; // upper bound inclusive in INR; null = all amounts above previous slab
  fee_inr: number;
}

export interface BankFee {
  bank: string;
  rules: FeeRule[];
  note: string | null;
  // Approximate flat rupee figure for the standard/individual case, used to
  // net the fee out of the amount calculator. 0 = confirmed free; null = we
  // don't know (see BankFee.note for why). Deliberately separate from
  // `rules`, which stays free text and isn't meant to be parsed for math.
  fee_inr: number | null;
  // Present when the fee varies by receive amount — takes precedence over
  // fee_inr for the net-receive calculation.
  fee_slabs?: FeeSlab[];
  source_url: string;
  checked_at: string;
}

export type FeesByBank = Record<string, BankFee>;
