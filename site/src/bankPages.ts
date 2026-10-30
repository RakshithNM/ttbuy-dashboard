// Banks that get their own page at /<slug>-tt-buy-rate. Each page is the
// same dashboard, with the header, hero and FAQ focused on that bank, so
// searches like "SBI TT buy rate" have a page that answers them directly.
// Names must match the keys in rates.json.
export interface BankPage {
  slug: string;
  name: string;
}

export const BANK_PAGES: BankPage[] = [
  { slug: "sbi", name: "State Bank of India" },
  { slug: "hdfc", name: "HDFC Bank" },
  { slug: "icici", name: "ICICI Bank" },
  { slug: "axis", name: "Axis Bank" },
  { slug: "kotak", name: "Kotak Mahindra Bank" },
];

export const SITE_URL = "https://ttbuyrates.rakshithnettar.com";

export function bankPagePath(slug: string): string {
  return `/${slug}-tt-buy-rate`;
}
