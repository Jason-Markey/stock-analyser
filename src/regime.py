"""Market regime engine — a small set of explainable rules, never a black box.

Inputs: breadth, benchmark trend, volatility, small-vs-large relative
strength, defensives-vs-cyclicals, and basket participation. Output: a
label plus the factor list that produced it (each factor: name, state,
direction, and its vote).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def assess(mkt_cfg: dict, prices: dict, m: pd.DataFrame,
           b: pd.DataFrame, breadth: dict) -> dict:
    factors = []   # (label, state, dir: +1 risk-on / 0 / -1 risk-off)
    votes = []

    # 1 — breadth level and direction
    lvl = breadth["above_ma20"]
    trend = breadth.get("trend") or []
    rising = len(trend) >= 6 and trend[-1] > trend[-6]
    state = f"{lvl:.0%} above 20DMA, {'rising' if rising else 'falling'}"
    v = (1 if lvl >= 0.55 else -1 if lvl <= 0.4 else 0) + (0.5 if rising else -0.5)
    factors.append(("Breadth", state, np.sign(v)))
    votes.append(v)

    # 2 — benchmark vs its 50DMA
    bench = prices.get(mkt_cfg["benchmark"])
    if bench is not None and len(bench) >= 50:
        c = bench["Close"]
        above = c.iloc[-1] > c.rolling(50).mean().iloc[-1]
        rv = float(c.pct_change().tail(20).std() * np.sqrt(252))
        vol_state = "low" if rv < 0.12 else "elevated" if rv > 0.22 else "normal"
        factors.append((mkt_cfg["benchmark_label"],
                        f"{'above' if above else 'below'} 50-day trend", 1 if above else -1))
        votes.append(1 if above else -1)
        factors.append(("Volatility", f"{vol_state} ({rv:.0%} annualised, 20d)",
                        1 if vol_state == "low" else -1 if vol_state == "elevated" else 0))
        votes.append(0.5 if vol_state == "low" else -1 if vol_state == "elevated" else 0)
    else:
        vol_state = "unknown"

    # 3 — small caps vs large caps
    s, l = mkt_cfg.get("small_vs_large", [None, None])
    if s in prices and l in prices and len(prices[s]) > 21 and len(prices[l]) > 21:
        sr = float(prices[s]["Close"].iloc[-1] / prices[s]["Close"].iloc[-22] - 1)
        lr = float(prices[l]["Close"].iloc[-1] / prices[l]["Close"].iloc[-22] - 1)
        diff = sr - lr
        factors.append(("Small vs large caps",
                        f"small caps {'leading' if diff > 0 else 'lagging'} by {abs(diff):.1%} (1M)",
                        1 if diff > 0.005 else -1 if diff < -0.005 else 0))
        votes.append(1 if diff > 0.005 else -1 if diff < -0.005 else 0)

    # 4 — defensives vs cyclicals (theme-level relative strength)
    defs = [t for t in mkt_cfg.get("defensives", []) if t in b.index]
    cycs = [t for t in mkt_cfg.get("cyclicals", []) if t in b.index]
    if defs and cycs:
        d, c_ = b.loc[defs, "rel_1m"].mean(), b.loc[cycs, "rel_1m"].mean()
        lead = "cyclicals" if c_ > d else "defensives"
        factors.append(("Defensives vs cyclicals", f"{lead} leading", 1 if lead == "cyclicals" else -1))
        votes.append(0.7 if lead == "cyclicals" else -0.7)

    # 5 — theme participation
    part = float((b["rel_1w"] > 0).mean()) if len(b) else 0.5
    factors.append(("Theme participation", f"{part:.0%} of themes beat the index this week",
                    1 if part >= 0.55 else -1 if part <= 0.35 else 0))
    votes.append(1 if part >= 0.55 else -1 if part <= 0.35 else 0)

    total = sum(votes)
    pos = sum(1 for v in votes if v > 0)
    neg = sum(1 for v in votes if v < 0)
    if total >= 2.5 and neg == 0:
        label = "Risk-on"
    elif total >= 1:
        label = "Selective risk-on"
    elif total <= -2.5 and pos == 0:
        label = "Risk-off"
    elif total <= -1:
        label = "Defensive"
    else:
        label = "Neutral / mixed"

    return {
        "label": label,
        "vol_state": vol_state,
        "factors": [{"name": n, "state": s_, "dir": int(d)} for n, s_, d in factors],
        "note": f"{pos} supportive · {neg} negative · rules-based, hover any factor",
    }
