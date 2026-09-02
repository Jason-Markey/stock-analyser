#!/usr/bin/env python3
"""Stock Analyser — daily pipeline (Stage 1: ASX + US + Global).

For each market: fetch prices → metrics → themes → breadth → regime →
signals → read → payload. Then render one self-contained HTML terminal app.

Run:  python run_daily.py            (live data)
      python run_daily.py --sample   (offline synthetic data)
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from src import baskets as bk, breadth as br, dataio, narrate, payload as pl  # noqa: E402
from src import regime as rg, signals, webapp  # noqa: E402

ROOT = Path(__file__).resolve().parent
BOUNCE_VOL_RATIO = 1.3
ACTION_SIZE = 20


def load_cfg(name: str) -> dict:
    return yaml.safe_load((ROOT / "config" / f"{name}.yaml").read_text())


def fetch(tickers: list[str], sample: bool) -> dict:
    if sample:
        from src import sampledata
        return sampledata.get_prices(tickers)
    return dataio.get_prices(tickers)


def build_market(cfg: dict, sample: bool) -> tuple[dict, dt.date]:
    mk, baskets_map = cfg["market"], cfg["baskets"]
    drivers_cfg = cfg.get("drivers", {})
    universe = sorted({t for names in baskets_map.values() for t in names})
    tickers = sorted(set(universe) | set(mk["tape"]) | set(drivers_cfg) | {mk["benchmark"]})

    prices = fetch(tickers, sample)
    missing = sorted(set(universe) - set(prices))
    if missing:
        print(f"  WARNING [{mk['key']}] no data for: {', '.join(missing)}")
    if mk["benchmark"] not in prices:
        raise RuntimeError(f"benchmark {mk['benchmark']} missing for {mk['key']}")

    m = signals.name_metrics(
        {t: prices[t] for t in prices if t in universe or t == mk["benchmark"]},
        mk["benchmark"], mk["liquidity_floor"], BOUNCE_VOL_RATIO)
    m = m.drop(index=[mk["benchmark"]], errors="ignore")

    b = bk.basket_metrics(m, baskets_map)
    m = signals.add_theme_relatives(m, baskets_map, b)
    m = signals.classify_signals(m, dict(zip(b.index, b["breadth"])))
    action = signals.action_list(m, ACTION_SIZE)
    breadth = br.market_breadth(m, prices, universe)
    regime = rg.assess(mk, prices, m, b, breadth)

    tape = {}
    for t in list(mk["tape"]) + [mk["benchmark"]]:
        if t in prices:
            tm = signals.name_metrics({t: prices[t], mk["benchmark"]: prices[mk["benchmark"]]},
                                      mk["benchmark"], 0, BOUNCE_VOL_RATIO)
            tape[t] = tm.loc[t].to_dict()

    read = narrate.todays_read(mk, m, b, tape, regime)
    drivers = pl.driver_metrics(prices, drivers_cfg)
    run_date = prices[mk["benchmark"]].index[-1].date()
    return pl.market_payload(mk, prices, m, b, breadth, regime, read,
                             action, tape, drivers, cfg.get("names", {})), run_date


def build_global(sample: bool) -> dict:
    cfg = load_cfg("global")
    drivers_cfg = cfg["drivers"]
    prices = fetch(sorted(drivers_cfg), sample)
    return {"key": "global", "label": "Global",
            "drivers": pl.driver_metrics(prices, drivers_cfg)}


def main(sample: bool = False) -> int:
    if sample:
        print("SAMPLE MODE — synthetic data, layout/logic test only")
    markets, run_date = {}, dt.date.today()
    for key in ("asx", "us"):
        print(f"Building {key.upper()} …")
        markets[key], run_date = build_market(load_cfg(key), sample)
    print("Building Global drivers …")
    glob = build_global(sample)

    data = pl.clean({
        "generated": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "run_date": run_date.isoformat(),
        "sample": sample,
        "markets": markets,
        "global": glob,
    })

    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    page = webapp.render(data)
    dated = out_dir / f"dashboard_{run_date.isoformat()}.html"
    dated.write_text(page, encoding="utf-8")
    (out_dir / "index.html").write_text(page, encoding="utf-8")
    (out_dir / "payload.json").write_text(json.dumps(data), encoding="utf-8")

    for k, mkt in markets.items():
        n = len(mkt["names"])
        sig = sum(1 for v in mkt["names"].values() if v["signal"])
        print(f"  {k.upper()}: {n} names · {len(mkt['themes'])} themes · {sig} signalled")
    print(f"Dashboard written: {dated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sample="--sample" in sys.argv))
