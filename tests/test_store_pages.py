"""Store pages: no pages for non-shops, readable slugs for accented names with redirects from the old URLs,
and real content built from our data (no thin, error-like pages). Run after python3 scripts/build.py."""
import os, re, json, glob, html, unittest
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DIST=os.path.join(ROOT,'dist'); DATA=os.path.join(ROOT,'data')
R=lambda p: open(os.path.join(DIST,p)).read()
T=lambda h: re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',h))).strip()
NS=json.load(open(os.path.join(ROOT,'config','non_shops.json')))
@unittest.skipUnless(os.path.exists(os.path.join(DIST,'index.html')),'dist not built')
class StorePages(unittest.TestCase):
    def setUp(self):
        self.slugs=json.load(open(os.path.join(DATA,'slugs-latest.json'))); self.sitemap=R('sitemap.xml')
        self.stubs={os.path.basename(f)[:-5]:open(f).read() for f in glob.glob(os.path.join(DIST,'store','*.html')) if 'http-equiv="refresh"' in open(f).read()}
    def test_non_shops_have_no_page(self):
        self.assertGreater(len(NS['items']),50)
        self.assertEqual([q for q in NS['items'] if q in self.slugs],[])
        seeds={s['id'] for s in json.load(open(os.path.join(DATA,'seeds.json')))}
        self.assertEqual([q for q in NS['items'] if q in seeds],[])
        self.assertFalse(os.path.exists(os.path.join(DIST,'store','villiers-en-bi-re.html')))
        self.assertNotIn('villiers',self.sitemap)
    def test_slugs_are_plain_ascii_words(self):
        names={v[0]:v[1] for v in self.slugs.values()}
        self.assertIn('el-corte-ingles',names); self.assertIn('cooperative-u',names)
        for s,n in names.items():
            self.assertRegex(s,r'^[a-z0-9]+(-[a-z0-9]+)*$',n)
    def test_old_slugs_redirect_and_stay_out_of_sitemap(self):
        self.assertGreater(len(self.stubs),10)
        self.assertIn('el-corte-ingl-s',self.stubs); self.assertIn('herm-s',self.stubs)
        live={v[0] for v in self.slugs.values()}
        for old,h in self.stubs.items():
            self.assertNotIn(old,live)
            tgt=re.search(r'url=([a-z0-9-]+)\.html',h).group(1)
            self.assertIn(tgt,live,old); self.assertIn(f'/store/{tgt}.html"',h)
            self.assertNotIn(f'/store/{old}.html<',self.sitemap)
    def test_store_pages_have_real_content(self):
        for sid,(s,n,st) in self.slugs.items():
            h=R(f'store/{s}.html'); lede=T(re.search(r'<p class="lede">(.*?)</p>',h,re.S).group(1))
            self.assertIn(' we track, listed under ',lede,s)
            self.assertIn('<h2>Weekly results</h2>',h,s)
            if st=='no_ucp': self.assertIn("doesn't mean AI agents can't shop there",lede,s)
            if st=='couldnt_check': self.assertIn('not the same as no profile',lede,s); self.assertNotIn('found no UCP profile',lede,s)
            if st=='ucp': self.assertIn('publishes a UCP profile, the profile AI shopping agents read',lede,s)
        h=R('store/coles-supermarkets.html')
        self.assertIn('<h2>Other stores in Grocery &amp; hypermarkets',h)
        self.assertGreater(len(T(re.search(r'<main.*?</main>',h,re.S).group(0) if '<main' in h else h)),2500)
if __name__=='__main__': unittest.main()
