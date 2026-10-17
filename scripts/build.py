"""Build the ShopBot Index static site from data/latest.json + data/channels.json -> ./dist
Usage: python3 scripts/build.py"""
import json, os, re, html, glob, shutil, collections
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.path.join(ROOT,'data'); DIST=os.path.join(ROOT,'dist')
SITE=os.environ.get('SBI_SITE','https://shopbotindex.com').rstrip('/')
NAME='ShopBot Index'
CONTACT='hello@shopbotindex.com'
MAILTO=f'<a href="mailto:{CONTACT}">{CONTACT}</a>'
FORM_ACTION='https://uufmlmwgvoqhhtqgrclu.supabase.co/functions/v1/sbi-subscribe'
DEFDESC='Which online stores can AI shopping agents actually buy from? A weekly public crawl of Shopify stores, big retailers and other online stores for Universal Commerce Protocol (UCP) profiles.'
E=lambda s: html.escape(str(s if s is not None else ''))
D=json.load(open(os.path.join(DATA,'latest.json'))); CH=json.load(open(os.path.join(DATA,'channels.json')))
RET=D['retailers']; SITES=D['sites']; DAY=D['crawl_date']
SITES_BY=collections.defaultdict(list)
for s in SITES: SITES_BY[s['rid']].append(s)
def slug(s): return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')
SEG={'shopify':'Shopify stores','big':'Big retailers','other':'Other retailers & marketplaces'}
SEGDESC={'shopify':'Stores from public lists of Shopify stores.','big':"Retailers on Wikipedia's List of largest retail companies, or with Wikipedia articles in 10+ languages.",
 'other':'Other retail chains, department stores, supermarkets, hypermarkets and online marketplaces listed on Wikipedia or Wikidata.'}
STL={'ucp':'UCP profile found','no_ucp':'No UCP profile','couldnt_check':"Couldn't check"}
SITEST={'ucp':'UCP profile found','no_ucp':'No profile (HTTP 404 or similar)','not_json':'No profile (answered with a web page, not JSON)','json_without_ucp':'No profile (JSON without a ucp object)',
 'blocked':"Couldn't check: request refused (401/403/429)",'error':"Couldn't check: timeout, TLS or DNS error",'robots_disallow':"Couldn't check: robots.txt disallows"}
CAPNAME={'dev.ucp.shopping.checkout':'Checkout','dev.ucp.shopping.cart':'Cart','dev.ucp.shopping.fulfillment':'Fulfillment (shipping options)',
 'dev.ucp.shopping.discount':'Discount codes','dev.ucp.shopping.order':'Order management','dev.ucp.shopping.buyer_consent':'Buyer consent',
 'dev.ucp.shopping.catalog.search':'Catalog search','dev.ucp.shopping.catalog.lookup':'Catalog lookup','dev.ucp.common.identity_linking':'Identity linking (account sign-in)',
 'dev.ucp.shopping.permalink':'Permalinks','dev.shopify.catalog':'Shopify catalog (vendor extension)'}
PHNAME={'com.google.pay':'Google Pay','dev.shopify.card':'Shopify card handler','dev.shopify.shop_pay':'Shop Pay','com.paypal':'PayPal'}
capn=lambda c: CAPNAME.get(c,c); phn=lambda p: PHNAME.get(p,p)
def pct(a,b): return f'{(100*a/b):.1f}%' if b else 'n/a'
def segstats(rs):
    st=collections.Counter(r['status'] for r in rs); chk=st['ucp']+st['no_ucp']
    return dict(n=len(rs),ucp=st['ucp'],no=st['no_ucp'],cc=st['couldnt_check'],checked=chk,rate=pct(st['ucp'],chk))
U=[r for r in RET if r['status']=='ucp']
NONSHOP=[r for r in U if any(p!='Shopify' for p in r['platforms'])]
BIGU=sorted([r for r in U if r['segment']=='big'],key=lambda r:r['name'].lower())
CAPC=collections.Counter(c for r in U for c in r['capabilities']); PHC=collections.Counter(p for r in U for p in r['payment_handlers'])
PLATC=collections.Counter(p for r in U for p in r['platforms'])
CATS=sorted({r['category'] for r in RET})
CSS=open(os.path.join(ROOT,'scripts','style.css')).read()
PAGES=[]
def page(path,title,body,desc=''):
    pre='../'*path.count('/')
    nav=''.join(f'<a href="{pre}{h}">{t}</a>' for h,t in [('stores.html','All stores'),('segments/','Segments'),('capabilities/','Capabilities'),('categories/','Categories'),('assistants.html','AI assistants'),('changes.html','What changed'),('methodology.html','Methodology'),('about.html','About')])
    full=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc or DEFDESC)}"><link rel="canonical" href="{SITE}/{path.replace('index.html','')}">
