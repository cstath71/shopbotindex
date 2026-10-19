"""Record-only check of public agent discovery files on each crawled website (not shown anywhere on the site yet).
Files: /.well-known/poppy.json (Personal Agent Protocol draft 0.1, https://personalagentprotocol.org/docs/spec section 3),
/.well-known/agent-card.json (A2A agent card, https://a2a-protocol.org/latest/topics/agent-discovery/) and the pre-v0.3.0 path
/.well-known/agent.json, and /.well-known/ai-catalog.json (MCP SEP-2127 AI catalog; skipped when phase 2 of the crawl already
recorded it as sites[].signals.ai_catalog).
Results go to sites[].agent_files in the crawl JSON only. build.py doesn't read them.
Safety: it runs after the UCP pass, never edits any existing field, every exception is caught, and it stops at a time budget.
Politeness: the crawl's own User-Agent identity (product token, link, contact) with a comment that names these files, the crawl's
timeouts, pause and worker count, one request at a time per website, robots.txt honoured for every URL, and no further requests
to a website once it refuses us (401/403/429/451) or a connection fails.
Switch: on by default only when ENABLED_DEFAULT is True; env SBI_AGENT_FILES=1/0 overrides. Budget: SBI_AGENT_FILES_BUDGET seconds (default 1200).
Order: UCP sites first, then the rest in a week-dependent order, so a short budget reaches a different subset each week.
Requests per website: at most 5 (robots.txt only when the crawl didn't already hold it, the 3 agent files, and ai-catalog.json only when
phase 2 didn't already try it), so with phase 1 (at most 4) and phase 2 (at most 10) a website never gets more than 18 requests a week.
Standalone (only this check, on an existing crawl file, e.g. for sites that answered the UCP pass):
  python3 scripts/agent_files.py data/crawl-YYYY-MM-DD.json [--hosts FILE] [--budget SECONDS] [--out PATH] [--dry-run]
--hosts: one host or domain per line (# comments ok); default every site that answered the UCP pass. Results are written into
sites[].agent_files of that file (in place unless --out) plus a run summary in timing.agent_files; --dry-run lists the sites and exits."""
import json, os, time, ssl, zlib, datetime, urllib.request, urllib.error, urllib.robotparser, concurrent.futures as cf
ENABLED_DEFAULT=True  # on since 19 Oct 2026 (approved by Gus 18 Oct); SBI_AGENT_FILES=0 turns it off
ANSWERED=('ucp','no_ucp','not_json','json_without_ucp')
CTX=ssl.create_default_context()
OLD_COMMENT='reads only /robots.txt and /.well-known/ucp'
FILES_NOTE='/.well-known/poppy.json, /.well-known/agent-card.json, /.well-known/agent.json, /.well-known/ai-catalog.json'
def agent_ua(ua):
    """Same identity as the crawl, with a comment that honestly lists the extra files."""
    if 'poppy.json' in ua: return ua
    if OLD_COMMENT in ua: return ua.replace(OLD_COMMENT,'reads /robots.txt, /.well-known/ucp and the agent discovery files '+FILES_NOTE)
    return ua[:-1]+'; also reads '+FILES_NOTE+')' if ua.endswith(')') else ua+' (also reads '+FILES_NOTE+')'
def enabled():
    v=os.environ.get('SBI_AGENT_FILES')
    return ENABLED_DEFAULT if v is None else v.strip() not in ('0','','false','no')
def _fetch(url,ua,timeout,maxbytes,accept):
    req=urllib.request.Request(url,headers={'User-Agent':ua,'Accept':accept})
    try:
        with urllib.request.urlopen(req,timeout=timeout,context=CTX) as r:
            return r.status,r.headers.get('Content-Type',''),r.geturl(),r.read(maxbytes)
    except urllib.error.HTTPError as e:
        return e.code,(e.headers.get('Content-Type','') if e.headers else ''),url,b''
    except Exception as e:
        return None,type(e).__name__+': '+str(e)[:120],url,b''
def _json(body):
    if not body or body.lstrip()[:1] not in (b'{',b'[',b'\xef'): return None
    try: return json.loads(body.decode('utf-8-sig','ignore'))
    except Exception: return None
