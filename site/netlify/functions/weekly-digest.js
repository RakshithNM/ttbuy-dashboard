import { getStore } from "@netlify/blobs";
import crypto from "crypto";

const RATES_URL =
  "https://raw.githubusercontent.com/RakshithNM/ttbuy-dashboard/refs/heads/main/data/rates.json";
const SITE_URL = process.env.URL || "https://ttbuyrates.rakshithnettar.com";
const FROM_EMAIL = "TTBuy Rates <digest@ttbuyrates.rakshithnettar.com>";

function makeToken(email) {
  const secret = process.env.DIGEST_SECRET;
  if (!secret) throw new Error("DIGEST_SECRET env var not set");
  return crypto.createHmac("sha256", secret).update(email).digest("hex");
}

function unsubUrl(email) {
  return `${SITE_URL}/api/email-unsubscribe?email=${encodeURIComponent(email)}&token=${makeToken(email)}`;
}

// Returns the N most-recent dates that appear in rates for any bank, excluding
// "Mid-market" (which is a benchmark row, not a real bank).
function recentDates(currencyRates, n) {
  const dateSet = new Set();
  for (const [bank, points] of Object.entries(currencyRates)) {
    if (bank === "Mid-market") continue;
    for (const p of points) dateSet.add(p.date);
  }
  return [...dateSet].sort().slice(-n);
}

function latestRates(currencyRates, date) {
  const result = [];
  for (const [bank, points] of Object.entries(currencyRates)) {
    if (bank === "Mid-market") continue;
    const point = [...points].reverse().find((p) => p.date <= date);
    if (point) result.push({ bank, rate: point.ttbuy, date: point.date });
  }
  return result.sort((a, b) => b.rate - a.rate);
}

function formatRate(r) {
  return r.toFixed(2);
}

function formatInr(n) {
  return Math.round(n).toLocaleString("en-IN");
}

function currencySymbol(c) {
  return c === "GBP" ? "£" : c === "EUR" ? "€" : c === "AED" ? "د.إ" : "$";
}

function buildEmailHtml({ currency, todayRanked, lastWeekBest, unsubLink }) {
  const best = todayRanked[0];
  const worst = todayRanked[todayRanked.length - 1];
  const spread = best && worst ? (best.rate - worst.rate) * 1000 : null;
  const sym = currencySymbol(currency);
  const weekChange = best && lastWeekBest
    ? ((best.rate - lastWeekBest) / lastWeekBest) * 100
    : null;

  const top5 = todayRanked.slice(0, 5);

  const weekArrow = weekChange === null ? ""
    : weekChange > 0.01 ? `<span style="color:#22a36b">▲ ${weekChange.toFixed(2)}%</span>`
    : weekChange < -0.01 ? `<span style="color:#d84040">▼ ${Math.abs(weekChange).toFixed(2)}%</span>`
    : `<span style="color:#888">→ flat</span>`;

  const tableRows = top5.map((r, i) => `
    <tr style="border-bottom:1px solid #eee;">
      <td style="padding:8px 12px;color:#888;font-size:13px;">${i + 1}</td>
      <td style="padding:8px 12px;font-weight:${i === 0 ? "600" : "400"};color:${i === 0 ? "#111" : "#444"};">${r.bank}</td>
      <td style="padding:8px 12px;text-align:right;font-variant-numeric:tabular-nums;">₹${formatRate(r.rate)}</td>
    </tr>`).join("");

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>TTBuy weekly digest</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f3;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#111;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f3;padding:32px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08);">

        <!-- Header -->
        <tr>
          <td style="background:#111;padding:24px 32px;">
            <p style="margin:0;font-size:13px;color:#aaa;letter-spacing:.05em;text-transform:uppercase;">Weekly digest</p>
            <h1 style="margin:4px 0 0;font-size:22px;color:#fff;">${sym}→₹ Rates this week</h1>
          </td>
        </tr>

        <!-- Best bank highlight -->
        <tr>
          <td style="padding:28px 32px 0;">
            <p style="margin:0 0 6px;font-size:12px;color:#888;text-transform:uppercase;letter-spacing:.05em;">Today's best ${currency} rate</p>
            ${best ? `
            <p style="margin:0;font-size:28px;font-weight:700;color:#111;">₹${formatRate(best.rate)} <span style="font-size:15px;font-weight:400;color:#888;">/ ${currency}</span></p>
            <p style="margin:4px 0 0;font-size:14px;color:#444;">${best.bank} &nbsp;${weekArrow}</p>
            ` : `<p style="color:#888;">No data available.</p>`}
          </td>
        </tr>

        <!-- Spread callout -->
        ${spread !== null ? `
        <tr>
          <td style="padding:16px 32px 0;">
            <div style="background:#f9f9f7;border-radius:8px;padding:14px 18px;font-size:13px;color:#555;">
              Best vs worst today: <strong style="color:#111;">₹${formatInr(spread)}</strong> difference on ${sym}1,000 —
              worst bank is <strong>${worst.bank}</strong> at ₹${formatRate(worst.rate)}
            </div>
          </td>
        </tr>` : ""}

        <!-- Top 5 table -->
        <tr>
          <td style="padding:24px 32px 0;">
            <p style="margin:0 0 10px;font-size:13px;font-weight:600;color:#111;">Top banks today</p>
            <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;font-size:14px;">
              <thead>
                <tr style="border-bottom:2px solid #eee;">
                  <th style="padding:6px 12px;text-align:left;font-size:11px;color:#888;font-weight:500;">#</th>
                  <th style="padding:6px 12px;text-align:left;font-size:11px;color:#888;font-weight:500;">Bank</th>
                  <th style="padding:6px 12px;text-align:right;font-size:11px;color:#888;font-weight:500;">TT Buy (₹/${currency})</th>
                </tr>
              </thead>
              <tbody>${tableRows}</tbody>
            </table>
          </td>
        </tr>

        <!-- CTA -->
        <tr>
          <td style="padding:24px 32px;">
            <a href="${SITE_URL}?currency=${currency}" style="display:inline-block;background:#111;color:#fff;text-decoration:none;padding:11px 22px;border-radius:6px;font-size:14px;font-weight:500;">View full table →</a>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:16px 32px 28px;border-top:1px solid #eee;">
            <p style="margin:0;font-size:12px;color:#aaa;line-height:1.6;">
              Data scraped from public bank pages · Not affiliated with any bank<br/>
              <a href="${unsubLink}" style="color:#aaa;">Unsubscribe</a>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>`;
}

async function sendEmail({ to, subject, html }) {
  const apiKey = process.env.RESEND_API_KEY;
  if (!apiKey) throw new Error("RESEND_API_KEY env var not set");

  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ from: FROM_EMAIL, to, subject, html }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Resend API error ${res.status}: ${text}`);
  }

  return res.json();
}