<meta property="og:type" content="website"><meta property="og:site_name" content="{NAME}"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc or DEFDESC)}"><meta property="og:url" content="{SITE}/{path.replace('index.html','')}"><meta property="og:image" content="{SITE}/og.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{pre}favicon.svg" type="image/svg+xml">
<meta name='impact-site-verification' value='b2e40b89-8d32-4fba-b983-f02842d65c9f'>
<meta name='impact-site-verification' value='644adb49-a10b-4e51-b34b-6674b6917c9f'>
<link rel="stylesheet" href="{pre}style.css"></head><body><header><div class="w"><a class="brand" href="{pre}index.html">{NAME}</a>{nav}</div></header>
<main><div class="w">{body}</div></main><footer><div class="w">{NAME} · Crawl of {DAY} · <a href="{pre}methodology.html">How we measure</a> · <a href="{pre}privacy.html">Privacy</a> · <a href="{pre}about.html">About</a> · Contact: {MAILTO} · Independent; not affiliated with Google, Shopify, OpenAI, Microsoft or any retailer listed.</div></footer></body></html>'''
    fp=os.path.join(DIST,path); os.makedirs(os.path.dirname(fp),exist_ok=True); open(fp,'w').write(full); PAGES.append(path)
def bars(counter,total,namef=lambda x:x,link=None,label='Stores'):
    rows=''.join(f'<tr><td>{(f"<a href=\"{link(k)}\">{E(namef(k))}</a>") if link else E(namef(k))}</td><td>{v}</td><td>{pct(v,total)}</td><td class="hide-sm" style="width:35%"><div class="bar"><i style="width:{100*v/max(total,1):.1f}%"></i></div></td></tr>' for k,v in counter.most_common())
    return f'<div class="tw nomax"><table><tr><th>Item</th><th>{label}</th><th>Share</th><th class="hide-sm"></th></tr>{rows}</table></div>'
def segcards(pre=''):
    out=''
    for k in ('shopify','big','other'):
        s=segstats([r for r in RET if r['segment']==k])
        out+=f'''<a class="seg" href="{pre}segments/{k}.html"><h3>{SEG[k]}</h3><b>{s["ucp"]}</b> <span>of {s["checked"]} we could check publish UCP ({s["rate"]})</span>
<div class="sbar"><i class="y" style="width:{100*s["ucp"]/max(s["n"],1):.1f}%"></i><i class="n" style="width:{100*s["no"]/max(s["n"],1):.1f}%"></i><i class="c" style="width:{100*s["cc"]/max(s["n"],1):.1f}%"></i></div>
<small>{s["n"]} tracked · {s["no"]} without · <span class="cc">{s["cc"]} couldn't check</span></small></a>'''
    return f'<div class="segs">{out}</div><p class="legend"><i class="y"></i> UCP profile <i class="n"></i> no profile <i class="c"></i> couldn\'t check (blocked or unreachable; not counted in the rate)</p>'
