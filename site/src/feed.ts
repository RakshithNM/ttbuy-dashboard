// Builds dist/feed.xml (Atom): one entry per day with the highest bank TT Buy
// rate in each currency. Runs at build time from vite.config.ts, so every
// daily data push gives feed readers a new entry without a backend.
// Imports carry .ts extensions because vite.config.ts (nodenext) loads this
// file. currencies.ts is left out: its extensionless import breaks nodenext.
import { isBenchmark, isPlatform } from "./bankPalette.ts";
import { SITE_URL } from "./bankPages.ts";

type Rates = Record<string, Record<string, { date: string; ttbuy: number }[]>>;

const CURRENCY_ORDER = ["USD", "GBP", "EUR", "AED"];
const MAX_ENTRIES = 30;
const AVG_DAYS = 7;

interface DayBest { date: string; bank: string; ttbuy: number }

function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function fmtDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `${MONTHS[m - 1]} ${d}, ${y}`;
}

function signed(n: number): string {
  return `${n >= 0 ? "▲" : "▼"} ₹${Math.abs(n).toFixed(2)}`;
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

export function buildFeed(rates: Rates): string {
  const rank = (c: string) => (CURRENCY_ORDER.indexOf(c) + 1 || 99);
  const currencies = Object.keys(rates).sort((a, b) => rank(a) - rank(b) || a.localeCompare(b));
  const series = new Map(currencies.map((c) => [c, bestByDate(rates[c])]));

  const dates = [...new Set([...series.values()].flatMap((s) => s.map((d) => d.date)))]
    .sort()
    .slice(-MAX_ENTRIES)
    .reverse();

  const entries = dates.map((date) => {
    const lines: string[] = [];
    const titleParts: string[] = [];
    for (const code of currencies) {
      const s = series.get(code)!;
      const i = s.findIndex((d) => d.date === date);
      if (i < 0) continue;
      const today = s[i];
      const prev = s[i - 1];
      const window = s.slice(Math.max(0, i - AVG_DAYS), i);
      const avg = window.length ? window.reduce((sum, d) => sum + d.ttbuy, 0) / window.length : null;
      titleParts.push(`${code} ₹${today.ttbuy.toFixed(2)}`);
      const notes: string[] = [];
      if (prev) notes.push(`${signed(today.ttbuy - prev.ttbuy)} vs ${fmtDate(prev.date)}`);
      if (avg !== null) notes.push(`${signed(today.ttbuy - avg)} vs ${window.length}-day average`);
      lines.push(
        `<li><strong>${code}</strong>: ${esc(today.bank)} at ₹${today.ttbuy.toFixed(2)}` +
          (notes.length ? ` (${notes.join(", ")})` : "") + `</li>`,
      );
    }
    const html =
      `<p>Highest bank TT Buy rate per currency on ${fmtDate(date)}. ` +
      `Rankings after fees, by amount, are on the site.</p><ul>${lines.join("")}</ul>` +
      `<p><a href="${SITE_URL}/">See all banks</a></p>`;
    return [
      "  <entry>",
      `    <title>Best TT Buy rates, ${fmtDate(date)}: ${esc(titleParts.join(" · "))}</title>`,
      `    <id>${SITE_URL}/feed.xml#${date}</id>`,
      `    <link href="${SITE_URL}/" />`,
      `    <updated>${date}T12:00:00+05:30</updated>`,
      `    <content type="html">${esc(html)}</content>`,
      "  </entry>",
    ].join("\n");
  });

  const updated = dates[0] ? `${dates[0]}T12:00:00+05:30` : new Date().toISOString();
  return [
    `<?xml version="1.0" encoding="utf-8"?>`,
    `<feed xmlns="http://www.w3.org/2005/Atom">`,
    `  <title>TTBuy Rates: best TT Buy rate by Indian banks</title>`,
    `  <subtitle>Daily highest TT Buy rate for USD, GBP, EUR and AED across Indian banks.</subtitle>`,
    `  <id>${SITE_URL}/feed.xml</id>`,
    `  <link rel="self" href="${SITE_URL}/feed.xml" />`,
    `  <link href="${SITE_URL}/" />`,
    `  <updated>${updated}</updated>`,
    `  <author><name>TTBuy Rates</name></author>`,
    ...entries,
    `</feed>`,
    "",
  ].join("\n");
}
