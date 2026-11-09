"""Website-level counts for public signals other than the UCP profile.

Every figure comes from a crawl file. A share uses only websites that answered
for that file (found + not found). Refused and error are left out of the share:
a refusal is not "no". Week-over-week is omitted when the previous crawl has
no data for that signal.

build.py writes data/beyond-ucp-latest.json and data/beyond-ucp-latest.md.
"""
import datetime, html, re

REFUSED_HTTP={401,403,429,451,503}
NOT_FOUND_HTTP={404,410}

def comma(n): return f'{n:,}'
def share(found, answered):
    return f'{(100*found/answered):.1f}%' if answered else 'n/a'
def dlong(d):
    x=datetime.date.fromisoformat(d); return f'{x.day} {x.strftime("%B")} {x.year}'
def E(s): return html.escape(str(s if s is not None else ''), quote=True)

def _blank():
    return dict(found=0,not_found=0,refused=0,error=0,robots_disallow=0,not_checked=0,
                not_applicable=0,could_not_read=0,not_recorded=0,reached=0,full=0,partial=0,
                refused_known=True,error_known=True)
def _check(key, t, parts):
    if sum(t[p] for p in parts)!=t['reached']:
        raise ValueError(f'{key} buckets { {p:t[p] for p in parts} } do not add up to reached {t["reached"]}')

def _phase2(sites):
    return [s for s in sites if (s.get('signals') or {}).get('checked')]
def _phase3(sites):
    return [s for s in sites if (s.get('agent_files') or {}).get('checked')]

def tally_file(sites, key):
    t=_blank(); rows=_phase2(sites); t['reached']=len(rows)
    for s in rows:
        v=(s.get('signals') or {}).get(key)
        st=v.get('state') if isinstance(v, dict) else None
        if st in ('found','not_found','refused','error','robots_disallow','not_checked'): t[st]+=1
        else: t['not_recorded']+=1
    _check(key, t, ('found','not_found','refused','error','robots_disallow','not_checked','not_recorded'))
    return t

def tally_mcp(sites):
    t=_blank(); rows=_phase2(sites); t['reached']=len(rows)
    for s in rows:
        m=(s.get('signals') or {}).get('mcp')
        m=m if isinstance(m, dict) else {}
        st=m.get('state'); http=m.get('http')
        if st=='answered': t['found']+=1
        elif st=='none_declared': t['not_applicable']+=1
        elif st=='robots_disallow': t['robots_disallow']+=1
        elif st=='not_checked': t['not_checked']+=1
        elif st=='no_tools':
            if http in (200,)+tuple(NOT_FOUND_HTTP): t['not_found']+=1
            elif http in REFUSED_HTTP: t['refused']+=1
            else: t['error']+=1
        else: t['not_recorded']+=1
    _check('mcp', t, ('found','not_found','refused','error','robots_disallow','not_checked','not_applicable','not_recorded'))
    return t

def tally_robots(sites, kind):
    """kind 'ai' (named AI crawler tokens) or 'content' (Content-Signal lines)."""
    t=_blank(); t['refused_known']=False; t['error_known']=False
    rows=_phase2(sites); t['reached']=len(rows)
    for s in rows:
        rb=(s.get('signals') or {}).get('robots')
        if not isinstance(rb, dict) or 'present' not in rb:
            t['not_recorded']+=1; continue
        if not rb.get('present'):
            t['could_not_read']+=1; continue
        hit=bool(rb.get('specific')) if kind=='ai' else bool(rb.get('content_signal'))
        t['found' if hit else 'not_found']+=1
    _check('robots_'+kind, t, ('found','not_found','could_not_read','not_recorded'))
    return t

def tally_product(sites):
    t=_blank(); t['refused_known']=False; t['error_known']=False
    rows=_phase2(sites); t['reached']=len(rows)
    for s in rows:
        p=(s.get('signals') or {}).get('product')
        st=p.get('state') if isinstance(p, dict) else None
        if st=='full': t['full']+=1; t['found']+=1
        elif st=='partial': t['partial']+=1; t['found']+=1
        elif st=='none': t['not_found']+=1
        elif st=='robots_disallow': t['robots_disallow']+=1
        elif st=='not_checked': t['not_checked']+=1
        else: t['not_recorded']+=1
    _check('product', t, ('found','not_found','robots_disallow','not_checked','not_recorded'))
    return t

def _af_state(rec):
    if not isinstance(rec, dict): return 'not_recorded'
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

