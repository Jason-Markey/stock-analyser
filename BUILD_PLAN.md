# Sector Skew AU — Build Plan for a Personal Stock-Analysis System

*Drafted by fable · 26 Aug 2026 (costs revised same day) · For Jason — US + ASX, start on free data, cloud daily run, small book.*

*A daily, self-running dashboard that narrows the US and ASX markets down to a short list of candidates, with entry zones, stops, and horizon-based exit rules. Decision support, not financial advice.*

---

## 1. What the system does, end to end

Every trading day, before you wake up, a scheduled cloud job:

1. **Downloads end-of-day data** — prices and volume for ~300 US names and ~150 ASX names, plus EOD options chains for the liquid US names.
2. **Computes two kinds of signal**:
   - **Price** = what already happened (returns over 1 day / 1 week / 1 month, relative strength vs index, volume vs average).
   - **Conviction** = what the crowd is paying for next. In the US this is 25-delta options skew (are people paying up for calls or puts?). On the ASX, where options data is thin, it is a substitute conviction score built from short interest, dollar-volume flow, breadth, and momentum quality.
3. **Looks for disagreement.** The edge claimed by the system you saw is exactly this: when price says one thing and positioning says another. A stock that has fallen 15% while the options crowd is paying up for calls is the interesting case.
4. **Ranks everything deterministically** — same formulas every day, no discretion — into theme tables, a treemap, a scatter, and a Top-15 action list.
5. **Turns the best candidates into a trade plan**: an entry zone, a confirmation trigger, an invalidation stop, and a horizon classification (1M / 3M / 6M / 12M / hold) with per-horizon profit-take and trailing-stop rules.
6. **Publishes one self-contained HTML file** you open with your coffee. Ten minutes, done.

You never trade off the dashboard blindly. It exists to shrink 450 names to 3–6 positions worth holding.

---

## 2. Signal engine spec

All metrics computed from adjusted EOD data. Every formula below is deterministic — same inputs, same outputs, every day.

### 2.1 Universe

- **US**: top ~12 names by average daily dollar volume per theme basket, ~25 baskets → ~300 names. Refresh membership monthly.
- **ASX**: ASX 200 constituents plus any watchlist additions, grouped into ~12 baskets → ~150 names.
- Minimum liquidity floor: 20-day average dollar volume ≥ US$5M (US) / A$1M (ASX). Below the floor, a name is displayed hollow and excluded from ranking.

### 2.2 Price metrics (per name, both markets)

| Metric | Formula |
|---|---|
| `ret_1d`, `ret_1w`, `ret_1m` | `close / close[n] − 1` for n = 1, 5, 21 trading days |
| `rel_1w`, `rel_1m` | `ret − index_ret` (index = SPY for US, STW/XJO for ASX) |
| `vol_ratio` | today's dollar volume ÷ 20-day average dollar volume |
| `dollar_flow` | today's dollar volume, also expressed in bps of total market dollar volume |
| `trend` | "improving" if `rel_1w > rel_1m / 4`, else "fading" (is the recent leg stronger than the run-rate?) |
| `dist_ma20`, `dist_ma50` | `close / SMA(n) − 1` — used by the entry engine |

### 2.3 Theme baskets

Custom baskets, finer than GICS. Weight each name by 20-day average dollar volume, **capped at 25% per name**, renormalised.

- **US examples**: AI infra/datacenter, Semis, Semi equipment, Memory, Software, Quantum, Space/defence, Nuclear/uranium, Gold/silver miners, Oil & gas, Crypto miners, Biotech, Banks, Homebuilders, Consumer staples.
- **ASX examples**: Iron ore (BHP, RIO, FMG, MIN), Gold miners (NST, EVN, GMD, PRU), Uranium (PDN, BOE, DYL), Lithium/battery (PLS, IGO, LTR), Banks (CBA, NAB, WBC, ANZ, MQG), Biotech/health (CSL, PME, RMD, COH), Tech/WAAAX (WTC, XRO, NXT, TNE), Energy (WDS, STO), Retail/consumer (JBH, WES, LOV), REITs (GMG, SCG), Defence/industrial (ASB, CDA, DRO), Travel (QAN, FLT, WEB).

