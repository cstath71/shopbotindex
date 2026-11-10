#!/usr/bin/env python3
"""Tell IndexNow (Bing, Yandex, Seznam, Naver) which URLs changed.

The key file /<key>.txt, written by scripts/seo.py, proves we own the host.
Run after a deploy is live.

  python3 scripts/indexnow.py                     # every URL in dist/sitemap.xml
  python3 scripts/indexnow.py --since 2026-11-09  # lastmod on or after that day
  python3 scripts/indexnow.py --dry               # print the payload, do not POST
"""
import os, re, sys, json, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seo import INDEXNOW_KEY as KEY
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.environ.get('SBI_SITE', 'https://shopbotindex.com').rstrip('/')
HOST = SITE.split('://', 1)[1]
LOC = re.compile(r'<loc>(.*?)</loc>\s*<lastmod>(.*?)</lastmod>')

def sitemap_entries(xml):
    return LOC.findall(xml)

def choose_urls(entries, since=None):
    """URLs whose sitemap lastmod is on or after `since` (YYYY-MM-DD). No cutoff submits every URL."""
    out = []
    for loc, last in entries:
        if since and last < since:
            continue
        out.append(loc)
    return out

def _since_arg(argv):
    if '--since' not in argv:
        return None
    i = argv.index('--since')
    if i + 1 >= len(argv) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', argv[i + 1]):
        sys.exit('usage: indexnow.py [--since YYYY-MM-DD] [--dry]')
    return argv[i + 1]

def main(argv):
    since = _since_arg(argv)
    xml = open(os.path.join(ROOT, 'dist', 'sitemap.xml')).read()
    urls = choose_urls(sitemap_entries(xml), since)
    body = json.dumps({'host': HOST, 'key': KEY, 'keyLocation': f'{SITE}/{KEY}.txt', 'urlList': urls[:10000]}).encode()
    if '--dry' in argv:
        print(len(urls), 'urls', 'since', since or 'all')
        return 0
    if not urls:
        print('IndexNow 0 urls')
        return 0
    req = urllib.request.Request('https://api.indexnow.org/indexnow', data=body, headers={'Content-Type': 'application/json; charset=utf-8'})
    try:
        r = urllib.request.urlopen(req, timeout=60)
        print('IndexNow', r.status, len(urls), 'urls')
        return 0
    except urllib.error.HTTPError as e:
        print('IndexNow HTTP', e.code, e.read()[:300])
        return 1

if __name__ == '__main__':
    sys.exit(main(sys.argv))
