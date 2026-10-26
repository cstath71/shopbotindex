# Seed list sources (all fetched 2026-10-17)

Three segments, shown side by side on the site. A retailer belongs to exactly one segment.

## Shopify stores (segment `shopify`, 1188 retailers)
Public lists of stores that run on Shopify:
1. GitHub ihof/shopify, `shopify-sites.txt` (sneaker/streetwear boutiques): https://github.com/ihof/shopify/blob/master/shopify-sites.txt (`ihof_shopify_sites.txt`)
2. GitHub dipinarora9/Shopify-Domains-Scraper, `script_output.csv` (mixed Shopify stores, mostly Europe): https://github.com/dipinarora9/Shopify-Domains-Scraper/blob/master/script_output.csv (`dipinarora_script_output.csv`)
3. GitHub TeamDukaan/performance, `shopify stores - shopify.csv` (mostly Indian D2C brands). We use the first 900 unique domains (`TEAMDUKAAN_LIMIT` in scripts/seeds.py): https://github.com/TeamDukaan/performance/blob/master/shopify%20stores%20-%20shopify.csv (`teamdukaan_shopify.csv`)

## Big retailers (`big`, 380) and other retailers & marketplaces (`other`, 708)
4. English Wikipedia list pages, read via the MediaWiki API (`scripts/wiki_seeds.py` writes `wikipedia_lists.json`). Each linked article is resolved to its Wikidata item and kept only if it has an official website (P856), is not a person/place/list, and is not dissolved (P576):
   - https://en.wikipedia.org/wiki/List_of_largest_retail_companies
   - https://en.wikipedia.org/wiki/List_of_department_stores_by_country
   - https://en.wikipedia.org/wiki/List_of_supermarket_chains
   - https://en.wikipedia.org/wiki/List_of_hypermarkets
   - https://en.wikipedia.org/wiki/List_of_online_marketplaces
5. Wikidata Query Service (CC0): instance of "retail chain" (Q507619) with at least 3 sitelinks, plus industry "e-commerce" (Q484847) with at least 4 sitelinks, each with an official website (P856). https://query.wikidata.org/ (`wikidata_retail.json`)

"Big" = on Wikipedia's List of largest retail companies, or a Wikidata item with 10+ Wikipedia sitelinks. Everything else from sources 4-5 is "other".

## Grouping and dedupe
- One retailer per Wikidata item; its official site(s) are its child sites (up to 8 per retailer). Multi-country sites like Pepco are one retailer with several children.
- Each host is used once overall (leading `www.` ignored). myshopify.com and support/help/blog/store/dtc subdomains are skipped.
- `pilot-crawl-2026-10-17.json` is the first crawl in the old per-site format, kept for reference and ignored by the weekly diff.

## Entries left out: not online shops
Some Wikipedia list entries resolve to Wikidata items that are not shops: towns, cities and regions (a hypermarket's location linked
from List_of_hypermarkets, for example), newspapers, a software licence, a web archive, an event, restaurants and cafés, and services
such as streaming, gyms, karaoke and arcades. They are listed with the reason in `config/non_shops.json` and left out of
`data/seeds.json`, the crawl and the site (`scripts/nonshops.py`). Their Wikidata classes are also skipped by `scripts/wiki_seeds.py`
when the Wikipedia seeds are refreshed.
