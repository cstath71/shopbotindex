"""What-changed page: totals, couldn't-check split, newly_tracked never counted as joined."""
import os, re, json, html, tempfile, shutil, unittest, subprocess, sys
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST=os.path.join(ROOT,'dist'); DATA=os.path.join(ROOT,'data')
T=lambda h: re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',h))).strip()

@unittest.skipUnless(os.path.exists(os.path.join(DIST,'changes.html')) and os.path.exists(os.path.join(DATA,'changes-latest.json')),'dist or diff not built')
class ChangesPageOct26(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h=open(os.path.join(DIST,'changes.html'),encoding='utf-8').read()
        cls.chg=json.load(open(os.path.join(DATA,'changes-latest.json')))
    def test_totals_match_chg(self):
        t=self.chg['totals']
        self.assertIn('id="totals"',self.h)
        self.assertEqual(t['ucp_previous'],770)
        self.assertEqual(t['ucp'],773)
        self.assertEqual(t['stores'],2179)
        self.assertEqual(t['stores_previous'],2179)
        needle_ucp='{0}</td><td>{1}</td>'.format(t['ucp_previous'],t['ucp'])
        self.assertIn(needle_ucp,self.h)
        needle_st='{0}</td><td>{1}</td>'.format(t['stores_previous'],t['stores'])
        self.assertIn(needle_st,self.h)
    def test_split_match_chg(self):
        s=self.chg['couldnt_check_split']
        self.assertEqual(s,dict(robots_disallow=77,blocked=240,error=303,mixed=7,total=627))
        self.assertIn('id="couldnt-split"',self.h)
        for n in ('77','240','303','7','627'):
            self.assertIn(n,self.h)
        self.assertIn('does not say what AI shopping agents see',self.h)
    def test_joined_unreachable_counts(self):
        self.assertEqual(len(self.chg['joined']),7)
        self.assertEqual(len(self.chg['now_unreachable']),4)
        self.assertEqual(len(self.chg['newly_tracked']),0)
        self.assertIn('Joined: newly publishing a UCP profile (7)',self.h)
        self.assertIn("Had a profile, now couldn't check (4)",self.h)
        for name in ('Debenhams','IKEA','On AG'):
            self.assertIn(name,self.h)
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
        # 26 Oct first full phase-2 week: most signals have comparable 0; a2a comparable > 0
        by={sc['key']:sc for sc in self.chg['signal_changes']}
        self.assertEqual(by['llms_txt']['now'], 852)
        self.assertEqual(by['acp']['now'], 1)
        self.assertEqual(by['a2a']['now'], 1)
        self.assertEqual(by['a2a']['previous'], 1)
        self.assertGreater(by['a2a']['comparable'], 0)
        self.assertEqual(len(by['llms_txt']['gained']), 0)  # no prior phase-2 check
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
