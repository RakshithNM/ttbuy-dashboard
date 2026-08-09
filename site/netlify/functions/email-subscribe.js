import { getStore } from "@netlify/blobs";
import crypto from "crypto";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Content-Type": "application/json",
};

const VALID_CURRENCIES = ["USD", "GBP", "EUR", "AED"];

function emailKey(email) {
  return crypto.createHash("sha256").update(email).digest("hex").slice(0, 20);
}

function makeToken(email) {
  const secret = process.env.DIGEST_SECRET;
  if (!secret) throw new Error("DIGEST_SECRET env var not set");
  return crypto.createHmac("sha256", secret).update(email).digest("hex");
}

async function handle(req) {
  if (req.method === "OPTIONS") {
    return new Response("", {
      status: 204,
      headers: {
        ...CORS,
        "Access-Control-Allow-Methods": "POST, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      },
    });
  }

  const store = getStore("email-subscribers");

  if (req.method === "POST") {
    let body;
    try { body = await req.json(); } catch {
      return new Response(JSON.stringify({ error: "Invalid JSON" }), { status: 400, headers: CORS });
    }

    const email = (body.email ?? "").toLowerCase().trim();
    const currency = VALID_CURRENCIES.includes(body.currency) ? body.currency : "USD";

    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return new Response(JSON.stringify({ error: "Invalid email address" }), { status: 400, headers: CORS });
    }

    const key = emailKey(email);
    await store.set(key, JSON.stringify({ email, currency, subscribedAt: Date.now() }));

    return new Response(JSON.stringify({ ok: true }), { status: 200, headers: CORS });
  }

  if (req.method === "DELETE") {
    let body;
    try { body = await req.json(); } catch {
      return new Response(JSON.stringify({ error: "Invalid JSON" }), { status: 400, headers: CORS });
    }

    const email = (body.email ?? "").toLowerCase().trim();
    const token = body.token;
    if (!email || !token) {
      return new Response(JSON.stringify({ error: "Missing email or token" }), { status: 400, headers: CORS });
    }

    if (!crypto.timingSafeEqual(Buffer.from(token), Buffer.from(makeToken(email)))) {
      return new Response(JSON.stringify({ error: "Invalid token" }), { status: 403, headers: CORS });
    }

    await store.delete(emailKey(email));
    return new Response(JSON.stringify({ ok: true }), { status: 200, headers: CORS });
  }

  return new Response(JSON.stringify({ error: "Method not allowed" }), { status: 405, headers: CORS });
}

export default async (req) => {
  try {
    return await handle(req);
  } catch (err) {
    console.error("email-subscribe error:", err);
    return new Response(JSON.stringify({ error: err.message }), { status: 500, headers: CORS });
  }
};
