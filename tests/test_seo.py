"""Offline checks of the SEO/AEO output (scripts/seo.py). Run after python3 scripts/build.py."""
import os, re, json, glob, html, unittest, collections
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DIST=os.path.join(ROOT,'dist')
R=lambda p: open(os.path.join(DIST,p)).read()
T=lambda h: re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',h))).strip()
def lds(h): return [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>',h,re.S)]
@unittest.skipUnless(os.path.exists(os.path.join(DIST,'index.html')),'dist not built')
class Seo(unittest.TestCase):
    def test_faq_ld_matches_visible_faq(self):
        for p in ('index.html','methodology.html'):
            h=R(p); faq=[x for o in lds(h) for x in o.get('@graph',[o]) if x.get('@type')=='FAQPage'][0]
            box=re.search(r'<div class="box faq" id="faq">(.*?)</div>',h,re.S).group(1); vis=T(box)
            self.assertGreaterEqual(len(faq['mainEntity']),4)
            for q in faq['mainEntity']:
                self.assertIn(q['name'],vis,p); self.assertIn(q['acceptedAnswer']['text'],vis,p)
    def test_summary_and_dataset(self):
        h=R('index.html'); self.assertIn('id="summary"',h); self.assertLess(h.index('id="subscribe-top"'),h.index('id="summary"'))
        g=lds(h)[0]['@graph']; ds=[x for x in g if x['@type']=='Dataset'][0]
        self.assertIn(ds['dateModified'],h); self.assertEqual(ds['license'],'https://shopbotindex.com/terms.html')
    def test_terms_page_built_and_linked(self):
        t=R('terms.html'); self.assertIn('All rights reserved',t); self.assertIn('hello@shopbotindex.com',t)
        self.assertIsNone(re.search(r'\b(official|PrimeLogic|Stathopoulos|Switzerland|governing law|jurisdiction)\b',T(t),re.I))
        self.assertIn('<loc>https://shopbotindex.com/terms.html</loc>',R('sitemap.xml')); self.assertIn('https://shopbotindex.com/terms.html',R('llms.txt'))
        for p in ('index.html','terms.html','store/ikea.html' if os.path.exists(os.path.join(DIST,'store/ikea.html')) else 'stores.html','segments/big.html'):
            f=re.search(r'<footer>.*?</footer>',R(p),re.S).group(0); pre='../'*p.count('/')
            self.assertIn(f'<a href="{pre}privacy.html">Privacy</a> · <a href="{pre}terms.html">Terms</a>',f,p)
    def test_changes_page_has_substance(self):
        h=R('changes.html'); v=T(re.search(r'<main>(.*?)</main>',h,re.S).group(1))
        self.assertNotIn('None.',v); self.assertIn('methodology.html#changes',h); self.assertIn('id="changes"',R('methodology.html'))
        chg=json.load(open(os.path.join(ROOT,'data','changes-latest.json')))
        for k in ('joined','left','now_unreachable'): self.assertIn(f'({len(chg[k])})',v)
        self.assertGreaterEqual(h.count('href="store/'),len(chg['joined'])+len(chg['left'])+len(chg['now_unreachable']))
        for m in re.findall(r'href="(store/[^"]+)"',h): self.assertTrue(os.path.exists(os.path.join(DIST,m)),m)
        faq=[x for o in lds(h) for x in o.get('@graph',[o]) if x.get('@type')=='FAQPage'][0]
        for q in faq['mainEntity']: self.assertIn(q['name'],v); self.assertIn(q['acceptedAnswer']['text'],v)
    def test_visit_counter_skips_crawlers(self):
        self.assertIn('n.webdriver||/bot|crawl',R('changes.html'))
    def test_every_page_one_h1_unique_title_valid_ld(self):
        ts=collections.Counter()
        for f in glob.glob(os.path.join(DIST,'**','*.html'),recursive=True):
            h=open(f).read(); self.assertEqual(len(re.findall(r'<h1[ >]',h)),1,f); lds(h)
            ts[re.search(r'<title>(.*?)</title>',h).group(1)]+=1
        self.assertEqual([t for t,n in ts.items() if n>1],[])
    def test_no_official_anywhere(self):
        # Gus's rule: the word 'official' never appears on the site (store domains such as chiqueofficial.com are data, not wording)
        for f in glob.glob(os.path.join(DIST,'**','*'),recursive=True):
            if os.path.isfile(f) and f.endswith(('.html','.txt','.xml','.json','.svg')):
                self.assertIsNone(re.search(r'(?<![a-z0-9.-])official(?!ly?[a-z0-9-]*\.[a-z])',open(f).read(),re.I),f)
    def test_root_files(self):
        r=R('robots.txt'); self.assertIn('User-agent: *\nAllow: /',r); self.assertIn('User-agent: GPTBot',r); self.assertIn('Sitemap: https://shopbotindex.com/sitemap.xml',r)
        self.assertNotIn('Disallow',r)
        s=R('sitemap.xml'); self.assertEqual(s.count('<url>'),s.count('<lastmod>'))
        l=R('llms.txt'); self.assertTrue(l.startswith('# ShopBot Index')); os.path.exists(os.path.join(DIST,'llms-full.txt'))
        self.assertIsNone(re.search(r'\b(official|PrimeLogic|Stathopoulos|Switzerland)\b',l+R('llms-full.txt'),re.I))
        import sys; sys.path.insert(0,os.path.join(ROOT,'scripts')); from seo import INDEXNOW_KEY as K
        self.assertEqual(R(f'{K}.txt'),K)
    def test_internal_links_use_clean_urls(self):
        # Google treats /index.html and / as two URLs; internal links must point at the canonical one.
        for p in ('index.html','methodology.html','segments/big.html','categories/electronics.html','store/ikea.html','unwatch.html'):
            self.assertNotRegex(R(p),r'href="[^"]*index\.html',p)
