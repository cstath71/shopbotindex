# Agentic Shopping Index (local prototype)

Static site measuring which online stores publish a Universal Commerce Protocol (UCP) business profile at `/.well-known/ucp`
(path per the UCP spec: https://ucp.dev/specification/overview/ , "Discovery: Fetch business profile from /.well-known/ucp").

## Pipeline
0. `python3 scripts/wiki_seeds.py`: resolves the Wikipedia retail list pages to Wikidata items and writes `data/seeds/wikipedia_lists.json`.
1. `python3 scripts/seeds.py`: builds `data/seeds.json` (one entry per retailer, segment shopify/big/other, country sites as children) from cited public sources (see `data/seeds/SOURCES.md`).
2. `python3 scripts/crawl.py`: polite crawl (robots.txt honoured, 12 workers, 10 s timeouts, honest User-Agent) and writes `data/crawl-YYYY-MM-DD.json` + `data/latest.json`.
   Site statuses: ucp, no_ucp, not_json, json_without_ucp, blocked (401/403/429/451), error, robots_disallow. A retailer is `ucp` if any site has a profile, `no_ucp` if any site answered without one, else `couldnt_check` (excluded from rates).
3. `python3 scripts/build.py`: compares with the most recent earlier `crawl-*.json` (new format) and writes `data/changes-latest.json` (joined, left, now_unreachable, newly_tracked, capability_changes); then writes `dist/` (home, stores table, capability/category pages, assistants, what changed, methodology, about, sitemap, robots).
4. `data/channels.json`: assistant to retailer claims, hand-maintained, official sources only.

Stdlib Python only. Site URL placeholder via `ASI_SITE` (domain not owned yet).

Run weekly: steps 2-3. The first real "who joined" list appears with the second crawl.

## Not done (needs Gus's approval)
No domain, no GitHub repo/push, newsletter form not wired, affiliate link is a placeholder, no scheduled crawl.
