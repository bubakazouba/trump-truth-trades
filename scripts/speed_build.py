"""Build speed_section.html — self-contained inline SVG, theme-aware, no CDN.
Every number is read from speed_results.json (real Polygon bars). Nothing hardcoded.
"""
import json, os, html, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "speed_results.json")))
FETCH = json.load(open(os.path.join(HERE, "speed_fetch_log.json")))

n = R["n_analyzed"]
curve = R["curve"]
fm = R["first_minute"]
# normalize negative zero so it never renders as "-0.00%"
for _k in ("mean", "median", "min", "max"):
    if abs(fm[_k]) < 5e-9:
        fm[_k] = 0.0
for _c in curve:
    for _k in ("mean", "median", "p25", "p75"):
        if abs(_c[_k]) < 5e-9:
            _c[_k] = 0.0
cap = R["capture"]
hit = R["hit_rate"]

OOW = sum(1 for x in FETCH if "doesn't include this data timeframe" in (x.get("error") or ""))

# n counts post-COMPANY observations; one post naming several companies yields several
# rows that move together. Surface the distinct-post count too — it is the honest n.
_ids = [r["id"] for r in R["posts"]]
N_DISTINCT = len(set(_ids))
_per = {}
for _i in _ids:
    _per[_i] = _per.get(_i, 0) + 1
N_MULTI = sum(1 for v in _per.values() if v > 1)
MAX_MULTI = max(_per.values())

# exact-zero first-minute moves (tick quantization on low-priced names)
N_ZERO = sum(1 for r in R["posts"] if abs(r["curve"]["0"]) < 1e-12)

# +60 min horizon, where a full window exists before the close
_h60 = [r["curve"]["60"] for r in R["posts"] if "60" in r["curve"]]
H60 = None
if _h60:
    H60 = {"n": len(_h60), "mean": statistics.fmean(_h60), "median": statistics.median(_h60),
           "hit": 100.0 * sum(1 for x in _h60 if x > 0) / len(_h60)}


def esc(s):
    return html.escape(str(s))


def f(x, d=3):
    return f"{x:.{d}f}"


# ---------- chart 1: reaction curve ----------
W, H = 720, 300
ML, MR, MT, MB = 54, 96, 18, 40
PW, PH = W - ML - MR, H - MT - MB
xs = [c["off"] for c in curve]
allv = [c["p25"] for c in curve] + [c["p75"] for c in curve] + [c["mean"] for c in curve] + [c["median"] for c in curve]
lo, hi = min(allv), max(allv)
pad = (hi - lo) * 0.15 or 0.1
lo, hi = lo - pad, hi + pad


def X(o):
    return ML + (o - xs[0]) / (xs[-1] - xs[0]) * PW


def Y(v):
    return MT + (hi - v) / (hi - lo) * PH


def ticks(lo, hi, n=5):
    import math
    span = hi - lo
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    step = min([m * mag for m in (1, 2, 2.5, 5, 10)], key=lambda s: abs(s - raw))
    t, out = math.ceil(lo / step) * step, []
    while t <= hi + 1e-9:
        out.append(round(t, 10)); t += step
    return out


yt = ticks(lo, hi)
mean_pts = " ".join(f"{X(c['off']):.1f},{Y(c['mean']):.1f}" for c in curve)
med_pts = " ".join(f"{X(c['off']):.1f},{Y(c['median']):.1f}" for c in curve)
band = (" ".join(f"{X(c['off']):.1f},{Y(c['p75']):.1f}" for c in curve) + " " +
        " ".join(f"{X(c['off']):.1f},{Y(c['p25']):.1f}" for c in reversed(curve)))
last = curve[-1]

# End-labels: only place them inline when the two series separate enough at the right
# edge to not collide. When they converge (they do here), use leader lines that fan the
# labels apart while staying tied to their line-ends — never silently stacked text.
_my, _dy = Y(last["mean"]), Y(last["median"])
_lx = X(last["off"])
if abs(_my - _dy) >= 16:
    end_labels = (
        f'<text class="dlab" x="{_lx+10:.1f}" y="{_my+4:.1f}">Mean {last["mean"]:+.2f}%</text>'
        f'<text class="dlab" x="{_lx+10:.1f}" y="{_dy+4:.1f}">Median {last["median"]:+.2f}%</text>')
