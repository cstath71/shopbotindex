"""Build data/seeds.json from cited public sources (see data/seeds/SOURCES.md).
Usage: python3 scripts/seeds.py"""
import json, os, re, csv, urllib.parse
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); S=os.path.join(ROOT,'data','seeds')
TEAMDUKAAN_LIMIT=300  # first N unique rows of the TeamDukaan list (it has ~9.7k rows)
def host(u):
    u=u.strip()
    if not u: return None
    if not re.match(r'^https?://',u): u='https://'+u
    h=urllib.parse.urlparse(u).hostname
    if not h or '.' not in h: return None
    return h.lower().rstrip('.')
def root(h): return re.sub(r'^www\d?\.','',h)
def cat_from_industry(ind,name=''):
    i=(ind or '').lower()
    if any(k in i for k in ('cloth','fashion','textile','footwear','apparel','luxury')): return 'Fashion & apparel'
    if any(k in i for k in ('cosmetic','beauty','perfum')): return 'Beauty & personal care'
    if any(k in i for k in ('food','grocer','supermarket','beverage')): return 'Grocery & food'
    if any(k in i for k in ('electronic','computer','consumer electronics')): return 'Electronics'
    if any(k in i for k in ('paint','hardware','furniture','home','diy','construction')): return 'Home, furniture & DIY'
    if 'e-commerce' in i or 'online' in i: return 'Online retail & marketplaces'
    if 'retail' in i or 'discount' in i or 'mass-market' in i: return 'General retail'
    return 'Other / unclassified'
out={}
def add(h,**kw):
    if not h: return
    r=root(h)
    if r in out: return
    out[r]=dict(domain=h,**kw)
wd=json.load(open(os.path.join(S,'wikidata_retail.json')))['results']['bindings']
wd.sort(key=lambda x:-int(x['links']['value']))
for b in wd:
    nm=b['itemLabel']['value']
    if re.fullmatch(r'Q\d+',nm): continue
    add(host(b['site']['value']),name=nm,source='wikidata',source_ref=b['item']['value'],
        industry=b.get('industry',{}).get('value',''),category=cat_from_industry(b.get('industry',{}).get('value','')),
        country=b.get('country',{}).get('value',''))
for line in open(os.path.join(S,'ihof_shopify_sites.txt')):
    h=host(line)
    if h and not h.endswith('myshopify.com'): add(h,name=root(h),source='github:ihof/shopify',source_ref='https://github.com/ihof/shopify/blob/master/shopify-sites.txt',industry='',category='Sneakers & streetwear boutiques',country='')
n=0
with open(os.path.join(S,'teamdukaan_shopify.csv'),newline='',errors='ignore') as f:
    for row in csv.reader(f):
        if not row or row[0].strip().upper()=='URL': continue
        h=host(row[0])
        if not h or h.endswith('myshopify.com') or root(h).startswith(('support.','dtc.','store.')): continue
        if root(h) in out: continue
        add(h,name=root(h),source='github:TeamDukaan/performance',source_ref='https://github.com/TeamDukaan/performance/blob/master/shopify%20stores%20-%20shopify.csv',industry='',category='D2C brands (India)',country='India')
        n+=1
        if n>=TEAMDUKAAN_LIMIT: break
seeds=sorted(out.values(),key=lambda x:x['domain'])
json.dump(seeds,open(os.path.join(ROOT,'data','seeds.json'),'w'),indent=1,ensure_ascii=False)
import collections
print(len(seeds),collections.Counter(s['source'] for s in seeds),collections.Counter(s['category'] for s in seeds))
