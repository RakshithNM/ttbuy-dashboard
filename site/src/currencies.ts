import type { CurrencyCode } from "./types";

export const CURRENCY_ORDER: CurrencyCode[] = ["USD", "GBP", "EUR", "AED"];

const SYMBOLS: Record<CurrencyCode, string> = {
  USD: "$",
  GBP: "£",
  EUR: "€",
  AED: "AED ",
};

export function currencySymbol(code: string): string {
  return SYMBOLS[code as CurrencyCode] ?? code;
}

export function sortByCurrencyOrder(codes: string[]): string[] {
  return [...codes].sort((a, b) => {
    const ai = CURRENCY_ORDER.indexOf(a as CurrencyCode);
    const bi = CURRENCY_ORDER.indexOf(b as CurrencyCode);
    return (ai === -1 ? Infinity : ai) - (bi === -1 ? Infinity : bi);
  });
}
