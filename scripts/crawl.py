"""Fetch each seed store's UCP business profile from /.well-known/ucp (UCP spec: https://ucp.dev/specification/overview/ ,
'Discovery: Fetch business profile from /.well-known/ucp'). Polite: honours robots.txt, one request at a time per host,
small global concurrency, timeouts, honest User-Agent. Writes data/crawl-YYYY-MM-DD.json and data/latest.json.
Usage: python3 scripts/crawl.py [--limit N]"""
import json, os, sys, collections, time, ssl, datetime, urllib.request, urllib.error, urllib.robotparser, concurrent.futures as cf, threading, re
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.path.join(ROOT,'data')
UA='AgenticShoppingIndexBot/0.1 (local research prototype; reads only /robots.txt and /.well-known/ucp)'
TIMEOUT=10; WORKERS=12; PAUSE=0.25; MAXBYTES=512*1024
CTX=ssl.create_default_context()
def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=TIMEOUT,context=CTX) as r:
            return r.status, r.headers.get('Content-Type',''), r.geturl(), r.read(MAXBYTES)
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get('Content-Type','') if e.headers else '', url, b''
    except Exception as e:
        return None, type(e).__name__+': '+str(e)[:120], url, b''
def robots_ok(base):
    st,ct,_,body=fetch(base+'/robots.txt')
    if st!=200 or not body: return True, st
    rp=urllib.robotparser.RobotFileParser(); rp.parse(body.decode('utf-8','ignore').splitlines())
    return rp.can_fetch(UA, base+'/.well-known/ucp'), st
def summarize(doc):
    u=doc.get('ucp',{}) if isinstance(doc,dict) else {}
    if not isinstance(u,dict) or not u: return None
    caps=sorted((u.get('capabilities') or {}).keys()) if isinstance(u.get('capabilities'),dict) else []
    svcs={}; transports=set(); platform=''
    for name,lst in (u.get('services') or {}).items():
        lst=lst if isinstance(lst,list) else [lst]
        for s in lst:
            if isinstance(s,dict):
                transports.add(s.get('transport','')); ep=s.get('endpoint','') or ''
                if 'myshopify.com' in ep or 'shopify' in ep: platform='Shopify'
        svcs[name]=len(lst)
    blob=json.dumps(u)
    if not platform and ('dev.shopify' in blob or 'myshopify.com' in blob): platform='Shopify'
    ph=u.get('payment_handlers') or {}
    handlers=sorted(ph.keys()) if isinstance(ph,dict) else []
    networks=set(); methods=set()
    for m in re.findall(r'"allowed_card_networks":\s*\[([^\]]*)\]',blob): networks|={x.strip(' "').upper() for x in m.split(',') if x.strip()}
    for m in re.findall(r'"enabled_card_brands":\s*\[([^\]]*)\]',blob): networks|={x.strip(' "').upper().replace('MASTER','MASTERCARD').replace('MASTERCARDCARD','MASTERCARD').replace('AMERICAN_EXPRESS','AMEX') for x in m.split(',') if x.strip()}
    for m in re.findall(r'"type":\s*"(CARD|card|PAYPAL|paypal|wallet|bank[^"]*)"',blob): methods.add(m.lower())
    return dict(version=u.get('version',''),supported_versions=sorted((u.get('supported_versions') or {}).keys()) if isinstance(u.get('supported_versions'),dict) else [],
                services=svcs,transports=sorted(t for t in transports if t),capabilities=caps,payment_handlers=handlers,
                card_networks=sorted(networks),payment_method_types=sorted(methods),platform_hint=platform,has_signing_keys=bool(doc.get('keys')) if isinstance(doc,dict) else False)
def crawl_one(seed):
    out=dict(domain=seed['domain'],fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'))
    hosts=[seed['domain']]
    alt=seed['domain'][4:] if seed['domain'].startswith('www.') else 'www.'+seed['domain']
    hosts.append(alt)
    for i,h in enumerate(hosts):
        base='https://'+h
        ok,rst=robots_ok(base); time.sleep(PAUSE)
        if rst is None and i==0:  # host unreachable: try alternate host
            out['note']='primary host unreachable'; continue
        if not ok:
            out.update(status='robots_disallow',host=h); return out
        st,ct,final,body=fetch(base+'/.well-known/ucp')
        out.update(host=h,http_status=st,content_type=ct if st else '',final_url=final)
        if st is None:
            out['status']='error'; out['error']=ct
            if i==0: continue
            return out
        if st==200 and body:
            try: doc=json.loads(body.decode('utf-8','ignore'))
            except Exception: out['status']='not_json'; return out
            s=summarize(doc)
            if s: out.update(status='ucp',ucp=s)
            else: out['status']='json_without_ucp'
            return out
        out['status']='blocked' if st in (401,403,429,451) else 'no_ucp'
        return out
    return out
def aggregate(seed,sites):
    """Retailer-level status: ucp if any site has a profile; no_ucp if at least one site answered without one;
    couldnt_check if every site refused, timed out or was disallowed by robots.txt."""
    st=[x.get('status') for x in sites]
    if 'ucp' in st: status='ucp'
    elif any(x in ('no_ucp','not_json','json_without_ucp') for x in st): status='no_ucp'
    else: status='couldnt_check'
    caps=sorted({c for x in sites if x.get('status')=='ucp' for c in x['ucp']['capabilities']})
    ph=sorted({c for x in sites if x.get('status')=='ucp' for c in x['ucp']['payment_handlers']})
    plat=sorted({x['ucp']['platform_hint'] or 'Other / not identified' for x in sites if x.get('status')=='ucp'})
    return dict(id=seed['id'],status=status,sites_checked=len(sites),sites_with_ucp=st.count('ucp'),capabilities=caps,payment_handlers=ph,platforms=plat)
def main():
    seeds=json.load(open(os.path.join(DATA,'seeds.json')))
    if '--limit' in sys.argv: seeds=seeds[:int(sys.argv[sys.argv.index('--limit')+1])]
    jobs=[dict(domain=h,rid=s['id']) for s in seeds for h in s['sites']]
    t0=time.time(); res=[]
    with cf.ThreadPoolExecutor(WORKERS) as ex:
        for i,r in enumerate(ex.map(crawl_one,jobs)):
            res.append(r)
            if i%250==0: print(i,'/',len(jobs),round(time.time()-t0),'s',flush=True)
    for j,r in zip(jobs,res): r['rid']=j['rid']
    by=collections.defaultdict(list)
    for r in res: by[r['rid']].append(r)
    retailers=[dict(aggregate(s,by[s['id']]),name=s['name'],segment=s['segment'],category=s['category'],country=s['country'],sources=s['sources']) for s in seeds]
    day=datetime.date.today().isoformat()
    doc=dict(crawl_date=day,user_agent=UA,spec='https://ucp.dev/specification/overview/',path='/.well-known/ucp',retailer_count=len(seeds),site_count=len(jobs),retailers=retailers,sites=res)
    for fn in (f'crawl-{day}.json','latest.json'): json.dump(doc,open(os.path.join(DATA,fn),'w'),indent=1,ensure_ascii=False)
    print('done',round(time.time()-t0),'s sites:',collections.Counter(r.get('status') for r in res),'retailers:',collections.Counter((r['segment'],r['status']) for r in retailers))
if __name__=='__main__': main()
