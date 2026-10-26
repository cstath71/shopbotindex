"""Build the ShopBot Index static site from data/latest.json + data/channels.json -> ./dist
Usage: python3 scripts/build.py"""
import json, os, re, html, glob, shutil, collections, unicodedata
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.environ.get('SBI_DATA_DIR') or os.path.join(ROOT,'data'); DIST=os.environ.get('SBI_DIST_DIR') or os.path.join(ROOT,'dist')  # env overrides for dry-run previews
SITE=os.environ.get('SBI_SITE','https://shopbotindex.com').rstrip('/')
NAME='ShopBot Index'
OGV='4'  # cache-buster for og.png/og-store.png (rendered by scripts/og_images.py); bump when the cards change so X/LinkedIn refetch
CONTACT='hello@shopbotindex.com'
MAILTO=f'<a href="mailto:{CONTACT}">{CONTACT}</a>'
FORM_ACTION='https://uufmlmwgvoqhhtqgrclu.supabase.co/functions/v1/sbi-subscribe'
DEFDESC='What online stores tell AI shopping agents: a weekly public crawl of Shopify stores, big retailers and other online stores for UCP profiles, the machine-readable profile AI shopping agents read, plus agent tools, AI rules in robots.txt, AI guidance files and product data.'
E=lambda s: html.escape(str(s if s is not None else ''))
D=json.load(open(os.path.join(DATA,'latest.json'))); CH=json.load(open(os.path.join(DATA,'channels.json')))
from nonshops import IDS as NON_SHOPS  # places, newspapers, restaurants etc. (config/non_shops.json) are not shops: no page, not counted
RET=[r for r in D['retailers'] if r['id'] not in NON_SHOPS]; SITES=[s for s in D['sites'] if s['rid'] not in NON_SHOPS]; DAY=D['crawl_date']
SITES_BY=collections.defaultdict(list)
for s in SITES: SITES_BY[s['rid']].append(s)
_TRANS=str.maketrans({'ß':'ss','Æ':'AE','æ':'ae','Ø':'O','ø':'o','Œ':'OE','œ':'oe','Ł':'L','ł':'l','Đ':'D','đ':'d','ı':'i','Þ':'Th','þ':'th','Ð':'D','ð':'d'})
def slug(s):  # accented letters become plain ASCII (Bière -> biere), instead of being dropped (bi-re)
    t=''.join(c for c in unicodedata.normalize('NFKD',str(s).translate(_TRANS)) if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+','-',t.lower()).strip('-')
def slug_v1(s): return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')  # pre-27 Oct 2026 slugs, kept only to redirect old URLs
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
def hero(body):
    # home hero: sky-blue banner look (X branding); wraps the first <h1> and its lede, text unchanged
    m=re.search(r'<h1>.*?</h1>\s*<p class="lede">.*?</p>',body,re.S)
    if not m: return body
    art='<img class="hero-art" src="robot-hero.png" width="210" height="210" alt="ShopBot Index robot pushing a shopping cart">'
    return body[:m.start()]+f'<section class="hero">{art}<div class="hero-t">{m.group(0)}</div></section>'+signup_slim()+body[m.end():]
def page(path,title,body,desc='',ogimg='og.png',ogtype='website',head=''):
    pre='../'*path.count('/')
    if path=='index.html': body=hero(body)
    if path in TOPFORM_PAGES: body=re.sub(r'(<p class="lede">.*?</p>)',lambda m:m.group(1)+signup_slim(pre),body,count=1,flags=re.S)+signup(pre)
    nav=''.join(f'<a href="{pre}{h}">{t}</a>' for h,t in [('stores.html','All stores'),('segments/','Segments'),('capabilities/','Capabilities'),('categories/','Categories'),('assistants.html','AI assistants'),('changes.html','What changed'),('check.html','Check your store'),('methodology.html','Methodology'),('about.html','About')])
    full=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc or DEFDESC)}"><link rel="canonical" href="{SITE}/{path.replace('index.html','')}">
<meta property="og:type" content="{ogtype}"><meta property="og:site_name" content="{NAME}"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc or DEFDESC)}"><meta property="og:url" content="{SITE}/{path.replace('index.html','')}"><meta property="og:image" content="{SITE}/{ogimg}?v={OGV}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="{E(title)}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:site" content="@ShopBotIndex"><meta name="twitter:title" content="{E(title)}"><meta name="twitter:description" content="{E(desc or DEFDESC)}"><meta name="twitter:image" content="{SITE}/{ogimg}?v={OGV}">{head}
<link rel="icon" href="{pre}favicon.ico" sizes="any"><link rel="icon" href="{pre}favicon-32.png" type="image/png" sizes="32x32"><link rel="apple-touch-icon" href="{pre}apple-touch-icon.png">
<meta name='impact-site-verification' value='b2e40b89-8d32-4fba-b983-f02842d65c9f'>
<meta name='impact-site-verification' value='644adb49-a10b-4e51-b34b-6674b6917c9f'>
<link rel="stylesheet" href="{pre}style.css"></head><body><header><div class="w"><a class="brand" href="{pre or './'}"><img src="{pre}logo-32.png" srcset="{pre}logo-64.png 2x, {pre}logo-96.png 3x" width="32" height="32" alt="">{NAME}</a>{nav}</div></header>
<main><div class="w">{body}</div></main><footer><div class="w">{NAME}: the weekly index of what online stores tell AI shopping agents · Crawl of {DAY} · <a href="{pre}methodology.html">How we measure</a> · <a href="{pre}privacy.html">Privacy</a> · <a href="{pre}terms.html">Terms</a> · <a href="{pre}about.html">About</a> · <a href="https://x.com/ShopBotIndex" rel="me noopener">Follow on X</a> · Contact: {MAILTO} · Independent; not affiliated with Google, Shopify, OpenAI, Microsoft or any retailer listed.</div></footer>{sticky_bar(pre) if path not in NOBAR_PAGES else ''}{VISIT_JS}</body></html>'''
    fp=os.path.join(DIST,path); os.makedirs(os.path.dirname(fp),exist_ok=True); open(fp,'w').write(full); PAGES.append(path)
def bars(counter,total,namef=lambda x:x,link=None,label='Stores'):
    rows=''.join(f'<tr><td>{(f"<a href=\"{link(k)}\">{E(namef(k))}</a>") if link else E(namef(k))}</td><td>{v}</td><td>{pct(v,total)}</td><td class="hide-sm" style="width:35%"><div class="bar"><i style="width:{100*v/max(total,1):.1f}%"></i></div></td></tr>' for k,v in counter.most_common())
    return f'<div class="tw nomax"><table><tr><th>Item</th><th>{label}</th><th>Share</th><th class="hide-sm"></th></tr>{rows}</table></div>'
def segcards(pre=''):
    out=''
    for k in ('shopify','big','other'):
        s=segstats([r for r in RET if r['segment']==k])
        out+=f'''<a class="seg" href="{pre}segments/{k}.html"><h2>{SEG[k]}</h2><b>{s["ucp"]}</b> <span>of {s["checked"]} we could check publish a UCP profile ({s["rate"]})</span>
<div class="sbar"><i class="y" style="width:{100*s["ucp"]/max(s["n"],1):.1f}%"></i><i class="n" style="width:{100*s["no"]/max(s["n"],1):.1f}%"></i><i class="c" style="width:{100*s["cc"]/max(s["n"],1):.1f}%"></i></div>
<small>{s["n"]} tracked · {s["no"]} no UCP profile found · <span class="cc">{s["cc"]} couldn't check</span></small></a>'''
    return f'<div class="segs">{out}</div><p class="legend"><i class="y"></i> UCP profile <i class="n"></i> no profile found <i class="c"></i> couldn\'t check (blocked or unreachable; not counted in the rate)</p>'