else:
    _hi_is_mean = _my <= _dy
    _ty = min(_my, _dy) - 13          # upper label slot
    _by = max(_my, _dy) + 17          # lower label slot
    _t_txt = (f'Mean {last["mean"]:+.2f}%' if _hi_is_mean else f'Median {last["median"]:+.2f}%')
    _b_txt = (f'Median {last["median"]:+.2f}%' if _hi_is_mean else f'Mean {last["mean"]:+.2f}%')
    end_labels = (
        f'<polyline class="lead" points="{_lx+4:.1f},{min(_my,_dy):.1f} {_lx+12:.1f},{_ty+ -3:.1f} {_lx+18:.1f},{_ty-3:.1f}"/>'
        f'<polyline class="lead" points="{_lx+4:.1f},{max(_my,_dy):.1f} {_lx+12:.1f},{_by-4:.1f} {_lx+18:.1f},{_by-4:.1f}"/>'
        f'<text class="dlab" x="{_lx+21:.1f}" y="{_ty:.1f}">{_t_txt}</text>'
        f'<text class="dlab" x="{_lx+21:.1f}" y="{_by:.1f}">{_b_txt}</text>')

grid = "".join(f'<line class="grid" x1="{ML}" x2="{ML+PW}" y1="{Y(t):.1f}" y2="{Y(t):.1f}"/>' for t in yt)
ylab = "".join(f'<text class="tick" x="{ML-8}" y="{Y(t)+4:.1f}" text-anchor="end">{t:+.2f}%</text>' for t in yt)
xlab = "".join(f'<text class="tick" x="{X(o):.1f}" y="{MT+PH+22}" text-anchor="middle">{o}</text>'
               for o in [0, 5, 10, 15, 20, 25, 30])
zero = (f'<line class="zero" x1="{ML}" x2="{ML+PW}" y1="{Y(0):.1f}" y2="{Y(0):.1f}"/>'
        if lo < 0 < hi else "")
hover1 = "".join(
    f'<rect class="hit" x="{X(c["off"])-PW/(len(curve)-1)/2:.1f}" y="{MT}" '
    f'width="{PW/(len(curve)-1):.1f}" height="{PH}" data-off="{c["off"]}" '
    f'data-mean="{f(c["mean"])}" data-median="{f(c["median"])}" data-n="{c["n"]}"/>'
    for c in curve)

chart1 = f'''<svg viewBox="0 0 {W} {H}" role="img" aria-label="Mean and median directional cumulative percent move by minutes after post" class="chart" id="c1">
  <title>Directional cumulative move, minute 0 to 30 after post</title>
  {grid}{zero}
  <line class="axis" x1="{ML}" x2="{ML}" y1="{MT}" y2="{MT+PH}"/>
  <line class="axis" x1="{ML}" x2="{ML+PW}" y1="{MT+PH}" y2="{MT+PH}"/>
  {ylab}{xlab}
  <polygon class="band" points="{band}"/>
  <polyline class="ln s2" points="{med_pts}"/>
  <polyline class="ln s1" points="{mean_pts}"/>
  <circle class="dot s1f" cx="{X(last['off']):.1f}" cy="{Y(last['mean']):.1f}" r="4"/>
  <circle class="dot s2f" cx="{X(last['off']):.1f}" cy="{Y(last['median']):.1f}" r="4"/>
  {end_labels}
  <text class="axlab" x="{ML+PW/2:.0f}" y="{H-4}" text-anchor="middle">Minutes after post</text>
  <g class="cross" id="c1cross" hidden><line class="chair" y1="{MT}" y2="{MT+PH}"/></g>
  {hover1}
</svg>'''

# ---------- chart 2: first-minute distribution ----------
vals = fm["values"]
W2, H2 = 720, 268
ML2, MR2, MT2, MB2 = 54, 20, 30, 40  # MT2 leaves a band above the plot for the median label
PW2, PH2 = W2 - ML2 - MR2, H2 - MT2 - MB2
amax = max(abs(min(vals)), abs(max(vals)))
edge = amax * 1.05 or 0.1
NB = 21
bw = 2 * edge / NB
bins = [0] * NB
for v in vals:
    i = min(NB - 1, int((v + edge) / bw))
    bins[i] += 1
bmax = max(bins)


