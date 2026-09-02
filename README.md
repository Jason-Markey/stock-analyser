# Stock Analyser — Stage 1 terminal

A daily, self-running market intelligence terminal covering **ASX, US and
Global drivers**: market command header, "Today's read", explainable market
regime, money-flow by theme (with flow phases), breadth, a configurable
momentum map, a signal-based action list with factor-level score breakdowns,
a stock intelligence drawer, watchlist stars, and Ctrl/Cmd-K search — all in
one self-contained HTML file. Free data (yfinance), no API keys. Phase 2 adds
the options-skew layer.

**Decision support, not financial advice.**

## Run it on your computer

```
pip install -r requirements.txt
python run_daily.py
```

Then open `output/index.html` in your browser. First run takes a few minutes
(~270 names across two markets); re-runs the same day are instant (cached).

Offline test with synthetic data (no network needed):
`python run_daily.py --sample`

## Set up the daily cloud run (one-off, ~15 minutes)

1. Move `setup/daily.yml` to `.github/workflows/daily.yml` (create the folders).
   Security tools often block writing workflow files remotely, so it ships in
   `setup/` — one drag-and-drop fixes it:
   ```
   mkdir .github\workflows
   move setup\daily.yml .github\workflows\daily.yml
   ```
2. Create a repo on GitHub (e.g. `stock-analyser`) and push this folder to it.
   From this folder:
   ```
   git init
   git add .
   git commit -m "Phase 1"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/stock-analyser.git
   git push -u origin main
   ```
3. On GitHub: repo → **Actions** tab → enable workflows if prompted.
4. Test it: Actions → "Daily dashboard" → **Run workflow**. After ~3 minutes a
   commit appears adding `docs/index.html` — that's your dashboard.
5. From then on it runs itself at **8:30am Brisbane** every US trading day.

**Opening the daily result.** Easiest: make the repo public and turn on GitHub
Pages (Settings → Pages → Deploy from branch → `main` / `docs`); your dashboard
is then at `https://YOUR_USERNAME.github.io/stock-analyser/` — bookmark it.
(Pages on a *private* repo needs a paid GitHub plan; if you'd rather keep it
private, just do a `git pull` in this OneDrive folder each morning — or ask
Claude to wire up an alternative.) The universe is public-market data, so a
public repo leaks nothing personal.

## Edit the universe

Each market has its own config — `config/asx.yaml`, `config/us.yaml`,
`config/global.yaml` — baskets, benchmarks, tape, drivers, session hours,
liquidity floors. No code changes needed. (Quote tickers like `"ON"` that
YAML would misread; ASX tickers carry the `.AX` suffix, displayed without it.)

## Layout

```
config/            per-market configs (asx, us, global drivers)
run_daily.py       orchestrator — builds every market, renders the app
src/dataio.py      data layer (swappable — Phase 2/3 backends drop in here)
src/signals.py     per-name metrics + explainable signal engine
src/baskets.py     theme aggregates + flow phases
src/breadth.py     market breadth stats + trend series
src/regime.py      rules-based market regime (never a black box)
src/narrate.py     "Today's read" insight cards
src/payload.py     JSON payload assembly (calc/presentation separation)
src/webapp.py      the terminal web app (client-side, self-contained)
src/sampledata.py  offline test fixture
tests/             metric-semantics checks (python -m tests.test_signals)
.github/workflows/daily.yml   the 8:30am Brisbane cron (via setup/daily.yml)
output/            generated dashboards + payload.json (git-ignored; cloud copies land in docs/)
```

## Phase map

- [x] **Phase 0/1** — price signals, themes, action list, daily cloud run
- [x] **Stage 1 UI** — ASX/US/Global terminal, regime, breadth, drawer, search
- [x] **Stage 3 UX** — theme detail view, full stock analysis, heatmap, watchlist view
- [ ] **Phase 2** — 25Δ options skew (Tradier), four-quadrant radar, real asymmetry score
- [ ] **Phase 3** — ASX module (ASIC short interest + composite conviction)
- [ ] **Phase 4** — entry/exit engine + trade journal
- [ ] **Phase 5** — backtest & tuning

See `BUILD_PLAN.md` for the full plan.