HONEYPOT='<input type="text" name="sbi_hp_note" value="" tabindex="-1" autocomplete="off" aria-hidden="true" style="position:absolute;left:-9999px;width:1px;height:1px;opacity:0">'  # anti-spam trap; a name browsers don't autofill (was "website" until 20 Oct 2026)'
SIGNUP_JS="""<script>if(!window.sbiSub){window.sbiSub=function(f){const m=f.parentNode.querySelector('.nl-msg'),b=f.querySelector('button');b.disabled=true;m.textContent='Subscribing…';fetch(f.action,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.fromEntries(new FormData(f)))}).then(r=>r.json().then(j=>[r.status,j])).then(([s,j])=>{if(j.ok){m.textContent=(j.watching&&f.dataset.okWatch)||"Thanks! You're on the list for Monday's email.";f.reset();}else{m.textContent=(j.error==='invalid_email'?'Please enter a valid email address.':(s===429?'Too many attempts. Please try again later.':'Something went wrong. Please try again.'));}}).catch(()=>{m.textContent='Network error. Please try again.'}).finally(()=>{b.disabled=false});return false;}}</script>"""
def signup(pre=''):
    return f'''<div class="cta" id="subscribe"><b>Get the weekly index of what online stores tell AI shopping agents.</b> {NL_COPY} One short email after each Monday crawl.<form class="nl" action="{FORM_ACTION}" method="post" onsubmit="return sbiSub(this)" style="margin-top:.6rem">
<input type="email" name="email" placeholder="you@store.com" required maxlength="254" aria-label="Email address">{HONEYPOT} <button type="submit">Send me Monday's changes</button></form><small class="nl-msg" aria-live="polite">Free. About one email a week. Unsubscribe anytime. <a href="{pre}privacy.html">Privacy</a></small>{SIGNUP_JS}</div>'''
# ---- signup placement, "watch this store", visit counter (20 Oct 2026) ----
NL_COPY='Every Monday: which stores started or stopped publishing a UCP profile, the profile AI shopping agents read.'
TOPFORM_PAGES=('stores.html','methodology.html','assistants.html')
NOBAR_PAGES=('unwatch.html',)
def signup_slim(pre=''):
    # one-line form near the top of a page (home hero, stores, methodology, AI assistants)
    return f'''<div class="nl-top" id="subscribe-top"><p><b>{NL_COPY}</b> One short email, free.</p><form class="nl" action="{FORM_ACTION}" method="post" onsubmit="return sbiSub(this)">
<input type="email" name="email" placeholder="you@store.com" required maxlength="254" aria-label="Email address">{HONEYPOT}<button type="submit">Send me Monday's changes</button></form><small class="nl-msg" aria-live="polite">Unsubscribe anytime. <a href="{pre}privacy.html">Privacy</a></small>{SIGNUP_JS}</div>'''
def watch_form(r,pre='../'):
    # store pages, right under the result: subscribe + watch this store (sbi-subscribe stores r['id'] in sbi_watches)
    nm=E(r['name'])
    return f'''<div class="nl-top watch" id="watch"><p><b>Watch {nm}.</b> Email me if {nm} starts or stops publishing a UCP profile.</p><form class="nl" action="{FORM_ACTION}" method="post" onsubmit="return sbiSub(this)" data-ok-watch="Thanks! We'll email you if {nm} starts or stops publishing a UCP profile, plus the Monday email.">
<input type="email" name="email" placeholder="you@store.com" required maxlength="254" aria-label="Email address"><input type="hidden" name="watch" value="{E(r['id'])}">{HONEYPOT}<button type="submit">Watch this store</button></form><small class="nl-msg" aria-live="polite">Free. You'll also get the Monday email: which stores started or stopped publishing a UCP profile. Unsubscribe or stop the alerts anytime. <a href="{pre}privacy.html">Privacy</a></small>{SIGNUP_JS}</div>'''
def sticky_bar(pre=''):
    # slim bar at the bottom of the screen; hidden while a signup form or the footer is on screen, closable; no storage of any kind
    return f'''<div class="nl-bar" id="nl-bar" hidden><span>Every Monday: which stores started or stopped publishing a UCP profile<span class="nl-bar-long">, the profile AI shopping agents read</span>.</span><a class="nl-bar-go" href="#subscribe">Subscribe</a><button type="button" class="nl-bar-x" aria-label="Close">×</button></div>
<script>(function(){{var b=document.getElementById('nl-bar');if(!b||!('IntersectionObserver' in window))return;var vis=new Set(),closed=false,past=false;
function upd(){{var show=!closed&&past&&vis.size==0;b.hidden=!show;document.body.classList.toggle('has-bar',show)}}
var t=document.querySelectorAll('.nl-top,.cta,footer');var go=b.querySelector('.nl-bar-go');var f=document.getElementById('subscribe-top')||document.getElementById('watch')||document.getElementById('subscribe');if(f)go.setAttribute('href','#'+f.id);
go.addEventListener('click',function(e){{if(f){{e.preventDefault();f.scrollIntoView({{behavior:'smooth',block:'center'}});var i=f.querySelector('input[type=email]');if(i)setTimeout(function(){{i.focus({{preventScroll:true}})}},400)}}}});
b.querySelector('.nl-bar-x').addEventListener('click',function(){{closed=true;upd()}});
var io=new IntersectionObserver(function(es){{es.forEach(function(e){{e.isIntersecting?vis.add(e.target):vis.delete(e.target)}});upd()}});t.forEach(function(x){{io.observe(x)}});
window.addEventListener('scroll',function(){{var p=window.scrollY>window.innerHeight*0.6;if(p!=past){{past=p;upd()}}}},{{passive:true}})}})();</script>'''
# cookie-free visit counter (Supabase function sbi-hit): sends only the path, the referrer's domain and utm tags (?ref= counts as utm_source);
# nothing is sent if the browser has Do Not Track or Global Privacy Control on, or the page isn't on shopbotindex.com
VISIT_JS='''<script>(function(){try{var n=navigator,w=window,h=location.hostname;if(n.doNotTrack=='1'||w.doNotTrack=='1'||n.msDoNotTrack=='1'||n.globalPrivacyControl===true)return;if(h!='shopbotindex.com'&&h!='www.shopbotindex.com')return;if(n.webdriver||/bot|crawl|spider|slurp|headless|lighthouse/i.test(n.userAgent||''))return;
var q=new URLSearchParams(location.search),r='';try{r=document.referrer?new URL(document.referrer).hostname:''}catch(e){}
var b=JSON.stringify({p:location.pathname,r:r,s:q.get('utm_source')||q.get('ref')||'',m:q.get('utm_medium')||'',c:q.get('utm_campaign')||''}),u='https://uufmlmwgvoqhhtqgrclu.supabase.co/functions/v1/sbi-hit';
if(n.sendBeacon)n.sendBeacon(u,new Blob([b],{type:'text/plain'}));else fetch(u,{method:'POST',body:b,keepalive:true,mode:'no-cors'})}catch(e){}})();</script>'''
CFG=json.load(open(os.path.join(ROOT,'config','site.json')))
AFF_URL=CFG['shopify_affiliate_url']; AFF_DISC=CFG['affiliate_disclosure']
def aff():
    s=segstats([r for r in RET if r['segment']=='shopify'])
    return f'''<div class="box"><b>Selling online?</b> In our latest crawl, {s["ucp"]} of the {s["checked"]} Shopify stores we could check publish a UCP profile ({s["rate"]}). <a href="{E(AFF_URL)}" rel="sponsored noopener" target="_blank">Start a Shopify free trial →</a><br><small class="muted">Affiliate link: {E(AFF_DISC)} It never changes a store's result.</small></div>'''
if os.path.isdir(DIST): shutil.rmtree(DIST)
os.makedirs(DIST); open(os.path.join(DIST,'style.css'),'w').write(CSS)
for _f in glob.glob(os.path.join(ROOT,'assets','brand','*')): shutil.copy(_f,DIST)  # logo, favicons, hero art (X branding)
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
# ---- per-store pages: slugs, lookup JSON, check widget, badges ----
def host(x): return (x.get('host') or x['domain']).lower()
def bare(h): return h[4:] if h.startswith('www.') else h
def primary(r):
    ss=SITES_BY[r['id']]
    if r['segment']=='shopify' and '.' in r['id']: return bare(r['id'].lower())
    return bare(host(ss[0])) if ss else ''
def make_slugs(fn):
    nc=collections.Counter(fn(r['name']) or 'store' for r in RET); out={}; used=set()
    for r in sorted(RET,key=lambda r:r['id']):
        b=fn(r['name']) or 'store'
        if nc[b]>1 and primary(r) and fn(primary(r))!=b: b=b+'-'+fn(primary(r))
        x=b; i=2
        while x in used: x=f'{b}-{i}'; i+=1
        used.add(x); out[r['id']]=x
    return out
SLUG=make_slugs(slug)
_new=set(SLUG.values()); OLD_SLUG={k:v for k,v in make_slugs(slug_v1).items() if v!=SLUG[k] and v not in _new}  # old URL -> redirect stub
STATUS_SHORT={'ucp':'Yes: UCP profile found','no_ucp':'No UCP profile found','couldnt_check':"Couldn't check"}
LOOK={}
for r in RET:
    for x in SITES_BY[r['id']]:
        LOOK.setdefault(bare(host(x)),[SLUG[r['id']],r['name'],r['status'],r['id']])
    if primary(r): LOOK.setdefault(primary(r),[SLUG[r['id']],r['name'],r['status'],r['id']])
CHECK_JS='''<script>if(!window.sbiCheck){window.sbiCheck=function(f){const root=f.getAttribute('data-root'),out=f.parentNode.querySelector('.ck-out'),badge=f.hasAttribute('data-badge');
let d=f.querySelector('input').value.trim().toLowerCase().replace(/^[a-z]+:\\/\\//,'').split(/[\\/?#]/)[0].split('@').pop().replace(/:\\d+$/,'').replace(/\\.$/,'');if(d.startsWith('www.'))d=d.slice(4);
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
if(!d||d.indexOf('.')<0){out.innerHTML='Please enter a store domain, like example.com.';return false;}
out.textContent='Looking up…';
const go=L=>{let k=d,hit=null;while(k.indexOf('.')>0){if(L[k]){hit=L[k];break}k=k.slice(k.indexOf('.')+1)}
if(!hit){const m='mailto:hello@shopbotindex.com?subject='+encodeURIComponent('Please add my store: '+d);out.innerHTML='<b>'+esc(d)+'</b> isn\\'t in the index yet. We only report stores our weekly crawl has checked, so we can\\'t say whether it publishes a UCP profile. <a href="'+m+'">Ask us to add it</a> and we\\'ll include it in a future crawl.';return}
const st=hit[2],cls=st=='ucp'?'yes':st=='couldnt_check'?'warn':'no',lbl={ucp:'Yes: UCP profile found',no_ucp:'No UCP profile found',couldnt_check:"Couldn't check (blocked or unreachable)"}[st];
let h='<b>'+esc(hit[1])+'</b> <span class="pill '+cls+'">'+lbl+'</span> in our latest crawl.'+(st=='no_ucp'?' That means no UCP profile was found, not that AI agents can\\'t shop there.':'')+' <a href="'+root+'store/'+hit[0]+'.html">See the full result →</a>'+'<div class="ck-watch" style="margin-top:.5rem"><a href="'+root+'store/'+hit[0]+'.html#watch"><b>Watch '+esc(hit[1])+'</b>: get an email if it starts or stops publishing a UCP profile →</a></div>';
if(f.hasAttribute('data-watch')&&hit[3]){const nm=esc(hit[1]);h=h.split('<div class="ck-watch"')[0]+'<div class="nl-top watch" style="margin-top:.8rem"><p><b>Watch '+nm+'.</b> Email me if '+nm+' starts or stops publishing a UCP profile.</p><form class="nl" action="'+f.getAttribute('data-action')+'" method="post" onsubmit="return sbiSub(this)" data-ok-watch="Thanks! We\\'ll email you if '+nm+' starts or stops publishing a UCP profile, plus the Monday email."><input type="email" name="email" placeholder="you@store.com" required maxlength="254" aria-label="Email address"><input type="hidden" name="watch" value="'+esc(hit[3])+'">'+f.getAttribute('data-hp')+'<button type="submit">Watch this store</button></form><small class="nl-msg" aria-live="polite">Free. You\\'ll also get the Monday email. Unsubscribe or stop the alerts anytime. <a href="'+root+'privacy.html">Privacy</a></small></div>'}
if(badge){h+=st=='ucp'?'<div style="margin-top:.8rem"><img src="'+root+'badge/'+hit[0]+'.svg" alt="UCP profile found · ShopBot Index" height="20"></div><p>Copy this HTML onto your site:</p><textarea readonly rows="3" style="width:100%;font-family:monospace;font-size:.85rem" onclick="this.select()">'+esc('<a href="https://shopbotindex.com/store/'+hit[0]+'.html" title="'+hit[1]+' on ShopBot Index"><img src="https://shopbotindex.com/badge/'+hit[0]+'.svg" alt="UCP profile found · ShopBot Index" height="20"></a>')+'</textarea>':'<p class="muted">The badge is only for stores where our latest crawl found a UCP profile.</p>'}
out.innerHTML=h};
if(window.sbiLook)go(window.sbiLook);else fetch(root+'stores.json').then(r=>r.json()).then(L=>{window.sbiLook=L;go(L)}).catch(()=>{out.textContent='Could not load the store list. Please try again.'});return false;}}</script>'''
CHECK_JS=CHECK_JS.replace("'+f.getAttribute('data-action')+'",FORM_ACTION).replace("'+f.getAttribute('data-hp')+'",HONEYPOT)  # inline watch form (data-watch) posts like every other form
def checkbox(pre='',badge=False,title='Check your store',watch=False):
    return f'''<div class="box ck"><b>{title}</b> Does your store publish a UCP profile, and what else does it tell AI shopping agents? Look it up in our latest crawl ({DAY}).
<form class="ckf" data-root="{pre}"{' data-badge' if badge else ''}{' data-watch' if watch else ''} onsubmit="return sbiCheck(this)" style="margin-top:.6rem;display:flex;flex-wrap:wrap;gap:.5rem"><input type="text" name="d" placeholder="yourstore.com" required maxlength="253" aria-label="Store domain" autocapitalize="off" spellcheck="false" style="padding:.5rem;border:1px solid #cdd5dd;border-radius:6px;min-width:220px;flex:1"> <button type="submit" style="padding:.5rem 1rem;border:0;border-radius:6px;background:#0f1f2e;color:#fff;font-weight:600">Check</button></form>
<div class="ck-out" aria-live="polite" style="margin-top:.6rem"></div>{CHECK_JS}{SIGNUP_JS if watch else ''}</div>'''
def badge_svg(ok):
    l,r=('UCP profile found','ShopBot Index') if ok else ('ShopBot Index','view listing')
    lw=round(len(l)*6.6)+12; rw=round(len(r)*6.6)+12; W=lw+rw; lc='#16a34a' if ok else '#555'; rc='#0f172a' if ok else '#9ca3af'
    t=E(l+' · '+r)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="20" role="img" aria-label="{t}"><title>{t}</title><linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient><clipPath id="r"><rect width="{W}" height="20" rx="3" fill="#fff"/></clipPath><g clip-path="url(#r)"><rect width="{lw}" height="20" fill="{lc}"/><rect x="{lw}" width="{rw}" height="20" fill="{rc}"/><rect width="{W}" height="20" fill="url(#s)"/></g><g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11"><text x="{lw/2}" y="15" fill="#010101" fill-opacity=".3" textLength="{lw-12}">{E(l)}</text><text x="{lw/2}" y="14" textLength="{lw-12}">{E(l)}</text><text x="{lw+rw/2}" y="15" fill="#010101" fill-opacity=".3" textLength="{rw-12}">{E(r)}</text><text x="{lw+rw/2}" y="14" textLength="{rw-12}">{E(r)}</text></g></svg>'''
