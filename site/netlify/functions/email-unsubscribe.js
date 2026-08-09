import { getStore } from "@netlify/blobs";
import crypto from "crypto";

const SITE_URL = process.env.URL || "https://ttbuyrates.rakshithnettar.com";

function emailKey(email) {
  return crypto.createHash("sha256").update(email).digest("hex").slice(0, 20);
}

function makeToken(email) {
  const secret = process.env.DIGEST_SECRET;
  if (!secret) throw new Error("DIGEST_SECRET env var not set");
  return crypto.createHmac("sha256", secret).update(email).digest("hex");
}

function htmlPage(title, body) {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${title} · TTBuy Rates</title>
  <style>
    body { font-family: -apple-system, sans-serif; max-width: 480px; margin: 80px auto; padding: 0 20px; text-align: center; color: #333; }
    h2 { font-size: 1.3rem; margin-bottom: 12px; }
    p { color: #666; line-height: 1.6; }
    a { color: #22a36b; }
  </style>
</head>
<body>${body}</body>
</html>`;
}

export default async (req) => {
  try {
    const url = new URL(req.url);
    const email = (url.searchParams.get("email") ?? "").toLowerCase().trim();
    const token = url.searchParams.get("token") ?? "";

    if (!email || !token) {
      return new Response(
        htmlPage("Invalid link", "<h2>Invalid unsubscribe link</h2><p>The link is missing required parameters.</p>"),
        { status: 400, headers: { "Content-Type": "text/html" } }
      );
    }

    const expected = makeToken(email);
    if (!crypto.timingSafeEqual(Buffer.from(token), Buffer.from(expected))) {
      return new Response(
        htmlPage("Invalid link", "<h2>Invalid unsubscribe link</h2><p>This link has expired or is incorrect.</p>"),
        { status: 403, headers: { "Content-Type": "text/html" } }
      );
    }

    const store = getStore("email-subscribers");
    await store.delete(emailKey(email));

    return new Response(
      htmlPage("Unsubscribed", `
        <h2>You've been unsubscribed</h2>
        <p>You won't receive the weekly TTBuy digest anymore.</p>
        <p><a href="${SITE_URL}">Back to TTBuy Rates →</a></p>
      `),
      { status: 200, headers: { "Content-Type": "text/html" } }
    );
  } catch (err) {
    console.error("email-unsubscribe error:", err);
    return new Response(
      htmlPage("Error", "<h2>Something went wrong</h2><p>Please try again or contact us.</p>"),
      { status: 500, headers: { "Content-Type": "text/html" } }
    );
  }
};