def _combine(states):
    xs=[x for x in states if x!='recorded_elsewhere']
    if not xs: return 'not_recorded'
    if 'found' in xs: return 'found'
    if all(x=='not_found' for x in xs): return 'not_found'
    for k in ('refused','error','robots_disallow','not_checked','not_recorded'):
        if k in xs: return k
    return 'not_recorded'

def tally_agent(sites, keys):
    t=_blank(); rows=_phase3(sites); t['reached']=len(rows)
    for s in rows:
        af=s.get('agent_files') or {}
        t[_combine([_af_state(af.get(k)) for k in keys])]+=1
    _check('+'.join(keys), t, ('found','not_found','refused','error','robots_disallow','not_checked','not_recorded'))
    return t

def _found_file(key):
    return lambda s: ((s.get('signals') or {}).get(key) or {}).get('state')=='found'
def _found_mcp(s):
    return ((s.get('signals') or {}).get('mcp') or {}).get('state')=='answered'
def _found_robots(kind):
    def pred(s):
        rb=(s.get('signals') or {}).get('robots') or {}
        if not rb.get('present'): return False
        return bool(rb.get('specific')) if kind=='ai' else bool(rb.get('content_signal'))
    return pred
def _found_product(s):
    return ((s.get('signals') or {}).get('product') or {}).get('state') in ('full','partial')
def _found_agent(keys):
    def pred(s):
        af=s.get('agent_files') or {}
        return any((af.get(k) or {}).get('valid') for k in keys)
    return pred

# sentence tokens {name} become links. Sources are ones the methodology already cites.
SPECS=[
 dict(key='llms_txt', id='llms-txt', label='llms.txt', scope='phase2', tally=lambda sites: tally_file(sites,'llms_txt'), pred=_found_file('llms_txt'),
      sentence='A Markdown file at /llms.txt with notes for AI assistants, from the {src} proposal.',
      sources=dict(src=('https://llmstxt.org/','llms.txt'))),
 dict(key='agents_md', id='agents-md', label='AGENTS.md', scope='phase2', tally=lambda sites: tally_file(sites,'agents_md'), pred=_found_file('agents_md'),
      sentence='A Markdown file at /agents.md with instructions for AI assistants, checked alongside llms.txt as described in our {src}.',
      sources=dict(src=('methodology.html#signals','methodology'))),
 dict(key='mcp_tools', id='mcp-tools', label='MCP tools', scope='phase2', tally=tally_mcp, pred=_found_mcp,
      sentence='A read-only tools/list answer from an MCP endpoint named in the store\'s UCP profile ({src}).',
      sources=dict(src=('https://ucp.dev/specification/overview/','UCP specification')),
      na='whose UCP profile named no MCP endpoint'),
 dict(key='ai_catalog', id='ai-catalog', label='AI catalog', scope='phase2', tally=lambda sites: tally_file(sites,'ai_catalog'), pred=_found_file('ai_catalog'),
      sentence='A discovery file at /.well-known/ai-catalog.json listing MCP servers ({src}).',
      sources=dict(src=('https://modelcontextprotocol.io/seps/2127-mcp-server-cards','MCP server cards'))),
 dict(key='acp', id='acp', label='ACP', scope='phase2', tally=lambda sites: tally_file(sites,'acp'), pred=_found_file('acp'),
      sentence='An Agentic Commerce Protocol discovery file at /.well-known/acp.json ({src}).',
      sources=dict(src=('https://github.com/agentic-commerce-protocol/agentic-commerce-protocol','ACP'))),
 dict(key='robots_ai', id='robots-ai', label='robots.txt AI rules', scope='phase2', tally=lambda sites: tally_robots(sites,'ai'), pred=_found_robots('ai'),
      sentence='robots.txt rules that name AI crawler tokens documented by {openai}, {anthropic}, {perplexity} and {google}.',
      sources=dict(openai=('https://developers.openai.com/api/docs/bots','OpenAI'),
                   anthropic=('https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler','Anthropic'),
                   perplexity=('https://docs.perplexity.ai/docs/resources/perplexity-crawlers','Perplexity'),
                   google=('https://developers.google.com/crawling/docs/crawlers-fetchers/google-user-triggered-fetchers','Google')),
      could='no readable robots.txt'),
 dict(key='content_signals', id='content-signals', label='Content signals', scope='phase2', tally=lambda sites: tally_robots(sites,'content'), pred=_found_robots('content'),
      sentence='Content-Signal lines in robots.txt, recorded with the AI crawler tokens documented by {openai}, {anthropic}, {perplexity} and {google}.',
      sources=dict(openai=('https://developers.openai.com/api/docs/bots','OpenAI'),
                   anthropic=('https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler','Anthropic'),
                   perplexity=('https://docs.perplexity.ai/docs/resources/perplexity-crawlers','Perplexity'),
                   google=('https://developers.google.com/crawling/docs/crawlers-fetchers/google-user-triggered-fetchers','Google')),
      could='no readable robots.txt'),
 dict(key='product', id='product-data', label='Product data', scope='phase2', tally=tally_product, pred=_found_product,
      sentence='schema.org Product markup on one product page we could fetch ({src}).',
      sources=dict(src=('https://schema.org/Product','schema.org Product')),
      unchecked='not reached (no product page)'),
 dict(key='poppy', id='poppy', label='Poppy', scope='phase3', tally=lambda sites: tally_agent(sites,('poppy',)), pred=_found_agent(('poppy',)),
      sentence='A Personal Agent Protocol file at /.well-known/poppy.json ({src}).',
      sources=dict(src=('https://personalagentprotocol.org/docs/spec','Personal Agent Protocol'))),
 dict(key='a2a', id='a2a', label='A2A agent card', scope='phase3', tally=lambda sites: tally_agent(sites,('a2a_card','a2a_card_legacy')), pred=_found_agent(('a2a_card','a2a_card_legacy')),
      sentence='An A2A agent card at /.well-known/agent-card.json or the earlier /.well-known/agent.json path ({src}).',
      sources=dict(src=('https://a2a-protocol.org/latest/topics/agent-discovery/','A2A agent discovery'))),
]

