"""Intraday reaction-speed analysis. REAL Polygon 1-min bars only.

Per post:
  reference = close of the LAST available bar strictly BEFORE the post minute
              (must be a regular-hours bar, >= 9:30, same session)
  anchor    = the bar containing the post minute, or the nearest SUBSEQUENT bar
  offset N  = cumulative % move vs reference at the nearest available bar at/before
              minute (anchor_minute + N); signed in the direction of the post.
Posts at 9:30 with no prior in-session bar are DROPPED (counted + reported):
we never reach into thin pre-market bars for a reference.
"""
import json, os, statistics
from datetime import datetime
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
ET = ZoneInfo("America/New_York")
OPEN_M, CLOSE_M = 9 * 60 + 30, 16 * 60
MAXOFF = 60


def in_hours_posts():
    rows = [json.loads(l) for l in open(os.path.join(HERE, "classified.jsonl"), encoding="utf-8")]
    out = []
    for r in rows:
        if r["sentiment"] not in ("PRAISE", "ATTACK"):
            continue
        t = r.get("ticker")
        if not t or t == "X":
            continue
        dt = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")).astimezone(ET)
        if dt.weekday() >= 5:
            continue
        m = dt.hour * 60 + dt.minute
        if not (OPEN_M <= m < CLOSE_M):
            continue
        r["_dt"], r["_min"] = dt, m
        out.append(r)
    return out


def load_bars(tk, d):
    """-> {minute_of_day: close} for regular-hours bars only."""
    p = os.path.join(HERE, f"poly_{tk}_{d}.json")
    if not os.path.exists(p):
        return None
    try:
        j = json.load(open(p))
    except Exception:
        return None
    res = j.get("results")
    if not res:
        return None
    bars = {}
    for b in res:
        dt = datetime.fromtimestamp(b["t"] / 1000, tz=ZoneInfo("UTC")).astimezone(ET)
        if dt.date().isoformat() != d:
            continue
        m = dt.hour * 60 + dt.minute
        if OPEN_M <= m < CLOSE_M:
            bars[m] = b["c"]
    return bars or None


def curve_for(post, bars):
    pm = post["_min"]
    prior = [m for m in bars if m < pm]
    if not prior:
        return None, "no_prior_bar"          # 9:30 post / no in-session reference
    ref = bars[max(prior)]
    if not ref:
        return None, "bad_ref"
    at_or_after = [m for m in bars if m >= pm]
    if not at_or_after:
        return None, "no_anchor_bar"
    anchor = min(at_or_after)                 # exact post minute, else next available
    sign = 1.0 if post["sentiment"] == "PRAISE" else -1.0
    avail = sorted(bars)
    curve = {}
    for off in range(0, MAXOFF + 1):
        target = anchor + off
        if target >= CLOSE_M:
            break
        cands = [m for m in avail if m <= target and m >= anchor]
        if not cands:
            continue
        px = bars[max(cands)]
        curve[off] = sign * (px / ref - 1.0) * 100.0
    if 0 not in curve or 30 not in curve:
        return None, "incomplete_window"      # needs a full 0..30 window
    return {"ref": ref, "anchor": anchor, "curve": curve}, "ok"


def main():
    posts = in_hours_posts()
    rec, drops = [], {}
    for p in posts:
        d = p["_dt"].date().isoformat()
        bars = load_bars(p["ticker"], d)
        if bars is None:
            drops["no_data"] = drops.get("no_data", 0) + 1
            continue
        r, why = curve_for(p, bars)
        if r is None:
            drops[why] = drops.get(why, 0) + 1
            continue
        rec.append({"id": p["id"], "ticker": p["ticker"], "company": p["company"],
                    "date": d, "et": p["_dt"].strftime("%H:%M"),
                    "sentiment": p["sentiment"], "curve": r["curve"]})

    n = len(rec)
    out = {"n_in_hours": len(posts), "n_analyzed": n, "drops": drops}
    if not n:
        json.dump(out, open(os.path.join(HERE, "speed_results.json"), "w"), indent=1)
        print(json.dumps(out, indent=1)); return

    # mean / median curve by offset
    curve_stats = []
    for off in range(0, 31):
        v = [r["curve"][off] for r in rec if off in r["curve"]]
        if not v:
            continue
        v_s = sorted(v)
        curve_stats.append({
            "off": off, "n": len(v),
            "mean": statistics.fmean(v), "median": statistics.median(v),
            "p25": v_s[int(.25 * (len(v_s) - 1))], "p75": v_s[int(.75 * (len(v_s) - 1))],
        })
    out["curve"] = curve_stats

    # first-minute distribution (offset 0 = the bar containing the post)
    first = [r["curve"][0] for r in rec]
    out["first_minute"] = {
        "n": len(first), "mean": statistics.fmean(first), "median": statistics.median(first),
        "stdev": statistics.stdev(first) if len(first) > 1 else 0.0,
        "min": min(first), "max": max(first),
        "pos_share": 100.0 * sum(1 for x in first if x > 0) / len(first),
        "values": first,
    }
    # +1 min too
    f1 = [r["curve"][1] for r in rec if 1 in r["curve"]]
    out["plus1"] = {"n": len(f1), "mean": statistics.fmean(f1), "median": statistics.median(f1),
                    "pos_share": 100.0 * sum(1 for x in f1 if x > 0) / len(f1)}

    # share of the +30 move captured at each horizon (ratio of MEANS, and per-post median ratio)
    m30 = statistics.fmean([r["curve"][30] for r in rec])
    cap = {}
    for h in (0, 1, 5, 15, 30):
        vals = [r["curve"][h] for r in rec if h in r["curve"]]
        mh = statistics.fmean(vals)
        cap[h] = {"n": len(vals), "mean_move": mh,
                  "share_of_30_mean": (100.0 * mh / m30) if m30 else None}
    out["capture"] = cap
    out["mean_30"] = m30

    # hit rate: moved in the post's direction at all
    out["hit_rate"] = {str(h): {"n": sum(1 for r in rec if h in r["curve"]),
                                "pct": 100.0 * sum(1 for r in rec if r["curve"].get(h, 0) > 0)
                                       / max(1, sum(1 for r in rec if h in r["curve"]))}
                       for h in (0, 1, 5, 15, 30)}
    # concentration
    tc = {}
    for r in rec:
        tc[r["ticker"]] = tc.get(r["ticker"], 0) + 1
    out["by_ticker"] = sorted(tc.items(), key=lambda x: -x[1])
    out["by_sentiment"] = {s: sum(1 for r in rec if r["sentiment"] == s) for s in ("PRAISE", "ATTACK")}
    out["posts"] = rec

    json.dump(out, open(os.path.join(HERE, "speed_results.json"), "w"), indent=1)
    p = dict(out); p.pop("posts"); p["first_minute"] = {k: v for k, v in p["first_minute"].items() if k != "values"}
    p.pop("curve")
    print(json.dumps(p, indent=1))


if __name__ == "__main__":
    main()