def X2(v):
    return ML2 + (v + edge) / (2 * edge) * PW2


def Y2(c):
    return MT2 + (1 - c / bmax) * PH2


yt2 = [t for t in range(0, bmax + 1, max(1, round(bmax / 4)))]
grid2 = "".join(f'<line class="grid" x1="{ML2}" x2="{ML2+PW2}" y1="{Y2(t):.1f}" y2="{Y2(t):.1f}"/>' for t in yt2)
ylab2 = "".join(f'<text class="tick" x="{ML2-8}" y="{Y2(t)+4:.1f}" text-anchor="end">{t}</text>' for t in yt2)
slot = PW2 / NB
bars2 = ""
for i, c in enumerate(bins):
    if not c:
        continue
    x = ML2 + i * slot + 1  # 2px surface gap between adjacent bars
    w = slot - 2
    h = PH2 - (Y2(c) - MT2)
    r = min(4, w / 2, h)
    lo_e, hi_e = -edge + i * bw, -edge + (i + 1) * bw
    bars2 += (f'<path class="hbar" d="M{x:.1f},{MT2+PH2} L{x:.1f},{Y2(c)+r:.1f} Q{x:.1f},{Y2(c):.1f} {x+r:.1f},{Y2(c):.1f} '
              f'L{x+w-r:.1f},{Y2(c):.1f} Q{x+w:.1f},{Y2(c):.1f} {x+w:.1f},{Y2(c)+r:.1f} L{x+w:.1f},{MT2+PH2} Z" '
              f'data-lo="{f(lo_e,2)}" data-hi="{f(hi_e,2)}" data-c="{c}" tabindex="0"/>')
xt2 = [-edge, -edge / 2, 0, edge / 2, edge]
xlab2 = "".join(f'<text class="tick" x="{X2(t):.1f}" y="{MT2+PH2+22}" text-anchor="middle">{t:+.2f}%</text>' for t in xt2)
med_x = X2(fm["median"])
# When the median is exactly 0 the median rule lands on the zero rule; say so rather
# than letting the reader think two coincident lines are a rendering bug.
med_note = " (on the zero line)" if abs(fm["median"]) < 5e-9 else ""
chart2 = f'''<svg viewBox="0 0 {W2} {H2}" role="img" aria-label="Distribution of the first-minute directional move across posts" class="chart" id="c2">
  <title>First-minute directional move, {n} posts</title>
  {grid2}
  <line class="axis" x1="{ML2}" x2="{ML2}" y1="{MT2}" y2="{MT2+PH2}"/>
  <line class="axis" x1="{ML2}" x2="{ML2+PW2}" y1="{MT2+PH2}" y2="{MT2+PH2}"/>
  {ylab2}{xlab2}
  <line class="zero" x1="{X2(0):.1f}" x2="{X2(0):.1f}" y1="{MT2}" y2="{MT2+PH2}"/>
  {bars2}
  <line class="medline" x1="{med_x:.1f}" x2="{med_x:.1f}" y1="{MT2}" y2="{MT2+PH2}"/>
  <text class="dlab" x="{med_x:.1f}" y="{MT2-9}" text-anchor="middle">Median {fm['median']:+.3f}%{med_note}</text>
  <text class="axlab" x="{ML2+PW2/2:.0f}" y="{H2-4}" text-anchor="middle">First-minute move, signed in the post's direction (%)</text>
</svg>'''

# ---------- chart 3: speed of capture ----------
HOR = [0, 1, 5, 15, 30]
W3, H3 = 720, 260
ML3, MR3, MT3, MB3 = 54, 20, 22, 40
PW3, PH3 = W3 - ML3 - MR3, H3 - MT3 - MB3
shares = [cap[str(h)]["share_of_30_mean"] for h in HOR]
smax = max(max(shares), 100) * 1.12
smin = min(min(shares), 0)
sspan = smax - smin


def Y3(v):
    return MT3 + (smax - v) / sspan * PH3


