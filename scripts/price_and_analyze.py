"""Price each PRAISE/ATTACK post via Yahoo daily closes; compute +1d and +1wk returns; aggregate."""
import json, os, subprocess, sys
from datetime import datetime, timezone, timedelta, date
from zoneinfo import ZoneInfo
from bisect import bisect_left

ET = ZoneInfo('America/New_York')
PRICE_DIR = 'prices'
os.makedirs(PRICE_DIR, exist_ok=True)
P1 = 1641000000   # ~2022-01-01
P2 = 1751500000   # ~2025-07 ... extended below per need

# Delisted/renamed remaps: Paramount PARA -> successor PSKY (Paramount Skydance), full history backfilled.
TICKER_REMAP = {'PARA': 'PSKY'}

def fetch_series(ticker):
    """Return sorted list of (et_date:date, close:float). Cached to prices/<ticker>.json."""
    ticker = TICKER_REMAP.get(ticker, ticker)
    cache = os.path.join(PRICE_DIR, f'{ticker}.json')
    if os.path.exists(cache):
        raw = json.load(open(cache, encoding='utf-8'))
        if raw.get('ok'):
            return [(date.fromisoformat(d), c) for d, c in raw['series']]
        return None
    series = None
    for host in ('query1', 'query2'):
        url = (f'https://{host}.finance.yahoo.com/v8/finance/chart/{ticker}'
               f'?period1={P1}&period2=1784505600&interval=1d')  # 2026-07-20
        try:
            out = subprocess.run(['curl', '-s', '-H', 'User-Agent: Mozilla/5.0', url],
                                 capture_output=True, text=True, timeout=60).stdout
            d = json.loads(out)
            r = d['chart']['result'][0]
            ts = r['timestamp']
            cl = r['indicators']['quote'][0]['close']
            series = []
            for t, c in zip(ts, cl):
                if c is None:
                    continue
                et_d = datetime.fromtimestamp(t, tz=timezone.utc).astimezone(ET).date()
                series.append((et_d, c))
            series.sort()
            break
        except Exception as e:
            series = None
            continue
    if series:
        json.dump({'ok': True, 'series': [[d.isoformat(), c] for d, c in series]},
                  open(cache, 'w', encoding='utf-8'))
    else:
        json.dump({'ok': False}, open(cache, 'w', encoding='utf-8'))
    return series

def price_post(created_at_utc, series):
    """series: sorted [(date,close)]. Return dict with entry info or None + reason."""
    dt_utc = datetime.fromisoformat(created_at_utc.replace('Z', '+00:00'))
    et_dt = dt_utc.astimezone(ET)
    # effective date: before 4pm ET -> same date; else next calendar day
    if et_dt.hour < 16:
        eff = et_dt.date()
    else:
        eff = et_dt.date() + timedelta(days=1)
    dates = [d for d, _ in series]
    idx = bisect_left(dates, eff)
    if idx >= len(dates):
        return None, 'post after last available price'
    entry_date = dates[idx]
    if (entry_date - eff).days > 10:
        return None, f'no price near post ({eff} -> {entry_date})'
    if idx + 1 >= len(series):
        return None, 'no +1d bar'
    entry_close = series[idx][1]
    nd_close = series[idx + 1][1]
    nd_ret = (nd_close - entry_close) / entry_close * 100
    wk_ret = None
    if idx + 5 < len(series):
        wk_close = series[idx + 5][1]
        wk_ret = (wk_close - entry_close) / entry_close * 100
    return {
        'entry_date': entry_date.isoformat(),
        'entry_close': round(entry_close, 4),
        'et_time': et_dt.strftime('%Y-%m-%d %H:%M'),
        # regular session 9:30-16:00 ET on a weekday (pre-market/after-hours = out)
        'inhours': (et_dt.weekday() < 5 and (9, 30) <= (et_dt.hour, et_dt.minute) < (16, 0)),
        'nd_ret': round(nd_ret, 3),
        'wk_ret': round(wk_ret, 3) if wk_ret is not None else None,
    }, None

def main():
    rows = [json.loads(l) for l in open('classified.jsonl', encoding='utf-8') if l.strip()]
    keep = [r for r in rows if r['sentiment'] in ('PRAISE', 'ATTACK')]
    tickers = sorted({r['ticker'] for r in keep})
    print(f'{len(rows)} classified, {len(keep)} praise/attack, {len(tickers)} tickers', flush=True)
    series_map = {}
    dead = []
    for tk in tickers:
        s = fetch_series(tk)
        if not s:
            dead.append(tk)
        series_map[tk] = s
        print(f'  {tk}: {"%d bars"%len(s) if s else "NO DATA"}', flush=True)

    priced, drops = [], []
    for r in keep:
        s = series_map.get(r['ticker'])
        if not s:
            drops.append((r, 'no ticker data'))
            continue
        info, reason = price_post(r['created_at'], s)
        if info is None:
            drops.append((r, reason))
            continue
        rec = dict(r)
        rec.update(info)
        priced.append(rec)
    json.dump(priced, open('priced.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump([{**r, '_drop': reason} for r, reason in drops],
              open('drops.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'priced {len(priced)}, dropped {len(drops)}, dead tickers {dead}', flush=True)

if __name__ == '__main__':
    main()
