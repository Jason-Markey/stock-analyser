"""Hand-computed checks that metric semantics never drift.

Run:  python -m tests.test_signals
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import signals  # noqa: E402


def frame(closes, vols=None):
    n = len(closes)
    vols = vols or [1e6] * n
    idx = pd.bdate_range(end="2026-08-25", periods=n)
    c = pd.Series(closes, index=idx, dtype=float)
    return pd.DataFrame({"Open": c, "High": c * 1.01, "Low": c * 0.99,
                         "Close": c, "Volume": vols}, index=idx)


def main():
    # stock: +10% over last 21 bars; index flat → rel_1m = +10%
    base = [100.0] * 80
    stock = base[:-22] + list(np.linspace(100, 110, 22))
    m = signals.name_metrics({"AAA": frame(stock), "IDX": frame(base)},
                             "IDX", 0, 1.3)
    r = m.loc["AAA"]
    assert abs(r["ret_1m"] - 0.10) < 1e-9, r["ret_1m"]
    assert abs(r["rel_1m"] - 0.10) < 1e-9
    assert abs(r["ret_1d"] - (110 / (100 + 10 * 20 / 21) - 1)) < 1e-9
    # vol_ratio: constant volume & rising price → today's $vol slightly above 20d avg
    assert 1.0 < r["vol_ratio"] < 1.1
    # trend: rel_1w vs rel_1m/4 — linear rise, index flat → improving-ish edge
    assert r["trend"] in ("improving", "fading")
    # MA distance: price above its 20DMA after a rise
    assert r["dist_ma20"] > 0
    # z-scores exist and are finite
    assert np.isfinite(r["rel_1m_z"])

    # signal engine: washed-out name flags with factors that sum to score
    weak = base[:-22] + list(np.linspace(100, 80, 22))
    m2 = signals.name_metrics({"BBB": frame(weak), "CCC": frame(stock),
                               "DDD": frame(base), "IDX": frame(base)}, "IDX", 0, 1.3)
    m2["theme"] = "T"
    m2 = signals.classify_signals(m2, {"T": 0.5})
    b = m2.loc["BBB"]
    assert b["signal"] in ("Washed out", "Bounce watch"), b["signal"]
    assert abs(sum(p for _, p in b["factors"]) - b["score"]) < 0.051
    print("all metric checks passed")


if __name__ == "__main__":
    main()