def _abs(href, site):
    if href.startswith('http://') or href.startswith('https://') or href.startswith('mailto:'): return href
    return site.rstrip('/')+'/'+href.lstrip('/')
def sentence_plain(spec, site):
    def repl(m):
        href,label=spec['sources'][m.group(1)]
        return f'{label} ({_abs(href, site)})'
    return re.sub(r'\{(\w+)\}', repl, spec['sentence'])
def sentence_html(spec):
    text=spec['sentence']
    parts=re.split(r'\{(\w+)\}', text)
    out=[]
    for i,part in enumerate(parts):
        if i%2==0: out.append(E(part))
        else:
            href,label=spec['sources'][part]
            out.append(f'<a href="{E(href)}">{E(label)}</a>')
    return ''.join(out)

def _has_data(t):
    return t['reached']>0 and t['not_recorded']<t['reached']

def _aside(spec, t):
    notes=[]
    if spec['key']=='product' and t['found']:
        notes.append(f"Of the {comma(t['found'])} found, {comma(t['full'])} have price, currency and availability and {comma(t['partial'])} have Product markup without all three.")
    left=[]
    if t['robots_disallow']: left.append(f"{comma(t['robots_disallow'])} disallowed by robots.txt")
    if t['not_applicable']: left.append(f"{comma(t['not_applicable'])} {spec.get('na','where the check did not apply')}")
    if t['could_not_read']: left.append(f"{comma(t['could_not_read'])} with {spec.get('could','no readable file')}")
    if t['not_checked']: left.append(f"{comma(t['not_checked'])} {spec.get('unchecked','not checked')}")
    if left: notes.append('Left out of the share: '+'; '.join(left)+'.')
    if spec['scope']=='phase3':
        notes.append(f"Checked on {comma(t['reached'])} websites that answered the UCP pass, which is this file's own denominator set.")
    if not t['refused_known']:
        notes.append('This file has no separate refused or error count.')
    return ' '.join(notes)

def _wow(found, prev):
    if not prev: return 'not in the previous crawl'
    delta=found-prev['found']
    was=f"was {comma(prev['found'])} of {comma(prev['answered'])}"
    if delta==0: return f'unchanged ({was})'
    word='more' if delta>0 else 'fewer'
    return f'{comma(abs(delta))} {word} ({was})'

def _num(t, key):
    if key=='refused' and not t['refused_known']: return None
    if key=='error' and not t['error_known']: return None
    return t[key]

def _publishers(sites, retailers, pred, slug_for_id):
    ids=sorted({s.get('rid') for s in sites if s.get('rid') and pred(s)})
    by={r['id']:r for r in retailers}
    out=[]
    for i in ids:
        r=by.get(i)
        if not r: continue
        item=dict(id=i, name=r.get('name') or i)
        if slug_for_id:
            sl=slug_for_id(i)
            if sl: item['path']=f'store/{sl}.html'
        out.append(item)
    out.sort(key=lambda x: (x['name'].lower(), x['id']))
    return out

