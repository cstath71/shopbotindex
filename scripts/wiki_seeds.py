"""Fetch retailer candidates from Wikipedia list pages, resolve to Wikidata items (own websites, industry, country).
Writes data/seeds/wikipedia_lists.json. Usage: python3 scripts/wiki_seeds.py"""
import json, os, sys, time, urllib.request, urllib.parse
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); OUT=os.path.join(ROOT,'data','seeds','wikipedia_lists.json')
UA='ShopBotIndexBot/1.0 (+https://shopbotindex.com/methodology.html)'
PAGES=['List_of_largest_retail_companies','List_of_department_stores_by_country','List_of_supermarket_chains','List_of_hypermarkets','List_of_online_marketplaces']
EXCL={'Q5','Q6256','Q515','Q1549591','Q3624078','Q4167410','Q13406463','Q35657','Q7275','Q486972','Q1637706','Q2221906','Q11424','Q5119','Q82794','Q1093829'}
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from nonshops import CLASSES as NON_SHOP_CLASSES, IDS as NON_SHOPS  # places, newspapers, licences... (config/non_shops.json)
EXCL=EXCL|NON_SHOP_CLASSES
def get(url):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':UA}),timeout=60) as r: return json.load(r)
        except Exception as e: time.sleep(3); err=e
    raise err
titles={}
for p in PAGES:
    d=get(f'https://en.wikipedia.org/w/api.php?action=parse&page={p}&prop=links&format=json')
    for l in d['parse']['links']:
        if l.get('ns')==0 and l.get('exists') is not None: titles.setdefault(l['*'],p)
    time.sleep(1)
print('titles',len(titles))
T=list(titles); items={}
for i in range(0,len(T),50):
    batch=T[i:i+50]
    d=get('https://www.wikidata.org/w/api.php?'+urllib.parse.urlencode(dict(action='wbgetentities',sites='enwiki',titles='|'.join(batch),props='claims|sitelinks|labels',languages='en',format='json')))
    for q,e in d.get('entities',{}).items():
        if q.startswith('-') or 'claims' not in e: continue
        c=e['claims']
        def vals(pid,kind='id'):
            out=[]
            for s in c.get(pid,[]):
                v=s.get('mainsnak',{}).get('datavalue',{}).get('value')
                if v is None: continue
                out.append(v['id'] if isinstance(v,dict) and 'id' in v else v)
            return out
        p31=set(vals('P31'))
        if p31 & EXCL or q in NON_SHOPS: continue
        sites=vals('P856')
        if not sites: continue
        if vals('P576'): continue  # dissolved
        title=e.get('sitelinks',{}).get('enwiki',{}).get('title','')
        items[q]=dict(qid=q,name=e.get('labels',{}).get('en',{}).get('value',title),sites=sites,industry_q=vals('P452'),country_q=vals('P17'),
                      sitelinks=len(e.get('sitelinks',{})),list_page=titles.get(title,''))
    time.sleep(0.5)
# resolve labels for industry/country
qs=sorted({x for it in items.values() for x in it['industry_q']+it['country_q']}); lab={}
for i in range(0,len(qs),50):
    d=get('https://www.wikidata.org/w/api.php?'+urllib.parse.urlencode(dict(action='wbgetentities',ids='|'.join(qs[i:i+50]),props='labels',languages='en',format='json')))
    for q,e in d.get('entities',{}).items(): lab[q]=e.get('labels',{}).get('en',{}).get('value','')
    time.sleep(0.5)
for it in items.values():
    it['industry']=[lab.get(x,'') for x in it['industry_q']]; it['country']=[lab.get(x,'') for x in it['country_q']]
json.dump(dict(fetched=time.strftime('%Y-%m-%d'),pages=['https://en.wikipedia.org/wiki/'+p for p in PAGES],items=list(items.values())),open(OUT,'w'),indent=1,ensure_ascii=False)
print('items',len(items))
