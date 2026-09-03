"""Data layer — the only module that talks to a vendor.

Swappable by design: keep the two functions' signatures stable and Phase 2/3
backends (Tradier chains, ASX feeds) drop in without touching signal code.
"""
from __future__ import annotations

import datetime as dt
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

CHUNK = 50           # tickers per request batch
RETRY_PAUSE = 25     # seconds before retrying rate-limited tickers

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
        start = (dt.date.today() - dt.timedelta(days=history_days)).isoformat()
        wide = _download_chunked(tickers, start)
        missing = _missing(wide, tickers)
        if missing:   # usually Yahoo rate limiting — pause once and retry those
            print(f"  retrying {len(missing)} tickers after {RETRY_PAUSE}s pause …")
            time.sleep(RETRY_PAUSE)
            retry = _download_chunked(missing, start)
            if retry is not None and not retry.empty:
                wide = pd.concat([wide, retry], axis=1)
        if wide is None or wide.empty:
            raise RuntimeError("Price download returned no data — check network / vendor.")
        wide.to_parquet(cache)
        # keep the cache dir tidy: drop caches older than 5 days
        for old in CACHE_DIR.glob("prices_*.parquet"):
            if old.name != cache.name and old.stat().st_mtime < (
                dt.datetime.now() - dt.timedelta(days=5)).timestamp():
                old.unlink(missing_ok=True)

    out: dict[str, pd.DataFrame] = {}
    seen = set()
    for t in tickers:
        if t in seen:
            continue
        seen.add(t)
        try:
            df = wide[t].dropna(how="all")
        except KeyError:
            continue
        df = df.dropna(subset=["Close"])
        if len(df) >= 30:  # need at least ~6 weeks of history
            out[t] = df
    return out


def _download_chunked(tickers: list[str], start: str) -> pd.DataFrame | None:
    """Download in batches to stay under vendor rate limits."""
    frames = []
    for i in range(0, len(tickers), CHUNK):
        chunk = tickers[i:i + CHUNK]
        w = yf.download(tickers=" ".join(chunk), start=start, auto_adjust=True,
                        group_by="ticker", progress=False, threads=True)
        if w is not None and not w.empty:
            if not isinstance(w.columns, pd.MultiIndex):   # single-ticker shape
                w = pd.concat({chunk[0]: w}, axis=1)
            frames.append(w)
        if i + CHUNK < len(tickers):
            time.sleep(2)
    return pd.concat(frames, axis=1) if frames else None


def _missing(wide: pd.DataFrame | None, tickers: list[str]) -> list[str]:
    if wide is None or wide.empty:
        return list(tickers)
    out = []
    for t in tickers:
        try:
            if wide[t]["Close"].dropna().empty:
                out.append(t)
        except KeyError:
            out.append(t)
    return out
