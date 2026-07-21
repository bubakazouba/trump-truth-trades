import urllib.request, json, datetime, ssl, time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# (ticker, post_date, entry_date, soft_flag, note)
JOBS = [
    ("AAPL","2025-03-12","2025-03-12",False,"Mar12 trio: US-investment praise"),
    ("GE",  "2025-03-12","2025-03-12",False,"Mar12 trio: GE Aerospace praise"),
    ("LLY", "2025-03-12","2025-03-12",False,"Mar12 trio: Eli Lilly praise"),
    ("NVDA","2025-04-15","2025-04-15",False,"permits expedited / AI supercomputers"),
    ("TSLA","2025-07-24","2025-07-24",True, "SOFT: 'I want Elon to THRIVE' defense post"),
    ("AEO", "2025-08-04","2025-08-04",False,"jeans flying off shelves (Sydney Sweeney ad)"),
    ("BA",  "2025-08-24","2025-08-25",True, "SOFT: F-22 'greatest jet' video (Sun->Mon entry)"),
    ("RTX", "2025-08-24","2025-08-25",True, "SOFT: F-22 video (Sun->Mon entry)"),
    ("NOC", "2025-08-24","2025-08-25",True, "SOFT: F-22 video (Sun->Mon entry)"),
    ("PLTR","2026-04-10","2026-04-10",False,"'great war fighting capabilities'"),
]

def fetch(ticker, entry_date):
    d = datetime.date.fromisoformat(entry_date)
    p1 = int(time.mktime((d - datetime.timedelta(days=6)).timetuple())) - 86400
    p2 = int(time.mktime((d + datetime.timedelta(days=20)).timetuple())) + 86400
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1={p1}&period2={p2}&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    data = json.load(urllib.request.urlopen(req, context=ctx, timeout=30))
    r = data["chart"]["result"][0]
    ts = r["timestamp"]
    closes = r["indicators"]["quote"][0]["close"]
    rows = []
    for t,c in zip(ts,closes):
        if c is None: continue
        dt = datetime.datetime.utcfromtimestamp(t).date().isoformat()
        rows.append((dt, round(c,4)))
    return rows

results=[]
for ticker,post,entry,soft,note in JOBS:
    rows = fetch(ticker, entry)
    dates = [r[0] for r in rows]
    if entry not in dates:
        print(f"!!! {ticker}: entry {entry} not a trading day in data. Dates around: {dates[:8]}")
        continue
    ei = dates.index(entry)
    if ei+5 >= len(rows):
        print(f"!!! {ticker}: not enough forward days after {entry}")
        continue
    entry_px = rows[ei][1]
    d1_px    = rows[ei+1][1]
    d5_px    = rows[ei+5][1]
    r1  = (d1_px/entry_px - 1)*100
    r5  = (d5_px/entry_px - 1)*100
    print(f"===== {ticker}  post={post} entry={entry}  [{'SOFT' if soft else 'core'}] {note}")
    for j in range(ei, ei+6):
        tag = ""
        if j==ei: tag=" <- ENTRY"
        elif j==ei+1: tag=" <- +1d"
        elif j==ei+5: tag=" <- +5d"
        print(f"    {rows[j][0]}  close={rows[j][1]}{tag}")
    print(f"    +1d = {r1:+.2f}%   +1wk = {r5:+.2f}%")
    results.append((post,ticker,entry,r1,r5,soft))

print("\n\n########## SUMMARY TABLE ##########")
print(f"{'date':11} {'tkr':5} {'+1d%':>8} {'+1wk%':>8}  soft")
for post,ticker,entry,r1,r5,soft in results:
    print(f"{post:11} {ticker:5} {r1:>+8.2f} {r5:>+8.2f}  {'SOFT' if soft else ''}")

import statistics as st
def agg(rows,label):
    if not rows: 
        print(f"\n[{label}] no rows"); return
    r1=[x[3] for x in rows]; r5=[x[4] for x in rows]
    n=len(rows)
    print(f"\n[{label}] n={n}")
    print(f"  avg +1d  = {st.mean(r1):+.2f}%   win {sum(1 for v in r1 if v>0)}/{n} = {100*sum(1 for v in r1 if v>0)/n:.0f}%")
    print(f"  avg +1wk = {st.mean(r5):+.2f}%   win {sum(1 for v in r5 if v>0)}/{n} = {100*sum(1 for v in r5 if v>0)/n:.0f}%")
    b1=max(rows,key=lambda x:x[3]); w1=min(rows,key=lambda x:x[3])
    b5=max(rows,key=lambda x:x[4]); w5=min(rows,key=lambda x:x[4])
    print(f"  best +1d  {b1[1]} {b1[3]:+.2f}% ; worst +1d {w1[1]} {w1[3]:+.2f}%")
    print(f"  best +1wk {b5[1]} {b5[4]:+.2f}% ; worst +1wk {w5[1]} {w5[4]:+.2f}%")

agg(results,"ALL ticker-observations")
core=[x for x in results if not x[5]]
agg(core,"CORE only (drop soft: TSLA,BA,RTX,NOC)")

# Event-level: collapse Mar12 trio and Aug25 F-22 trio into event averages
ev={}
for post,ticker,entry,r1,r5,soft in results:
    key = "MAR12" if entry=="2025-03-12" else ("F22" if entry=="2025-08-25" else ticker)
    ev.setdefault(key,[]).append((r1,r5))
print("\n[EVENT-LEVEL] collapse Mar12 trio + F-22 trio to their means")
erows=[]
for k,v in ev.items():
    m1=st.mean([a for a,b in v]); m5=st.mean([b for a,b in v])
    print(f"  {k:6} n_tk={len(v)}  +1d {m1:+.2f}%  +1wk {m5:+.2f}%")
    erows.append((k,k,k,m1,m5,False))
agg(erows,"EVENT-LEVEL (independent posts)")
