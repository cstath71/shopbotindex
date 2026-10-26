"""Offline checks of the built site's signup forms, watch form, sticky bar and visit counter, plus scripts/watch_alerts.py.
Run after python3 scripts/build.py:  python3 -m unittest discover -s tests"""
import os, re, sys, json, glob, unittest
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DIST=os.path.join(ROOT,'dist')
sys.path.insert(0,os.path.join(ROOT,'scripts'))
import watch_alerts as WA
R=lambda p: open(os.path.join(DIST,p)).read()
FN='https://uufmlmwgvoqhhtqgrclu.supabase.co/functions/v1/sbi-subscribe'
@unittest.skipUnless(os.path.exists(os.path.join(DIST,'index.html')),'dist not built')
class Site(unittest.TestCase):
    def test_home_form_right_after_hero(self):
        h=R('index.html'); i=h.index('</section>'); self.assertEqual(h.index('<div class="nl-top"'),i+len('</section>'))
        self.assertIn('Every Monday: which stores started or stopped publishing a UCP profile, the profile AI shopping agents read.',h)
    def test_top_and_bottom_forms(self):
        for p in ('stores.html','methodology.html','assistants.html'):
            h=R(p); self.assertIn('id="subscribe-top"',h,p); self.assertIn('id="subscribe"',h,p)
            self.assertLess(h.index('id="subscribe-top"'),h.index('</p>',h.index('class="lede"'))+40,p)
    def test_every_store_page_has_watch_under_result(self):
        fs=glob.glob(os.path.join(DIST,'store','*.html')); self.assertGreater(len(fs),2000)
        for f in fs:
            h=open(f).read()
            if 'http-equiv="refresh"' in h: continue  # redirect stub for an old store URL
            m=re.search(r'name="watch" value="([^"]+)"',h); self.assertTrue(m,f)
            self.assertLess(h.index('What this means.'),h.index('id="watch"'),f); self.assertLess(h.index('id="watch"'),h.index('<h2>Websites checked'),f)
    def test_check_result_offers_watch(self):
        # the store lookup result links to that store's watch form
        for f in ('check.html','index.html'): self.assertIn(".html#watch\"><b>Watch '",R(f),f)
    def test_store_owner_page(self):
        # for-stores.html: lookup with an inline watch form; wording rules; linked from check.html; in the sitemap
        h=R('for-stores.html'); self.assertIn('data-watch',h); self.assertIn('window.sbiSub',h); self.assertIn("doesn't mean AI agents can't shop",h)
        self.assertIn("we don't know whether it publishes a UCP profile",h); self.assertIn('for-stores.html',R('check.html')); self.assertIn('/for-stores.html',R('sitemap.xml'))
        t=re.sub(r'<script.*?</script>','',h,flags=re.S).lower(); self.assertNotIn('official',t); self.assertNotIn('can buy',t); self.assertNotIn("agents can't buy",t)
        L=json.load(open(os.path.join(DIST,'stores.json'))); self.assertEqual(L['ikea.com'][3],'Q54078')
    def test_forms_post_to_function_with_honeypot(self):
        for p in ('index.html','stores.html','store/ikea.html'):
            h=R(p)
            for f in re.findall(r'<form class="nl".*?</form>',h,re.S):
                self.assertIn(f'action="{FN}"',f); self.assertIn('name="sbi_hp_note"',f); self.assertNotIn('name="website"',f); self.assertIn('autocomplete="off"',f); self.assertIn('tabindex="-1"',f); self.assertIn('aria-hidden="true"',f); self.assertIn('type="email"',f)
    def test_bar_and_counter_on_pages(self):
        for p in ('index.html','stores.html','store/ikea.html','privacy.html'):
            h=R(p); self.assertIn('id="nl-bar"',h); self.assertIn('functions/v1/sbi-hit',h)
            self.assertIn("doNotTrack=='1'",h); self.assertIn('globalPrivacyControl',h)
            self.assertNotIn('document.cookie',h); self.assertNotIn('localStorage',h); self.assertNotIn('sessionStorage',h)
        self.assertNotIn('id="nl-bar"',R('unwatch.html')); self.assertIn('noindex',R('unwatch.html'))
        self.assertNotIn('unwatch.html',R('sitemap.xml'))
    def test_wording(self):
        # the new copy only (store data can legitimately name countries)
        new=' '.join(re.findall(r'<div class="nl-(?:top|bar).*?</div>',R('store/ikea.html')+R('index.html'),re.S)+[R('unwatch.html'),R('privacy.html')]).lower()
        for bad in ('primelogic','stathopoulos','switzerland'): self.assertNotIn(bad,new)
        self.assertNotIn('official',new); self.assertNotIn('can buy',new); self.assertNotIn("can't buy",new)
    def test_privacy_mentions_counter(self):
        h=R('privacy.html'); self.assertIn('Do Not Track',h); self.assertIn("We don't store your IP address",h); self.assertIn('which stores you watch',h)
    def test_logo_left(self):
        h=R('index.html'); self.assertLess(h.index('class="hero-art"'),h.index('class="hero-t"'))
        self.assertLess(h.index('<img src="logo-32.png"'),h.index('ShopBot Index</a>'))
class Alerts(unittest.TestCase):
    def test_build_changes(self):
        slugs={'a.com':['a-com','A','ucp'],'Q1':['ikea','IKEA','no_ucp'],'Q2':['x','X','couldnt_check']}
        c=WA.build_changes(dict(joined=['a.com'],left=['Q1'],now_unreachable=['Q2'],newly_tracked=['Q2']),slugs)
        self.assertEqual(c,[dict(store_id='a.com',slug='a-com',name='A',change='started'),dict(store_id='Q1',slug='ikea',name='IKEA',change='stopped')])
if __name__=='__main__': unittest.main()
