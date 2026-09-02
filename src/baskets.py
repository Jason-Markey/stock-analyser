"""Theme-basket aggregates (BUILD_PLAN §2.3) with flow-phase classification.

Dollar-volume weighted, single name capped at 25%, renormalised. New in
Stage 1: acceleration, above-MA participation, leaders AND weakening names,
and an explainable phase label (Money entering / Emerging / Crowded /
Rolling over / Washed out / Quiet).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def basket_metrics(m: pd.DataFrame, baskets: dict[str, list[str]],
                   name_cap: float = 0.25) -> pd.DataFrame:
    rows = []
    total_dollar_vol = m.loc[m["liquid"], "dollar_vol"].sum()
    for name, tickers in baskets.items():
        sub = m[m.index.isin(tickers) & m["liquid"]]
        if len(sub) < 2:
            continue
        w = sub["adv20"] / sub["adv20"].sum()
        w = (w.clip(upper=name_cap))
        w = w / w.sum()
        rel_1w = float((sub["rel_1w"] * w).sum())
        rel_1m = float((sub["rel_1m"] * w).sum())
        accel = rel_1w - rel_1m / 4
        breadth = float((sub["rel_1w"] > 0).mean())
        vol_ratio = float((sub["vol_ratio"] * w).sum())
        rows.append({
            "basket": name, "n": len(sub),
            "ret_1d": float((sub["ret_1d"] * w).sum()),
            "rel_1w": rel_1w, "rel_1m": rel_1m,
            "rel_3m": float((sub["rel_3m"] * w).sum()),
            "accel": accel, "vol_ratio": vol_ratio,
            "flow_bps": sub["dollar_vol"].sum() / total_dollar_vol * 1e4 if total_dollar_vol else 0,
            "breadth": breadth,
            "above_ma20": float((sub["dist_ma20"] > 0).mean()),
            "above_ma50": float((sub["dist_ma50"] > 0).mean()),
            "above_ma200": float((sub["dist_ma200"] > 0).mean()),
            "trend": "improving" if accel > 0 else "fading",
            "phase": _phase(rel_1m, rel_1w, accel, breadth, vol_ratio),
            "leaders": list(sub.sort_values("rel_1w", ascending=False).index[:3]),
            "weak": list(sub.sort_values("rel_1w").index[:2]),
            "spark": _basket_spark(sub, w),
        })
    return (pd.DataFrame(rows).set_index("basket")
            .sort_values("rel_1m", ascending=False))


def _phase(rel_1m: float, rel_1w: float, accel: float,
           breadth: float, vol_ratio: float) -> str:
    """Explainable flow phase — thresholds are deliberately simple."""
    if rel_1m < -0.03 and rel_1w > 0 and accel > 0:
        return "Emerging"                       # was weak, now turning with the tape
    if rel_1m < -0.05 and rel_1w <= 0:
        return "Washed out"
    if rel_1m > 0.05 and accel < -0.005:
        return "Rolling over"
    if rel_1m > 0.08 and breadth >= 0.8:
        return "Crowded"                        # everyone is already in
    if rel_1w > 0.01 and breadth >= 0.6 and vol_ratio >= 1.0:
        return "Money entering"
    return "Quiet"


def _basket_spark(sub: pd.DataFrame, w: pd.Series) -> list[float]:
    """Weighted composite of member sparklines (each already normalised to 1.0)."""
    n = max((len(s) for s in sub["spark"]), default=0)
    sparks = [np.array(s) * wt for s, wt in zip(sub["spark"], w) if len(s) == n and n > 1]
    if not sparks:
        return []
    comp = np.sum(sparks, axis=0)
    return [round(float(v / comp[0]), 4) for v in comp] if comp[0] else []