HONEYPOT='<input type="text" name="website" tabindex="-1" autocomplete="off" aria-hidden="true" style="position:absolute;left:-9999px;width:1px;height:1px;opacity:0">'
SIGNUP_JS="""<script>if(!window.sbiSub){window.sbiSub=function(f){const m=f.parentNode.querySelector('.nl-msg'),b=f.querySelector('button');b.disabled=true;m.textContent='Subscribing…';fetch(f.action,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.fromEntries(new FormData(f)))}).then(r=>r.json().then(j=>[r.status,j])).then(([s,j])=>{if(j.ok){m.textContent="Thanks! You're on the list.";f.reset();}else{m.textContent=(j.error==='invalid_email'?'Please enter a valid email address.':(s===429?'Too many attempts. Please try again later.':'Something went wrong. Please try again.'));}}).catch(()=>{m.textContent='Network error. Please try again.'}).finally(()=>{b.disabled=false});return false;}}</script>"""
def signup(pre=''):
    return f'''<div class="cta" id="subscribe"><b>Get the weekly index in your inbox.</b> One short email: who joined, who left, what changed.<form class="nl" action="{FORM_ACTION}" method="post" onsubmit="return sbiSub(this)" style="margin-top:.6rem">
<input type="email" name="email" placeholder="you@store.com" required maxlength="254" aria-label="Email address">{HONEYPOT} <button type="submit">Subscribe</button></form><small class="nl-msg" aria-live="polite">Free. About one email a week. Unsubscribe anytime. <a href="{pre}privacy.html">Privacy</a></small>{SIGNUP_JS}</div>'''
AFF='<div class="box"><b>Selling online?</b> <span class="muted">[Affiliate placeholder: a disclosed partner link will go here. No affiliate account exists yet.]</span></div>'
if os.path.isdir(DIST): shutil.rmtree(DIST)
os.makedirs(DIST); open(os.path.join(DIST,'style.css'),'w').write(CSS)
# ---- changes (weekly diff) ----
def prev_crawl():
    fs=sorted(f for f in glob.glob(os.path.join(DATA,'crawl-*.json')) if not f.endswith(f'crawl-{DAY}.json'))
    for f in reversed(fs):
        d=json.load(open(f))
        if 'retailers' in d: return d
    return None
P=prev_crawl(); CHG=None
if P:
    PR={r['id']:r for r in P['retailers']}; CR={r['id']:r for r in RET}
    CHG=dict(previous=P['crawl_date'],current=DAY,
        joined=[r['id'] for r in RET if r['status']=='ucp' and r['id'] in PR and PR[r['id']]['status']!='ucp'],
        left=[r['id'] for r in RET if r['id'] in PR and PR[r['id']]['status']=='ucp' and r['status']=='no_ucp'],
        now_unreachable=[r['id'] for r in RET if r['id'] in PR and PR[r['id']]['status']=='ucp' and r['status']=='couldnt_check'],
        newly_tracked=[r['id'] for r in RET if r['id'] not in PR],
        capability_changes=[dict(id=r['id'],added=sorted(set(r['capabilities'])-set(PR[r['id']]['capabilities'])),removed=sorted(set(PR[r['id']]['capabilities'])-set(r['capabilities'])))
                            for r in RET if r['status']=='ucp' and r['id'] in PR and PR[r['id']]['status']=='ucp' and set(r['capabilities'])!=set(PR[r['id']]['capabilities'])])
    json.dump(CHG,open(os.path.join(DATA,'changes-latest.json'),'w'),indent=1)
elif os.path.exists(os.path.join(DATA,'changes-latest.json')):
    os.remove(os.path.join(DATA,'changes-latest.json'))  # no previous crawl: drop any stale diff
