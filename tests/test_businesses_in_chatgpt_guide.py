"""The 10 November 2026 guide keeps the approved Businesses in ChatGPT copy.

Run after python3 scripts/build.py.
"""
import os, re, json, html, unittest
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST=os.path.join(ROOT,'dist')
SRC=os.path.join(ROOT,'content','guides','businesses-in-chatgpt.md')
PAGE='guides/businesses-in-chatgpt/index.html'
URL='https://shopbotindex.com/guides/businesses-in-chatgpt/'
TITLE='Businesses in ChatGPT: what it means for online stores'
DESC="What OpenAI's Businesses in ChatGPT launch means for online stores, and what ShopBot Index can and cannot see in its 9 November 2026 crawl."
R=lambda p: open(os.path.join(DIST,p),encoding='utf-8').read()

def _lds(h):
    return [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>',h,re.S)]

def _txt(s):
    return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',s))).strip()

def _md_lines(md):
    lines=[]
    for line in md.splitlines():
        if line.startswith('### '): line=line[4:]
        elif line.startswith('## '): line=line[3:]
        elif line.startswith('# '): line=line[2:]
        elif line.startswith('- '): line=line[2:]
        line=re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',line).replace('`','')
        if line.strip(): lines.append(line.strip())
    return lines

def _article_lines(page):
    art=re.search(r'<article class="prose">(.*)</article>',page,re.S).group(1)
    art=re.sub(r'<p class="muted crumbs">.*?</p>','',art,count=1,flags=re.S)
    art=re.sub(r'<p class="muted" id="published">.*?</p>','',art,count=1,flags=re.S)
    lines=[]
    for part in re.split(r'</(?:p|h1|h2|h3|li)>',art):
        part=_txt(part)
        if part: lines.append(part)
    return lines

def _visible_faq(page):
    art=re.search(r'<article class="prose">(.*)</article>',page,re.S).group(1)
    parts=re.split(r'<h3>(.*?)</h3>',art)
    pairs=[]
    it=iter(parts[1:])
    for q, body in zip(it, it):
        paras=re.findall(r'<p[^>]*>(.*?)</p>', body, re.S)
        pairs.append((_txt(q), _txt(' '.join(paras))))
    return pairs

class BusinessesInChatgptGuide(unittest.TestCase):
    def test_page_exists_and_lead_paragraph_is_present(self):
        path=os.path.join(DIST, PAGE)
        self.assertTrue(os.path.isfile(path), PAGE)
        h=R(PAGE)
        src=open(SRC,encoding='utf-8').read()
        lead=src.split('\n\n',2)[1]
        self.assertTrue(lead.startswith('OpenAI launched Businesses in ChatGPT in beta on 10 November 2026.'))
        self.assertIn(f'<p class="lede">{lead}</p>', h)
        self.assertIn(f'<link rel="canonical" href="{URL}">', h)
        self.assertIn(f'<meta name="description" content="{html.escape(DESC, quote=True)}">', h)
        self.assertIn('href="../../style.css"', h)
        self.assertIn('href="../../guides/">Guides</a>', h)
        self.assertIn('hello@shopbotindex.com', h)
        self.assertEqual(_article_lines(h), _md_lines(src))

    def test_faq_jsonld_matches_visible_text(self):
        h=R(PAGE)
        visible=_visible_faq(h)
        self.assertEqual(len(visible), 3)
        graph=_lds(h)[0]['@graph']
        faq=[x for x in graph if x.get('@type')=='FAQPage']
        self.assertEqual(len(faq), 1)
        got=[(q['name'], q['acceptedAnswer']['text']) for q in faq[0]['mainEntity']]
        self.assertEqual(got, visible)
        for q, a in got:
            self.assertIn(f'<h3>{q}</h3>', h)
            self.assertIn(f'<p>{a}</p>', h)
        art=[x for x in graph if x.get('@type')=='Article'][0]
        self.assertEqual(art['headline'], TITLE)
        self.assertEqual(art['description'], DESC)
        self.assertEqual(art['datePublished'], '2026-11-10')
        self.assertEqual(art['dateModified'], '2026-11-10')
        self.assertEqual(art['mainEntityOfPage']['@id'], URL)
        self.assertIn('<time datetime="2026-11-10">10 November 2026</time>', h)
        self.assertIn('<time datetime="2026-11-10" id="modified">10 November 2026</time>', h)

    def test_listed_in_sitemap_guides_index_and_llms(self):
        sm=R('sitemap.xml')
        self.assertEqual(sm.count('businesses-in-chatgpt'), 1)
        self.assertIn(f'<loc>{URL}</loc><lastmod>2026-11-10</lastmod>', sm)
        self.assertNotIn('guides/businesses-in-chatgpt.html', sm)
        self.assertNotIn('guides/businesses-in-chatgpt/index.html', sm)
        hub=R('guides/index.html')
        self.assertIn(f'href="businesses-in-chatgpt/">{html.escape(TITLE)}</a>', hub)
        self.assertIn(html.escape(DESC, quote=True), hub)
        line=f'- [{TITLE}]({URL}): {DESC}'
        self.assertIn(line, R('llms.txt'))
        self.assertIn(line, R('llms-full.txt'))
        self.assertIn('href="https://openai.com/index/introducing-businesses-chatgpt/"', R(PAGE))
