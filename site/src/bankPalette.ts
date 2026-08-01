// Fixed categorical hue order (dataviz skill palette, validated for CVD-safe
// adjacent pairs). Slot assignment follows a fixed bank order, not alphabetical
// or data-driven sort, so a bank's color never shifts as other banks are
// filtered in/out or as new banks are added at the end of the list.
export const CATEGORICAL_SLOTS = [
  "--series-1", // blue
  "--series-2", // orange
  "--series-3", // aqua
  "--series-4", // yellow
  "--series-5", // magenta
  "--series-6", // green
  "--series-7", // violet
  "--series-8", // red
] as const;

// Remittance platform names. These appear in rates.json alongside banks but
// are displayed in a separate section in the UI.
export const PLATFORM_NAMES = new Set(["Skydo", "Remitly"]);

export function isPlatform(name: string): boolean {
  return PLATFORM_NAMES.has(name);
}

// Known banks in a stable order. New banks get appended here (never inserted)
// so existing colors never repaint. Includes a few not-yet-scraped banks
// (Punjab National Bank, Yes Bank, ...) so their slot is already reserved
// once they do get implemented, rather than shifting banks after them.
export const BANK_ORDER = [
  "Axis Bank",
  "Indian Overseas Bank",
  "State Bank of India",
  "Punjab National Bank",
  "Bank of Baroda",
  "Canara Bank",
  "HDFC Bank",
  "ICICI Bank",
  "Kotak Mahindra Bank",
  "Yes Bank",
  "IDBI Bank",
  "Karnataka Bank",
  "Central Bank of India",
  "Bank of Maharashtra",
  "Bandhan Bank",
  "City Union Bank",
  "HSBC",
  "Jammu & Kashmir Bank",
  "Karur Vysya Bank",
  "Citibank",
  "Ujjivan Small Finance Bank",
  "DCB Bank",
  "IDFC FIRST Bank",
  "DBS Bank India",
  // Platforms get stable color slots after banks
  "Skydo",
  "Remitly",
];

// The categorical palette only validates CVD-safe adjacent pairs up to 8
// slots (see dataviz skill palette.md) — past that, hue alone can't carry
// identity. A 9th+ bank reuses a hue but is drawn dashed (see LineChart.vue)
// so it's never visually confused with the hue's first owner.
export function isWrappedSlot(bank: string): boolean {
  const index = BANK_ORDER.indexOf(bank);
  return index === -1 || index >= CATEGORICAL_SLOTS.length;
}

export function slotForBank(bank: string): string {
  let index = BANK_ORDER.indexOf(bank);
  if (index === -1) index = BANK_ORDER.length; // unknown bank -> append after known ones
  return CATEGORICAL_SLOTS[index % CATEGORICAL_SLOTS.length];
}

// Short display names for banks whose full name is unwieldy in tight spaces
// (table headers, dense legends). Falls back to the full name otherwise.
const SHORT_NAMES: Record<string, string> = {
  "Axis Bank": "Axis",
  "Indian Overseas Bank": "IOB",
  "State Bank of India": "SBI",
  "Punjab National Bank": "Punjab National",
  "Bank of Baroda": "Bank of Baroda",
  "Canara Bank": "Canara",
  "HDFC Bank": "HDFC",
  "ICICI Bank": "ICICI",
  "Kotak Mahindra Bank": "Kotak Mahindra",
  "Yes Bank": "Yes",
  "IDBI Bank": "IDBI",
  "Karnataka Bank": "Karnataka",
  "Central Bank of India": "Central Bank of India",
  "Bank of Maharashtra": "Bank of Maharastra",
  "Bandhan Bank": "Bandhan",
  "City Union Bank": "City Union",
  "HSBC": "HSBC",
  "Jammu & Kashmir Bank": "J&K Bank",
  "Karur Vysya Bank": "KVB",
  "Citibank": "Citibank",
  "Ujjivan Small Finance Bank": "Ujjivan",
  "DCB Bank": "DCB",
  "IDFC FIRST Bank": "IDFC FIRST",
  "DBS Bank India": "DBS",
};

export function shortName(bank: string): string {
  return SHORT_NAMES[bank] ?? bank;
}

export function sortByBankOrder(banks: string[]): string[] {
  return [...banks].sort((a, b) => {
    const ai = BANK_ORDER.indexOf(a);
    const bi = BANK_ORDER.indexOf(b);
    return (ai === -1 ? Infinity : ai) - (bi === -1 ? Infinity : bi);
  });
}
