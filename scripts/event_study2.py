import urllib.request, json, datetime, time

def fetch(ticker, start, end):
    p1 = int(datetime.datetime(*start, tzinfo=datetime.timezone.utc).timestamp())
    p2 = int(datetime.datetime(*end, tzinfo=datetime.timezone.utc).timestamp())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
           f"?period1={p1}&period2={p2}&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.load(r); break
        except Exception as e:
            if attempt==2: raise
            time.sleep(2)
    res = d["chart"]["result"][0]
    ts, closes = res["timestamp"], res["indicators"]["quote"][0]["close"]
    out=[]
    for t,c in zip(ts,closes):
        if c is None: continue
        day=datetime.datetime.fromtimestamp(t,tz=datetime.timezone.utc).strftime("%Y-%m-%d")
        out.append((day,round(c,2)))
    return out

# (label, ticker, post_date, post_time_ET "HH:MM", window_start, window_end, tier, note)
events = [
 ("US Steel","X","2025-01-06","08:29",(2025,1,2),(2025,1,21),"core","delisted Jun2025 (Nippon) - no price"),
 ("Tesla (buy-a-Tesla)","TSLA","2025-03-11","00:14",(2025,3,6),(2025,3,25),"core",""),
 ("Apple","AAPL","2025-03-12","16:23",(2025,3,7),(2025,3,27),"core","after-close post"),
 ("GE Aerospace","GE","2025-03-12","16:23",(2025,3,7),(2025,3,27),"core","after-close post"),
 ("Eli Lilly","LLY","2025-03-12","16:23",(2025,3,7),(2025,3,27),"core","after-close post"),
 ("Nvidia","NVDA","2025-04-15","07:36",(2025,4,10),(2025,4,30),"core","pre-market post"),
 ("Tesla (THRIVE)","TSLA","2025-07-24","09:34",(2025,7,21),(2025,8,8),"core",""),
 ("American Eagle","AEO","2025-08-04","10:25",(2025,7,30),(2025,8,18),"core",""),
 ("RTX (F-22)","RTX","2025-08-23","22:44",(2025,8,20),(2025,9,8),"border","Sat night; company unnamed"),
 ("Boeing (F-22)","BA","2025-08-23","22:44",(2025,8,20),(2025,9,8),"border","Sat night; company unnamed"),
 ("Northrop (F-22)","NOC","2025-08-23","22:44",(2025,8,20),(2025,9,8),"border","Sat night; company unnamed"),
 ("Palantir","PLTR","2026-04-10","10:32",(2026,4,6),(2026,4,27),"border","2026, outside CNN 2025 window"),
 ("Dell","DELL","2025-12-02","08:55",(2025,11,26),(2025,12,12),"border","'I LOVE DELL' re: family donation, not stock/product"),
]

def entry_index(series, post_date, hh):
    days=[d for d,_ in series]
    same = post_date in days
    if same and hh < 16:            # trading day + before close -> same-day close
        return days.index(post_date), "same-day"
    # else next trading day strictly after post_date
    for i,(d,_) in enumerate(series):
        if d > post_date:
            return i, "next-day"
    return None, None

rows=[]
for label,tk,pd,pt,ws,we,tier,note in events:
    hh=int(pt.split(":")[0])
    try:
        series=fetch(tk,ws,we)
    except Exception as e:
        rows.append(dict(label=label,tk=tk,tier=tier,pd=pd,pt=pt,note=note,err=f"fetch fail: {e}")); continue
    if not series:
        rows.append(dict(label=label,tk=tk,tier=tier,pd=pd,pt=pt,note=note,err="no price data (delisted)")); continue
    ei,mode=entry_index(series,pd,hh)
    if ei is None:
        rows.append(dict(label=label,tk=tk,tier=tier,pd=pd,pt=pt,note=note,err="no entry day")); continue
    ed,ep=series[ei]
    nd=series[ei+1] if ei+1<len(series) else None
    wk=series[ei+5] if ei+5<len(series) else None
    r1=round((nd[1]/ep-1)*100,2) if nd else None
    r5=round((wk[1]/ep-1)*100,2) if wk else None
    rows.append(dict(label=label,tk=tk,tier=tier,pd=pd,pt=pt,note=note,mode=mode,
                     ed=ed,ep=ep,d1=nd,r1=r1,d5=wk,r5=r5,series=series))

for r in rows:
    print("="*72)
    print(f"{r['label']} [{r['tk']}] {r['pd']} {r['pt']} ET  tier={r['tier']}  {r['note']}")
    if r.get("err"): print("  ->", r["err"]); continue
    print(f"  entry={r['ed']} ({r['mode']}) @ {r['ep']}")
    print(f"  +1d {r['d1'][0] if r['d1'] else '-'}: {r['d1'][1] if r['d1'] else '-'} => {r['r1']}%")
    print(f"  +1wk {r['d5'][0] if r['d5'] else '-'}: {r['d5'][1] if r['d5'] else '-'} => {r['r5']}%")

def agg(name,sel):
    r1=[r['r1'] for r in sel if r.get('r1') is not None]
    r5=[r['r5'] for r in sel if r.get('r5') is not None]
    if not r1: print(f"\n[{name}] no data"); return
    w1=sum(1 for x in r1 if x>0); w5=sum(1 for x in r5 if x>0)
    print(f"\n##### {name}  (n={len(r1)} priced) #####")
    print(f"  avg +1d  = {sum(r1)/len(r1):+.2f}%   win {w1}/{len(r1)} = {100*w1/len(r1):.0f}%")
    print(f"  avg +1wk = {sum(r5)/len(r5):+.2f}%   win {w5}/{len(r5)} = {100*w5/len(r5):.0f}%")
    b1=max(sel,key=lambda r:r.get('r1') if r.get('r1') is not None else -1e9)
    wo1=min(sel,key=lambda r:r.get('r1') if r.get('r1') is not None else 1e9)
    b5=max(sel,key=lambda r:r.get('r5') if r.get('r5') is not None else -1e9)
    wo5=min(sel,key=lambda r:r.get('r5') if r.get('r5') is not None else 1e9)
    print(f"  best +1d {b1['label']} {b1['r1']}% | worst +1d {wo1['label']} {wo1['r1']}%")
    print(f"  best +1wk {b5['label']} {b5['r5']}% | worst +1wk {wo5['label']} {wo5['r5']}%")

priced=[r for r in rows if r.get('r1') is not None]
core=[r for r in priced if r['tier']=='core']
agg("CLEAN CORE (named-company TS praise)", core)
agg("COMPLETE SET (no exclusions, all priced)", priced)
print("\nDROPPED (no price):", [r['label'] for r in rows if r.get('err')])
