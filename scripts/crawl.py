"""Fetch each seed store's UCP business profile from /.well-known/ucp (UCP spec: https://ucp.dev/specification/overview/ ,
'Discovery: Fetch business profile from /.well-known/ucp'). Polite: honours robots.txt, one request at a time per host,
small global concurrency, timeouts, honest User-Agent. Writes data/crawl-YYYY-MM-DD.json and data/latest.json.
Phase 1 (unchanged headline metric): robots.txt + /.well-known/ucp for every site.
Phase 2 (agent-readiness signals, scripts/signals.py): runs after phase 1 within a time budget (env SBI_SIGNALS_BUDGET seconds,
default 3600); sites not reached in time are recorded as not checked. SBI_SIGNALS=0 skips phase 2 entirely.
Usage: python3 scripts/crawl.py [--limit N] [--every N] [--out DIR]   (--out writes crawl files to DIR instead of data/, for dry runs)"""
import json, os, sys, collections, time, ssl, datetime, urllib.request, urllib.error, urllib.robotparser, concurrent.futures as cf, threading, re
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.path.join(ROOT,'data')
UA=('ShopBotIndexBot/1.0 (+https://shopbotindex.com/methodology.html#crawler; hello@shopbotindex.com; reads /robots.txt, /.well-known/ucp, '
    '/.well-known/acp.json, /.well-known/ai-catalog.json, /llms.txt, /agents.md, the home page, up to 2 sitemap files and 1 product page, '
    'and sends one read-only MCP tools/list request to the endpoint a UCP profile declares)')
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import signals as SIG
SITE=os.environ.get('SBI_SITE','https://shopbotindex.com').rstrip('/')
AGENT_PROFILE=os.environ.get('SBI_AGENT_PROFILE',SITE+'/ucp/agent-profile.json')
ROBOTS_TXT={}
TIMEOUT=10; WORKERS=12; WORKERS2=16; PAUSE=0.25; MAXBYTES=512*1024  # WORKERS2: phase 2 (still one request at a time per site)
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
    ROBOTS_TXT[base]=body.decode('utf-8','ignore')
    rp=urllib.robotparser.RobotFileParser(); rp.parse(body.decode('utf-8','ignore').splitlines())
    return rp.can_fetch(UA, base+'/.well-known/ucp'), st
def summarize(doc):
    u=doc.get('ucp',{}) if isinstance(doc,dict) else {}
    if not isinstance(u,dict) or not u: return None
    caps=sorted((u.get('capabilities') or {}).keys()) if isinstance(u.get('capabilities'),dict) else []
    svcs={}; transports=set(); platform=''; mcp_eps=[]
    for name,lst in (u.get('services') or {}).items():
        lst=lst if isinstance(lst,list) else [lst]
        for s in lst:
            if isinstance(s,dict):
                transports.add(s.get('transport','')); ep=s.get('endpoint','') or ''
                if s.get('transport')=='mcp' and isinstance(ep,str) and ep.startswith('https://') and ep not in mcp_eps: mcp_eps.append(ep)
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
                card_networks=sorted(networks),payment_method_types=sorted(methods),platform_hint=platform,mcp_endpoints=mcp_eps[:3],has_signing_keys=bool(doc.get('keys')) if isinstance(doc,dict) else False)
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
    return dict(id=seed['id'],status=status,sites_checked=len(sites),sites_with_ucp=st.count('ucp'),capabilities=caps,payment_handlers=ph,platforms=plat,signals=SIG.rollup(sites))
def agent_profile():
    """Our own UCP agent profile (published by build.py); fall back to Shopify's documented example until ours is live."""
    st,ct,_,body=fetch(AGENT_PROFILE)
    try:
        if st==200 and 'json' in ct.lower() and isinstance(json.loads(body).get('ucp'),dict): return AGENT_PROFILE  # Shopify rejects non-JSON content types
    except Exception: pass
    return SIG.SHOPIFY_EXAMPLE_PROFILE
