# Agentic Shopping Index (local prototype)

Static site measuring which online stores publish a Universal Commerce Protocol (UCP) business profile at `/.well-known/ucp`
(path per the UCP spec: https://ucp.dev/specification/overview/ , "Discovery: Fetch business profile from /.well-known/ucp").

## Pipeline
1. `python3 scripts/seeds.py`: builds `data/seeds.json` from cited public sources (see `data/seeds/SOURCES.md`).
2. `python3 scripts/crawl.py`: polite crawl (robots.txt honoured, 12 workers, 10 s timeouts, honest User-Agent) and writes `data/crawl-YYYY-MM-DD.json` + `data/latest.json`.
3. `python3 scripts/build.py`: writes `dist/` (home, stores table, capability/category pages, assistants, what changed, methodology, about, sitemap, robots).
4. `data/channels.json`: assistant to retailer claims, hand-maintained, official sources only.

Stdlib Python only. Site URL placeholder via `ASI_SITE` (domain not owned yet).

## Not done (needs Gus's approval)
No domain, no GitHub repo/push, newsletter form not wired, affiliate link is a placeholder, no scheduled crawl.
