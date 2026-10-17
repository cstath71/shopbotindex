"""Build the Agentic Shopping Index static site from data/latest.json + data/channels.json -> ./dist
Usage: python3 scripts/build.py"""
import json, os, re, html, glob, shutil, collections, datetime
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.path.join(ROOT,'data'); DIST=os.path.join(ROOT,'dist')
SITE=os.environ.get('ASI_SITE','https://agenticshoppingindex.com')  # domain NOT owned yet; placeholder
NAME='Agentic Shopping Index'
E=lambda s: html.escape(str(s if s is not None else ''))
D=json.load(open(os.path.join(DATA,'latest.json'))); CH=json.load(open(os.path.join(DATA,'channels.json')))
R=D['results']; DAY=D['crawl_date']
def slug(s): return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')
CAPNAME={'dev.ucp.shopping.checkout':'Checkout','dev.ucp.shopping.cart':'Cart','dev.ucp.shopping.fulfillment':'Fulfillment (shipping options)',
 'dev.ucp.shopping.discount':'Discount codes','dev.ucp.shopping.order':'Order management','dev.ucp.shopping.buyer_consent':'Buyer consent',
 'dev.ucp.shopping.catalog.search':'Catalog search','dev.ucp.shopping.catalog.lookup':'Catalog lookup','dev.ucp.common.identity_linking':'Identity linking (account sign-in)',
 'dev.ucp.shopping.permalink':'Permalinks','dev.shopify.catalog':'Shopify catalog (vendor extension)'}
PHNAME={'com.google.pay':'Google Pay','dev.shopify.card':'Shopify card handler','dev.shopify.shop_pay':'Shop Pay','com.paypal':'PayPal'}
def capn(c): return CAPNAME.get(c,c)
def phn(p): return PHNAME.get(p,p)
U=[r for r in R if r.get('status')=='ucp']
reach=[r for r in R if r.get('http_status') is not None or r.get('status')=='robots_disallow']
ST=collections.Counter(r.get('status','error') for r in R)
CAPC=collections.Counter(c for r in U for c in r['ucp']['capabilities'])
PHC=collections.Counter(p for r in U for p in r['ucp']['payment_handlers'])
NETC=collections.Counter(n for r in U for n in r['ucp']['card_networks'])
VERC=collections.Counter(r['ucp']['version'] for r in U)
TRC=collections.Counter(t for r in U for t in r['ucp']['transports'])
PLAT=collections.Counter(r['ucp']['platform_hint'] or 'Not identified' for r in U)
CATS=sorted({r['category'] for r in R})
def pct(a,b): return f'{(100*a/b):.1f}%' if b else 'n/a'
STLABEL={'ucp':'UCP profile found','no_ucp':'No UCP profile (HTTP error, usually 404)','blocked':'Request refused (401/403/429)','error':'Unreachable (timeout, TLS or DNS error)',
 'not_json':'Answered but not JSON','json_without_ucp':'JSON without a ucp object','robots_disallow':'Skipped: robots.txt disallows'}
