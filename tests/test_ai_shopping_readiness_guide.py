"""The 11 November 2026 guide keeps the approved AI shopping readiness copy.

Every figure is recomputed from data/crawl-2026-11-09.json. A mismatch fails
the test. Do not edit the approved article to make a figure pass.

Run after python3 scripts/build.py.
"""
import os, re, json, html, unittest
from collections import Counter, defaultdict
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST=os.path.join(ROOT,'dist')
SRC=os.path.join(ROOT,'content','guides','ai-shopping-readiness.md')
PAGE='guides/ai-shopping-readiness/index.html'
URL='https://shopbotindex.com/guides/ai-shopping-readiness/'
TITLE='AI shopping readiness: what agents check on a store'
DESC='What AI shopping agents can read on a store, beyond UCP: llms.txt, ACP, MCP, robots.txt AI rules, product markup and payment handlers. 9 November 2026 crawl.'
R=lambda p: open(os.path.join(DIST,p),encoding='utf-8').read()
FILE_ORDER=('found','not_found','refused','error','robots_disallow','not_checked','missing')
MCP_ORDER=('found','not_found','refused','error','robots_disallow','not_checked','none_declared','missing')
PROD_ORDER=('full','partial','none','robots_disallow','not_checked','missing')
RANK={'blocked':4,'mostly_blocked':3,'restricted':2,'allowed':1}
WHOLE={'blocked','mostly_blocked'}
RECORDED=('GPTBot','ClaudeBot','Google-Extended','PerplexityBot','OAI-SearchBot','ChatGPT-User','Claude-User','Perplexity-User','Claude-SearchBot','Google-Agent')
WORDS={1:'One',2:'Two',3:'Three',4:'Four',5:'Five',6:'Six',7:'Seven',8:'Eight',9:'Nine',10:'Ten'}

