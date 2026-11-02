"""What-changed page: totals, couldn't-check split, newly_tracked never counted as joined.

Rendered-page checks read expected counts from data/changes-latest.json (and names from
data/latest.json, excluding non-shops the same way build.py does). They must stay free of
week-specific hardcoded dates or numbers so every Monday crawl can pass without rewriting
the tests.
"""
import os, re, json, html, tempfile, shutil, unittest, subprocess, sys
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT,'scripts'))
from nonshops import IDS as NON_SHOPS
DIST=os.path.join(ROOT,'dist'); DATA=os.path.join(ROOT,'data')
T=lambda h: re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',h))).strip()

@unittest.skipUnless(os.path.exists(os.path.join(DIST,'changes.html')) and os.path.exists(os.path.join(DATA,'changes-latest.json')),'dist or diff not built')
class ChangesPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h=open(os.path.join(DIST,'changes.html'),encoding='utf-8').read()
        cls.text=T(cls.h)
        cls.chg=json.load(open(os.path.join(DATA,'changes-latest.json')))
        latest_path=os.path.join(DATA,'latest.json')
        cls.latest=json.load(open(latest_path)) if os.path.exists(latest_path) else None
        cls.ret=[]
        cls.by_id={}
        if cls.latest:
            cls.ret=[r for r in cls.latest['retailers'] if r['id'] not in NON_SHOPS]
            cls.by_id={r['id']:r for r in cls.ret}

    def test_totals_match_chg(self):
        t=self.chg['totals']
        self.assertIn('id="totals"',self.h)
        # Cross-check totals against filtered retailers (same cut as build.py).
        if self.ret:
            self.assertEqual(t['stores'],len(self.ret))
            self.assertEqual(t['ucp'],sum(1 for r in self.ret if r['status']=='ucp'))
            self.assertEqual(t['no'],sum(1 for r in self.ret if r['status']=='no_ucp'))
            self.assertEqual(t['cc'],sum(1 for r in self.ret if r['status']=='couldnt_check'))
        self.assertEqual(t['stores'],self.chg['same_store']['n']+len(self.chg.get('newly_tracked',[])))
        needle_ucp='{0}</td><td>{1}</td>'.format(t['ucp_previous'],t['ucp'])
        self.assertIn(needle_ucp,self.h)
        needle_st='{0}</td><td>{1}</td>'.format(t['stores_previous'],t['stores'])
        self.assertIn(needle_st,self.h)

    def test_split_match_chg(self):
        s=self.chg['couldnt_check_split']
        self.assertEqual(s['total'],s['robots_disallow']+s['blocked']+s['error']+s['mixed'])
        if self.ret:
            self.assertEqual(s['total'],sum(1 for r in self.ret if r['status']=='couldnt_check'))
        self.assertIn('id="couldnt-split"',self.h)
        # Page shows this run's split figures in the couldn't-check table.
        for n in (str(s['robots_disallow']),str(s['blocked']),str(s['error']),str(s['mixed']),str(s['total'])):
            self.assertIn(n,self.h)
        self.assertIn('does not say what AI shopping agents see',self.h)

    def test_joined_unreachable_counts(self):
        n_joined=len(self.chg['joined'])
        n_unreach=len(self.chg['now_unreachable'])
        n_new=len(self.chg['newly_tracked'])
        self.assertIn(f'Joined: newly publishing a UCP profile ({n_joined})',self.h)
        self.assertIn(f"Had a profile, now couldn't check ({n_unreach})",self.h)
        self.assertIn('id="new"',self.h)
        # Every named joined / unreachable store must appear (HTML-escaped) on the page.
        for rid in self.chg['joined']+self.chg['now_unreachable']:
            name=(self.by_id.get(rid) or {}).get('name')
            if name:
                self.assertIn(html.escape(name),self.h)
        # Newly tracked stores must never be counted as joined.
        for rid in self.chg['newly_tracked']:
            self.assertNotIn(rid,self.chg['joined'])
        if n_new:
            self.assertIn(f'Newly tracked',self.h)

    def test_wording_rules(self):
        low=self.h.lower()
        # store domains may contain the letters "official"
        self.assertNotIn('official',low.replace('chiqueofficial',''))
        self.assertNotIn("can't buy",low)
        self.assertNotIn('cannot buy',low)
        self.assertNotIn('primelogic',low)
        self.assertNotIn('stathopoulos',low)
        self.assertNotIn('switzerland',low)
        self.assertIn('publishes a UCP profile',self.h)
        self.assertIn('Not counted as leaving',self.h)
        self.assertIn('id="new"',self.h)

    def test_signal_changes_section(self):
        self.assertIn('signal_changes', self.chg)
        self.assertGreaterEqual(len(self.chg['signal_changes']), 8)
        keys={sc['key'] for sc in self.chg['signal_changes']}
        for k in ('acp','ai_catalog','mcp_declared','mcp_tools','llms_txt','agents_md','robots_ai','a2a','access_answered'):
            self.assertIn(k, keys)
        self.assertIn('id="signals-changed"', self.h)
        self.assertIn('ACP discovery', self.h)
        self.assertIn('llms.txt', self.h)
        self.assertIn('A2A agent card', self.h)
        by={sc['key']:sc for sc in self.chg['signal_changes']}
        # Page must reflect this run's signal counts (not a prior week's numbers).
        for key in ('llms_txt','acp','a2a'):
            self.assertIn(str(by[key]['now']), self.h)
        self.assertGreaterEqual(by['a2a']['comparable'], 0)
        self.assertIn('Not found does not mean AI shopping agents', self.h)
        self.assertIn('never described as not found', self.h)

    def test_nav_and_home_link(self):
        idx=open(os.path.join(DIST,'index.html'),encoding='utf-8').read()
        self.assertIn('href="changes.html"',idx)
        self.assertIn('class="brand"',idx)  # logo stays left of name


