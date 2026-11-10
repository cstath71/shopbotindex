"""Store-level answers for every agent-readiness signal the crawl records.

A store is in a share only when at least one of its websites gave a definitive
answer for that signal (found or not found). Refused, error and not reached
are left out: a refusal is not "no". A store counts once even when several
country sites were checked. Callers pass retailers and sites already filtered
with the non-shop exclusion build.py uses.

The sentences are the visible answer paragraphs. build.py prints them into
HTML; scripts/seo.py copies the same strings into FAQPage and Dataset JSON-LD.
"""
import html as _html
from collections import Counter, defaultdict

REFUSED_HTTP={401,403,429,451,503}
NOT_FOUND_HTTP={404,410}
FILE_ORDER=('found','not_found','refused','error','robots_disallow','not_checked','missing')
MCP_ORDER=('found','not_found','refused','error','robots_disallow','not_checked','none_declared','missing')
PROD_ORDER=('full','partial','none','robots_disallow','not_checked','missing')
AF_ORDER=('found','not_found','refused','error','robots_disallow','not_checked','missing')
# A store "names an endpoint" when the tools request was sent: answered, no tools, refused, or another HTTP status.
# robots.txt disallow and not reached stay out of that share, matching the site's mcp_declared flag (rollup state answered or no_tools).
ENDPOINT_NAMED=('found','not_found','refused','error')
VENDORS=(('cloudflare','Cloudflare'),('akamai','Akamai'),('datadome','DataDome'),('human','HUMAN'),('imperva','Imperva'))
CAVEAT=('A published file or profile is a declaration, not proof that agents can buy. '
        'ShopBot Index does not test purchases.')
ACCESS_NOTE='A refusal of our crawler says nothing about whether shoppers or AI agents can use the site.'

def E(s): return _html.escape(str(s if s is not None else ''), quote=True)
def comma(n): return f'{n:,}'
def share(found, checked):
    return f'{(100*found/checked):.1f}%' if checked else 'n/a'
def figure(date, found, checked, verb, verb_one=None):
    if not checked:
        return f'In the ShopBot Index crawl of {date}, we could not check any store, so there is no share for this signal.'
    word=verb_one if found==1 and verb_one else verb
    return (f'In the ShopBot Index crawl of {date}, {comma(found)} of {comma(checked)} stores we could check {word} ({share(found, checked)}).')
def _best(states, order):
    have=set(states)
    for s in order:
        if s in have: return s
    return order[-1]
def _nv(n, singular, plural):
    if n==0: return f'0 {plural}'
    if n==1: return f'1 {singular}'
    return f'{comma(n)} {plural}'
def human_join(xs):
    if not xs: return ''
    if len(xs)==1: return xs[0]
    if len(xs)==2: return xs[0]+' and '+xs[1]
    return ', '.join(xs[:-1])+' and '+xs[-1]
ROBOT_RANK={'blocked':4,'mostly_blocked':3,'restricted':2,'allowed':1}
WHOLE_SITE={'blocked','mostly_blocked'}
BOT_PHRASE={'blocked':'asks it to stay out of the whole site','mostly_blocked':'disallows the whole site except some paths'}
TOKEN_ORDER=('GPTBot','ChatGPT-User','OAI-SearchBot','ClaudeBot','Claude-User','Claude-SearchBot','PerplexityBot','Perplexity-User','Google-Extended','Google-Agent')
def _robots_bots(sig_sites):
    """Most restrictive recorded state for each named AI crawler, across the store's websites."""
    spec={}
    for s in sig_sites:
        rb=(s.get('signals') or {}).get('robots')
        if not isinstance(rb, dict) or not rb.get('present'): continue
        sp=rb.get('specific') or {}
        if not isinstance(sp, dict): continue
        for t,st in sp.items():
            if t not in spec or ROBOT_RANK.get(st,0)>ROBOT_RANK.get(spec[t],0):
                spec[t]=st
    return spec
def _mcp_answered(sig_sites):
    """Endpoints that returned a tools list, in the order the crawl recorded them."""
    out=[]; seen=set()
    for s in sig_sites:
        m=(s.get('signals') or {}).get('mcp')
        if not isinstance(m, dict) or m.get('state')!='answered': continue
        ep=m.get('endpoint') or ''
        if not ep or ep in seen: continue
        seen.add(ep)
        tools=m.get('tools') or []
        out.append((ep, list(tools) if isinstance(tools, list) else []))
    return out

def _file_state(sig, key):
    v=sig.get(key)
    st=v.get('state') if isinstance(v, dict) else None
    return st if st in FILE_ORDER else 'missing'
def _mcp_state(sig):
    m=sig.get('mcp') if isinstance(sig.get('mcp'), dict) else {}
    st=m.get('state'); http=m.get('http')
    if st=='answered': return 'found'
    if st=='none_declared': return 'none_declared'
    if st=='robots_disallow': return 'robots_disallow'
    if st=='not_checked': return 'not_checked'
    if st=='no_tools':
        if http in (200,)+tuple(NOT_FOUND_HTTP): return 'not_found'
        if http in REFUSED_HTTP: return 'refused'
        return 'error'
    return 'missing'
def _product_state(sig):
    p=sig.get('product') if isinstance(sig.get('product'), dict) else {}
    st=p.get('state')
    return st if st in PROD_ORDER else 'missing'
def _af_state(rec):
    if not isinstance(rec, dict): return 'missing'
    if rec.get('recorded_in'): return 'recorded_elsewhere'
    st=rec.get('status')
    if st=='robots_disallow': return 'robots_disallow'
    if st=='not fetched':
        reason=(rec.get('reason') or '').lower()
        if 'refused' in reason: return 'refused'
        if 'connection' in reason or 'failed' in reason: return 'error'
        return 'not_checked'
    if st=='error' or st is None: return 'error'
    if st==200 and rec.get('valid'): return 'found'
    if st==200 or st in NOT_FOUND_HTTP: return 'not_found'
    if st in REFUSED_HTTP: return 'refused'
    if isinstance(st, int): return 'error'
    return 'error'
def _af_bucket(af_sites, keys):
    states=[]
    for s in af_sites:
        af=s.get('agent_files') or {}
        xs=[x for x in (_af_state(af.get(k)) for k in keys) if x!='recorded_elsewhere']
        if not xs: states.append('missing'); continue
        if 'found' in xs: states.append('found')
        elif all(x=='not_found' for x in xs): states.append('not_found')
        else:
            hit=next((k for k in ('refused','error','robots_disallow','not_checked','missing') if k in xs), 'missing')
            states.append(hit)
    if not states: return 'missing'
    return _best(states, AF_ORDER)