def _lds(h):
    return [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>',h,re.S)]

def _txt(s):
    return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',s))).strip()

def comma(n): return f'{n:,}'
def pct(a,b): return f'{(100*a/b):.1f}%'
def best(states, order):
    have=set(states)
    for o in order:
        if o in have: return o
    return 'missing'

def _md_lines(md):
    lines=[]
    for line in md.splitlines():
        if line.startswith('### '): line=line[4:]
        elif line.startswith('## '): line=line[3:]
        elif line.startswith('# '): line=line[2:]
        elif line.startswith('- '): line=line[2:]
        elif re.match(r'^\d+\. ', line): line=re.sub(r'^\d+\. ','', line)
        line=re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',line).replace('`','').replace('**','')
        if line.strip(): lines.append(line.strip())
    return lines

def _article_lines(page):
    art=re.search(r'<article class="prose">(.*)</article>',page,re.S).group(1)
    art=re.sub(r'<p class="muted crumbs">.*?</p>','',art,count=1,flags=re.S)
    art=re.sub(r'<p class="muted" id="published">.*?</p>','',art,count=1,flags=re.S)
    lines=[]
    for part in re.split(r'</(?:p|h1|h2|h3|li)>',art):
        part=_txt(part)
        if part: lines.append(part)
    return lines

def _visible_faq(page):
    art=re.search(r'<article class="prose">(.*)</article>',page,re.S).group(1)
    parts=re.split(r'<h3>(.*?)</h3>',art)
    pairs=[]
    it=iter(parts[1:])
    for q, body in zip(it, it):
        paras=re.findall(r'<p[^>]*>(.*?)</p>', body, re.S)
        pairs.append((_txt(q), _txt(' '.join(paras))))
    return pairs

def _mstate(m):
    st=m.get('state'); http=m.get('http')
    if st=='answered': return 'found'
    if st=='no_tools':
        if http in (200,404,410): return 'not_found'
        if http in (401,403,429,451,503): return 'refused'
        return 'error'
    return st or 'missing'

class AiShoppingReadinessGuide(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sys
        sys.path.insert(0, os.path.join(ROOT,'scripts'))
        from nonshops import IDS
        D=json.load(open(os.path.join(ROOT,'data','crawl-2026-11-09.json'),encoding='utf-8'))
        cls.crawl_date=D['crawl_date']
        R=[r for r in D['retailers'] if r['id'] not in IDS]
        S=[s for s in D['sites'] if s.get('rid') not in IDS]
        by=defaultdict(list)
        for s in S:
            if (s.get('signals') or {}).get('checked'): by[s['rid']].append(s)
        cls.n=len(R)
        st=Counter(r['status'] for r in R)
        cls.ucp=st['ucp']; cls.checked=st['ucp']+st['no_ucp']
        cls.seg={}
        for seg in ('shopify','big'):
            s2=Counter(r['status'] for r in R if r['segment']==seg)
            cls.seg[seg]=(s2['ucp'], s2['ucp']+s2['no_ucp'])
        U=[r for r in R if r['status']=='ucp']
        cls.checkout=sum(1 for r in U if 'dev.ucp.shopping.checkout' in (r.get('capabilities') or []))
        cls.ph=Counter(p for r in U for p in set(r.get('payment_handlers') or []))
        cls.ph_any=sum(1 for r in U if r.get('payment_handlers'))
        cls.ph_none=sum(1 for r in U if not r.get('payment_handlers'))
        def filestat(key):
            c=Counter()
            for r in R:
                ss=by.get(r['id'],[])
                c[best({(s['signals'].get(key) or {}).get('state') for s in ss}, FILE_ORDER) if ss else 'missing']+=1
            return c
        cls.files={k:filestat(k) for k in ('acp','llms_txt','agents_md','ai_catalog')}
        cls.acp_domain=None
        for r in R:
            for s in by.get(r['id'],[]):
                if (s['signals'].get('acp') or {}).get('state')=='found':
                    cls.acp_domain=s.get('domain') or s.get('host') or r['name']
        big=[]
        for r in R:
            if r['segment']!='big': continue
            ss=by.get(r['id'],[])
            stt=best({(s['signals'].get('llms_txt') or {}).get('state') for s in ss}, FILE_ORDER) if ss else 'missing'
            if stt=='found': big.append(r['name'])
        cls.big_llms=big
        mc=Counter(); http=Counter(); answered=[]
        for r in R:
            ss=by.get(r['id'],[])
            if not ss:
                mc['missing']+=1; continue
            ps=[]
            for s in ss:
                m=s['signals'].get('mcp') or {}
                ps.append((_mstate(m), m.get('http'), s))
            b=best({p[0] for p in ps}, MCP_ORDER); mc[b]+=1
            if b in ('not_found','refused','error'):
                http[(b, next(h for k,h,s in ps if k==b))]+=1
            if b=='found':
                answered.append([s for k,h,s in ps if k=='found'])
        cls.mc=mc; cls.http=http; cls.answered=answered
        cls.mcp_named=mc['found']+mc['not_found']+mc['refused']+mc['error']
        cls.mcp_denom=cls.mcp_named+mc['none_declared']
        rd=ai=cs=wild=0; gpt=Counter(); specs={}
        for r in R:
            ss=by.get(r['id'],[]); read=False; a=c=w=False; spec={}
            for s in ss:
                rb=s['signals'].get('robots') or {}
                if not rb.get('present'): continue
                read=True; a|=bool(rb.get('specific')); c|=bool(rb.get('content_signal')); w|=rb.get('wildcard') in WHOLE
                for t,v in (rb.get('specific') or {}).items():
                    if RANK.get(v,0)>RANK.get(spec.get(t),0): spec[t]=v
            if read:
                rd+=1; ai+=int(a); cs+=int(c); wild+=int(w); gpt[spec.get('GPTBot','not named')]+=1
                if r['name'] in ('Amazon','EBay','Walmart'): specs[r['name']]=spec
        cls.readable=rd; cls.ai=ai; cls.cs=cs; cls.wild=wild; cls.gpt=gpt; cls.specs=specs
        cls.bot=Counter()
        for r in R:
            if '_spec' in r: continue
            ss=by.get(r['id'],[])
            if not any((s['signals'].get('robots') or {}).get('present') for s in ss): continue
            spec={}
            for s in ss:
                rb=s['signals'].get('robots') or {}
                if not rb.get('present'): continue
                for t,v in (rb.get('specific') or {}).items():
                    if RANK.get(v,0)>RANK.get(spec.get(t),0): spec[t]=v
            r['_spec']=spec
        cls.whole={}
        for token in ('ClaudeBot','Google-Extended','ChatGPT-User','PerplexityBot'):
            c=Counter((r.get('_spec') or {}).get(token,'not named') for r in R if '_spec' in r)
            cls.whole[token]=c['blocked']+c['mostly_blocked']
        pc=Counter()
        for r in R:
            ss=by.get(r['id'],[])
            pc[best({(s['signals'].get('product') or {}).get('state') for s in ss}, PROD_ORDER) if ss else 'missing']+=1
        cls.pc=pc
        ac=Counter()
        for r in R:
            hs=[(s['signals'].get('home') or {}).get('state') for s in by.get(r['id'],[])]
            ac['answered' if 'answered' in hs else 'refused' if 'refused' in hs else 'out']+=1
        cls.ac=ac

    def need(self, fragment):
        text=_txt(re.search(r'<article class="prose">(.*)</article>', R(PAGE), re.S).group(1))
        self.assertIn(fragment, text, 'Computed figure is not in the approved copy. Stop and report it; do not change the article text. Missing: '+fragment)

    def test_page_keeps_the_approved_words(self):
        path=os.path.join(DIST, PAGE)
        self.assertTrue(os.path.isfile(path), PAGE)
        h=R(PAGE)
        src=open(SRC,encoding='utf-8').read()
        self.assertEqual(_article_lines(h), _md_lines(src))
        self.assertIn(f'<h1>{TITLE}</h1>', h)
        self.assertIn(f'<title>{TITLE} | ShopBot Index</title>', h)
        self.assertIn(f'<link rel="canonical" href="{URL}">', h)
        self.assertIn(f'<meta name="description" content="{html.escape(DESC, quote=True)}">', h)
        self.assertIn('href="../../style.css"', h)
        self.assertIn('href="../../guides/">Guides</a>', h)
        self.assertIn('hello@shopbotindex.com', h)
        self.assertIn('<ol><li>Look up your domain on <a href="https://shopbotindex.com/check.html">Check your store</a>', h)
        self.assertIn('<strong>Amazon</strong>', h)
        self.assertIn("<strong>Walmart</strong>'s robots.txt", h)
        text=_txt(re.search(r'<article class="prose">(.*)</article>', h, re.S).group(1))
        self.assertNotRegex(text, r'[—–]')
        self.assertNotIn('100%', text)
        low=text.lower()
        for bad in ('official','mandatory'):
            self.assertNotIn(bad, low)
        self.assertNotRegex(low, r'\bverified\b')
        for bad in ('PrimeLogic','Stathopoulos','Switzerland'):
            self.assertNotIn(bad, h)
            self.assertNotIn(bad, src)

    def test_faq_jsonld_matches_visible_text(self):
        h=R(PAGE)
        visible=_visible_faq(h)
        self.assertEqual(len(visible), 6)
        graph=_lds(h)[0]['@graph']
        faq=[x for x in graph if x.get('@type')=='FAQPage']
        self.assertEqual(len(faq), 1)
        got=[(q['name'], q['acceptedAnswer']['text']) for q in faq[0]['mainEntity']]
        self.assertEqual(got, visible)
        for q, a in got:
            self.assertIn(f'<h3>{q}</h3>', h)
            self.assertIn(f'<p>{a}</p>', h)
            self.assertNotRegex(q+' '+a, r'[—–]')
        art=[x for x in graph if x.get('@type')=='Article'][0]
        self.assertEqual(art['headline'], TITLE)
        self.assertEqual(art['description'], DESC)
        self.assertEqual(art['datePublished'], '2026-11-11')
        self.assertEqual(art['dateModified'], '2026-11-11')
        self.assertEqual(art['mainEntityOfPage']['@id'], URL)
        self.assertIn('<time datetime="2026-11-11">11 November 2026</time>', h)
        self.assertIn('<time datetime="2026-11-11" id="modified">11 November 2026</time>', h)
        self.assertNotIn('"@type": "Person"', json.dumps(graph))

    def test_internal_links_and_discovery(self):
        art=re.search(r'<article class="prose">(.*)</article>', R(PAGE), re.S).group(1)
        hrefs=set(re.findall(r'href="([^"]+)"', art))
        for url in (
            'https://shopbotindex.com/guides/what-is-a-ucp-profile/',
            'https://shopbotindex.com/which-stores-declare-ucp-checkout/',
            'https://shopbotindex.com/signals/acp/',
            'https://shopbotindex.com/signals/llms-txt/',
            'https://shopbotindex.com/signals/mcp/',
            'https://shopbotindex.com/signals/ai-bots-robots/',
            'https://shopbotindex.com/signals/product-data/',
            'https://shopbotindex.com/signals/bot-protection/',
            'https://shopbotindex.com/payment-handlers/',
            'https://shopbotindex.com/check.html',
            'https://shopbotindex.com/guides/businesses-in-chatgpt/',
        ):
            self.assertIn(url, hrefs, url)
        sm=R('sitemap.xml')
        self.assertEqual(sm.count('ai-shopping-readiness'), 1)
        self.assertIn(f'<loc>{URL}</loc><lastmod>2026-11-11</lastmod>', sm)
        self.assertNotIn('guides/ai-shopping-readiness.html', sm)
        self.assertNotIn('guides/ai-shopping-readiness/index.html', sm)
        hub=R('guides/index.html')
        self.assertIn(f'href="ai-shopping-readiness/">{html.escape(TITLE)}</a>', hub)
        self.assertIn(html.escape(DESC, quote=True), hub)
        line=f'- [{TITLE}]({URL}): {DESC}'
        self.assertIn(line, R('llms.txt'))
        self.assertIn(line, R('llms-full.txt'))

    def test_every_figure_matches_the_9_november_crawl(self):
        self.assertEqual(self.crawl_date, '2026-11-09')
        self.need(f'We track {comma(self.n)} stores.')
        self.need(f'{comma(self.ucp)} of {comma(self.checked)} stores we could check publish a UCP profile ({pct(self.ucp, self.checked)})')
        sh, shc=self.seg['shopify']; bg, bgc=self.seg['big']
        self.need(f'That includes {comma(sh)} of {comma(shc)} Shopify stores ({pct(sh, shc)}) and {comma(bg)} of {comma(bgc)} big retailers ({pct(bg, bgc)}).')
        self.need(f'{comma(self.checkout)} of the {comma(self.ucp)} declare checkout.')
        acp=self.files['acp']
        acp_found, acp_checked=acp['found'], acp['found']+acp['not_found']
        left=self.n-acp_checked
        self.need(f'{comma(acp_found)} of {comma(acp_checked)} stores we could check publishes one ({pct(acp_found, acp_checked)}): {self.acp_domain}.')
        self.need(f'{comma(left)} stores were left out, {comma(acp["refused"])} of them because the request was refused.')
        ll=self.files['llms_txt']
        self.need(f'{comma(ll["found"])} of {comma(ll["found"]+ll["not_found"])} stores we could check publish one ({pct(ll["found"], ll["found"]+ll["not_found"])})')
        self.need(f'including {len(self.big_llms)} big retailers such as Etsy, Target Corporation, Zalando and Shein.')
        for name in ('Etsy','Target Corporation','Zalando','Shein'):
            self.assertIn(name, self.big_llms, name)
        ag=self.files['agents_md']; cat=self.files['ai_catalog']
        self.need(f'{comma(ag["found"])} of {comma(ag["found"]+ag["not_found"])} stores ({pct(ag["found"], ag["found"]+ag["not_found"])})')
        self.need(f'{comma(cat["found"])} of {comma(cat["found"]+cat["not_found"])} stores ({pct(cat["found"], cat["found"]+cat["not_found"])})')
        self.need(f'{comma(self.mcp_named)} of {comma(self.mcp_denom)} stores we could check name an MCP endpoint in their UCP profile ({pct(self.mcp_named, self.mcp_denom)})')
        self.need(f'Only {self.mc["found"]} of those {comma(self.mcp_named)} endpoints returned a tools list when we asked.')
        http422=self.http[('error',422)]
        other=self.mc['error']-http422
        self.need(f'{http422} answered with HTTP 422 and no tools list, {self.mc["refused"]} refused, and {other} gave other errors.')
        wix=0; names=set()
        for sites in self.answered:
            endpoints=[]
            for s in sites:
                m=s['signals'].get('mcp') or {}
                endpoints.append(m.get('endpoint') or '')
                names.update(m.get('tools') or [])
            if any('wixapis.com' in e for e in endpoints): wix+=1
        self.assertIn(wix, WORDS)
        self.assertIn(self.mc['found'], WORDS)
        self.need(f'{WORDS[wix]} of the {WORDS[self.mc["found"]].lower()} that returned tools are Wix endpoints')
        self.assertTrue(any('search' in t and 'catalog' in t for t in names), sorted(names))
        self.assertTrue(any('product' in t for t in names), sorted(names))
        self.assertTrue(any('checkout' in t for t in names), sorted(names))
        self.need('the tools listed include catalog search, product lookup and checkout steps')
        self.need(f'{comma(self.ai)} of {comma(self.readable)} stores whose robots.txt we could read have rules that name an AI crawler ({pct(self.ai, self.readable)})')
        gpt_whole=self.gpt['blocked']+self.gpt['mostly_blocked']
        self.need(f'{comma(gpt_whole)} of the {comma(self.readable)} disallow the whole site for GPTBot ({pct(gpt_whole, self.readable)}), counting {self.gpt["mostly_blocked"]} that allow some paths back.')
        self.need(f'ClaudeBot at {self.whole["ClaudeBot"]} stores, Google-Extended at {self.whole["Google-Extended"]}, ChatGPT-User at {self.whole["ChatGPT-User"]} and PerplexityBot at {self.whole["PerplexityBot"]}.')
        self.need(f'{self.wild} stores have a wildcard rule that disallows the whole site for every crawler, and {self.cs} publish a Content-Signal line ({pct(self.cs, self.readable)}).')
        amazon=('GPTBot','ChatGPT-User','OAI-SearchBot','ClaudeBot','Claude-User','Claude-SearchBot','PerplexityBot','Perplexity-User','Google-Extended')
        for token in amazon:
            self.assertEqual(self.specs['Amazon'].get(token), 'blocked', token)
        for token in ('GPTBot','ClaudeBot','PerplexityBot'):
            self.assertEqual(self.specs['EBay'].get(token), 'mostly_blocked', token)
        for token in ('ChatGPT-User','OAI-SearchBot','Claude-User','Claude-SearchBot'):
            self.assertEqual(self.specs['EBay'].get(token), 'restricted', token)
        for token in RECORDED:
            self.assertNotIn(token, self.specs['Walmart'], token)
        found=self.pc['full']+self.pc['partial']; checked=found+self.pc['none']
        self.need(f'{comma(found)} of {comma(checked)} stores we could check have Product markup on the product page we fetched ({pct(found, checked)})')
        self.need(f'{comma(self.pc["full"])} of them include price, currency and availability')
        self.need(f'We could not reach a product page for {comma(self.n-checked)} stores')
        self.need(f'{comma(self.ph["com.google.pay"])} declare Google Pay')
        self.need(f'{comma(self.ph["dev.shopify.shop_pay"])} declare Shop Pay')
        self.need(f'{comma(self.ph["dev.shopify.card"])} declare the Shopify card handler')
        klarna=self.ph['com.klarna.payments']
        self.need(f'{comma(klarna)} {"declares" if klarna==1 else "declare"} Klarna')
        self.need(f'{comma(self.ph_any)} declare at least one handler and {comma(self.ph_none)} declare none.')
        access=self.ac['answered']+self.ac['refused']
        self.need(f'{comma(self.ac["refused"])} of {comma(access)} stores we could check had bot protection that refused our crawler ({pct(self.ac["refused"], access)}).')
