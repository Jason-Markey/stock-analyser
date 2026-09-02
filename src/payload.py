"""Assemble the JSON payload the web app renders.

Calculation logic lives in signals/baskets/breadth/regime; this module only
shapes results for the front end. Display tickers drop the .AX suffix; the
raw Yahoo symbol is kept for future live links.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def disp(t: str) -> str:
    return t[:-3] if t.endswith(".AX") else t


def _f(x, nd=4):
    """JSON-safe float."""
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return None
    return round(float(x), nd)


def _tape_entry(label: str, d: dict) -> dict:
    return {"label": label, "close": _f(d.get("close"), 2),
            "ret_1d": _f(d.get("ret_1d")), "ret_1w": _f(d.get("ret_1w")),
            "ret_1m": _f(d.get("ret_1m")), "spark": d.get("spark", [])}


def driver_metrics(prices: dict[str, pd.DataFrame], drivers_cfg: dict) -> list[dict]:
    out = []
    for tick, meta in drivers_cfg.items():
        df = prices.get(tick)
        if df is None or len(df) < 22:
            continue
        c = df["Close"]
        r1d = float(c.iloc[-1] / c.iloc[-2] - 1)
        r1w = float(c.iloc[-1] / c.iloc[-6] - 1)
        r1m = float(c.iloc[-1] / c.iloc[-22] - 1)
        spark = c.tail(30)
        out.append({
            "ticker": tick, "label": meta["label"], "group": meta.get("group", ""),
            "close": _f(c.iloc[-1], 2 if c.iloc[-1] < 1000 else 0),
            "ret_1d": _f(r1d), "ret_1w": _f(r1w), "ret_1m": _f(r1m),
            "accel": "accelerating" if r1w > r1m / 4 else "fading",
            "themes": meta.get("themes", []),
            "beneficiaries": [disp(b) for b in meta.get("beneficiaries", [])],
            "spark": [round(float(v / spark.iloc[0]), 4) for v in spark] if spark.iloc[0] else [],
        })
    return out


def market_payload(cfg: dict, prices: dict, m: pd.DataFrame, b: pd.DataFrame,
                   breadth: dict, regime: dict, read: list[dict],
                   action: pd.DataFrame, tape: dict[str, dict],
                   drivers: list[dict], name_map: dict | None = None) -> dict[str, Any]:
    mk = cfg
    name_map = name_map or {}
    names: dict[str, dict] = {}
    for t, r in m.iterrows():
        names[disp(t)] = {
            "co": name_map.get(t, ""),
            "close": _f(r["close"], 2),
            "ret_1d": _f(r["ret_1d"]), "ret_1w": _f(r["ret_1w"]),
            "ret_1m": _f(r["ret_1m"]), "ret_3m": _f(r["ret_3m"]),
            "rel_1w": _f(r["rel_1w"]), "rel_1m": _f(r["rel_1m"]), "rel_3m": _f(r["rel_3m"]),
            "theme_rel_1m": _f(r.get("theme_rel_1m")),
            "vol_ratio": _f(r["vol_ratio"], 2), "adv20": _f(r["adv20"], 0),
            "trend": r["trend"], "accel": _f(r["accel"]),
            "ma20": _f(r["dist_ma20"]), "ma50": _f(r["dist_ma50"]), "ma200": _f(r["dist_ma200"]),
            "hi60": _f(r["dist_hi60"]),
            "liquid": bool(r["liquid"]),
            "theme": r.get("theme", "—"),
            "signal": r.get("signal", ""), "score": _f(r.get("score"), 1),
            "factors": r.get("factors", []),
            "spark": r.get("spark", []),
        }
    themes = []
    for name, r in b.iterrows():
        themes.append({
            "name": name, "n": int(r["n"]),
            "ret_1d": _f(r["ret_1d"]), "rel_1w": _f(r["rel_1w"]),
            "rel_1m": _f(r["rel_1m"]), "rel_3m": _f(r["rel_3m"]),
            "accel": _f(r["accel"]), "vol_ratio": _f(r["vol_ratio"], 2),
            "flow_bps": _f(r["flow_bps"], 1), "breadth": _f(r["breadth"], 3),
            "above_ma20": _f(r["above_ma20"], 3), "above_ma50": _f(r["above_ma50"], 3),
            "above_ma200": _f(r["above_ma200"], 3),
            "trend": r["trend"], "phase": r["phase"],
            "leaders": [disp(t) for t in r["leaders"]],
            "weak": [disp(t) for t in r["weak"]],
            "spark": r["spark"],
        })
    return {
        "key": mk["key"], "label": mk["label"], "currency": mk["currency"],
        "benchmark": mk["benchmark_label"], "session": mk.get("session", {}),
        "tape": [_tape_entry(lbl, tape.get(t, {})) for t, lbl in mk["tape"].items()],
        "regime": regime, "breadth": breadth,
        "read": [{**c, "tickers": [disp(t) for t in c.get("tickers", [])]} for c in read],
        "themes": themes, "names": names,
        "action": [disp(t) for t in action.index],
        "drivers": drivers,
    }


def clean(obj):
    """Recursively make numpy types JSON-serialisable."""
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj
