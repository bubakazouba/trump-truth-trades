"""Retry pass: re-attempt ONLY ticker-days that failed for reasons other than
NOT_AUTHORIZED (rate limits, transient errors). Never re-burns quota on
out-of-window days that Polygon has definitively refused.
"""
import json, os, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
KEY = open(os.path.join(HERE, "polygon_key.txt")).read().strip()
log = json.load(open(os.path.join(HERE, "speed_fetch_log.json")))

todo = []
for x in log:
    if x["status"] in ("ok", "cached"):
        continue
    err = (x.get("error") or "")
    if "doesn't include this data timeframe" in err:   # definitive: out of free window
        continue
    if os.path.exists(os.path.join(HERE, f"poly_{x['ticker']}_{x['date']}.json")):
        continue
    todo.append((x["ticker"], x["date"]))

print(f"retrying {len(todo)} transient failures", flush=True)
fixed = []
for i, (tk, d) in enumerate(todo, 1):
    url = (f"https://api.polygon.io/v2/aggs/ticker/{tk}/range/1/minute/{d}/{d}"
           f"?adjusted=true&sort=asc&limit=50000&apiKey={KEY}")
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            j = json.loads(resp.read().decode())
        if j.get("status") in ("OK", "DELAYED") and j.get("results"):
            json.dump(j, open(os.path.join(HERE, f"poly_{tk}_{d}.json"), "w"))
            print(f"[{i}/{len(todo)}] {tk} {d} ok bars={len(j['results'])}", flush=True)
            fixed.append((tk, d))
        else:
            print(f"[{i}/{len(todo)}] {tk} {d} still-failing: {j.get('status')} {j.get('message') or j.get('error')}", flush=True)
    except Exception as e:
        print(f"[{i}/{len(todo)}] {tk} {d} exception {repr(e)[:160]}", flush=True)
    time.sleep(16)
print(f"RETRY DONE. recovered {len(fixed)}", flush=True)