def _public(spec, t, prev, prev_date, stores, site):
    answered=t['found']+t['not_found']
    previous=None; change=None
    if prev and _has_data(prev):
        pa=prev['found']+prev['not_found']
        previous=dict(crawl_date=prev_date, found=prev['found'], not_found=prev['not_found'], answered=pa,
                      refused=_num(prev,'refused'), error=_num(prev,'error'), reached=prev['reached'],
                      share_display=share(prev['found'], pa))
        change=t['found']-prev['found']
    sig=dict(key=spec['key'], id=spec['id'], label=spec['label'], scope=spec['scope'],
             sentence=sentence_plain(spec, site), sentence_html=sentence_html(spec),
             sources=[dict(token=k, href=_abs(v[0], site), label=v[1]) for k,v in spec['sources'].items()],
             found=t['found'], not_found=t['not_found'], answered=answered,
             refused=_num(t,'refused'), error=_num(t,'error'),
             robots_disallow=t['robots_disallow'], not_checked=t['not_checked'],
             not_applicable=t['not_applicable'], could_not_read=t['could_not_read'],
             reached=t['reached'], full=t['full'] if spec['key']=='product' else None,
             partial=t['partial'] if spec['key']=='product' else None,
             share_display=share(t['found'], answered),
             aside=_aside(spec, t), wow=_wow(t['found'], previous),
             previous=previous, found_change=change,
             stores=stores, store_count=len(stores))
    sig['prose']=_prose(sig, prev_date)
    return sig

def _cell(v):
    return 'n/a' if v is None else comma(v)

def _prose(sig, prev_date):
    bits=[f"{sig['label']}: found {comma(sig['found'])} of {comma(sig['answered'])} websites that answered ({sig['share_display']})."]
    if sig['refused'] is not None: bits.append(f"Refused {comma(sig['refused'])}.")
    if sig['error'] is not None: bits.append(f"Error {comma(sig['error'])}.")
    if sig['aside']: bits.append(sig['aside'])
    if sig['previous']:
        bits.append(f"Week over week: {sig['wow']} on {dlong(sig['previous']['crawl_date'])}.")
    elif prev_date:
        bits.append(f"Week over week: not in the {dlong(prev_date)} crawl.")
    if sig['store_count']==0: bits.append('No tracked store publishes it.')
    elif sig['store_count']==1: bits.append('1 store publishes it.')
    else: bits.append(f"{comma(sig['store_count'])} stores publish it.")
    return ' '.join(bits)

def report(sites, retailers, crawl_date, previous_sites=None, previous_retailers=None, previous_date=None, slug_for_id=None, site='https://shopbotindex.com'):
    phase2=len(_phase2(sites)); phase3=len(_phase3(sites))
    signals=[]
    for spec in SPECS:
        t=spec['tally'](sites)
        prev=spec['tally'](previous_sites) if previous_sites is not None else None
        if prev is not None and not _has_data(prev): prev=None
        stores=_publishers(sites, retailers, spec['pred'], slug_for_id)
        signals.append(_public(spec, t, prev, previous_date, stores, site))
    out=dict(crawl_date=crawl_date, previous_crawl_date=previous_date,
             phase2_reached=phase2, phase3_reached=phase3,
             denominator='Websites that answered for that file (found plus not found). Refused is not "no". Error is not "no". Those websites are left out of the share.',
             signals=signals)
    out['newsletter_text']=newsletter_text(out, site)
    return out

def public_dict(rep):
    """JSON-ready copy: counts, denominators, stores. HTML for the sentence is left out."""
    sigs=[]
    for s in rep['signals']:
        sigs.append({k:v for k,v in s.items() if k!='sentence_html'})
    body=dict(rep); body['signals']=sigs
    return body

def newsletter_text(rep, site='https://shopbotindex.com'):
    when=dlong(rep['crawl_date'])
    lines=[
        f'Beyond UCP, crawl of {when}',
        '',
        'UCP stays the headline: which stores publish a UCP profile. The same crawl also counts other public signals. Each share uses only the websites that answered for that file. Refused is not "no". An error is not "no". Those websites are left out of the share.',
        '',
        f"Agent-readiness pass: {comma(rep['phase2_reached'])} websites reached. Agent discovery files (Poppy, A2A): {comma(rep['phase3_reached'])} websites checked.",
        '',
    ]
    for sig in rep['signals']:
        lines.append(sig['prose'])
        lines.append('')
    lines.append(f"Stores for each signal: {site.rstrip('/')}/signals.html")
    lines.append(f"How we check: {site.rstrip('/')}/methodology.html#signals")
    return '\n'.join(lines).rstrip()+'\n'

