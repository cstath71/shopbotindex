"""Store-level answers for every agent-readiness signal.
Figures are recomputed from data/latest.json, the crawl file the build reads.
Run after python3 scripts/build.py.
"""
import os, re, json, html, datetime, unittest
from collections import Counter, defaultdict
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST=os.path.join(ROOT,'dist'); DATA=os.path.join(ROOT,'data')
R=lambda p: open(os.path.join(DIST,p),encoding='utf-8').read()
def T(h): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',h))).strip()
def lds(h): return [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>',h,re.S)]
def faq_of(h): return [x for o in lds(h) for x in o.get('@graph',[o]) if x.get('@type')=='FAQPage'][0]
CONTENT_FLOOR='2026-11-10'
FILE_ORDER=('found','not_found','refused','error','robots_disallow','not_checked','missing')
MCP_ORDER=('found','not_found','refused','error','robots_disallow','not_checked','none_declared','missing')
PROD_ORDER=('full','partial','none','robots_disallow','not_checked','missing')
AF_ORDER=('found','not_found','refused','error','robots_disallow','not_checked','missing')
REFUSED_HTTP={401,403,429,451,503}
NOT_FOUND_HTTP={404,410}
PAGES={
 'acp':'signals/acp/index.html',
 'llms_txt':'signals/llms-txt/index.html',
 'agents_md':'signals/agents-md/index.html',
 'ai_catalog':'signals/ai-catalog/index.html',
 'mcp':'signals/mcp/index.html',
 'robots':'signals/ai-bots-robots/index.html',
 'access':'signals/bot-protection/index.html',
 'product':'signals/product-data/index.html',
 'agent':'signals/agent-cards/index.html',
}

def _best(states, order):
    have=set(states)
    for s in order:
        if s in have: return s
    return order[-1]
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
def _af_bucket(sites, keys):
    states=[]
    for s in sites:
        af=s.get('agent_files') or {}
        xs=[x for x in (_af_state(af.get(k)) for k in keys) if x!='recorded_elsewhere']
        if not xs: states.append('missing'); continue
        if 'found' in xs: states.append('found')
        elif all(x=='not_found' for x in xs): states.append('not_found')
        else:
            states.append(next((k for k in ('refused','error','robots_disallow','not_checked','missing') if k in xs), 'missing'))
    return _best(states, AF_ORDER) if states else 'missing'

def load():
    import sys
    sys.path.insert(0, os.path.join(ROOT,'scripts'))
    from nonshops import IDS
    D=json.load(open(os.path.join(DATA,'latest.json'),encoding='utf-8'))
    ret=[r for r in D['retailers'] if r['id'] not in IDS]
    sites=[s for s in D['sites'] if s.get('rid') not in IDS]
    return D, ret, sites

def facts(ret, sites):
    by=defaultdict(list); af=defaultdict(list)
    for s in sites:
        if (s.get('signals') or {}).get('checked'): by[s.get('rid')].append(s)
        if (s.get('agent_files') or {}).get('checked'): af[s.get('rid')].append(s)
    rows=[]
    for r in ret:
        sigs=by.get(r['id'], [])
        def files(key):
            if not sigs: return 'missing'
            return _best([_file_state(s.get('signals') or {}, key) for s in sigs], FILE_ORDER)
        mcp, mcp_http='missing', None
        if sigs:
            pairs=[]
            for s in sigs:
                sig=s.get('signals') or {}
                m=sig.get('mcp') if isinstance(sig.get('mcp'), dict) else {}
                pairs.append((_mcp_state(sig), m.get('http')))
            mcp=_best([p[0] for p in pairs], MCP_ORDER)
            mcp_http=next((h for k,h in pairs if k==mcp), None)
        readable=ai=content=wild=False
        for s in sigs:
            rb=(s.get('signals') or {}).get('robots')
            if not isinstance(rb, dict) or not rb.get('present'): continue
            readable=True
            if rb.get('specific'): ai=True
            if rb.get('content_signal'): content=True
            if rb.get('wildcard') in ('blocked','mostly_blocked'): wild=True
        homes=[]
        for s in sigs:
            h=(s.get('signals') or {}).get('home')
            if isinstance(h, dict) and h.get('state'): homes.append(h)
        if any(h.get('state')=='answered' for h in homes): access='answered'
        elif any(h.get('state')=='refused' for h in homes): access='refused'
        else: access='out'
        prod='missing'
        if sigs:
            prod=_best([((s.get('signals') or {}).get('product') or {}).get('state') or 'missing' for s in sigs], PROD_ORDER)
            prod=prod if prod in PROD_ORDER else 'missing'
        rows.append(dict(r=r, acp=files('acp'), ai_catalog=files('ai_catalog'), llms_txt=files('llms_txt'), agents_md=files('agents_md'),
                         mcp=mcp, mcp_http=mcp_http, robots=readable, robots_ai=ai, robots_content=content, robots_wild=wild,
                         access=access, challenge=bool(access=='refused' and any(h.get('challenge') for h in homes)),
                         vendors=set().union(*[set(h.get('vendors') or []) for h in homes]) if access in ('answered','refused') and homes else set(),
                         product=prod, poppy=_af_bucket(af.get(r['id'], []), ('poppy',)),
                         a2a=_af_bucket(af.get(r['id'], []), ('a2a_card','a2a_card_legacy')), segment=r.get('segment') or 'other',
                         ucp=r.get('status')=='ucp'))
    return rows

def share_of(rows, hit):
    found=checked=0; seg=defaultdict(lambda: Counter())
    for row in rows:
        b=hit(row)
        sk=row['segment']
        if b in ('found','not_found'):
            checked+=1; seg[sk]['checked']+=1
            if b=='found':
                found+=1; seg[sk]['found']+=1
        else:
            seg[sk]['couldnt']+=1
    return dict(found=found, checked=checked, couldnt=len(rows)-checked, seg=seg)

@unittest.skipUnless(os.path.exists(os.path.join(DIST,'signals','llms-txt','index.html')),'dist not built')
class SignalAnswers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.D, cls.ret, cls.sites=load()
        cls.rows=facts(cls.ret, cls.sites)
        x=datetime.date.fromisoformat(cls.D['crawl_date'])
        cls.long=f'{x.day} {x.strftime("%B")} {x.year}'
        cls.stamp=max(CONTENT_FLOOR, cls.D['crawl_date'])
        cls.counts={
            'acp':share_of(cls.rows, lambda r: 'found' if r['acp']=='found' else 'not_found' if r['acp']=='not_found' else 'out'),
            'ai_catalog':share_of(cls.rows, lambda r: 'found' if r['ai_catalog']=='found' else 'not_found' if r['ai_catalog']=='not_found' else 'out'),
            'llms_txt':share_of(cls.rows, lambda r: 'found' if r['llms_txt']=='found' else 'not_found' if r['llms_txt']=='not_found' else 'out'),
            'agents_md':share_of(cls.rows, lambda r: 'found' if r['agents_md']=='found' else 'not_found' if r['agents_md']=='not_found' else 'out'),
            'mcp_tools':share_of(cls.rows, lambda r: 'found' if r['mcp']=='found' else 'not_found' if r['mcp']=='not_found' else 'out'),
            'mcp_declared':share_of(cls.rows, lambda r: 'found' if r['mcp'] in ('found','not_found','refused','error') else 'not_found' if r['mcp']=='none_declared' else 'out'),
            'robots_ai':share_of(cls.rows, lambda r: 'found' if r['robots'] and r['robots_ai'] else 'not_found' if r['robots'] else 'out'),
            'robots_wild':share_of(cls.rows, lambda r: 'found' if r['robots'] and r['robots_wild'] else 'not_found' if r['robots'] else 'out'),
            'content_signal':share_of(cls.rows, lambda r: 'found' if r['robots'] and r['robots_content'] else 'not_found' if r['robots'] else 'out'),
            'access':share_of(cls.rows, lambda r: 'found' if r['access']=='refused' else 'not_found' if r['access']=='answered' else 'out'),
            'product':share_of(cls.rows, lambda r: 'found' if r['product'] in ('full','partial') else 'not_found' if r['product']=='none' else 'out'),
            'poppy':share_of(cls.rows, lambda r: 'found' if r['poppy']=='found' else 'not_found' if r['poppy']=='not_found' else 'out'),
            'a2a':share_of(cls.rows, lambda r: 'found' if r['a2a']=='found' else 'not_found' if r['a2a']=='not_found' else 'out'),
        }
        st=Counter(r['status'] for r in cls.ret)
        cls.counts['ucp']=dict(found=st['ucp'], checked=st['ucp']+st['no_ucp'])

    def sentence(self, found, checked, verb, verb_one):
        word=verb_one if found==1 and verb_one else verb
        share=f'{(100*found/checked):.1f}%'
        return f'In the ShopBot Index crawl of {self.long}, {found:,} of {checked:,} stores we could check {word} ({share}).'

    def test_crawl_file_is_9_november_2026(self):
        raw=json.load(open(os.path.join(DATA,'crawl-2026-11-09.json'),encoding='utf-8'))
        self.assertEqual(raw['crawl_date'], '2026-11-09')
        self.assertEqual(self.D['crawl_date'], '2026-11-09')
        self.assertEqual(len(raw['retailers']), len(self.ret))

    def test_found_matches_the_beyond_ucp_store_counts(self):
        rep=json.load(open(os.path.join(DATA,'beyond-ucp-latest.json'),encoding='utf-8'))
        by={s['key']:s['store_count'] for s in rep['signals']}
        for key in ('acp','ai_catalog','llms_txt','agents_md','mcp_tools','robots_ai','product','poppy','a2a'):
            self.assertEqual(self.counts[key]['found'], by[key], key)
        self.assertEqual(self.counts['content_signal']['found'], by['content_signals'])

    def test_mcp_endpoint_matches_the_retailer_rollup(self):
        dec=sum(1 for r in self.ret if (r.get('signals') or {}).get('checked') and ((r.get('signals') or {}).get('mcp') or {}).get('state') in ('answered','no_tools'))
        self.assertEqual(self.counts['mcp_declared']['found'], dec)

    def test_pages_quote_the_computed_figures(self):
        verbs={
            'acp':('publish an Agentic Commerce Protocol (ACP) discovery file','publishes an Agentic Commerce Protocol (ACP) discovery file', PAGES['acp']),
            'llms_txt':('publish an llms.txt file','publishes an llms.txt file', PAGES['llms_txt']),
            'agents_md':('publish an AGENTS.md file','publishes an AGENTS.md file', PAGES['agents_md']),
            'ai_catalog':('publish an AI catalog','publishes an AI catalog', PAGES['ai_catalog']),
            'mcp_declared':('name an MCP endpoint in their UCP profile','names an MCP endpoint in their UCP profile', PAGES['mcp']),
            'robots_ai':('have robots.txt rules that name an AI crawler','has robots.txt rules that name an AI crawler', PAGES['robots']),
            'robots_wild':('have a wildcard robots.txt rule that disallows the whole site','has a wildcard robots.txt rule that disallows the whole site', PAGES['robots']),
            'content_signal':('publish a Content-Signal line in robots.txt','publishes a Content-Signal line in robots.txt', PAGES['robots']),
            'access':('had bot protection that refused our crawler','had bot protection that refused our crawler', PAGES['access']),
            'product':('have schema.org Product markup on a product page we fetched','has schema.org Product markup on a product page we fetched', PAGES['product']),
            'poppy':('publish a valid Poppy file','publishes a valid Poppy file', PAGES['agent']),
            'a2a':('publish a valid A2A agent card','publishes a valid A2A agent card', PAGES['agent']),
            'ucp':('publish a UCP profile','publishes a UCP profile','index.html'),
        }
        home=R('index.html'); signals=R('signals.html'); llms=R('llms.txt'); full=R('llms-full.txt'); sm=R('sitemap.xml')
        for key,(verb,verb_one,path) in verbs.items():
            c=self.counts[key]
            sent=self.sentence(c['found'], c['checked'], verb, verb_one)
            h=R(path)
            self.assertIn(sent, T(h), key)
            self.assertIn(sent, T(home), key)
            self.assertIn(sent, T(signals), key)
            self.assertIn(sent, llms, key)
            self.assertIn(sent, full, key)
            self.assertLess(os.path.getsize(os.path.join(DIST, path)), 1_000_000, path)
        self.assertIn('does not test purchases', T(home))
        self.assertIn('publish a UCP profile', T(home))
        self.assertNotRegex(T(re.search(r'id="agent-readiness">(.*?)</div>', home, re.S).group(1)), r'[—–]')

    def test_mcp_lead_opens_with_the_declared_endpoint(self):
        declared=self.sentence(self.counts['mcp_declared']['found'], self.counts['mcp_declared']['checked'],
                               'name an MCP endpoint in their UCP profile', 'names an MCP endpoint in their UCP profile')
        n=self.counts['mcp_tools']['found']
        n422=sum(1 for row in self.rows if row['mcp']=='error' and row['mcp_http']==422)
        nref=sum(1 for row in self.rows if row['mcp']=='refused')
        follow=f'Only {n:,} endpoints returned a tools list when queried ({n422:,} returned HTTP 422, {nref:,} refused).'
        old=f'{n:,} of {self.counts["mcp_tools"]["checked"]:,} stores we could check return a tools list'
        home=T(re.search(r'id="agent-readiness">(.*?)</div>', R('index.html'), re.S).group(1))
        signals=T(re.search(r'id="agent-readiness">(.*?)</div>', R('signals.html'), re.S).group(1))
        lead=T(re.search(r'<p class="lede" id="answer">(.*?)</p>', R(PAGES['mcp']), re.S).group(1))
        llms=R('llms.txt'); full=R('llms-full.txt')
        ready=llms[llms.index('## AI agent readiness'):llms.index('## Key pages')]
        ready_full=full[full.index('## AI agent readiness'):full.index('## Results by segment')]
        for text in (home, signals, lead, ready, ready_full):
            self.assertTrue(text.startswith(declared) or declared in text)
            self.assertLess(text.index(declared), text.index(follow))
            self.assertNotIn(old, text)
            self.assertNotIn('8 of 8', text)
        self.assertTrue(lead.startswith(declared))
        page=R(PAGES['mcp'])
        self.assertNotIn(old, page)
        self.assertNotIn('8 of 8', page)
        self.assertNotIn('(100.0%)', re.search(r'id="tools">.*$', page, re.S).group(0))
        self.assertIn('id="tools"', page)
        self.assertLess(page.index('id="answer"'), page.index('id="tools"'))

    def test_faq_jsonld_matches_the_visible_answer(self):
        sm=R('sitemap.xml')
        for path in PAGES.values():
            h=R(path)
            lead=T(re.search(r'<p class="lede" id="answer">(.*?)</p>', h, re.S).group(1))
            self._faq_matches(h)
            self.assertEqual(faq_of(h)['mainEntity'][0]['acceptedAnswer']['text'], lead)
            graph=lds(h)[0]['@graph']
            ds=[x for x in graph if x.get('@type')=='Dataset'][0]
            page=[x for x in graph if x.get('@type')=='WebPage'][0]
            self.assertEqual(ds['description'], lead)
            self.assertEqual(ds['dateModified'], self.stamp)
            self.assertEqual(page['dateModified'], self.stamp)
            loc='https://shopbotindex.com/'+path.replace('index.html','')
            self.assertIn(f'<loc>{loc}</loc><lastmod>{self.stamp}</lastmod>', sm)
            # the answer is in the HTML, not only inside the JSON-LD script
            body=re.sub(r'<script.*?</script>','',h,flags=re.S)
            self.assertIn(lead, T(body))
            self.assertEqual(len(re.findall(r'<h1[ >]', h)), 1)
            self.assertNotRegex(lead, r'[—–]')
            for bad in ('PrimeLogic','Stathopoulos','Switzerland'): self.assertNotIn(bad, lead)
            self.assertNotIn('official', lead.lower())
            self.assertIn('does not test purchases', lead)

    def test_overview_faq_on_home_and_signals(self):
        for path in ('index.html','signals.html'):
            h=R(path)
            block=T(re.search(r'id="agent-readiness">(.*?)</div>', h, re.S).group(1))
            self._faq_matches(h)
            got=[q for q in faq_of(h)['mainEntity'] if q['name'].startswith('What did the')][0]
            self.assertEqual(got['acceptedAnswer']['text'], block)
            ds=[x for o in lds(h) for x in o.get('@graph',[o]) if x.get('@type')=='Dataset' and x.get('name','').startswith('AI agent readiness')]
            if path=='signals.html':
                self.assertEqual(ds[0]['description'], block)
                self.assertEqual(ds[0]['dateModified'], self.stamp)
                page=[x for o in lds(h) for x in o.get('@graph',[o]) if x.get('@type')=='WebPage'][0]
                self.assertEqual(page['dateModified'], self.stamp)
                self.assertIn(f'<loc>https://shopbotindex.com/signals.html</loc><lastmod>{self.stamp}</lastmod>', R('sitemap.xml'))

    def test_segment_rows_match_the_crawl(self):
        h=R(PAGES['llms_txt'])
        seg=self.counts['llms_txt']['seg']
        for k,label in (('shopify','Shopify stores'),('big','Big retailers'),('other','Other retailers &amp; marketplaces')):
            row=re.search(rf'<tr data-seg="{k}">(.*?)</tr>', h, re.S).group(1)
            cells=re.findall(r'<td>(.*?)</td>', row)
            self.assertEqual(cells[0], label)
            self.assertEqual(cells[1], f'{seg[k]["found"]:,}')
            self.assertEqual(cells[2], f'{seg[k]["checked"]:,}')
            self.assertEqual(cells[4], f'{seg[k]["couldnt"]:,}')

    def test_named_examples_are_the_stores_that_met_the_check(self):
        import sys
        sys.path.insert(0, os.path.join(ROOT,'scripts'))
        slugs=json.load(open(os.path.join(DATA,'slugs-latest.json'),encoding='utf-8'))
        h=R(PAGES['acp'])
        hits=[row['r'] for row in self.rows if row['acp']=='found']
        box=re.search(r'<div id="examples">(.*?)</div>', h, re.S).group(1)
        self.assertEqual(len(hits), 1)
        self.assertIn(html.escape(hits[0]['name']), box)
        self.assertIn(f'href="../../store/{slugs[hits[0]["id"]][0]}.html"', box)
        # every llms.txt store is named, big retailers first
        h=R(PAGES['llms_txt'])
        box=re.search(r'<div id="examples">(.*?)</div>', h, re.S).group(1)
        names=re.findall(r'<li>(?:<a[^>]*>)?([^<]+)', box)
        want=sorted([row['r'] for row in self.rows if row['llms_txt']=='found'], key=lambda r: (0 if r.get('segment')=='big' else 1, (r.get('name') or '').lower(), r.get('id') or ''))
        self.assertEqual([html.unescape(n) for n in names], [r.get('name') or r['id'] for r in want])
        bigs=[r for r in want if r.get('segment')=='big']
        if bigs:
            self.assertEqual(html.unescape(names[0]), bigs[0].get('name') or bigs[0]['id'])

    def test_platform_table_only_counts_stores_with_a_ucp_profile(self):
        h=R(PAGES['llms_txt'])
        self.assertIn('We can name a platform only for a store that publishes a UCP profile.', h)
        checked=self.counts['llms_txt']['checked']
        in_table=0
        for row in re.findall(r'<tr data-platform="(.*?)">(.*?)</tr>', h, re.S):
            cells=re.findall(r'<td>(.*?)</td>', row[1])
            in_table+=int(cells[2].replace(',',''))
        no_profile=sum(1 for row in self.rows if row['llms_txt'] in ('found','not_found') and not row['ucp'])
        self.assertEqual(in_table, checked-no_profile)
        self.assertIn(f'{no_profile:,} of {checked:,} stores we could check do not publish a UCP profile', h)

    def test_product_split_and_access_vendors(self):
        full=sum(1 for row in self.rows if row['product']=='full')
        partial=sum(1 for row in self.rows if row['product']=='partial')
        def nv(n, one, many): return f'1 {one}' if n==1 else f'{n:,} {many}'
        h=T(R(PAGES['product']))
        self.assertIn(nv(full, 'includes price, currency and availability', 'include price, currency and availability'), h)
        self.assertIn(nv(partial, 'has Product markup without all three', 'have Product markup without all three'), h)
        chal=sum(1 for row in self.rows if row['challenge'])
        acc=self.counts['access']
        h=T(R(PAGES['access']))
        if chal==1: phrase=f'1 of the {acc["found"]:,} refusals was a challenge page'
        else: phrase=f'{chal:,} of the {acc["found"]:,} refusals were a challenge page'
        self.assertIn(phrase, h)
        for key,label in (('cloudflare','Cloudflare'),('akamai','Akamai'),('datadome','DataDome'),('human','HUMAN'),('imperva','Imperva')):
            n=sum(1 for row in self.rows if key in row['vendors'])
            self.assertIn(f'{label} {n:,}', h)

    def test_how_we_check_is_on_the_page(self):
        self.assertIn('/.well-known/acp.json', R(PAGES['acp']))
        self.assertIn('protocol.name', R(PAGES['acp']))
        self.assertIn('/llms.txt', R(PAGES['llms_txt']))
        self.assertIn('/agents.md', R(PAGES['agents_md']))
        self.assertIn('ai-catalog.json', R(PAGES['ai_catalog']))
        self.assertIn('tools/list', R(PAGES['mcp']))
        self.assertIn('ChatGPT-User', R(PAGES['robots']))
        self.assertIn('Content-Signal', R(PAGES['robots']))
        self.assertIn('cf-mitigated', R(PAGES['access']))
        self.assertIn('schema.org/Product', R(PAGES['product']))
        self.assertIn('poppy.json', R(PAGES['agent']))
        self.assertIn('agent-card.json', R(PAGES['agent']))

    def _faq_matches(self, h):
        box=re.search(r'<div class="box faq" id="faq">(.*?)</div>', h, re.S).group(1)
        vis=T(box)
        for q in faq_of(h)['mainEntity']:
            self.assertIn(q['name'], vis)
            self.assertIn(q['acceptedAnswer']['text'], vis)
            self.assertNotRegex(q['name']+' '+q['acceptedAnswer']['text'], r'[—–]')

if __name__=='__main__':
    unittest.main()
