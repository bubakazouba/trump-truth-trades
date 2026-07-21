# Trump Truth Social → Stock Moves

An empirical study of what happens to a company's stock after Donald Trump posts about it
on Truth Social: does *praising* a company move its stock up, does *attacking* one move it
down, and **how fast** does the market react?

**Live dashboard:** https://bubakazouba.github.io/trump-truth-trades/

This repo contains the full pipeline and **all underlying data** — the matched posts, the
per-company stance classifications (with verbatim quotes), the raw minute-level price data,
and every analysis script — so the dashboard's numbers can be independently audited and
re-run. Nothing on the dashboard is fabricated or estimated; every figure traces to a file here.

## Data sources

- **Posts:** Donald Trump's Truth Social posts (`@realDonaldTrump`).
- **Prices:** [Polygon.io](https://polygon.io) — 1-minute intraday OHLCV bars, and daily closes.
  Raw pulls are in `data/polygon_bars/` (`poly_<TICKER>_<DATE>.json`).
- **Classifications:** produced by an LLM pass (Anthropic Claude, Sonnet) — see methodology.

## Methodology (how the numbers are produced)

1. **Company detection** (`scripts/companies.py`): a curated map of company → (US-listed ticker,
   regex keyword patterns, e.g. `\bnvidia\b`, `\bjensen huang\b`). Each Trump post is scanned for
   these patterns to produce `(post, company)` candidate **pairs**. → `data/pairs.jsonl`.
2. **Stance classification** (`scripts/classify.py`): every pair is labeled by Claude (Sonnet) for
   Trump's stance **toward that specific company** in that post — `PRAISE` / `ATTACK` / `NEUTRAL` —
   plus a `substantive` flag (materially about the company vs. an incidental name-drop / reflexive
   "Fake News CNN!" tag) and a short verbatim `quote` showing the stance. The exact labeling prompt
   is in `classify.py`. Raw model output: `data/classified.jsonl`.
3. **Pricing / event study** (`scripts/price_and_analyze.py`, `event_study.py`, `study.py`): for each
   post, pull the stock's price around the post time from Polygon, compute the **next-day return**
   (`nd_ret`) and **one-week return** (`wk_ret`) from the entry close, and flag whether the post was
   during market hours (`inhours`). → `data/posts_classified.json` (the joined final dataset).
4. **Reaction speed** (`scripts/speed_fetch.py`, `speed_analyze.py`, `speed_build.py`): for
   in-market-hours posts, pull 1-minute bars and measure how quickly the stock moves after the post
   (first-minute move, cumulative curve, how much of the day-1 move is captured in the first N
   minutes). → `data/speed_results.json`, `data/speed_fetch_log.json`.
5. **Aggregation & page build** (`scripts/aggregate.py`, `build_page.py`): roll the per-post rows into
   the summary stats and charts, then bake them into `index.html`. → `data/aggregates.json`,
   `data/stats.json`.

## Data files

| File | What it is |
|---|---|
| `data/posts_classified.json` | **The dataset.** 635 records: `id, created_at, company, ticker, text, sentiment, substantive, quote, entry_date, entry_close, et_time, inhours, nd_ret, wk_ret`. (470 ATTACK, 165 PRAISE.) |
| `data/pairs.jsonl` | Every matched `(post, company)` pair before classification (the raw matched-post set). |
| `data/classified.jsonl` | Raw LLM classification output (stance + substantive + quote per pair). |
| `data/polygon_bars/` | Raw Polygon 1-minute OHLCV pulls, one file per `(ticker, date)`. |
| `data/speed_results.json`, `data/speed_fetch_log.json` | Intraday reaction-speed analysis (n=73 on 1-min bars) + fetch log. |
| `data/aggregates.json`, `data/stats.json` | Aggregated figures + statistical breakdowns that feed the dashboard. |
| `data/drops.json` | Notable individual cases. |

## Reproducing

The scripts run in order: `companies.py` (config) → build pairs → `classify.py` (needs the Claude
CLI) → `price_and_analyze.py` (needs a Polygon API key; raw pulls are already cached in
`data/polygon_bars/`) → `speed_*.py` → `aggregate.py` / `build_page.py`. The cached Polygon data and
classification outputs are committed, so the analysis and page can be rebuilt from the checked-in
files without re-fetching or re-classifying.

## Honest caveats

- **Correlation, not proof of causation** — many things move a stock on a given day; a single post is
  rarely the only driver. Returns are raw (not market/sector-adjusted).
- **Classification is model-judgment**, not ground truth — the `sentiment`/`substantive` labels are
  Claude's calls; the prompt and the verbatim quotes are provided so you can spot-check them.
- Company coverage is limited to the tickers in `companies.py` (US-listed / ADR-tradable with Polygon
  data); posts about companies outside that list aren't captured.
