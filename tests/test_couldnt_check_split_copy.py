"""Home and methodology couldn't-check split copy.

The home line is built from the current crawl's date and couldnt_check_split (filtered
retailers, same cut as build.py). Methodology keeps a fixed historical example from the
first week the split shipped (26 October 2026); that paragraph is intentional documentation,
not the live crawl.
"""
import os, json, sys, unittest, datetime as _dt
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT,'scripts'))
from nonshops import IDS as NON_SHOPS
DIST=os.path.join(ROOT,'dist')
DATA=os.path.join(ROOT,'data')
R=lambda p: open(os.path.join(DIST,p),encoding='utf-8').read()

def _day_long(d):
    x=_dt.date.fromisoformat(d)
    return f'{x.day} {x.strftime("%B")} {x.year}'

class T(unittest.TestCase):
    def test_methodology_split_historical_example(self):
        # Documented first-week example in methodology.html (build.py keeps these figures).
        h=R('methodology.html')
        self.assertIn('id="couldnt-check"',h)
        self.assertIn('26 October 2026',h)
        for n in ('627','77','240','303','7'):
            self.assertIn(n,h)
        self.assertIn('robots.txt',h)
        self.assertIn('401',h)
        self.assertIn('403',h)
        self.assertIn('429',h)
        self.assertIn('451',h)
        # wording rules
        self.assertNotIn('official',h.lower().replace('chiqueofficial',''))  # store domains may contain the letters
        self.assertNotIn("can't buy",h.lower())
        self.assertNotIn('cannot buy',h.lower())
        self.assertIn('never described as having no profile',h)
        self.assertIn('does not say what AI shopping agents see',h)

    def test_home_line_matches_current_crawl(self):
        h=R('index.html')
        latest=json.load(open(os.path.join(DATA,'latest.json')))
        chg=json.load(open(os.path.join(DATA,'changes-latest.json')))
        day=latest['crawl_date']
        day_long=_day_long(day)
        ret=[r for r in latest['retailers'] if r['id'] not in NON_SHOPS]
        s=chg['couldnt_check_split']
        cc=sum(1 for r in ret if r['status']=='couldnt_check')
        self.assertEqual(s['total'],cc)
        needle=f'Of those {cc} on {day_long}'
        self.assertIn(needle,h)
        self.assertIn(f'{s["robots_disallow"]} robots.txt disallow',h)
        self.assertIn(f'{s["blocked"]} refused (401/403/429/451)',h)
        self.assertIn(f'{s["error"]} timeout or connection error',h)
        self.assertIn(f'{s["mixed"]} mixed',h)
        self.assertIn('methodology.html#couldnt-check',h)
        # Footer crawl date must match latest.json (ISO form).
        self.assertIn(f'Crawl of {day}',h)

if __name__=='__main__':
    unittest.main()