Baskets live in a single YAML file so editing themes never touches code.

**Per-basket metrics**: weighted `rel_1m`, `rel_1w`, `ret_1d`, `vol_ratio`; `flow_bps` (basket dollar volume ÷ total market dollar volume, in bps, vs its own 20-day average); **breadth** = % of members with `rel_1w > 0`; trend label as above.

### 2.4 US conviction: 25Δ skew

From EOD chains, per name:

1. Pick the monthly expiry nearest to 30 days out (21–45 day window).
2. Find the put closest to −0.25 delta and the call closest to +0.25 delta (use provided greeks; else Black-Scholes from mid and a rate assumption).
3. `skew = IV(25Δ put) − IV(25Δ call)`, in vol points. **Positive = puts bid (protection). Negative = calls bid (upside).**
4. **Clean-chain filter**: require both legs to have bid > 0, spread ÷ mid ≤ 25%, and total chain open interest at that expiry ≥ 1,000. Fail any test → mark the name "hollow: thin chain, don't trust the number" and exclude from skew ranking (price metrics still shown).
5. `skew_vs_sector = skew − median(skew of clean names in same basket)` — this removes the baseline (gold miners always skew differently to software) and isolates the *unusual* positioning.
6. Store daily history so you also get `skew_change_1w`.

### 2.5 ASX conviction substitute (be explicit: this is NOT skew)

ASX single-stock options are thin and quality EOD chain data is expensive, so the ASX column labelled **"Conviction"** is a composite score in [−1, +1], built from four free/cheap signals:

```
conviction = 0.35 × short_signal + 0.25 × flow_signal + 0.20 × breadth_signal + 0.20 × momo_quality
```

- `short_signal`: from ASIC's daily aggregated short-position CSV (free, ~T+4 lag). Score = z-score of the **change** in % of shares shorted over 2 weeks, sign-flipped (shorts covering = bullish, shorts building = bearish), clipped to [−1, 1]. A high absolute short base (>8%) with a falling trend flags squeeze potential.
- `flow_signal`: z-score of the name's 5-day dollar-volume share of its basket vs its 60-day norm, clipped. Money arriving quietly is the tell.
- `breadth_signal`: the name's basket breadth mapped from [0%, 100%] to [−1, +1] — a rising tide check.
- `momo_quality`: +1 if up-days over the past month averaged higher volume than down-days, −1 if the reverse (accumulation vs distribution), scaled by magnitude, clipped.

Optional later upgrade: broker consensus EPS-revision momentum if a cheap source appears. The dashboard must label US conviction "25Δ skew" and ASX conviction "composite" — never pretend they are the same measurement.

### 2.6 Asymmetry score (the action-list ranker)

For each clean name, using `conv` = −`skew_vs_sector` normalised to [−1, 1] for US (so positive = bullish positioning) or the ASX composite:

```
asymmetry = (−rel_1m_z) × 1.0        # fell hard vs index (z-scored within market)
          + conv × 1.5               # crowd leans bullish vs sector peers
          + bounce_bonus             # +0.5 if ret_1d > 0 AND vol_ratio > 1.3
          − crowding_penalty         # −0.5 if rel_1m_z > +1 AND conv > 0.5 (already chased)
```

Only names with `rel_1m < 0` and `conv > 0` are eligible for the **FRESH LOOK** label; names with `rel_1m > 0` and `conv > 0` are labelled **MOMENTUM — crowded**. Top 15 by score, per market, published daily.

### 2.7 "Today's read" — five auto-written sentences

Deterministic templates filled from the numbers, e.g.:

1. Tape: "SPY {ret_1d:+.1%}, QQQ {…}, IWM {…}, VXX {…} — {risk-on/risk-off/mixed by simple sign rules}." (ASX version: XJO, XSO, gold, AUD.)
2. Strongest theme: highest `rel_1w` with breadth ≥ 60%.
3. Fading leader: highest `rel_1m` whose trend flipped to "fading".
4. Caution flag: any watchlist name whose skew jumped > +3 vol points in a week (or ASX conviction dropped > 0.5).
5. Big-picture flow: basket with the largest `flow_bps` change vs its average.

