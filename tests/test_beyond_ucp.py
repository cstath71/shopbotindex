"""Beyond UCP counts: each signal's share uses only websites that answered for that file.

Rendered checks read data/beyond-ucp-latest.json, which build.py writes from the latest crawl,
so a later Monday crawl does not need new expected numbers. The 9 Nov 2026 crawl file is
historical and keeps the counts from that week's brief.
"""
import os, re, json, html, unittest, sys
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT,'scripts'))
import beyond_ucp
DIST=os.path.join(ROOT,'dist'); DATA=os.path.join(ROOT,'data')
T=lambda h: re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',h))).strip()
DASH=re.compile(r'[\u2013\u2014]')

def comma(n): return f'{n:,}'

class BucketRules(unittest.TestCase):
    def test_refused_is_not_in_the_denominator_and_missing_previous_has_no_change(self):
        sig=dict(checked=True,
                 llms_txt=dict(state='refused',http=403),
                 agents_md=dict(state='found',http=200),
                 acp=dict(state='not_found',http=404),
                 ai_catalog=dict(state='error',http=500),
                 mcp=dict(state='no_tools',http=401),
                 robots=dict(present=True,specific={'GPTBot':'blocked'},wildcard='allowed',content_signal=['search=y']),
                 product=dict(state='none'))
        sites=[dict(rid='a',signals=sig,agent_files=dict(checked=True,
                 poppy=dict(status=403),
                 a2a_card=dict(status=404),
                 a2a_card_legacy=dict(status='not fetched',reason='site refused (403)')))]
        retailers=[dict(id='a',name='A Shop')]
        # Previous crawl checked llms.txt only. Other signals must not invent a week-over-week line.
        prev_sites=[dict(rid='a',signals=dict(checked=True,llms_txt=dict(state='not_found',http=404)))]
        prev_ret=[dict(id='a',name='A Shop')]
        rep=beyond_ucp.report(sites,retailers,'2026-11-09',prev_sites,prev_ret,'2026-11-02',slug_for_id=lambda i:'a-shop')
        by={s['key']:s for s in rep['signals']}
        self.assertEqual(by['llms_txt']['found'],0)
        self.assertEqual(by['llms_txt']['answered'],0)
        self.assertEqual(by['llms_txt']['refused'],1)
        self.assertEqual(by['llms_txt']['share_display'],'n/a')
        self.assertEqual(by['llms_txt']['found_change'],0)
        self.assertEqual(by['llms_txt']['previous']['found'],0)
        self.assertEqual(by['llms_txt']['previous']['answered'],1)
        self.assertEqual(by['agents_md']['found'],1)
        self.assertEqual(by['agents_md']['answered'],1)
        self.assertEqual(by['agents_md']['store_count'],1)
        self.assertEqual(by['agents_md']['stores'][0]['path'],'store/a-shop.html')
        self.assertIsNone(by['agents_md']['previous'])
        self.assertEqual(by['agents_md']['wow'],'not in the previous crawl')
        self.assertEqual(by['acp']['found'],0)
        self.assertEqual(by['acp']['answered'],1)
        self.assertEqual(by['ai_catalog']['error'],1)
        self.assertEqual(by['ai_catalog']['answered'],0)
        self.assertEqual(by['mcp_tools']['refused'],1)
        self.assertEqual(by['mcp_tools']['answered'],0)
        self.assertEqual(by['robots_ai']['found'],1)
        self.assertEqual(by['robots_ai']['answered'],1)
        self.assertIsNone(by['robots_ai']['refused'])
        self.assertEqual(by['content_signals']['found'],1)
        self.assertEqual(by['poppy']['refused'],1)
        self.assertEqual(by['poppy']['answered'],0)
        # One path answered 404 and the other was refused: refused is not "no", so it stays out of the share.
        self.assertEqual(by['a2a']['refused'],1)
        self.assertEqual(by['a2a']['answered'],0)
        self.assertEqual(by['a2a']['found'],0)
        for s in rep['signals']:
            self.assertEqual(s['answered'], s['found']+s['not_found'])
            self.assertIsNone(DASH.search(s['prose']))
            self.assertNotIn('official', s['prose'].lower())
        self.assertIn('Refused is not "no"', rep['newsletter_text'])
        self.assertIsNone(DASH.search(rep['newsletter_text']))

    def test_nov9_crawl_matches_the_brief(self):
        path=os.path.join(DATA,'crawl-2026-11-09.json')
        prev=os.path.join(DATA,'crawl-2026-11-02.json')
        if not (os.path.exists(path) and os.path.exists(prev)):
            self.skipTest('historical crawl files are not in this checkout')
        cur=json.load(open(path)); old=json.load(open(prev))
        rep=beyond_ucp.report(cur['sites'],cur['retailers'],cur['crawl_date'],old['sites'],old['retailers'],old['crawl_date'])
        by={s['key']:s for s in rep['signals']}
        self.assertEqual(rep['phase2_reached'],2865)
        self.assertEqual(by['llms_txt']['found'],226)
        self.assertEqual(by['llms_txt']['refused'],1217)
        self.assertEqual(by['llms_txt']['error'],67)
        self.assertEqual(by['llms_txt']['answered'],1581)
        self.assertEqual(by['llms_txt']['share_display'],'14.3%')
        self.assertEqual(by['llms_txt']['found_change'],-2)
        self.assertEqual(by['agents_md']['found'],31)
        self.assertEqual(by['mcp_tools']['found'],8)
        self.assertEqual(by['ai_catalog']['found'],3)
        self.assertEqual(by['acp']['found'],1)
        self.assertEqual(by['robots_ai']['found'],312)
        self.assertEqual(by['content_signals']['found'],75)
        # Share is not "found / every website reached".
        self.assertNotEqual(by['llms_txt']['share_display'], f'{(100*226/2865):.1f}%')
        self.assertEqual(by['acp']['stores'][0]['name'],'alphonsomango.in')
        self.assertEqual(by['poppy']['stores'][0]['name'],'Etsy')
        self.assertEqual(by['a2a']['found'],0)
        self.assertEqual(by['a2a']['store_count'],0)
        for s in rep['signals']:
            self.assertEqual(s['answered'], s['found']+s['not_found'])
            if s['refused']:
                self.assertLess(s['answered'], s['found']+s['not_found']+s['refused'])