def v_poppy(d):
    if not (isinstance(d,dict) and isinstance(d.get('protocol_version'),str) and isinstance(d.get('organization'),dict)): return None
    return dict(protocol_version=d['protocol_version'][:16],organization_domain=str(d['organization'].get('domain',''))[:100],
                has_auth=isinstance(d.get('auth'),dict),has_company_agent=isinstance(d.get('agent'),dict),
                has_browser_session=isinstance(d.get('web'),dict),api_types=sorted({str(a.get('type',''))[:20] for a in d.get('apis') or [] if isinstance(a,dict)})[:5])
def v_card(d):
    if not (isinstance(d,dict) and isinstance(d.get('name'),str) and any(k in d for k in ('skills','supportedInterfaces','url','capabilities'))): return None
    sk=d.get('skills'); return dict(name=d['name'][:100],version=str(d.get('version',''))[:30],protocol_version=str(d.get('protocolVersion',''))[:16],skills=len(sk) if isinstance(sk,list) else 0)
def v_catalog(d):
    if not (isinstance(d,dict) and isinstance(d.get('entries'),list)): return None
    return dict(entries=len(d['entries']))
CHECKS=[('poppy','/.well-known/poppy.json',v_poppy),('a2a_card','/.well-known/agent-card.json',v_card),
        ('a2a_card_legacy','/.well-known/agent.json',v_card),('ai_catalog','/.well-known/ai-catalog.json',v_catalog)]
REFUSED=(401,403,429,451)
def probe(site,ua,timeout,pause,maxbytes,robots_cache,deadline):
    host=site['host']; base='https://'+host; out=dict(checked=True); n=0
    txt=robots_cache.get(base)
    if txt is None:
        st,ct,_,body=_fetch(base+'/robots.txt',ua,timeout,maxbytes,'text/plain'); n+=1; time.sleep(pause)
        if st is None or st in REFUSED: return dict(checked=False,reason='robots.txt: '+(str(st) if st else 'connection failed'),requests=n)
        txt=body.decode('utf-8','ignore') if st==200 and body else ''
    rp=urllib.robotparser.RobotFileParser(); rp.parse(txt.splitlines())
    stop=None
    for key,path,val in CHECKS:
        if key=='ai_catalog' and isinstance((site.get('signals') or {}).get('ai_catalog'),dict):
            out[key]=dict(recorded_in='signals.ai_catalog'); continue
        if key=='ai_catalog' and str((site.get('signals') or {}).get('reason','')).startswith('probe error'):
            out[key]=dict(status='not fetched',reason='phase 2 already tried it'); continue  # keeps the weekly per-site maximum
        if stop: out[key]=dict(status='not fetched',reason=stop); continue
        if time.time()>deadline: out[key]=dict(status='not fetched',reason='time budget reached'); continue
        if txt and not rp.can_fetch(ua,base+path): out[key]=dict(status='robots_disallow'); continue
        st,ct,final,body=_fetch(base+path,ua,timeout,maxbytes,'application/json'); n+=1; time.sleep(pause)
        if st is None: out[key]=dict(status='error',error=ct[:80]); stop='connection failed earlier'; continue
        rec=dict(status=st)
        if st==200:
            s=val(_json(body)); rec['valid']=bool(s)
            if s: rec['summary']=s
            if final.rstrip('/')!=(base+path).rstrip('/'): rec['final_url']=final[:200]
        elif st in REFUSED: stop=f'site refused ({st})'
        out[key]=rec
    out['requests']=n
    return out