def snippet(r):
    u=SLUG[r['id']]
    return f'<a href="{SITE}/store/{u}.html" title="{E(r["name"])} on ShopBot Index"><img src="{SITE}/badge/{u}.svg" alt="UCP profile found · ShopBot Index" height="20"></a>'
# ---- home ----
nsites=len(SITES); nsites_u=sum(1 for s in SITES if s.get('status')=='ucp')
joined_txt=(f'<p><b>This week:</b> {len(CHG["joined"])} joined, {len(CHG["left"])} left since {CHG["previous"]}. <a href="changes.html">See who →</a></p>' if CHG else '<p class="muted">Weekly "who joined" starts with the second crawl.</p>')
home=f'''<h1>What online stores tell AI shopping agents</h1>
<p class="lede">Every week we check {len(RET)} retailers and stores ({nsites} websites) to see whether they publish the profile AI shopping agents read. It's called a <a href="https://ucp.dev/">UCP</a> profile. We also record four supporting signals: agent tools, AI rules in robots.txt, AI guidance files and product data. No profile doesn't mean AI agents can't shop there. Every figure comes from our own crawl on {DAY}. <a href="methodology.html#meaning">How we measure</a>.</p>
{segcards()}{joined_txt}
{checkbox()}
<div class="stats"><div class="stat"><b>{len(U)}</b><span>retailers/stores with a UCP profile on at least one site</span></div>
<div class="stat"><b>{PLATC.get("Shopify",0)}</b><span>of them run it on Shopify</span></div>
<div class="stat"><b>{len(NONSHOP)}</b><span>on other platforms</span></div>
<div class="stat"><b>{sum(1 for r in RET if r["status"]=="couldnt_check")}</b><span>couldn't be checked (blocked/unreachable)</span></div></div>
<h2>Big retailers with a UCP profile ({len(BIGU)})</h2>{"<ul class='cols'>"+"".join(f"<li>{E(r['name'])} <small>({r['sites_with_ucp']} of {r['sites_checked']} sites{', '+E('/'.join(r['platforms'])) if r['platforms'] else ''})</small></li>" for r in BIGU)+"</ul>" if BIGU else "<p>None found in this crawl.</p>"}
<h2>UCP profiles not on Shopify ({len(NONSHOP)})</h2>{"<ul class='cols'>"+"".join(f"<li>{E(r['name'])} <small>({E(SEG[r['segment']])})</small></li>" for r in NONSHOP)+"</ul>" if NONSHOP else "<p>None found.</p>"}
<p><a href="stores.html"><b>Browse all {len(RET)} stores →</b></a></p>
<h2>What UCP profiles declare</h2>{bars(CAPC,len(U),capn,lambda k:f"capabilities/{slug(k)}.html")}
<h2>Payment handlers listed</h2>{bars(PHC,len(U),phn)}
<h2>Which AI assistants name which retailers</h2><p>From public announcements and help pages only. <a href="assistants.html">Details →</a></p>
<div class="tw nomax"><table><tr><th>Assistant</th><th>Retailers named</th><th>Source</th></tr>{"".join(f'<tr><td><b>{E(c["assistant"])}</b></td><td>{", ".join(E(x) for x in c["retailers_named"])}</td><td><a href="{E(c["source_url"])}" rel="noopener">{E(c["source_title"].split(" (")[-1].rstrip(")"))}</a>, {E(c["date"])}</td></tr>' for c in CH["channels"])}</table></div>
{signup()}{aff()}'''
page('index.html',f'What online stores tell AI shopping agents: weekly UCP index · {NAME}',home,DEFDESC)
# ---- stores table ----
rows=[]
for r in sorted(RET,key=lambda r:(r['status']!='ucp',r['name'].lower())):
    rows.append(dict(u=SLUG[r['id']],n=r['name'],g=r['segment'],c=r['category'],s=r['status'],co=r['country'][:40] if r['segment']!='shopify' else '',
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
tb.innerHTML=r.slice(0,1500).map(x=>'<tr><td><a href="store/'+x.u+'.html"><b>'+esc(x.n)+'</b></a>'+(x.co?'<br><small>'+esc(x.co)+'</small>':'')+'</td><td>'+esc(SEG[x.g])+'</td><td class="hide-sm">'+esc(x.c)+'</td><td>'+pill(x.s)+'</td><td class="hide-sm">'+esc(x.p)+'</td><td>'+(x.caps.length?'<span class="pill" title="'+esc(x.caps.join(', '))+'">'+x.caps.length+' declared</span>'+(x.caps.includes('Checkout')?'<span class="pill yes">Checkout</span>':''):'')+'</td><td>'+(x.st.length==1?'<a href="https://'+esc(x.st[0].h)+'/.well-known/ucp" rel="nofollow noopener" target="_blank">'+esc(x.st[0].h)+'</a>'+(x.s=='couldnt_check'?' '+pill(x.st[0].s):''):'<details><summary>'+x.st.length+' sites</summary>'+x.st.map(y=>'<div class="child"><a href="https://'+esc(y.h)+'/.well-known/ucp" rel="nofollow noopener" target="_blank">'+esc(y.h)+'</a> '+pill(y.s)+'</div>').join('')+'</details>')+'</td></tr>').join('')}}
['q','fg','fs','fc','fp'].forEach(i=>$(i).addEventListener('input',render));
document.querySelectorAll('th[data-k]').forEach(th=>th.addEventListener('click',()=>{{const k=th.dataset.k;sd=(sk==k)?-sd:1;sk=k;render()}}));render();</script>'''
page('stores.html',f'All {len(RET)} stores checked for UCP | {NAME}',stores,'Sortable table of Shopify stores, big retailers and other online stores and whether they publish a UCP profile.')
# ---- segment pages ----
def rtable(rs,pre='../'):
    li=''.join(f'<tr><td><a href="{pre}store/{SLUG[r["id"]]}.html">{E(r["name"])}</a></td><td class="hide-sm">{E(r["category"])}</td><td>{"<span class=\"pill yes\">Yes</span>" if r["status"]=="ucp" else ("<span class=\"pill warn\">Couldn&#39;t check</span>" if r["status"]=="couldnt_check" else "No")}</td><td>{r["sites_with_ucp"]}/{r["sites_checked"]}</td><td class="hide-sm">{E("/".join(r["platforms"]))}</td></tr>' for r in sorted(rs,key=lambda r:({"ucp":0,"no_ucp":1,"couldnt_check":2}[r["status"]],r["name"].lower())))
    return f'<div class="tw"><table><tr><th>Store</th><th class="hide-sm">Category</th><th>UCP</th><th>Sites with UCP</th><th class="hide-sm">Platform</th></tr>{li}</table></div>'
page('segments/index.html',f'Segments | {NAME}',f'<h1>Segments</h1><p class="lede">We track three groups side by side. Rates exclude stores we couldn\'t check.</p>{segcards("../")}<ul>{"".join(f"<li><b>{SEG[k]}</b>: {SEGDESC[k]}</li>" for k in SEG)}</ul>')
for k in SEG:
    rs=[r for r in RET if r['segment']==k]; s=segstats(rs); cu=collections.Counter(c for r in rs if r['status']=='ucp' for c in r['capabilities'])
    cats=collections.Counter(r['category'] for r in rs)
    ct=''.join(f'<tr><td>{E(c)}</td><td>{n}</td><td>{sum(1 for r in rs if r["category"]==c and r["status"]=="ucp")}</td><td>{sum(1 for r in rs if r["category"]==c and r["status"]=="couldnt_check")}</td></tr>' for c,n in cats.most_common())
    page(f'segments/{k}.html',f'{SEG[k]}: UCP adoption | {NAME}',f'<h1>{SEG[k]}</h1><p class="lede">{SEGDESC[k]} {s["ucp"]} of {s["checked"]} we could check publish a UCP profile ({s["rate"]}); {s["cc"]} couldn\'t be checked.</p><h2>By category</h2><div class="tw nomax"><table><tr><th>Category</th><th>Tracked</th><th>With UCP</th><th>Couldn\'t check</th></tr>{ct}</table></div>{"<h2>Capabilities declared</h2>"+bars(cu,s["ucp"],capn) if s["ucp"] else ""}<h2>All {len(rs)}</h2>{rtable(rs)}'+(aff() if k=='shopify' else ''))
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
page('assistants.html',f'AI assistants and the retailers they name | {NAME}',f'<h1>AI assistants and the retailers they name</h1><p class="lede">{E(CH["note"])} Last checked {E(CH["checked_on"])}.</p><div class="tw nomax"><table><tr><th>Assistant</th><th>Feature</th><th>Retailers named</th><th>Date</th><th>Source</th></tr>{li}</table></div>')
# ---- changes ----
def _dlong(d): x=_dt.date.fromisoformat(d); return f'{x.day} {x.strftime("%B")} {x.year}'
import datetime as _dt
def _hist():
    # every comparison our saved crawls allow (consecutive crawl-*.json files in the current format); nothing is typed in by hand
    cs=[]
    for f in sorted(glob.glob(os.path.join(DATA,'crawl-*.json'))):
        d=json.load(open(f))
        if 'retailers' in d: cs.append(d)
    out=[]
    for a,b in zip(cs,cs[1:]):
        A={r['id']:r['status'] for r in a['retailers']}
        j=sum(1 for r in b['retailers'] if r['status']=='ucp' and r['id'] in A and A[r['id']]!='ucp')
        l=sum(1 for r in b['retailers'] if A.get(r['id'])=='ucp' and r['status']=='no_ucp')
        u=sum(1 for r in b['retailers'] if A.get(r['id'])=='ucp' and r['status']=='couldnt_check')
        out.append((a['crawl_date'],b['crawl_date'],j,l,u,sum(1 for r in b['retailers'] if r['status']=='ucp')))
    return cs,out
CHGTITLE='What changed: stores that started or stopped publishing a UCP profile'
if CHG:
    pv=_dlong(CHG['previous']); cu=_dlong(DAY); nT=len(RET); nU=sum(1 for r in RET if r['status']=='ucp')
    SL=lambda i: f'<a href="store/{SLUG[i]}.html">{E(NM[i]["name"])}</a> <small>({E(SEG[NM[i]["segment"]])})</small>'
    def L(ids,why,empty): return '<ul>'+''.join(f'<li>{SL(i)}: {why(i) if callable(why) else why}</li>' for i in ids)+'</ul>' if ids else f'<p>{empty}</p>'
    n=lambda k: len(CHG[k])
    pl=lambda k,one,many: (one if n(k)==1 else many).format(n=n(k))
    intro=(f'<p class="lede">Between our crawls of {pv} and {cu}, {pl("joined","{n} retailer or store","{n} retailers and stores")} started publishing a UCP profile, the profile AI shopping agents read, '
           f'and {n("left")} stopped. Of the stores that had a profile, {n("now_unreachable")} couldn&#39;t be checked this time, so '
           f'{"it is" if n("now_unreachable")==1 else "they are"} not counted as leaving. In the crawl of {cu}, {nU} of the {nT} retailers and stores we track publish a UCP profile.</p>'
           f'<p>How we count: each crawl is compared, store by store, with the previous one. <b>Joined</b> means a store we already tracked now has a UCP profile at <code>/.well-known/ucp</code> after the previous crawl found none or couldn\'t check it. '
           f'<b>Left</b> means a store had a profile in the previous crawl and its website answered this time without one. <b>Couldn\'t check</b> means the website blocked our crawler or was unreachable, so we don\'t know, and we never count that as leaving. '
           f'Stores added to our list are shown as newly tracked, not as joining. Details are in the <a href="methodology.html#changes">methodology</a>.</p>')
    cc=''.join(f'<li><a href="store/{SLUG[x["id"]]}.html">{E(NM[x["id"]]["name"])}</a>: {"added "+", ".join(capn(a) for a in x["added"]) if x["added"] else ""}{"; " if x["added"] and x["removed"] else ""}{"removed "+", ".join(capn(a) for a in x["removed"]) if x["removed"] else ""}</li>' for x in CHG['capability_changes'])
    cs,H=_hist()
    def joined_why(i):
        # wording follows what each crawl actually saw: checked without a profile, couldn't check, or had one in an earlier crawl and is back
        if PR[i]['status']=='couldnt_check': return f"we couldn&#39;t check it on {pv}; it publishes a profile now."
        had=[c['crawl_date'] for c in cs if c['crawl_date']<CHG['previous'] and any(r['id']==i and r['status']=='ucp' for r in c['retailers'])]
        if had: return f"UCP profile found on {_dlong(had[-1])}, none found on {pv}; it publishes one again on {cu}."
        return f"no UCP profile found on {pv}, profile found on {cu}."
    if len(H)>1:
        hist='<h2>Earlier comparisons</h2><div class="tw"><table><tr><th>Crawls compared</th><th>Joined</th><th>Left</th><th>Had a profile, now couldn\'t check</th><th>With a UCP profile</th></tr>'+''.join(f'<tr><td>{_dlong(a)} → {_dlong(b)}</td><td>{j}</td><td>{l}</td><td>{u}</td><td>{t}</td></tr>' for a,b,j,l,u,t in reversed(H))+'</table></div>'
    else:
        hist=f'<h2>Earlier comparisons</h2><p>None yet. Our crawl of {_dlong(cs[0]["crawl_date"])} is the first one saved in this format, so this is the first comparison. Each new crawl adds a row here.</p>'
    body=f'''<h1>{CHGTITLE}</h1>{intro}