def store_facts(retailer, sig_sites, af_sites):
    """One bucket per signal for this store. 'missing' means we could not check it."""
    def files(key):
        if not sig_sites: return 'missing'
        return _best([_file_state(s.get('signals') or {}, key) for s in sig_sites], FILE_ORDER)
    readable=ai=content=wild=False
    for s in sig_sites:
        rb=(s.get('signals') or {}).get('robots')
        if not isinstance(rb, dict) or 'present' not in rb or not rb.get('present'): continue
        readable=True
        if rb.get('specific'): ai=True
        if rb.get('content_signal'): content=True
        if rb.get('wildcard') in ('blocked','mostly_blocked'): wild=True
    homes=[]; challenge=False; vendors=set()
    for s in sig_sites:
        h=(s.get('signals') or {}).get('home')
        if not isinstance(h, dict): continue
        if h.get('state'): homes.append(h.get('state'))
        if h.get('challenge'): challenge=True
        for v in h.get('vendors') or []: vendors.add(v)
    if 'answered' in homes: access='answered'
    elif 'refused' in homes: access='refused'
    else: access,challenge,vendors='out',False,set()
    mcp_state, mcp_http=_mcp_state_store(sig_sites)
    return dict(
        acp=files('acp'), ai_catalog=files('ai_catalog'), llms_txt=files('llms_txt'), agents_md=files('agents_md'),
        mcp=mcp_state, mcp_http=mcp_http, product=_product_store(sig_sites),
        robots_readable=readable, robots_ai=ai, robots_content=content, robots_wild=wild,
        access=access, challenge=bool(challenge) if access=='refused' else False, vendors=vendors if access in ('answered','refused') else set(),
        poppy=_af_bucket(af_sites, ('poppy',)), a2a=_af_bucket(af_sites, ('a2a_card','a2a_card_legacy')),
        robots_bots=_robots_bots(sig_sites), mcp_endpoints=_mcp_answered(sig_sites))
def _mcp_state_store(sig_sites):
    if not sig_sites: return 'missing', None
    pairs=[]
    for s in sig_sites:
        sig=s.get('signals') or {}
        m=sig.get('mcp') if isinstance(sig.get('mcp'), dict) else {}
        pairs.append((_mcp_state(sig), m.get('http')))
    best=_best([p[0] for p in pairs], MCP_ORDER)
    return best, next((h for k,h in pairs if k==best), None)
def _product_store(sig_sites):
    if not sig_sites: return 'missing'
    return _best([_product_state(s.get('signals') or {}) for s in sig_sites], PROD_ORDER)

def _rows(retailers, sites):
    by=defaultdict(list); af=defaultdict(list)
    for s in sites:
        if (s.get('signals') or {}).get('checked'): by[s.get('rid')].append(s)
        if (s.get('agent_files') or {}).get('checked'): af[s.get('rid')].append(s)
    return [(r, store_facts(r, by.get(r['id'], []), af.get(r['id'], []))) for r in retailers]

def _platform_name(r):
    if r.get('status')!='ucp': return None
    ps=[p for p in (r.get('platforms') or []) if p]
    return ' / '.join(ps) if ps else 'Not identified'

def tally(rows, bucket_of, hit_values, denom_values, segs):
    hits=[]; buckets=Counter(); seg={k:Counter() for k in segs}
    plat=defaultdict(Counter); unknown=0
    for r,f in rows:
        b=bucket_of(f); buckets[b]+=1; sk=r.get('segment') or 'other'
        if sk not in seg: seg[sk]=Counter()
        if b in denom_values:
            seg[sk]['checked']+=1
            if b in hit_values:
                seg[sk]['found']+=1; hits.append(r)
            name=_platform_name(r)
            if name is None: unknown+=1
            else:
                plat[name]['checked']+=1
                if b in hit_values: plat[name]['found']+=1
        else:
            seg[sk]['couldnt']+=1
    hits.sort(key=lambda r: (0 if r.get('segment')=='big' else 1, (r.get('name') or '').lower(), r.get('id') or ''))
    found=sum(seg[k]['found'] for k in seg); checked=sum(seg[k]['checked'] for k in seg)
    couldnt=sum(seg[k]['couldnt'] for k in seg)
    return dict(hits=hits, buckets=buckets, seg=seg, plat=plat, unknown=unknown,
                found=found, checked=checked, couldnt=couldnt, share=share(found, checked))

def _big_sentence(hits, store_prefix, slug_for_id):
    big=[r for r in hits if r.get('segment')=='big']
    if not big: return 'No big retailer met this check in this crawl.'
    links=[]
    for r in big:
        slug=slug_for_id(r['id']) if slug_for_id else None
        name=E(r.get('name') or r['id'])
        if slug: links.append(f'<a href="{store_prefix}store/{E(slug)}.html">{name}</a>')
        else: links.append(name)
    return f'Big retailers first ({comma(len(big))}): {human_join(links)}.'
def _examples(hits, store_prefix, slug_for_id, eid):
    if not hits:
        return f'<div id="{eid}"><p>No tracked store met this check in this crawl.</p></div>'
    items=[]
    for r in hits:
        slug=slug_for_id(r['id']) if slug_for_id else None
        name=E(r.get('name') or r['id'])
        if slug: items.append(f'<li><a href="{store_prefix}store/{E(slug)}.html">{name}</a></li>')
        else: items.append(f'<li>{name}</li>')
    return f'<div id="{eid}"><ul class="cols">{"".join(items)}</ul></div>'
def _seg_table(t, labels, segs):
    rows=[]
    for k in list(segs)+[k for k in t['seg'] if k not in segs]:
        s=t['seg'].get(k) or Counter()
        rows.append(f'<tr data-seg="{E(k)}"><td>{E(labels.get(k,k))}</td><td>{comma(s["found"])}</td><td>{comma(s["checked"])}</td>'
                    f'<td>{share(s["found"], s["checked"])}</td><td>{comma(s["couldnt"])}</td></tr>')
    return ('<div class="tw nomax"><table><tr><th>Segment</th><th>In this count</th><th>Stores we could check</th>'
            f'<th>Share</th><th>Couldn\'t check</th></tr>{"".join(rows)}</table></div>')
def _plat_table(t):
    if not t['plat'] and not t['checked']:
        return '<p>No store was in this share, so no platform split is available.</p>'
    note=(f'<p>We can name a platform only for a store that publishes a UCP profile. '
          f'{comma(t["unknown"])} of {comma(t["checked"])} stores we could check do not publish a UCP profile, so they are not in this table.</p>')
    if not t['plat']:
        return note+'<p>None of the stores we could check for this signal publish a UCP profile, so no platform is identified.</p>'
    rows=[]
    for name,s in sorted(t['plat'].items(), key=lambda kv: (-kv[1]['found'], -kv[1]['checked'], kv[0].lower())):
        rows.append(f'<tr data-platform="{E(name)}"><td>{E(name)}</td><td>{comma(s["found"])}</td><td>{comma(s["checked"])}</td><td>{share(s["found"], s["checked"])}</td></tr>')
    table=('<div class="tw nomax"><table><tr><th>Platform</th><th>In this count</th>'
           f'<th>Stores we could check that publish a UCP profile</th><th>Share</th></tr>{"".join(rows)}</table></div>')
    return note+table

def _link_store_bits(t, date, verb, left):
    return figure(date, t['found'], t['checked'], verb)+(' '+left if left else '')

