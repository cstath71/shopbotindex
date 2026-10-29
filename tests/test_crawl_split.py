"""Offline tests for the couldn't-check split in scripts/crawl.py (robots vs blocked vs challenge vs error)."""
import os, sys, json, unittest, unittest.mock as mock
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
import crawl as C

class ChallengeDetect(unittest.TestCase):
    def test_cf_mitigated_header(self):
        self.assertTrue(C.is_challenge(403, {'cf-mitigated': 'challenge'}, b''))
    def test_bare_403_not_challenge(self):
        self.assertFalse(C.is_challenge(403, {}, b'Forbidden'))
        self.assertFalse(C.is_challenge(403, {'server': 'cloudflare'}, b'{"error":"denied"}'))
    def test_body_markers(self):
        self.assertTrue(C.is_challenge(403, {}, b'<html>Just a moment...</html>'))
        self.assertTrue(C.is_challenge(503, {}, b'Checking your browser before accessing shop.example'))
        self.assertFalse(C.is_challenge(404, {}, b'Just a moment'))  # wrong status
    def test_none_status(self):
        self.assertFalse(C.is_challenge(None, {}, b'Just a moment'))

class CouldntCheckReason(unittest.TestCase):
    def test_robots_only(self):
        self.assertEqual(C.couldnt_check_reason([{'status': 'robots_disallow'}, {'status': 'robots_disallow'}]), 'robots_disallow')
    def test_challenge_beats_blocked(self):
        sites = [{'status': 'blocked', 'challenge': False, 'http_status': 403},
                 {'status': 'blocked', 'challenge': True, 'http_status': 403}]
        self.assertEqual(C.couldnt_check_reason(sites), 'challenge')
    def test_blocked_without_challenge(self):
        self.assertEqual(C.couldnt_check_reason([{'status': 'blocked', 'challenge': False, 'http_status': 403}]), 'blocked')
    def test_error(self):
        self.assertEqual(C.couldnt_check_reason([{'status': 'error'}]), 'error')
    def test_mixed_robots_and_error_prefers_robots(self):
        self.assertEqual(C.couldnt_check_reason([{'status': 'robots_disallow'}, {'status': 'error'}]), 'robots_disallow')
    def test_aggregate_sets_reason_only_on_cc(self):
        seed = {'id': 'ex.com'}
        ucp_site = {'status': 'ucp', 'ucp': {'capabilities': [], 'payment_handlers': [], 'platform_hint': ''}}
        r = C.aggregate(seed, [ucp_site])
        self.assertEqual(r['status'], 'ucp')
        self.assertNotIn('couldnt_check_reason', r)
        r2 = C.aggregate(seed, [{'status': 'blocked', 'challenge': True, 'http_status': 403}])
        self.assertEqual(r2['status'], 'couldnt_check')
        self.assertEqual(r2['couldnt_check_reason'], 'challenge')

class CrawlOneSplit(unittest.TestCase):
    def tearDown(self):
        C.ROBOTS_TXT.clear()
    def _patch_fetch(self, routes):
        """routes: url -> (status, ct, final, body, headers) or Exception string for transport error."""
        def fake(url):
            r = routes.get(url)
            if r is None:
                return None, 'URLError: missing', url, b'', {}
            if isinstance(r, tuple) and r[0] is None:
                return r if len(r) == 5 else (None, r[1], url, b'', {})
            return r
        return mock.patch.object(C, 'fetch', side_effect=fake)
    def test_robots_disallow(self):
        routes = {
            'https://ex.com/robots.txt': (200, 'text/plain', 'https://ex.com/robots.txt',
                                          b'User-agent: *\nDisallow: /.well-known/\n', {}),
        }
        with self._patch_fetch(routes), mock.patch.object(C.time, 'sleep'):
            out = C.crawl_one({'domain': 'ex.com'})
        self.assertEqual(out['status'], 'robots_disallow')
        self.assertNotIn('challenge', out)
    def test_blocked_plain_403(self):
        routes = {
            'https://ex.com/robots.txt': (200, 'text/plain', 'https://ex.com/robots.txt', b'User-agent: *\nAllow: /\n', {}),
            'https://ex.com/.well-known/ucp': (403, 'text/html', 'https://ex.com/.well-known/ucp', b'Forbidden', {}),
        }
        with self._patch_fetch(routes), mock.patch.object(C.time, 'sleep'):
            out = C.crawl_one({'domain': 'ex.com'})
        self.assertEqual(out['status'], 'blocked')
        self.assertEqual(out['http_status'], 403)
        self.assertIs(out['challenge'], False)
    def test_blocked_challenge(self):
        body = b'<html><title>Just a moment...</title><div id="cf-challenge-platform"></div></html>'
        routes = {
            'https://ex.com/robots.txt': (200, 'text/plain', 'https://ex.com/robots.txt', b'User-agent: *\nAllow: /\n', {}),
            'https://ex.com/.well-known/ucp': (403, 'text/html', 'https://ex.com/.well-known/ucp', body,
                                              {'cf-mitigated': 'challenge'}),
        }
        with self._patch_fetch(routes), mock.patch.object(C.time, 'sleep'):
            out = C.crawl_one({'domain': 'ex.com'})
        self.assertEqual(out['status'], 'blocked')
        self.assertTrue(out['challenge'])
    def test_ucp_ok_unchanged(self):
        doc = json.dumps({'ucp': {'version': '2026-01-01', 'capabilities': {}, 'services': {}}}).encode()
        routes = {
            'https://ex.com/robots.txt': (404, 'text/plain', 'https://ex.com/robots.txt', b'', {}),
            'https://ex.com/.well-known/ucp': (200, 'application/json', 'https://ex.com/.well-known/ucp', doc, {}),
        }
        with self._patch_fetch(routes), mock.patch.object(C.time, 'sleep'):
            out = C.crawl_one({'domain': 'ex.com'})
        self.assertEqual(out['status'], 'ucp')
        self.assertNotIn('challenge', out)

if __name__ == '__main__':
    unittest.main()
