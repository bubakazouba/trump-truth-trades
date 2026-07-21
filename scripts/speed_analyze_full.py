"""Reaction-speed analysis over the FULL LLM-swept in-hours universe
(data/sweep_inhours_labeled.json), answering: when Trump names a public company
during market hours, how much and how fast does that stock actually move?

Primary measure is UNSIGNED (absolute % move vs the pre-post reference) — it asks
"does the stock move at all, in either direction," which is the honest test of
market impact and needs no stance label. We also report the SIGNED curve for the
directional (PRAISE/ATTACK) subset, and a matched-baseline: the same stock's
absolute move at a random in-session minute on the same day, to see whether the
post-minute move is bigger than normal intraday noise.

Reuses the reference/anchor bar logic from speed_analyze.py verbatim.
Bars: data/polygon_bars/poly_<TICKER>_<DATE>.json (Polygon + Twelve Data backfill).
"""
import json, os, statistics
from datetime import datetime
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
BARS_DIR = os.path.join(DATA, "polygon_bars")
ET = ZoneInfo("America/New_York")
OPEN_M, CLOSE_M = 9 * 60 + 30, 16 * 60
MAXOFF = 60


def load_pairs():
    pairs = json.load(open(os.path.join(DATA, "sweep_inhours_labeled.json")))
    for p in pairs:
        dt = datetime.fromisoformat(p["created_at"].replace("Z", "+00:00")).astimezone(ET)
        p["_dt"], p["_min"] = dt, dt.hour * 60 + dt.minute
    return pairs


def load_bars(tk, d):
    p = os.path.join(BARS_DIR, f"poly_{tk}_{d}.json")
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


def curve_for(pm, bars, sign=1.0):
    """Cumulative % move vs last pre-post bar, from offset 0..MAXOFF. sign flips direction."""
    prior = [m for m in bars if m < pm]
    if not prior:
        return None, "no_prior_bar"
    ref = bars[max(prior)]
    if not ref:
        return None, "bad_ref"
    at_or_after = [m for m in bars if m >= pm]
    if not at_or_after:
        return None, "no_anchor_bar"
    anchor = min(at_or_after)
    avail = sorted(bars)
    curve = {}
    for off in range(0, MAXOFF + 1):
        target = anchor + off
        if target >= CLOSE_M:
            break
        cands = [m for m in avail if anchor <= m <= target]
        if not cands:
            continue
        px = bars[max(cands)]
        curve[off] = sign * (px / ref - 1.0) * 100.0
    if 0 not in curve or 30 not in curve:
        return None, "incomplete_window"
    return {"ref": ref, "anchor": anchor, "curve": curve}, "ok"