CSS='''*{box-sizing:border-box}body{margin:0;font:16px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#15202b;background:#fafaf7}
a{color:#0b5cad}header{background:#0f1f2e;color:#fff}header .w{display:flex;flex-wrap:wrap;align-items:center;gap:.4rem 1.2rem;padding:.8rem 1rem}
header a{color:#cfe3ff;text-decoration:none;font-size:.95rem}header .brand{color:#fff;font-weight:700;font-size:1.1rem;margin-right:auto}
.w{max-width:1100px;margin:0 auto;padding:0 1rem}main{padding:1.2rem 0 3rem}h1{font-size:1.9rem;line-height:1.2;margin:.6rem 0}h2{margin-top:2rem}
.lede{font-size:1.1rem;color:#38495a;max-width:760px}.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:.8rem;margin:1.2rem 0}
.stat{background:#fff;border:1px solid #e3e6ea;border-radius:10px;padding:.9rem}.stat b{display:block;font-size:1.8rem;color:#0f1f2e}.stat span{color:#56677a;font-size:.9rem}
table{border-collapse:collapse;width:100%;background:#fff;font-size:.92rem}th,td{padding:.45rem .55rem;border-bottom:1px solid #eceff2;text-align:left;vertical-align:top}
th{background:#f1f4f7;position:sticky;top:0;cursor:pointer;white-space:nowrap}.tw{overflow-x:auto;border:1px solid #e3e6ea;border-radius:10px;max-height:75vh}
.bar{background:#e8eef5;border-radius:4px;height:10px;min-width:60px}.bar i{display:block;height:10px;background:#2f7dd1;border-radius:4px}
.pill{display:inline-block;padding:.05rem .45rem;border-radius:99px;font-size:.78rem;background:#eef2f6;margin:.1rem .15rem .1rem 0;white-space:nowrap}
.yes{background:#dff5e3;color:#145c2a}.no{background:#f2f2f2;color:#666}.warn{background:#fff3d6;color:#7a5200}
.filters{display:flex;flex-wrap:wrap;gap:.5rem;margin:.8rem 0}.filters input,.filters select{padding:.45rem;border:1px solid #cdd5dd;border-radius:6px;font-size:.95rem}
.box{background:#fff;border:1px solid #e3e6ea;border-radius:10px;padding:1rem 1.1rem;margin:1rem 0}.cta{background:#0f1f2e;color:#fff;border-radius:10px;padding:1.1rem}
.cta input{padding:.55rem;border-radius:6px;border:0;min-width:240px}.cta button{padding:.55rem 1rem;border:0;border-radius:6px;background:#ffcf4a;font-weight:600}
footer{border-top:1px solid #e3e6ea;color:#56677a;font-size:.88rem;padding:1.2rem 0}small,.muted{color:#56677a}
@media(max-width:640px){h1{font-size:1.5rem}td,th{padding:.35rem}.hide-sm{display:none}}'''
def page(path,title,body,desc=''):
    depth=path.count('/'); pre='../'*depth
    nav=''.join(f'<a href="{pre}{h}">{t}</a>' for h,t in [('stores.html','Stores'),('capabilities/','Capabilities'),('categories/','Categories'),('assistants.html','AI assistants'),('changes.html','What changed'),('methodology.html','Methodology'),('about.html','About')])
    full=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc or title)}"><link rel="canonical" href="{SITE}/{path.replace('index.html','')}">