def _faq_box(faq):
    return '<div class="box faq" id="faq"><h2>Frequently asked questions</h2>'+''.join(f'<h3>{E(q)}</h3><p>{a}</p>' for q,a in faq)+'</div>'
def _crumbs(name):
    return ('<p class="muted crumbs"><a href="../../">ShopBot Index</a> › '
            f'<a href="../../signals.html">Beyond UCP</a> › {E(name)}</p>')

# ---- how we check (inline HTML, no invented counts) ----
_TAIL=' A store counts when at least one of its websites meets the rule. This page counts stores. The <a href="../../signals.html">Beyond UCP</a> table counts websites, so the two numbers can differ. <a href="../../methodology.html#signals">How we check</a>.'
HOW=dict(
acp=('We request <code>/.well-known/acp.json</code> after reading <code>/robots.txt</code>. It counts as published only on HTTP 200 when the JSON is an object whose <code>protocol.name</code> is <code>acp</code> '
     '(<a href="https://github.com/agentic-commerce-protocol/agentic-commerce-protocol">ACP</a>). A store is one we could check when at least one website returned that file or a not-found response. Refusals, errors and checks we did not reach are left out.'+_TAIL),
ai_catalog=('We request <code>/.well-known/ai-catalog.json</code>. It counts as published only on HTTP 200 when the JSON is an object with an <code>entries</code> list '
            '(<a href="https://modelcontextprotocol.io/seps/2127-mcp-server-cards">MCP server cards</a>). A store is one we could check when at least one website returned that file or a not-found response. Refusals, errors and checks we did not reach are left out.'+_TAIL),
llms_txt=('We request <code>/llms.txt</code>. It counts as published only on HTTP 200 when the body starts with <code>#</code> and the start of the body is not an HTML page (<a href="https://llmstxt.org/">llms.txt</a>). On Shopify this file is generated by the platform. A store is one we could check when at least one website returned that file or a not-found response. Refusals, errors and checks we did not reach are left out.'+_TAIL),
agents_md=('We request <code>/agents.md</code>. It counts as published only on HTTP 200 when the body starts with <code>#</code> and the start of the body is not an HTML page. We check it alongside <code>/llms.txt</code>. A store is one we could check when at least one website returned that file or a not-found response. Refusals, errors and checks we did not reach are left out.'+_TAIL),
mcp=('An MCP endpoint counts only when a UCP profile names one. We send that endpoint one read-only JSON-RPC <code>tools/list</code> request and we never call a tool (<a href="https://ucp.dev/specification/overview/">UCP specification</a>). A tools list counts only on HTTP 200 when at least one tool is named. HTTP 200, 404 or 410 with no tools list is a check that found none. HTTP 401, 403, 429, 451 or 503 is a refusal and is left out of the tools-list share. Any other HTTP status, including 422, means the endpoint responded but we did not get a tools list we accept, so that store is left out of the tools-list share and is counted as naming an endpoint. A store names an endpoint when the tools request was sent and the endpoint answered, refused, or returned no tools list. A robots.txt disallow, or a check we did not reach, is left out of both shares. A store whose profile names no endpoint is left out of the tools-list share and is in the endpoint share as not naming one.'+_TAIL),
robots=('We read <code>/robots.txt</code>. A store has AI crawler rules when a group names at least one of <code>ChatGPT-User</code>, <code>Claude-User</code>, <code>Perplexity-User</code>, <code>Google-Agent</code>, <code>OAI-SearchBot</code>, <code>Claude-SearchBot</code>, <code>PerplexityBot</code>, <code>GPTBot</code>, <code>ClaudeBot</code> or <code>Google-Extended</code>. '
        'The tokens come from the docs of <a href="https://developers.openai.com/api/docs/bots">OpenAI</a>, <a href="https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler">Anthropic</a>, <a href="https://docs.perplexity.ai/docs/resources/perplexity-crawlers">Perplexity</a> and <a href="https://developers.google.com/crawling/docs/crawlers-fetchers/google-user-triggered-fetchers">Google</a>. '
        'A wildcard rule is the <code>User-agent: *</code> group. It disallows the whole site when it disallows <code>/</code>, including when some paths are allowed back. A Content-Signal line is a <code>Content-Signal</code> line in the same file. We could check a store when at least one website returned a robots.txt we could read. robots.txt states the site\'s wishes. It is not a technical block.'+_TAIL),
access=('We request the home page. Answered means HTTP 200 to 299. Refused means HTTP 401, 403, 429 or 503, or a challenge response (<code>cf-mitigated: challenge</code>) that is not a 2xx success. A store was refused only when no checked website answered and at least one was refused. Vendor marks are observations, not refusals: Cloudflare (<code>cf-ray</code>, or server Cloudflare), Akamai (server Akamai, or cookies <code>_abck</code>, <code>bm_sz</code> or <code>ak_bmsc</code>), DataDome (<code>x-datadome</code>, or a datadome cookie), HUMAN (a <code>_px</code> cookie) and Imperva (<code>incap_ses</code> or <code>x-iinfo</code>). '+ACCESS_NOTE+_TAIL),
product=('We fetch one page that looks like a product page, from a link on the home page or, if there is none, from at most two sitemap files. Full means schema.org Product or ProductGroup markup, or microdata <code>itemtype</code> of schema.org/Product, with an Offer or AggregateOffer that has a price, a currency and availability. Partial means Product markup without all three. None means the page we fetched had no Product markup. A store is one we could check when at least one website landed in full, partial or none. If we could not reach a product page, the store is left out. See <a href="https://schema.org/Product">schema.org Product</a>.'+_TAIL),
agent=('These files are read only on websites that answered the UCP pass. Poppy is <code>/.well-known/poppy.json</code>. It counts as published on HTTP 200 when the JSON is an object with a string <code>protocol_version</code> and an <code>organization</code> object (<a href="https://personalagentprotocol.org/docs/spec">Personal Agent Protocol</a>). HTTP 200 that fails that check counts as not found. An A2A agent card is <code>/.well-known/agent-card.json</code> or the earlier <code>/.well-known/agent.json</code> (<a href="https://a2a-protocol.org/latest/topics/agent-discovery/">A2A agent discovery</a>). It counts as published on HTTP 200 when the JSON is an object with a string <code>name</code> and at least one of <code>skills</code>, <code>supportedInterfaces</code>, <code>url</code> or <code>capabilities</code>. If one of the two card paths is a refusal, that website is not treated as a no. A refusal is not "no".'+_TAIL),
)

def _left_file(t):
    refused=t['buckets']['refused']
    s=f'Left out of the share: {comma(t["couldnt"])} stores we couldn\'t check.'
    if refused==1: s+=' 1 of them was refused, and a refusal is not "no".'
    elif refused: s+=f' {comma(refused)} of them were refused, and a refusal is not "no".'
    else: s+=' A refusal is not "no".'
    return s
def _left_simple(t, why):
    return f'Left out of the share: {comma(t["couldnt"])} stores we couldn\'t check ({why}). A refusal is not "no".'

