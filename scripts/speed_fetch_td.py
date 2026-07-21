"""Backfill 1-min bars that Polygon's free tier refused (pre-2-year window),
using Twelve Data's free tier (https://twelvedata.com), which serves historical
1-minute intraday back to ~2022 (validated against Polygon: 390/390 bars match,
mean close diff 0.0005%).

Only touches ticker-days that FAILED in speed_fetch_log.json and were never cached
by Polygon. Output is written in Polygon's exact JSON schema
({"results": [{"t","o","h","l","c","v"}], "status": "OK"}) so speed_analyze.py
reads these files with zero changes.

Free tier: 800 requests/day, 8/min — the whole ~90-ticker-day backlog fits in one run.

Known gap: pre-merger Trump Media traded as DWAC (delisted), which Twelve Data no
longer serves, so DJT dates before the 2024-03-26 merger close can't be backfilled.

Key: put a Twelve Data free key in scripts/twelvedata_key.txt (git-ignored via *_key.txt).
"""
import json, os, time, urllib.request, urllib.error
from datetime import datetime
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
ET = ZoneInfo("America/New_York")
BARS_DIR = os.path.join(DATA, "polygon_bars")
KEY = open(os.path.join(HERE, "twelvedata_key.txt")).read().strip()
LOG_PATH = os.path.join(DATA, "speed_fetch_td_log.json")

FAIL = {"http_error", "rate_limited", "exception", "empty"}
THROTTLE = 8  # seconds between calls (free tier ~8/min)


def data_file(name):
    for base in (DATA, HERE):
        p = os.path.join(base, name)
        if os.path.exists(p):
            return p
    return os.path.join(DATA, name)


def to_backfill():
    """Ticker-days that failed on Polygon and were never successfully cached."""
    log = json.load(open(data_file("speed_fetch_log.json")))
    ok = {(r["ticker"], r["date"]) for r in log if r["status"] in ("ok", "cached")}
    fail = {(r["ticker"], r["date"]) for r in log if r["status"] in FAIL}
    return sorted(fail - ok, key=lambda x: x[1])


def cache_path(tk, d):
    return os.path.join(BARS_DIR, f"poly_{tk}_{d}.json")


def fetch_day(tk, d, key):
    """One Twelve Data call: all regular-session 1-min bars for tk on day d."""
    url = ("https://api.twelvedata.com/time_series"
           f"?symbol={tk}&interval=1min"
           f"&start_date={d} 09:30:00&end_date={d} 16:00:00"
           f"&outputsize=5000&timezone=America/New_York&apikey={key}").replace(" ", "%20")
    with urllib.request.urlopen(url, timeout=90) as resp:
        return json.loads(resp.read().decode())


def td_to_polygon(tk, d, td):
    """Convert a Twelve Data time_series payload -> Polygon-shaped bars for one day.
    TD datetimes are exchange-local (ET here); convert to epoch ms."""
    vals = td.get("values")
    if not vals:
        return None
    results = []
    for v in vals:
        ts = v["datetime"]
        # can be "YYYY-MM-DD HH:MM:SS" or just "YYYY-MM-DD"
        fmt = "%Y-%m-%d %H:%M:%S" if " " in ts else "%Y-%m-%d"
        dt = datetime.strptime(ts, fmt).replace(tzinfo=ET)
        if dt.date().isoformat() != d:
            continue
        results.append({
            "t": int(dt.timestamp() * 1000),
            "o": float(v["open"]), "h": float(v["high"]),
            "l": float(v["low"]), "c": float(v["close"]),
            "v": float(v.get("volume", 0) or 0),
        })
    if not results:
        return None
    results.sort(key=lambda b: b["t"])
    return {"ticker": tk, "results": results, "status": "OK",
            "resultsCount": len(results), "adjusted": True, "source": "twelvedata"}


def main():
    os.makedirs(BARS_DIR, exist_ok=True)
    tds = to_backfill()
    log = json.load(open(LOG_PATH)) if os.path.exists(LOG_PATH) else []
    print(f"ticker-days to backfill: {len(tds)}", flush=True)
    for i, (tk, d) in enumerate(tds, 1):
        cp = cache_path(tk, d)
        if os.path.exists(cp):
            print(f"[{i}/{len(tds)}] {tk} {d} already on disk", flush=True)
            continue
        status, bars, err = "ok", 0, None
        try:
            td = fetch_day(tk, d, KEY)
            code = td.get("code")
            if code and code != 200:
                msg = (td.get("message") or "")[:160]
                if code == 429 or "limit" in msg.lower():
                    status, err = "rate_limited", msg
                elif code in (400, 404):
                    status, err = "empty", f"{code}: {msg}"  # delisted/unknown symbol-day
                else:
                    status, err = "http_error", f"{code}: {msg}"
            else:
                out = td_to_polygon(tk, d, td)
                if out:
                    json.dump(out, open(cp, "w"))
                    bars = out["resultsCount"]
                else:
                    status, err = "empty", "no bars returned"
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:160]
            status = "rate_limited" if e.code == 429 else "http_error"
            err = f"{e.code}: {body}"
        except Exception as e:
            status, err = "exception", repr(e)[:160]
        print(f"[{i}/{len(tds)}] {tk} {d} {status} bars={bars} {err or ''}", flush=True)
        log.append({"ticker": tk, "date": d, "status": status, "bars": bars, "error": err})
        json.dump(log, open(LOG_PATH, "w"), indent=1)
        if status == "rate_limited":
            print("Rate limited — pausing 60s.", flush=True)
            time.sleep(60)
        else:
            time.sleep(THROTTLE)
    ok = sum(1 for x in log if x["status"] == "ok")
    print(f"DONE. {ok} ticker-days backfilled via Twelve Data.", flush=True)


if __name__ == "__main__":
    main()