def baseline_abs_move(bars, exclude_min):
    """Absolute 30-min cumulative move from a deterministic 'typical' in-session
    minute (the session midpoint), as a noise baseline. No RNG (workflow-safe)."""
    mins = sorted(bars)
    if len(mins) < 40:
        return None
    mid = mins[len(mins) // 2]
    if abs(mid - exclude_min) < 35:  # avoid overlapping the real post window
        mid = mins[len(mins) // 4]
    r, why = curve_for(mid, bars, 1.0)
    if r is None or 30 not in r["curve"]:
        return None
    return abs(r["curve"][30])


def pct_pos(vals):
    return 100.0 * sum(1 for x in vals if x > 0) / len(vals) if vals else 0.0


def stats_block(vals):
    v = sorted(vals)
    return {
        "n": len(v),
        "mean": statistics.fmean(v) if v else 0.0,
        "median": statistics.median(v) if v else 0.0,
        "p25": v[int(.25 * (len(v) - 1))] if v else 0.0,
        "p75": v[int(.75 * (len(v) - 1))] if v else 0.0,
        "p90": v[int(.90 * (len(v) - 1))] if v else 0.0,
        "max": max(v) if v else 0.0,
    }


def main():
    pairs = load_pairs()
    rec, drops = [], {}
    for p in pairs:
        d = p["_dt"].date().isoformat()
        bars = load_bars(p["ticker"], d)
        if bars is None:
            drops["no_data"] = drops.get("no_data", 0) + 1
            continue
        # unsigned curve (sign=1); we take abs() per offset for the unsigned view
        r, why = curve_for(p["_min"], bars, 1.0)
        if r is None:
            drops[why] = drops.get(why, 0) + 1
            continue
        sign = 1.0 if p["sentiment"] == "PRAISE" else (-1.0 if p["sentiment"] == "ATTACK" else 0.0)
        rec.append({
            "id": p["id"], "ticker": p["ticker"], "company": p["company"],
            "date": d, "et": p["_dt"].strftime("%H:%M"),
            "sentiment": p["sentiment"], "substantive": p.get("substantive", False),
            "basis": p.get("basis"), "mention": p.get("mention"),
            "raw_curve": r["curve"],  # signed-up (raw price direction)
            "sign": sign,
            "baseline30": baseline_abs_move(bars, p["_min"]),
        })

    n = len(rec)
    out = {"n_in_hours_pairs": len(pairs), "n_analyzed": n, "drops": drops}
    if not n:
        json.dump(out, open(os.path.join(DATA, "speed_full_results.json"), "w"), indent=1)
        print(json.dumps(out, indent=1)); return

    # ---- UNSIGNED (absolute move) — the core "does it move at all" measure ----
    def absmove(r, off):
        return abs(r["raw_curve"][off]) if off in r["raw_curve"] else None

    abs_curve = []
    for off in range(0, 31):
        v = [absmove(r, off) for r in rec]
        v = [x for x in v if x is not None]
        if v:
            s = stats_block(v)
            s["off"] = off
            abs_curve.append(s)
    out["abs_curve"] = abs_curve

    first_abs = [abs(r["raw_curve"][0]) for r in rec]
    m30_abs = [abs(r["raw_curve"][30]) for r in rec if 30 in r["raw_curve"]]
    out["first_minute_abs"] = stats_block(first_abs)
    out["move_30_abs"] = stats_block(m30_abs)

    # baseline: typical same-day 30-min absolute move
    base = [r["baseline30"] for r in rec if r["baseline30"] is not None]
    out["baseline_30_abs"] = stats_block(base)
    out["excess_vs_baseline"] = {
        "post_median_30": statistics.median(m30_abs),
        "baseline_median_30": statistics.median(base) if base else None,
        "ratio_median": (statistics.median(m30_abs) / statistics.median(base)) if base and statistics.median(base) else None,
    }

    # how big is the first-minute move? thresholds
    out["first_minute_buckets"] = {
        ">=0.5%": sum(1 for x in first_abs if x >= 0.5),
        ">=1%": sum(1 for x in first_abs if x >= 1.0),
        ">=2%": sum(1 for x in first_abs if x >= 2.0),
        "<0.25%": sum(1 for x in first_abs if x < 0.25),
        "n": len(first_abs),
    }

    # ---- SIGNED (directional) — only PRAISE/ATTACK subset ----
    directional = [r for r in rec if r["sign"] != 0.0]
    if directional:
        sc = []
        for off in range(0, 31):
            v = [r["sign"] * r["raw_curve"][off] for r in directional if off in r["raw_curve"]]
            if v:
                sc.append({"off": off, "n": len(v), "mean": statistics.fmean(v),
                           "median": statistics.median(v)})
        out["signed_curve"] = sc
        fsm = [r["sign"] * r["raw_curve"][0] for r in directional]
        out["signed_first_minute"] = {
            "n": len(fsm), "mean": statistics.fmean(fsm), "median": statistics.median(fsm),
            "pct_correct_direction": pct_pos(fsm),
        }
        s30 = [r["sign"] * r["raw_curve"][30] for r in directional if 30 in r["raw_curve"]]
        out["signed_move_30"] = {"n": len(s30), "mean": statistics.fmean(s30),
                                 "median": statistics.median(s30),
                                 "pct_correct_direction": pct_pos(s30)}
        out["directional_n"] = {"PRAISE": sum(1 for r in directional if r["sentiment"] == "PRAISE"),
                                 "ATTACK": sum(1 for r in directional if r["sentiment"] == "ATTACK")}

    # substantive-only cut (materially about the company)
    sub = [r for r in rec if r["substantive"]]
    if sub:
        sub_first = [abs(r["raw_curve"][0]) for r in sub]
        sub_30 = [abs(r["raw_curve"][30]) for r in sub if 30 in r["raw_curve"]]
        out["substantive_abs"] = {"n": len(sub),
                                  "first_minute": stats_block(sub_first),
                                  "move_30": stats_block(sub_30)}

    # concentration + composition
    tc = {}
    for r in rec:
        tc[r["ticker"]] = tc.get(r["ticker"], 0) + 1
    out["by_ticker"] = sorted(tc.items(), key=lambda x: -x[1])
    out["by_sentiment"] = {s: sum(1 for r in rec if r["sentiment"] == s)
                           for s in ("PRAISE", "ATTACK", "NEUTRAL")}
    out["posts"] = rec

    json.dump(out, open(os.path.join(DATA, "speed_full_results.json"), "w"), indent=1)
    # printable summary (drop big arrays)
    pr = {k: v for k, v in out.items() if k not in ("posts", "abs_curve", "signed_curve")}
    print(json.dumps(pr, indent=1))


if __name__ == "__main__":
    main()
