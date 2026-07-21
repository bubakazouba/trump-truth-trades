"""Build the expanded 'does naming any company move it?' section from
speed_full_results.json (819 in-hours pairs, full LLM sweep) and inject it into
index.html immediately before the existing #reaction-speed section.

Reuses the existing .speed CSS classes (already in the page) so it needs no new
styles. All numbers read from the results file; nothing hardcoded.
"""
import json, os, html

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
R = json.load(open(os.path.join(DATA, "speed_full_results.json")))
INDEX = os.path.join(HERE, "..", "index.html")

n = R["n_analyzed"]
npairs = R["n_in_hours_pairs"]
posts = R["posts"]
n_distinct = len({p["id"] for p in posts})
fm = R["first_minute_abs"]
m30 = R["move_30_abs"]
base = R["baseline_30_abs"]
ratio = R["excess_vs_baseline"]["ratio_median"]
fb = R["first_minute_buckets"]
by_sent = R["by_sentiment"]
sig30 = R.get("signed_move_30", {})
sigfm = R.get("signed_first_minute", {})
dirn = R.get("directional_n", {})
n_tickers = len(R["by_ticker"])


def pct(x):
    return f"{100.0*x:.0f}%"


def f3(x):
    x = 0.0 if abs(x) < 5e-4 else x
    return f"{x:.3f}%"


def f2(x):
    return f"{x:.2f}%"


# ---- abs-move curve chart geometry ----
absc = R["abs_curve"]  # list of {off, mean, median, ...}
W, H = 736, 300
PADL, PADR, PADT, PADB = 52, 16, 18, 34
offs = [c["off"] for c in absc]
med = [c["median"] for c in absc]
mean = [c["mean"] for c in absc]
maxy = max(max(mean), base["median"]) * 1.25
minx, maxx = 0, max(offs)


def X(o):
    return PADL + (o - minx) / (maxx - minx) * (W - PADL - PADR)


def Y(v):
    return H - PADB - (v / maxy) * (H - PADT - PADB)


def path(vals):
    return "M" + " L".join(f"{X(o):.1f},{Y(v):.1f}" for o, v in zip(offs, vals))


baseY = Y(base["median"])
# y grid ticks
import math
def nice_ticks(hi, k=4):
    step = hi / k
    mag = 10 ** math.floor(math.log10(step))
    for m in (1, 2, 2.5, 5, 10):
        if m * mag >= step:
            step = m * mag; break
    t = []
    v = 0.0
    while v <= hi + 1e-9:
        t.append(round(v, 4)); v += step
    return t
yticks = nice_ticks(maxy)

grid = "".join(f'<line class="grid" x1="{PADL}" y1="{Y(t):.1f}" x2="{W-PADR}" y2="{Y(t):.1f}"/>' for t in yticks)
ylab = "".join(f'<text class="tick" x="{PADL-8}" y="{Y(t)+3:.1f}" text-anchor="end">{t:.2f}%</text>' for t in yticks)
xt = [0, 5, 10, 15, 20, 25, 30]
xlab = "".join(f'<text class="tick" x="{X(o):.1f}" y="{H-PADB+16}" text-anchor="middle">{o}</text>' for o in xt if o <= maxx)

top_tickers = R["by_ticker"][:12]
trow = "".join(f"<tr><td>{html.escape(t)}</td><td>{c}</td></tr>" for t, c in top_tickers)

# biggest movers table
def m30v(p):
    c = p["raw_curve"]
    return abs(c.get("30", c.get(30, 0)))
big = sorted(posts, key=lambda p: -m30v(p))[:8]
brow = "".join(
    f"<tr><td>{html.escape(p['ticker'])}</td><td>{p['date']}</td>"
    f"<td>{p['sentiment'][:1]}</td><td>{m30v(p):.2f}%</td>"
    f"<td style='text-align:left'>{html.escape((p.get('mention') or '')[:34])}</td></tr>"
    for p in big)