def _table(rep, link_prefix):
    prev=rep.get('previous_crawl_date')
    head=f'Vs {dlong(prev)}' if prev else 'Vs previous crawl'
    rows=[]
    for sig in rep['signals']:
        href=f'{link_prefix}#{sig["id"]}' if link_prefix else f'#{sig["id"]}'
        rows.append(
            f'<tr><td><a href="{E(href)}">{E(sig["label"])}</a></td>'
            f'<td>{comma(sig["found"])}</td><td>{comma(sig["answered"])}</td><td>{E(sig["share_display"])}</td>'
            f'<td>{_cell(sig["refused"])}</td><td>{_cell(sig["error"])}</td><td>{E(sig["wow"])}</td></tr>')
    return (f'<div class="tw nomax"><table><tr><th>Signal</th><th>Found</th><th>Websites that answered</th>'
            f'<th>Share</th><th>Refused</th><th>Error</th><th>{E(head)}</th></tr>{"".join(rows)}</table></div>')

def summary_html(rep, link_prefix='signals.html', page='home'):
    """Compact Beyond UCP block for the home page and the changes page."""
    intro=(f'<p class="sig-copy">UCP stays the headline: which stores publish a UCP profile. '
           f'The same crawl of {E(dlong(rep["crawl_date"]))} also counts other public signals. '
           f'Each share uses only the websites that answered for that file. '
           f'<b>Refused is not "no".</b> An error is not "no". Those websites are left out of the share.</p>'
           f'<p class="sig-copy">Agent-readiness pass: <b>{comma(rep["phase2_reached"])}</b> websites reached. '
           f'Poppy and the A2A agent card were checked on <b>{comma(rep["phase3_reached"])}</b> websites that answered the UCP pass. '
           f'That is their own set, not the {comma(rep["phase2_reached"])} above.</p>')
    notes=''.join(f'<li class="sig-copy"><b>{E(s["label"])}.</b> {E(s["aside"])}</li>' for s in rep['signals'] if s['aside'])
    if page=='changes':
        foot=('<p class="sig-copy">Store by store, who gained or lost a signal is further down this page. '
              f'<a href="{E(link_prefix or "signals.html")}">Every signal and the stores that publish it</a>. '
              '<a href="methodology.html#signals">How we check</a>.</p>')
    elif page=='signals':
        foot=('<p class="sig-copy">The stores are listed under each signal below. '
              '<a href="methodology.html#signals">How we check</a>. '
              'A store is listed when at least one of its websites publishes the file, so the store count can be lower than the website count.</p>')
    else:
        foot=(f'<p class="sig-copy"><a href="{E(link_prefix or "signals.html")}">Every signal and the stores that publish it</a>. '
              '<a href="methodology.html#signals">How we check</a>.</p>')
    return (f'<section id="beyond-ucp" class="beyond"><h2>Beyond UCP</h2>{intro}{_table(rep, "" if page=="signals" else (link_prefix or "signals.html"))}'
            f'<ul class="sig-notes">{notes}</ul>{foot}</section>')

def page_html(rep):
    blocks=[f'<h1>Beyond UCP</h1>',
            f'<p class="lede sig-copy">Public signals other than the UCP profile, from the crawl of {E(dlong(rep["crawl_date"]))}. '
            f'UCP stays the headline on the home page: which stores publish a UCP profile. '
            f'Each share below uses only the websites that answered for that file. '
            f'<b>Refused is not "no".</b> An error is not "no".</p>',
            summary_html(rep, link_prefix='', page='signals')]
    for sig in rep['signals']:
        if sig['stores']:
            items=''.join(f'<li><a href="{E(s["path"])}">{E(s["name"])}</a></li>' if s.get('path') else f'<li>{E(s["name"])}</li>' for s in sig['stores'])
            listing=f'<ul class="cols">{items}</ul>'
        else:
            listing='<p class="sig-copy">No tracked store published this in this crawl.</p>'
        n=sig['store_count']
        blocks.append(
            f'<section><h2 id="{E(sig["id"])}">{E(sig["label"])}</h2>'
            f'<p class="sig-copy">{sig["sentence_html"]}</p>'
            f'<p class="sig-copy">{E(sig["prose"])}</p>'
            f'<h3>Stores that publish it ({comma(n)})</h3>{listing}</section>')
    return ''.join(blocks)
