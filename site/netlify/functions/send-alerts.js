import { getStore } from "@netlify/blobs";
import webpush from "web-push";

webpush.setVapidDetails(
  process.env.VAPID_SUBJECT,
  process.env.VAPID_PUBLIC_KEY,
  process.env.VAPID_PRIVATE_KEY
);

const RATES_URL =
  "https://raw.githubusercontent.com/RakshithNM/ttbuy-dashboard/refs/heads/main/data/rates.json";

export default async (req) => {
  if (req.headers.get("x-alerts-secret") !== process.env.ALERTS_SECRET) {
    return new Response("Unauthorized", { status: 401 });
  }

  const ratesRes = await fetch(RATES_URL);
  if (!ratesRes.ok) return new Response("Failed to fetch rates", { status: 502 });
  const rates = await ratesRes.json();

  const today = new Date().toISOString().split("T")[0];
  const store = getStore("push-subscriptions");
  const { blobs } = await store.list();

  let sent = 0, skipped = 0, errors = 0;

  for (const { key } of blobs) {
    const raw = await store.get(key);
    if (!raw) continue;

    let data;
    try { data = JSON.parse(raw); } catch { continue; }

    const { subscription, alerts = [], last_alerted_date } = data;

    if (last_alerted_date === today) { skipped++; continue; }

    const triggered = [];
    for (const alert of alerts) {
      const { bank, currency, threshold, direction } = alert;
      const points = rates[currency]?.[bank];
      if (!points?.length) continue;
      const rate = points[points.length - 1].ttbuy;
      const hit = direction === "above" ? rate >= threshold : rate <= threshold;
      if (hit) triggered.push({ bank, currency, rate, threshold, direction });
    }

    if (!triggered.length) continue;

    const { bank, currency, rate, threshold, direction } = triggered[0];
    const payload = JSON.stringify({
      title: `Rate alert: ${bank}`,
      body: `${currency} rate is ₹${rate.toFixed(2)} (${direction} your ₹${threshold.toFixed(2)} target)`,
      url: "https://ttbuyrates.rakshithnettar.com",
    });

    try {
      await webpush.sendNotification(subscription, payload);
      await store.set(key, JSON.stringify({ ...data, last_alerted_date: today }));
      sent++;
    } catch (err) {
      if (err.statusCode === 410 || err.statusCode === 404) await store.delete(key);
      errors++;
    }
  }

  return new Response(JSON.stringify({ sent, skipped, errors, date: today }), { status: 200 });
};
