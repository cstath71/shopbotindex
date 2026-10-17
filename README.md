# ShopBot Index (shopbotindex.com)

What online stores tell AI shopping agents: the weekly index. Headline measure: does a store publish a UCP profile, the official machine-readable profile AI shopping agents read? A static site that measures which online stores publish a
Universal Commerce Protocol (UCP) business profile at `/.well-known/ucp` (path per the UCP spec:
https://ucp.dev/specification/overview/ , "Discovery: Fetch business profile from /.well-known/ucp").
Three segments side by side: Shopify stores, big retailers, other retailers & marketplaces.

## Weekly update (one command)

```bash
cd /workspace/agenticshoppingindex && scripts/weekly.sh
```

Crawls (~10 minutes), rebuilds `dist/`, commits `data/` + `dist/` as cstath71 and pushes to `main`; the GitHub Pages
workflow (`.github/workflows/pages.yml`) then deploys `dist/` to https://shopbotindex.com.
`scripts/weekly.sh --no-push` crawls and builds only. Example cron (Mondays 06:00 box time):
`0 6 * * 1 cd /workspace/agenticshoppingindex && scripts/weekly.sh >> /tmp/sbi-weekly.log 2>&1`

## Pipeline
0. `python3 scripts/wiki_seeds.py`: resolves the Wikipedia retail list pages to Wikidata items and writes `data/seeds/wikipedia_lists.json` (rerun only to refresh the seed list).
1. `python3 scripts/seeds.py`: builds `data/seeds.json` (one entry per retailer, segment shopify/big/other, country sites as children) from cited public sources (see `data/seeds/SOURCES.md`).
2. `python3 scripts/crawl.py`: polite crawl (robots.txt honoured, 12 workers, 10 s timeouts, User-Agent `ShopBotIndexBot/1.0` with a link to methodology.html#crawler and hello@shopbotindex.com) and writes `data/crawl-YYYY-MM-DD.json` + `data/latest.json` (latest is not committed).
   Site statuses: ucp, no_ucp, not_json, json_without_ucp, blocked (401/403/429/451), error, robots_disallow. A retailer is `ucp` if any site has a profile, `no_ucp` if any site answered without one, else `couldnt_check` (excluded from rates).
3. `python3 scripts/build.py`: compares with the most recent earlier `crawl-*.json` and writes `data/changes-latest.json` (joined, left, now_unreachable, newly_tracked, capability_changes); then writes `dist/` (home, stores table, segments, capabilities, categories, assistants, what changed, methodology, about, privacy, sitemap, robots, CNAME, OG image from `assets/og.png`).
4. `data/channels.json`: assistant to retailer claims, hand-maintained, official sources only.

Stdlib Python only. Site URL via `SBI_SITE` (default https://shopbotindex.com). Preview: `cd dist && python3 -m http.server 4321`.

## Newsletter signup
Forms post to the Supabase edge function `sbi-subscribe` (project `uufmlmwgvoqhhtqgrclu`, source in `supabase/functions/sbi-subscribe/`):
honeypot field `website`, email validation, 5 attempts per IP-hash per hour, rows in `sbi_subscribers` (RLS on, no public access).
Resend segment: **ShopBot Index** `6aeffea0-50d8-4887-b18d-8babefbbc1fa`. Resend sending domain: `shopbotindex.com`
(id `4793016a-f6c9-40df-9db2-2926aa36ad4c`, EU region eu-west-1, open/click tracking off; DNS records on `send.` + `rsend.` + `resend._domainkey`, no clash with Zoho on the root).
The Resend API key and segment id are read from function secrets `RESEND_API_KEY` / `SBI_RESEND_SEGMENT_ID` if set, otherwise from Supabase Vault
(secrets `sbi_resend_api_key`, `sbi_resend_segment_id`) via `public.sbi_resend_config()`, a SECURITY DEFINER function executable only by
service_role (`supabase/migrations/20261017_sbi_resend_config.sql`; anon/authenticated get "permission denied"). Each signup is mirrored into the segment:
first "add existing contact to segment" (keeps an existing contact's global unsubscribe status), and on 404 "create contact in segment";
`synced_to_resend_at` is stamped on success. If the secrets are missing or Resend fails, the row stays in Supabase; sync those rows
(`synced_to_resend_at is null`) the same way as Fusion Updates (`/workspace/newsletter/sync_subscribers.md`, with `sbi_subscribers` and the segment id above).
The API key copy lives outside the repo in `/home/box/.private/resend-shopbotindex.json` (never commit it).

**Welcome email (automatic, ON since 17 Oct 2026, approved by Gus).** For a newly created, subscribed Resend contact, `sbi-subscribe` (version 4)
fires the Resend event `sbi.subscribed` (event id `01a14a26-d8e9-731a-8294-9bbcc8918e43`), which starts the enabled automation
**ShopBot Index welcome** (`01a14a27-01ed-712d-a1fb-36acf50d211a`): send template **ShopBot Index welcome** (`2e6535a3-17f5-448d-8f12-6e4b2e29492a`,
alias `sbi-welcome`, published) from `ShopBot Index <hello@shopbotindex.com>`, reply-to `hello@shopbotindex.com`, subject "Welcome to ShopBot Index".
Gated by Vault secret `sbi_welcome_enabled` = `'true'`, exposed as `welcome_enabled` by `sbi_resend_config()`
(`supabase/migrations/20261017_sbi_welcome_flag.sql`, still service_role only). Never fired for existing contacts (e.g. already on another list),
re-subscribes or reserved test domains (example.com/.net/.org, *.test, *.example, *.invalid, *.localhost); existing subscribers were not backfilled.
Off: `delete from vault.secrets where name='sbi_welcome_enabled';` On: `select vault.create_secret('true','sbi_welcome_enabled','Send ShopBot Index welcome from sbi-subscribe');`
Content: `newsletter/welcome/build_welcome.py` builds `welcome.html` / `welcome.txt`; after editing, rerun it, `update-template` (html + text) and `publish-template`.
Test with Resend's sandbox address `delivered+<tag>@resend.dev` (not excluded, so it runs the whole path), then delete the contact, the `sbi_subscribers` row and the `sbi_signup_attempts` entry.

## Shopify affiliate (Impact)
- Approved 17 Oct 2026. Impact account id **7989432**, Shopify campaign **13624**.
- Tracking link (Shopify free trial): `https://shopify.pxf.io/c/7989432/1061744/13624`, set in `config/site.json` (`shopify_affiliate_url`, `affiliate_disclosure`), so every rebuild (`scripts/weekly.sh`) keeps it.
- Shown in the "Selling online?" box on the home page and the Shopify segment page, plus the About page; all links use `rel="sponsored noopener"`. Disclosure next to the links and on About + Privacy: "We may earn a commission if you start a Shopify trial through our links."
- New deep links to other Shopify pages: create them in Impact with **Create a Link** (campaign 13624), then add them to `config/site.json`.
- Impact site verification meta tags are in the page template in `scripts/build.py`.
