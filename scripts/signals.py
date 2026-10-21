"""Agent-readiness signals beyond UCP (phase 2 of scripts/crawl.py). Stdlib only.
Every fetch is checked against the site's robots.txt for ShopBotIndexBot first; one request at a time per site with a pause.
What phase 2 reads per website (and nothing else; the record-only agent discovery files are read by scripts/agent_files.py): /robots.txt (already fetched in phase 1), /.well-known/acp.json, /.well-known/ai-catalog.json,
/llms.txt, /agents.md, the home page, at most 2 sitemap files (only if the home page links no product), one product page, and, when the
site's UCP profile declares an MCP endpoint, one read-only JSON-RPC `tools/list` request to that endpoint."""
import json, re, time, gzip, ssl, urllib.request, urllib.error, urllib.parse, urllib.robotparser
TIMEOUT=12; PAUSE=1.0; MAXB=1536*1024; CTX=ssl.create_default_context()
# robots.txt tokens we report (from the docs of OpenAI, Anthropic, Perplexity and Google; see methodology)
TOKENS=['ChatGPT-User','Claude-User','Perplexity-User','Google-Agent','OAI-SearchBot','Claude-SearchBot','PerplexityBot','GPTBot','ClaudeBot','Google-Extended']
FAMILY={'user':['ChatGPT-User','Claude-User','Perplexity-User','Google-Agent'],'search':['OAI-SearchBot','Claude-SearchBot','PerplexityBot'],'training':['GPTBot','ClaudeBot','Google-Extended']}
SHOPIFY_EXAMPLE_PROFILE='https://shopify.dev/ucp/agent-profiles/examples/2026-08-25/valid-with-capabilities.json'

def fetch(url,ua,method='GET',data=None,accept='*/*',ctype=None,maxb=MAXB):
    h={'User-Agent':ua,'Accept':accept}
    if ctype: h['Content-Type']=ctype
    req=urllib.request.Request(url,data=data,headers=h,method=method)
    try:
        with urllib.request.urlopen(req,timeout=TIMEOUT,context=CTX) as r:
            return dict(status=r.status,headers={k.lower():v for k,v in r.headers.items()},cookies=r.headers.get_all('Set-Cookie') or [],url=r.geturl(),body=r.read(maxb))
    except urllib.error.HTTPError as e:
        b=b''
        try: b=e.read(64*1024)
        except Exception: pass
        hd={k.lower():v for k,v in (e.headers.items() if e.headers else [])}
        return dict(status=e.code,headers=hd,cookies=(e.headers.get_all('Set-Cookie') if e.headers else None) or [],url=url,body=b)
    except Exception as e:
        return dict(status=None,error=type(e).__name__,headers={},cookies=[],url=url,body=b'')

# ---------- robots.txt ----------
def _groups(txt):
    groups=[];cur=None;last_ua=False;signals=[]
    for line in txt.splitlines():
        line=line.split('#',1)[0].strip()
        if not line or ':' not in line: continue
        k,v=[x.strip() for x in line.split(':',1)]; k=k.lower()
        if k=='content-signal':
            if v: signals.append(v[:200])
            continue
        if k=='user-agent':
            if not last_ua: cur={'agents':[],'rules':[]}; groups.append(cur)
            cur['agents'].append(v.lower()); last_ua=True
        else:
            last_ua=False
            if cur is not None and k in('allow','disallow'): cur['rules'].append((k,v))
    return groups,signals
def _state(rules):
    dis=[v for k,v in rules if k=='disallow' and v]; al=[v for k,v in rules if k=='allow' and v]
    if '/' in dis and not al: return 'blocked'
    if '/' in dis: return 'mostly_blocked'
    if dis: return 'restricted'
    return 'allowed'
def robots_policy(txt):
    """Stated robots.txt policy for each AI-agent token. Only groups that name the token count as AI-specific;
    the '*' group is reported separately (it applies to every crawler, including AI agents without their own group)."""
    if not txt or '<html' in txt[:800].lower(): return dict(present=False)
    groups,signals=_groups(txt)
    specific={}
    for t in TOKENS:
        g=[x for x in groups if t.lower() in x['agents']]
        if g: specific[t]=_state([r for x in g for r in x['rules']])
    star=[x for x in groups if '*' in x['agents']]
    return dict(present=True,specific=specific,wildcard=_state([r for x in star for r in x['rules']]) if star else 'none',content_signal=signals[:3])

