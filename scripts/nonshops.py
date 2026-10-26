"""Entries that are not online shops (config/non_shops.json): places, newspapers, restaurants and cafés, services, other non-shops.
Used by seeds.py, crawl.py and build.py so they stay out of the store list, the crawl and the site; wiki_seeds.py skips their Wikidata classes."""
import json, os
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_C=json.load(open(os.path.join(ROOT,'config','non_shops.json'),encoding='utf-8'))
IDS=frozenset(_C['items'])      # Wikidata item IDs to leave out
CLASSES=frozenset(_C['classes'])  # Wikidata P31 classes to skip when refreshing Wikipedia seeds
