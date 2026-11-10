"""The 8 November 2026 guide keeps the approved public copy and the 2 November crawl figures.

Run after python3 scripts/build.py.
"""
import os, re, json, html, collections, unittest, datetime
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST=os.path.join(ROOT,'dist')
SRC=os.path.join(ROOT,'content','guides','what-a-ucp-profile-proves.md')
PAGE='guides/what-a-ucp-profile-proves/index.html'
URL='https://shopbotindex.com/guides/what-a-ucp-profile-proves/'
DESC='Understand what a published UCP profile tells you, why unchecked stores stay unknown, and how to read ShopBot Index results without overstating them.'
R=lambda p: open(os.path.join(DIST,p),encoding='utf-8').read()

def _lds(h):
    return [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>',h,re.S)]

def _md_lines(md):
    lines=[]
    for line in md.splitlines():
        if line.startswith('# '): line=line[2:]
        elif line.startswith('## '): line=line[3:]
        elif line.startswith('- '): line=line[2:]
        line=re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',line).replace('`','')
        if line.strip(): lines.append(line.strip())
    return lines

def _article_lines(page):
    art=re.search(r'<article class="prose">(.*)</article>',page,re.S).group(1)
    art=re.sub(r'<p class="muted crumbs">.*?</p>','',art,count=1,flags=re.S)
    art=re.sub(r'<p class="muted" id="published">.*?</p>','',art,count=1,flags=re.S)
    art=re.sub(r'<div class="answer" id="summary">.*?</div>','',art,count=1,flags=re.S)
    art=re.sub(r'<div class="box faq" id="faq">.*?</div>','',art,count=1,flags=re.S)
    lines=[]
    for part in re.split(r'</(?:p|h1|h2|li)>',art):
        part=html.unescape(re.sub(r'<[^>]+>','',part)).strip()
        if part: lines.append(part)
    return lines

@unittest.skipUnless(os.path.exists(os.path.join(DIST,PAGE)),'dist not built')
class Guide(unittest.TestCase):
    def test_exact_public_copy(self):
        src=open(SRC,encoding='utf-8').read()
        self.assertEqual(_article_lines(R(PAGE)), _md_lines(src))
        h=R(PAGE)
        self.assertIn('publishes a UCP profile',h)
        self.assertIn('or certified an integration',h)
        self.assertNotIn('is certified',h.lower())
        self.assertNotIn('we certify',h.lower())
        self.assertNotIn('official',h.lower())
        for bad in ('PrimeLogic','Stathopoulos','Switzerland'):
            self.assertNotIn(bad,h)
            self.assertNotIn(bad,R('guides/index.html'))
            self.assertNotIn(bad,src)

    def test_figures_match_2_nov_crawl_not_a_recrawl(self):
        # Approved figures are retailer/store entries from the saved 2 November crawl.
        D=json.load(open(os.path.join(ROOT,'data','crawl-2026-11-02.json'),encoding='utf-8'))
        self.assertEqual(D['crawl_date'],'2026-11-02')
        st=collections.Counter(r['status'] for r in D['retailers'])
        self.assertEqual((st['ucp'],st['no_ucp'],st['couldnt_check']), (947,1277,630))
        self.assertEqual(st['ucp']+st['no_ucp'],2224)
        h=R(PAGE)
        self.assertIn('Our 2 November 2026 crawl recorded 947 positive retailer/store entries among 2,224 we could check.',h)
        self.assertIn('Another 630 tracked entries were marked "couldn\'t check".',h)
        self.assertIn('The remaining 1,277 checkable entries had no profile found under our checks.',h)
        self.assertIn('Do not read the figures as a count of distinct corporate owners or as a retail-wide adoption rate.',h)

    def test_route_canonical_meta_and_single_copy(self):
        h=R(PAGE)
        self.assertIn(f'<link rel="canonical" href="{URL}">',h)
        self.assertIn(f'<meta property="og:url" content="{URL}">',h)
        self.assertIn('property="og:type" content="article"',h)
        self.assertIn(f'<meta name="description" content="{DESC}">',h)
        self.assertIn('<meta name="viewport" content="width=device-width,initial-scale=1">',h)
        self.assertEqual(len(re.findall(r'<h1[ >]',h)),1)
        self.assertIn('href="../../style.css"',h)
        sm=R('sitemap.xml')
        self.assertEqual(sm.count('what-a-ucp-profile-proves'),1)
        day=json.load(open(os.path.join(ROOT,'data','latest.json'),encoding='utf-8'))['crawl_date']
        stamp=max('2026-11-11', day)
        self.assertIn(f'<loc>{URL}</loc><lastmod>{stamp}</lastmod>',sm)
        self.assertIn(f'<loc>https://shopbotindex.com/guides/</loc><lastmod>{stamp}</lastmod>',sm)
        # Home lastmod is the crawl date build.py stamps from data/latest.json (not a fixed Monday).
        day=json.load(open(os.path.join(ROOT,'data','latest.json'),encoding='utf-8'))['crawl_date']
        self.assertRegex(day,r'^\d{4}-\d{2}-\d{2}$')
        datetime.date.fromisoformat(day)
        self.assertIn(f'<loc>https://shopbotindex.com/</loc><lastmod>{day}</lastmod>',sm)
        self.assertNotIn('guides/what-a-ucp-profile-proves.html',sm)
        self.assertNotIn('guides/what-a-ucp-profile-proves/index.html',sm)
        self.assertIn(URL,R('llms.txt'))
        self.assertIn('https://shopbotindex.com/guides/',R('llms.txt'))

    def test_discoverable_links(self):
        self.assertIn('href="guides/"',R('index.html'))
        self.assertIn('href="../guides/"',R('store/ikea.html'))
        self.assertIn('href="../../guides/">Guides</a>',R(PAGE))
        meth=R('methodology.html')
        self.assertIn('href="guides/what-a-ucp-profile-proves/">What a published UCP profile proves, and what it doesn\'t</a>',meth)
        self.assertIn('id="meaning"',meth)
        hub=R('guides/index.html')
        self.assertIn('href="what-a-ucp-profile-proves/"',hub)
        self.assertNotIn('index.html',re.search(r'<main>.*?</main>',hub,re.S).group(0))
        # approved outbound links, unchanged targets
        h=R(PAGE)
        self.assertIn('href="https://ucp.dev/specification/overview/"',h)
        self.assertIn('href="https://shopbotindex.com/methodology.html"',h)

    def test_article_schema_publication_date_only(self):
        h=R(PAGE)
        graph=_lds(h)[0]['@graph']
        art=[x for x in graph if x.get('@type')=='Article'][0]
        self.assertEqual(art['headline'],"What a published UCP profile proves, and what it doesn't")
        self.assertEqual(art['description'],DESC)
        day=json.load(open(os.path.join(ROOT,'data','latest.json'),encoding='utf-8'))['crawl_date']
        stamp=max('2026-11-11', day)
        self.assertEqual(art['datePublished'],'2026-11-08')
        self.assertEqual(art['dateModified'],stamp)
        self.assertIn(f'<time datetime="{stamp}" id="modified">',h)
        self.assertEqual(art['mainEntityOfPage']['@id'],URL)
        self.assertNotIn('author',art)
        self.assertEqual(art['publisher']['@id'],'https://shopbotindex.com/#org')
        org=[x for x in graph if x.get('@type')=='Organization'][0]
        self.assertEqual(org['name'],'ShopBot Index')
        self.assertNotIn('author',org)
        self.assertIn('<time datetime="2026-11-08">8 November 2026</time>',h)
        crumbs=[x for x in graph if x.get('@type')=='BreadcrumbList'][0]
        self.assertEqual([i['name'] for i in crumbs['itemListElement']],['ShopBot Index','Guides',art['headline']])
        self.assertEqual(crumbs['itemListElement'][-1]['item'],URL)
        # no person invented anywhere in this page's structured data
        self.assertNotIn('"@type": "Person"',json.dumps(graph))
        self.assertNotIn('"@type":"Person"',json.dumps(graph,separators=(',',':')))
