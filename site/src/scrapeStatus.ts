// When each bank's page was last checked and what the check found, from
// public/data/status.json (written by scraper/status.py on every run).
//
// All times are shown as absolute IST times ("Nov 27, 4:03 PM IST"), never as
// "2 hours ago": the page is prerendered, and a relative time would differ
// between the prerendered HTML and the hydrated page.
import { DISCONTINUED_BANKS } from "./bankPalette";
import statusData from "../public/data/status.json";

export type CheckResult = "ok" | "waiting" | "error";

export interface BankCheck {
  checkedAt: string;
  result: CheckResult;
  /** Date shown on the bank's page (ok / waiting). */
  rateDate?: string | null;
  /** Raw error text (error only). Not shown to users. */
  error?: string;
  /** Last check that could read the page. */
  lastOkAt?: string;
  /** First check of the current run of errors. */
  failingSince?: string;
}

export interface ScrapeStatus { checkedAt: string | null; banks: Record<string, BankCheck> }

export const scrapeStatus = statusData as unknown as ScrapeStatus;

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// "2026-11-27T16:03:12+05:30" → { date: "Nov 27", time: "4:03 PM" }. The
// scraper writes IST offsets, so the wall-clock digits are read as-is.
function parts(iso: string): { date: string; time: string } {
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(iso);
  if (!m) return { date: iso, time: "" };
  const [, , mo, d, hh, mm] = m;
  const h = Number(hh);
  return {
    date: `${MONTHS[Number(mo) - 1]} ${Number(d)}`,
    time: `${h % 12 || 12}:${mm} ${h < 12 ? "AM" : "PM"}`,
  };
}

/** "Nov 27, 4:03 PM IST" */
export function fmtCheckedAt(iso: string): string {
  const p = parts(iso);
  return `${p.date}, ${p.time} IST`;
}

/** "Nov 27" */
export function fmtCheckDate(iso: string): string {
  return parts(iso).date;
}

/** "4:03 PM" */
export function fmtCheckTime(iso: string): string {
  return parts(iso).time;
}

export function bankCheck(bank: string): BankCheck | null {
  return scrapeStatus.banks[bank] ?? null;
}

/**
 * One short line on why a bank's rate is older than the others, for the
 * table's date cell. Null when the status file has nothing useful to add.
 */
export function staleReason(bank: string): string | null {
  if (DISCONTINUED_BANKS[bank]) return "No longer checked";
  const c = bankCheck(bank);
  if (!c) return null;
  if (c.result === "error") {
    return c.failingSince && fmtCheckDate(c.failingSince) !== fmtCheckDate(c.checkedAt)
      ? `Can't read bank's page since ${fmtCheckDate(c.failingSince)}`
      : `Can't read bank's page (${fmtCheckTime(c.checkedAt)})`;
  }
  if (c.result === "waiting") return `No newer rate at ${fmtCheckTime(c.checkedAt)}`;
  return null;
}

/** Longer status for the About page's "Last check" column. */
export function checkSummary(bank: string): { text: string; tone: "ok" | "warn" | "muted" } {
  if (DISCONTINUED_BANKS[bank]) return { text: "No longer checked", tone: "muted" };
  const c = bankCheck(bank);
  if (!c) return { text: "—", tone: "muted" };
  const when = fmtCheckedAt(c.checkedAt);
  if (c.result === "ok") return { text: `${when}: today's rate`, tone: "ok" };
  if (c.result === "waiting") {
    return { text: `${when}: page still shows ${c.rateDate ? fmtCheckDate(`${c.rateDate}T00:00`) : "an older rate"}`, tone: "muted" };
  }
  const since = c.failingSince ? `, failing since ${fmtCheckedAt(c.failingSince)}` : "";
  return { text: `${when}: couldn't read page${since}`, tone: "warn" };
}
