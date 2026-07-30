export type CurrencyCode = "USD" | "GBP" | "EUR" | "AED";

export interface RatePoint {
  date: string; // YYYY-MM-DD
  ttbuy: number;
}

export type RatesByBank = Record<string, RatePoint[]>;
export type RatesByCurrency = Record<string, RatesByBank>;

export interface BankSeries {
  name: string;
  color: string;
  wrapped: boolean;
  points: RatePoint[];
}
