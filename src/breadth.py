"""Market breadth statistics + a 30-day breadth trend series."""
from __future__ import annotations

import pandas as pd


def market_breadth(m: pd.DataFrame, prices: dict[str, pd.DataFrame],
                   universe: list[str]) -> dict:
    liquid = m[m["liquid"]]
    out = {
        "above_ma20": round(float((liquid["dist_ma20"] > 0).mean()), 3),
        "above_ma50": round(float((liquid["dist_ma50"] > 0).mean()), 3),
        "above_ma200": round(float((liquid["dist_ma200"] > 0).mean()), 3),
        "advancers": int((liquid["ret_1d"] > 0).sum()),
        "decliners": int((liquid["ret_1d"] < 0).sum()),
        "n": int(len(liquid)),
    }
    # 20-day highs/lows
    hi = lo = 0
    for t in liquid.index:
        df = prices.get(t)
        if df is None or len(df) < 21:
            continue
        c = df["Close"]
        if c.iloc[-1] >= c.tail(21).max():
            hi += 1
        elif c.iloc[-1] <= c.tail(21).min():
            lo += 1
    out["new_hi20"], out["new_lo20"] = hi, lo

    # 30-day trend of % above 20DMA (the breadth chart series)
    series = []
    frames = {t: prices[t]["Close"] for t in liquid.index if t in prices and len(prices[t]) >= 50}
    if frames:
        closes = pd.DataFrame(frames).dropna(how="all")
        ma20 = closes.rolling(20).mean()
        pct = (closes > ma20).mean(axis=1).tail(30)
        series = [round(float(v), 3) for v in pct]
    out["trend"] = series
    return out