NM={r['id']:r for r in RET}
# ---- home ----
nsites=len(SITES); nsites_u=sum(1 for s in SITES if s.get('status')=='ucp')
joined_txt=(f'<p><b>This week:</b> {len(CHG["joined"])} joined, {len(CHG["left"])} left since {CHG["previous"]}. <a href="changes.html">See who →</a></p>' if CHG else '<p class="muted">Weekly "who joined" starts with the second crawl.</p>')
home=f'''<h1>Which online stores can AI shopping agents actually buy from?</h1>
<p class="lede">We check {len(RET)} retailers and stores ({nsites} websites) for a published <a href="https://ucp.dev/">Universal Commerce Protocol</a> (UCP) profile, the file AI agents read to learn what a store supports. Every figure comes from our own crawl on {DAY}.</p>
{segcards()}{joined_txt}
<div class="stats"><div class="stat"><b>{len(U)}</b><span>retailers/stores with a UCP profile on at least one site</span></div>
<div class="stat"><b>{PLATC.get("Shopify",0)}</b><span>of them run it on Shopify</span></div>
<div class="stat"><b>{len(NONSHOP)}</b><span>on other platforms</span></div>
<div class="stat"><b>{sum(1 for r in RET if r["status"]=="couldnt_check")}</b><span>couldn't be checked (blocked/unreachable)</span></div></div>
<h2>Big retailers with a UCP profile ({len(BIGU)})</h2>{"<ul class='cols'>"+"".join(f"<li>{E(r['name'])} <small>({r['sites_with_ucp']} of {r['sites_checked']} sites{', '+E('/'.join(r['platforms'])) if r['platforms'] else ''})</small></li>" for r in BIGU)+"</ul>" if BIGU else "<p>None found in this crawl.</p>"}
<h2>UCP profiles not on Shopify ({len(NONSHOP)})</h2>{"<ul class='cols'>"+"".join(f"<li>{E(r['name'])} <small>({E(SEG[r['segment']])})</small></li>" for r in NONSHOP)+"</ul>" if NONSHOP else "<p>None found.</p>"}
<p><a href="stores.html"><b>Browse all {len(RET)} stores →</b></a></p>
<h2>What UCP stores support</h2>{bars(CAPC,len(U),capn,lambda k:f"capabilities/{slug(k)}.html")}
<h2>Payment handlers listed</h2>{bars(PHC,len(U),phn)}
<h2>Which AI assistants name which retailers</h2><p>From official announcements and help pages only. <a href="assistants.html">Details →</a></p>
<div class="tw nomax"><table><tr><th>Assistant</th><th>Retailers named</th><th>Source</th></tr>{"".join(f'<tr><td><b>{E(c["assistant"])}</b></td><td>{", ".join(E(x) for x in c["retailers_named"])}</td><td><a href="{E(c["source_url"])}" rel="noopener">{E(c["source_title"].split(" (")[-1].rstrip(")"))}</a>, {E(c["date"])}</td></tr>' for c in CH["channels"])}</table></div>
{signup()}{AFF}'''
page('index.html',f'{NAME}: which online stores AI shopping agents can actually buy from',home,DEFDESC)
# ---- stores table ----
rows=[]
for r in sorted(RET,key=lambda r:(r['status']!='ucp',r['name'].lower())):
    rows.append(dict(n=r['name'],g=r['segment'],c=r['category'],s=r['status'],co=r['country'][:40] if r['segment']!='shopify' else '',
        caps=[capn(x) for x in r['capabilities']],ph=[phn(x) for x in r['payment_handlers']],p='/'.join(r['platforms']),
        st=[dict(h=x.get('host') or x['domain'],s=x.get('status','error')) for x in SITES_BY[r['id']]]))