def _section(title, eid, t, store_prefix, slug_for_id, labels, segs, anchor=''):
    h=f'<h2 id="{anchor}">{E(title)}</h2>' if anchor else f'<h2>{E(title)}</h2>'
    big=_big_sentence(t['hits'], store_prefix, slug_for_id)
    return (h+f'<p id="big-{eid}">{big}</p>'
            f'<h3>Named examples, big retailers first ({comma(len(t["hits"]))})</h3>'
            +_examples(t['hits'], store_prefix, slug_for_id, 'examples' if eid=='primary' else 'examples-'+eid)
            +f'<h3 id="by-segment-{eid}">By segment</h3><p>In this count means the stores in the headline figure. Couldn\'t check is left out of the share.</p>'
            +_seg_table(t, labels, segs)
            +f'<h3 id="by-platform-{eid}">By platform</h3>'+_plat_table(t), big)

def _page(path, title, h1, name, desc, lead, parts, faq, big_hits, slug_for_id=None, list_items=None, list_name=''):
    body=_crumbs(name)+f'<h1>{E(h1)}</h1><p class="lede" id="answer">{lead}</p>'+''.join(parts)+_faq_box(faq)
    big_items=[]
    for r in big_hits:
        if r.get('segment')!='big': continue
        slug=slug_for_id(r['id']) if slug_for_id else None
        big_items.append(dict(name=r.get('name') or r['id'], path=(f'store/{slug}.html' if slug else '')))
    return dict(path=path, title=title, h1=h1, desc=desc, body=body, faq=faq, lead=lead,
                big=[x['name'] for x in big_items], big_items=big_items,
                list_items=list_items or [], list_name=list_name)
def _store_link(r, pre, slug_for_id):
    slug=slug_for_id(r['id']) if slug_for_id else None
    name=E(r.get('name') or r['id'])
    if slug: return f'<a href="{pre}store/{E(slug)}.html">{name}</a>'
    return name
def _list_items(hits, slug_for_id, desc_of=None):
    items=[]
    for r in hits:
        slug=slug_for_id(r['id']) if slug_for_id else None
        item=dict(name=r.get('name') or r['id'], path=(f'store/{slug}.html' if slug else ''))
        if desc_of:
            d=desc_of(r)
            if d: item['description']=d
        items.append(item)
    return items

def _item(key, label, href, absurl, sentence):
    return dict(key=key, label=label, href=href, url=absurl, sentence=sentence)