<h2>Joined: newly publishing a UCP profile ({n("joined")})</h2>{L(CHG["joined"],joined_why,f"No store started publishing a UCP profile between {pv} and {cu}.")}
<h2>Left: profile no longer found ({n("left")})</h2>{L(CHG["left"],f"UCP profile found on {pv}, none found on {cu}.",f"No store stopped publishing a UCP profile between {pv} and {cu}.")}
<h2>Had a profile, now couldn't check ({n("now_unreachable")})</h2><p class="muted">Not counted as leaving: the site blocked us or was unreachable this time.</p>{L(CHG["now_unreachable"],f"UCP profile found on {pv}; on {cu} the site blocked us or was unreachable.",f"Every store that had a UCP profile on {pv} could be checked again on {cu}.")}
<h2>Capability changes ({len(CHG["capability_changes"])})</h2>{"<ul>"+cc+"</ul>" if cc else f"<p>No store changed its declared capabilities between these two crawls.</p>"}
<h2>Newly tracked ({n("newly_tracked")})</h2><p class="muted">Added to our list this time; not counted as joining.</p>{L(CHG["newly_tracked"],"added to our list for this crawl.",f"No stores were added to our list between {pv} and {cu}; we tracked the same {nT} both times.")}
{hist}'''
else:
    body=f'<h1>{CHGTITLE}</h1><p class="lede">Each week we compare the new crawl with the previous one: who joined (started publishing a UCP profile), who left, who we couldn\'t reach, and capability changes.</p><div class="box">Only one crawl in this format exists so far ({DAY}). The first "who joined this week" list appears after the next crawl.</div>'
page('changes.html',f'What changed: stores that started or stopped publishing a UCP profile | {NAME}',body+signup())
# ---- agent-readiness signals (phase 2 of the crawl) ----
import datetime as _dt; _nd=_dt.date.fromisoformat(DAY)+_dt.timedelta(days=7-_dt.date.fromisoformat(DAY).weekday()); NEXTCRAWL=f'{_nd.day} {_nd.strftime("%B")} {_nd.year}'  # next Monday after the crawl
HAS_SIG=any((r.get('signals') or {}).get('checked') for r in RET)
TOKFAM={'ChatGPT-User':'OpenAI, user-requested','Claude-User':'Anthropic, user-requested','Perplexity-User':'Perplexity, user-requested','Google-Agent':'Google, user-requested',
 'OAI-SearchBot':'OpenAI search','Claude-SearchBot':'Anthropic search','PerplexityBot':'Perplexity search','GPTBot':'OpenAI training','ClaudeBot':'Anthropic training','Google-Extended':'Google Gemini training/grounding'}
RSTATE={'blocked':'asks it to stay out of the whole site','mostly_blocked':'disallows the whole site except some paths','restricted':'disallows some paths','allowed':'explicitly allows it'}
def sigpill(cls,lbl): return f'<span class="pill {cls}">{E(lbl)}</span>'
def readiness(r):
    sg=r.get('signals') or {}; st=r['status']
    if not sg.get('checked'):
        why=f'We start checking these signals with the next weekly crawl on {NEXTCRAWL}.' if not HAS_SIG else "We couldn't check these signals this week: none of this store's websites answered our crawler, or our weekly time budget ran out before we reached it."
        return f'<h2 id="readiness">Supporting signals</h2><p class="muted">{why} <a href="../methodology.html#signals">What we check</a>.</p>'
    rows=[]
    capl=[capn(c) for c in r['capabilities']]
    if st=='ucp':
        t='Publishes a UCP profile at <code>/.well-known/ucp</code>'
        if capl: t+=f' declaring {len(capl)} capabilit{"y" if len(capl)==1 else "ies"}'+(', including checkout' if 'dev.ucp.shopping.checkout' in r['capabilities'] else '')
        ucpt=(('yes','Found'),t+'.')
    elif st=='no_ucp': ucpt=(('no','No profile'),'No UCP profile found at <code>/.well-known/ucp</code>.')
    else: ucpt=(('warn',"Couldn't check"),"Couldn't check: our request for the profile was refused or failed.")
    extra=(' Also publishes an Agentic Commerce Protocol (ACP) discovery document at <code>/.well-known/acp.json</code>.' if sg.get('acp') else '')+(' Also publishes an AI catalog at <code>/.well-known/ai-catalog.json</code>.' if sg.get('ai_catalog') else '')
    rows.append(('UCP profile',ucpt[0],ucpt[1]+extra))
    m=sg.get('mcp',{}); ms=m.get('state','not_checked'); tl=m.get('tools',[])
    if ms=='answered': mrow=(('yes','Answered'),f'The MCP endpoint named in its UCP profile answered our read-only tools list request with {len(tl)} tool{"s" if len(tl)!=1 else ""}: '+', '.join(f'<code>{E(t)}</code>' for t in tl)+'. We never call the tools.')
    elif ms=='no_tools': mrow=(('no','No tools list'),"Its UCP profile names an MCP endpoint, but it didn't return a tools list to our request.")
    elif st=='ucp' and ms=='none_declared': mrow=(('no','None declared'),'Its UCP profile declares no MCP endpoint.')
    elif st=='no_ucp': mrow=(('no','No endpoint'),'No UCP profile, so no MCP endpoint to check. We only look for one in a UCP profile.')
    else: mrow=(('warn','Not checked'),'Not checked this week.')
    rows.append(('Agent tools (MCP)',)+mrow)
    rb=sg.get('robots',{})
    if not rb.get('present'): rows.append(('AI rules (robots.txt)',('warn','Not checked'),"We couldn't read a robots.txt for this site."))
    else:
        sp=rb.get('specific',{})
        if sp:
            by=collections.defaultdict(list)
            for t,v in sp.items(): by[v].append(t)
            order=['blocked','mostly_blocked','restricted','allowed']
            txt=' '.join('robots.txt '+RSTATE[v]+' for '+', '.join(f'<code>{E(t)}</code> <small>({E(TOKFAM.get(t,""))})</small>' for t in ts)+'.' for v,ts in sorted(by.items(),key=lambda kv:order.index(kv[0])))
            state=('warn','Names AI agents') if any(v in ('blocked','mostly_blocked') for v in sp.values()) else ('no','Names AI agents')
        else: txt='Its robots.txt has no rules that name AI agents.'; state=('no','No AI-specific rules')
        if rb.get('wildcard') in ('blocked','mostly_blocked'): txt+=' Its general rule (<code>User-agent: *</code>) '+RSTATE[rb['wildcard']].replace(' it',' them')+' for all crawlers.'
        if rb.get('content_signal'): txt+=' Content signals: '+'; '.join(f'<code>{E(c)}</code>' for c in rb['content_signal'])+'.'
        txt+=" <small class=\"muted\">robots.txt states the site's wishes. OpenAI, Perplexity and Google say agents acting on a user's request may not follow it; Anthropic says Claude-User does.</small>"
        rows.append(('AI rules (robots.txt)',state,txt))
    g=[x for x,k in (('<code>/llms.txt</code>','llms_txt'),('<code>/agents.md</code>','agents_md')) if sg.get(k)]
    gs=sg.get('guide_state','found' if g else 'not_found')
    rows.append(('AI guidance files',('yes','Found') if g else ('no','Not found') if gs=='not_found' else ('warn','Not checked'),('Publishes '+' and '.join(g)+'.') if g else 'No <code>/llms.txt</code> or <code>/agents.md</code> found.' if gs=='not_found' else "Not checked: our requests for these files were refused or failed."))
    pr=sg.get('product',{}); ps=pr.get('state','not_checked')
    pt={'full':'A product page we checked has schema.org Product markup with price, currency and availability.','partial':'A product page we checked has schema.org Product markup, but not all of price, currency and availability.',
        'none':'We found no schema.org Product markup on the page we checked.'}.get(ps,"Not checked: we couldn't reach a product page.")
    if pr.get('url') and ps in ('full','partial','none'): pt+=f' <small>(<a href="{E(pr["url"])}" rel="nofollow noopener" target="_blank">page checked</a>)</small>'
    rows.append(('Product data',{'full':('yes','Found'),'partial':('warn','Partial'),'none':('no','Not found')}.get(ps,('warn','Not checked')),pt))
    tr=''.join(f'<tr><td><b>{E(a)}</b></td><td>{sigpill(*b)}</td><td>{c}</td></tr>' for a,b,c in rows)
    ac=sg.get('access',{}); note=''
    if ac.get('state')=='refused':
        note='<p class="muted"><b>Note:</b> this site\'s bot protection refused our identified crawler'+(' with a challenge page' if ac.get('challenge') else '')+", so some of these signals couldn't be checked. That says nothing about whether shoppers or AI agents can use the site.</p>"
    intro=f'Public signals we checked on {DAY}, besides the UCP profile. They show what the store publishes for AI agents; none of them says whether a particular AI agent can or can\'t buy here.'
    return f'<h2 id="readiness">Supporting signals</h2><p>{intro} <a href="../methodology.html#signals">What each signal means</a>.</p><div class="tw nomax"><table><tr><th>Signal</th><th>Result</th><th>Details</th></tr>{tr}</table></div>{note}'
# ---- store pages ----
SEG1={'shopify':'a Shopify store','big':'a big retailer','other':'a retailer or marketplace'}
def store_desc(r):
    d=primary(r); nm=r['name']; who=nm if nm.lower()==d else f'{nm} ({d})' if d else nm
    intro=f"{who} is {SEG1[r['segment']]} we track, listed under {r['category']}"+(f" in {r['country']}" if r.get('country') else '')+'.'
    if r['status']=='ucp':
        k=len(r['capabilities']); ck=' including checkout' if 'dev.ucp.shopping.checkout' in r['capabilities'] else ''
        return f"{intro} In ShopBot Index's crawl of {DAY}, it publishes a UCP profile, the profile AI shopping agents read, at /.well-known/ucp, declaring {k} capabilit{'y' if k==1 else 'ies'}{ck}."
    if r['status']=='no_ucp':
        ss=SITES_BY[r['id']]; n=sum(1 for x in ss if x.get('status') in ('no_ucp','not_json','json_without_ucp'))
        reached='its website' if len(ss)==1 else f'{n} of its {len(ss)} websites' if n<len(ss) else f'its {len(ss)} websites'
        return f"{intro} In ShopBot Index's crawl of {DAY}, we reached {reached} but found no UCP profile, the profile AI shopping agents read, at /.well-known/ucp. That doesn't mean AI agents can't shop there."
    return f"{intro} In ShopBot Index's crawl of {DAY}, we couldn't check whether it publishes a UCP profile: every request was refused or failed. That is not the same as no profile."
PILL={'ucp':'yes','no_ucp':'no','couldnt_check':'warn'}
HIST=[]  # (date, {id: (status, n capabilities)}) from every saved weekly crawl, oldest first
for _f in sorted(glob.glob(os.path.join(DATA,'crawl-*.json'))):
    _d=json.load(open(_f))
    if 'retailers' in _d and _d.get('crawl_date')!=DAY: HIST.append((_d['crawl_date'],{x['id']:(x['status'],len(x.get('capabilities') or [])) for x in _d['retailers']}))
HIST.append((DAY,{x['id']:(x['status'],len(x.get('capabilities') or [])) for x in RET}))
def history(r):
    rows=[(d,m[r['id']]) for d,m in HIST if r['id'] in m]
    tr=''.join(f'<tr><td>{E(d)}</td><td><span class="pill {PILL[st]}">{E(STL[st])}</span></td><td class="hide-sm">{(str(k)+" capabilit"+("y" if k==1 else "ies")) if st=="ucp" else ""}</td></tr>' for d,(st,k) in reversed(rows))
    first=f'We have tracked it in every weekly crawl since {E(rows[0][0])}.' if len(rows)>1 else f'Our crawl of {E(DAY)} is the first that included it.'
    return f'<h2>Weekly results</h2><p>{first} Each Monday\'s crawl adds a row.</p><div class="tw nomax"><table><tr><th>Crawl</th><th>UCP profile</th><th class="hide-sm">Declared</th></tr>{tr}</table></div>'
BYCAT=collections.defaultdict(list)
for _r in RET: BYCAT[_r['category']].append(_r)
def related(r):
    pool=[x for x in BYCAT[r['category']] if x['id']!=r['id']]; c=r.get('country') or ''
    same=[x for x in pool if c and x.get('country')==c]
    key=lambda x:({'ucp':0,'no_ucp':1,'couldnt_check':2}[x['status']],-x.get('sitelinks',0),x['name'].lower())
    if len(same)>=4: pick=sorted(same,key=key)[:8]; where=f' in {c}'
    else: pick=sorted(pool,key=key)[:8]; where=''
    if not pick: return ''
    li=''.join(f'<li><a href="{SLUG[x["id"]]}.html">{E(x["name"])}</a> <span class="pill {PILL[x["status"]]}">{E(STL[x["status"]])}</span></li>' for x in pick)
    return f'<h2>Other stores in {E(r["category"])}{E(where)}</h2><ul>{li}</ul><p><a href="../categories/{slug(r["category"])}.html">All {len(BYCAT[r["category"]])} stores in {E(r["category"])}</a></p>'
for r in RET:
    u=SLUG[r['id']]; d=primary(r); ss=SITES_BY[r['id']]; st=r['status']
    sites=''.join(f'<tr><td><a href="https://{E(host(x))}/.well-known/ucp" rel="nofollow noopener" target="_blank">{E(host(x))}</a></td><td><span class="pill {"yes" if x.get("status")=="ucp" else "warn" if x.get("status") in ("blocked","error","robots_disallow") else "no"}">{E(SITEST.get(x.get("status","error"),x.get("status")))}</span></td><td class="hide-sm">{E(x.get("http_status") or "")}</td></tr>' for x in ss)
    caps=('<h2>What its UCP profile declares</h2><h3>Capabilities</h3><ul>'+''.join(f'<li>{E(capn(c))} <small><code>{E(c)}</code></small></li>' for c in r['capabilities'])+'</ul>'
          +('<h3>Payment handlers</h3><ul>'+''.join(f'<li>{E(phn(x))} <small><code>{E(x)}</code></small></li>' for x in r['payment_handlers'])+'</ul>' if r['payment_handlers'] else '')
          +(f'<p>Platform: {E(" / ".join(r["platforms"]))}</p>' if r['platforms'] else '')) if st=='ucp' else ''
    meaning={'ucp':'AI shopping agents that use the Universal Commerce Protocol can read this store\'s profile to see what it supports'+(', including checkout' if 'dev.ucp.shopping.checkout' in r['capabilities'] else '')+'. It doesn\'t guarantee that a given assistant buys from it; that depends on the assistant.',
             'no_ucp':'At least one of its websites answered our request, but none published a UCP profile. AI agents may still be able to shop here, for example through a normal web browser, or through channels we can\'t see from outside, such as product feeds shared privately with AI assistants. The supporting signals below show what else the store tells AI agents.',
             'couldnt_check':'Every website we tried refused our request, timed out or disallowed it in robots.txt. We never try to get around that, so we don\'t know whether it publishes a profile. It is excluded from adoption rates.'}[st]
    badge=(f'<h2>Badge for this store</h2><p>{E(r["name"])} can show that it publishes a UCP profile. Paste this HTML on the site; it links back to this page.</p><p><img src="../badge/{u}.svg" alt="UCP profile found · ShopBot Index" height="20"></p><textarea readonly rows="3" style="width:100%;font-family:monospace;font-size:.85rem" onclick="this.select()">{E(snippet(r))}</textarea><p class="muted"><a href="../badge.html">About the badge</a>. If a later crawl stops finding the profile, the badge turns into a neutral grey "view listing" link.</p>') if st=='ucp' else ''
    jsonld=json.dumps({"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":NAME,"item":SITE+"/"},{"@type":"ListItem","position":2,"name":"All stores","item":SITE+"/stores.html"},{"@type":"ListItem","position":3,"name":r['name'],"item":f"{SITE}/store/{u}.html"}]},ensure_ascii=False).replace('</','<\\/')
    body=f'''<p class="muted"><a href="../stores.html">All stores</a> › <a href="../segments/{r["segment"]}.html">{E(SEG[r["segment"]])}</a></p>