---

## 3. The four-quadrant framework and the action list

Every clean name is plotted: **x = return (1D/1W/1M selectable), y = conviction** (skew sign-flipped so up = bullish). Watchlist names starred.

| Quadrant | Price | Positioning | Read | Rule |
|---|---|---|---|---|
| **FEAR** | falling | protection bid | Crowd agrees it's bad | Avoid. No entries. |
| **HEDGED RALLY** | rising | protection bid | Rally people don't trust | Hold if owned, tighten stop to 1× ATR below MA20. No new entries. |
| **CONTRARIAN BID** | falling | upside bid | Price and money disagree — the opportunity | Feed into the action list and entry engine. |
| **CHASE** | rising | upside bid | Trend confirmed but crowded | New entries only on pullback-to-MA20 setups; half size. |

The **action list** is the CONTRARIAN BID quadrant sorted by asymmetry score, top 15 per market, each row showing: score, label, `rel_1m`, conviction, `vol_ratio`, bounce flag, and — once Phase 4 is built — the computed entry zone and stop. This is the only part of the dashboard that generates trades; everything else is context.

---

## 4. Entry guide logic (deterministic)

A FRESH LOOK candidate never becomes a buy on the day it appears. It must pass a **confirmation trigger**, then gets a **staged entry** and a pre-computed **invalidation stop**.

**Confirmation trigger** (either, evaluated on EOD data — you act next morning):
- **Trigger A — volume reversal**: first day with `ret_1d > 0` AND `vol_ratio ≥ 1.3` AND close in the top half of the day's range.
- **Trigger B — reclaim**: close back above the 20-day SMA after ≥ 5 days below it.

**Entry zone** (after trigger):
- Zone = [trigger-day low, trigger-day close]. Stage in: **half position** at market next open if it opens inside the zone (or limit at zone top), **second half** only after a second up-day or a higher low. If price gaps > 3% above the zone, do not chase — the name stays on watch and re-triggers or dies.
- Candidate expires if untriggered within 10 trading days of first appearing.