def prepare(retailers, sites, slug_for_id, crawl_date, date_long, segments, seg_labels, ucp, site='https://shopbotindex.com'):
    """ucp is dict(found, checked) for stores we could check for a UCP profile (status ucp + no_ucp)."""
    rows=_rows(retailers, sites); segs=list(segments); labels=seg_labels; pre='../../'; site=site.rstrip('/')
    def T(bucket_of, hits, denoms):
        return tally(rows, bucket_of, hits, denoms, segs)
    file_hit={'found'}; file_denom={'found','not_found'}
    acp=T(lambda f:f['acp'], file_hit, file_denom)
    catalog=T(lambda f:f['ai_catalog'], file_hit, file_denom)
    llms=T(lambda f:f['llms_txt'], file_hit, file_denom)
    agents=T(lambda f:f['agents_md'], file_hit, file_denom)
    mcp_tools=T(lambda f:f['mcp'], {'found'}, {'found','not_found'})
    mcp_decl=T(lambda f:f['mcp'], set(ENDPOINT_NAMED), set(ENDPOINT_NAMED)|{'none_declared'})
    rob=T(lambda f: 'found' if f['robots_readable'] and f['robots_ai'] else 'not_found' if f['robots_readable'] else 'missing', file_hit, file_denom)
    wild=T(lambda f: 'found' if f['robots_readable'] and f['robots_wild'] else 'not_found' if f['robots_readable'] else 'missing', file_hit, file_denom)
    content=T(lambda f: 'found' if f['robots_readable'] and f['robots_content'] else 'not_found' if f['robots_readable'] else 'missing', file_hit, file_denom)
    access=T(lambda f: 'found' if f['access']=='refused' else 'not_found' if f['access']=='answered' else 'missing', file_hit, file_denom)
    # product: full and partial are both "in this count"; none is checked but not in the count
    product=T(lambda f: f['product'] if f['product'] in ('full','partial','none') else 'missing', {'full','partial'}, {'full','partial','none'})
    poppy=T(lambda f:f['poppy'], file_hit, file_denom)
    a2a=T(lambda f:f['a2a'], file_hit, file_denom)
    # access extras and product split use the same rows
    answered=challenge=0; vendors=Counter()
    full=partial=0
    for r,f in rows:
        if f['access']=='answered': answered+=1
        elif f['access']=='refused':
            if f['challenge']: challenge+=1
        if f['access'] in ('answered','refused'):
            for v in f['vendors']: vendors[v]+=1
        if f['product']=='full': full+=1
        elif f['product']=='partial': partial+=1
    access['answered']=answered; access['challenge']=challenge; access['vendor_counts']=vendors
    product['full']=full; product['partial']=partial

    d=date_long
    s_acp=figure(d, acp['found'], acp['checked'], 'publish an Agentic Commerce Protocol (ACP) discovery file', 'publishes an Agentic Commerce Protocol (ACP) discovery file')
    s_cat=figure(d, catalog['found'], catalog['checked'], 'publish an AI catalog', 'publishes an AI catalog')
    s_llms=figure(d, llms['found'], llms['checked'], 'publish an llms.txt file', 'publishes an llms.txt file')
    s_ag=figure(d, agents['found'], agents['checked'], 'publish an AGENTS.md file', 'publishes an AGENTS.md file')
    s_decl=figure(d, mcp_decl['found'], mcp_decl['checked'], 'name an MCP endpoint in their UCP profile', 'names an MCP endpoint in their UCP profile')
    s_ai=figure(d, rob['found'], rob['checked'], 'have robots.txt rules that name an AI crawler', 'has robots.txt rules that name an AI crawler')
    s_wild=figure(d, wild['found'], wild['checked'], 'have a wildcard robots.txt rule that disallows the whole site', 'has a wildcard robots.txt rule that disallows the whole site')
    s_cs=figure(d, content['found'], content['checked'], 'publish a Content-Signal line in robots.txt', 'publishes a Content-Signal line in robots.txt')
    s_acc=figure(d, access['found'], access['checked'], 'had bot protection that refused our crawler')
    s_prod=figure(d, product['found'], product['checked'], 'have schema.org Product markup on a product page we fetched', 'has schema.org Product markup on a product page we fetched')
    s_pop=figure(d, poppy['found'], poppy['checked'], 'publish a valid Poppy file', 'publishes a valid Poppy file')
    s_a2a=figure(d, a2a['found'], a2a['checked'], 'publish a valid A2A agent card', 'publishes a valid A2A agent card')
    s_ucp=figure(d, ucp['found'], ucp['checked'], 'publish a UCP profile', 'publishes a UCP profile')

    err_http=Counter(f['mcp_http'] for r,f in rows if f['mcp']=='error')
    def mcp_tools_sentence():
        n=mcp_tools['found']; n422=err_http.get(422, 0); nref=mcp_tools['buckets']['refused']
        head='Only 1 endpoint returned a tools list when queried' if n==1 else f'Only {comma(n)} endpoints returned a tools list when queried'
        parts=[]
        if n422==1: parts.append('1 returned HTTP 422')
        elif n422: parts.append(f'{comma(n422)} returned HTTP 422')
        if nref==1: parts.append('1 refused')
        elif nref: parts.append(f'{comma(nref)} refused')
        if len(parts)==2: return f'{head} ({parts[0]}, {parts[1]}).'
        if len(parts)==1: return f'{head} ({parts[0]}).'
        return head+'.'
    s_tools=mcp_tools_sentence()
    def mcp_left():
        b=mcp_tools['buckets']
        bits=[]
        if b['refused']: bits.append(_nv(b['refused'], 'store refused the tools request', 'stores refused the tools request'))
        for http, n in sorted(err_http.items(), key=lambda kv: (-kv[1], str(kv[0]))):
            if http==422:
                bits.append(_nv(n, 'store got HTTP 422 and no tools list (the endpoint responded, but the body was not a tools list we accept)',
                                 'stores got HTTP 422 and no tools list (the endpoint responded, but the body was not a tools list we accept)'))
            elif http is None:
                bits.append(_nv(n, 'store got no HTTP status and no tools list', 'stores got no HTTP status and no tools list'))
            else:
                bits.append(_nv(n, f'store got HTTP {http} and no tools list', f'stores got HTTP {http} and no tools list'))
        if b['robots_disallow']: bits.append(_nv(b['robots_disallow'], 'store was disallowed by robots.txt', 'stores were disallowed by robots.txt'))
        if b['not_checked']: bits.append(_nv(b['not_checked'], 'store named an endpoint we did not reach', 'stores named an endpoint we did not reach'))
        if b['none_declared']: bits.append(_nv(b['none_declared'], 'store named no MCP endpoint', 'stores named no MCP endpoint'))
        if b['missing']: bits.append(_nv(b['missing'], 'store was not checked for signals', 'stores were not checked for signals'))
        body='; '.join(bits) if bits else 'none'
        return f'Left out of the tools-list share: {body}. A refusal is not "no". Left out of the endpoint share: {comma(mcp_decl["couldnt"])} stores we couldn\'t check.'
    def access_extra():
        if not access['checked']: return ''
        if challenge==1: ch=f'1 of the {comma(access["found"])} refusals was a challenge page.'
        else: ch=f'{comma(challenge)} of the {comma(access["found"])} refusals were a challenge page.'
        marks=', '.join(f'{label} {comma(vendors[key])}' for key,label in VENDORS)
        return (f'The other {comma(answered)} of those {comma(access["checked"])} answered. {ch} '
                f'Vendor marks on the {comma(access["checked"])} stores we could check: {marks}. A mark is a header or cookie, not a refusal. {ACCESS_NOTE}')
    prod_split=('' if not product['found'] else
                f'Of those, {_nv(full, "includes price, currency and availability", "include price, currency and availability")} and {_nv(partial, "has Product markup without all three", "have Product markup without all three")}.')
    rob_left=(f'All three shares use the same {comma(rob["checked"])} stores whose robots.txt we could read. '
              f'Left out of the share: {comma(rob["couldnt"])} stores whose robots.txt we could not read. A refusal is not "no".')
    facts={r['id']:f for r,f in rows}
    acp_who=(('The store that publishes it is '+human_join([_store_link(r, pre, slug_for_id) for r in acp['hits']])+'.') if len(acp['hits'])==1
             else (('The stores that publish it are '+human_join([_store_link(r, pre, slug_for_id) for r in acp['hits']])+'.') if acp['hits'] else 'No tracked store published one.'))
    acp_note=('The file is the Agentic Commerce Protocol discovery document at <code>/.well-known/acp.json</code>. '
              'OpenAI has written that merchants share catalogs through the Agentic Commerce Protocol for product discovery in ChatGPT '
              '(<a href="https://openai.com/index/powering-product-discovery-in-chatgpt/">OpenAI, March 2026</a>). '
              'Publishing the file is a declaration, not proof that OpenAI checkout works at the store.')
    def _mcp_named():
        bits=[]
        for r in mcp_tools['hits']:
            eps=facts[r['id']].get('mcp_endpoints') or []
            name=_store_link(r, pre, slug_for_id)
            if not eps:
                bits.append(name); continue
            shown=[]
            for ep, tools in eps:
                tool=', '.join(E(t) for t in tools)
                shown.append(f'<a href="{E(ep)}">{E(ep)}</a>'+(f' (tools: {tool})' if tool else ''))
            bits.append(name+' at '+human_join(shown))
        if not bits: return 'No endpoint returned a tools list in this crawl.'
        if len(bits)==1: return 'The endpoint that returned a tools list is '+bits[0]+'.'
        return 'The endpoints that returned a tools list are '+human_join(bits)+'.'
    s_mcp_names=_mcp_named()
    def _whole(spec): return {t:st for t,st in (spec or {}).items() if st in WHOLE_SITE}
    blockers=[]; gpt_block=[]
    for r,f in rows:
        if not f['robots_readable']: continue
        spec=f.get('robots_bots') or {}
        whole=_whole(spec)
        if spec.get('GPTBot') in WHOLE_SITE: gpt_block.append(r)
        if whole: blockers.append((r, whole))
    blockers.sort(key=lambda pair: (0 if pair[0].get('segment')=='big' else 1, (pair[0].get('name') or '').lower(), pair[0].get('id') or ''))
    by_name={r['name']:(r,f) for r,f in rows}
    def _gpt_line(name):
        hit=by_name.get(name)
        if not hit: return ''
        r,f=hit
        if not f.get('robots_readable'): return ''
        spec=f.get('robots_bots') or {}
        st=spec.get('GPTBot')
        if st=='blocked': return f"{E(name)}'s robots.txt asks GPTBot to stay out of the whole site."
        if st=='mostly_blocked': return f"{E(name)}'s robots.txt disallows the whole site for GPTBot except some paths."
        if st=='restricted': return f"{E(name)}'s robots.txt disallows some paths for GPTBot. That is not a whole-site disallow."
        if st=='allowed': return f"{E(name)}'s robots.txt explicitly allows GPTBot."
        if not spec: return f"{E(name)}'s robots.txt that we could read does not name GPTBot or the other AI crawler tokens we record."
        return f"{E(name)}'s robots.txt that we could read does not name GPTBot."
    s_gpt=(f'In the ShopBot Index crawl of {d}, {comma(len(gpt_block))} of {comma(rob["checked"])} stores whose robots.txt we could read disallow the whole site for GPTBot '
           f'(the recorded state is blocked, or mostly blocked when some paths are allowed back).')
    s_named=' '.join(x for x in (_gpt_line('Amazon'), _gpt_line('EBay'), _gpt_line('Walmart')) if x)
    s_wish="A robots.txt disallow is the site's stated wish. It is not a technical block we tested."
    def _bot_bits(whole, esc):
        keys=[t for t in TOKEN_ORDER if t in whole]+sorted(t for t in whole if t not in TOKEN_ORDER)
        return '; '.join(f'{esc(t)}, {BOT_PHRASE[whole[t]]}' for t in keys)
    block_items=[]; block_list=[]
    for r, whole in blockers:
        block_items.append(f'<li>{_store_link(r, pre, slug_for_id)}: {_bot_bits(whole, E)}</li>')
        slug=slug_for_id(r['id']) if slug_for_id else None
        block_list.append(dict(name=r.get('name') or r['id'], path=(f'store/{slug}.html' if slug else ''), description=_bot_bits(whole, lambda t: t)))
    block_html=(f'<h2 id="blocks">Stores whose robots.txt disallows the whole site for a named AI bot ({comma(len(blockers))})</h2>'
                '<p>Blocked means the group disallows <code>/</code> and allows nothing back. Mostly blocked means it disallows <code>/</code> and allows some paths. '
                'When a store has several websites, the state shown is the most restrictive one any checked website recorded for that bot. '
                'A rule that only disallows some paths is not listed here.</p>'
                f'<ul id="bot-blocks">{"".join(block_items)}</ul>')
    mcp_ep_items=[]; mcp_list=[]
    for r in mcp_tools['hits']:
        eps=facts[r['id']].get('mcp_endpoints') or []
        bits=[]; plain=[]
        for ep, tools in eps:
            tool=', '.join(tools)
            bits.append(f'<a href="{E(ep)}">{E(ep)}</a>'+(f' (tools: {E(tool)})' if tool else ''))
            plain.append(ep+(f' (tools: {tool})' if tool else ''))
        mcp_ep_items.append(f'<li>{_store_link(r, pre, slug_for_id)}: {"; ".join(bits)}</li>')
        slug=slug_for_id(r['id']) if slug_for_id else None
        mcp_list.append(dict(name=r.get('name') or r['id'], path=(f'store/{slug}.html' if slug else ''), description='; '.join(plain)))

    leads=dict(
        acp=' '.join(x for x in (s_acp, acp_who, acp_note, _left_file(acp), CAVEAT) if x),
        ai_catalog=' '.join(x for x in (s_cat, _left_file(catalog), CAVEAT) if x),
        llms_txt=' '.join(x for x in (s_llms, _left_file(llms), CAVEAT) if x),
        agents_md=' '.join(x for x in (s_ag, _left_file(agents), CAVEAT) if x),
        mcp=' '.join(x for x in (s_decl, s_tools, s_mcp_names, mcp_left(), CAVEAT) if x),
        robots=' '.join(x for x in (s_gpt, s_named, s_wish, s_ai, s_wild, s_cs, rob_left, CAVEAT) if x),
        access=' '.join(x for x in (s_acc, access_extra(), _left_simple(access, 'the home page was not fetched, or it neither answered nor refused'), CAVEAT) if x),
        product=' '.join(x for x in (s_prod, prod_split, _left_simple(product, 'we could not reach a product page'), CAVEAT) if x),
        agent=' '.join(x for x in (
            s_pop, s_a2a,
            f'Left out of the Poppy share: {comma(poppy["couldnt"])} stores we couldn\'t check. A refusal is not "no".',
            f'Left out of the A2A share: {comma(a2a["couldnt"])} stores we couldn\'t check. A refusal is not "no".',
            CAVEAT) if x),
    )

    def one(key, path, title, h1, crumb, desc, lead, blocks, faq, bigs):
        return _page(path, f'{title} | ShopBot Index', h1, crumb, desc, lead, blocks, faq, bigs, slug_for_id)
    def file_page(key, path, crumb, h1, verb_big, t, how, sentence, list_name=''):
        big=_big_sentence(t['hits'], pre, slug_for_id)
        lead=leads[key]
        faq=[(h1, lead),
             (f'Which big retailers {verb_big}?', big),
             ('How does ShopBot Index check this?', how),
             ('Does publishing this mean agents can buy?', CAVEAT)]
        pg=one(key, path, h1, h1, crumb, sentence, lead, [_single_body(t, pre, slug_for_id, labels, segs, how, big)], faq, t['hits'])
        if list_name:
            pg['list_items']=_list_items(t['hits'], slug_for_id)
            pg['list_name']=list_name
        return pg
    def _single_body(t, pre, slug_for_id, labels, segs, how, big):
        return (f'<p id="big-primary">{big}</p>'
                f'<h2>Named examples, big retailers first ({comma(len(t["hits"]))})</h2>'
                +_examples(t['hits'], pre, slug_for_id, 'examples')
                +'<h2 id="by-segment">By segment</h2><p>In this count means the stores in the headline figure. Couldn\'t check is left out of the share.</p>'
                +_seg_table(t, labels, segs)
                +'<h2 id="by-platform">By platform</h2>'+_plat_table(t)
                +f'<h2 id="how">How we check</h2><p>{how}</p>')

    pages=[]
    pages.append(file_page('acp','signals/acp/index.html','ACP','Which stores publish an Agentic Commerce Protocol (ACP) discovery file?',
                           'publish an ACP discovery file', acp, HOW['acp'], s_acp,
                           list_name='Stores that publish an Agentic Commerce Protocol (ACP) discovery file'))
    pages.append(file_page('llms_txt','signals/llms-txt/index.html','llms.txt','How many online stores have an llms.txt file in 2026?',
                           'publish an llms.txt file', llms, HOW['llms_txt'], s_llms,
                           list_name='Stores that publish an llms.txt file'))
    pages.append(file_page('agents_md','signals/agents-md/index.html','AGENTS.md','How many stores publish an AGENTS.md file?',
                           'publish an AGENTS.md file', agents, HOW['agents_md'], s_ag))
    pages.append(file_page('ai_catalog','signals/ai-catalog/index.html','AI catalog','How many stores publish an AI catalog?',
                           'publish an AI catalog', catalog, HOW['ai_catalog'], s_cat))
    # MCP
    big_tools=_big_sentence(mcp_tools['hits'], pre, slug_for_id)
    big_decl=_big_sentence(mcp_decl['hits'], pre, slug_for_id)
    mcp_h1='Which online stores publish an MCP server for AI agents?'
    mcp_faq=[(mcp_h1, leads['mcp']),
             ('Which big retailers name an MCP endpoint in their UCP profile?', big_decl),
             ('How many endpoints returned a tools list?', s_tools),
             ('Which stores returned a tools list?', s_mcp_names),
             ('How does ShopBot Index check MCP?', HOW['mcp']),
             ('Does naming an MCP endpoint mean agents can buy?', CAVEAT)]
    def _found_line(t):
        bits=[]
        for k in segs:
            s=t['seg'][k]
            bits.append(f'{labels.get(k,k)} {comma(s["found"])}')
        return ', '.join(bits)
    mcp_blocks=[
        f'<p id="big-primary">{big_decl}</p>',
        f'<h2 id="declared">Stores that name an MCP endpoint, big retailers first ({comma(len(mcp_decl["hits"]))})</h2>',
        _examples(mcp_decl['hits'], pre, slug_for_id, 'examples'),
        '<h2 id="by-segment">Endpoint by segment</h2><p>In this count means the stores in the headline figure. Couldn\'t check is left out of the share.</p>',
        _seg_table(mcp_decl, labels, segs),
        '<h2 id="by-platform">Endpoint by platform</h2>', _plat_table(mcp_decl),
        f'<h2 id="tools">Tools list</h2><p>{s_tools}</p>',
        f'<ul id="tools-endpoints">{"".join(mcp_ep_items)}</ul>',
        f'<p id="big-tools">{big_tools}</p>',
        f'<h3>Stores that returned a tools list, big retailers first ({comma(len(mcp_tools["hits"]))})</h3>',
        _examples(mcp_tools['hits'], pre, slug_for_id, 'examples-tools'),
        f'<p>Stores whose endpoint returned a tools list, by segment: {_found_line(mcp_tools)}. This is a count of responses, not a share of stores.</p>',
        f'<h2 id="how">How we check</h2><p>{HOW["mcp"]}</p>']
    pages.append(_page('signals/mcp/index.html', mcp_h1+' | ShopBot Index', mcp_h1,
                       'MCP', s_decl, leads['mcp'], mcp_blocks, mcp_faq, mcp_decl['hits'], slug_for_id,
                       list_items=mcp_list, list_name='MCP endpoints that returned a tools list'))
    # robots
    big_ai=_big_sentence(rob['hits'], pre, slug_for_id)
    big_w=_big_sentence(wild['hits'], pre, slug_for_id)
    big_c=_big_sentence(content['hits'], pre, slug_for_id)
    rob_h1='Which retailers block AI bots like GPTBot in robots.txt?'
    rob_faq=[(rob_h1, leads['robots']),
             ('How many stores name AI crawlers in robots.txt?', s_ai+' '+rob_left),
             ('Which big retailers have robots.txt rules that name an AI crawler?', big_ai),
             ('Which big retailers have a wildcard robots.txt rule that disallows the whole site?', big_w),
             ('Which big retailers publish a Content-Signal line?', big_c),
             ('How does ShopBot Index check robots.txt?', HOW['robots']),
             ('Does a robots.txt rule mean agents can buy?', CAVEAT)]
    rob_blocks=[
        block_html,
        f'<p id="big-primary">{big_ai}</p>',
        f'<h2>Stores with AI crawler rules, big retailers first ({comma(len(rob["hits"]))})</h2>',
        _examples(rob['hits'], pre, slug_for_id, 'examples'),
        '<h2 id="by-segment">AI crawler rules by segment</h2>', _seg_table(rob, labels, segs),
        '<h2 id="by-platform">AI crawler rules by platform</h2>', _plat_table(rob),
        f'<h2 id="wildcard">Wildcard rule that disallows the whole site</h2><p>{s_wild}</p>',
        f'<p id="big-wildcard">{big_w}</p>',
        f'<h3>Stores with a wildcard block, big retailers first ({comma(len(wild["hits"]))})</h3>',
        _examples(wild['hits'], pre, slug_for_id, 'examples-wildcard'),
        '<h3 id="by-segment-wildcard">Wildcard block by segment</h3>', _seg_table(wild, labels, segs),
        f'<h2 id="content-signal">Content-Signal</h2><p>{s_cs}</p>',
        f'<p id="big-content">{big_c}</p>',
        f'<h3>Stores with a Content-Signal line, big retailers first ({comma(len(content["hits"]))})</h3>',
        _examples(content['hits'], pre, slug_for_id, 'examples-content'),
        '<h3 id="by-segment-content">Content-Signal by segment</h3>', _seg_table(content, labels, segs),
        f'<h2 id="how">How we check</h2><p>{HOW["robots"]}</p>']
    pages.append(_page('signals/ai-bots-robots/index.html', rob_h1+' | ShopBot Index', rob_h1,
                       'AI crawler rules', s_ai, leads['robots'], rob_blocks, rob_faq, rob['hits'], slug_for_id,
                       list_items=block_list, list_name='Stores whose robots.txt disallows the whole site for a named AI bot'))
    # bot protection
    big_acc=_big_sentence(access['hits'], pre, slug_for_id)
    acc_faq=[('How many stores were refused by bot protection?', leads['access']),
             ('Which big retailers were refused by bot protection?', big_acc),
             ('How does ShopBot Index check bot protection?', HOW['access']),
             ('What does a bot-protection refusal say about shoppers and AI agents?', ACCESS_NOTE+' '+CAVEAT)]
    acc_blocks=[
        f'<p id="big-primary">{big_acc}</p>',
        f'<h2>Stores bot protection refused, big retailers first ({comma(len(access["hits"]))})</h2>',
        _examples(access['hits'], pre, slug_for_id, 'examples'),
        '<h2 id="by-segment">By segment</h2>', _seg_table(access, labels, segs),
        '<h2 id="by-platform">By platform</h2>', _plat_table(access),
        f'<h2 id="how">How we check</h2><p>{HOW["access"]}</p>']
    pages.append(_page('signals/bot-protection/index.html','How many stores were refused by bot protection? | ShopBot Index','How many stores were refused by bot protection?',
                       'Bot protection', s_acc, leads['access'], acc_blocks, acc_faq, access['hits'], slug_for_id))
    # product
    pages.append(file_page('product','signals/product-data/index.html','Product data','How many stores have structured product data?',
                           'have structured product data', product, HOW['product'], s_prod))
    # fix product page lead (file_page used leads['product'] via key). file_page looks up leads[key]. Good.
    # agent cards
    big_pop=_big_sentence(poppy['hits'], pre, slug_for_id)
    big_a=_big_sentence(a2a['hits'], pre, slug_for_id)
    ag_faq=[('How many stores publish a Poppy file or an A2A agent card?', leads['agent']),
            ('Which big retailers publish a valid Poppy file?', big_pop),
            ('Which big retailers publish a valid A2A agent card?', big_a),
            ('How does ShopBot Index check Poppy and A2A?', HOW['agent']),
            ('Does publishing an agent card mean agents can buy?', CAVEAT)]
    ag_blocks=[
        f'<h2 id="poppy">Poppy</h2><p>{s_pop}</p>',
        f'<p id="big-poppy">{big_pop}</p>',
        f'<h3>Stores with a valid Poppy file, big retailers first ({comma(len(poppy["hits"]))})</h3>',
        _examples(poppy['hits'], pre, slug_for_id, 'examples'),
        '<h3 id="by-segment">Poppy by segment</h3>', _seg_table(poppy, labels, segs),
        '<h3 id="by-platform">Poppy by platform</h3>', _plat_table(poppy),
        f'<h2 id="a2a">A2A agent card</h2><p>{s_a2a}</p>',
        f'<p id="big-a2a">{big_a}</p>',
        f'<h3>Stores with a valid A2A agent card, big retailers first ({comma(len(a2a["hits"]))})</h3>',
        _examples(a2a['hits'], pre, slug_for_id, 'examples-a2a'),
        '<h3 id="by-segment-a2a">A2A by segment</h3>', _seg_table(a2a, labels, segs),
        '<h3 id="by-platform-a2a">A2A by platform</h3>', _plat_table(a2a),
        f'<h2 id="how">How we check</h2><p>{HOW["agent"]}</p>']
    pages.append(_page('signals/agent-cards/index.html','How many stores publish a Poppy file or an A2A agent card? | ShopBot Index','How many stores publish a Poppy file or an A2A agent card?',
                       'Agent cards', s_pop, leads['agent'], ag_blocks, ag_faq, poppy['hits'], slug_for_id))

    # The product file_page call used key 'product' and leads['product']. Good.
    # But file_page's first FAQ is (h1, lead) and h1 was passed. Verify product is in pages before agent... yes.

    urls=dict(
        ucp=(site+'/#summary','./#summary'),
        acp=(site+'/signals/acp/','signals/acp/'),
        llms_txt=(site+'/signals/llms-txt/','signals/llms-txt/'),
        agents_md=(site+'/signals/agents-md/','signals/agents-md/'),
        ai_catalog=(site+'/signals/ai-catalog/','signals/ai-catalog/'),
        mcp_tools=(site+'/signals/mcp/#tools','signals/mcp/#tools'),
        mcp_declared=(site+'/signals/mcp/','signals/mcp/'),
        robots_ai=(site+'/signals/ai-bots-robots/','signals/ai-bots-robots/'),
        robots_wild=(site+'/signals/ai-bots-robots/#wildcard','signals/ai-bots-robots/#wildcard'),
        content_signal=(site+'/signals/ai-bots-robots/#content-signal','signals/ai-bots-robots/#content-signal'),
        access=(site+'/signals/bot-protection/','signals/bot-protection/'),
        product=(site+'/signals/product-data/','signals/product-data/'),
        poppy=(site+'/signals/agent-cards/#poppy','signals/agent-cards/#poppy'),
        a2a=(site+'/signals/agent-cards/#a2a','signals/agent-cards/#a2a'),
    )
    specs=[
        ('ucp','UCP profile', s_ucp),
        ('acp','ACP', s_acp),
        ('llms_txt','llms.txt', s_llms),
        ('agents_md','AGENTS.md', s_ag),
        ('ai_catalog','AI catalog', s_cat),
        ('mcp_declared','MCP endpoint', s_decl),
        ('mcp_tools','MCP tools list', s_tools),
        ('robots_ai','AI crawler rules', s_ai),
        ('robots_wild','Wildcard robots.txt block', s_wild),
        ('content_signal','Content-Signal', s_cs),
        ('access','Bot protection', s_acc),
        ('product','Product data', s_prod),
        ('poppy','Poppy', s_pop),
        ('a2a','A2A agent card', s_a2a),
    ]
    items=[_item(k, lab, urls[k][1], urls[k][0], sent) for k,lab,sent in specs]
    framing=(f'In the ShopBot Index crawl of {d}, these are the agent-readiness signals the crawl records. '
             f'Each figure counts stores, and only stores we could check for that signal. '
             f'A store counts when at least one of its websites meets the check. '
             f'Stores we couldn\'t check are left out. A refusal is not "no". {CAVEAT}')
    lines=[f'{it["label"]}: {it["sentence"]} <a href="{E(it["href"])}">{E(it["url"])}</a>' for it in items]
    inner=framing+' <br>'+' <br>'.join(lines)
    overview=f'<div class="answer" id="agent-readiness"><p>{inner}</p></div>'
    q=f'What did the {d} crawl record for each agent-readiness signal?'
    faq=[(q, inner)]
    plain=['## AI agent readiness','',framing,'']
    for it in items:
        plain.append(f'- {it["label"]}: {it["sentence"]} {it["url"]}')
    plain.append('')
    # segment breakdown for llms-full
    seg_lines=['','## AI agent readiness by segment (stores we could check)','',
               'Each line is the stores in that segment we could check for that signal. Could not check is left out.','']
    seg_stats=[
        ('ACP', acp, urls['acp'][0], 'share'), ('llms.txt', llms, urls['llms_txt'][0], 'share'), ('AGENTS.md', agents, urls['agents_md'][0], 'share'),
        ('AI catalog', catalog, urls['ai_catalog'][0], 'share'),
        ('MCP endpoint', mcp_decl, urls['mcp_declared'][0], 'share'),
        ('MCP tools list', mcp_tools, urls['mcp_tools'][0], 'count'),
        ('AI crawler rules', rob, urls['robots_ai'][0], 'share'),
        ('Wildcard robots.txt block', wild, urls['robots_wild'][0], 'share'), ('Content-Signal', content, urls['content_signal'][0], 'share'),
        ('Bot protection refused our crawler', access, urls['access'][0], 'share'), ('Product data', product, urls['product'][0], 'share'),
        ('Poppy', poppy, urls['poppy'][0], 'share'), ('A2A agent card', a2a, urls['a2a'][0], 'share')]
    for lab,t,url,kind in seg_stats:
        seg_lines.append(f'### {lab}')
        seg_lines.append('')
        for k in segs:
            s=t['seg'][k]
            if kind=='count':
                seg_lines.append(f'- {labels.get(k,k)}: {comma(s["found"])} returned a tools list. {url}')
            else:
                seg_lines.append(f'- {labels.get(k,k)}: {comma(s["found"])} of {comma(s["checked"])} ({share(s["found"], s["checked"])}). {url}')
        seg_lines.append('')
    deep={
        'acp':'signals/acp/','ai-catalog':'signals/ai-catalog/','llms-txt':'signals/llms-txt/','agents-md':'signals/agents-md/',
        'mcp-tools':'signals/mcp/','robots-ai':'signals/ai-bots-robots/','content-signals':'signals/ai-bots-robots/#content-signal',
        'product-data':'signals/product-data/','poppy':'signals/agent-cards/#poppy','a2a':'signals/agent-cards/#a2a',
    }
    figures=dict(acp=acp, ai_catalog=catalog, llms_txt=llms, agents_md=agents, mcp_tools=mcp_tools, mcp_declared=mcp_decl,
                 robots_ai=rob, robots_wild=wild, content_signal=content, access=access, product=product, poppy=poppy, a2a=a2a)
    return dict(overview_html=overview, faq=faq, llms='\n'.join(plain).rstrip()+'\n', segments_llms='\n'.join(seg_lines).rstrip()+'\n',
                pages=pages, items=items, deep=deep, figures=figures, sentences=dict(
                    ucp=s_ucp, acp=s_acp, ai_catalog=s_cat, llms_txt=s_llms, agents_md=s_ag, mcp_tools=s_tools, mcp_declared=s_decl,
                    robots_ai=s_ai, robots_wild=s_wild, content_signal=s_cs, access=s_acc, product=s_prod, poppy=s_pop, a2a=s_a2a),
                framing=framing, product_full=full, product_partial=partial, access_answered=answered, access_challenge=challenge,
                vendor_counts={k:vendors[k] for k,_ in VENDORS})
