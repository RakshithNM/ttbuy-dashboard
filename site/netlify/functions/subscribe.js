import { getStore } from "@netlify/blobs";
import crypto from "crypto";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Content-Type": "application/json",
};

function subKey(endpoint) {
  return crypto.createHash("sha256").update(endpoint).digest("hex").slice(0, 20);
}

async function handle(req) {
  if (req.method === "OPTIONS") {
    return new Response("", {
      status: 204,
      headers: {
        ...CORS,
        "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      },
    });
  }

  const store = getStore("push-subscriptions");

  if (req.method === "GET") {
    const endpoint = new URL(req.url).searchParams.get("endpoint");
    if (!endpoint) return new Response(JSON.stringify({ error: "Missing endpoint" }), { status: 400, headers: CORS });
    const raw = await store.get(subKey(endpoint));
    const alerts = raw ? (JSON.parse(raw).alerts ?? []) : [];
    return new Response(JSON.stringify({ alerts }), { status: 200, headers: CORS });
  }

  if (req.method === "POST") {
    let body;
    try { body = await req.json(); } catch {
      return new Response(JSON.stringify({ error: "Invalid JSON" }), { status: 400, headers: CORS });
    }

    const { subscription, alerts } = body;
    if (!subscription?.endpoint) {
      return new Response(JSON.stringify({ error: "Missing subscription" }), { status: 400, headers: CORS });
    }

    const key = subKey(subscription.endpoint);
    await store.set(key, JSON.stringify({ subscription, alerts: alerts ?? [], created: Date.now() }));
    return new Response(JSON.stringify({ ok: true }), { status: 200, headers: CORS });
  }

  if (req.method === "DELETE") {
    let body;
    try { body = await req.json(); } catch {
      return new Response(JSON.stringify({ error: "Invalid JSON" }), { status: 400, headers: CORS });
    }

    const { endpoint } = body;
    if (!endpoint) {
      return new Response(JSON.stringify({ error: "Missing endpoint" }), { status: 400, headers: CORS });
    }

    await store.delete(subKey(endpoint));
    return new Response(JSON.stringify({ ok: true }), { status: 200, headers: CORS });
  }

  return new Response(JSON.stringify({ error: "Method not allowed" }), { status: 405, headers: CORS });
}

export default async (req) => {
  try {
    return await handle(req);
  } catch (err) {
    console.error("subscribe error:", err);
    return new Response(JSON.stringify({ error: err.message, stack: err.stack }), {
      status: 500,
      headers: CORS,
    });
  }
};
