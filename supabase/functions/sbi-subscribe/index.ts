import { createClient } from "npm:@supabase/supabase-js@2";

// Public signup endpoint for ShopBot Index (shopbotindex.com). No secrets in the client.
const ALLOWED = ["https://shopbotindex.com", "https://www.shopbotindex.com", "https://cstath71.github.io", "http://localhost:4321"];
const EMAIL_RE = /^[^\s@<>()\[\],;:"]{1,64}@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$/;
const MAX_PER_HOUR = 5;

function cors(origin: string | null) {
  const o = origin && ALLOWED.includes(origin) ? origin : ALLOWED[0];
  return { "Access-Control-Allow-Origin": o, "Access-Control-Allow-Methods": "POST, OPTIONS", "Access-Control-Allow-Headers": "content-type", "Vary": "Origin" };
}
const json = (b: unknown, s: number, h: Record<string, string>) => new Response(JSON.stringify(b), { status: s, headers: { ...h, "Content-Type": "application/json" } });

async function sha256(s: string) {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return Array.from(new Uint8Array(d)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

Deno.serve(async (req) => {
  const origin = req.headers.get("origin");
  const h = cors(origin);
  if (req.method === "OPTIONS") return new Response("ok", { headers: h });
  if (req.method !== "POST") return json({ ok: false, error: "method" }, 405, h);
  if (origin && !ALLOWED.includes(origin)) return json({ ok: false, error: "origin" }, 403, h);

  let body: Record<string, unknown> = {};
  try {
    const ct = req.headers.get("content-type") || "";
    if (ct.includes("application/json")) body = await req.json();
    else body = Object.fromEntries((await req.formData()).entries());
  } catch { return json({ ok: false, error: "bad_request" }, 400, h); }

  // Honeypot: real users never fill the hidden 'website' field. Pretend success.
  if (String(body.website ?? "").trim() !== "") return json({ ok: true }, 200, h);

  const email = String(body.email ?? "").trim().toLowerCase();
  if (email.length > 254 || !EMAIL_RE.test(email)) return json({ ok: false, error: "invalid_email" }, 400, h);

  const sb = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, { auth: { persistSession: false } });
  const ip = (req.headers.get("x-forwarded-for") || "").split(",")[0].trim() || "unknown";
  const ipHash = await sha256("sbi:" + ip);

  // Rate limit: max MAX_PER_HOUR attempts per IP per hour.
  const since = new Date(Date.now() - 3600_000).toISOString();
  const { count } = await sb.from("sbi_signup_attempts").select("id", { count: "exact", head: true }).eq("ip_hash", ipHash).gte("created_at", since);
  if ((count ?? 0) >= MAX_PER_HOUR) return json({ ok: false, error: "rate_limited" }, 429, h);
  await sb.from("sbi_signup_attempts").insert({ ip_hash: ipHash });

  const { error } = await sb.from("sbi_subscribers").upsert({ email, ip_hash: ipHash, unsubscribed_at: null }, { onConflict: "email" });
  if (error) return json({ ok: false, error: "store_failed" }, 500, h);

  // Mirror into the Resend segment. Settings come from function secrets (RESEND_API_KEY, SBI_RESEND_SEGMENT_ID) if set,
  // otherwise from Supabase Vault via public.sbi_resend_config() (executable by service_role only).
  let key = Deno.env.get("RESEND_API_KEY");
  let seg = Deno.env.get("SBI_RESEND_SEGMENT_ID");
  if (!key || !seg) {
    try {
      const { data } = await sb.rpc("sbi_resend_config");
      const cfg = Array.isArray(data) ? data[0] : data;
      key = key || cfg?.api_key || undefined;
      seg = seg || cfg?.segment_id || undefined;
    } catch { /* no config: keep the row for a manual sync */ }
  }
  if (key && seg) {
    try {
      const auth = { Authorization: `Bearer ${key}`, "Content-Type": "application/json" };
      // Existing contact (e.g. already on another list): add it to the segment without touching its global subscription status.
      let r = await fetch(`https://api.resend.com/contacts/${encodeURIComponent(email)}/segments/${seg}`, { method: "POST", headers: auth });
      // Not a contact yet: create it directly in the segment.
      if (r.status === 404) r = await fetch("https://api.resend.com/contacts", { method: "POST", headers: auth, body: JSON.stringify({ email, unsubscribed: false, segments: [{ id: seg }] }) });
      if (r.ok) await sb.from("sbi_subscribers").update({ synced_to_resend_at: new Date().toISOString() }).eq("email", email);
    } catch { /* keep the Supabase row; sync later */ }
  }
  return json({ ok: true }, 200, h);
});