stores=f'''<h1>All stores ({len(RET)})</h1><p class="lede">Every retailer and store we track, with the result of fetching <code>/.well-known/ucp</code> on each of its websites on {DAY}. Retailers with several country sites show them underneath. Click a column to sort.</p>
<div class="filters"><input id="q" placeholder="Search name or domain" aria-label="Search">
<select id="fg"><option value="">All segments</option>{"".join(f'<option value="{k}">{v}</option>' for k,v in SEG.items())}</select>
<select id="fs"><option value="">All results</option>{"".join(f'<option value="{k}">{v}</option>' for k,v in STL.items())}</select>
<select id="fc"><option value="">All categories</option>{"".join(f'<option>{E(c)}</option>' for c in CATS)}</select>
<select id="fp"><option value="">Any platform</option>{"".join(f'<option>{E(p)}</option>' for p in PLATC)}</select></div>
<p class="muted" id="cnt"></p><div class="tw"><table id="t"><thead><tr><th data-k="n">Store</th><th data-k="g">Segment</th><th data-k="c" class="hide-sm">Category</th><th data-k="s">UCP</th><th data-k="p" class="hide-sm">Platform</th><th data-k="nc">Capabilities</th><th data-k="ns">Sites checked</th></tr></thead><tbody></tbody></table></div>
<script>const D={json.dumps(rows,ensure_ascii=False)};const SEG={json.dumps(SEG)},STL={json.dumps(STL)},SST={json.dumps(SITEST)};
const tb=document.querySelector('#t tbody');let sk='s',sd=1;const $=i=>document.getElementById(i);
function esc(s){{return String(s).replace(/[&<>"]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]))}}
function pill(s){{return '<span class="pill '+(s=='ucp'?'yes':s=='couldnt_check'||s=='blocked'||s=='error'||s=='robots_disallow'?'warn':'no')+'">'+(s=='ucp'?'Yes':s=='couldnt_check'?"Couldn't check":s=='no_ucp'?'No':esc((SST[s]||s).split(' (')[0].split(':')[0]))+'</span>'}}
function render(){{const q=$('q').value.toLowerCase();
let r=D.filter(x=>(!q||(x.n+' '+x.st.map(y=>y.h).join(' ')).toLowerCase().includes(q))&&(!$('fg').value||x.g==$('fg').value)&&(!$('fs').value||x.s==$('fs').value)&&(!$('fc').value||x.c==$('fc').value)&&(!$('fp').value||x.p.split('/').includes($('fp').value)));
const v=x=>sk=='nc'?x.caps.length:sk=='ns'?x.st.length:sk=='s'?({{ucp:0,no_ucp:1,couldnt_check:2}})[x.s]:String(x[sk]).toLowerCase();
r.sort((a,b)=>(v(a)>v(b)?1:v(a)<v(b)?-1:0)*sd);$('cnt').textContent=r.length+' of '+D.length+' shown';
tb.innerHTML=r.slice(0,1500).map(x=>'<tr><td><b>'+esc(x.n)+'</b>'+(x.co?'<br><small>'+esc(x.co)+'</small>':'')+'</td><td>'+esc(SEG[x.g])+'</td><td class="hide-sm">'+esc(x.c)+'</td><td>'+pill(x.s)+'</td><td class="hide-sm">'+esc(x.p)+'</td><td>'+(x.caps.length?'<span class="pill" title="'+esc(x.caps.join(', '))+'">'+x.caps.length+' declared</span>'+(x.caps.includes('Checkout')?'<span class="pill yes">Checkout</span>':''):'')+'</td><td>'+(x.st.length==1?'<a href="https://'+esc(x.st[0].h)+'/.well-known/ucp" rel="nofollow noopener" target="_blank">'+esc(x.st[0].h)+'</a>'+(x.s=='couldnt_check'?' '+pill(x.st[0].s):''):'<details><summary>'+x.st.length+' sites</summary>'+x.st.map(y=>'<div class="child"><a href="https://'+esc(y.h)+'/.well-known/ucp" rel="nofollow noopener" target="_blank">'+esc(y.h)+'</a> '+pill(y.s)+'</div>').join('')+'</details>')+'</td></tr>').join('')}}
['q','fg','fs','fc','fp'].forEach(i=>$(i).addEventListener('input',render));
document.querySelectorAll('th[data-k]').forEach(th=>th.addEventListener('click',()=>{{const k=th.dataset.k;sd=(sk==k)?-sd:1;sk=k;render()}}));render();</script>'''
page('stores.html',f'All {len(RET)} stores checked for UCP | {NAME}',stores,'Sortable table of Shopify stores, big retailers and other online stores and whether they publish a UCP profile.')
# ---- segment pages ----
def rtable(rs):
    li=''.join(f'<tr><td>{E(r["name"])}</td><td class="hide-sm">{E(r["category"])}</td><td>{"<span class=\"pill yes\">Yes</span>" if r["status"]=="ucp" else ("<span class=\"pill warn\">Couldn&#39;t check</span>" if r["status"]=="couldnt_check" else "No")}</td><td>{r["sites_with_ucp"]}/{r["sites_checked"]}</td><td class="hide-sm">{E("/".join(r["platforms"]))}</td></tr>' for r in sorted(rs,key=lambda r:({"ucp":0,"no_ucp":1,"couldnt_check":2}[r["status"]],r["name"].lower())))
    return f'<div class="tw"><table><tr><th>Store</th><th class="hide-sm">Category</th><th>UCP</th><th>Sites with UCP</th><th class="hide-sm">Platform</th></tr>{li}</table></div>'
page('segments/index.html',f'Segments | {NAME}',f'<h1>Segments</h1><p class="lede">We track three groups side by side. Rates exclude stores we couldn\'t check.</p>{segcards("../")}<ul>{"".join(f"<li><b>{SEG[k]}</b>: {SEGDESC[k]}</li>" for k in SEG)}</ul>')
for k in SEG:
    rs=[r for r in RET if r['segment']==k]; s=segstats(rs); cu=collections.Counter(c for r in rs if r['status']=='ucp' for c in r['capabilities'])
    cats=collections.Counter(r['category'] for r in rs)
    ct=''.join(f'<tr><td>{E(c)}</td><td>{n}</td><td>{sum(1 for r in rs if r["category"]==c and r["status"]=="ucp")}</td><td>{sum(1 for r in rs if r["category"]==c and r["status"]=="couldnt_check")}</td></tr>' for c,n in cats.most_common())
    page(f'segments/{k}.html',f'{SEG[k]}: UCP adoption | {NAME}',f'<h1>{SEG[k]}</h1><p class="lede">{SEGDESC[k]} {s["ucp"]} of {s["checked"]} we could check publish a UCP profile ({s["rate"]}); {s["cc"]} couldn\'t be checked.</p><h2>By category</h2><div class="tw nomax"><table><tr><th>Category</th><th>Tracked</th><th>With UCP</th><th>Couldn\'t check</th></tr>{ct}</table></div>{"<h2>Capabilities declared</h2>"+bars(cu,s["ucp"],capn) if s["ucp"] else ""}<h2>All {len(rs)}</h2>{rtable(rs)}')