yt3 = ticks(smin, smax, 4)
grid3 = "".join(f'<line class="grid" x1="{ML3}" x2="{ML3+PW3}" y1="{Y3(t):.1f}" y2="{Y3(t):.1f}"/>' for t in yt3)
ylab3 = "".join(f'<text class="tick" x="{ML3-8}" y="{Y3(t)+4:.1f}" text-anchor="end">{t:.0f}%</text>' for t in yt3)
band3 = PW3 / len(HOR)
bw3 = min(24, band3 - 16)
bars3 = ""
for i, h in enumerate(HOR):
    s = cap[str(h)]["share_of_30_mean"]
    cx = ML3 + band3 * (i + .5)
    x = cx - bw3 / 2
    y0, y1 = Y3(0), Y3(s)
    top, bot = min(y0, y1), max(y0, y1)
    hgt = bot - top
    r = min(4, hgt)
    if s >= 0:
        d = (f'M{x:.1f},{bot:.1f} L{x:.1f},{top+r:.1f} Q{x:.1f},{top:.1f} {x+r:.1f},{top:.1f} '
             f'L{x+bw3-r:.1f},{top:.1f} Q{x+bw3:.1f},{top:.1f} {x+bw3:.1f},{top+r:.1f} L{x+bw3:.1f},{bot:.1f} Z')
    else:
        d = (f'M{x:.1f},{top:.1f} L{x:.1f},{bot-r:.1f} Q{x:.1f},{bot:.1f} {x+r:.1f},{bot:.1f} '
             f'L{x+bw3-r:.1f},{bot:.1f} Q{x+bw3:.1f},{bot:.1f} {x+bw3:.1f},{bot-r:.1f} L{x+bw3:.1f},{top:.1f} Z')
    lab_y = top - 8 if s >= 0 else bot + 16
    # full precision in the attribute: rounding to 1dp here and again in JS made the
    # tooltip disagree with the bar's own label (29% vs 30%).
    bars3 += (f'<path class="cbar" d="{d}" data-h="{h}" data-s="{f(s,6)}" '
              f'data-m="{f(cap[str(h)]["mean_move"])}" tabindex="0"/>'
              f'<text class="blab" x="{cx:.1f}" y="{lab_y:.1f}" text-anchor="middle">{s:.0f}%</text>')
xlab3 = "".join(f'<text class="tick" x="{ML3+band3*(i+.5):.1f}" y="{MT3+PH3+22}" text-anchor="middle">+{h} min</text>'
                for i, h in enumerate(HOR))
# Reference line label sits at the LEFT edge: the right edge is occupied by the +30 bar's
# own 100% value label, and two labels on the same line collide.
ref100 = (f'<line class="ref" x1="{ML3}" x2="{ML3+PW3}" y1="{Y3(100):.1f}" y2="{Y3(100):.1f}"/>'
          f'<text class="reflab" x="{ML3+4}" y="{Y3(100)-6:.1f}" text-anchor="start">100% = the +30 min mean</text>')
chart3 = f'''<svg viewBox="0 0 {W3} {H3}" role="img" aria-label="Share of the 30-minute mean move already present at each horizon" class="chart" id="c3">
  <title>Share of the +30 min mean move present at each horizon</title>
  {grid3}
  <line class="axis" x1="{ML3}" x2="{ML3}" y1="{MT3}" y2="{MT3+PH3}"/>
  <line class="axis" x1="{ML3}" x2="{ML3+PW3}" y1="{Y3(0):.1f}" y2="{Y3(0):.1f}"/>
  {ylab3}{xlab3}{ref100}
  {bars3}
  <text class="axlab" x="{ML3+PW3/2:.0f}" y="{H3-4}" text-anchor="middle">Minutes after post</text>
</svg>'''

# ---------- table view ----------
rows = "".join(
    f"<tr><td>+{h} min</td><td>{cap[str(h)]['mean_move']:+.3f}%</td>"
    f"<td>{cap[str(h)]['share_of_30_mean']:.0f}%</td>"
    f"<td>{hit[str(h)]['pct']:.0f}%</td><td>{cap[str(h)]['n']}</td></tr>" for h in HOR)
tick_rows = "".join(f"<tr><td>{esc(t)}</td><td>{c}</td></tr>" for t, c in R["by_ticker"])

hl_share = cap["0"]["share_of_30_mean"]
h60_txt = ("<b>Past +30 min:</b> a full +60 min window exists for {n60} of {nn} observations — mean "
           "{m60:+.3f}% (median {md60:+.3f}%, {h60hit:.0f}% hit rate), i.e. the drift continues rather "
           "than reverting, on an even thinner sample.").format(
    n60=H60["n"], nn=n, m60=H60["mean"], md60=H60["median"], h60hit=H60["hit"]) if H60 else ""