<link rel="stylesheet" href="{pre}style.css"></head><body><header><div class="w"><a class="brand" href="{pre}index.html">{NAME}</a>{nav}</div></header>
<main><div class="w">{body}</div></main><footer><div class="w">{NAME} · Data from crawl of {DAY} · <a href="{pre}methodology.html">How we measure</a> · Prototype, not yet published.</div></footer></body></html>'''
    fp=os.path.join(DIST,path); os.makedirs(os.path.dirname(fp),exist_ok=True); open(fp,'w').write(full); PAGES.append(path)
PAGES=[]
def bars(counter,total,namef=lambda x:x,link=None):
    rows=''.join(f'<tr><td>{(f"<a href=\"{link(k)}\">{E(namef(k))}</a>") if link else E(namef(k))}</td><td>{v}</td><td>{pct(v,total)}</td><td style="width:40%"><div class="bar"><i style="width:{100*v/max(total,1):.1f}%"></i></div></td></tr>' for k,v in counter.most_common())
    return f'<div class="tw" style="max-height:none"><table><tr><th>Item</th><th>Stores</th><th>Share</th><th></th></tr>{rows}</table></div>'
SIGNUP='''<div class="cta"><b>Get the weekly index in your inbox.</b> One short email when the numbers move.<form onsubmit="alert('Newsletter not connected yet (prototype).');return false" style="margin-top:.6rem">
<input type="email" placeholder="you@store.com" aria-label="Email"> <button type="submit">Subscribe</button></form><small style="color:#cfd8e3">Placeholder: not connected to any email service yet.</small></div>'''
AFF='''<div class="box"><b>Selling online?</b> <span class="muted">[Affiliate placeholder: a disclosed partner link (for example a store platform) will go here. No affiliate account exists yet.]</span></div>'''
if os.path.isdir(DIST): shutil.rmtree(DIST)
os.makedirs(DIST); open(os.path.join(DIST,'style.css'),'w').write(CSS)
N=len(R); NU=len(U)
top_caps=CAPC.most_common(3)
home=f'''<h1>Which online stores can AI shopping agents actually buy from?</h1>
<p class="lede">We check each store for a published <a href="https://ucp.dev/">Universal Commerce Protocol</a> (UCP) profile, the file AI agents read to discover what a store supports. Figures below come only from our own crawl on {DAY}.</p>
<div class="stats"><div class="stat"><b>{N}</b><span>store domains checked</span></div><div class="stat"><b>{len(reach)}</b><span>answered our request</span></div>
<div class="stat"><b>{NU}</b><span>publish a UCP profile ({pct(NU,N)} of checked)</span></div><div class="stat"><b>{CAPC.get("dev.ucp.shopping.checkout",0)}</b><span>advertise UCP checkout</span></div>
<div class="stat"><b>{PHC.get("com.google.pay",0)}</b><span>list Google Pay as a payment handler</span></div><div class="stat"><b>{ST.get("blocked",0)}</b><span>refused our request (403 etc.)</span></div><div class="stat"><b>{sum(1 for r in U if r["ucp"]["platform_hint"]!="Shopify")}</b><span>UCP stores not identified as Shopify</span></div></div>
<p><a href="stores.html"><b>Browse all {N} stores →</b></a></p>
<h2>What UCP stores support</h2>{bars(CAPC,NU,capn,lambda k:f"capabilities/{slug(k)}.html")}
<h2>Payment handlers listed</h2>{bars(PHC,NU,phn)}
<h2>Adoption by category</h2><div class="tw" style="max-height:none"><table><tr><th>Category</th><th>Checked</th><th>With UCP</th><th>Share</th></tr>{"".join(f'<tr><td><a href="categories/{slug(c)}.html">{E(c)}</a></td><td>{sum(1 for r in R if r["category"]==c)}</td><td>{sum(1 for r in U if r["category"]==c)}</td><td>{pct(sum(1 for r in U if r["category"]==c),sum(1 for r in R if r["category"]==c))}</td></tr>' for c in CATS)}</table></div>
<p class="muted">Category sizes reflect our seed sources, not the market. See <a href="methodology.html">methodology</a>.</p>
<h2>Which AI assistants say they support which retailers</h2><p>From official announcements and help pages only. <a href="assistants.html">Details and sources →</a></p>
<div class="tw" style="max-height:none"><table><tr><th>Assistant</th><th>Retailers named</th><th>Source</th></tr>{"".join(f'<tr><td><b>{E(c["assistant"])}</b></td><td>{", ".join(E(x) for x in c["retailers_named"])}</td><td><a href="{E(c["source_url"])}" rel="noopener">{E(c["source_title"].split(" (")[-1].rstrip(")"))}</a>, {E(c["date"])}</td></tr>' for c in CH["channels"])}</table></div>
{SIGNUP}{AFF}'''
page('index.html',f'{NAME}: which stores AI agents can buy from',home,'Weekly measured index of online stores publishing a Universal Commerce Protocol (UCP) profile for AI shopping agents.')
# stores table
rows=[]
for r in sorted(R,key=lambda r:(r.get('status')!='ucp',r['name'].lower())):
    u=r.get('ucp') or {}
    rows.append(dict(n=r['name'],d=r.get('host') or r['domain'],c=r['category'],s=r.get('status','error'),v=u.get('version',''),caps=[capn(x) for x in u.get('capabilities',[])],ph=[phn(x) for x in u.get('payment_handlers',[])],p=u.get('platform_hint',''),co=r.get('country','')))
stores=f'''<h1>All stores checked ({N})</h1><p class="lede">Every domain from our seed list, with the result of fetching <code>/.well-known/ucp</code> on {DAY}. Click a column to sort.</p>
<div class="filters"><input id="q" placeholder="Search store or domain" aria-label="Search"><select id="fs"><option value="">All results</option>{"".join(f'<option value="{k}">{E(STLABEL.get(k,k))} ({v})</option>' for k,v in ST.most_common())}</select>
<select id="fc"><option value="">All categories</option>{"".join(f'<option>{E(c)}</option>' for c in CATS)}</select><select id="fk"><option value="">Any capability</option>{"".join(f'<option>{E(capn(c))}</option>' for c,_ in CAPC.most_common())}</select></div>
<p class="muted" id="cnt"></p><div class="tw"><table id="t"><thead><tr><th data-k="n">Store</th><th data-k="d">Domain</th><th data-k="c">Category</th><th data-k="s">UCP</th><th data-k="v" class="hide-sm">Version</th><th data-k="nc">Capabilities</th><th data-k="np" class="hide-sm">Payment handlers</th><th data-k="p" class="hide-sm">Platform hint</th></tr></thead><tbody></tbody></table></div>
<script>const D={json.dumps(rows,ensure_ascii=False)};const SL={json.dumps(STLABEL)};
const tb=document.querySelector('#t tbody');let sk='s',sd=1;
function esc(s){{return String(s).replace(/[&<>"]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]))}}
function render(){{const q=document.getElementById('q').value.toLowerCase(),fs=fs_.value,fc=fc_.value,fk=fk_.value;
let r=D.filter(x=>(!q||(x.n+' '+x.d).toLowerCase().includes(q))&&(!fs||x.s==fs)&&(!fc||x.c==fc)&&(!fk||x.caps.includes(fk)));
r.sort((a,b)=>{{let A=sk=='nc'?a.caps.length:sk=='np'?a.ph.length:a[sk],B=sk=='nc'?b.caps.length:sk=='np'?b.ph.length:b[sk];if(sk=='s'){{A=a.s=='ucp'?0:1;B=b.s=='ucp'?0:1}}return (A>B?1:A<B?-1:0)*sd}});
document.getElementById('cnt').textContent=r.length+' of '+D.length+' stores shown';
tb.innerHTML=r.map(x=>'<tr><td>'+esc(x.n)+'</td><td><a href="https://'+esc(x.d)+'/.well-known/ucp" rel="nofollow noopener" target="_blank">'+esc(x.d)+'</a></td><td>'+esc(x.c)+'</td><td><span class="pill '+(x.s=='ucp'?'yes':x.s=='blocked'||x.s=='error'?'warn':'no')+'" title="'+esc(SL[x.s]||x.s)+'">'+(x.s=='ucp'?'Yes':esc(SL[x.s]?SL[x.s].split(' (')[0].split(':')[0]:x.s))+'</span></td><td class="hide-sm">'+esc(x.v)+'</td><td>'+(x.caps.length?'<span class="pill" title="'+esc(x.caps.join(', '))+'">'+x.caps.length+' declared</span>'+(x.caps.includes('Checkout')?'<span class="pill yes">Checkout</span>':''):'')+'</td><td class="hide-sm">'+x.ph.map(c=>'<span class="pill">'+esc(c)+'</span>').join('')+'</td><td class="hide-sm">'+esc(x.p)+'</td></tr>').join('')}}
const fs_=document.getElementById('fs'),fc_=document.getElementById('fc'),fk_=document.getElementById('fk');
['q','fs','fc','fk'].forEach(i=>document.getElementById(i).addEventListener('input',render));
document.querySelectorAll('th[data-k]').forEach(th=>th.addEventListener('click',()=>{{const k=th.dataset.k;sd=(sk==k)?-sd:1;sk=k;render()}}));render();</script>'''
page('stores.html',f'All {N} stores checked for UCP | {NAME}',stores,'Sortable table of online stores and whether they publish a UCP profile for AI shopping agents.')
# capabilities
lst=''.join(f'<li><a href="{slug(c)}.html">{E(capn(c))}</a>: {v} stores <small>(<code>{E(c)}</code>)</small></li>' for c,v in CAPC.most_common())
page('capabilities/index.html',f'UCP capabilities | {NAME}',f'<h1>UCP capabilities</h1><p class="lede">Capabilities each store declares in its UCP profile, counted over the {NU} stores that publish one.</p><ul>{lst}</ul>')
for c,v in CAPC.items():
    st=sorted([r for r in U if c in r['ucp']['capabilities']],key=lambda r:r['name'].lower())
    li=''.join(f'<tr><td>{E(r["name"])}</td><td>{E(r.get("host"))}</td><td>{E(r["category"])}</td></tr>' for r in st)
    page(f'capabilities/{slug(c)}.html',f'{capn(c)}: stores declaring it | {NAME}',f'<h1>{E(capn(c))}</h1><p class="lede"><code>{E(c)}</code> is declared by {v} of {NU} stores with a UCP profile ({pct(v,NU)}), crawl of {DAY}.</p><div class="tw"><table><tr><th>Store</th><th>Host</th><th>Category</th></tr>{li}</table></div>')
# categories
li=''.join(f'<li><a href="{slug(c)}.html">{E(c)}</a>: {sum(1 for r in U if r["category"]==c)} of {sum(1 for r in R if r["category"]==c)} with UCP</li>' for c in CATS)
page('categories/index.html',f'Categories | {NAME}',f'<h1>Categories</h1><p class="lede">Categories come from Wikidata industry labels or from the seed list a store came from. See <a href="../methodology.html">methodology</a>.</p><ul>{li}</ul>')
for c in CATS:
    st=sorted([r for r in R if r['category']==c],key=lambda r:(r.get('status')!='ucp',r['name'].lower())); nu=sum(1 for r in st if r.get('status')=='ucp')
    cc=collections.Counter(x for r in st if r.get('status')=='ucp' for x in r['ucp']['capabilities'])
    li=''.join(f'<tr><td>{E(r["name"])}</td><td>{E(r.get("host") or r["domain"])}</td><td>{"<span class=\"pill yes\">Yes</span>" if r.get("status")=="ucp" else E(STLABEL.get(r.get("status"),r.get("status")))}</td><td>{len((r.get("ucp") or {}).get("capabilities",[]))}</td></tr>' for r in st)
    page(f'categories/{slug(c)}.html',f'{c}: UCP adoption | {NAME}',f'<h1>{E(c)}</h1><p class="lede">{nu} of {len(st)} stores checked publish a UCP profile ({pct(nu,len(st))}).</p>{bars(cc,nu,capn) if nu else ""}<h2>Stores</h2><div class="tw"><table><tr><th>Store</th><th>Host</th><th>UCP</th><th>Capabilities</th></tr>{li}</table></div>')
# assistants
li=''.join(f'<tr><td><b>{E(c["assistant"])}</b></td><td>{E(c["feature"])}<br><small>{E(c["how"])} · {E(c["region"])}</small></td><td>{", ".join(E(x) for x in c["retailers_named"])}</td><td>{E(c["date"])}</td><td><a href="{E(c["source_url"])}" rel="noopener">{E(c["source_title"])}</a></td></tr>' for c in CH['channels'])
page('assistants.html',f'AI assistants and the retailers they name | {NAME}',f'<h1>AI assistants and the retailers they name</h1><p class="lede">{E(CH["note"])} Last checked {E(CH["checked_on"])}.</p><div class="tw" style="max-height:none"><table><tr><th>Assistant</th><th>Feature</th><th>Retailers named in the source</th><th>Date</th><th>Official source</th></tr>{li}</table></div>')
# changes
prev=sorted(f for f in glob.glob(os.path.join(DATA,'crawl-*.json')) if not f.endswith(f'crawl-{DAY}.json'))
if prev:
    P={r['domain']:r for r in json.load(open(prev[-1]))['results']}
    new=[r for r in U if P.get(r['domain'],{}).get('status')!='ucp']; gone=[r for r in R if P.get(r['domain'],{}).get('status')=='ucp' and r.get('status')!='ucp']
    body=f'<h1>What changed</h1><p class="lede">Compared with {E(os.path.basename(prev[-1])[6:16])}.</p><h2>Newly publishing UCP ({len(new)})</h2><ul>{"".join("<li>"+E(r["name"])+"</li>" for r in new)}</ul><h2>No longer found ({len(gone)})</h2><ul>{"".join("<li>"+E(r["name"])+"</li>" for r in gone)}</ul>'
else:
    body=f'<h1>What changed</h1><p class="lede">This page compares each weekly crawl with the previous one: stores that started or stopped publishing a UCP profile, and capability changes.</p><div class="box">Only one crawl exists so far ({DAY}). The first comparison appears after the next crawl.</div>'
page('changes.html',f'What changed | {NAME}',body)
meth=f'''<h1>Methodology</h1><p class="lede">Exactly how the numbers on this site are produced. Crawl date: {DAY}.</p>
<h2>1. What we look for</h2><p>The Universal Commerce Protocol specification says platforms discover a business by fetching its business profile from <code>/.well-known/ucp</code> (<a href="{E(D["spec"])}">UCP specification overview</a>). The profile is JSON with a <code>ucp</code> object containing the protocol version, services, optional capabilities and payment handlers. We fetch that one path per store, nothing else (plus <code>/robots.txt</code>).</p>
<h2>2. Which stores we check</h2><p>{N} domains from three public sources, de-duplicated by domain:</p><ul>
<li>Wikidata: retail chains (Q507619) with at least 3 Wikipedia language links, and organisations whose industry is e-commerce (Q484847) with at least 4, each with an official website. Category comes from the Wikidata industry label.</li>
<li>A public GitHub list of Shopify sneaker and streetwear stores (<a href="https://github.com/ihof/shopify/blob/master/shopify-sites.txt">ihof/shopify</a>).</li>
<li>The first 300 unique domains of a public GitHub list of Shopify stores, mostly Indian D2C brands (<a href="https://github.com/TeamDukaan/performance/blob/master/shopify%20stores%20-%20shopify.csv">TeamDukaan/performance</a>).</li></ul>
<p>This is not a random sample of all online stores. Shares are shares of <em>our list</em>, and category sizes reflect the sources.</p>
<h2>3. How we fetch</h2><ul><li>User-Agent: <code>{E(D["user_agent"])}</code></li><li>We read <code>/robots.txt</code> first and skip the store if it disallows the UCP path for our agent.</li>
<li>At most 12 stores at a time, one request at a time per store, a short pause between requests, 10-second timeouts, HTTPS only. If the listed host is unreachable we try the same domain with or without <code>www.</code>.</li></ul>
<h2>4. How we classify results</h2><ul>{"".join(f"<li><b>{E(STLABEL[k])}</b>: {ST.get(k,0)} stores</li>" for k in STLABEL)}</ul>
<p>A refused request or timeout does not mean the store lacks a UCP profile; it means we could not check. A "platform hint" of Shopify means the profile's endpoints or extensions reference Shopify.</p>
<h2>5. AI assistants table</h2><p>Retailer names on the <a href="assistants.html">AI assistants page</a> come only from official company announcements and help-centre pages, linked per row. We do not test those integrations ourselves.</p>
<h2>6. Corrections</h2><p>If a result is wrong, re-run the check: every domain in the store table links to its live <code>/.well-known/ucp</code> URL.</p>'''
page('methodology.html',f'Methodology | {NAME}',meth)
about='''<h1>About</h1><p class="lede">The Agentic Shopping Index tracks, week by week, which online stores AI shopping agents can discover and buy from through open protocols.</p>
<p>It is run by Gus, an experienced enterprise software consultant, as an independent project. It is not affiliated with Google, Shopify, OpenAI, Microsoft, Perplexity, PayPal or any retailer listed.</p>
<p>All figures come from our own public crawl or from linked official sources. Some links on this site may become disclosed affiliate links in future; that will never change a store's result.</p>'''
page('about.html',f'About | {NAME}',about)
open(os.path.join(DIST,'robots.txt'),'w').write(f'User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n')
open(os.path.join(DIST,'sitemap.xml'),'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{SITE}/{p.replace("index.html","")}</loc><lastmod>{DAY}</lastmod></url>\n' for p in PAGES)+'</urlset>\n')
print('built',len(PAGES),'pages;',N,'stores,',NU,'with UCP',dict(ST))
