#!/usr/bin/env python3
"""Tell IndexNow search engines (Bing, Yandex, Seznam, Naver...) which URLs changed: every <loc> in dist/sitemap.xml.
Free, no account: the key file /<key>.txt (written by scripts/seo.py) proves we own the site.
Run after a deploy is live:  python3 scripts/indexnow.py   (--dry prints the payload only)"""
import os, re, sys, json, urllib.request
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from seo import INDEXNOW_KEY as KEY
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE=os.environ.get('SBI_SITE','https://shopbotindex.com').rstrip('/'); HOST=SITE.split('://',1)[1]
urls=re.findall(r'<loc>(.*?)</loc>',open(os.path.join(ROOT,'dist','sitemap.xml')).read())
body=json.dumps({'host':HOST,'key':KEY,'keyLocation':f'{SITE}/{KEY}.txt','urlList':urls[:10000]}).encode()
if '--dry' in sys.argv: print(len(urls),'urls', body[:300]); sys.exit()
req=urllib.request.Request('https://api.indexnow.org/indexnow',data=body,headers={'Content-Type':'application/json; charset=utf-8'})
try:
    r=urllib.request.urlopen(req,timeout=60); print('IndexNow',r.status,len(urls),'urls')
except urllib.error.HTTPError as e: print('IndexNow HTTP',e.code,e.read()[:300]); sys.exit(1)
