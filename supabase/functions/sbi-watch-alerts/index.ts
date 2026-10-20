import { createClient } from "npm:@supabase/supabase-js@2";

// "Watch this store" alerts for ShopBot Index. Called by the weekly job on the box (scripts/watch_alerts.py) after the crawl,
// with the stores that started or stopped publishing a UCP profile. Not public: needs the shared secret (Vault sbi_alerts_token)
// in the x-sbi-token header.
// mode "dry": returns who would get an alert (addresses masked), sends nothing.
// mode "send": sends only when Vault sbi_watch_alerts_enabled = 'true', OR when only_to is a box-owned test inbox (TEST_INBOXES).
//              Otherwise it answers like a dry run with sent: 0 and enabled: false.
const TEST_INBOXES = ["cstath@mail.grokbot.com"];
const SITE = "https://shopbotindex.com";
const FROM = "ShopBot Index <hello@shopbotindex.com>";
const ID_RE = /^[A-Za-z0-9._-]{1,120}$/;
const SLUG_RE = /^[a-z0-9-]{1,160}$/;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const json = (b: unknown, s = 200) => new Response(JSON.stringify(b), { status: s, headers: { "Content-Type": "application/json" } });
const esc = (s: string) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));
const mask = (e: string) => { const [u, d] = e.split("@"); return (u.slice(0, 2) + "***@" + d); };
function same(a: string, b: string) { if (a.length !== b.length) return false; let x = 0; for (let i = 0; i < a.length; i++) x |= a.charCodeAt(i) ^ b.charCodeAt(i); return x === 0; }
const longDate = (d: string) => new Date(d + "T12:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });

type Change = { store_id: string; slug: string; name: string; change: "started" | "stopped" };

function message(c: Change, crawl: string, token: string) {
  const page = `${SITE}/store/${c.slug}.html`, stop = `${SITE}/unwatch.html?t=${token}`, day = longDate(crawl);
  const subject = c.change === "started" ? `${c.name} now publishes a UCP profile` : `${c.name} no longer publishes a UCP profile`;
  const line = c.change === "started"
    ? `In our crawl of ${day}, ${c.name} published a UCP profile, the profile AI shopping agents read. Our previous crawl didn't find one.`
    : `In our crawl of ${day}, we found no UCP profile for ${c.name}. Our previous crawl found one.`;
  const why = `You're getting this because you asked us to email you if ${c.name} starts or stops publishing a UCP profile.`;
  const text = `${line}\n\nSee the full result: ${page}\n\n${why}\nStop alerts for this store: ${stop}\nPrivacy: ${SITE}/privacy.html\n\nShopBot Index: the weekly index of what online stores tell AI shopping agents · ${SITE}`;
  const html = `<div style="font:16px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#15202b;max-width:560px">
<p style="margin:0 0 1rem"><img src="${SITE}/logo-64.png" width="32" height="32" alt="" style="vertical-align:middle;border-radius:50%"> <b>ShopBot Index</b></p>
<p>${esc(line)}</p><p><a href="${page}" style="color:#0b5cad">See the full result for ${esc(c.name)} →</a></p>
<p style="color:#56677a;font-size:13px">${esc(why)} <a href="${stop}" style="color:#56677a">Stop alerts for this store</a> · <a href="${SITE}/privacy.html" style="color:#56677a">Privacy</a><br>ShopBot Index: the weekly index of what online stores tell AI shopping agents</p></div>`;
  return { subject, text, html, stop };
}

Deno.serve(async (req) => {
  if (req.method !== "POST") return json({ ok: false, error: "method" }, 405);
  const sb = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, { auth: { persistSession: false } });
  const { data: cfgRows } = await sb.rpc("sbi_alerts_config");
  const cfg = Array.isArray(cfgRows) ? cfgRows[0] : cfgRows;
  if (!cfg?.alerts_token || !same(req.headers.get("x-sbi-token") || "", cfg.alerts_token)) return json({ ok: false, error: "unauthorized" }, 401);

  let b: Record<string, unknown> = {};
  try { b = await req.json(); } catch { return json({ ok: false, error: "bad_request" }, 400); }
  const crawl = String(b.crawl_date ?? "");
  if (!DATE_RE.test(crawl)) return json({ ok: false, error: "crawl_date" }, 400);
  const changes = (Array.isArray(b.changes) ? b.changes : []).filter((c: any) =>
    c && ID_RE.test(String(c.store_id)) && SLUG_RE.test(String(c.slug)) && typeof c.name === "string" && c.name.length <= 200 && (c.change === "started" || c.change === "stopped")) as Change[];
  if (changes.length > 1000) return json({ ok: false, error: "too_many" }, 400);
  const onlyTo = b.only_to ? String(b.only_to).toLowerCase() : "";
  const testSend = onlyTo !== "" && TEST_INBOXES.includes(onlyTo);
  if (onlyTo && !testSend) return json({ ok: false, error: "only_to must be a test inbox" }, 400);
  const wantSend = b.mode === "send";
  const enabled = cfg.alerts_enabled === true;
  const sending = wantSend && (enabled || testSend);

  const byId = new Map(changes.map((c) => [c.store_id, c]));
  const rows: any[] = [];
  const ids = [...byId.keys()];
  for (let i = 0; i < ids.length; i += 200) {
    const { data, error } = await sb.from("sbi_watches").select("id, store_id, token, last_alert_crawl, sbi_subscribers(email, unsubscribed_at)").in("store_id", ids.slice(i, i + 200));
    if (error) return json({ ok: false, error: "query_failed" }, 500);
    rows.push(...(data ?? []));
  }
  const due = rows.filter((w) => w.sbi_subscribers && !w.sbi_subscribers.unsubscribed_at && w.last_alert_crawl !== crawl
    && (!onlyTo || w.sbi_subscribers.email === onlyTo));
  const plan = due.map((w) => ({ to: mask(w.sbi_subscribers.email), store_id: w.store_id, change: byId.get(w.store_id)!.change }));
  if (!sending) return json({ ok: true, mode: "dry", enabled, changes: changes.length, watches_matched: rows.length, would_send: plan.length, plan });

  const key = cfg.api_key;
  if (!key) return json({ ok: false, error: "no_resend_key" }, 500);
  const auth = { Authorization: `Bearer ${key}`, "Content-Type": "application/json" };
  let sent = 0, skipped = 0, failed = 0;
  for (const w of due) {
    const email = w.sbi_subscribers.email;
    // Respect a global unsubscribe in Resend (e.g. from the weekly email's unsubscribe link).
    const rc = await fetch(`https://api.resend.com/contacts/${encodeURIComponent(email)}`, { headers: auth });
    if (rc.ok && (await rc.json().catch(() => ({})))?.unsubscribed === true) { skipped++; continue; }
    const m = message(byId.get(w.store_id)!, crawl, w.token);
    const r = await fetch("https://api.resend.com/emails", { method: "POST", headers: { ...auth, "Idempotency-Key": `sbi-watch-${w.id}-${crawl}` },
      body: JSON.stringify({ from: FROM, to: [email], reply_to: "hello@shopbotindex.com", subject: m.subject, html: m.html, text: m.text,
        headers: { "List-Unsubscribe": `<${m.stop}>` } }) });
    if (r.ok) { sent++; await sb.from("sbi_watches").update({ last_alert_crawl: crawl, last_alerted_at: new Date().toISOString() }).eq("id", w.id); }
    else failed++;
  }
  return json({ ok: true, mode: "send", enabled, test_send: testSend, changes: changes.length, watches_matched: rows.length, sent, skipped, failed });
});
