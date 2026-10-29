"""The methodology page publishes the 26 Oct couldn't-check split with exact counts."""
import os, unittest
DIST=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'dist')
R=lambda p: open(os.path.join(DIST,p),encoding='utf-8').read()
class T(unittest.TestCase):
    def test_methodology_split(self):
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
    def test_home_line_while_oct26(self):
        h=R('index.html')
        # live crawl is still 26 Oct; home should carry the short line
        if 'Crawl of 2026-10-26' in open(os.path.join(DIST,'index.html'),encoding='utf-8').read() or '2026-10-26' in h:
            self.assertIn('Of those 627 on 26 October 2026',h)
            self.assertIn('methodology.html#couldnt-check',h)
if __name__=='__main__':
    unittest.main()
