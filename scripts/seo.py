"""SEO + answer-engine pass for the built ShopBot Index site (called once at the end of scripts/build.py).
Every number here is computed from the same crawl data (data/latest.json) the pages show; nothing is typed in by hand.
Adds: short visible "In short" summaries and FAQ blocks (home, methodology), JSON-LD (WebSite, Organization, Dataset,
FAQPage, BreadcrumbList) that only repeats what the page shows, visible breadcrumbs on segment/category/capability pages,
page-specific meta descriptions where a page used the site default, robots.txt with explicit AI-crawler groups, sitemap.xml
with lastmod, llms.txt + llms-full.txt, and the IndexNow key file."""
import os, re, json, html
INDEXNOW_KEY='35eae0974e7713ed6033cc8e281bc48d'  # public IndexNow key (served at /<key>.txt); scripts/indexnow.py pings with it
AI_BOTS=('GPTBot','OAI-SearchBot','ChatGPT-User','PerplexityBot','Perplexity-User','ClaudeBot','Claude-SearchBot','Claude-User','Google-Extended','Applebot','Applebot-Extended','Bingbot','Googlebot','DuckDuckBot')
def _txt(h): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',h))).strip()
def _ld(o): return '<script type="application/ld+json">'+json.dumps(o,ensure_ascii=False).replace('</','<\\/')+'</script>'
def _and(xs): return xs[0] if len(xs)==1 else ', '.join(xs[:-1])+' and '+xs[-1]
def _date(d):
    import datetime as dt; x=dt.date.fromisoformat(d); return f'{x.day} {x.strftime("%B")} {x.year}'

