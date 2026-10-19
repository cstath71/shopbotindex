"""Offline tests for scripts/agent_files.py (no network). Run: python3 -m unittest discover -s tests"""
import os, sys, json, unittest
sys.path.insert(0,os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'scripts'))
import agent_files as AF
POPPY=json.dumps({"protocol_version":"0.1","organization":{"name":"Ex","domain":"ex.com"},"auth":{"issuer":"https://a.ex.com"},"apis":[{"type":"mcp","url":"https://m"}]}).encode()
CARD=json.dumps({"name":"Ex agent","version":"1.0","skills":[{"id":"a"},{"id":"b"}],"supportedInterfaces":[]}).encode()
def fake(routes,log):
    def f(url,ua,timeout,maxbytes,accept):
        log.append((url,ua)); r=routes.get(url,(404,b''))
        if r=='boom': raise RuntimeError('x')
        if r is None: return None,'TimeoutError: t',url,b''
        return r[0],'application/json',url,r[1]
    return f
class T(unittest.TestCase):
    def setUp(self): self.orig=AF._fetch; os.environ['SBI_AGENT_FILES']='1'
    def tearDown(self): AF._fetch=self.orig; os.environ.pop('SBI_AGENT_FILES',None)
    def run1(self,routes,site=None,cache=None,budget=60):
        log=[]; AF._fetch=fake(routes,log); s=site or dict(host='ex.com',status='no_ucp')
        summ=AF.run([s],'ShopBotIndexBot/1.0 (+https://shopbotindex.com/methodology.html#crawler; hello@shopbotindex.com; reads only /robots.txt and /.well-known/ucp)',pause=0,robots_cache=cache,budget=budget)
        return s,log,summ
    def test_valid_files(self):
        s,log,summ=self.run1({'https://ex.com/robots.txt':(200,b'User-agent: *\nAllow: /'),'https://ex.com/.well-known/poppy.json':(200,POPPY),'https://ex.com/.well-known/agent-card.json':(200,CARD)})
        a=s['agent_files']; self.assertTrue(a['poppy']['valid']); self.assertEqual(a['poppy']['summary']['api_types'],['mcp'])
        self.assertEqual(a['a2a_card']['summary']['skills'],2); self.assertEqual(a['a2a_card_legacy']['status'],404); self.assertEqual(a['requests'],5)
        self.assertEqual(summ['valid']['poppy'],1)
    def test_ua_honest_same_identity(self):
        s,log,_=self.run1({})
        ua=log[0][1]; self.assertTrue(ua.startswith('ShopBotIndexBot/1.0 (+https://shopbotindex.com/methodology.html#crawler; hello@shopbotindex.com;'))
        self.assertIn('poppy.json',ua); self.assertNotIn('reads only',ua)
        self.assertIn('poppy.json',AF.agent_ua('X/1 (+u; a)'))
    def test_soft_200_html_not_valid(self):
        s,_,_=self.run1({'https://ex.com/.well-known/poppy.json':(200,b'<!doctype html><html>app shell</html>')})
        self.assertFalse(s['agent_files']['poppy']['valid'])
    def test_robots_respected(self):
        s,log,_=self.run1({'https://ex.com/robots.txt':(200,b'User-agent: ShopBotIndexBot\nDisallow: /.well-known/poppy.json')})
        self.assertEqual(s['agent_files']['poppy']['status'],'robots_disallow')
        self.assertNotIn('https://ex.com/.well-known/poppy.json',[u for u,_ in log])
    def test_stop_after_refusal(self):
        s,log,_=self.run1({'https://ex.com/.well-known/poppy.json':(403,b'')})
        self.assertEqual(len(log),2); self.assertEqual(s['agent_files']['a2a_card']['status'],'not fetched')
    def test_robots_cache_and_phase2_ai_catalog(self):
        site=dict(host='ex.com',status='ucp',signals=dict(ai_catalog=dict(status=404)))
        s,log,_=self.run1({},site=site,cache={'https://ex.com':'User-agent: *\nAllow: /'})
        urls=[u for u,_ in log]; self.assertNotIn('https://ex.com/robots.txt',urls); self.assertNotIn('https://ex.com/.well-known/ai-catalog.json',urls)
        self.assertEqual(s['agent_files']['ai_catalog'],{'recorded_in':'signals.ai_catalog'}); self.assertEqual(s['signals'],dict(ai_catalog=dict(status=404)))
    def test_skips_unanswered_and_errors_never_raise(self):
        for st in ('error','blocked','robots_disallow'):
            s,log,_=self.run1({},site=dict(host='ex.com',status=st)); self.assertFalse(s['agent_files']['checked']); self.assertEqual(log,[])
        s,_,_=self.run1({'https://ex.com/robots.txt':'boom'}); self.assertFalse(s['agent_files']['checked'])
    def test_does_not_touch_existing_fields(self):
        site=dict(host='ex.com',status='ucp',ucp={'capabilities':['a']},http_status=200); before=json.dumps(site,sort_keys=True)
        s,_,_=self.run1({},site=site); s.pop('agent_files'); self.assertEqual(json.dumps(s,sort_keys=True),before)
    def test_budget(self):
        s,log,summ=self.run1({},budget=-1); self.assertEqual(s['agent_files']['reason'],'time budget reached'); self.assertEqual(log,[])
    def test_disabled_by_default_flag(self):
        os.environ.pop('SBI_AGENT_FILES'); log=[]; AF._fetch=fake({},log); s=dict(host='ex.com',status='ucp')
        r=AF.run([s],'UA (x)',pause=0)
        if not AF.ENABLED_DEFAULT: self.assertEqual(r,{'enabled':False}); self.assertNotIn('agent_files',s); self.assertEqual(log,[])
    def test_enabled_by_default_and_env_off(self):
        os.environ.pop('SBI_AGENT_FILES'); self.assertTrue(AF.ENABLED_DEFAULT); self.assertTrue(AF.enabled())
        os.environ['SBI_AGENT_FILES']='0'; self.assertFalse(AF.enabled())
        s=dict(host='ex.com',status='ucp'); self.assertEqual(AF.run([s],'UA (x)',pause=0),{'enabled':False}); self.assertNotIn('agent_files',s)
    def test_max_five_requests_and_no_ai_catalog_refetch_after_probe_error(self):
        s,log,_=self.run1({})
        self.assertEqual(len(log),5); self.assertEqual(s['agent_files']['requests'],5)
        site=dict(host='ex.com',status='no_ucp',signals=dict(checked=False,reason='probe error: AttributeError'))
        s,log,_=self.run1({},site=site); self.assertNotIn('https://ex.com/.well-known/ai-catalog.json',[u for u,_ in log]); self.assertEqual(len(log),4)
    def test_crawl_ua_lists_agent_files(self):
        import importlib.util as ilu
        sp=ilu.spec_from_file_location('sbi_crawl_t',os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'scripts','crawl.py')); cm=ilu.module_from_spec(sp); sp.loader.exec_module(cm)
        for f in ('poppy.json','agent-card.json','agent.json','ai-catalog.json'): self.assertIn('/.well-known/'+f,cm.UA)
        self.assertEqual(AF.agent_ua(cm.UA),cm.UA)
    def test_standalone_cli_writes_only_agent_files(self):
        import tempfile
        doc=dict(crawl_date='2026-10-19',sites=[dict(host='ex.com',domain='ex.com',status='no_ucp'),dict(host='www.b.com',domain='b.com',status='ucp'),dict(host='c.com',status='error')],retailers=[dict(id='Q1',status='ucp')])
        d=tempfile.mkdtemp(); p=os.path.join(d,'crawl.json'); json.dump(doc,open(p,'w')); hp=os.path.join(d,'hosts.txt'); open(hp,'w').write('# list\nhttps://b.com/\n')
        log=[]; AF._fetch=fake({},log)
        self.assertEqual(AF.main([p,'--dry-run']),0); self.assertEqual(json.load(open(p)),doc)
        orig=AF.run; AF.run=lambda sites,*a,**k: orig(sites,a[0],pause=0,budget=60)
        try: self.assertEqual(AF.main([p,'--hosts',hp]),0)
        finally: AF.run=orig
        out=json.load(open(p)); self.assertNotIn('agent_files',out['sites'][0]); self.assertTrue(out['sites'][1]['agent_files']['checked']); self.assertNotIn('agent_files',out['sites'][2])
        self.assertEqual(out['retailers'],doc['retailers']); self.assertEqual(out['timing']['agent_files']['sites_selected'],1)
        self.assertTrue(all(u.startswith('https://www.b.com/') for u,_ in log))
if __name__=='__main__': unittest.main()
