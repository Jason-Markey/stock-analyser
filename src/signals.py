"""Per-name metrics + the explainable signal engine.

Every formula is deterministic — same inputs, same outputs, every day.
Existing Phase-1 metric semantics (ret/rel/vol_ratio/trend/z-score) are
unchanged; this module adds 3M horizon, moving averages, 60-day-high
distance, momentum acceleration, and the signal classification with a
factor-by-factor score breakdown (nothing opaque).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

HORIZONS = (("ret_1d", 1), ("ret_1w", 5), ("ret_1m", 21), ("ret_3m", 63))


def name_metrics(prices: dict[str, pd.DataFrame], index_ticker: str,
                 liquidity_floor: float, bounce_vol_ratio: float) -> pd.DataFrame:
    """One row per ticker with the full metric set."""
    idx = _returns(prices[index_ticker])
    rows = []
    for t, df in prices.items():
        close, vol = df["Close"], df["Volume"].fillna(0)
        if len(close) < 30:
            continue
        r = _returns(df)
        dollar_vol = float(close.iloc[-1] * vol.iloc[-1])
        adv20 = float((close * vol).rolling(20).mean().iloc[-1])
        last = float(close.iloc[-1])

        def ma(n):
            return float(close.rolling(n).mean().iloc[-1]) if len(close) >= n else np.nan

        ma20, ma50, ma200 = ma(20), ma(50), ma(200)
        hi60 = float(close.tail(63).max())
        rel = {k: r[k] - idx[k] for k in ("ret_1w", "ret_1m", "ret_3m")}
        spark = close.tail(130)
        rows.append({
            "ticker": t, "close": last,
            **{k: r[k] for k, _ in HORIZONS},
            "rel_1w": rel["ret_1w"], "rel_1m": rel["ret_1m"], "rel_3m": rel["ret_3m"],
            "vol_ratio": dollar_vol / adv20 if adv20 > 0 else np.nan,
            "dollar_vol": dollar_vol, "adv20": adv20,
            "trend": "improving" if rel["ret_1w"] > rel["ret_1m"] / 4 else "fading",
            "accel": rel["ret_1w"] - rel["ret_1m"] / 4,   # momentum acceleration (+ = quickening)
            "dist_ma20": last / ma20 - 1 if ma20 > 0 else np.nan,
            "dist_ma50": last / ma50 - 1 if ma50 and ma50 > 0 else np.nan,
            "dist_ma200": last / ma200 - 1 if ma200 and ma200 > 0 else np.nan,
            "dist_hi60": last / hi60 - 1 if hi60 > 0 else np.nan,
            "liquid": adv20 >= liquidity_floor,
            "range_pos": _range_position(df),
            "spark": [round(float(v / spark.iloc[0]), 4) for v in spark] if spark.iloc[0] > 0 else [],
        })
    m = pd.DataFrame(rows).set_index("ticker")

    liquid = m[m["liquid"]]
    for col in ("rel_1m", "rel_3m"):
        mu, sd = liquid[col].mean(), liquid[col].std(ddof=0)
        m[f"{col}_z"] = (m[col] - mu) / sd if sd and sd > 0 else 0.0

    m["bounce"] = (m["ret_1d"] > 0) & (m["vol_ratio"] > bounce_vol_ratio) & (m["range_pos"] > 0.5)
    return m


def add_theme_relatives(m: pd.DataFrame, baskets: dict[str, list[str]],
                        basket_stats: pd.DataFrame) -> pd.DataFrame:
    """Attach each name's primary theme and its return relative to that theme."""
    theme_of: dict[str, str] = {}
    for theme, tickers in baskets.items():
        for t in tickers:
            theme_of.setdefault(t, theme)   # first basket listed wins as primary
    m = m.copy()
    m["theme"] = [theme_of.get(t, "—") for t in m.index]
    tr = []
    for t, r in m.iterrows():
        th = r["theme"]
        tr.append(r["rel_1m"] - basket_stats.loc[th, "rel_1m"]
                  if th in basket_stats.index else np.nan)
    m["theme_rel_1m"] = tr
    return m