**Invalidation stop** (set before entry, never widened):
- `stop = min(trigger-day low, recent swing low) − 0.5 × ATR(14)`, floored so risk is never more than 12% below entry (if the formula wants a wider stop, the position doesn't get taken).
- **Position size from the stop**: risk per trade = 1.5% of book. Size = (book × 0.015) ÷ (entry − stop). With a small book this naturally caps you at 3–6 concurrent positions. Round to whole shares; skip any trade where minimum brokerage exceeds 0.5% of position value (relevant on ASX — see costs).

---

## 5. Exit framework across horizons

Each entered position is classified **on entry day** by what fired, and carries that horizon unless the thesis-broken rule fires first.

**Classification rules (checked top-down, first match wins):**

| Class | Rule at entry | Horizon |
|---|---|---|
| **Contrarian swing** | FRESH LOOK signal, basket trend "fading" or neutral | **1–3 months** |
| **Theme rider** | FRESH LOOK or CHASE-pullback, AND basket breadth ≥ 60% AND basket trend "improving" | **6–12 months** |
| **Compounder** | Theme rider that, at the 6-month review, still has positive `rel_1m`, improving basket, and (manual once-off check) profitable with revenue growth | **Hold indefinitely** |

**Per-horizon rules:**

| Horizon | Profit-take | Trailing stop | Review |
|---|---|---|---|
| **1M** | Sell half at +8% vs entry, rest at +15% or horizon end | 2 × ATR(14) below highest close since entry | Flat by day ~22 regardless |
| **3M** | Sell half at +15%, let rest run | 2.5 × ATR below highest close | At 3 months: if `rel_1m > 0` and basket improving, promote to 6M; else exit |
| **6M** | Sell one-third at +25% | Close below 50-day SMA for 3 consecutive days | Promote to 12M on same test |
| **12M** | Sell one-third at +40% | Close below 100-day SMA for 5 consecutive days | Crossing 12 months matters for the CGT discount — if a position is within 4 weeks of the 12-month mark and only the trailing stop (not thesis-broken) has fired, the dashboard flags it for a deliberate hold/sell decision rather than auto-signalling exit |
| **Hold** | None automatic | Close below 200-day SMA for 5 days, or demotion at quarterly review | Quarterly: still profitable, still growing, basket not in FEAR |

**Thesis-broken override — exits everything, any horizon, next open:**
- Initial invalidation stop hit (never moved down), OR
- Name enters the FEAR quadrant (negative `rel_1m` AND protection bid / conviction < −0.3) for 3 consecutive days, OR
- Basket breadth collapses below 30% while the name is below its MA50.

**Churn guard**: maximum 2 new entries per week; a sold name cannot be re-entered for 10 trading days.

---

## 6. Build phases

All Python. One repo, one `config.yaml` (universes, baskets, thresholds, API keys via env vars). The data layer is a thin interface (`get_prices(tickers, start)`, `get_chain(ticker, date)`) with swappable backends, so changing vendor never touches signal code.

**Phase 0 — Prototype (2–3 evenings).** US only, free data (`yfinance`), one script, run by hand. Computes §2.2 price metrics and basket tables for ~100 names, prints the theme table and a crude action list (price-only score) to terminal or a basic HTML file.
*Accept when:* you can run one command and get a ranked theme table + top-15 list that matches sanity checks against a finance site.

**Phase 1 — Daily cloud run + dashboard (2 weekends).** Move to GitHub Actions (free tier): cron at 21:15 UTC (≈ 7:15am AEST, after US close), workflow runs the pipeline and writes `dashboard_YYYY-MM-DD.html` — a single self-contained file (inline CSS/JS, embedded JSON, Plotly for treemap/scatter). Publish via a private GitHub Pages repo, or regenerate into a Claude Cowork-hosted HTML artifact. Store rolling signal history as parquet committed to the repo (fine at this size). Includes "Today's read" sentences.
*Accept when:* three consecutive mornings the dashboard is waiting for you without intervention, and a failed API call produces an error email, not a silently stale page.

**Phase 2 — Options skew layer (2–3 weekends).** Add the EOD chain backend — first choice Tradier (free API access with a funded US brokerage account; the account admin is the only cost), fallback Polygon.io Options Starter (~US$29/mo) if the account route stalls — then the 25Δ skew computation, clean-chain filter, skew-vs-sector, treemap colouring, the real four-quadrant scatter, and the full asymmetry score. Backfill enough history for `skew_change_1w`.
*Accept when:* skew for 10 well-known names roughly matches a free reference (e.g. eyeballing a chain), thin names show hollow, and the action list reorders sensibly when you perturb inputs in a test.

**Phase 3 — ASX module (2 weekends).** Add ASX price backend (yfinance with `.AX` tickers — free; see §7 for the optional EODHD upgrade), the ASIC short-interest downloader/parser, the composite conviction score, ASX baskets, and a second dashboard section (or tab) that runs after ASX close (~16:15 AEST job, or fold into one morning run using the previous ASX session — acceptable at EOD granularity). Clearly label conviction as "composite".
*Accept when:* ASX section renders daily with short-interest data no more than ~5 days stale, and the top-15 ASX list contains no names below the liquidity floor.

**Phase 4 — Entry/exit engine + journal (2–3 weekends).** Implement §4 triggers, entry zones, stops, position sizing, and §5 classification/exits as a state machine over a `positions.json` you edit when you actually trade. Dashboard gains: "Triggered today" panel, per-position status cards (horizon, stop level, next rule that could fire), and an append-only trade journal CSV (entry/exit, class, R multiple, which rule fired).
*Accept when:* a dry-run paper position walks correctly through trigger → entry → trailing stop → exit over two weeks with no manual correction.

**Phase 5 — Backtest & tuning (optional, ongoing).** Replay the stored parquet history through the signal + entry/exit engine. Measure hit rate and average R by quadrant, class, and market. Tune at most one threshold at a time, and only with ≥ 30 trades of evidence.
*Accept when:* you can state, with numbers, whether FRESH LOOK entries have beaten buying the index over the sample — and you believe the answer either way.

---

## 7. Costs — start free

**Decision (26 Aug 2026): the whole system starts at US$0/month.** Paid data enters only if and when a specific limitation actually bites.

**The free stack (Phases 0, 1, 3, 4):**

| Item | Source | US$/month |
|---|---|---|
| US EOD prices | yfinance | 0 |
| ASX EOD prices | yfinance (`.AX` tickers) | 0 |
| ASX short interest | ASIC daily short-position reports (public CSV) | 0 |
| Compute + hosting | GitHub Actions + private Pages / Cowork artifact | 0 |

**Phase 2 (US options skew) — the one place data isn't free-by-default:**

| Route | Cost | Notes |
|---|---|---|
| **Tradier brokerage API** (first choice) | $0/mo | Free EOD chains + greeks with a funded US brokerage account. The "cost" is account-opening admin from Australia — accepted; Jason will do the setup when Phase 2 arrives. |
| Polygon.io Options Starter (fallback) | ~$29/mo | If the Tradier account route stalls, this is the swap-in — the data-layer interface means changing vendor touches nothing else. |

**Optional add-on, only if needed later — EODHD All-World (~US$20/mo):** professionally maintained EOD prices for ASX and global markets — adjusted for corporate actions (splits, consolidations, special dividends), delisted-stock history, and a stable API with an SLA, versus yfinance which scrapes Yahoo and can silently break, misadjust, or rate-limit. Add it only if the free ASX feed proves unreliable in practice (stale prices, bad adjustments, failed runs) — the symptom to watch for is the dashboard disagreeing with your broker's charts.

**Bottom line: $0 now, $0 at Phase 2 if the Tradier admin goes through, ~$29/mo worst case, +$20/mo only if ASX data quality forces it.**

Brokerage reality check: US trading via Stake/IBKR is near-zero; ASX trades cost ~A$3–10 each way. On a small ASX position that's up to ~0.5% round trip — another reason for the churn guard and the minimum-position rule in §4. (A funded Tradier account opened for the data can also simply hold a token balance — it doesn't have to become your trading broker.)

