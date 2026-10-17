# ShopBot Index (shopbotindex.com)

Which online stores can AI shopping agents actually buy from? A static site that measures which online stores publish a
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
2. `python3 scripts/crawl.py`: polite crawl (robots.txt honoured, 12 workers, 10 s timeouts, User-Agent `ShopBotIndexBot/1.0`) and writes `data/crawl-YYYY-MM-DD.json` + `data/latest.json` (latest is not committed).
   Site statuses: ucp, no_ucp, not_json, json_without_ucp, blocked (401/403/429/451), error, robots_disallow. A retailer is `ucp` if any site has a profile, `no_ucp` if any site answered without one, else `couldnt_check` (excluded from rates).
3. `python3 scripts/build.py`: compares with the most recent earlier `crawl-*.json` and writes `data/changes-latest.json` (joined, left, now_unreachable, newly_tracked, capability_changes); then writes `dist/` (home, stores table, segments, capabilities, categories, assistants, what changed, methodology, about, privacy, sitemap, robots, CNAME, OG image from `assets/og.png`).
4. `data/channels.json`: assistant to retailer claims, hand-maintained, official sources only.

Stdlib Python only. Site URL via `SBI_SITE` (default https://shopbotindex.com). Preview: `cd dist && python3 -m http.server 4321`.

## Newsletter signup
Forms post to the Supabase edge function `sbi-subscribe` (project `uufmlmwgvoqhhtqgrclu`, source in `supabase/functions/sbi-subscribe/`):
honeypot field `website`, email validation, 5 attempts per IP-hash per hour, rows in `sbi_subscribers` (RLS on, no public access).
Resend segment: **ShopBot Index** `6aeffea0-50d8-4887-b18d-8babefbbc1fa`. The function mirrors new signups into it only if the
`RESEND_API_KEY` and `SBI_RESEND_SEGMENT_ID` function secrets are set; otherwise sync manually like Fusion Updates
(`/workspace/newsletter/sync_subscribers.md`, using `sbi_subscribers` and the segment id above). No sending domain yet; no emails are sent.

## Placeholders
The "Selling online?" box is a labelled affiliate placeholder; no affiliate account exists.
