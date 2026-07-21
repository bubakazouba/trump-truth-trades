"""Fetch 1-min bars (Polygon JSON schema) for an arbitrary list of (ticker, date)
pairs from Twelve Data's free tier. Used to price the expanded post-company universe
produced by the full LLM sweep (data/sweep_need_ticker_days.json).

Reads a JSON list of [ticker, "YYYY-MM-DD"] pairs (default: sweep_need_ticker_days.json),
skips any (ticker,date) already on disk, writes poly_<TICKER>_<DATE>.json into
data/polygon_bars/ in Polygon's exact schema so speed_analyze.py needs no changes.

Free tier: 800 req/day, 8/min. Resumable — re-run to continue.
Validated: Twelve Data 1-min closes match Polygon 390/390 bars, mean diff 0.0005%.

Key: scripts/twelvedata_key.txt (git-ignored via *_key.txt).
Usage: python3 scripts/fetch_bars_td.py [path_to_pairs.json]
"""
import json, os, sys, time, urllib.request, urllib.error
from datetime import datetime
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
ET = ZoneInfo("America/New_York")
BARS_DIR = os.path.join(DATA, "polygon_bars")
KEY = open(os.path.join(HERE, "twelvedata_key.txt")).read().strip()
THROTTLE = 8
DAILY_CAP = 780  # stay just under the 800/day free limit


def cache_path(tk, d):
    return os.path.join(BARS_DIR, f"poly_{tk}_{d}.json")


def fetch_day(tk, d, key):
    url = ("https://api.twelvedata.com/time_series"
           f"?symbol={tk}&interval=1min"
           f"&start_date={d} 09:30:00&end_date={d} 16:00:00"
           f"&outputsize=5000&timezone=America/New_York&apikey={key}").replace(" ", "%20")
    with urllib.request.urlopen(url, timeout=90) as resp:
        return json.loads(resp.read().decode())


def td_to_polygon(tk, d, td):
    vals = td.get("values")
    if not vals:
        return None
    results = []
    for v in vals:
        ts = v["datetime"]
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
    pairs_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DATA, "sweep_need_ticker_days.json")
    pairs = [tuple(x) for x in json.load(open(pairs_path))]
    log_path = os.path.join(DATA, "fetch_bars_td_log.json")
    log = json.load(open(log_path)) if os.path.exists(log_path) else []
    logged = {(r["ticker"], r["date"]) for r in log}
    calls = 0
    todo = [(tk, d) for tk, d in pairs if not os.path.exists(cache_path(tk, d))]
    print(f"pairs: {len(pairs)} | already on disk: {len(pairs)-len(todo)} | to fetch: {len(todo)}", flush=True)
    for i, (tk, d) in enumerate(todo, 1):
        if calls >= DAILY_CAP:
            print(f"Hit daily cap ({DAILY_CAP}). Re-run tomorrow to continue.", flush=True)
            break
        status, bars, err = "ok", 0, None
        try:
            td = fetch_day(tk, d, KEY)
            calls += 1
            code = td.get("code")
            if code and code != 200:
                msg = (td.get("message") or "")[:140]
                if code == 429 or "limit" in msg.lower():
                    status, err = "rate_limited", msg
                elif code in (400, 404):
                    status, err = "empty", f"{code}: {msg}"
                else:
                    status, err = "http_error", f"{code}: {msg}"
            else:
                out = td_to_polygon(tk, d, td)
                if out:
                    json.dump(out, open(cache_path(tk, d), "w"))
                    bars = out["resultsCount"]
                else:
                    status, err = "empty", "no bars"
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:140]
            status = "rate_limited" if e.code == 429 else "http_error"
            err = f"{e.code}: {body}"
        except Exception as e:
            status, err = "exception", repr(e)[:140]
        print(f"[{i}/{len(todo)}] {tk} {d} {status} bars={bars} {err or ''}", flush=True)
        if (tk, d) not in logged:
            log.append({"ticker": tk, "date": d, "status": status, "bars": bars, "error": err})
            logged.add((tk, d))
        json.dump(log, open(log_path, "w"), indent=1)
        if status == "rate_limited":
            print("Rate limited — pausing 60s.", flush=True)
            time.sleep(60)
        else:
            time.sleep(THROTTLE)
    ok = sum(1 for r in log if r["status"] == "ok")
    print(f"DONE this run. calls={calls}. total ok in log: {ok}.", flush=True)


if __name__ == "__main__":
    main()