def run(g):
    DIST,SITE,NAME,DAY,RET,U,E=g['DIST'],g['SITE'],g['NAME'],g['DAY'],g['RET'],g['U'],g['E']
    SEG,SEGDESC,segstats,capn,slug,pct=g['SEG'],g['SEGDESC'],g['segstats'],g['capn'],g['slug'],g['pct']
    CONTACT=g['CONTACT']; CHG=g.get('CHG'); NEXTCRAWL=g.get('NEXTCRAWL'); nsites=len(g['SITES'])
    ALL=segstats(RET); SS={k:segstats([r for r in RET if r['segment']==k]) for k in SEG}
    ORG={"@type":"Organization","@id":SITE+"/#org","name":NAME,"url":SITE+"/","logo":SITE+"/logo-hd.png","email":CONTACT,"sameAs":["https://x.com/ShopBotIndex"]}
    segline=_and([f'{SEG[k].lower() if k!="shopify" else SEG[k]} {SS[k]["ucp"]} of {SS[k]["checked"]} ({SS[k]["rate"]})' for k in SEG])
    # ---- answer-first summaries ----
    home_sum=(f'In ShopBot Index\'s crawl of {_date(DAY)}, {ALL["ucp"]} of the {ALL["checked"]} retailers and stores we could check publish a UCP profile, '
              f'the profile AI shopping agents read ({ALL["rate"]}). By segment: {segline}. '
              f'We couldn\'t check {ALL["cc"]} of the {ALL["n"]} we track (blocked or unreachable), so they aren\'t counted, and we re-check every store each Monday.')
    meth_sum=(f'Once a week our crawler, ShopBotIndexBot, reads <code>/robots.txt</code> and then <code>/.well-known/ucp</code> on each of the {nsites} websites of the {ALL["n"]} retailers and stores we track, '
              f'plus a few supporting signals. Sites that refuse or fail our requests are marked "couldn\'t check" and left out of adoption rates. Latest crawl: {_date(DAY)}.')
    # ---- FAQs (question, answer HTML); answers use only facts shown on this site ----
    big=g['BIGU']; bign=[r['name'] for r in big]
    home_faq=[
     ('What is a UCP profile?','A Universal Commerce Protocol (UCP) profile is a JSON file a store publishes at <code>/.well-known/ucp</code>: the machine-readable profile AI shopping agents read. It lists the protocol version, services, capabilities (for example checkout, cart or catalog search) and payment handlers. <a href="methodology.html">How we check it</a>.'),
     ('How many online stores publish a UCP profile?',f'In our crawl of {_date(DAY)}, {ALL["ucp"]} of the {ALL["checked"]} retailers and stores we could check ({ALL["rate"]}). By segment: {segline}. These are shares of our list of {ALL["n"]}, not of all online stores.'),
     ('Which big retailers publish a UCP profile?',(f'{len(big)} in the crawl of {_date(DAY)}: {E(_and(bign))}.' if big else f'None in the crawl of {_date(DAY)}.')+f' That is {SS["big"]["ucp"]} of the {SS["big"]["checked"]} big retailers we could check. <a href="segments/big.html">See all big retailers</a>.'),
     ('What does it mean if a store has no UCP profile?','Only that we found no profile at <code>/.well-known/ucp</code>. Some agent shopping runs through a normal web browser or through channels we can\'t see from outside, such as product feeds shared privately with AI assistants. Equally, a UCP profile isn\'t proof that AI agents can shop at a store.'),
     ('How often is ShopBot Index updated?',f'Every week. The crawl runs on Mondays; the latest was on {_date(DAY)}'+(f' and the next is due on {NEXTCRAWL}' if NEXTCRAWL else '')+'. <a href="changes.html">See what changed</a>.'),
     ('How can I check my own store?',f'Type its domain into <a href="check.html">Check your store</a>. It looks the domain up in our latest crawl. If the store isn\'t in the index yet, email <a href="mailto:{CONTACT}">{CONTACT}</a> and we\'ll include it in a future crawl.')]
    cm=g.get('CRAWLMETH',''); rq=re.search(r'usually (\d+) to (\d+) requests per website per week, and never more than (\d+)',cm)
    meth_faq=[
     ('What does ShopBot Index check on each website?','It reads <code>/robots.txt</code> first, then fetches <code>/.well-known/ucp</code>, where the UCP specification says a business publishes its profile. It also records supporting signals: an MCP endpoint named in the UCP profile, AI-agent rules in robots.txt, <code>/llms.txt</code> or <code>/agents.md</code>, and schema.org Product markup on one product page. <a href="methodology.html#signals">Details</a>.'),
     ('Why are some stores marked "couldn\'t check"?',f'Every one of their websites refused our request (401/403/429), timed out, failed TLS or DNS, or disallowed the path in robots.txt. We never try to get around that. These stores are shown separately and left out of adoption rates: {ALL["cc"]} of {ALL["n"]} in the crawl of {_date(DAY)}.'),
     ('Which stores are tracked?','Three segments, side by side: '+_and([f'{SEG[k]} ({SS[k]["n"]})' for k in SEG])+'. They come from Wikipedia and Wikidata lists and public lists of Shopify stores. This is not a random sample of all stores, so shares are shares of our list.')]
    if rq: meth_faq.append(('How many requests does the crawler send?',f'Usually {rq.group(1)} to {rq.group(2)} per website per week, and never more than {rq.group(3)}, one at a time per website, with robots.txt respected for every URL. <a href="methodology.html#crawler">How we fetch</a>.'))
    meth_faq+=[('How can a website opt out?',f'Disallow <code>/</code> (or just the paths we read) for <code>ShopBotIndexBot</code> in robots.txt, or email <a href="mailto:{CONTACT}">{CONTACT}</a>.'),
     ('Does ShopBot Index test purchases?','No. We don\'t test purchases, and we don\'t score or rank how well a store works with any assistant.')]
    def faq_html(faq): return '<div class="box faq" id="faq"><h2>Frequently asked questions</h2>'+''.join(f'<h3>{E(q)}</h3><p>{a}</p>' for q,a in faq)+'</div>'
    def faq_ld(faq): return {"@type":"FAQPage","mainEntity":[{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":_txt(a)}} for q,a in faq]}
    def sum_html(s): return f'<div class="answer" id="summary"><p><b>In short:</b> {s}</p></div>'
    DATASET={"@type":"Dataset","@id":SITE+"/#dataset","name":f"{NAME}: weekly crawl of UCP profiles","url":SITE+"/",
             "description":_txt(home_sum)+' Each record says whether the store publishes a UCP profile at /.well-known/ucp, and if so which capabilities and payment handlers it declares.',
             "creator":{"@id":SITE+"/#org"},"publisher":{"@id":SITE+"/#org"},"dateModified":DAY,
             "license":SITE+"/terms.html","copyrightNotice":f"© {DAY[:4]} {NAME}. All rights reserved.",
             "measurementTechnique":"HTTPS request for /.well-known/ucp on each website, after reading robots.txt",
             "variableMeasured":["Whether a UCP profile is published at /.well-known/ucp","Capabilities declared in the UCP profile","Payment handlers listed in the UCP profile"]}
    # ---- page-specific descriptions where the site default was used ----
    desc={'segments/index.html':f'Shopify stores, big retailers and other retailers & marketplaces side by side: how many of each publish a UCP profile, the profile AI shopping agents read, in the crawl of {_date(DAY)}.',
          'methodology.html':'How ShopBot Index measures: what our crawler reads on each website (robots.txt first, then /.well-known/ucp), what "couldn\'t check" means, and what a UCP profile does and doesn\'t tell you.',
          'about.html':'About ShopBot Index, the independent weekly index of what online stores tell AI shopping agents, and how to contact us.',
          'terms.html':'ShopBot Index terms of use: all rights reserved; you may link to pages and quote individual findings with credit; bulk copying or republishing the data needs written permission.',
          'privacy.html':'ShopBot Index privacy: what we store when you subscribe, cookie-free visit counts, and how to unsubscribe or ask for deletion.',
          'assistants.html':'Which AI assistants name which retailers for shopping, from the companies\' own announcements and help pages, with links and dates.',
          'capabilities/index.html':f'Capabilities declared in UCP profiles, counted per store, across the {len(U)} stores with a UCP profile in the crawl of {_date(DAY)}.',
          'categories/index.html':f'UCP profiles by store category and segment: how many stores in each category publish a UCP profile, crawl of {_date(DAY)}.'}
    for k in SEG: desc[f'segments/{k}.html']=f'{SEG[k]}: {SS[k]["ucp"]} of {SS[k]["checked"]} we could check publish a UCP profile ({SS[k]["rate"]}) in the crawl of {_date(DAY)}; {SS[k]["cc"]} couldn\'t be checked. By category, with every store listed.'
    for c in g['CATS']:
        s=segstats([r for r in RET if r['category']==c]); desc[f'categories/{slug(c)}.html']=f'{c}: {s["ucp"]} of {s["checked"]} stores we could check publish a UCP profile ({s["rate"]}) in the crawl of {_date(DAY)}; {s["cc"]} couldn\'t be checked.'
    for c,v in g['CAPC'].items(): desc[f'capabilities/{slug(c)}.html']=f'{capn(c)} ({c}): declared by {v} of the {len(U)} stores with a UCP profile ({pct(v,len(U))}) in the crawl of {_date(DAY)}, with the list of stores.'
    if CHG: desc['changes.html']=f'Which stores started or stopped publishing a UCP profile between the ShopBot Index crawls of {_date(CHG["previous"])} and {_date(DAY)}: {len(CHG["joined"])} joined, {len(CHG["left"])} left, {len(CHG["now_unreachable"])} couldn\'t be checked, {len(CHG["capability_changes"])} capability changes. Each store links to its result.'
    chg_faq=[
     ('What counts as a store joining?','A store we already tracked joins when our crawl now finds a UCP profile at <code>/.well-known/ucp</code> and the previous crawl found none or couldn\'t check it. Stores newly added to our list are shown as newly tracked, not as joining.'),
     ('What counts as a store leaving?','A store leaves when the previous crawl found a UCP profile and its website answered this time without one. If the website blocked our crawler or was unreachable, the store is listed under "couldn\'t check" and is not counted as leaving.'),
     ('How often is this page updated?',f'After every crawl. The crawl runs on Mondays; the latest was on {_date(DAY)}'+(f' and the next is due on {NEXTCRAWL}' if NEXTCRAWL else '')+'. <a href="methodology.html#changes">How we compare crawls</a>.')]
    # ---- breadcrumbs (visible + JSON-LD) on segment, category and capability pages ----
    def crumbs(path):
        sec,_,leaf=path.partition('/')
        names={'segments':'Segments','categories':'Categories','capabilities':'Capabilities'}
        if sec not in names: return None
        lst=[(NAME,'')]
        lst.append((names[sec],sec+'/'))
        if leaf!='index.html':
            nm={f'{k}.html':SEG[k] for k in SEG} if sec=='segments' else {f'{slug(c)}.html':c for c in g['CATS']} if sec=='categories' else {f'{slug(c)}.html':capn(c) for c in g['CAPC']}
            lst.append((nm.get(leaf,leaf),path))
        return lst
    defd=E(g['DEFDESC'])
    # store pages: retailers that share a name (e.g. country chains) get their main domain in the title so every title is unique
    _nc=__import__('collections').Counter(r['name'].lower() for r in RET); dupt={}
    for r in RET:
        if _nc[r['name'].lower()]>1: dupt[f"store/{g['SLUG'][r['id']]}.html"]=(r['name'],g['primary'](r) or g['SLUG'][r['id']])
    for p in list(g['PAGES']):
        fp=os.path.join(DIST,p); h=open(fp).read(); pre='../'*p.count('/'); lds=[]
        if p in dupt:
            nm,dm=dupt[p]; en=E(nm)
            h=re.sub(r'(<title>|<meta property="og:title" content="|<meta name="twitter:title" content=")'+re.escape(en),lambda m:m.group(1)+f'{en} ({E(dm)})',h)
        if p in desc and f'content="{defd}"' in h: h=h.replace(f'content="{defd}"',f'content="{E(desc[p])}"')
        if p=='index.html':
            h=_insert_after_topform(h,sum_html(home_sum)); h=_insert_before_bottom_cta(h,faq_html(home_faq))
            lds=[{"@type":"WebSite","@id":SITE+"/#website","url":SITE+"/","name":NAME,"description":g['DEFDESC'],"publisher":{"@id":SITE+"/#org"}},ORG,DATASET,faq_ld(home_faq)]
        elif p=='methodology.html':
            h=_insert_after_topform(h,sum_html(meth_sum)); h=_insert_before_bottom_cta(h,faq_html(meth_faq))
            lds=[{"@type":"WebPage","@id":SITE+"/methodology.html","url":SITE+"/methodology.html","name":f"Methodology | {NAME}","dateModified":DAY,"isPartOf":{"@id":SITE+"/#website"},"about":{"@id":SITE+"/#dataset"}},
                 dict(DATASET,url=SITE+"/methodology.html"),ORG,faq_ld(meth_faq)]
        elif p=='changes.html' and CHG:
            h=_insert_before_bottom_cta(h,faq_html(chg_faq))
            lds=[{"@type":"WebPage","@id":SITE+"/changes.html","url":SITE+"/changes.html","name":g['CHGTITLE'],"dateModified":DAY,"isPartOf":{"@id":SITE+"/#website"},"about":{"@id":SITE+"/#dataset"}},faq_ld(chg_faq)]
        else:
            cl=crumbs(p)
            if cl:
                vis='<p class="muted crumbs">'+' › '.join(f'<a href="{(pre+u) or "./"}">{E(n)}</a>' if i<len(cl)-1 else E(n) for i,(n,u) in enumerate(cl))+'</p>'
                h=h.replace('<h1>',vis+'<h1>',1)
                lds=[{"@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":i+1,"name":n,"item":SITE+'/'+u} for i,(n,u) in enumerate(cl)]}]
        if lds: h=h.replace('</head>',_ld({"@context":"https://schema.org","@graph":lds})+'</head>',1)
        open(fp,'w').write(h)
    # ---- robots.txt, sitemap.xml, llms.txt, llms-full.txt, IndexNow key ----
    rob='User-agent: *\nAllow: /\n\n# Search engines and AI assistants are welcome to crawl and cite this site.\n'+''.join(f'User-agent: {b}\n' for b in AI_BOTS)+'Allow: /\n\n'+f'Sitemap: {SITE}/sitemap.xml\n'
    open(os.path.join(DIST,'robots.txt'),'w').write(rob)
    open(os.path.join(DIST,'sitemap.xml'),'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{SITE}/{p.replace("index.html","")}</loc><lastmod>{DAY}</lastmod></url>\n' for p in g['PAGES'])+'</urlset>\n')
    open(os.path.join(DIST,f'{INDEXNOW_KEY}.txt'),'w').write(INDEXNOW_KEY)
    llms=_llms(g,ALL,SS,home_sum,home_faq,meth_faq,nsites)
    open(os.path.join(DIST,'llms.txt'),'w').write(llms)
    open(os.path.join(DIST,'llms-full.txt'),'w').write(_llms_full(g,llms,ALL,SS))