# ---- capabilities ----
page('capabilities/index.html',f'UCP capabilities | {NAME}',f'<h1>UCP capabilities</h1><p class="lede">Capabilities declared in UCP profiles, counted per retailer/store ({len(U)} with a profile).</p><ul>{"".join(f"<li><a href=\"{slug(c)}.html\">{E(capn(c))}</a>: {v} <small>(<code>{E(c)}</code>)</small></li>" for c,v in CAPC.most_common())}</ul>')
for c,v in CAPC.items():
    rs=[r for r in U if c in r['capabilities']]; sc=collections.Counter(r['segment'] for r in rs)
    page(f'capabilities/{slug(c)}.html',f'{capn(c)}: stores declaring it | {NAME}',f'<h1>{E(capn(c))}</h1><p class="lede"><code>{E(c)}</code> is declared by {v} of {len(U)} stores with a UCP profile ({pct(v,len(U))}): {", ".join(f"{SEG[k]} {n}" for k,n in sc.most_common())}.</p>{rtable(rs)}')
# ---- categories ----
page('categories/index.html',f'Categories | {NAME}',f'<h1>Categories</h1><p class="lede">From Wikidata industry labels, the Wikipedia list a retailer came from, or the Shopify list a store came from.</p><div class="tw nomax"><table><tr><th>Category</th>{"".join(f"<th>{v}</th>" for v in SEG.values())}</tr>{"".join("<tr><td><a href=\"%s.html\">%s</a></td>"%(slug(c),E(c))+"".join(f"<td>{sum(1 for r in RET if r['category']==c and r['segment']==k and r['status']=='ucp')} / {sum(1 for r in RET if r['category']==c and r['segment']==k)}</td>" for k in SEG)+"</tr>" for c in CATS)}</table></div><p class="muted">Cells: with UCP / tracked.</p>')
for c in CATS:
    rs=[r for r in RET if r['category']==c]; s=segstats(rs)
    page(f'categories/{slug(c)}.html',f'{c}: UCP adoption | {NAME}',f'<h1>{E(c)}</h1><p class="lede">{s["ucp"]} of {s["checked"]} we could check publish a UCP profile ({s["rate"]}); {s["cc"]} couldn\'t be checked.</p>{rtable(rs)}')