class NewsletterTemplate(unittest.TestCase):
    def test_weekly_template_requires_the_generated_block(self):
        t=open(os.path.join(ROOT,'newsletter','weekly','template.md'),encoding='utf-8').read()
        self.assertIn('data/beyond-ucp-latest.md', t)
        self.assertIn('data/beyond-ucp-latest.json', t)
        self.assertIn('a refusal is not "no"', t)
        self.assertNotIn("don't mention", t.lower())
        self.assertIsNone(DASH.search(t))


@unittest.skipUnless(os.path.exists(os.path.join(DIST,'signals.html')) and os.path.exists(os.path.join(DATA,'beyond-ucp-latest.json')),'dist or beyond-ucp json not built')
class RenderedBeyondUcp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rep=json.load(open(os.path.join(DATA,'beyond-ucp-latest.json'),encoding='utf-8'))
        cls.home=open(os.path.join(DIST,'index.html'),encoding='utf-8').read()
        cls.signals=open(os.path.join(DIST,'signals.html'),encoding='utf-8').read()
        cls.changes=open(os.path.join(DIST,'changes.html'),encoding='utf-8').read()
        cls.md=open(os.path.join(DATA,'beyond-ucp-latest.md'),encoding='utf-8').read()

    def _row(self, sig):
        return f'<td>{comma(sig["found"])}</td><td>{comma(sig["answered"])}</td><td>{sig["share_display"]}</td>'

    def test_home_keeps_ucp_headline_and_shows_counts(self):
        h=self.home
        self.assertIn('<h1>What online stores tell AI shopping agents</h1>', h)
        self.assertIn('It\'s called a <a href="https://ucp.dev/">UCP</a> profile.', h)
        self.assertLess(h.index('<h1>'), h.index('id="beyond-ucp"'))
        self.assertIn('href="signals.html">Beyond UCP</a>', h)
        self.assertIn('Refused is not "no"', h)
        for sig in self.rep['signals']:
            self.assertIn(self._row(sig), h)
            self.assertIn(sig['wow'], h)

    def test_signals_page_lists_signals_stores_and_methodology(self):
        h=self.signals
        self.assertEqual(len(re.findall(r'<h1[ >]', h)), 1)
        self.assertIn('href="methodology.html#signals"', h)
        self.assertIn('id="signals"', open(os.path.join(DIST,'methodology.html'),encoding='utf-8').read())
        self.assertIn('<loc>https://shopbotindex.com/signals.html</loc>', open(os.path.join(DIST,'sitemap.xml'),encoding='utf-8').read())
        self.assertIn('signals.html', open(os.path.join(DIST,'llms.txt'),encoding='utf-8').read())
        for sig in self.rep['signals']:
            self.assertIn(f'id="{sig["id"]}"', h)
            self.assertIn(self._row(sig), h)
            self.assertIn(html.escape(sig['prose']), h)
            for store in sig['stores']:
                self.assertIn(f'href="{html.escape(store["path"], quote=True)}"', h)
                self.assertTrue(os.path.exists(os.path.join(DIST, store['path'])), store['path'])
        copies=' '.join(re.findall(r'class="sig-copy">(.*?)</(?:p|li)>', h, re.S))
        self.assertIsNone(DASH.search(copies))
        self.assertNotIn('official', copies.lower())
        self.assertNotIn('primelogic', copies.lower())
        self.assertNotIn('stathopoulos', copies.lower())
        self.assertNotIn('switzerland', copies.lower())
        self.assertNotIn("can't shop", copies.lower())
        self.assertNotIn('cannot shop', copies.lower())

    def test_changes_page_and_newsletter_block_match_the_json(self):
        self.assertIn('id="beyond-ucp"', self.changes)
        self.assertIn('Refused is not "no"', self.changes)
        for sig in self.rep['signals']:
            self.assertIn(self._row(sig), self.changes)
            self.assertIn(sig['wow'], self.changes)
        self.assertEqual(self.md, self.rep['newsletter_text'])
        self.assertIn(f"Agent-readiness pass: {comma(self.rep['phase2_reached'])} websites reached.", self.md)
        self.assertIsNone(DASH.search(self.md))
        for bad in ('official','PrimeLogic','Stathopoulos','Switzerland'):
            self.assertNotIn(bad, self.md)
        # JSON is the reusable artifact: denominators are explicit and HTML is not stored.
        self.assertIn('denominator', self.rep)
        self.assertNotIn('sentence_html', json.dumps(self.rep))
        for sig in self.rep['signals']:
            self.assertEqual(sig['answered'], sig['found']+sig['not_found'])


if __name__=='__main__':
    unittest.main()