drops = R["drops"]
drop_txt = ", ".join(f"{k.replace('_',' ')}: {v}" for k, v in sorted(drops.items(), key=lambda x: -x[1]))

HTML = f'''<section class="speed viz-root" id="reaction-speed">
<style>
.speed {{
  color-scheme: light;
  --surface-1:#fcfcfb; --plane:#f9f9f7;
  --text-primary:#0b0b0b; --text-secondary:#52514e; --muted:#898781;
  --grid:#e1e0d9; --axis:#c3c2b7; --border:rgba(11,11,11,0.10);
  --series-1:#2a78d6; --series-2:#008300;
  font-family:system-ui,-apple-system,"Segoe UI",sans-serif;
  color:var(--text-primary); background:var(--plane);
  padding:clamp(16px,3vw,28px); border-radius:12px;
}}
@media (prefers-color-scheme: dark) {{
  :root:where(:not([data-theme="light"])) .speed {{
    color-scheme: dark;
    --surface-1:#1a1a19; --plane:#0d0d0d;
    --text-primary:#ffffff; --text-secondary:#c3c2b7; --muted:#898781;
    --grid:#2c2c2a; --axis:#383835; --border:rgba(255,255,255,0.10);
    --series-1:#3987e5; --series-2:#008300;
  }}
}}
:root[data-theme="dark"] .speed {{
  color-scheme: dark;
  --surface-1:#1a1a19; --plane:#0d0d0d;
  --text-primary:#ffffff; --text-secondary:#c3c2b7; --muted:#898781;
  --grid:#2c2c2a; --axis:#383835; --border:rgba(255,255,255,0.10);
  --series-1:#3987e5; --series-2:#008300;
}}
.speed *{{box-sizing:border-box}}
.speed h2{{font-size:clamp(20px,2.6vw,26px);margin:0 0 6px;letter-spacing:-.02em}}
.speed .hero{{font-size:clamp(38px,6vw,52px);font-weight:650;line-height:1.05;margin:10px 0 6px;letter-spacing:-.03em}}
.speed .sub{{color:var(--text-secondary);font-size:15px;line-height:1.55;max-width:68ch;margin:0 0 4px}}
.speed .card{{background:var(--surface-1);border:1px solid var(--border);border-radius:10px;padding:16px 14px 8px;margin:16px 0}}
.speed .card h3{{font-size:15px;margin:0 0 2px;font-weight:600}}
.speed .card p.cap{{color:var(--text-secondary);font-size:13px;margin:0 0 10px;line-height:1.5}}
.speed .scroll{{overflow-x:auto}}
.speed svg.chart{{display:block;width:100%;height:auto;min-width:520px;overflow:visible}}
.speed .grid{{stroke:var(--grid);stroke-width:1}}
.speed .axis{{stroke:var(--axis);stroke-width:1}}
.speed .zero{{stroke:var(--axis);stroke-width:1}}
.speed .ref{{stroke:var(--muted);stroke-width:1;opacity:.7}}
.speed .reflab{{fill:var(--muted);font-size:11px}}
.speed .tick{{fill:var(--muted);font-size:11px;font-variant-numeric:tabular-nums}}
.speed .axlab{{fill:var(--text-secondary);font-size:12px}}
.speed .dlab{{fill:var(--text-secondary);font-size:12px;font-weight:600}}
.speed .blab{{fill:var(--text-secondary);font-size:12px;font-weight:600;font-variant-numeric:tabular-nums}}
.speed .ln{{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}}
.speed .s1{{stroke:var(--series-1)}} .speed .s2{{stroke:var(--series-2)}}
.speed .s1f{{fill:var(--series-1)}} .speed .s2f{{fill:var(--series-2)}}
.speed .dot{{stroke:var(--surface-1);stroke-width:2}}
.speed .band{{fill:var(--series-1);opacity:.10}}
.speed .hbar,.speed .cbar{{fill:var(--series-1);transition:opacity .12s}}
.speed .hbar:hover,.speed .cbar:hover,.speed .hbar:focus,.speed .cbar:focus{{opacity:.72;outline:none}}
.speed .medline{{stroke:var(--series-2);stroke-width:2}}
.speed .lead{{fill:none;stroke:var(--axis);stroke-width:1}}
.speed .hit{{fill:transparent}}
.speed .chair{{stroke:var(--muted);stroke-width:1}}
.speed .legend{{display:flex;gap:16px;flex-wrap:wrap;align-items:center;margin:2px 0 10px;font-size:13px;color:var(--text-secondary)}}
.speed .legend span{{display:inline-flex;align-items:center;gap:7px}}
.speed .key{{width:16px;height:2px;border-radius:2px;flex:none}}
.speed .tip{{position:fixed;pointer-events:none;z-index:9;background:var(--surface-1);border:1px solid var(--border);
  border-radius:8px;padding:8px 10px;font-size:12px;color:var(--text-secondary);box-shadow:0 4px 14px rgba(0,0,0,.13);opacity:0;transition:opacity .1s}}
.speed .tip b{{color:var(--text-primary);font-size:13px;font-variant-numeric:tabular-nums}}
.speed .tip .r{{display:flex;align-items:center;gap:7px;margin-top:3px}}
.speed details{{margin:14px 0 0}}
.speed summary{{cursor:pointer;font-size:13px;color:var(--text-secondary);padding:6px 0}}
.speed table{{border-collapse:collapse;width:100%;font-size:13px;margin-top:8px}}
.speed th,.speed td{{text-align:right;padding:6px 10px;border-bottom:1px solid var(--border);font-variant-numeric:tabular-nums}}
.speed th:first-child,.speed td:first-child{{text-align:left}}
.speed th{{color:var(--text-secondary);font-weight:600}}
.speed .note{{font-size:12.5px;color:var(--text-secondary);line-height:1.6;border-left:2px solid var(--axis);padding:2px 0 2px 12px;margin:14px 0 0}}
.speed .warn{{background:var(--surface-1);border:1px solid var(--border);border-left:3px solid #eda100;border-radius:8px;padding:12px 14px;font-size:13px;color:var(--text-secondary);line-height:1.6;margin:12px 0}}
</style>

<h2>How fast does a stock move after Trump posts about it?</h2>
<div class="hero">The first minute is<br>a coin flip</div>
<p class="sub">Measured on real Polygon 1-minute bars for <b>n&nbsp;=&nbsp;{n}</b> post–company observations
(from <b>{N_DISTINCT}</b> distinct posts) that landed while the market was open. Each move is signed in the
direction the post pushed — praise up, attack down — so a positive number means the stock moved the way
the post argued.
<b>The median first-minute move is {fm['median']:+.2f}%</b>, and only <b>{fm['pos_share']:.0f}%</b> of posts
moved the right way in that minute — no better than chance. The mean move does reach
<b>{R['mean_30']:+.3f}%</b> by +30&nbsp;min ({hit['30']['pct']:.0f}% hit rate), but it accumulates
<i>gradually</i> — most of it appears between +5 and +15&nbsp;min, not on impact.</p>

<div class="warn"><b>Sample-size warning — read this before the charts.</b> Of the
<b>{R['n_in_hours']}</b> in-market-hours post–company pairs in the dataset, only <b>{n}</b> could be
measured, and those come from just <b>{N_DISTINCT}</b> distinct posts. Polygon's free tier serves roughly
2 years of minute data, so <b>{OOW}</b> ticker-days (everything before ~mid-2024) return
<i>NOT_AUTHORIZED</i> and cannot be priced at all — that alone removes {R['drops'].get('no_data', 0)}
observations. This is a small, recency-skewed sample and the observations are not independent
(see the method note). Treat every number here as indicative, not conclusive.</div>

<div class="card">
  <h3>Reaction curve — the move by minute</h3>
  <p class="cap">Mean and median cumulative directional move vs. the last price before the post.
  The shaded band is the 25th–75th percentile <i>across posts</i> at each minute — it is the spread of
  individual reactions, not a confidence interval on the mean. n = {n} posts.</p>
  <div class="legend">
    <span><i class="key" style="background:var(--series-1)"></i>Mean</span>
    <span><i class="key" style="background:var(--series-2)"></i>Median</span>
    <span><i class="key" style="background:var(--series-1);opacity:.25"></i>25th–75th pct</span>
  </div>
  <div class="scroll">{chart1}</div>
</div>

<div class="card">
  <h3>First-minute move — the distribution behind the average</h3>
  <p class="cap">Each post's move during the minute it was posted, signed in the post's direction.
  The spread is what the mean hides: only <b>{fm['pos_share']:.0f}%</b> of posts moved the right way —
  a coin flip — and the median is <b>{fm['median']:+.2f}%</b>, i.e. the typical post moves the stock
  nothing at all in its first minute. The <b>{fm['mean']:+.3f}%</b> mean is carried by a handful of
  outliers, not by consistency. Range {fm['min']:+.2f}% to {fm['max']:+.2f}%, SD {fm['stdev']:.3f}%. n = {fm['n']}.</p>
  <div class="scroll">{chart2}</div>
</div>

<div class="card">
  <h3>Speed of capture — how much is already there</h3>
  <p class="cap">Mean move at each horizon as a share of the mean move at +30 min. <b>This is not a
  monotonic build-up:</b> the small first-minute blip ({cap['0']['share_of_30_mean']:.0f}%) partly
  <i>fades</i> by +5 min ({cap['5']['share_of_30_mean']:.0f}%) before the move actually accumulates between
  +5 and +15 min. These are ratios of two very small means ({cap['0']['mean_move']:+.3f}% over
  {R['mean_30']:+.3f}%), so treat the percentages as a shape, not a precise claim. n = {n}.</p>
  <div class="scroll">{chart3}</div>
</div>

<details>
  <summary>Table view — every plotted value, and the ticker mix</summary>
  <table>
    <caption class="cap" style="text-align:left;padding:6px 0">Directional move by horizon (n = {n} observations from {N_DISTINCT} posts)</caption>
    <thead><tr><th>Horizon</th><th>Mean move</th><th>Share of +30 mean</th><th>Hit rate</th><th>n</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <table>
    <caption class="cap" style="text-align:left;padding:10px 0 6px">Observations per ticker — the concentration limitation</caption>
    <thead><tr><th>Ticker</th><th>Observations</th></tr></thead>
    <tbody>{tick_rows}</tbody>
  </table>
</details>

<p class="note"><b>Method &amp; honest limitations.</b>
<b>Source:</b> post text/timestamps from the Matt Stiles Trump Truth Social Archive (CC0);
prices from Polygon.io 1-minute aggregates, regular hours only.
<b>Sample:</b> {R['n_in_hours']} of the dataset's praise/attack post–company pairs landed Mon–Fri
9:30–16:00 ET; {n} could be priced ({drop_txt}).
<b>Effective n is smaller than {n}.</b> Three separate reasons: (1) the {n} observations come from only
<b>{N_DISTINCT} distinct posts</b> — {N_MULTI} posts name several companies at once (one names {MAX_MULTI}),
and those rows react to the same sentence at the same instant; (2) the ticker mix is concentrated —
{R['by_ticker'][0][1]} of {n} are {esc(R['by_ticker'][0][0])} alone; (3) same-day posts on one ticker
share overlapping windows.
<b>Measurement floor:</b> {N_ZERO} observations show a first-minute move of exactly zero — on the
low-priced names in this sample ({esc(R['by_ticker'][0][0])} and {esc(R['by_ticker'][1][0])} traded near
$10–13) one tick is already ~0.08%, so "no move" is partly the price grid, not just calm. Those zeros sit
exactly at the median, which is why the median first-minute move is {fm['median']:+.2f}%.
<b>The first-minute window straddles the post:</b> the reference is the previous bar's close (up to ~60s
<i>before</i> the post) and minute 0 is the post-minute's close (up to ~60s <i>after</i>), so it brackets
the moment rather than starting exactly at it. This makes the "no reaction" finding conservative, not overstated.
{h60_txt}
<b>Split:</b> {R['by_sentiment']['PRAISE']} praise / {R['by_sentiment']['ATTACK']} attack — too thin to split the curve
by sentiment with any confidence, so the headline curve combines them.
<b>No counterfactual:</b> this measures the move around the post, not the move <i>caused</i> by it —
there is no market/sector benchmark subtracted, and no control for news arriving at the same moment.
A hit rate near 50% is what a coin flip looks like; the mean is carried by a few large moves, not by consistency.</p>

<script>
(function(){{
  var root=document.getElementById('reaction-speed'); if(!root) return;
  var tip=document.createElement('div'); tip.className='tip'; root.appendChild(tip);
  function show(x,y,rows){{
    tip.textContent='';
    rows.forEach(function(r){{
      var d=document.createElement('div'); d.className='r';
      if(r.color){{var k=document.createElement('i'); k.className='key'; k.style.background=r.color; d.appendChild(k);}}
      var b=document.createElement('b'); b.textContent=r.value; d.appendChild(b);
      var s=document.createElement('span'); s.textContent=r.label; d.appendChild(s);
      tip.appendChild(d);
    }});
    tip.style.opacity=1;
    var w=tip.offsetWidth,h=tip.offsetHeight;
    tip.style.left=Math.min(window.innerWidth-w-8,Math.max(8,x+14))+'px';
    tip.style.top=Math.max(8,y-h-12)+'px';
  }}
  function hide(){{tip.style.opacity=0;}}
  var cs=getComputedStyle(root);
  var C1=cs.getPropertyValue('--series-1'),C2=cs.getPropertyValue('--series-2');
  // chart 1 crosshair
  var c1=document.getElementById('c1'), cross=document.getElementById('c1cross');
  if(c1){{
    c1.querySelectorAll('.hit').forEach(function(h){{
      function on(e){{
        var r=h.getBoundingClientRect(), cx=r.left+r.width/2;
        var ln=cross.querySelector('.chair');
        ln.setAttribute('x1',+h.getAttribute('x')+ +h.getAttribute('width')/2);
        ln.setAttribute('x2',+h.getAttribute('x')+ +h.getAttribute('width')/2);
        cross.hidden=false;
        show(cx,r.top+30,[
          {{value:(+h.dataset.mean>=0?'+':'')+(+h.dataset.mean).toFixed(3)+'%',label:'mean',color:C1}},
          {{value:(+h.dataset.median>=0?'+':'')+(+h.dataset.median).toFixed(3)+'%',label:'median',color:C2}},
          {{value:'+'+h.dataset.off+' min',label:'n = '+h.dataset.n+' posts'}}
        ]);
      }}
      h.addEventListener('pointermove',on); h.addEventListener('pointerenter',on);
      h.addEventListener('pointerleave',function(){{hide();cross.hidden=true;}});
    }});
  }}
  // chart 2 + 3 per-mark
  root.querySelectorAll('.hbar').forEach(function(b){{
    function on(){{var r=b.getBoundingClientRect();
      show(r.left+r.width/2,r.top,[
        {{value:b.dataset.c+(b.dataset.c==='1'?' post':' posts'),label:'in this bin'}},
        {{value:(+b.dataset.lo).toFixed(2)+'% to '+(+b.dataset.hi).toFixed(2)+'%',label:'first-minute move',color:C1}}
      ]);}}
    b.addEventListener('pointerenter',on); b.addEventListener('focus',on);
    b.addEventListener('pointerleave',hide); b.addEventListener('blur',hide);
  }});
  root.querySelectorAll('.cbar').forEach(function(b){{
    function on(){{var r=b.getBoundingClientRect();
      show(r.left+r.width/2,r.top,[
        {{value:(+b.dataset.s).toFixed(0)+'%',label:'of the +30 min mean',color:C1}},
        {{value:(+b.dataset.m>=0?'+':'')+(+b.dataset.m).toFixed(3)+'%',label:'mean move at +'+b.dataset.h+' min'}}
      ]);}}
    b.addEventListener('pointerenter',on); b.addEventListener('focus',on);
    b.addEventListener('pointerleave',hide); b.addEventListener('blur',hide);
  }});
}})();
</script>
</section>
'''

open(os.path.join(HERE, "speed_section.html"), "w", encoding="utf-8").write(HTML)
print(f"wrote speed_section.html  n={n}  in_hours={R['n_in_hours']}  out_of_window_tickerdays={OOW}")
print(f"first-min mean {fm['mean']:+.4f}% median {fm['median']:+.4f}% hit {fm['pos_share']:.1f}%")
print("capture:", {h: round(cap[str(h)]["share_of_30_mean"], 1) for h in HOR})
print("hit rate:", {h: round(hit[str(h)]["pct"], 1) for h in HOR})
