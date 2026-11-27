// Daily "best rate" entries, shared by the Atom feed (dist/feed.xml, built
// from vite.config.ts) and the human-readable /feed page (FeedPage.vue).
//
// Imports carry .ts extensions because vite.config.ts (nodenext) loads this
// file. currencies.ts is left out: its extensionless import breaks nodenext.
import { isBenchmark, isPlatform } from "./bankPalette.ts";
import { SITE_URL } from "./bankPages.ts";

type Rates = Record<string, Record<string, { date: string; ttbuy: number }[]>>;

const CURRENCY_ORDER = ["USD", "GBP", "EUR", "AED"];
const MAX_ENTRIES = 30;
const AVG_DAYS = 7;

export interface FeedLine {
  code: string;
  bank: string;
  ttbuy: number;
  /** Change vs the previous counted day, with that day's date. */
  prev: { date: string; change: number } | null;
  /** Change vs the average of up to AVG_DAYS previous counted days. */
  avg: { days: number; change: number } | null;
}

export interface FeedDay { date: string; lines: FeedLine[] }

interface DayBest { date: string; bank: string; ttbuy: number }

export function fmtFeedDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `${MONTHS[m - 1]} ${d}, ${y}`;
}

export function fmtChange(n: number): string {
  return `${n >= 0 ? "▲" : "▼"} ₹${Math.abs(n).toFixed(2)}`;
}

function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// Best bank per date for one currency. A date counts only when a majority of
// banks published that day, so a day where two scrapers ran doesn't crown
// whoever happened to show up.
function bestByDate(byBank: Rates[string]): DayBest[] {
  const banks = Object.keys(byBank).filter((b) => !isPlatform(b) && !isBenchmark(b));
  const majority = Math.floor(banks.length / 2) + 1;
  const perDate = new Map<string, { count: number; best: DayBest }>();
  for (const bank of banks) {
    for (const p of byBank[bank]) {
      const cur = perDate.get(p.date);
      if (!cur) perDate.set(p.date, { count: 1, best: { date: p.date, bank, ttbuy: p.ttbuy } });
      else {
        cur.count++;
        if (p.ttbuy > cur.best.ttbuy) cur.best = { date: p.date, bank, ttbuy: p.ttbuy };
      }
    }
  }
  return [...perDate.values()]
    .filter((v) => v.count >= majority)
    .map((v) => v.best)
    .sort((a, b) => a.date.localeCompare(b.date));
}

/** Newest day first, at most MAX_ENTRIES days. */
export function feedDays(rates: Rates): FeedDay[] {
  const rank = (c: string) => (CURRENCY_ORDER.indexOf(c) + 1 || 99);
  const currencies = Object.keys(rates).sort((a, b) => rank(a) - rank(b) || a.localeCompare(b));
  const series = new Map(currencies.map((c) => [c, bestByDate(rates[c])]));

  const dates = [...new Set([...series.values()].flatMap((s) => s.map((d) => d.date)))]
    .sort()
    .slice(-MAX_ENTRIES)
    .reverse();

  return dates.map((date) => {
    const lines: FeedLine[] = [];
    for (const code of currencies) {
      const s = series.get(code)!;
      const i = s.findIndex((d) => d.date === date);
      if (i < 0) continue;
      const today = s[i];
      const prev = s[i - 1];
      const window = s.slice(Math.max(0, i - AVG_DAYS), i);
      lines.push({
        code,
        bank: today.bank,
        ttbuy: today.ttbuy,
        prev: prev ? { date: prev.date, change: today.ttbuy - prev.ttbuy } : null,
        avg: window.length
          ? { days: window.length, change: today.ttbuy - window.reduce((sum, d) => sum + d.ttbuy, 0) / window.length }
          : null,
      });
    }
    return { date, lines };
  });
}

/** Short title for a day, e.g. "USD ₹92.23 · GBP ₹120.63". */
export function feedDayTitle(day: FeedDay): string {
  return day.lines.map((l) => `${l.code} ₹${l.ttbuy.toFixed(2)}`).join(" · ");
}

export function lineNotes(l: FeedLine): string {
  const notes: string[] = [];
  if (l.prev) notes.push(`${fmtChange(l.prev.change)} vs ${fmtFeedDate(l.prev.date)}`);
  if (l.avg) notes.push(`${fmtChange(l.avg.change)} vs ${l.avg.days}-day average`);
  return notes.join(", ");
}

export function buildFeed(rates: Rates): string {
  const days = feedDays(rates);
  const XHTML = "http://www.w3.org/1999/xhtml";

  // Content is XHTML, not escaped HTML: feed.xsl can then copy it as real
  // markup, which works in every XSLT browser (escaped HTML would need
  // disable-output-escaping, which Firefox ignores).
  const entries = days.map((day) => {
    const items = day.lines
      .map((l) => {
        const notes = lineNotes(l);
        return `<li><strong>${l.code}</strong>: ${esc(l.bank)} at ₹${l.ttbuy.toFixed(2)}${notes ? ` (${esc(notes)})` : ""}</li>`;
      })
      .join("");
    return [
      "  <entry>",
      `    <title>Best TT Buy rates, ${fmtFeedDate(day.date)}: ${esc(feedDayTitle(day))}</title>`,
      `    <id>${SITE_URL}/feed.xml#${day.date}</id>`,
      `    <link href="${SITE_URL}/feed#d-${day.date}" />`,
      `    <updated>${day.date}T12:00:00+05:30</updated>`,
      `    <content type="xhtml"><div xmlns="${XHTML}">` +
        `<p>Highest bank TT Buy rate per currency on ${fmtFeedDate(day.date)}. Rankings after fees, by amount, are on the site.</p>` +
        `<ul>${items}</ul>` +
        `<p><a href="${SITE_URL}/">See all banks</a></p>` +
        `</div></content>`,
      "  </entry>",
    ].join("\n");
  });

  const updated = days[0] ? `${days[0].date}T12:00:00+05:30` : new Date().toISOString();
  return [
    `<?xml version="1.0" encoding="utf-8"?>`,
    `<?xml-stylesheet href="/feed.xsl" type="text/xsl"?>`,
    `<feed xmlns="http://www.w3.org/2005/Atom">`,
    `  <title>TTBuy Rates: best TT Buy rate by Indian banks</title>`,
    `  <subtitle>Daily highest TT Buy rate for USD, GBP, EUR and AED across Indian banks.</subtitle>`,
    `  <id>${SITE_URL}/feed.xml</id>`,
    `  <link rel="self" href="${SITE_URL}/feed.xml" />`,
    `  <link rel="alternate" type="text/html" href="${SITE_URL}/feed" />`,
    `  <updated>${updated}</updated>`,
    `  <author><name>TTBuy Rates</name></author>`,
    ...entries,
    `</feed>`,
    "",
  ].join("\n");
}
