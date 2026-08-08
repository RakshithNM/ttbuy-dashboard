// Official brand colors for each bank/platform, used for indicators and chart
// lines. Colors are sourced from published brand guidelines and logo palettes.
// Where a bank uses multiple brand colors, the single most recognizable one is
// used. Add new banks at the end of BANK_ORDER, then add a color here.
export const BRAND_COLORS: Record<string, string> = {
  "Axis Bank":                  "#97144D", // Axis magenta-maroon
  "Indian Overseas Bank":       "#013CC8", // IOB deep blue
  "State Bank of India":        "#22409A", // SBI navy
  "Punjab National Bank":       "#FBBC09", // PNB yellow/gold
  "Bank of Baroda":             "#F15A29", // BoB orange
  "Canara Bank":                "#019EEC", // Canara sky blue
  "HDFC Bank":                  "#ED232A", // HDFC red
  "ICICI Bank":                 "#F99D27", // ICICI orange
  "Kotak Mahindra Bank":        "#ED1C24", // Kotak red
  "IDBI Bank":                  "#F58220", // IDBI orange
  "Bandhan Bank":               "#0A3152", // Bandhan dark blue
  "City Union Bank":            "#C8102E", // CUB red
  "HSBC":                       "#DB0011", // HSBC red
  "Jammu & Kashmir Bank":       "#0084C4", // J&K blue
  "Karur Vysya Bank":           "#00854A", // KVB green
  "Citibank":                   "#003B70", // Citi navy
  "Ujjivan Small Finance Bank": "#249D82", // Ujjivan teal
  "DCB Bank":                   "#26358F", // DCB indigo
  "IDFC FIRST Bank":            "#9C1D26", // IDFC FIRST dark red
  "DBS Bank India":             "#DA291C", // DBS red
  "RBL Bank":                   "#21317D", // RBL dark blue
  "Union Bank of India":        "#00579C", // Union Bank blue
  "Skydo":                      "#1B4FD8", // Skydo blue
  "Remitly":                    "#1D3557", // Remitly dark navy
  "Mid-market":                 "#888888", // Mid-market grey
};

const BRAND_COLOR_FALLBACK = "#6b7280";

export function brandColor(name: string): string {
  return BRAND_COLORS[name] ?? BRAND_COLOR_FALLBACK;
}

// Legacy slot system — kept for reference but no longer used for rendering.
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

// Source URLs for each bank/platform's published forex rate card or page.
export const SOURCE_URLS: Record<string, string> = {
  "Axis Bank": "https://application.axis.bank.in/webforms/corporatecardrate/index.aspx",
  "Bandhan Bank": "https://bandhan.bank.in/rates-charges",
  "Bank of Baroda": "https://bankofbaroda.bank.in/business-banking/treasury/forex-card-rates",
  "Canara Bank": "https://www.canarabank.bank.in/pages/forex-card-rates",
  "Citibank": "https://www.citigroup.com/rcs/citigpa/storage/public/India/forex-rates.pdf", // no general web page (retail ops transferred to Axis Bank)
  "City Union Bank": "https://cityunionbank.bank.in/foreign-exchange-rates",
  "DBS Bank India": "https://www.dbs.bank.in/in/treasures/rates-online/foreign-currency-foreign-exchange.page",
  "DCB Bank": "https://www.dcb.bank.in/rates/forex-rates",
  "HDFC Bank": "https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/personal-banking/discover-products/interest-rates/hdfc-bank-treasury-forex-card-rates.pdf",
  "HSBC": "https://www.hsbc.co.in/nri/foreign-exchange-rates/",
  "ICICI Bank": "https://www.icici.bank.in/corporate/global-markets/forex/forex-card-rate",
  "IDBI Bank": "https://idbi.bank.in/merchantrates.aspx",
  "IDFC FIRST Bank": "https://www.idfcfirst.bank.in/forex-rates.html",
  "Indian Overseas Bank": "https://www.iob.bank.in/en/forex-rates",
  "Jammu & Kashmir Bank": "https://eapp.jkb.bank.in/eintraweb/forex-rates",
  "Karur Vysya Bank": "https://www.kvb.bank.in/interest-rates/",
  "Kotak Mahindra Bank": "https://www.kotak.bank.in/en/rates/forex-rates.html",
  "Punjab National Bank": "https://pnb.bank.in/PNB-helpdesk-forexservices.html",
  "RBL Bank": "https://www.rbl.bank.in/fxadmin_getfx",
  "Remitly": "https://www.remitly.com/us/en/india",
  "Skydo": "https://www.skydo.com/convert-usd-to-inr?amount=1000",
  "State Bank of India": "https://sbi.bank.in/web/personal-banking/forex-cards",
  "Ujjivan Small Finance Bank": "https://www.ujjivansfb.bank.in/forex-rates",
  "Union Bank of India": "https://www.unionbankofindia.co.in/english/ibd-other-exchangerate.aspx",
};

export function sourceUrl(name: string): string | null {
  return SOURCE_URLS[name] ?? null;
}

// Remittance platform names. These appear in rates.json alongside banks but
// are displayed in a separate section in the UI.
export const PLATFORM_NAMES = new Set(["Skydo", "Remitly"]);

export function isPlatform(name: string): boolean {
  return ["Skydo", "Remitly", "Wise", "Payoneer"].includes(name);
}

export function isBenchmark(name: string): boolean {
  return name === "Mid-market";
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