<h1>What does {E(r["name"])} tell AI shopping agents?</h1>
<p class="lede"><span class="pill {PILL[st]}" style="font-size:1rem">{E(STATUS_SHORT[st])}</span> {E(store_desc(r))}</p>
<div class="box"><b>What this means.</b> {meaning}</div>
{watch_form(r)}
<h2>Websites checked ({len(ss)})</h2><p>We fetched <code>/.well-known/ucp</code> on each site on {DAY}.</p><div class="tw nomax"><table><tr><th>Website</th><th>Result</th><th class="hide-sm">HTTP</th></tr>{sites}</table></div>
{caps}
{readiness(r)}
{history(r)}
<h2>About this store in the index</h2><ul><li>Segment: <a href="../segments/{r["segment"]}.html">{E(SEG[r["segment"]])}</a></li><li>Category: <a href="../categories/{slug(r["category"])}.html">{E(r["category"])}</a></li>{f'<li>Country: {E(r["country"])}</li>' if r["country"] else ''}<li>Last checked: {DAY} (re-checked every week)</li></ul>
{related(r)}
{badge}
<p>Run this store and think the result is wrong, or want it removed? Email {MAILTO} with the domain; we re-check it in the next weekly crawl and never change a result by hand. <a href="../methodology.html">How we measure</a>.</p>
{checkbox("../",title="Check another store")}{signup("../")}'''
    page(f'store/{u}.html',f'{r["name"]}: UCP profile and AI-agent signals | {NAME}',body,store_desc(r),ogimg='og-store.png',ogtype='article',head=f'<script type="application/ld+json">{jsonld}</script>')
# old URLs of stores whose slug changed (accented letters used to be dropped): redirect stubs, kept out of the sitemap
for _id,_o in OLD_SLUG.items():
    _u=f'{SITE}/store/{SLUG[_id]}.html'
    open(os.path.join(DIST,'store',f'{_o}.html'),'w').write(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{E(NM[_id]["name"])} | {NAME}</title><link rel="canonical" href="{_u}"><meta http-equiv="refresh" content="0; url={SLUG[_id]}.html"><script>location.replace("{SLUG[_id]}.html")</script></head><body><p>This page moved to <a href="{SLUG[_id]}.html">{_u}</a>.</p></body></html>')
_ncc=sum(1 for r in RET if r['status']=='couldnt_check')
# ---- store-owner landing: look up your store, then watch it (draft for review) ----
page('for-stores.html',f'For store owners: what does your store tell AI shopping agents? | {NAME}',f'''<h1>For store owners: what does your store tell AI shopping agents?</h1><p class="lede">Every Monday we check {len(RET)} retailers and stores for a UCP profile, the profile AI shopping agents read, published at <code>/.well-known/ucp</code>. Look up your store, then watch it: we'll email you when your result changes.</p>
{checkbox(title="Look up your store",watch=True)}
<h2>What your result means</h2><div class="tw nomax"><table><tr><th>Result</th><th>What it means</th><th>What you can do</th></tr>
<tr><td><span class="pill yes">UCP profile found</span></td><td>Your store publishes a UCP profile at <code>/.well-known/ucp</code>. Your store page lists the capabilities the profile declares.</td><td>Watch your store so you hear if a later crawl stops finding it. Show a <a href="badge.html">badge</a> on your site.</td></tr>
<tr><td><span class="pill no">No UCP profile found</span></td><td>Our crawler reached your site but found no UCP profile at <code>/.well-known/ucp</code>. That doesn't mean AI agents can't shop at your store; it only means we found no profile.</td><td>Read the <a href="https://ucp.dev/specification/overview/">UCP specification</a> or your ecommerce platform's documentation. Watch your store: we'll email you when a crawl finds a profile.</td></tr>
<tr><td><span class="pill warn">Couldn't check</span></td><td>Your site blocked our crawler or didn't answer, so we don't know whether it publishes a UCP profile. We don't count it either way.</td><td>Our crawler identifies itself as <code>ShopBotIndexBot/1.0</code> and honours robots.txt (<a href="methodology.html#crawler">details</a>). We try again every Monday.</td></tr>
<tr><td>Not in the index</td><td>Our weekly crawl hasn't checked your store, so we can't say anything about it.</td><td><a href="mailto:{CONTACT}?subject=Please%20add%20my%20store">Ask us to add it</a> and we'll include it in a future crawl.</td></tr></table></div>
<h2>Why watch your store</h2><ul><li>We email you when our weekly crawl finds that your store started or stopped publishing a UCP profile.</li><li>You also get the Monday email: which stores started or stopped publishing a UCP profile.</li><li>Free. Unsubscribe or stop the alerts anytime. We only store what's needed to send the emails (<a href="privacy.html">privacy</a>).</li></ul>
<h2>What else we record</h2><p>Each store page also lists four supporting signals: agent tools, AI rules in robots.txt, AI guidance files and product data. None of them says whether a particular AI agent can or can't buy at your store. <a href="methodology.html#meaning">What each signal means</a>.</p>
<h2>From our latest crawl ({DAY})</h2><ul><li>{len(U)} of the {len(RET)-_ncc} retailers and stores we could check publish a UCP profile; {PLATC.get("Shopify",0)} of them run it on Shopify.</li><li>We couldn't check {_ncc} of the {len(RET)} we track (blocked or unreachable), so they aren't counted.</li><li><a href="changes.html">What changed this week</a> · <a href="stores.html">All stores</a></li></ul>
<p>Think your result is wrong, or want your store removed? Email {MAILTO} with the domain; we re-check it in the next weekly crawl and never change a result by hand.</p>{signup()}''',f'Look up your store in the ShopBot Index weekly crawl, see whether it publishes a UCP profile, the profile AI shopping agents read, and get an email when your result changes.')
# ---- check + badge pages, lookup JSON, badge SVGs ----
page('check.html',f'Check your store: what does it tell AI shopping agents? | {NAME}',f'''<h1>Check your store</h1><p class="lede">Type a store's domain to see whether our latest weekly crawl ({DAY}) found a Universal Commerce Protocol (UCP) profile, the machine-readable profile AI shopping agents read. We track {len(RET)} retailers and stores. No UCP profile found doesn't mean AI agents can't shop there (<a href="methodology.html#meaning">details</a>). Each store's page also lists its supporting signals: agent tools, AI rules in robots.txt, AI guidance files and product data.</p>
{checkbox(title="Look up a store")}<h2>How it works</h2><ul><li>This looks the domain up in our published results. It doesn't fetch anything from your store live.</li><li>Results are updated every Monday after the weekly crawl.</li><li>Not in the index? Use the link in the result to ask us to add it.</li><li>Have a UCP profile? Get a <a href="badge.html">badge for your site</a>.</li><li>Run a store? <a href="for-stores.html">See what your result means and watch your store</a>.</li></ul>{signup()}''',f'Look up any store in ShopBot Index: what does it tell AI shopping agents? Its UCP profile and supporting signals from our weekly crawl of {len(RET)} retailers and stores.')
page('badge.html',f'"UCP profile found" badge for your store | {NAME}',f'''<h1>A "UCP profile found" badge for your store</h1><p class="lede">Stores where our latest crawl found a UCP profile can show it with a small badge that links to their ShopBot Index page. The badge covers the UCP profile only. Supporting signals are listed on each store's page and don't affect the badge.</p>
<p><img src="badge/{SLUG[U[0]["id"]] if U else ""}.svg" alt="UCP profile found · ShopBot Index" height="20"> <small class="muted">(example)</small></p>
{checkbox(badge=True,title="Get your badge")}<h2>Rules</h2><ul><li>The badge is only offered for stores where our latest crawl found a profile at <code>/.well-known/ucp</code>.</li><li>Each badge is served from shopbotindex.com and is regenerated every week. If a later crawl no longer finds the profile, it turns into a neutral grey "ShopBot Index · view listing" badge.</li><li>No tracking: the badge is a plain SVG image, with no scripts or cookies.</li></ul>{signup()}''','Stores that publish a UCP profile can embed a free "UCP profile found · ShopBot Index" badge linking to their result page.')
json.dump(LOOK,open(os.path.join(DIST,'stores.json'),'w'),ensure_ascii=False,separators=(',',':'))
os.makedirs(os.path.join(DIST,'badge'),exist_ok=True); _B={True:badge_svg(True),False:badge_svg(False)}
for r in RET: open(os.path.join(DIST,'badge',SLUG[r['id']]+'.svg'),'w').write(_B[r['status']=='ucp'])
for _id,_o in OLD_SLUG.items(): open(os.path.join(DIST,'badge',_o+'.svg'),'w').write(_B[NM[_id]['status']=='ucp'])  # badges already pasted on sites under the old slug keep working
# ---- methodology ----
import importlib.util as _ilu
_sp=_ilu.spec_from_file_location('sbi_crawl',os.path.join(ROOT,'scripts','crawl.py')); _cm=_ilu.module_from_spec(_sp); _sp.loader.exec_module(_cm)
CRAWL_UA=_cm.UA
UA_NOTE='' if D.get('user_agent')==CRAWL_UA else f' <small class="muted">(The crawl of {DAY} still used the earlier User-Agent <code>{E(D.get("user_agent",""))}</code>, which read only <code>/robots.txt</code> and <code>/.well-known/ucp</code>.)</small>'
SIGMETH=f'''<h2 id="signals">1b. Supporting signals (beyond UCP)</h2><p>UCP stays our headline measure and trend. Since October 2026 we also record other public signals of how a store presents itself to AI agents. Each store page lists them separately; we don't combine them into a score.</p>
<div class="tw nomax"><table><tr><th>Signal</th><th>How we check</th><th>What it means</th><th>What it doesn't mean</th></tr>
<tr><td><b>UCP profile</b></td><td><code>/.well-known/ucp</code> (see section 1)</td><td>The store publishes the machine-readable profile and lists what it supports.</td><td>That any particular assistant buys from it.</td></tr>
<tr><td><b>Agent tools (MCP)</b></td><td>If the UCP profile names an MCP endpoint, we send one read-only JSON-RPC <code>tools/list</code> request, identifying ourselves with our <a href="ucp/agent-profile.json">agent profile</a>. We never call a tool.</td><td>The endpoint is live and lists tools (for example catalog search, cart, checkout) right now.</td><td>That a purchase completes without the buyer; checkouts may hand the buyer back to the store's own checkout page.</td></tr>
<tr><td><b>AI rules (robots.txt)</b></td><td>Groups in <code>/robots.txt</code> that name <code>ChatGPT-User</code>, <code>Claude-User</code>, <code>Perplexity-User</code>, <code>Google-Agent</code>, <code>OAI-SearchBot</code>, <code>Claude-SearchBot</code>, <code>PerplexityBot</code>, <code>GPTBot</code>, <code>ClaudeBot</code> or <code>Google-Extended</code>, plus <code>Content-Signal</code> lines. Tokens from <a href="https://developers.openai.com/api/docs/bots">OpenAI</a>, <a href="https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler">Anthropic</a>, <a href="https://docs.perplexity.ai/docs/resources/perplexity-crawlers">Perplexity</a> and <a href="https://developers.google.com/crawling/docs/crawlers-fetchers/google-user-triggered-fetchers">Google</a>.</td><td>The site's stated wishes for each kind of AI agent: user-requested, search or training.</td><td>A technical block or permission. OpenAI, Perplexity and Google say their user-requested agents may not follow robots.txt; Anthropic says its bots do.</td></tr>
<tr><td><b>AI guidance files</b></td><td><code>/llms.txt</code> and <code>/agents.md</code> (Markdown files, not web pages)</td><td>The site publishes instructions for AI assistants. On Shopify these are generated by the platform.</td><td>That assistants read them; <a href="https://llmstxt.org/">llms.txt</a> is a community proposal, not a formal standard.</td></tr>
<tr><td><b>Product data</b></td><td>One page that looks like a product page, found via a link on the home page or, failing that, at most two sitemap files. We look for <a href="https://schema.org/Product">schema.org Product</a> markup with an Offer that has price, currency and availability.</td><td>Product facts are machine-readable on the page.</td><td>Anything about checkout. "Not checked" means we couldn't reach a product page, often because of bot protection or pages built by scripts.</td></tr></table></div>
<p>We also record, without a public column until a store first publishes one, two newer discovery files: the <a href="https://github.com/agentic-commerce-protocol/agentic-commerce-protocol">Agentic Commerce Protocol</a> discovery document at <code>/.well-known/acp.json</code> and the MCP <a href="https://modelcontextprotocol.io/seps/2127-mcp-server-cards">AI catalog</a> at <code>/.well-known/ai-catalog.json</code>.</p>
<p>We also read <code>/.well-known/poppy.json</code> (<a href="https://personalagentprotocol.org/docs/spec">Personal Agent Protocol</a>), <code>/.well-known/agent-card.json</code> and <code>/.well-known/agent.json</code> (<a href="https://a2a-protocol.org/latest/topics/agent-discovery/">A2A agent card</a>), and <code>ai-catalog.json</code> above, record-only: no public column, and they never change a store's results.</p>
<p>When a site's bot protection refuses our identified crawler, its store page says so in a neutral note. That only describes how the site treated our crawler, not whether shoppers or AI agents can use it.</p>
<h3 id="cant-see">What we can't see from outside</h3><p>A lot of agent shopping runs through channels that leave no public trace on a store's website. We never count these as "no":</p><ul>
<li><b>ChatGPT product feeds:</b> merchants share catalogs with OpenAI privately through the Agentic Commerce Protocol (<a href="https://openai.com/index/powering-product-discovery-in-chatgpt/">OpenAI, March 2026</a>).</li>
<li><b>Shopify Catalog and agentic storefronts:</b> Shopify syndicates eligible stores to AI channels, managed in each store's admin (<a href="https://help.shopify.com/en/manual/online-sales-channels/agentic-storefronts">Shopify Help Center</a>).</li>
<li><b>Microsoft Copilot Checkout</b> enrolment (<a href="https://about.ads.microsoft.com/en/blog/post/january-2026/conversations-that-convert-copilot-checkout-and-brand-agents">Microsoft Advertising</a>).</li>
<li><b>Card-network agent programs:</b> Visa Intelligent Commerce and its <a href="https://developer.visa.com/capabilities/trusted-agent-protocol/trusted-agent-protocol-specifications/">Trusted Agent Protocol</a>, and Mastercard Agent Pay (<a href="https://blog.cloudflare.com/secure-agentic-commerce/">Cloudflare</a>).</li>
<li><b>Web Bot Auth:</b> whether a store verifies signed AI agents (<a href="https://developers.cloudflare.com/bots/reference/bot-verification/web-bot-auth/">Cloudflare docs</a>).</li></ul>'''
CRAWLMETH=f'''<h2 id="crawler">5. How we fetch</h2><ul><li>User-Agent: <code>{E(CRAWL_UA)}</code>{UA_NOTE}</li>
<li>What we read on each website, and nothing else: <code>/robots.txt</code>, <code>/.well-known/ucp</code>, <code>/.well-known/acp.json</code>, <code>/.well-known/ai-catalog.json</code>, <code>/.well-known/poppy.json</code>, <code>/.well-known/agent-card.json</code>, <code>/.well-known/agent.json</code>, <code>/llms.txt</code>, <code>/agents.md</code>, the home page, at most two sitemap files (only when the home page links no product), and one product page. When the UCP profile names an MCP endpoint, we also send it one read-only <code>tools/list</code> request. That's usually 10 to 14 requests per website per week, and never more than 18.</li>
<li>robots.txt is read first and respected for every one of those URLs. If <code>/.well-known/ucp</code> is disallowed for us, we skip the website entirely.</li>
<li>At most 12 websites at a time for the UCP pass and 16 for the extra signals, always one request at a time per website, with a pause between requests (1 second for the extra signals), 10 to 12 second timeouts, HTTPS only. If a listed host is unreachable we try the same domain with or without <code>www.</code>. The extra signals run within a fixed weekly time budget; websites we don't reach in time show as "not checked".</li>
<li>Site owners: to have your site excluded, disallow <code>/</code> (or just the paths above) for <code>ShopBotIndexBot</code> in robots.txt, or email {MAILTO}.</li></ul>'''