# --------------------------------------------------------------------------
# Signal engine — categories + factor breakdown (BUILD_PLAN §2.6 extended).
# conviction (options skew / ASX composite) still enters at 0 until Phase 2.
# --------------------------------------------------------------------------

def classify_signals(m: pd.DataFrame, theme_breadth: dict[str, float]) -> pd.DataFrame:
    """Return m with `signal`, `score`, `factors` (list of [label, points]).

    Categories (first match wins, most specific first):
      Bounce watch · Breakout · Emerging · Trend leader · Losing momentum ·
      Washed out · Abnormal volume · RS leader · none
    """
    sigs, scores, factors_col = [], [], []
    for t, r in m.iterrows():
        f: list[tuple[str, float]] = []
        tb = theme_breadth.get(r.get("theme", ""), np.nan)

        washed = r["rel_1m_z"] < -1.0
        strong = r["rel_1m_z"] > 0.75
        near_high = r["dist_hi60"] > -0.02
        vol_spike = r["vol_ratio"] > 2.0
        above50 = r["dist_ma50"] > 0 if pd.notna(r["dist_ma50"]) else False

        if washed:
            f.append(("fell hard vs benchmark (1M z-score "
                      f"{r['rel_1m_z']:+.1f})", round(min(-r["rel_1m_z"], 3.0), 1)))
        if r["bounce"]:
            f.append((f"bounced on {r['vol_ratio']:.1f}× volume, closed in top half of range", 1.5))
        if r["accel"] > 0.01:
            f.append((f"momentum accelerating ({r['accel']:+.1%} 1W vs 1M run-rate)", 1.2))
        elif r["accel"] < -0.01 and strong:
            f.append((f"momentum deteriorating ({r['accel']:+.1%})", 1.0))
        if vol_spike:
            f.append((f"abnormal volume ({r['vol_ratio']:.1f}× 20-day average)", 1.3))
        if near_high and r["ret_1d"] > 0.02 and r["vol_ratio"] > 1.5:
            f.append(("pressing 60-day highs on real volume", 1.5))
        if strong and above50:
            f.append((f"established trend (+{r['rel_1m_z']:.1f}z 1M, above 50DMA)", 1.2))
        if pd.notna(tb) and tb >= 0.6:
            f.append((f"theme breadth healthy ({tb:.0%} of {r['theme']} participating)", 0.8))
        if r["rel_3m_z"] > 1.5:
            f.append((f"3-month relative-strength leader ({r['rel_3m']:+.1%} vs benchmark)", 1.0))

        # category — most specific first
        if washed and r["bounce"]:
            sig = "Bounce watch"
        elif near_high and r["ret_1d"] > 0.02 and r["vol_ratio"] > 1.5:
            sig = "Breakout"
        elif r["rel_1m"] < -0.02 and r["rel_1w"] > 0.005 and r["accel"] > 0.015:
            sig = "Emerging"
        elif strong and above50 and r["trend"] == "improving":
            sig = "Trend leader"
        elif strong and r["accel"] < -0.01:
            sig = "Losing momentum"
        elif washed:
            sig = "Washed out"
        elif vol_spike:
            sig = "Abnormal volume"
        elif r["rel_3m_z"] > 1.5:
            sig = "RS leader"
        else:
            sig = ""

        sigs.append(sig)
        scores.append(round(sum(p for _, p in f), 1) if sig else 0.0)
        factors_col.append([[lbl, p] for lbl, p in f] if sig else [])

    out = m.copy()
    out["signal"], out["score"], out["factors"] = sigs, scores, factors_col
    return out


def action_list(m: pd.DataFrame, size: int = 15) -> pd.DataFrame:
    """Top signalled names, liquid only, highest score first."""
    elig = m[m["liquid"] & (m["signal"] != "")]
    return elig.sort_values("score", ascending=False).head(size)


def _returns(df: pd.DataFrame) -> dict[str, float]:
    c = df["Close"]
    return {k: float(c.iloc[-1] / c.iloc[-1 - n] - 1) if len(c) > n else np.nan
            for k, n in HORIZONS}


def _range_position(df: pd.DataFrame) -> float:
    last = df.iloc[-1]
    rng = last["High"] - last["Low"]
    return float((last["Close"] - last["Low"]) / rng) if rng > 0 else 0.5