def run(sites,ua,timeout=10,workers=12,pause=0.25,maxbytes=512*1024,robots_cache=None,budget=None):
    """Adds sites[i]['agent_files'] in place. Returns a summary dict (printed to the crawl log)."""
    t0=time.time()
    if not enabled():
        return dict(enabled=False)
    budget=int(os.environ.get('SBI_AGENT_FILES_BUDGET','1200')) if budget is None else budget
    deadline=t0+budget; ua=agent_ua(ua); cache=robots_cache or {}
    def one(s):
        if s.get('status') not in ANSWERED or not s.get('host'):
            s['agent_files']=dict(checked=False,reason='site did not answer the UCP pass ('+str(s.get('status'))+')'); return
        if time.time()>deadline: s['agent_files']=dict(checked=False,reason='time budget reached'); return
        try: s['agent_files']=probe(s,ua,timeout,pause,maxbytes,cache,deadline)
        except Exception as e: s['agent_files']=dict(checked=False,reason='check failed: '+type(e).__name__)
    wk=datetime.date.today().isocalendar()[1]
    order=sorted(sites,key=lambda s:(0 if s.get('status')=='ucp' else 1,(zlib.crc32(str(s.get('host') or s.get('domain')).encode())+wk*7919)%10007))
    with cf.ThreadPoolExecutor(workers) as ex: list(ex.map(one,order))
    af=[s.get('agent_files') or {} for s in sites]
    valid={k:sum(1 for a in af if (a.get(k) or {}).get('valid')) for k,_,_ in CHECKS}
    return dict(enabled=True,seconds=round(time.time()-t0),budget=budget,checked=sum(1 for a in af if a.get('checked')),
                requests=sum(a.get('requests',0) for a in af),valid=valid,
                not_checked_budget=sum(1 for a in af if a.get('reason')=='time budget reached'))
def _load_hosts(path):
    hs=set()
    with open(path,encoding='utf-8') as f: lines=f.read().splitlines()
    for line in lines:
        line=line.split('#',1)[0].strip().lower()
        if not line: continue
        line=line.split('://',1)[-1].split('/',1)[0]
        hs.add(line[4:] if line.startswith('www.') else line)
    return hs
def main(argv=None):
    """Run only the agent-files check on the sites of an existing crawl file and write the results back into it."""
    import sys
    argv=list(sys.argv[1:] if argv is None else argv)
    def opt(name,default=None):
        if name in argv: i=argv.index(name); v=argv[i+1]; del argv[i:i+2]; return v
        return default
    hosts=opt('--hosts'); out=opt('--out'); budget=opt('--budget'); dry='--dry-run' in argv
    if dry: argv.remove('--dry-run')
    if len(argv)!=1: print(__doc__); return 2
    src=argv[0]
    with open(src,encoding='utf-8') as f: raw=f.read()
    doc=json.loads(raw); fmt=dict(indent=1) if raw.startswith('{\n') else dict(separators=(',',':'))  # keep the file's own layout so git diffs stay small
    sites=[s for s in doc['sites'] if s.get('status') in ANSWERED and s.get('host')]
    if hosts:
        want=_load_hosts(hosts); norm=lambda h:(h or '').lower()[4:] if (h or '').lower().startswith('www.') else (h or '').lower()
        sites=[s for s in sites if norm(s.get('host')) in want or norm(s.get('domain')) in want]
    print('agent files:',len(sites),'sites selected from',src,'(enabled)' if enabled() else '(DISABLED: SBI_AGENT_FILES=0)',flush=True)
    if dry:
        for s in sites: print(s['host'])
        return 0
    here=os.path.dirname(os.path.abspath(__file__))
    import importlib.util as ilu
    sp=ilu.spec_from_file_location('sbi_crawl',os.path.join(here,'crawl.py')); cm=ilu.module_from_spec(sp); sp.loader.exec_module(cm)
    summ=run(sites,cm.UA,cm.TIMEOUT,cm.WORKERS,cm.PAUSE,cm.MAXBYTES,None,int(budget) if budget else None)
    summ['run_at']=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'); summ['sites_selected']=len(sites)
    print('agent files',summ,flush=True)
    if not summ.get('enabled'): return 1
    doc.setdefault('timing',{})['agent_files']=summ
    dst=out or src; tmp=dst+'.tmp'
    with open(tmp,'w',encoding='utf-8') as f: json.dump(doc,f,ensure_ascii=False,**fmt)
    os.replace(tmp,dst)
    print('wrote',dst,flush=True); return 0
if __name__=='__main__':
    raise SystemExit(main())
