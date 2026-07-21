import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

POSTS = [
    ("TSLA", "2025-07-24", (9, 34)),
    ("AEO",  "2025-08-04", (10, 25)),
    ("PLTR", "2026-04-10", (10, 32)),
]

def load(t, d):
    res = json.load(open(f"poly_{t}_{d}.json"))["results"]
    bars = {}
    for r in res:
        dt = datetime.fromtimestamp(r["t"]/1000, tz=ET)
        bars[dt.replace(second=0, microsecond=0)] = r
    return bars

def bar_at_or_after(bars, target, maxfwd=15):
    """Return (dt, bar, note). target is a datetime. Look forward up to maxfwd min."""
    for i in range(maxfwd+1):
        cand = target + timedelta(minutes=i)
        if cand in bars:
            note = "" if i == 0 else f"(no {target.strftime('%H:%M')} bar; used {cand.strftime('%H:%M')}, +{i}m)"
            return cand, bars[cand], note
    return None, None, "MISSING"

def last_regular_close(bars, day):
    """4pm close = close of the last regular-session bar (<=15:59 ET)."""
    end = datetime.combine(day, datetime.min.time(), tzinfo=ET).replace(hour=15, minute=59)
    for i in range(0, 30):
        cand = end - timedelta(minutes=i)
        if cand in bars:
            return cand, bars[cand]
    return None, None

results = []
for t, d, (hh, mm) in POSTS:
    bars = load(t, d)
    day = datetime.strptime(d, "%Y-%m-%d").date()
    post = datetime.combine(day, datetime.min.time(), tzinfo=ET).replace(hour=hh, minute=mm)

    a_dt, a_bar, a_note = bar_at_or_after(bars, post)
    entry = a_bar["c"]

    offsets = {"+1m": 1, "+5m": 5, "+15m": 15, "+30m": 30}
    pts = {}
    for label, om in offsets.items():
        tgt = a_dt + timedelta(minutes=om)
        dt, bar, note = bar_at_or_after(bars, tgt, maxfwd=5)
        pts[label] = (dt, bar["c"] if bar else None, note)

    c_dt, c_bar = last_regular_close(bars, day)
    close = c_bar["c"]

    full_move = close - entry  # post-minute -> 4pm close
    row = {
        "ticker": t, "date": d, "post": f"{hh:02d}:{mm:02d}",
        "anchor_time": a_dt.strftime("%H:%M"), "anchor_note": a_note,
        "entry": entry, "close": close, "close_time": c_dt.strftime("%H:%M"),
        "full_move_pct": full_move/entry*100,
        "full_move_abs": full_move,
        "windows": {}, "fraction": {},
    }
    for label, (dt, px, note) in pts.items():
        if px is None:
            row["windows"][label] = None; row["fraction"][label] = None; continue
        move = px - entry
        pct = move/entry*100
        frac = (move/full_move*100) if full_move != 0 else float('nan')
        row["windows"][label] = {"time": dt.strftime("%H:%M"), "px": px, "pct": pct, "note": note}
        row["fraction"][label] = frac
    results.append(row)

# ---- print per-post ----
for r in results:
    print("="*78)
    print(f"{r['ticker']}  {r['date']}  post {r['post']} ET   anchor bar {r['anchor_time']} {r['anchor_note']}")
    print(f"  entry (post-min close) = ${r['entry']:.2f}")
    for label in ["+1m","+5m","+15m","+30m"]:
        w = r["windows"][label]; f = r["fraction"][label]
        if w is None: print(f"  {label:4s}: MISSING"); continue
        print(f"  {label:4s} {w['time']}: ${w['px']:.2f}  move {w['pct']:+.3f}%  "
              f"= {f:+.0f}% of full intraday move {w['note']}")
    print(f"  close {r['close_time']}: ${r['close']:.2f}  full move {r['full_move_pct']:+.3f}% (${r['full_move_abs']:+.2f})")

# ---- aggregate ----
print("\n"+"="*78)
print("AGGREGATE across 3 posts (mean of fraction-of-full-move captured):")
for label in ["+1m","+5m","+15m","+30m"]:
    fr = [r["fraction"][label] for r in results if r["fraction"][label] is not None]
    pc = [r["windows"][label]["pct"] for r in results if r["windows"][label] is not None]
    print(f"  {label:4s}: mean {sum(fr)/len(fr):+.0f}% of full move captured   "
          f"(per-post: {', '.join(f'{x:+.0f}%' for x in fr)})   raw move mean {sum(pc)/len(pc):+.3f}%")
