# Seed list sources (fetched 2026-10-17)
1. Wikidata Query Service (CC0): items that are an instance of "retail chain" (Q507619) with at least 3 Wikipedia sitelinks, plus items whose industry is "e-commerce" (Q484847) with at least 4 sitelinks, each with an official website (P856). Query in scripts/seeds.py notes and /data/seeds/wikidata_retail.json. https://query.wikidata.org/
2. GitHub ihof/shopify, shopify-sites.txt (a public list of Shopify sneaker/streetwear stores): https://github.com/ihof/shopify/blob/master/shopify-sites.txt
3. GitHub TeamDukaan/performance, "shopify stores - shopify.csv" (a public list of Shopify stores, mostly Indian D2C brands); first 300 unique domains only: https://github.com/TeamDukaan/performance/blob/master/shopify%20stores%20-%20shopify.csv
Duplicates removed by domain (ignoring a leading www.). Wikidata entries whose label is only a Q-number were dropped.
