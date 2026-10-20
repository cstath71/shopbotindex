import { createClient } from "npm:@supabase/supabase-js@2";

// Cookie-free visit counter for shopbotindex.com. Stores only: day, path, referrer domain, utm_source/medium/campaign,
// aggregated as a count (public.sbi_pageviews_daily). No IP, no cookie, no user agent, no identifier of any kind is stored.
// Skipped when the browser sends Do Not Track (DNT: 1) or Global Privacy Control (Sec-GPC: 1); the page script also checks before sending.
const ALLOWED = ["https://shopbotindex.com", "https://www.shopbotindex.com"];
const BOT_RE = /bot|crawl|spider|slurp|preview|fetch|headless|lighthouse|python|curl|wget|httpclient|monitor/i;
const PATH_RE = /^\/[A-Za-z0-9\/._-]{0,199}$/;
const DOMAIN_RE = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$/;
const TAG_RE = /^[a-z0-9._-]{1,60}$/;
const done = () => new Response(null, { status: 204, headers: { "Access-Control-Allow-Origin": "https://shopbotindex.com", "Vary": "Origin" } });

Deno.serve(async (req) => {
  if (req.method !== "POST") return done();
  const origin = req.headers.get("origin") || "";
  if (!ALLOWED.includes(origin)) return done();
  if (req.headers.get("dnt") === "1" || req.headers.get("sec-gpc") === "1") return done();
  if (BOT_RE.test(req.headers.get("user-agent") || "")) return done();
  let b: Record<string, unknown> = {};
  try { b = JSON.parse((await req.text()).slice(0, 2000)); } catch { return done(); }
  let path = String(b.p ?? "").split(/[?#]/)[0];
  if (path.endsWith("/index.html")) path = path.slice(0, -10);
  if (!PATH_RE.test(path)) return done();
  let ref = String(b.r ?? "").toLowerCase().replace(/^www\./, "");
  if (!DOMAIN_RE.test(ref) || ref.length > 100 || ref === "shopbotindex.com") ref = "";
  const tag = (v: unknown) => { const t = String(v ?? "").toLowerCase().trim(); return TAG_RE.test(t) ? t : ""; };
  const sb = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, { auth: { persistSession: false } });
  try { await sb.rpc("sbi_count_view", { p_path: path, p_ref: ref, p_src: tag(b.s), p_med: tag(b.m), p_camp: tag(b.c) }); } catch { /* best effort */ }
  return done();
});
