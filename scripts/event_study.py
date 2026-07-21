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
                d = json.load(r)
            break
        except Exception as e:
            if attempt==2: raise
            time.sleep(2)
    res = d["chart"]["result"][0]
    ts = res["timestamp"]
    closes = res["indicators"]["quote"][0]["close"]
    out = []
    for t,c in zip(ts,closes):
        if c is None: continue
        day = datetime.datetime.fromtimestamp(t, tz=datetime.timezone.utc).strftime("%Y-%m-%d")
        out.append((day, round(c,2)))
    return out

# (label, ticker, post_date, window_start, window_end, tier)
events = [
    ("US Steel",      "X",    "2025-01-06", (2025,1,2),  (2025,1,21), "core"),
    ("Tesla (Musk video)","TSLA","2025-03-11",(2025,3,6),(2025,3,25),"core"),
    ("Apple",         "AAPL", "2025-03-12", (2025,3,7),  (2025,3,26), "core"),
    ("GE Aerospace",  "GE",   "2025-03-12", (2025,3,7),  (2025,3,26), "core"),
    ("Eli Lilly",     "LLY",  "2025-03-12", (2025,3,7),  (2025,3,26), "core"),
    ("Nvidia",        "NVDA", "2025-04-15", (2025,4,10), (2025,4,30), "core"),
    ("Tesla (THRIVE)","TSLA", "2025-07-24", (2025,7,21), (2025,8,8),  "core"),
    ("American Eagle","AEO",  "2025-08-04", (2025,7,30), (2025,8,18), "core"),
    # borderline
    ("RTX (F-22)",    "RTX",  "2025-08-24", (2025,8,20), (2025,9,8),  "border"),
    ("Boeing (F-22)", "BA",   "2025-08-24", (2025,8,20), (2025,9,8),  "border"),
    ("Northrop (F-22)","NOC", "2025-08-24", (2025,8,20), (2025,9,8),  "border"),
    ("Palantir",      "PLTR", "2026-04-10", (2026,4,6),  (2026,4,27), "border"),
]

def analyze(label, ticker, post_date, ws, we, tier):
    try:
        series = fetch(ticker, ws, we)
    except Exception as e:
        return {"label":label,"ticker":ticker,"error":f"fetch failed: {e}","tier":tier}
    if not series:
        return {"label":label,"ticker":ticker,"error":"no data","tier":tier}
    days = [d for d,_ in series]
    price = dict(series)
    # entry = first trading day >= post_date
    entry_idx = None
    for i,(d,c) in enumerate(series):
        if d >= post_date:
            entry_idx = i; break
    if entry_idx is None:
        return {"label":label,"ticker":ticker,"error":"post_date beyond series","tier":tier,"series":series}
    entry_day, entry_px = series[entry_idx]
    nd = series[entry_idx+1] if entry_idx+1 < len(series) else None
    wk = series[entry_idx+5] if entry_idx+5 < len(series) else None
    r1 = round((nd[1]/entry_px-1)*100,2) if nd else None
    r5 = round((wk[1]/entry_px-1)*100,2) if wk else None
    return {"label":label,"ticker":ticker,"tier":tier,"post_date":post_date,
            "entry_day":entry_day,"entry_px":entry_px,
            "d1_day":nd[0] if nd else None,"d1_px":nd[1] if nd else None,"r1":r1,
            "d5_day":wk[0] if wk else None,"d5_px":wk[1] if wk else None,"r5":r5,
            "series":series}

results=[]
for e in events:
    r=analyze(*e)
    results.append(r)
    print("="*70)
    print(f"{r['label']} [{r['ticker']}] tier={r['tier']}")
    if r.get("error"):
        print("  ERROR:", r["error"]); continue
    print(f"  post={r['post_date']} entry={r['entry_day']} @ {r['entry_px']}")
    print(f"  +1d ({r['d1_day']}): {r['d1_px']}  => {r['r1']}%")
    print(f"  +5d ({r['d5_day']}): {r['d5_px']}  => {r['r5']}%")
    print("  closes used:", r["series"])

# aggregates
def agg(rows, name):
    r1s=[r["r1"] for r in rows if r.get("r1") is not None]
    r5s=[r["r5"] for r in rows if r.get("r5") is not None]
    if not r1s:
        print(f"\n[{name}] no data"); return
    print(f"\n===== AGGREGATE: {name} (n={len(rows)}) =====")
    print(f"  avg +1d: {sum(r1s)/len(r1s):.2f}%   win rate: {sum(1 for x in r1s if x>0)}/{len(r1s)} = {100*sum(1 for x in r1s if x>0)/len(r1s):.0f}%")
    print(f"  avg +1wk: {sum(r5s)/len(r5s):.2f}%  win rate: {sum(1 for x in r5s if x>0)}/{len(r5s)} = {100*sum(1 for x in r5s if x>0)/len(r5s):.0f}%")
    b1=max(rows,key=lambda r:r['r1'] if r.get('r1') is not None else -999)
    w1=min(rows,key=lambda r:r['r1'] if r.get('r1') is not None else 999)
    b5=max(rows,key=lambda r:r['r5'] if r.get('r5') is not None else -999)
    w5=min(rows,key=lambda r:r['r5'] if r.get('r5') is not None else 999)
    print(f"  best +1d: {b1['label']} {b1['r1']}%   worst +1d: {w1['label']} {w1['r1']}%")
    print(f"  best +1wk: {b5['label']} {b5['r5']}%  worst +1wk: {w5['label']} {w5['r5']}%")

core=[r for r in results if r.get("tier")=="core" and not r.get("error")]
allv=[r for r in results if not r.get("error")]
agg(core,"CLEAN CORE (named-company praise, Truth Social)")
agg(allv,"CORE + BORDERLINE (incl F-22 trio + Palantir)")