# ---------- page helpers ----------
VENDOR_RULES=[('cloudflare',lambda h,c:'cf-ray' in h or h.get('server','').lower()=='cloudflare'),
 ('akamai',lambda h,c:'akamai' in h.get('server','').lower() or '_abck' in c or 'bm_sz' in c or 'ak_bmsc' in c),
 ('datadome',lambda h,c:'x-datadome' in h or 'datadome=' in c),('human',lambda h,c:'_px' in c),('imperva',lambda h,c:'incap_ses' in c or 'x-iinfo' in h)]
def vendors(r):
    h=r['headers']; c=' '.join(r['cookies']).lower()
    return [n for n,f in VENDOR_RULES if f(h,c)]
PRODUCT_RE=re.compile(r'href=["\']((?:https?://[^"\'\s]+)?/(?:[a-z]{2}(?:[-_][a-z]{2})?/)*(?:products?|p|dp|ip|itm|listing|pd)/[^"\'\s#?<>]{3,})["\']',re.I)
SKIP_RE=re.compile(r'\.(js|css|png|jpe?g|gif|svg|webp|json|xml|pdf)$|/(collections?|cart|account|search)(/|$)|/index\.html?$|/(products?|p)/?$',re.I)
def host_of(u): return urllib.parse.urlparse(u).netloc.lower()
def same_site(a,b):
    a=a[4:] if a.startswith('www.') else a; b=b[4:] if b.startswith('www.') else b
    return a==b