def phase2(res,budget):
    """Agent-readiness signals for every site that answered in phase 1. Primary sites (first site of each retailer) go first."""
    t0=time.time(); deadline=t0+budget; prof=agent_profile(); cache={}; lock=threading.Lock(); done=[0]
    order=sorted(range(len(res)),key=lambda i:(res[i].get('_rank',9),i))
    def one(i):
        r=res[i]
        if r.get('status') in (None,'error') or not r.get('host'): r['signals']=dict(checked=False,reason='site unreachable in phase 1'); return
        if r.get('status')=='robots_disallow': r['signals']=dict(checked=False,reason='robots.txt disallows ShopBotIndexBot'); return
        if time.time()>deadline: r['signals']=dict(checked=False,reason='time budget reached'); return
        try: r['signals']=SIG.probe_site(r['host'],ROBOTS_TXT.get('https://'+r['host'],''),(r.get('ucp') or {}).get('mcp_endpoints',[]),UA,prof,deadline,cache)
        except Exception as e: r['signals']=dict(checked=False,reason='probe error: '+type(e).__name__)
        with lock:
            done[0]+=1
            if done[0]%250==0: print('signals',done[0],'/',len(res),round(time.time()-t0),'s',flush=True)
    with cf.ThreadPoolExecutor(WORKERS2) as ex: list(ex.map(one,order))
    return dict(agent_profile=prof,seconds=round(time.time()-t0),budget=budget,requests=sum((r.get('signals') or {}).get('requests',0) for r in res),
                checked=sum(1 for r in res if (r.get('signals') or {}).get('checked')),not_checked_budget=sum(1 for r in res if (r.get('signals') or {}).get('reason')=='time budget reached'))
def main():
    seeds=json.load(open(os.path.join(DATA,'seeds.json')))
    if '--every' in sys.argv: seeds=seeds[::int(sys.argv[sys.argv.index('--every')+1])]
    if '--limit' in sys.argv: seeds=seeds[:int(sys.argv[sys.argv.index('--limit')+1])]
    out_dir=sys.argv[sys.argv.index('--out')+1] if '--out' in sys.argv else DATA
    jobs=[dict(domain=h,rid=s['id'],rank=k) for s in seeds for k,h in enumerate(s['sites'])]
    t0=time.time(); res=[]
    with cf.ThreadPoolExecutor(WORKERS) as ex:
        for i,r in enumerate(ex.map(crawl_one,jobs)):
            res.append(r)
            if i%250==0: print(i,'/',len(jobs),round(time.time()-t0),'s',flush=True)
    p1=round(time.time()-t0); print('phase 1 done',p1,'s',flush=True)
    for j,r in zip(jobs,res): r['rid']=j['rid']; r['_rank']=j['rank']
    p2=None
    if os.environ.get('SBI_SIGNALS','1')!='0':
        try: p2=phase2(res,int(os.environ.get('SBI_SIGNALS_BUDGET','3600')))
        except Exception as e:  # never let the extra signals break the weekly UCP crawl
            p2=dict(error=type(e).__name__+': '+str(e)[:200])
            for r in res: r.setdefault('signals',dict(checked=False,reason='signals pass failed'))
    for r in res: r.pop('_rank',None)
    print('phase 2',p2,flush=True)
    by=collections.defaultdict(list)
    for r in res: by[r['rid']].append(r)
    try:  # record-only agent discovery files (scripts/agent_files.py): adds sites[].agent_files, never changes UCP results
        sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import agent_files as AF
        print('agent files',AF.run(res,UA,TIMEOUT,WORKERS,PAUSE,MAXBYTES,globals().get('ROBOTS_TXT')),flush=True)
    except Exception as e: print('agent files pass skipped:',type(e).__name__,str(e)[:200],flush=True)
    retailers=[dict(aggregate(s,by[s['id']]),name=s['name'],segment=s['segment'],category=s['category'],country=s['country'],sources=s['sources']) for s in seeds]
    day=datetime.date.today().isoformat()
    doc=dict(crawl_date=day,user_agent=UA,spec='https://ucp.dev/specification/overview/',path='/.well-known/ucp',retailer_count=len(seeds),site_count=len(jobs),
             timing=dict(phase1_seconds=p1,phase2=p2),retailers=retailers,sites=res)
    os.makedirs(out_dir,exist_ok=True)
    for fn in (f'crawl-{day}.json','latest.json'): json.dump(doc,open(os.path.join(out_dir,fn),'w'),ensure_ascii=False,separators=(',',':'))
    print('done',round(time.time()-t0),'s sites:',collections.Counter(r.get('status') for r in res),'retailers:',collections.Counter((r['segment'],r['status']) for r in retailers))
if __name__=='__main__': main()
