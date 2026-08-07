const { getStore } = require("@netlify/blobs");
const crypto = require("crypto");

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Content-Type": "application/json",
};

function subKey(endpoint) {
  return crypto.createHash("sha256").update(endpoint).digest("hex").slice(0, 20);
}

exports.handler = async (event) => {
  if (event.httpMethod === "OPTIONS") {
    return {
      statusCode: 204,
      headers: {
        ...CORS,
        "Access-Control-Allow-Methods": "POST, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      },
      body: "",
    };
  }

  const store = getStore("push-subscriptions");

  if (event.httpMethod === "POST") {
    let body;
    try { body = JSON.parse(event.body || "{}"); } catch { return { statusCode: 400, headers: CORS, body: JSON.stringify({ error: "Invalid JSON" }) }; }

    const { subscription, alerts } = body;
    if (!subscription?.endpoint) return { statusCode: 400, headers: CORS, body: JSON.stringify({ error: "Missing subscription" }) };

    const key = subKey(subscription.endpoint);
    await store.set(key, JSON.stringify({ subscription, alerts: alerts ?? [], created: Date.now() }));
    return { statusCode: 200, headers: CORS, body: JSON.stringify({ ok: true }) };
  }

  if (event.httpMethod === "DELETE") {
    let body;
    try { body = JSON.parse(event.body || "{}"); } catch { return { statusCode: 400, headers: CORS, body: JSON.stringify({ error: "Invalid JSON" }) }; }

    const { endpoint } = body;
    if (!endpoint) return { statusCode: 400, headers: CORS, body: JSON.stringify({ error: "Missing endpoint" }) };

    await store.delete(subKey(endpoint));
    return { statusCode: 200, headers: CORS, body: JSON.stringify({ ok: true }) };
  }

  return { statusCode: 405, headers: CORS, body: JSON.stringify({ error: "Method not allowed" }) };
};