class NewlyTrackedNotJoined(unittest.TestCase):
    """List expansion must never show newly tracked stores under Joined; signal gained requires both-week checks."""
    def test_synthetic_list_growth(self):
        def R(id,status,name,sg,caps=None):
            return dict(id=id,status=status,sites_checked=1,sites_with_ucp=1 if status=='ucp' else 0,
                        capabilities=caps or (['dev.ucp.shopping.cart'] if status=='ucp' else []),
                        payment_handlers=[],platforms=['Shopify'],signals=sg,
                        name=name,segment='shopify',category='x',country='US',sources=[])
        def S(rid,status,sg,af,http=200):
            return dict(rid=rid,domain=rid,host=rid,status=status,http_status=http,signals=sg,agent_files=af)
        sg_a_prev=dict(checked=True,acp=False,ai_catalog=False,mcp=dict(state='none_declared',tools=[]),
                       robots=dict(present=True,specific={},wildcard='allowed',content_signal=[]),
                       llms_txt=False,agents_md=False,guide_state='not_found',
                       product=dict(state='none',url=None),access=dict(state='answered',challenge=False,vendors=[]))
        sg_b_prev=dict(checked=True,acp=False,ai_catalog=False,mcp=dict(state='no_tools',tools=[]),
                       robots=dict(present=True,specific={'GPTBot':'blocked'},wildcard='allowed',content_signal=[]),
                       llms_txt=True,agents_md=True,guide_state='found',
                       product=dict(state='full',url='https://b.com/p'),access=dict(state='answered',challenge=False,vendors=[]))
        # a.com gains UCP + llms.txt; b.com loses a2a validity; new.com is newly tracked with UCP+acp
        sg_a_cur=dict(checked=True,acp=False,ai_catalog=False,mcp=dict(state='none_declared',tools=[]),
                      robots=dict(present=True,specific={},wildcard='allowed',content_signal=[]),
                      llms_txt=True,agents_md=False,guide_state='found',
                      product=dict(state='none',url=None),access=dict(state='answered',challenge=False,vendors=[]))
        sg_b_cur=dict(checked=True,acp=False,ai_catalog=False,mcp=dict(state='answered',tools=['search']),
                      robots=dict(present=True,specific={'GPTBot':'blocked'},wildcard='allowed',content_signal=[]),
                      llms_txt=True,agents_md=True,guide_state='found',
                      product=dict(state='full',url='https://b.com/p'),access=dict(state='answered',challenge=False,vendors=[]))
        sg_new=dict(checked=True,acp=True,ai_catalog=False,mcp=dict(state='none_declared',tools=[]),
                    robots=dict(present=True,specific={},wildcard='allowed',content_signal=[]),
                    llms_txt=False,agents_md=False,guide_state='not_found',
                    product=dict(state='none',url=None),access=dict(state='answered',challenge=False,vendors=[]))
        af_ok=dict(checked=True,a2a_card=dict(status=200,valid=True),a2a_card_legacy=dict(status=404),poppy=dict(status=404))
        af_no=dict(checked=True,a2a_card=dict(status=404,valid=False),a2a_card_legacy=dict(status=404),poppy=dict(status=404))
        prev=dict(crawl_date='2026-01-01', retailers=[
            R('a.com','no_ucp','A',sg_a_prev), R('b.com','ucp','B',sg_b_prev),
        ], sites=[
            S('a.com','no_ucp',dict(checked=True),af_no,404), S('b.com','ucp',dict(checked=True),af_ok),
        ])
        cur=dict(crawl_date='2026-01-08', retailers=[
            R('a.com','ucp','A',sg_a_cur), R('b.com','ucp','B',sg_b_cur),
            R('new.com','ucp','NewCo',sg_new),
        ], sites=[
            S('a.com','ucp',dict(checked=True),af_no), S('b.com','ucp',dict(checked=True),af_no),
            S('new.com','ucp',dict(checked=True),af_no),
        ])
        td=tempfile.mkdtemp(); dist=tempfile.mkdtemp()
        try:
            open(os.path.join(td,'crawl-2026-01-01.json'),'w').write(json.dumps(prev))
            open(os.path.join(td,'crawl-2026-01-08.json'),'w').write(json.dumps(cur))
            latest=dict(crawl_date='2026-01-08',user_agent='test',spec='https://ucp.dev/',path='/.well-known/ucp',
                        retailer_count=3,site_count=3,timing={},retailers=cur['retailers'],sites=cur['sites'])
            open(os.path.join(td,'latest.json'),'w').write(json.dumps(latest))
            open(os.path.join(td,'channels.json'),'w').write(json.dumps(dict(note='',checked_on='2026-01-08',channels=[])))
            env=os.environ.copy(); env['SBI_DATA_DIR']=td; env['SBI_DIST_DIR']=dist
            r=subprocess.run([sys.executable,os.path.join(ROOT,'scripts','build.py')],cwd=ROOT,env=env,capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr+r.stdout)
            chg=json.load(open(os.path.join(td,'changes-latest.json')))
            self.assertEqual(chg['joined'],['a.com'])
            self.assertEqual(chg['newly_tracked'],['new.com'])
            self.assertNotIn('new.com',chg['joined'])
            self.assertEqual(chg['same_store']['n'],2)
            by={sc['key']:sc for sc in chg['signal_changes']}
            self.assertEqual(by['llms_txt']['gained'],['a.com'])
            self.assertEqual(by['mcp_tools']['gained'],['b.com'])
            self.assertEqual(by['a2a']['lost'],['b.com'])
            self.assertEqual(by['acp']['first_seen'],['new.com'])
            self.assertNotIn('new.com', by['acp']['gained'])
            page=open(os.path.join(dist,'changes.html'),encoding='utf-8').read()
            joined_sec=re.search(r'<h2>Joined:.*?</h2>(.*?)<h2>',page,re.S).group(1)
            new_sec=re.search(r'<h2 id="new">Newly tracked.*?</h2>(.*?)(?:<h2|$)',page,re.S).group(1)
            self.assertIn('A',joined_sec)
            self.assertNotIn('NewCo',joined_sec)
            self.assertIn('NewCo',new_sec)
            self.assertIn('id="signals-changed"',page)
            self.assertIn('same stores tracked both weeks: 2 of 2, was 1',page)
        finally:
            shutil.rmtree(td,ignore_errors=True); shutil.rmtree(dist,ignore_errors=True)


if __name__=='__main__':
    unittest.main()
