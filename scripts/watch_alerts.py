#!/usr/bin/env python3
"""'Watch this store' alerts: after the weekly crawl + build, send the stores that started or stopped publishing a UCP profile
to the Supabase function sbi-watch-alerts, which emails the people watching them.

Started = data/changes-latest.json "joined"; stopped = "left" (profile no longer found). "Had a profile, now couldn't check"
and newly tracked stores never trigger an alert. Names and page slugs come from data/slugs-latest.json (written by build.py).

Usage:
  python3 scripts/watch_alerts.py                 dry run: prints who would get an alert (addresses masked), sends nothing
  python3 scripts/watch_alerts.py --send          sends, but only if Vault flag sbi_watch_alerts_enabled = 'true'
                                                  (otherwise the function answers as a dry run with enabled: false)
  python3 scripts/watch_alerts.py --send --only-to cstath@mail.grokbot.com    test send to the box-owned test inbox only
  python3 scripts/watch_alerts.py --changes FILE  use another changes file (same format as changes-latest.json)
The shared secret is read from /home/box/.private/sbi-alerts.json (never commit it). Stdlib only."""
import json, os, sys, argparse, urllib.request, urllib.error
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.environ.get('SBI_DATA_DIR') or os.path.join(ROOT,'data')
CRED=os.environ.get('SBI_ALERTS_CRED','/home/box/.private/sbi-alerts.json')

def build_changes(chg,slugs):
    out=[]
    for kind,key in (('started','joined'),('stopped','left')):
        for i in chg.get(key,[]):
            if i in slugs: out.append(dict(store_id=i,slug=slugs[i][0],name=slugs[i][1],change=kind))
    return out

def main(argv=None):
    a=argparse.ArgumentParser(); a.add_argument('--send',action='store_true'); a.add_argument('--only-to'); a.add_argument('--changes')
    a=a.parse_args(argv)
    cf=a.changes or os.path.join(DATA,'changes-latest.json')
    if not os.path.exists(cf): print('watch alerts: no changes file (first crawl?), nothing to do'); return 0
    chg=json.load(open(cf)); slugs=json.load(open(os.path.join(DATA,'slugs-latest.json')))
    changes=build_changes(chg,slugs)
    body=dict(crawl_date=chg['current'],mode='send' if a.send else 'dry',changes=changes)
    if a.only_to: body['only_to']=a.only_to
    if not changes: print(f'watch alerts {chg["current"]}: no store started or stopped publishing a UCP profile, nothing to send'); return 0
    cred=json.load(open(CRED))
    req=urllib.request.Request(cred['function_url'],data=json.dumps(body).encode(),method='POST',headers={'Content-Type':'application/json','x-sbi-token':cred['token']})
    try:
        with urllib.request.urlopen(req,timeout=120) as r: res=json.load(r)
    except urllib.error.HTTPError as e: print('watch alerts: HTTP',e.code,e.read()[:300].decode('utf-8','replace')); return 1
    print(f'watch alerts {chg["current"]}: {len(changes)} changed stores ->',json.dumps(res))
    return 0

if __name__=='__main__': sys.exit(main())