# ---- assistants ----
li=''.join(f'<tr><td><b>{E(c["assistant"])}</b></td><td>{E(c["feature"])}<br><small>{E(c["how"])} · {E(c["region"])}</small></td><td>{", ".join(E(x) for x in c["retailers_named"])}</td><td>{E(c["date"])}</td><td><a href="{E(c["source_url"])}" rel="noopener">{E(c["source_title"])}</a></td></tr>' for c in CH['channels'])
page('assistants.html',f'AI assistants and the retailers they name | {NAME}',f'<h1>AI assistants and the retailers they name</h1><p class="lede">{E(CH["note"])} Last checked {E(CH["checked_on"])}.</p><div class="tw nomax"><table><tr><th>Assistant</th><th>Feature</th><th>Retailers named</th><th>Date</th><th>Official source</th></tr>{li}</table></div>')
# ---- changes ----
if CHG:
    L=lambda ids: '<ul>'+''.join(f'<li>{E(NM[i]["name"])} <small>({E(SEG[NM[i]["segment"]])})</small></li>' for i in ids)+'</ul>' if ids else '<p class="muted">None.</p>'
    cc=''.join(f'<li>{E(NM[x["id"]]["name"])}: {"added "+", ".join(capn(a) for a in x["added"]) if x["added"] else ""} {"removed "+", ".join(capn(a) for a in x["removed"]) if x["removed"] else ""}</li>' for x in CHG['capability_changes'])
    body=f'''<h1>What changed</h1><p class="lede">Crawl of {DAY} compared with {E(CHG["previous"])}.</p>
<h2>Joined: newly publishing UCP ({len(CHG["joined"])})</h2>{L(CHG["joined"])}<h2>Left: profile no longer found ({len(CHG["left"])})</h2>{L(CHG["left"])}
<h2>Had a profile, now couldn't check ({len(CHG["now_unreachable"])})</h2><p class="muted">Not counted as leaving: the site blocked us or was unreachable this time.</p>{L(CHG["now_unreachable"])}
<h2>Capability changes ({len(CHG["capability_changes"])})</h2>{"<ul>"+cc+"</ul>" if cc else "<p class='muted'>None.</p>"}
<h2>Newly tracked ({len(CHG["newly_tracked"])})</h2><p class="muted">Added to our list this week; not counted as joining.</p>{L(CHG["newly_tracked"])}'''
else:
    body=f'<h1>What changed</h1><p class="lede">Each week we compare the new crawl with the previous one: who joined (started publishing UCP), who left, who we couldn\'t reach, and capability changes.</p><div class="box">Only one crawl in this format exists so far ({DAY}). The first "who joined this week" list appears after the next crawl.</div>'