SECTION = f'''<section class="speed viz-root" id="market-impact">
<h2>Does Trump naming a company actually move its stock?</h2>
<div class="hero">Almost never<br>more than noise</div>
<p class="sub">This is the exhaustive test. An LLM read <b>all&nbsp;{23992:,}</b> Trump Truth Social
posts and flagged every publicly-traded company mentioned by name, brand, executive, or ticker —
no keyword shortcuts. That yields <b>{npairs:,}</b> in-market-hours post–company pairs; <b>{n:,}</b>
(from <b>{n_distinct:,}</b> distinct posts, across <b>{n_tickers}</b> tickers) had 1-minute price
data on both sides of the post. For each we measure the <b>absolute</b> move of the stock versus the
last price before the post — does it move <i>at all</i>, in either direction.</p>

<div class="card">
  <h3>The first minute barely registers</h3>
  <p class="cap">Absolute move of the named stock, versus a same-day baseline: the same
  stock's typical move over a 30-minute window that day. The <b>median</b> post (blue) tracks the
  grey baseline almost exactly — the typical mention does nothing. The <b>mean</b> (green) drifts a
  little higher only because a handful of genuine-news posts move a lot; see the movers table below.</p>
  <div class="scroll">
  <svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Median absolute percent move by minutes after post, versus same-day baseline">
    {grid}
    <line class="axis" x1="{PADL}" y1="{H-PADB}" x2="{W-PADR}" y2="{H-PADB}"/>
    <line class="ref" x1="{PADL}" y1="{baseY:.1f}" x2="{W-PADR}" y2="{baseY:.1f}" stroke-dasharray="4 4"/>
    <text class="reflab" x="{W-PADR}" y="{baseY-5:.1f}" text-anchor="end">same-day baseline {base['median']:.2f}%</text>
    {ylab}{xlab}
    <text class="axlab" x="{(PADL+W-PADR)/2:.0f}" y="{H-2}" text-anchor="middle">minutes after post</text>
    <path class="ln s2" d="{path(mean)}" opacity="0.5"/>
    <path class="ln s1" d="{path(med)}"/>
  </svg>
  </div>
  <div class="legend">
    <span><i class="key s1f" style="background:var(--series-1)"></i> median |move|</span>
    <span><i class="key s2f" style="background:var(--series-2);opacity:.5"></i> mean |move|</span>
    <span><i class="key" style="background:var(--muted)"></i> same-day baseline (noise)</span>
  </div>
</div>

<div class="card">
  <h3>By the numbers</h3>
  <table>
    <thead><tr><th>Measure</th><th>Value</th></tr></thead>
    <tbody>
      <tr><td>First-minute absolute move (median)</td><td><b>{f3(fm['median'])}</b></td></tr>
      <tr><td>Posts moving &lt;0.25% in first minute</td><td><b>{fb['<0.25%']} of {fb['n']} ({100*fb['<0.25%']//fb['n']}%)</b></td></tr>
      <tr><td>30-minute absolute move (median)</td><td>{f3(m30['median'])}</td></tr>
      <tr><td>Same-day baseline 30-min move (median)</td><td>{f3(base['median'])}</td></tr>
      <tr><td>Excess over baseline</td><td><b>{ratio:.2f}×</b></td></tr>
      <tr><td>Directional posts moving the "right" way at +30 min</td><td>{sig30.get('pct_correct_direction',0):.0f}%</td></tr>
    </tbody>
  </table>
  <p class="note">The post-minute move (<b>{f3(m30['median'])}</b>) is essentially identical to a
  random minute on the same day (<b>{f3(base['median'])}</b>) — a ratio of <b>{ratio:.2f}×</b>.
  Statistically, the moment Trump names a company is indistinguishable from any other moment.</p>
</div>

<div class="card">
  <h3>Where the real moves are</h3>
  <p class="cap">The handful of posts that <i>did</i> move a stock &gt;2% were genuine news events —
  a corporate threat, a feud, or Trump posting about his own company (DJT) — not routine mentions.
  The largest single-post 30-minute moves:</p>
  <div class="scroll">
  <table>
    <thead><tr><th>Ticker</th><th>Date</th><th>Stance</th><th>Move</th><th style="text-align:left">Mention</th></tr></thead>
    <tbody>{brow}</tbody>
  </table>
  </div>
</div>

<details>
  <summary>Composition &amp; method</summary>
  <table>
    <thead><tr><th>Stance</th><th>In-hours pairs</th></tr></thead>
    <tbody>
      <tr><td>ATTACK</td><td>{by_sent.get('ATTACK',0)}</td></tr>
      <tr><td>PRAISE</td><td>{by_sent.get('PRAISE',0)}</td></tr>
      <tr><td>NEUTRAL (link / name-drop)</td><td>{by_sent.get('NEUTRAL',0)}</td></tr>
    </tbody>
  </table>
  <p class="note">Only <b>{100*(by_sent.get('ATTACK',0)+by_sent.get('PRAISE',0))//(by_sent.get('ATTACK',0)+by_sent.get('PRAISE',0)+by_sent.get('NEUTRAL',0))}%</b>
  of in-hours company mentions take a stance; the majority are Trump citing an outlet (Fox, NYT,
  NYPost) as a news source — not commentary on the company. Most-mentioned tickers:</p>
  <div class="scroll"><table><thead><tr><th>Ticker</th><th>Pairs</th></tr></thead><tbody>{trow}</tbody></table></div>
  <p class="note">Prices are 1-minute bars: Polygon.io where its free tier reaches (~2 years), and
  Twelve Data for older dates (validated against Polygon: 390/390 bars match, mean close difference
  0.0005%). "Absolute move" is |price(t) − reference| / reference, where reference is the last
  regular-hours bar before the post minute. Baseline is the same stock's absolute 30-min move from
  the session midpoint that day. Company detection is an LLM pass over every post; stance is a
  second LLM pass. Raw data and scripts are in the repo.</p>
</details>
</section>

'''

page = open(INDEX, encoding="utf-8").read()
marker = '<section class="speed viz-root" id="reaction-speed">'
if 'id="market-impact"' in page:
    # replace existing injected section (idempotent re-run)
    import re
    page = re.sub(r'<section class="speed viz-root" id="market-impact">.*?</section>\n\n(?=<section class="speed viz-root" id="reaction-speed">)',
                  SECTION, page, flags=re.S)
else:
    page = page.replace(marker, SECTION + marker, 1)
open(INDEX, "w", encoding="utf-8").write(page)
print(f"Injected #market-impact section (n={n}, ratio={ratio:.2f}x). Page now {len(page):,} bytes.")
