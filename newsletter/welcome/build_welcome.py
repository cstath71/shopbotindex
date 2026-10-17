# Welcome email for new ShopBot Index subscribers (Resend template "ShopBot Index welcome", alias sbi-welcome).
# Builds welcome.html / welcome.txt / send-settings.json. Nothing here sends.
import html, json
E=html.escape
SITE='https://shopbotindex.com'
FROM='ShopBot Index <hello@shopbotindex.com>'; REPLY_TO='hello@shopbotindex.com'
SUBJECT='Welcome to ShopBot Index'
PRE="One short email a week: which stores started or stopped publishing a UCP profile for AI shopping agents, and what changed."
P1="Thanks for subscribing to ShopBot Index."
P2="Every Monday the index checks each tracked store for a UCP business profile, the /.well-known/ucp file that is the official machine-readable profile AI shopping agents read. After each crawl you'll get one short, free email: which stores started publishing a UCP profile, which stopped, and what else changed that week."
P3="Until the next issue, here's where to look:"
LINKS=[("The index",SITE+"/","Which stores publish a UCP profile, across Shopify stores, big retailers and other stores."),
       ("What changed",SITE+"/changes.html","Joined, left and other changes compared with the previous crawl."),
       ("Methodology",SITE+"/methodology.html","Exactly how each store is checked and how the numbers are produced.")]
P4="Questions, or a store you'd like checked? Just reply to this email. It goes to hello@shopbotindex.com."
a=lambda u,t,c='#1f5fa8': f'<a href="{E(u)}" style="color:{c};text-decoration:underline">{t}</a>'
F='font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif'
p=lambda s,extra='': f'<p style="{F};font-size:15px;line-height:24px;color:#14202b;margin:0 0 12px 0{extra}">{s}</p>'
h=f'''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta http-equiv="X-UA-Compatible" content="IE=edge"><title>{E(SUBJECT)}</title></head>
<body style="margin:0;padding:0;background-color:#f2f4f7">
<div style="display:none;max-height:0;overflow:hidden">{E(PRE)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#f2f4f7" style="background-color:#f2f4f7"><tr><td align="center" style="padding-top:24px;padding-bottom:24px;padding-left:12px;padding-right:12px">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" bgcolor="#ffffff" style="max-width:600px;width:100%;background-color:#ffffff">
<tr><td bgcolor="#14202b" style="background-color:#14202b;padding-top:18px;padding-bottom:18px;padding-left:28px;padding-right:28px"><img src="{SITE}/logo-96.png" width="40" height="40" border="0" alt="ShopBot Index logo" style="display:block;border:0;width:40px;height:40px;margin:0 0 8px 0"><p style="{F};font-size:20px;line-height:26px;font-weight:700;color:#ffffff;margin:0">ShopBot Index</p><p style="{F};font-size:13px;line-height:18px;color:#d6dee6;margin:2px 0 0 0">Which online stores publish a UCP profile for AI shopping agents</p></td></tr>
<tr><td style="padding-top:28px;padding-bottom:4px;padding-left:28px;padding-right:28px">
<h1 style="{F};font-size:24px;line-height:30px;color:#14202b;margin:0 0 12px 0">{E(SUBJECT)}</h1>
{p(E(P1))}{p(E(P2))}{p(E(P3),';margin-bottom:4px')}</td></tr>
<tr><td style="padding-left:28px;padding-right:28px">'''+''.join(f'<p style="{F};font-size:15px;line-height:22px;color:#14202b;margin:12px 0;border-left:3px solid #1f5fa8;padding-left:12px"><b>{a(u,E(t),"#14202b")}</b><br><span style="{F};color:#5b6875;font-size:14px;line-height:20px">{E(d)}</span></p>' for t,u,d in LINKS)+f'''</td></tr>
<tr><td style="padding-top:12px;padding-bottom:24px;padding-left:28px;padding-right:28px">{p(E(P4))}<p style="{F};font-size:15px;line-height:22px;color:#14202b;margin:0">Gus<br><span style="color:#5b6875">ShopBot Index</span></p></td></tr>
<tr><td bgcolor="#f6f7f9" style="background-color:#f6f7f9;padding-top:18px;padding-bottom:18px;padding-left:28px;padding-right:28px"><p style="{F};font-size:12px;line-height:19px;color:#5b6875;margin:0">You're getting this because you subscribed at {a(SITE,"shopbotindex.com","#5b6875")}. {a("{{{RESEND_UNSUBSCRIBE_URL}}}","Unsubscribe","#5b6875")} · {a(SITE+"/privacy.html","Privacy","#5b6875")}</p></td></tr>
</table></td></tr></table></body></html>'''
open('welcome.html','w').write(h)
t=[SUBJECT,"",P1,"",P2,"",P3,""]
for ti,u,d in LINKS: t+=[f"- {ti}: {u}",f"  {d}",""]
t+=[P4,"","Gus","ShopBot Index","","---","You're getting this because you subscribed at shopbotindex.com. Unsubscribe: {{{RESEND_UNSUBSCRIBE_URL}}} · Privacy: "+SITE+"/privacy.html"]
open('welcome.txt','w').write('\n'.join(t)+'\n')
json.dump({'from':FROM,'reply_to':REPLY_TO,'subject':SUBJECT,'preheader':PRE,'event':'sbi.subscribed','template_alias':'sbi-welcome'},open('send-settings.json','w'),indent=2)