page('changes.html',f'What changed | {NAME}',body+signup())
# ---- methodology ----
SC=collections.Counter(s.get('status','error') for s in SITES)
meth=f'''<h1>Methodology</h1><p class="lede">Exactly how the numbers are produced. Crawl date: {DAY}.</p>
<h2>1. What we look for</h2><p>The UCP specification says platforms discover a business by fetching its business profile from <code>/.well-known/ucp</code> (<a href="{E(D["spec"])}">UCP specification overview</a>). The profile is JSON with a <code>ucp</code> object: protocol version, services, capabilities and payment handlers. We fetch that path on each website, plus <code>/robots.txt</code>, and nothing else.</p>
<h2>2. Who we track: three segments, side by side</h2><ul>{"".join(f"<li><b>{SEG[k]}</b> ({sum(1 for r in RET if r['segment']==k)}): {SEGDESC[k]}</li>" for k in SEG)}</ul>
<p>Sources: Wikipedia list pages (largest retail companies, department stores by country, supermarket chains, hypermarkets, online marketplaces) resolved to Wikidata for official websites; Wikidata queries for retail chains and e-commerce companies; and public GitHub lists of Shopify stores (<a href="https://github.com/ihof/shopify">ihof/shopify</a>, <a href="https://github.com/dipinarora9/Shopify-Domains-Scraper">dipinarora9/Shopify-Domains-Scraper</a>, first 900 of <a href="https://github.com/TeamDukaan/performance">TeamDukaan/performance</a>). This is not a random sample of all stores; shares are shares of our list.</p>
<h2>3. One retailer, many country sites</h2><p>When a retailer's Wikidata entry lists several official websites (for example one per country), we check up to 8 of them and show them as children of one retailer. A retailer counts as publishing UCP if at least one of its sites does.</p>
<h2>4. "Couldn't check" is not "no"</h2><p>Many large retailers use bot protection that refuses automated requests. We never try to get around it. A retailer is <b>couldn't check</b> when every one of its sites refused us (401/403/429), timed out, failed TLS/DNS, or disallowed the path in robots.txt. These are shown separately and <b>excluded</b> from adoption rates. A retailer is <b>no UCP profile</b> only when at least one of its sites answered and had no profile.</p>
<h2 id="crawler">5. How we fetch</h2><ul><li>User-Agent: <code>{E(D["user_agent"])}</code></li><li>robots.txt is read first and respected.</li><li>At most 12 websites at a time, one request at a time per site, a pause between requests, 10-second timeouts, HTTPS only. If a listed host is unreachable we try the same domain with or without <code>www.</code>.</li><li>Site owners: to have your site excluded, disallow <code>/.well-known/ucp</code> for <code>ShopBotIndexBot</code> in robots.txt, or email {MAILTO}.</li></ul>
<h2>6. Site-level results this crawl ({nsites} websites)</h2><ul>{"".join(f"<li>{E(SITEST.get(k,k))}: {v}</li>" for k,v in SC.most_common())}</ul>
<h2>7. Platform</h2><p>"Shopify" means the profile's endpoints or extensions reference Shopify. Anything else is shown as another platform. We can only identify a platform for stores that publish a profile.</p>
<h2>8. Weekly changes</h2><p>Each crawl is saved with its date. The "What changed" page compares retailer-level status with the previous crawl: joined, left, couldn't check this time (not counted as leaving), capability changes, and newly tracked retailers (not counted as joining).</p>
<h2>9. AI assistants table</h2><p>Only official company announcements and help-centre pages, linked per row. We don't test those integrations.</p>
<h2 id="contact">10. Add, remove or correct a store</h2><p>Run a store or retailer that should be added, removed or corrected, or think a result is wrong? Email {MAILTO} with the store's domain. We re-check it in the next weekly crawl and never change a result by hand.</p>'''
page('methodology.html',f'Methodology | {NAME}',meth)
page('about.html',f'About | {NAME}','''<h1>About</h1><p class="lede">ShopBot Index tracks, week by week, which online stores AI shopping agents can discover and buy from through open protocols, across Shopify stores, big retailers and other online stores.</p>
<p>It is run by Gus, an experienced enterprise software consultant, as an independent project. It is not affiliated with Google, Shopify, OpenAI, Microsoft, Perplexity, PayPal or any retailer listed.</p>
<p>All figures come from our own public crawl or from linked official sources. Some links may become disclosed affiliate links in future; that will never change a store's result.</p><p>Contact: <a href="mailto:hello@shopbotindex.com">hello@shopbotindex.com</a> (including stores that want to be added, removed or corrected; see the <a href="methodology.html#contact">methodology</a>).</p>'''+signup())
page('privacy.html',f'Privacy | {NAME}','''<h1>Privacy</h1><p class="lede">Short version: we only store what's needed to send you the weekly email.</p>
<h2>What we store when you subscribe</h2><ul><li>Your email address</li><li>When you signed up</li><li>A one-way hash of your IP address, kept only to limit spam signups (we never store the IP address itself)</li></ul>
<h2>How we use it</h2><p>Only to send the ShopBot Index email (about one a week: who joined, who left, what changed). We don't sell or share your data, and we don't add you to other lists.</p>
<h2>Where it's kept</h2><p>Subscriber data is stored with Supabase (EU region, Frankfurt), and emails will be sent with Resend. Both act as processors for us.</p>
<h2>Unsubscribe and deletion</h2><p>Every email will have a one-click unsubscribe link, and unsubscribing removes you from the list. To have your data deleted, or for any question, write to <a href="mailto:hello@shopbotindex.com">hello@shopbotindex.com</a>.</p>
<h2>Analytics</h2><p>This site uses no cookies and no analytics or tracking scripts.</p>
<h2>Our crawler</h2><p>ShopBot Index reads only <code>/robots.txt</code> and <code>/.well-known/ucp</code> on the stores it tracks, respects robots.txt, and identifies itself honestly. See the <a href="methodology.html">methodology</a>.</p>
<p>Questions about your data: <a href="mailto:hello@shopbotindex.com">hello@shopbotindex.com</a>.</p><p class="muted">Last updated: October 2026.</p>''')
open(os.path.join(DIST,'CNAME'),'w').write(SITE.split('://',1)[1]+'\n')
open(os.path.join(DIST,'favicon.svg'),'w').write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#0f172a"/><path d="M14 20h6l5 22h20l5-16H23" fill="none" stroke="#22c55e" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="28" cy="50" r="4" fill="#22c55e"/><circle cx="43" cy="50" r="4" fill="#22c55e"/></svg>')
OG=os.path.join(ROOT,'assets','og.png')
if os.path.exists(OG): shutil.copy(OG,os.path.join(DIST,'og.png'))
open(os.path.join(DIST,'robots.txt'),'w').write(f'User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n')
open(os.path.join(DIST,'sitemap.xml'),'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{SITE}/{p.replace("index.html","")}</loc><lastmod>{DAY}</lastmod></url>\n' for p in PAGES)+'</urlset>\n')
print('built',len(PAGES),'pages;',{k:segstats([r for r in RET if r['segment']==k]) for k in SEG},'nonshopify',len(NONSHOP),'big ucp',len(BIGU))
