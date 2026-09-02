"""'Today's read' — 4–6 deterministic insight cards.

Each card: title, why-it-matters body, direction (up/flat/down), clickable
tickers. Auto-written from the numbers, same rules every day; every claim
is checkable in the tables below it.
"""
from __future__ import annotations

import pandas as pd


def todays_read(mkt_cfg: dict, m: pd.DataFrame, b: pd.DataFrame,
                tape: dict[str, dict], regime: dict) -> list[dict]:
    bench = mkt_cfg["benchmark_label"]
    cards: list[dict] = []

    # 1 — the tape + regime in one card
    bt = tape.get(mkt_cfg["benchmark"], {})
    cards.append({
        "title": f"{bench}: {bt.get('ret_1d', 0):+.1%} today · regime {regime['label'].lower()}",
        "body": (f"{bt.get('ret_1m', 0):+.1%} over the month. "
                 + " · ".join(f"{f['name']}: {f['state']}" for f in regime["factors"][:3]) + "."),
        "tickers": [], "dir": "up" if bt.get("ret_1d", 0) > 0 else "down",
    })

    # 2 — strongest broad theme
    broad = b[b["breadth"] >= 0.6]
    if not broad.empty:
        t = broad.sort_values("rel_1w", ascending=False).iloc[0]
        cards.append({
            "title": f"{t.name} continue{'s' if not t.name.endswith('s') else ''} to lead",
            "body": (f"Outperformed the {bench} by {t['rel_1w']:+.1%} this week with "
                     f"{t['breadth']:.0%} of the group participating — broad moves like this "
                     f"are the healthy kind, not one name dragging an index."),
            "tickers": t["leaders"], "dir": "up",
        })

    # 3 — emerging turn (the "what changed" card)
    emerging = b[b["phase"] == "Emerging"]
    if not emerging.empty:
        t = emerging.sort_values("accel", ascending=False).iloc[0]
        cards.append({
            "title": f"{t.name} may be turning",
            "body": (f"Still {t['rel_1m']:+.1%} vs {bench} on the month, but this week flipped "
                     f"positive ({t['rel_1w']:+.1%}) with momentum accelerating. Early — worth "
                     f"watching for confirmation, not chasing."),
            "tickers": t["leaders"], "dir": "up",
        })

    # 4 — fading leader
    fading = b[(b["phase"] == "Rolling over") | ((b["trend"] == "fading") & (b["rel_1m"] > 0.03))]
    if not fading.empty:
        t = fading.sort_values("rel_1m", ascending=False).iloc[0]
        cards.append({
            "title": f"{t.name}: leadership losing steam",
            "body": (f"Still {t['rel_1m']:+.1%} vs {bench} over the month but the last week went "
                     f"{t['rel_1w']:+.1%} — momentum is decelerating. If you're long, this is "
                     f"where gains get protected, not added to."),
            "tickers": t["leaders"], "dir": "down",
        })

    # 5 — weakest theme
    w = b.sort_values("rel_1m").iloc[0]
    cards.append({
        "title": f"{w.name} stay in the penalty box",
        "body": (f"{w['rel_1m']:+.1%} vs {bench} on the month with breadth at {w['breadth']:.0%}. "
                 f"Weak groups can stay weak — nothing to do here until buyers actually show up."),
        "tickers": w["leaders"], "dir": "down",
    })

    # 6 — dollar-flow concentration
    f = b.sort_values("flow_bps", ascending=False).iloc[0]
    cards.append({
        "title": f"Trading dollars concentrated in {f.name}",
        "body": (f"{f['flow_bps']:.0f} bps of tracked-universe turnover went through this group "
                 f"today at {f['vol_ratio']:.1f}× normal volume — where the money actually is, "
                 f"regardless of price direction."),
        "tickers": f["leaders"], "dir": "flat",
    })
    return cards[:6]