def _insert_after_topform(h,ins):
    i=h.find('<div class="nl-top" id="subscribe-top">')
    if i<0:  # no top form: right after the lede
        m=re.search(r'<p class="lede"[^>]*>.*?</p>',h,re.S); return h[:m.end()]+ins+h[m.end():] if m else h
    j=h.find('</script></div>',i)+len('</script></div>'); return h[:j]+ins+h[j:]
def _insert_before_bottom_cta(h,ins):
    i=h.rfind('<div class="cta" id="subscribe">')
    if i<0: i=h.find('</div></main>')
    return h[:i]+ins+h[i:]
def _md(a): return re.sub(r'<a href="([^"]+)">(.*?)</a>',lambda m:f'[{m.group(2)}]({m.group(1)})',a).replace('<code>','`').replace('</code>','`')
def _abs(s,SITE): return re.sub(r'\]\((?!https?:|mailto:)([^)#]*)(#[^)]*)?\)',lambda m:f']({SITE}/{m.group(1)}{m.group(2) or ""})',s)
def _llms(g,ALL,SS,home_sum,home_faq,meth_faq,nsites):
    SITE,NAME,DAY,SEG=g['SITE'],g['NAME'],g['DAY'],g['SEG']
    faq=lambda f:'\n'.join(f'- **{q}** '+_abs(html.unescape(_md(a)),SITE) for q,a in f)
    pages=[('Home','',f'Headline numbers from the latest crawl, by segment, big retailers with a UCP profile, capabilities and payment handlers.'),
           ('All stores','stores.html',f'Every one of the {ALL["n"]} retailers and stores with its result (the table is drawn with JavaScript; each store also has its own page under /store/).'),
           ('Segments','segments/','Shopify stores, big retailers, other retailers & marketplaces, side by side.')]+[(SEG[k],f'segments/{k}.html',f'{SS[k]["ucp"]} of {SS[k]["checked"]} checked publish a UCP profile ({SS[k]["rate"]}).') for k in SEG]+[
           ('Capabilities','capabilities/','What UCP profiles declare (checkout, cart, catalog search and more), with the stores declaring each.'),
           ('Categories','categories/','Results by store category.'),
           ('What changed','changes.html','This week compared with the previous crawl: who started or stopped publishing a UCP profile.'),
           ('Check your store','check.html','Look up any domain in the latest crawl.'),
           ('Methodology','methodology.html','Exactly what we fetch, how, and what the results do and don\'t mean.'),
           ('AI assistants','assistants.html','Which AI assistants name which retailers, from the companies\' own announcements, with links.'),
           ('About','about.html','Who runs the index and how to contact us.'),
           ('Terms of use','terms.html','All rights reserved. Link to pages and quote individual findings with credit and a link; bulk copying or republishing the data needs written permission.')]
    return f'''# {NAME}

> {NAME} is an independent weekly index of what online stores tell AI shopping agents. Every Monday it checks {ALL["n"]} retailers and stores ({nsites} websites): Shopify stores, big retailers and other retailers & marketplaces. The headline measure is whether each one publishes a UCP profile, the profile AI shopping agents read, at /.well-known/ucp.

Latest crawl: {DAY}. {_txt(home_sum)}

How to read the results:
- "UCP profile found": the store publishes a Universal Commerce Protocol profile at /.well-known/ucp and lists what it supports. A UCP profile isn't proof that AI agents can shop at a store.
- "No UCP profile found": we found no profile. It does not mean AI agents can't shop there.
- "Couldn't check": the site refused or failed our requests; excluded from all rates.
- Shares are shares of our list, not of all online stores. Every figure comes from our own crawl.

## Key pages

{chr(10).join(f"- [{n}]({SITE}/{u}): {d}" for n,u,d in pages)}

## Data

- One page per store: {SITE}/store/<name>.html (all listed in {SITE}/sitemap.xml)
- Store lookup used by "Check your store": {SITE}/stores.json (domain -> [page slug, store name, result: ucp | no_ucp | couldnt_check])
- Updated every Monday after the crawl. Full text of the key facts and methodology: {SITE}/llms-full.txt

## FAQ

{faq(home_faq)}

## Methodology

{faq(meth_faq)}

## Contact

{g["CONTACT"]} · https://x.com/ShopBotIndex
'''
def _llms_full(g,llms,ALL,SS):
    SITE,DAY,SEG,U,capn,slug,E=g['SITE'],g['DAY'],g['SEG'],g['U'],g['capn'],g['slug'],g['E']
    out=[llms,f'\n## Results by segment (crawl of {DAY})\n']
    for k in SEG:
        s=SS[k]; out.append(f'- {SEG[k]} ({g["SEGDESC"][k]}): {s["n"]} tracked, {s["ucp"]} UCP profile found, {s["no"]} no UCP profile found, {s["cc"]} couldn\'t check; {s["ucp"]} of {s["checked"]} checked ({s["rate"]}).')
    out.append(f'\n## Capabilities declared in UCP profiles ({len(U)} stores with a profile)\n')
    out+= [f'- {capn(c)} (`{c}`): {v} of {len(U)} ({g["pct"](v,len(U))}) - {SITE}/capabilities/{slug(c)}.html' for c,v in g['CAPC'].most_common()]
    out.append(f'\n## Payment handlers listed\n')
    out+= [f'- {g["phn"](p)} (`{p}`): {v} of {len(U)}' for p,v in g['PHC'].most_common()]
    out.append(f'\n## All {len(U)} retailers and stores with a UCP profile (crawl of {DAY})\n')
    out+= [f'- [{r["name"]}]({SITE}/store/{g["SLUG"][r["id"]]}.html) ({SEG[r["segment"]]}; {len(r["capabilities"])} capabilities declared{", including checkout" if "dev.ucp.shopping.checkout" in r["capabilities"] else ""})' for r in sorted(U,key=lambda r:r['name'].lower())]
    return '\n'.join(out)+'\n'