def product_markup(html):
    """Return 'full' (Product + Offer with price, currency and availability), 'partial' (Product markup without all three) or 'none'."""
    prods=[]
    for m in re.finditer(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>',html,re.S|re.I):
        try: d=json.loads(m.group(1).strip())
        except Exception: continue
        st=[d]
        while st:
            x=st.pop()
            if isinstance(x,list): st.extend(x); continue
            if not isinstance(x,dict): continue
            t=x.get('@type'); ts=t if isinstance(t,list) else [t]
            if any(tt in ('Product','ProductGroup') for tt in ts): prods.append(x)
            st.extend(v for v in x.values() if isinstance(v,(dict,list)))
    if prods:
        def offers(p):
            out=[];st=[p]
            while st:
                x=st.pop()
                if isinstance(x,list): st.extend(x); continue
                if not isinstance(x,dict): continue
                t=x.get('@type'); ts=t if isinstance(t,list) else [t]
                if any(tt in ('Offer','AggregateOffer') for tt in ts): out.append(x)
                st.extend(v for k,v in x.items() if isinstance(v,(dict,list)))
            return out
        for p in prods:
            for o in offers(p):
                ps=o.get('priceSpecification'); ps=ps[0] if isinstance(ps,list) and ps else ps
                price=o.get('price') not in (None,'') or o.get('lowPrice') not in (None,'') or (isinstance(ps,dict) and ps.get('price') not in (None,''))
                cur=bool(o.get('priceCurrency') or (isinstance(ps,dict) and ps.get('priceCurrency')))
                if price and cur and o.get('availability'): return 'full'
        return 'partial'
    if re.search(r'itemtype=["\']https?://schema\.org/Product["\']',html,re.I):
        ok=all(re.search(r'itemprop=["\']%s["\']'%p,html,re.I) for p in ('price','priceCurrency','availability'))
        return 'full' if ok else 'partial'
    return 'none'
def _text_ok(b):
    t=b.decode('utf-8','ignore').lstrip('\ufeff \r\n\t'); return t.startswith('#') and '<html' not in t[:1000].lower()
def _json_ok(key):
    def f(b):
        try: d=json.loads(b.decode('utf-8','ignore').lstrip('\ufeff'))
        except Exception: return False
        return bool(key(d))
    return f
def _parse_jsonrpc(body):
    t=body.decode('utf-8','ignore').strip()
    if t.startswith('{'):
        try: return json.loads(t)
        except Exception: return None
    for line in t.splitlines():  # streamable HTTP may answer as SSE
        if line.startswith('data:'):
            try: return json.loads(line[5:].strip())
            except Exception: pass
    return None

# ---------- per-site probe ----------
def probe_site(host,robots_txt,mcp_endpoints,ua,agent_profile,deadline,robots_cache):
    base='https://'+host; out=dict(checked=True); n=[0]
    rp=urllib.robotparser.RobotFileParser(); pol=robots_policy(robots_txt)
    rp.parse(robots_txt.splitlines() if pol.get('present') else [])
    ok=lambda url: rp.can_fetch(ua,url) if pol.get('present') else True
    def get(url,**kw):
        if n[0]: time.sleep(PAUSE)
        n[0]+=1; return fetch(url,ua,**kw)
    out['robots']=pol
    def wk(path,validate,accept):
        if time.time()>deadline: return dict(state='not_checked')
        if not ok(base+path): return dict(state='robots_disallow')
        r=get(base+path,accept=accept)
        if r['status'] is None: return dict(state='error',http=None)
        if r['status']==200: return dict(state='found' if validate(r['body']) else 'not_found',http=200)
        if r['status'] in (404,410): return dict(state='not_found',http=r['status'])
        return dict(state='refused' if r['status'] in (401,403,429,503) else 'error',http=r['status'])
    out['acp']=wk('/.well-known/acp.json',_json_ok(lambda d:isinstance(d,dict) and isinstance(d.get('protocol'),dict) and d['protocol'].get('name')=='acp'),'application/json')
    out['ai_catalog']=wk('/.well-known/ai-catalog.json',_json_ok(lambda d:isinstance(d,dict) and isinstance(d.get('entries'),list)),'application/ai-catalog+json, application/json')
    out['llms_txt']=wk('/llms.txt',_text_ok,'text/plain, text/markdown')
    out['agents_md']=wk('/agents.md',_text_ok,'text/markdown, text/plain')
    # home page
    html=''; fh=host
    if time.time()>deadline: out['home']=dict(state='not_checked')
    elif not ok(base+'/'): out['home']=dict(state='robots_disallow')
    else:
        r=get(base+'/',accept='text/html')
        st=r['status']; html=r['body'].decode('utf-8','ignore') if st==200 else ''; fh=host_of(r['url']) or host
        chal=r['headers'].get('cf-mitigated')=='challenge'
        out['home']=dict(state='answered' if st and 200<=st<300 else 'refused' if st in (401,403,429,503) or chal else 'error' if st is None else 'other',http=st,challenge=chal,vendors=vendors(r))
    # product page: a link on the home page, else at most 2 sitemap files
    cand=None; src=None
    for m in PRODUCT_RE.finditer(html):
        u=urllib.parse.urljoin('https://'+fh+'/',m.group(1).replace('&amp;','&'))
        if same_site(host_of(u),fh) and not SKIP_RE.search(urllib.parse.urlparse(u).path): cand=u; src='home'; break
    if not cand and html and time.time()<deadline:
        sms=re.findall(r'(?im)^\s*sitemap:\s*(\S+)',robots_txt or '') or ['https://'+fh+'/sitemap.xml']
        sms=[s for s in sms if same_site(host_of(s),fh)][:1]; tries=0
        while sms and tries<2 and not cand and time.time()<deadline:
            sm=sms.pop(0)
            if not ok(sm): break
            r=get(sm,accept='application/xml'); tries+=1; b=r['body']
            if b[:2]==b'\x1f\x8b':
                try: b=gzip.decompress(b)
                except Exception: b=b''
            b=b.decode('utf-8','ignore'); locs=[l.replace('&amp;','&') for l in re.findall(r'<loc>\s*([^<\s]+)\s*</loc>',b)]
            if '<sitemapindex' in b:
                kids=[l for l in locs if same_site(host_of(l),fh) and re.search(r'product',l,re.I)]
                sms=kids[:1]; continue
            for l in locs:
                if same_site(host_of(l),fh) and re.search(r'/(products?|p|dp|ip|itm|listing|pd)/',l,re.I) and not SKIP_RE.search(urllib.parse.urlparse(l).path): cand=l; src='sitemap'; break
    if cand and time.time()<deadline:
        if not ok(cand): out['product']=dict(state='robots_disallow')
        else:
            r=get(cand,accept='text/html')
            out['product']=dict(state=product_markup(r['body'].decode('utf-8','ignore')) if r['status']==200 else 'not_checked',http=r['status'],url=cand,source=src)
    else: out['product']=dict(state='not_checked',reason='no product page found' if html else 'home page not available')
    # MCP tools/list on the endpoint the UCP profile declares (read-only; never calls a tool)
    if mcp_endpoints and time.time()<deadline:
        ep=mcp_endpoints[0]; eh=host_of(ep)
        if not ep.startswith('https://'): out['mcp']=dict(state='not_checked',endpoint=ep)
        else:
            if eh==host: allowed=ok(ep)
            else:
                if eh not in robots_cache:
                    rr=get('https://'+eh+'/robots.txt',accept='text/plain'); robots_cache[eh]=rr['body'].decode('utf-8','ignore') if rr['status']==200 else ''
                rp2=urllib.robotparser.RobotFileParser(); t2=robots_cache[eh]
                rp2.parse(t2.splitlines() if t2 and '<html' not in t2[:800].lower() else []); allowed=rp2.can_fetch(ua,ep)
            if not allowed: out['mcp']=dict(state='robots_disallow',endpoint=ep)
            else:
                body=json.dumps({'jsonrpc':'2.0','id':1,'method':'tools/list','params':{'arguments':{'meta':{'ucp-agent':{'profile':agent_profile}}}}}).encode()
                r=get(ep,method='POST',data=body,accept='application/json, text/event-stream',ctype='application/json')
                j=_parse_jsonrpc(r['body']) if r['status']==200 else None
                tools=[t.get('name') for t in ((j or {}).get('result') or {}).get('tools',[]) if isinstance(t,dict) and t.get('name')]
                out['mcp']=dict(state='answered' if tools else 'no_tools',http=r['status'],endpoint=ep,tools=sorted(tools))
    elif mcp_endpoints: out['mcp']=dict(state='not_checked',endpoint=mcp_endpoints[0])
    else: out['mcp']=dict(state='none_declared')
    out['requests']=n[0]
    return out

# ---------- retailer roll-up ----------
PRANK={'full':3,'partial':2,'none':1,'robots_disallow':0,'not_checked':0}
def rollup(sites):
    chk=[s for s in sites if (s.get('signals') or {}).get('checked')]
    if not chk: return dict(checked=False)
    sg=[s['signals'] for s in chk]
    mcps=[x['mcp'] for x in sg if x['mcp'].get('state')=='answered']
    best_mcp=max(mcps,key=lambda m:len(m['tools'])) if mcps else None
    mstate='answered' if best_mcp else ('no_tools' if any(x['mcp'].get('state')=='no_tools' for x in sg) else 'not_checked' if any(x['mcp'].get('state') in('not_checked','robots_disallow') for x in sg) else 'none_declared')
    rob=next((x['robots'] for x in sg if x['robots'].get('present')),dict(present=False))
    prod=max((x['product'] for x in sg),key=lambda p:PRANK.get(p.get('state'),0))
    homes=[x['home'] for x in sg]
    access='answered' if any(h.get('state')=='answered' for h in homes) else 'refused' if any(h.get('state')=='refused' for h in homes) else 'not_checked'
    return dict(checked=True,
        acp=any(x['acp'].get('state')=='found' for x in sg),ai_catalog=any(x['ai_catalog'].get('state')=='found' for x in sg),
        mcp=dict(state=mstate,tools=best_mcp['tools'] if best_mcp else []),
        robots=dict(present=rob.get('present',False),specific=rob.get('specific',{}),wildcard=rob.get('wildcard','none'),content_signal=rob.get('content_signal',[])),
        llms_txt=any(x['llms_txt'].get('state')=='found' for x in sg),agents_md=any(x['agents_md'].get('state')=='found' for x in sg),
        guide_state='found' if any(x[k].get('state')=='found' for x in sg for k in ('llms_txt','agents_md')) else 'not_found' if any(x[k].get('state')=='not_found' for x in sg for k in ('llms_txt','agents_md')) else 'not_checked',
        product=dict(state=prod.get('state','not_checked'),url=prod.get('url')),
        access=dict(state=access,challenge=any(h.get('challenge') for h in homes),vendors=sorted({v for h in homes for v in h.get('vendors',[])})))
