"""The What changed page describes each joined store by what the previous crawls actually saw. Run after python3 scripts/build.py."""
import os, re, json, glob, html, unittest
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DIST=os.path.join(ROOT,'dist'); DATA=os.path.join(ROOT,'data')
T=lambda h: re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',h))).strip()
def dlong(d):
    import datetime; x=datetime.date.fromisoformat(d); return f'{x.day} {x.strftime("%B")} {x.year}'
@unittest.skipUnless(os.path.exists(os.path.join(DIST,'changes.html')) and os.path.exists(os.path.join(DATA,'changes-latest.json')),'dist or diff not built')
class JoinedWording(unittest.TestCase):
    def test_joined_lines_match_previous_status(self):
        chg=json.load(open(os.path.join(DATA,'changes-latest.json'))); pv=dlong(chg['previous']); cu=dlong(chg['current'])
        crawls=[d for d in (json.load(open(f)) for f in sorted(glob.glob(os.path.join(DATA,'crawl-*.json')))) if 'retailers' in d]
        st=lambda d,i: next((r['status'] for r in d['retailers'] if r['id']==i),None)
        prev=next(d for d in crawls if d['crawl_date']==chg['previous'])
        h=open(os.path.join(DIST,'changes.html')).read()
        sec=re.search(r'<h2>Joined:.*?</h2>(.*?)<h2>',h,re.S).group(1)
        items={T(re.search(r'<a [^>]*>(.*?)</a>',li).group(1)):T(li) for li in re.findall(r'<li>(.*?)</li>',sec,re.S)}
        nm={r['id']:r['name'] for r in crawls[-1]['retailers']}
        self.assertEqual(len(items),len(chg['joined']))
        for i in chg['joined']:
            line=items[nm[i]]; ps=st(prev,i)
            earlier=[d['crawl_date'] for d in crawls if d['crawl_date']<chg['previous'] and st(d,i)=='ucp']
            if ps=='couldnt_check':
                self.assertIn(f"we couldn't check it on {pv}; it publishes a profile now.",line,i); self.assertNotIn('no UCP profile found',line,i)
            elif earlier:
                self.assertIn(f"UCP profile found on {dlong(earlier[-1])}, none found on {pv}; it publishes one again on {cu}.",line,i)
            else:
                self.assertEqual(ps,'no_ucp',i); self.assertIn(f"no UCP profile found on {pv}, profile found on {cu}.",line,i)
if __name__=='__main__': unittest.main()
