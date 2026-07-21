"""Fetch 1-min Polygon bars for every in-market-hours Trump post ticker-day.
Attempts ALL ticker-days newest-first; caches; logs failures. REAL data only.
"""
import json, os, sys, time, urllib.request, urllib.error
from datetime import datetime
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
ET = ZoneInfo("America/New_York")
KEY = open(os.path.join(HERE, "polygon_key.txt")).read().strip()


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
        mins = dt.hour * 60 + dt.minute
        if not (570 <= mins < 960):  # 9:30 <= t < 16:00
            continue
        r["_et"] = dt.isoformat()
        out.append(r)
    return out


def cache_path(tk, d):
    return os.path.join(HERE, f"poly_{tk}_{d}.json")


def main():
    posts = in_hours_posts()
    tds = sorted({(p["ticker"], p["_et"][:10]) for p in posts}, key=lambda x: x[1], reverse=True)
    print(f"in-hours posts: {len(posts)} | unique ticker-days: {len(tds)}", flush=True)
    log = []
    for i, (tk, d) in enumerate(tds, 1):
        cp = cache_path(tk, d)
        if os.path.exists(cp):
            try:
                j = json.load(open(cp))
                if j.get("results"):
                    print(f"[{i}/{len(tds)}] {tk} {d} CACHED ({len(j['results'])} bars)", flush=True)
                    log.append({"ticker": tk, "date": d, "status": "cached", "bars": len(j["results"])})
                    continue
            except Exception:
                pass
        url = (f"https://api.polygon.io/v2/aggs/ticker/{tk}/range/1/minute/{d}/{d}"
               f"?adjusted=true&sort=asc&limit=50000&apiKey={KEY}")
        status, bars, err = "ok", 0, None
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                j = json.loads(resp.read().decode())
            if j.get("status") in ("OK", "DELAYED") and j.get("results"):
                bars = len(j["results"])
                json.dump(j, open(cp, "w"))
            else:
                status, err = "empty", j.get("status") or j.get("message")
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:200]
            status = "http_error"
            try:
                err = json.loads(body).get("message", body)
            except Exception:
                err = body
            if e.code == 429:
                status = "rate_limited"
        except Exception as e:
            status, err = "exception", repr(e)[:200]
        print(f"[{i}/{len(tds)}] {tk} {d} {status} bars={bars} {err or ''}", flush=True)
        log.append({"ticker": tk, "date": d, "status": status, "bars": bars, "error": err})
        json.dump(log, open(os.path.join(HERE, "speed_fetch_log.json"), "w"), indent=1)
        time.sleep(13)  # free tier ~5 calls/min
    json.dump(log, open(os.path.join(HERE, "speed_fetch_log.json"), "w"), indent=1)
    ok = sum(1 for x in log if x["status"] in ("ok", "cached"))
    print(f"DONE. {ok}/{len(tds)} ticker-days have data.", flush=True)


if __name__ == "__main__":
    main()
