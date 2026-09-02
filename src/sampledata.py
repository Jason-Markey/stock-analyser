"""Deterministic synthetic OHLCV — offline test fixture.

`python run_daily.py --sample` runs the whole pipeline without network access.
Seeded per ticker, so output is reproducible. Never used in the daily job.
"""
from __future__ import annotations

import datetime as dt
import zlib

import numpy as np
import pandas as pd


def get_prices(tickers: list[str], history_days: int = 400, **_) -> dict[str, pd.DataFrame]:
    end = dt.date.today()
    dates = pd.bdate_range(end=end, periods=min(history_days, 260))
    out = {}
    for t in tickers:
        rng = np.random.default_rng(zlib.crc32(t.encode()))
        drift = rng.normal(0.0004, 0.0012)
        vol = rng.uniform(0.012, 0.045)
        rets = rng.normal(drift, vol, len(dates))
        # give some names a distinct recent regime so quadrants/action list populate
        regime = rng.integers(0, 4)
        if regime == 1:
            rets[-21:] -= 0.006   # washed out
        elif regime == 2:
            rets[-21:] += 0.005   # momentum
        if regime == 1 and rng.random() < 0.5:
            rets[-1] = abs(rets[-1]) + 0.02  # bounce day
        if t.endswith("=X"):
            base = rng.uniform(0.55, 0.75); vol = 0.006; rets = rng.normal(0, vol, len(dates))
        elif t.startswith("^") and "VIX" not in t and "TNX" not in t:
            base = rng.uniform(2000, 9500)
        elif "VIX" in t or "TNX" in t:
            base = rng.uniform(14, 45)
        elif t.endswith("=F"):
            base = rng.uniform(3, 3000)
        else:
            base = 20 * rng.uniform(1, 20)
        close = base * np.exp(np.cumsum(rets)) / np.exp(np.cumsum(rets))[0]
        high = close * (1 + rng.uniform(0.001, 0.02, len(dates)))
        low = close * (1 - rng.uniform(0.001, 0.02, len(dates)))
        openp = low + (high - low) * rng.uniform(0.2, 0.8, len(dates))
        volume = rng.uniform(0.5e6, 3e7) * (1 + rng.normal(0, 0.3, len(dates)).clip(-0.8))
        out[t] = pd.DataFrame(
            {"Open": openp, "High": high, "Low": low, "Close": close,
             "Volume": volume.clip(1e5)}, index=dates)
    return out
