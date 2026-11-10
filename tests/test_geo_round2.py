"""GEO round 2 headlines are recomputed from the 9 November 2026 crawl.

Run after python3 scripts/build.py. Every count below is derived from
data/crawl-2026-11-09.json, the same file the build reads as data/latest.json.
"""
import os, re, json, html, datetime, unittest
from collections import Counter, defaultdict
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST=os.path.join(ROOT,'dist'); DATA=os.path.join(ROOT,'data')
R=lambda p: open(os.path.join(DIST,p),encoding='utf-8').read()
def T(h): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',h))).strip()
def lds(h): return [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>',h,re.S)]
def sentences(text): return re.findall(r'\.(?=\s|$)', text)
STAMP='2026-11-11'
WHOLE={'blocked','mostly_blocked'}
RANK={'blocked':4,'mostly_blocked':3,'restricted':2,'allowed':1}
PH={'com.google.pay':'Google Pay','dev.shopify.shop_pay':'Shop Pay','dev.shopify.card':'the Shopify card handler','com.klarna.payments':'Klarna'}

def _best_bots(sites):
    spec={}
    readable=False
    for s in sites:
        rb=(s.get('signals') or {}).get('robots')
        if not isinstance(rb, dict) or not rb.get('present'): continue
        readable=True
        sp=rb.get('specific') or {}
        if not isinstance(sp, dict): continue
        for t,st in sp.items():
            if t not in spec or RANK.get(st,0)>RANK.get(spec[t],0):
                spec[t]=st
    return readable, spec

@unittest.skipUnless(os.path.exists(os.path.join(DIST,'which-stores-declare-ucp-checkout','index.html')),'dist not built')
class GeoRound2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sys
        sys.path.insert(0, os.path.join(ROOT,'scripts'))
        from nonshops import IDS
        cls.D=json.load(open(os.path.join(DATA,'crawl-2026-11-09.json'),encoding='utf-8'))
        latest=json.load(open(os.path.join(DATA,'latest.json'),encoding='utf-8'))
        if latest['crawl_date']!=cls.D['crawl_date']:
            raise AssertionError('data/latest.json is not the 9 November 2026 crawl')
        cls.ret=[r for r in cls.D['retailers'] if r['id'] not in IDS]
        by=defaultdict(list)
        for s in cls.D['sites']:
            if (s.get('signals') or {}).get('checked'): by[s.get('rid')].append(s)
        cls.by=by
        ucp=[r for r in cls.ret if r['status']=='ucp']
        cls.ucp=ucp
        cls.co=sorted((r for r in ucp if 'dev.ucp.shopping.checkout' in (r.get('capabilities') or [])),
                      key=lambda r: (0 if r.get('segment')=='big' else 1, (r.get('name') or '').lower(), r.get('id') or ''))
        cls.noco=sorted((r for r in ucp if 'dev.ucp.shopping.checkout' not in (r.get('capabilities') or [])), key=lambda r: (r.get('name') or '').lower())
        cls.ph=Counter()
        cls.combos=Counter()
        for r in ucp:
            handlers=tuple(sorted(r.get('payment_handlers') or []))
            cls.combos[handlers]+=1
            for p in handlers: cls.ph[p]+=1
        cls.readable=0; cls.gpt=[]; cls.blockers=[]
        cls.named={}
        for r in cls.ret:
            readable, spec=_best_bots(by.get(r['id'], []))
            if not readable: continue
            cls.readable+=1
            whole={t:st for t,st in spec.items() if st in WHOLE}
            if spec.get('GPTBot') in WHOLE: cls.gpt.append(r)
            if whole: cls.blockers.append(r)
            if r['name'] in ('Amazon','EBay','Walmart'): cls.named[r['name']]=(readable, spec)
        cls.mcp=[]
        for r in cls.ret:
            eps=[]
            for s in by.get(r['id'], []):
                m=(s.get('signals') or {}).get('mcp')
                if isinstance(m, dict) and m.get('state')=='answered' and m.get('endpoint'):
                    eps.append(m['endpoint'])
            if eps: cls.mcp.append((r, eps))
        cls.acp=[r for r in cls.ret if any(((s.get('signals') or {}).get('acp') or {}).get('state')=='found' for s in by.get(r['id'], []))]
        order=('found','not_found','refused','error','robots_disallow','not_checked','missing')
        llms=[]
        for r in cls.ret:
            states=[]
            for s in by.get(r['id'], []):
                v=(s.get('signals') or {}).get('llms_txt')
                st=v.get('state') if isinstance(v, dict) else None
                states.append(st if st in order else 'missing')
            if states and next(s for s in order if s in states)=='found':
                llms.append(r)
        llms.sort(key=lambda r: (0 if r.get('segment')=='big' else 1, (r.get('name') or '').lower(), r.get('id') or ''))
        cls.llms=llms
        x=datetime.date.fromisoformat(cls.D['crawl_date'])
        cls.long=f'{x.day} {x.strftime("%B")} {x.year}'

    def _graph(self, path):
        return lds(R(path))[0]['@graph']
    def _lead(self, path):
        return T(re.search(r'<p class="lede" id="answer">(.*?)</p>', R(path), re.S).group(1))
    def _h1(self, path):
        return T(re.search(r'<h1[^>]*>(.*?)</h1>', R(path), re.S).group(1))
    def _faq_matches(self, path):
        h=R(path)
        box=T(re.search(r'<div class="box faq" id="faq">(.*?)</div>', h, re.S).group(1))
        faq=[x for x in self._graph(path) if x.get('@type')=='FAQPage'][0]
        for q in faq['mainEntity']:
            self.assertIn(q['name'], box)
            self.assertIn(q['acceptedAnswer']['text'], box)
            self.assertNotRegex(q['name']+' '+q['acceptedAnswer']['text'], r'[—–]')
            low=(q['name']+' '+q['acceptedAnswer']['text']).lower()
            self.assertNotIn('official', low)
            self.assertNotRegex(low, r'\bverified\b')
        return faq
    def _dataset(self, path, lead):
        ds=[x for x in self._graph(path) if x.get('@type')=='Dataset'][0]
        self.assertEqual(ds['dateModified'], STAMP)
        self.assertEqual(ds['description'], lead)
        loc='https://shopbotindex.com/'+path.replace('index.html','')
        self.assertIn(f'<loc>{loc}</loc><lastmod>{STAMP}</lastmod>', R('sitemap.xml'))
        self.assertIn(loc, R('llms.txt'))
        self.assertIn(loc, R('llms-full.txt'))
    def _words(self, text):
        self.assertNotRegex(text, r'[—–]')
        self.assertNotIn('official', text.lower())
        self.assertNotRegex(text.lower(), r'\bverified\b')
        for bad in ('PrimeLogic','Stathopoulos','Switzerland'): self.assertNotIn(bad, text)
        self.assertIn('publish a UCP profile', text)

    def test_checkout_headline_matches_the_crawl(self):
        path='which-stores-declare-ucp-checkout/index.html'
        h=R(path); lead=self._lead(path)
        self.assertEqual(self._h1(path), 'Which stores declare UCP checkout?')
        self.assertIn(self.long, lead)
        self.assertIn(f'{len(self.co):,} of the {len(self.ucp):,} stores that publish a UCP profile declare checkout', lead)
        self._words(lead)
        self.assertIn('not proof that an AI agent can complete a purchase', lead)
        for r in self.co:
            if r['segment']=='big': self.assertIn(r['name'], lead)
        missing=T(re.search(r'id="no-checkout">(.*?)</p>', h, re.S).group(1))
        self.assertIn(f'{len(self.noco):,} of the {len(self.ucp):,}', missing)
        for r in self.noco: self.assertIn(r['name'], missing)
        items=[x for x in self._graph(path) if x.get('@type')=='ItemList' and x.get('name')=='Stores that declare UCP checkout'][0]
        self.assertEqual([i['name'] for i in items['itemListElement']], [r['name'] for r in self.co])
        faq=self._faq_matches(path)
        self.assertEqual(faq['mainEntity'][0]['acceptedAnswer']['text'], lead)
        self._dataset(path, lead)
        self.assertIn('which-stores-declare-ucp-checkout/', R('index.html'))

    def test_ucp_profile_page_answers_both_questions(self):
        path='guides/what-is-a-ucp-profile/index.html'
        h=R(path); lead=self._lead(path)
        self.assertEqual(self._h1(path), 'What is a /.well-known/ucp profile for AI shopping agents?')
        self.assertEqual(len(sentences(lead)), 2)
        self.assertIn('/.well-known/ucp', lead)
        self.assertIn(self.long, lead)
        checked=sum(1 for r in self.ret if r['status'] in ('ucp','no_ucp'))
        self.assertIn(f'{len(self.ucp):,} of the {checked:,}', lead)
        self.assertIn('does not by itself prove that agents can check out', lead)
        self._words(lead)
        self.assertIn('Does a UCP profile mean AI agents can check out at a store?', h)
        body=T(re.search(r'id="checkout-meaning">(.*?)</p>', h, re.S).group(1))
        self.assertIn(f'{len(self.co):,} of the {len(self.ucp):,}', body)
        self.assertIn('does not by itself prove that AI agents can check out at a store', body)
        self.assertIn('does not test purchases', body)
        faq=self._faq_matches(path)
        self.assertEqual(faq['mainEntity'][0]['name'], 'What is a /.well-known/ucp profile for AI shopping agents?')
        self.assertEqual(faq['mainEntity'][0]['acceptedAnswer']['text'], lead)
        self.assertEqual(faq['mainEntity'][1]['name'], 'Does a UCP profile mean AI agents can check out at a store?')
        self.assertEqual(faq['mainEntity'][1]['acceptedAnswer']['text'], body)
        self._dataset(path, lead)
        self.assertIn('href="what-is-a-ucp-profile/"', R('guides/index.html'))
        self.assertIn('href="businesses-in-chatgpt/"', R('guides/index.html'))

    def test_check_page_explains_both_methods(self):
        h=R('check.html')
        self.assertEqual(self._h1('check.html'), 'How can I check if my online store is ready for AI shopping agents?')
        summary=T(re.search(r'id="summary">(.*?)</p>', h, re.S).group(1))
        self.assertGreaterEqual(len(sentences(summary)), 2)
        self.assertLessEqual(len(sentences(summary)), 3)
        self.assertIn(self.long, summary)
        self.assertIn('https://your-domain/.well-known/ucp', summary)
        self.assertIn('stores.html', h)
        self.assertIn('does not by itself prove that agents can check out', summary)
        self._words(summary)
        self.assertIn('<form', h)

    def test_payment_handler_counts_match_the_crawl(self):
        path='payment-handlers/index.html'
        lead=self._lead(path)
        self.assertEqual(self._h1(path), 'Which payment handlers do stores declare in their UCP profile?')
        self.assertIn(self.long, lead)
        self.assertIn(f'of the {len(self.ucp):,} stores that publish a UCP profile', lead)
        none=self.combos[()]
        self.assertIn(f'{len(self.ucp)-none:,} declare at least one payment handler and {none:,} declare none', lead)
        for pid, n in self.ph.most_common():
            word='declares' if n==1 else 'declare'
            self.assertIn(f'{n:,} {word} {PH.get(pid, pid)}', lead)
            self.assertIn(pid, lead)
        self.assertIn('Shop Pay', lead)
        self.assertIn('Google Pay', lead)
        self.assertIn('not proof that an agent can pay', lead)
        self._words(lead)
        faq=self._faq_matches(path)
        self.assertEqual(faq['mainEntity'][0]['acceptedAnswer']['text'], lead)
        self._dataset(path, lead)
        # combination rows are the exact multisets in the crawl
        h=R(path)
        for key, n in self.combos.items():
            self.assertIn(f'<td>{n:,}</td>', h)

    def test_signal_titles_and_named_lists_match_the_crawl(self):
        acp='signals/acp/index.html'
        self.assertEqual(self._h1(acp), 'Which stores publish an Agentic Commerce Protocol (ACP) discovery file?')
        lead=self._lead(acp)
        self.assertEqual(len(self.acp), 1)
        self.assertIn(self.acp[0]['name'], lead)
        self.assertIn('not proof that OpenAI checkout works at the store', lead)
        items=[x for x in self._graph(acp) if x.get('@type')=='ItemList' and 'ACP' in x.get('name','')][0]
        self.assertEqual([i['name'] for i in items['itemListElement']], [self.acp[0]['name']])
        self._faq_matches(acp)
        self._dataset(acp, lead)

        llms='signals/llms-txt/index.html'
        self.assertEqual(self._h1(llms), 'How many online stores have an llms.txt file in 2026?')
        llms_lead=self._lead(llms)
        self.assertIn(self.long, llms_lead)
        named=[x for x in self._graph(llms) if x.get('@type')=='ItemList' and x.get('name')=='Stores that publish an llms.txt file'][0]
        self.assertEqual([i['name'] for i in named['itemListElement']], [r['name'] for r in self.llms])
        self.assertIn(f'{len(self.llms):,} of ', llms_lead)
        self.assertIn('publish an llms.txt file', llms_lead)
        self._dataset(llms, llms_lead)

        mcp='signals/mcp/index.html'
        self.assertEqual(self._h1(mcp), 'Which online stores publish an MCP server for AI agents?')
        mcp_lead=self._lead(mcp)
        self.assertTrue(mcp_lead.startswith('In the ShopBot Index crawl of'))
        self.assertIn('name an MCP endpoint in their UCP profile', mcp_lead)
        self.assertLess(mcp_lead.index('name an MCP endpoint'), mcp_lead.index('returned a tools list'))
        tools=[x for x in self._graph(mcp) if x.get('@type')=='ItemList' and x.get('name')=='MCP endpoints that returned a tools list'][0]
        self.assertEqual(sorted(i['name'] for i in tools['itemListElement']), sorted(r['name'] for r,_ in self.mcp))
        self.assertEqual(len(self.mcp), tools['numberOfItems'])
        for r, eps in self.mcp:
            self.assertIn(r['name'], mcp_lead)
            for ep in eps:
                self.assertIn(ep, mcp_lead)
                self.assertIn(ep, ' '.join(i.get('description','') for i in tools['itemListElement']))
        self.assertNotIn('8 of 8', R(mcp))
        self._dataset(mcp, mcp_lead)

        bots='signals/ai-bots-robots/index.html'
        self.assertEqual(self._h1(bots), 'Which retailers block AI bots like GPTBot in robots.txt?')
        bot_lead=self._lead(bots)
        self.assertIn(f'{len(self.gpt):,} of {self.readable:,} stores whose robots.txt we could read disallow the whole site for GPTBot', bot_lead)
        self.assertIn("Amazon's robots.txt asks GPTBot to stay out of the whole site.", bot_lead)
        self.assertEqual(self.named['Amazon'][1].get('GPTBot'), 'blocked')
        self.assertIn("EBay's robots.txt disallows the whole site for GPTBot except some paths.", bot_lead)
        self.assertEqual(self.named['EBay'][1].get('GPTBot'), 'mostly_blocked')
        self.assertIn("Walmart's robots.txt that we could read does not name GPTBot", bot_lead)
        self.assertEqual(self.named['Walmart'][1].get('GPTBot'), None)
        self.assertNotIn("Walmart's robots.txt asks GPTBot", bot_lead)
        self.assertIn('not a technical block we tested', bot_lead)
        self.assertIn('have robots.txt rules that name an AI crawler', bot_lead)
        listed=[x for x in self._graph(bots) if x.get('@type')=='ItemList' and 'disallows the whole site' in x.get('name','')][0]
        self.assertEqual(sorted(i['name'] for i in listed['itemListElement']), sorted(r['name'] for r in self.blockers))
        amazon=[i for i in listed['itemListElement'] if i['name']=='Amazon'][0]
        self.assertIn('GPTBot, asks it to stay out of the whole site', amazon['description'])
        self._dataset(bots, bot_lead)

if __name__=='__main__': unittest.main()