SC=collections.Counter(s.get('status','error') for s in SITES)
meth=f'''<h1>Methodology</h1><p class="lede">Exactly what we check, how we check it, and what it does and doesn't mean. UCP profiles are our headline measure; four supporting signals are listed per store. Crawl date: {DAY}.</p>
<div class="box" id="meaning"><h2 style="margin-top:0">What this does and doesn't mean</h2><ul><li><b>UCP profile found</b>: the store publishes a Universal Commerce Protocol profile at <code>/.well-known/ucp</code>, the machine-readable profile AI shopping agents read, and lists what it supports (for example checkout). It doesn't guarantee that any particular assistant buys from it; that depends on the assistant.</li><li><b>No UCP profile found</b>: we found no UCP profile. It does <b>not</b> mean AI agents can't shop there. Agents can use a store through a normal web browser, and some agent shopping runs through channels we <a href="#cant-see">can't see from outside</a>, such as product feeds shared privately with AI assistants.</li><li><b>Couldn't check</b>: the site refused or failed our request, so we don't know either way.</li><li>UCP is our headline measure. We also list four supporting signals per store (<a href="#signals">section 1b</a>), but we don't test purchases, and we don't score or rank how well a store works with any assistant.</li></ul></div>
<h2>1. What we look for</h2><p>The UCP specification says platforms discover a business by fetching its business profile from <code>/.well-known/ucp</code> (<a href="{E(D["spec"])}">UCP specification overview</a>). The profile is JSON with a <code>ucp</code> object: protocol version, services, capabilities and payment handlers. We fetch that path on each website after reading <code>/robots.txt</code>. This is our headline measure. The other things we read are listed in <a href="#signals">section 1b</a> and <a href="#crawler">section 5</a>.</p>
{SIGMETH}
<h2>2. Who we track: three segments, side by side</h2><ul>{"".join(f"<li><b>{SEG[k]}</b> ({sum(1 for r in RET if r['segment']==k)}): {SEGDESC[k]}</li>" for k in SEG)}</ul>
<p>Sources: Wikipedia list pages (largest retail companies, department stores by country, supermarket chains, hypermarkets, online marketplaces) resolved to Wikidata for each retailer's own websites; Wikidata queries for retail chains and e-commerce companies; and public GitHub lists of Shopify stores (<a href="https://github.com/ihof/shopify">ihof/shopify</a>, <a href="https://github.com/dipinarora9/Shopify-Domains-Scraper">dipinarora9/Shopify-Domains-Scraper</a>, first 900 of <a href="https://github.com/TeamDukaan/performance">TeamDukaan/performance</a>). This is not a random sample of all stores; shares are shares of our list.</p>
<h2>3. One retailer, many country sites</h2><p>When a retailer's Wikidata entry lists several of its own websites (for example one per country), we check up to 8 of them and show them as children of one retailer. A retailer counts as publishing UCP if at least one of its sites does.</p>
<h2>4. "Couldn't check" is not "no"</h2><p>Many large retailers use bot protection that refuses automated requests. We never try to get around it. A retailer is <b>couldn't check</b> when every one of its sites refused us (401/403/429), timed out, failed TLS/DNS, or disallowed the path in robots.txt. These are shown separately and <b>excluded</b> from adoption rates. A retailer is <b>no UCP profile</b> only when at least one of its sites answered and had no profile.</p>
{CRAWLMETH}
<h2>6. Site-level results this crawl ({nsites} websites)</h2><ul>{"".join(f"<li>{E(SITEST.get(k,k))}: {v}</li>" for k,v in SC.most_common())}</ul>
<h2>7. Platform</h2><p>"Shopify" means the profile's endpoints or extensions reference Shopify. Anything else is shown as another platform. We can only identify a platform for stores that publish a profile.</p>
<h2 id="changes">8. Weekly changes</h2><p>Each crawl is saved with its date. The "What changed" page compares retailer-level status with the previous crawl: joined, left, couldn't check this time (not counted as leaving), capability changes, and newly tracked retailers (not counted as joining).</p>
<h2>9. AI assistants table</h2><p>Only company announcements and help-centre pages, linked per row. We don't test those integrations.</p>
<h2 id="contact">10. Add, remove or correct a store</h2><p>Run a store or retailer that should be added, removed or corrected, or think a result is wrong? Email {MAILTO} with the store's domain. We re-check it in the next weekly crawl and never change a result by hand.</p>'''
page('methodology.html',f'Methodology | {NAME}',meth)
page('about.html',f'About | {NAME}','''<h1>About</h1><p class="lede">ShopBot Index is the weekly index of what online stores tell AI shopping agents. Our headline measure is whether a store publishes a Universal Commerce Protocol (UCP) profile, the machine-readable profile AI shopping agents read. Alongside it we record four supporting signals: agent tools, AI rules in robots.txt, AI guidance files and product data. We cover Shopify stores, big retailers and other online stores.</p>
<p>It is run by Gus, an experienced enterprise software consultant, as an independent project. It is not affiliated with Google, Shopify, OpenAI, Microsoft, Perplexity, PayPal or any retailer listed.</p>
<p>All figures come from our own public crawl or from linked sources. Shopify trial links on this site (like the <a href="'''+E(AFF_URL)+'''" rel="sponsored noopener" target="_blank">Shopify free trial</a>) are affiliate links: '''+E(AFF_DISC)+''' That never changes a store's result.</p><p>Contact: <a href="mailto:hello@shopbotindex.com">hello@shopbotindex.com</a> (including stores that want to be added, removed or corrected; see the <a href="methodology.html#contact">methodology</a>).</p>'''+signup())
page('privacy.html',f'Privacy | {NAME}','''<h1>Privacy</h1><p class="lede">Short version: we only store what's needed to send you the weekly email.</p>
<h2>What we store when you subscribe</h2><ul><li>Your email address</li><li>When you signed up</li><li>A one-way hash of your IP address, kept only to limit spam signups (we never store the IP address itself)</li><li>If you use "Watch this store": which stores you watch</li></ul>
<h2>How we use it</h2><p>Only to send the ShopBot Index email (about one a week: which stores started or stopped publishing a UCP profile, and what else changed) and, if you watch a store, an email when that store starts or stops publishing a UCP profile. Every alert has a link to stop alerts for that store. We don't sell or share your data, and we don't add you to other lists.</p>
<h2>Where it's kept</h2><p>Subscriber data is stored with Supabase (EU region, Frankfurt), and emails will be sent with Resend. Both act as processors for us.</p>
<h2>Unsubscribe and deletion</h2><p>Every email will have a one-click unsubscribe link, and unsubscribing removes you from the list. To have your data deleted, or for any question, write to <a href="mailto:hello@shopbotindex.com">hello@shopbotindex.com</a>.</p>
<h2>Visit counts</h2><p>This site uses no cookies and no third-party analytics or tracking. To see which pages people read, each page sends one anonymous count to our own database (Supabase, EU): the page's path, the domain of the website that linked to it, and any utm or ref tags in the link. We store only daily totals of those. We don't store your IP address, any identifier, your browser or device, or anything else about you, so a visit can't be linked to you or to your other visits. If your browser sends Do Not Track or Global Privacy Control, nothing is sent.</p>
<h2>Spam protection</h2><p>Our signup forms have a hidden field that people never see or fill in. When it's filled, we drop the signup and add one to a daily count; nothing else about that request is stored.</p>
<h2>Affiliate links</h2><p>Shopify trial links on this site are affiliate links run through Impact; when you click one, Shopify and Impact may set their own cookies to attribute a trial. '''+E(AFF_DISC)+'''</p>
<h2>Our crawler</h2><p>ShopBot Index reads a short, fixed list of public files and pages on the stores it tracks (robots.txt, the UCP profile, a few agent-related files, the home page and one product page; full list in the methodology), respects robots.txt, and identifies itself honestly. See the <a href="methodology.html">methodology</a>.</p>
<p>Questions about your data: <a href="mailto:hello@shopbotindex.com">hello@shopbotindex.com</a>.</p><p class="muted">Last updated: October 2026.</p>''')
page('terms.html',f'Terms of use | {NAME}','''<h1>Terms of use</h1><p class="lede">Short version: link to us and quote our findings with credit; ask before copying the data in bulk.</p>
<h2>Copyright</h2><p>Copyright © 2026 ShopBot Index. All rights reserved. This covers the site's text, its data and the way the data is compiled and presented.</p>
<h2>What you may do</h2><ul><li>Link to any page on this site.</li><li>Quote individual findings, such as one store's result or a headline figure, with credit to ShopBot Index and a link to <a href="https://shopbotindex.com/">shopbotindex.com</a>.</li></ul>
<h2>What needs our written permission</h2><p>Copying, scraping or republishing the dataset or large parts of it, in any form. To ask, write to <a href="mailto:hello@shopbotindex.com">hello@shopbotindex.com</a>.</p>
<h2>About the data</h2><p>The data comes from automated crawls and is provided as is. It may contain errors. Each result is a snapshot of what a store's website published when we checked it. It says nothing about whether AI agents can buy at that store. If you think a result is wrong, see the <a href="methodology.html#contact">methodology</a> for how to ask us to re-check it.</p>
<h2>Names and trademarks</h2><p>Store names and trademarks belong to their owners. ShopBot Index is independent; not affiliated with Google, Shopify, OpenAI, Microsoft or any retailer listed.</p>
<p>Questions: <a href="mailto:hello@shopbotindex.com">hello@shopbotindex.com</a>.</p><p class="muted">Last updated: October 2026.</p>''')
# ---- "stop alerts" page for watch alerts (linked from each alert email; not in the sitemap) ----
UNWATCH_JS='''<script>(function(){var o=document.getElementById('uw'),t=new URLSearchParams(location.search).get('t')||'';if(!/^[0-9a-f-]{36}$/i.test(t)){o.textContent='This link is incomplete. Copy the whole link from the email, or write to hello@shopbotindex.com.';return}
fetch('''+json.dumps(FORM_ACTION)+''',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'unwatch',token:t})}).then(r=>r.json()).then(j=>{o.textContent=j.ok?(j.removed?"Done. You won't get alerts for this store any more. The Monday email is unchanged; it has its own unsubscribe link.":"These alerts were already stopped."):"Something went wrong. Please try again, or write to hello@shopbotindex.com."}).catch(()=>{o.textContent='Network error. Please try again.'})})();</script>'''
page('unwatch.html',f'Stop store alerts | {NAME}',f'<h1>Stop alerts for a store</h1><p class="lede" id="uw" aria-live="polite">Stopping the alerts…</p>{UNWATCH_JS}','Stop the email alerts for one store you watch on ShopBot Index. The Monday email is unchanged; it has its own unsubscribe link.',head='<meta name="robots" content="noindex">'); PAGES.remove('unwatch.html')
json.dump({r['id']:[SLUG[r['id']],r['name'],r['status']] for r in RET},open(os.path.join(DATA,'slugs-latest.json'),'w'),ensure_ascii=False,separators=(',',':'))  # for scripts/watch_alerts.py; not committed (.gitignore)
os.makedirs(os.path.join(DIST,'ucp'),exist_ok=True)
_V='2026-08-25'; _cap=lambda: [{'version':_V}]
json.dump({'ucp':{'version':_V,'services':{'dev.ucp.shopping':[{'version':_V,'spec':f'https://ucp.dev/{_V}/specification/overview','transport':'mcp','schema':f'https://ucp.dev/{_V}/services/shopping/mcp.openrpc.json'}]},
  'capabilities':{c:_cap() for c in ('dev.ucp.shopping.checkout','dev.ucp.shopping.cart','dev.ucp.shopping.order','dev.ucp.shopping.catalog.search','dev.ucp.shopping.catalog.lookup')},'payment_handlers':{}}},
  open(os.path.join(DIST,'ucp','agent-profile.json'),'w'),indent=1)
open(os.path.join(DIST,'CNAME'),'w').write(SITE.split('://',1)[1]+'\n')
open(os.path.join(DIST,'favicon.svg'),'w').write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#0f172a"/><path d="M14 20h6l5 22h20l5-16H23" fill="none" stroke="#22c55e" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="28" cy="50" r="4" fill="#22c55e"/><circle cx="43" cy="50" r="4" fill="#22c55e"/></svg>')
OG=os.path.join(ROOT,'assets','og.png')
if os.path.exists(OG): shutil.copy(OG,os.path.join(DIST,'og.png'))
OGS=os.path.join(ROOT,'assets','og-store.png')
if os.path.exists(OGS): shutil.copy(OGS,os.path.join(DIST,'og-store.png'))
import seo; seo.run(globals())  # summaries, FAQs, JSON-LD, descriptions, breadcrumbs, robots.txt (AI crawlers), sitemap.xml, llms.txt, IndexNow key (scripts/seo.py)
print('built',len(PAGES),'pages;',{k:segstats([r for r in RET if r['segment']==k]) for k in SEG},'nonshopify',len(NONSHOP),'big ucp',len(BIGU))
