"""Does the line actually move toward truth? Real 2024 historical movement.

**Two things my first pass got wrong, both fixed here.**

1. Including BOTH sides of a game makes `beat_rate` exactly 0.5000 by
   construction: devigging forces `p_home + p_away = 1`, so `clv_home` is the
   exact negative of `clv_away`. A metric that cannot come out any other way is
   not evidence. Sides are now measured from the HOME side only, and the real
   question is asked directionally instead.
2. The T-6h entry window `(0, 12)` swallowed the close itself at 0.66h, so
   entry == close and CLV was identically 0. Entry windows now exclude anything
   inside `CLOSE_MAX`.

The test that can actually fail: **is the closing fair probability a better
forecast of the result than the earlier one?** That is the CLV premise --
informed money moves the line toward truth. Brier score, lower is better. If the
close is not better, the whole thesis is unsupported on real data.
"""
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from src.clv.metrics import bootstrap_ci
from src.model.baseline import market_baseline
from src.store.pit_store import PointInTimeStore

ANCHOR = "pinnacle"
TARGETS = [120.0, 72.0, 48.0, 24.0, 6.0]
CLOSE_MAX = 2.0
WINDOW = 3.0


def _home_fair(rows: pd.DataFrame) -> float | None:
    w = rows.pivot_table(index="capture_time", columns="side", values="price_american", aggfunc="last")
    if "home" not in w.columns or "away" not in w.columns:
        return None
    w = w.dropna(subset=["home", "away"])
    if w.empty:
        return None
    r = w.iloc[-1]
    return market_baseline([int(r["home"]), int(r["away"])], side_index=0)


def main() -> None:
    store = PointInTimeStore(root="data/snapshots")
    df = store.read_as_of(datetime.now(UTC))
    ml = df[(df.season == 2024) & (df.market == "moneyline") & (df.book == ANCHOR)].copy()
    ml["hours_out"] = (ml.event_start_time - ml.capture_time).dt.total_seconds() / 3600

    n_caps = ml.groupby("event_id")["capture_time"].nunique()
    ml = ml[ml.event_id.isin(n_caps[n_caps > 1].index)]

    sched = pd.read_parquet("data/static/schedules_2015_2025.parquet")
    sched = sched.dropna(subset=["home_score", "away_score"])
    won = {r.game_id: int(r.home_score > r.away_score) for r in sched.itertuples()}

    rows = []
    for eid, g in ml.groupby("event_id"):
        if eid not in won:
            continue
        close = _home_fair(g[g.hours_out <= CLOSE_MAX])
        if close is None:
            continue
        for t in TARGETS:
            w = g[(g.hours_out > max(t - WINDOW, CLOSE_MAX)) & (g.hours_out < t + WINDOW)]
            entry = _home_fair(w)
            if entry is None:
                continue
            rows.append({"event_id": eid, "offset_h": t, "entry": entry,
                         "close": close, "home_won": won[eid]})

    r = pd.DataFrame(rows)
    print(f"games with a series and a result: {r.event_id.nunique()}")
    print(f"(entry, close) pairs             : {len(r):,}\n")

    print("Does the line MOVE, and does it move toward the eventual result?")
    print(f"{'entry':>8} {'n':>5} {'mean|move|':>11} {'Brier entry':>12} {'Brier close':>12} "
          f"{'improvement':>12} {'95% CI':>24}")
    print("-" * 92)
    for t in TARGETS:
        s = r[r.offset_h == t]
        if len(s) < 20:
            continue
        move = (s.close - s.entry).abs()
        b_entry = ((s.entry - s.home_won) ** 2).to_numpy()
        b_close = ((s.close - s.home_won) ** 2).to_numpy()
        diff = b_entry - b_close                     # >0 means the CLOSE is better
        lo, hi = bootstrap_ci(diff, random_state=0)
        print(f"T-{t:5.0f}h {len(s):>5} {move.mean():>11.4f} {b_entry.mean():>12.4f} "
              f"{b_close.mean():>12.4f} {diff.mean():>+12.5f}  ({lo:+.5f}, {hi:+.5f})")

    print("\n'improvement' > 0 means the closing line forecasts the result BETTER")
    print("than the earlier line -- the CLV premise. CI excluding 0 = real.")

    # how often does the line move at all, and by how much?
    print("\nline-movement distribution (|close - entry| in fair probability):")
    for t in TARGETS:
        s = r[r.offset_h == t]
        if len(s) < 20:
            continue
        m = (s.close - s.entry).abs()
        print(f"  T-{t:5.0f}h  median={m.median():.4f}  p90={m.quantile(0.9):.4f}  "
              f"share >1pt={np.mean(m > 0.01):.1%}  share >3pt={np.mean(m > 0.03):.1%}")


if __name__ == "__main__":
    main()
