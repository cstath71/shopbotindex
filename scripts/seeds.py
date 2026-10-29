"""Build data/seeds.json: one entry per retailer/store with its site(s), from cited public sources (data/seeds/SOURCES.md).
Segments (side by side, none primary):
  shopify : stores from public lists of Shopify stores
  big     : retailers on Wikipedia's 'List of largest retail companies' OR with Wikipedia articles in >=10 languages
  other   : other retail chains, department stores, supermarkets, hypermarkets and online marketplaces from Wikipedia/Wikidata
Multi-country sites of one retailer (several of its own websites on its Wikidata item) are kept as children of that retailer.
Usage: python3 scripts/seeds.py"""
import json, os, re, csv, urllib.parse, collections
from nonshops import IDS as NON_SHOPS  # places, newspapers, restaurants etc. (config/non_shops.json)
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); S=os.path.join(ROOT,'data','seeds')
TEAMDUKAAN_LIMIT=900; MAX_SITES=8; BIG_SITELINKS=10
def host(u):
    u=(u or '').strip()
    if not u: return None
    if not re.match(r'^https?://',u): u='https://'+u
    try: h=urllib.parse.urlparse(u).hostname
    except Exception: return None
    if not h or '.' not in h: return None
    return h.lower().rstrip('.')
def root(h): return re.sub(r'^www\d?\.','',h)
def category(inds,list_page=''):
    i=' '.join(inds).lower()+' '+list_page.lower()
    if any(k in i for k in ('cloth','fashion','textile','footwear','apparel','luxury')): return 'Fashion & apparel'
    if any(k in i for k in ('cosmetic','beauty','perfum','pharmac','drugstore')): return 'Beauty, health & pharmacy'
    if any(k in i for k in ('electronic','computer')): return 'Electronics'
    if any(k in i for k in ('furniture','hardware','diy','home improvement','paint','construction')): return 'Home, furniture & DIY'
    if any(k in i for k in ('supermarket','grocer','food','hypermarket','beverage')): return 'Grocery & hypermarkets'
    if 'department' in i: return 'Department stores'
    if any(k in i for k in ('e-commerce','online','marketplace','internet')): return 'Online retail & marketplaces'
    if any(k in i for k in ('retail','discount','mass-market','wholesale')): return 'General retail'
    return 'Other / unclassified'
R={}; seen_hosts={}
def add_sites(rid,hosts):
    for h in hosts:
        if not h or h.endswith('myshopify.com'): continue
        r=root(h)
        if r in seen_hosts: continue
        if len(R[rid]['sites'])>=MAX_SITES: break
        seen_hosts[r]=rid; R[rid]['sites'].append(h)
# 1) Wikipedia list pages resolved via Wikidata
W=json.load(open(os.path.join(S,'wikipedia_lists.json')))
for it in sorted(W['items'],key=lambda x:-x['sitelinks']):
    rid=it['qid']
    if rid in NON_SHOPS: continue
    big=it['list_page']=='List_of_largest_retail_companies' or it['sitelinks']>=BIG_SITELINKS
    R[rid]=dict(id=rid,name=it['name'],segment='big' if big else 'other',category=category(it['industry'],it['list_page']),
                country=', '.join(x for x in it['country'] if x)[:80],sitelinks=it['sitelinks'],
                sources=[f"wikipedia:{it['list_page']}",f"https://www.wikidata.org/wiki/{rid}"],sites=[])
    add_sites(rid,[host(s) for s in it['sites']])
# 2) Wikidata SPARQL (retail chains / e-commerce), grouped by item
grp=collections.defaultdict(list); meta={}
for b in json.load(open(os.path.join(S,'wikidata_retail.json')))['results']['bindings']:
    q=b['item']['value'].rsplit('/',1)[-1]; grp[q].append(b['site']['value']); meta[q]=b
for q,sites in grp.items():
    b=meta[q]; nm=b['itemLabel']['value']
    if q in NON_SHOPS: continue
    if re.fullmatch(r'Q\d+',nm): continue
    links=int(b['links']['value'])
    if q in R:
        add_sites(q,[host(s) for s in sites]); R[q]['sources'].append('wikidata:sparql'); continue
    R[q]=dict(id=q,name=nm,segment='big' if links>=BIG_SITELINKS else 'other',category=category([b.get('industry',{}).get('value','')]),
              country=b.get('country',{}).get('value',''),sitelinks=links,sources=['wikidata:sparql',f'https://www.wikidata.org/wiki/{q}'],sites=[])
    add_sites(q,[host(s) for s in sites])
# 3) Shopify store lists
def add_shop(h,src,cat,country=''):
    if not h or h.endswith('myshopify.com'): return False
    r=root(h)
    if r in seen_hosts or r.startswith(('support.','dtc.','store.','help.','blog.')): return False
    R[r]=dict(id=r,name=r,segment='shopify',category=cat,country=country,sitelinks=0,sources=[src],sites=[]); add_sites(r,[h]); return True
for line in open(os.path.join(S,'ihof_shopify_sites.txt')):
    add_shop(host(line),'https://github.com/ihof/shopify/blob/master/shopify-sites.txt','Sneakers & streetwear')
for line in open(os.path.join(S,'dipinarora_script_output.csv')):
    add_shop(host(line),'https://github.com/dipinarora9/Shopify-Domains-Scraper/blob/master/script_output.csv','Shopify stores (mixed, mostly Europe)')
n=0
with open(os.path.join(S,'teamdukaan_shopify.csv'),newline='',errors='ignore') as f:
    for row in csv.reader(f):
        if not row or row[0].strip().upper()=='URL': continue
        if add_shop(host(row[0]),'https://github.com/TeamDukaan/performance/blob/master/shopify%20stores%20-%20shopify.csv','D2C brands (India)','India'): n+=1
        if n>=TEAMDUKAAN_LIMIT: break
# 4) Additions with a start date (data/seeds/additions-YYYY-MM-DD.json): new stores tagged 'added'.
#    Same rules: one entry per retailer, each host used once overall, max 8 sites.
for fn in sorted(f for f in os.listdir(S) if re.fullmatch(r'additions-\d{4}-\d{2}-\d{2}\.json',f)):
    A=json.load(open(os.path.join(S,fn)))
    for it in A['stores']:
        if it['id'] in R: continue
        R[it['id']]=dict(id=it['id'],name=it['name'],segment=it['segment'],category=it['category'],country=it.get('country',''),
                         sitelinks=it.get('sitelinks',0),sources=list(it['sources']),sites=[],added=it.get('added',A['added']))
        add_sites(it['id'],[host(s) for s in it['sites']])
seeds=[r for r in R.values() if r['sites']]
json.dump(sorted(seeds,key=lambda x:(x['segment'],x['name'].lower())),open(os.path.join(ROOT,'data','seeds.json'),'w'),indent=1,ensure_ascii=False)
print('retailers',len(seeds),'sites',sum(len(s['sites']) for s in seeds),collections.Counter(s['segment'] for s in seeds),
      'multi-site',sum(1 for s in seeds if len(s['sites'])>1),'added',dict(collections.Counter(s['added'] for s in seeds if s.get('added'))))
