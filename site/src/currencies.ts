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

// Keyboard handling for a currency radiogroup (WAI-ARIA radio pattern):
// arrows move selection and focus together, wrapping at the ends;
// Home/End jump to the first/last option. Each radio needs data-currency.
export function onCurrencyRadioKeydown(
  e: KeyboardEvent,
  codes: string[],
  current: string,
  select: (code: string) => void,
): void {
  const i = codes.indexOf(current);
  let next: number;
  switch (e.key) {
    case "ArrowRight":
    case "ArrowDown": next = (i + 1) % codes.length; break;
    case "ArrowLeft":
    case "ArrowUp": next = (i - 1 + codes.length) % codes.length; break;
    case "Home": next = 0; break;
    case "End": next = codes.length - 1; break;
    default: return;
  }
  e.preventDefault();
  const code = codes[next];
  select(code);
  (e.currentTarget as HTMLElement)
    .querySelector<HTMLElement>(`[data-currency="${code}"]`)
    ?.focus();
}
