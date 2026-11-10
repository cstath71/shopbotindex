"""IndexNow URL selection. Recomputes the post-9-Nov set from dist/sitemap.xml. Does not call the network."""
import os, re, sys, unittest
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from indexnow import sitemap_entries, choose_urls
DIST=os.path.join(ROOT, 'dist')
SITE='https://shopbotindex.com'

@unittest.skipUnless(os.path.exists(os.path.join(DIST, 'sitemap.xml')), 'dist not built')
class IndexNow(unittest.TestCase):
    def test_since_drops_older_lastmod(self):
        xml='<url><loc>https://shopbotindex.com/old</loc><lastmod>2026-10-23</lastmod></url><url><loc>https://shopbotindex.com/new</loc><lastmod>2026-11-09</lastmod></url>'
        self.assertEqual(choose_urls(sitemap_entries(xml), '2026-11-09'), ['https://shopbotindex.com/new'])
        self.assertEqual(choose_urls(sitemap_entries(xml), None), ['https://shopbotindex.com/old', 'https://shopbotindex.com/new'])
    def test_since_9_nov_includes_signals_segments_stores_and_guides(self):
        urls=choose_urls(sitemap_entries(open(os.path.join(DIST, 'sitemap.xml')).read()), '2026-11-09')
        for path in ('', 'signals/acp/', 'signals/llms-txt/', 'signals/mcp/', 'signals/ai-bots-robots/',
                     'segments/', 'segments/big.html', 'segments/shopify.html', 'segments/other.html',
                     'stores.html', 'stores-2.html', 'stores-3.html',
                     'guides/', 'guides/what-is-a-ucp-profile/', 'guides/businesses-in-chatgpt/',
                     'guides/ai-shopping-readiness/',
                     'which-stores-declare-ucp-checkout/', 'payment-handlers/', 'check.html'):
            self.assertIn(SITE+'/'+path, urls, path)
        self.assertGreater(sum(1 for u in urls if '/store/' in u), 2000)
        self.assertLessEqual(len(urls), 10000)
    def test_workflow_pings_indexnow_after_deploy(self):
        y=open(os.path.join(ROOT, '.github', 'workflows', 'pages.yml')).read()
        deploy=y.index('actions/deploy-pages')
        ping=y.index('scripts/indexnow.py --since 2026-11-09')
        self.assertLess(deploy, ping)