export default async (req) => {
  // Allow both scheduled invocations and manual POST with the secret header.
  const isScheduled = req.headers.get("x-netlify-event") === "schedule";
  const isManual = req.headers.get("x-digest-secret") === process.env.DIGEST_SECRET;
  if (!isScheduled && !isManual) {
    return new Response("Unauthorized", { status: 401 });
  }

  const ratesRes = await fetch(RATES_URL);
  if (!ratesRes.ok) return new Response("Failed to fetch rates", { status: 502 });
  const rates = await ratesRes.json();

  const store = getStore("email-subscribers");
  const { blobs } = await store.list();

  const today = new Date().toISOString().split("T")[0];

  let sent = 0, skipped = 0, errors = 0;

  for (const { key } of blobs) {
    const raw = await store.get(key);
    if (!raw) continue;

    let data;
    try { data = JSON.parse(raw); } catch { continue; }

    const { email, currency = "USD" } = data;
    if (!email) continue;

    const currencyRates = rates[currency];
    if (!currencyRates) { skipped++; continue; }

    const dates = recentDates(currencyRates, 14);
    const todayRanked = latestRates(currencyRates, today);

    if (!todayRanked.length) { skipped++; continue; }

    // Find last week's best for trend comparison
    const lastWeekDate = dates.length >= 8 ? dates[dates.length - 8] : null;
    const lastWeekRanked = lastWeekDate ? latestRates(currencyRates, lastWeekDate) : [];
    const lastWeekBest = lastWeekRanked[0]?.rate ?? null;

    const best = todayRanked[0];
    const sym = currencySymbol(currency);
    const subject = `TTBuy weekly: ${best.bank} leads ${currency} at ₹${formatRate(best.rate)} this week`;

    const html = buildEmailHtml({
      currency,
      todayRanked,
      lastWeekBest,
      unsubLink: unsubUrl(email),
    });

    try {
      await sendEmail({ to: email, subject, html });
      sent++;
    } catch (err) {
      console.error(`Failed to send to ${email}:`, err.message);
      errors++;
    }
  }

  return new Response(JSON.stringify({ sent, skipped, errors, date: today }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
};
