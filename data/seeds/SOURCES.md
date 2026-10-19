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

## Added on 2 Nov 2026 (`additions-2026-11-02.json`, 674 stores, tagged `added: 2026-11-02`)
Prepared 19 Oct 2026, frozen in the repo; `scripts/seeds.py` appends every `additions-YYYY-MM-DD.json` after the sources above with the same rules
(one entry per retailer, each host once overall, up to 8 sites, myshopify.com skipped). Each entry was new by registrable domain (Public Suffix List)
against the 2,276 stores above, and its home page answered our one-GET check on 19 Oct with shop markers. Per-entry citations are in `sources`.
- Shopify (142): GitHub TeamDukaan/performance `shopify stores - shopify.csv`, rows after the first 900 (139): https://github.com/TeamDukaan/performance/blob/master/shopify%20stores%20-%20shopify.csv ;
  GitHub gist alexfilatov, custom domains only (3): https://gist.github.com/alexfilatov/636dfa9d9a4b54eb0f13c21c21aa7597 . Kept only if the home page carried Shopify markup.
- Big (53) and other (479) retailers:
  - 68 more English Wikipedia list pages (national "List of supermarket chains in …" pages, List of convenience stores, List of bookstore chains,
    List of superstores, List of pharmacies, List of department stores of the United States and others), each link resolved to its Wikidata item;
    kept only with a retail type or industry on Wikidata. e.g. https://en.wikipedia.org/wiki/List_of_superstores
  - Wikidata Query Service (CC0): instance of online shop (Q4382945) or online marketplace (Q3390477); industry (P452) retail (Q126793),
    e-commerce (Q484847) or Q212930 with 2+ sitelinks; each with an official website (P856), not dissolved, not a person.
- Review (`additions-2026-11-02-review.json`): one Wikidata SPARQL query for the instance-of (P31) and industry (P452) values of the 579 Wikidata items
  (query.wikidata.org only, no store site contacted), plus a manual review of every name and domain. 51 of 725 dropped: 7 food service (restaurant,
  bakery, ice cream), 29 not retailers (software platforms, services, manufacturers, media, utilities), 11 holding/corporate sites or mall operators,
  4 Shopify-list entries that are apps, admin or government sites. Retail-chain subclass items from Wikidata (mostly restaurant/hotel chains) are not included.
