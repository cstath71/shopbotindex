"""Answer-first pages for AI answer engines. Numbers are recomputed from data/latest.json
(the crawl file the build reads). Run after python3 scripts/build.py.
"""
import os, re, json, html, collections, datetime, unittest
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST=os.path.join(ROOT,'dist'); DATA=os.path.join(ROOT,'data')
R=lambda p: open(os.path.join(DIST,p),encoding='utf-8').read()
def T(h): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',h))).strip()
def lds(h): return [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>',h,re.S)]
def faq(h): return [x for o in lds(h) for x in o.get('@graph',[o]) if x.get('@type')=='FAQPage'][0]
def sentences(text): return re.findall(r'\.(?=\s|$)', text)
CONTENT_FLOOR='2026-11-11'

def stats():
    import sys
    sys.path.insert(0,os.path.join(ROOT,'scripts'))
    from nonshops import IDS
    D=json.load(open(os.path.join(DATA,'latest.json'),encoding='utf-8'))
    ret=[r for r in D['retailers'] if r['id'] not in IDS]
    def seg(rs):
        st=collections.Counter(r['status'] for r in rs)
        return dict(n=len(rs),ucp=st['ucp'],no=st['no_ucp'],cc=st['couldnt_check'],checked=st['ucp']+st['no_ucp'])
    big=[r for r in ret if r['segment']=='big']
    return D,ret,seg(ret),seg([r for r in ret if r['segment']=='shopify']),seg(big),sorted((r['name'] for r in big if r['status']=='ucp'),key=str.lower)

@unittest.skipUnless(os.path.exists(os.path.join(DIST,'segments','big.html')),'dist not built')
class GeoAnswers(unittest.TestCase):
    def setUp(self):
        self.D,self.ret,self.all,self.shop,self.big,self.names=stats()
        self.day=self.D['crawl_date']
        x=datetime.date.fromisoformat(self.day)
        self.long=f'{x.day} {x.strftime("%B")} {x.year}'
        self.stamp=max(CONTENT_FLOOR, self.day)

    def _fig(self, text):
        a,s,b=self.all,self.shop,self.big
        self.assertIn(self.long, text)
        self.assertIn(f'{a["ucp"]:,} of the {a["checked"]:,}', text)
        self.assertIn(f'{s["ucp"]:,} of the {s["checked"]:,}', text)
        self.assertIn(f'{b["ucp"]:,} of the {b["checked"]:,}', text)
        self.assertIn('publish a UCP profile', text)
        self.assertNotIn('official', text.lower())
        self.assertNotRegex(text, r'[—–]')
        for bad in ('PrimeLogic','Stathopoulos','Switzerland'): self.assertNotIn(bad, text)

    def _faq_matches(self, h):
        box=re.search(r'<div class="box faq" id="faq">(.*?)</div>',h,re.S).group(1)
        vis=T(box)
        got=faq(h)
        self.assertGreaterEqual(len(got['mainEntity']),1)
        for q in got['mainEntity']:
            self.assertIn(q['name'], vis)
            self.assertIn(q['acceptedAnswer']['text'], vis)
            self.assertNotRegex(q['name']+' '+q['acceptedAnswer']['text'], r'[—–]')
            self.assertNotIn('official', (q['name']+' '+q['acceptedAnswer']['text']).lower())

    def test_big_retailers_first_paragraph_names_the_crawl(self):
        h=R('segments/big.html')
        after=h.split('</h1>',1)[1]
        m=re.search(r'<p([^>]*)>(.*?)</p>',after,re.S)
        self.assertIn('id="big-answer"', m.group(1))
        text=T(m.group(2))
        self.assertIn(f'{self.big["ucp"]:,} of the {self.big["checked"]:,} big retailers we could check publish a UCP profile', text)
        self.assertIn(self.long, text)
        for name in self.names: self.assertIn(name, text)
        self.assertEqual(len(sentences(text)),1)
        self.assertNotRegex(text, r'[—–]')
        self.assertNotIn('official', text.lower())
        self._faq_matches(h)
        ans=faq(h)['mainEntity'][0]['acceptedAnswer']['text']
        self.assertEqual(ans, text)
        graph=lds(h)[0]['@graph']
        items=[x for x in graph if x.get('@type')=='ItemList'][0]
        self.assertEqual(items['numberOfItems'], len(self.names))
        self.assertEqual([i['name'] for i in items['itemListElement']], self.names)
        ds=[x for x in graph if x.get('@type')=='Dataset'][0]
        self.assertEqual(ds['dateModified'], self.stamp)
        self.assertEqual(ds['description'], text)
        page=[x for x in graph if x.get('@type')=='WebPage'][0]
        self.assertEqual(page['dateModified'], self.stamp)
        self.assertIn(f'<loc>https://shopbotindex.com/segments/big.html</loc><lastmod>{self.stamp}</lastmod>', R('sitemap.xml'))

    def test_stores_rows_are_in_the_html(self):
        pages=['stores.html']+sorted(p for p in os.listdir(DIST) if re.fullmatch(r'stores-\d+\.html', p))
        self.assertGreaterEqual(len(pages), 1)
        sm=R('sitemap.xml'); hrefs=set(); rows=0
        slugs=json.load(open(os.path.join(DATA,'slugs-latest.json'),encoding='utf-8'))
        for p in pages:
            h=R(p)
            tbody=re.search(r'<tbody>(.*)</tbody>',h,re.S).group(1)
            rows+=len(re.findall(r'<tr\b', tbody))
            hrefs |= set(re.findall(r'href="store/([^"]+)\.html"', tbody))
            self.assertNotIn('const D=', h)
            self.assertNotIn('tb.innerHTML', h)
            self.assertIn('addEventListener', h)
            self.assertLess(os.path.getsize(os.path.join(DIST,p)), 1_000_000, p)
            page=[x for o in lds(h) for x in o.get('@graph',[o]) if x.get('@type')=='WebPage'][0]
            self.assertEqual(page['dateModified'], self.stamp, p)
            self.assertIn(f'<loc>https://shopbotindex.com/{p}</loc><lastmod>{self.stamp}</lastmod>', sm)
            self.assertIn('href="store/', tbody)
        self.assertEqual(rows, len(self.ret))
        self.assertEqual(hrefs, {v[0] for v in slugs.values()})
        # /stores.html itself is not an empty shell: it lists the stores that publish a UCP profile
        first=R('stores.html')
        self.assertGreater(len(re.findall(r'data-s="ucp"', first)), 0)
        if len(pages)>1:
            self.assertIn('stores-2.html', first)

    def test_check_and_guide_open_with_summary_and_faq(self):
        for path in ('check.html','guides/what-a-ucp-profile-proves/index.html'):
            h=R(path)
            summary=T(re.search(r'id="summary">(.*?)</(?:p|div)>',h,re.S).group(1))
            self.assertGreaterEqual(len(sentences(summary)),2)
            self.assertLessEqual(len(sentences(summary)),3)
            self._fig(summary)
            self.assertIn('does not by itself prove that agents can check out', summary)
            self._faq_matches(h)
            qs=[q['name'] for q in faq(h)['mainEntity']]
            base=[
                'What is a UCP profile?',
                'How do I check whether a store publishes a UCP profile?',
                'Does a UCP profile mean agents can check out?',
                'How many stores publish a UCP profile?']
            if path=='check.html':
                self.assertEqual(qs, ['How can I check if my online store is ready for AI shopping agents?']+base)
                how=faq(h)['mainEntity'][0]['acceptedAnswer']['text']
                self.assertIn('/.well-known/ucp', how)
                self.assertIn('all-stores table', how)
                self.assertIn('href="stores.html"', h)
                self.assertIn('does not by itself prove that agents can check out', how)
            else:
                self.assertEqual(qs, base)
            by={q['name']:q['acceptedAnswer']['text'] for q in faq(h)['mainEntity']}
            self.assertIn('does not by itself prove that agents can check out', by['Does a UCP profile mean agents can check out?'])
            self.assertIn('published declaration', by['Does a UCP profile mean agents can check out?'])
            self.assertIn('does not test purchases', by['Does a UCP profile mean agents can check out?'])
            self._fig(by['How many stores publish a UCP profile?'])
            n_co=sum(1 for r in self.ret if r['status']=='ucp' and 'dev.ucp.shopping.checkout' in r['capabilities'])
            n_ucp=sum(1 for r in self.ret if r['status']=='ucp')
            self.assertIn(f'{n_co:,} of the {n_ucp:,}', by['Does a UCP profile mean agents can check out?'])
        chk=R('check.html')
        after=chk.split('</h1>',1)[1]
        self.assertTrue(re.search(r'<p[^>]*id="summary"', after).start()<after.index('<h2'))
        guide=R('guides/what-a-ucp-profile-proves/index.html')
        self.assertLess(guide.index('id="summary"'), guide.index('A store that publishes a UCP profile'))
        gpage=[x for o in lds(guide) for x in o.get('@graph',[o]) if x.get('@type')=='Article'][0]
        self.assertEqual(gpage['dateModified'], self.stamp)
        self.assertEqual(gpage['datePublished'], '2026-11-08')
        cpage=[x for o in lds(chk) for x in o.get('@graph',[o]) if x.get('@type')=='WebPage'][0]
        self.assertEqual(cpage['dateModified'], self.stamp)
        sm=R('sitemap.xml')
        self.assertIn(f'<loc>https://shopbotindex.com/check.html</loc><lastmod>{self.stamp}</lastmod>', sm)
        self.assertIn(f'<loc>https://shopbotindex.com/guides/what-a-ucp-profile-proves/</loc><lastmod>{self.stamp}</lastmod>', sm)

if __name__=='__main__': unittest.main()
