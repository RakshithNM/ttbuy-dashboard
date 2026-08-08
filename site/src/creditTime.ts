export type CreditCategory = "same-day" | "1-2-days" | "2-3-days" | "not-published";

export interface CreditTimeInfo {
  category: CreditCategory;
  note: string;
  source: string | null;
}

export type CreditTimesByBank = Record<string, CreditTimeInfo>;

export const CREDIT_TIMES: CreditTimesByBank = {
  "Axis Bank": {
    category: "same-day",
    note: "Same day for funds received during FX market hours; next business day otherwise. Axis maintains dedicated same-day credit tie-ups with several major correspondent banks.",
    source: "https://www.axis.bank.in/business-banking/remittances/inward-remittances",
  },
  "Indian Overseas Bank": {
    category: "not-published",
    note: "No credit SLA is published on IOB's official pages.",
    source: null,
  },
  "State Bank of India": {
    category: "1-2-days",
    note: "USD/INR remittances credited within 1 banking day; other currencies within 2 banking days after transmission. Per SBI New York branch FAQ.",
    source: "https://sbinewyork.statebank/remittance-faq",
  },
  "Punjab National Bank": {
    category: "not-published",
    note: "No credit SLA is published on PNB's official pages.",
    source: null,
  },
  "Bank of Baroda": {
    category: "not-published",
    note: "BoB publishes an inward payments FAQ but no specific credit SLA is stated on public-facing pages.",
    source: null,
  },
  "Canara Bank": {
    category: "not-published",
    note: "No credit SLA is published on Canara Bank's official remittance pages.",
    source: null,
  },
  "HDFC Bank": {
    category: "not-published",
    note: "No official credit SLA is published. Third-party sources cite 'within 72 hours' but this is not a bank-published commitment.",
    source: null,
  },
  "ICICI Bank": {
    category: "same-day",
    note: "SWIFT gpi Instant enables near-instant credit for personal remittances up to ₹2 lakh (via IMPS). Standard SWIFT: 24–48 banking hours. Trade remittances: within 1 hour of receiving disposal instruction.",
    source: "https://www.icici.bank.in/about-us/news-room/2021/news-icici-bank-offers-instant-facility-for-crossborder-inward-remittances",
  },
  "Kotak Mahindra Bank": {
    category: "1-2-days",
    note: "Officially: funds credited within 1–2 working days of receipt in correspondent bank's Nostro account.",
    source: "https://www.kotak.bank.in/en/personal-banking/nri/transfer-money/wire-transfer.html",
  },
  "IDBI Bank": {
    category: "not-published",
    note: "No credit SLA is published. IDBI's disposal instruction documents explicitly state the bank will not be held responsible for credit delays.",
    source: null,
  },
  "Bandhan Bank": {
    category: "same-day",
    note: "Officially: same day credit upon receipt of funds.",
    source: "https://bandhan.bank.in/nri-banking/nri-remittance",
  },
  "City Union Bank": {
    category: "not-published",
    note: "Official pages mention 'faster processing' but publish no specific credit timeline.",
    source: null,
  },
  "HSBC": {
    category: "2-3-days",
    note: "Officially: credited within 2 working days from the day HSBC India receives the funds. SWIFT transit time to reach HSBC is additional.",
    source: "https://www.hsbc.co.in/help/faqs/remittances/",
  },
  "Jammu & Kashmir Bank": {
    category: "not-published",
    note: "No credit SLA is published on official pages.",
    source: null,
  },
  "Karur Vysya Bank": {
    category: "not-published",
    note: "No credit SLA is published. Routing enquiries go to KVB's Central Forex Processing Centre.",
    source: null,
  },
  "Citibank": {
    category: "not-published",
    note: "Citibank India's retail and NRI banking was acquired by Axis Bank (completed March 2023). Rates shown here may reflect the institutional entity only. Retail customers should refer to Axis Bank.",
    source: null,
  },
  "Ujjivan Small Finance Bank": {
    category: "1-2-days",
    note: "Officially: generally credited within 1–3 business days, depending on remitter's bank, intermediary network, and time zone. Rate applied at prevailing forex rate at time of conversion.",
    source: "https://www.ujjivansfb.bank.in/nri/forex/Inward-remittance",
  },
  "DCB Bank": {
    category: "not-published",
    note: "Official pages mention 'faster credit' but publish no specific credit timeline.",
    source: null,
  },
  "IDFC FIRST Bank": {
    category: "1-2-days",
    note: "Officially: funds deposited within 1–2 days of receiving the foreign currency in bank's Nostro account. Purpose of payment is mandatory for faster processing.",
    source: "https://www.idfcfirst.bank.in/personal-banking/forex/inward-remittance",
  },
  "DBS Bank India": {
    category: "same-day",
    note: "NRE account transfers credited within 24 hours of DBS Treasures receiving instructions, if received before 11:30 AM IST. No service charges on NRE account credits.",
    source: "https://www.dbs.bank.in/in/treasures/en_us/nri-banking/remittance/send-money-to-india",
  },
  "RBL Bank": {
    category: "2-3-days",
    note: "Officially: credited in less than 48 working hours of receipt.",
    source: "https://www.rbl.bank.in/nri-banking/money-transfer/wire-transfers",
  },
  "Union Bank of India": {
    category: "same-day",
    note: "Same day credit for funds received during FX market hours; next business day otherwise. Flat ₹250 charge on incoming remittances.",
    source: "https://www.unionbankofindia.bank.in/en/details/inward-remittances",
  },
  "Skydo": {
    category: "1-2-days",
    note: "Skydo uses local payment rails (not traditional SWIFT) — sender makes a domestic wire, Skydo credits INR within 12–24 hours. Total end-to-end: 24–48 hours. Issues FIRC within 24 hours.",
    source: "https://www.skydo.com/blog/how-long-does-international-wire-transfer-take",
  },
  "Remitly": {
    category: "same-day",
    note: "Express (debit/credit card funded): delivered in minutes. Economy (bank account funded): 3–5 business days. Unlike banks, Remitly locks the exchange rate at the time of booking — not at credit time.",
    source: "https://www.remitly.com/us/en/india",
  },
};
