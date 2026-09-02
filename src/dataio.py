"""Data layer — the only module that talks to a vendor.

Swappable by design: keep the two functions' signatures stable and Phase 2/3
backends (Tradier chains, ASX feeds) drop in without touching signal code.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
import yfinance as yf

CACHE_DIR = Path(__file__).resolve().parent.parent / "data"


def get_prices(tickers: list[str], history_days: int = 400,
               use_cache: bool = True) -> dict[str, pd.DataFrame]:
    """Return {ticker: OHLCV DataFrame} of adjusted daily bars.

    Caches to parquet per run-date so re-runs on the same day are instant.
    Tickers that fail to download are silently dropped (callers handle absence).
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()
    cache = CACHE_DIR / f"prices_{today}.parquet"

    if use_cache and cache.exists():
        wide = pd.read_parquet(cache)
    else:
        start = dt.date.today() - dt.timedelta(days=history_days)
        wide = yf.download(
            tickers=" ".join(tickers), start=start.isoformat(),
            auto_adjust=True, group_by="ticker", progress=False, threads=True,
        )
        if wide is None or wide.empty:
            raise RuntimeError("Price download returned no data — check network / vendor.")
        wide.to_parquet(cache)
        # keep the cache dir tidy: drop caches older than 5 days
        for old in CACHE_DIR.glob("prices_*.parquet"):
            if old.name != cache.name and old.stat().st_mtime < (
                dt.datetime.now() - dt.timedelta(days=5)).timestamp():
                old.unlink(missing_ok=True)

    out: dict[str, pd.DataFrame] = {}
    for t in tickers:
        try:
            df = wide[t].dropna(how="all")
        except KeyError:
            continue
        df = df.dropna(subset=["Close"])
        if len(df) >= 30:  # need at least ~6 weeks of history
            out[t] = df
    return out