---

## 8. Honest limitations

- **The Instagram claim is marketing.** "$144k in 6 months" is one person's unaudited, survivorship-selected result. People whose skew dashboards lost money don't make reels. Judge this system only by your own Phase 5 numbers.
- **Skew is a crowd signal, not a crystal ball.** It tells you what option buyers are paying for; crowds are often wrong, and skew can reflect hedging mechanics, earnings timing, or a single large trade rather than "smart money".
- **Small samples everywhere.** 15 names a day, 2 entries a week — it takes a year to accumulate statistically meaningful evidence. Resist tuning thresholds off five trades.
- **The ASX conviction score is a substitute**, built from slower, coarser inputs (short data lags ~4 days). Expect it to be weaker than US skew and size accordingly.
- **EOD data means you're always acting a day late** by design. That's fine for the 1M+ horizons this targets; it's fatal for day trading — don't drift into it.
- **Tax**: Australian CGT applies; positions held ≥ 12 months get the 50% CGT discount, which is why the 12M review deliberately flags near-anniversary positions. Frequent 1M swings are taxed at full marginal rate — factor that into whether the 1M class earns its keep. This plan is not tax or financial advice; a session with an accountant is cheaper than getting it wrong.
- **This is decision support.** Every entry and exit is still your call, made with your money.

---

## 9. A morning in the life (under 10 minutes)

**~7:20am, coffee in hand:**

1. **Open today's dashboard** (bookmark). Read the five "Today's read" sentences. (1 min)
2. **Check "Triggered today"** — any FRESH LOOK candidate that fired its confirmation trigger overnight, with entry zone, stop, and share count pre-computed. If one looks right and you have a free slot (max 6 positions, max 2 entries/week), queue the order for the open. (3 min)
3. **Check position cards** — any stop hit, trailing rule fired, or thesis-broken flag? If so, queue the exit. No judgement calls; the rule already decided. (2 min)
4. **Scan the scatter and theme table** — 30 seconds each for US and ASX. Star anything interesting into the watchlist (one click, or one line in the config). (2 min)
5. **Close the laptop.** The system re-ranks everything tomorrow whether you watch or not. Log any fills in `positions.json` tonight (30 seconds).

Everything else — backtests, basket edits, threshold tweaks — is weekend work, never morning work.
