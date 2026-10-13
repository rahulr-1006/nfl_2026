"""Reproduce the H1 / H1b Train numbers that froze M=2pp, E=1%.

`analysis/train_results_2026-10-04.md` §5 was produced by scratchpad scripts
that no longer exist. This rebuilds it from committed code only
(`backtest.pinnacle_lag` + `clv.metrics.clustered_bootstrap`), so the freeze can
be re-derived by anyone with the store.

Train only, by construction: the store is read as of 2026-10-04 19:30 ET, before
Week 4's Sunday night kickoff, which is the cut the original run used (62 games:
Weeks 1-4 minus Week 4 SNF/MNF). Nothing from Week 5 onward can be visible.

    .venv/bin/python -m scripts.h1_train_grid
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from src.backtest.pinnacle_lag import (
    detect_moves,
    pinnacle_fair_path,
    score,
    stale_quotes,
)
from src.clv.metrics import clustered_bootstrap
from src.store.pit_store import PointInTimeStore

AS_OF = datetime(2026, 10, 4, 19, 30, tzinfo=ZoneInfo("America/New_York"))
BAD_QUOTE_EV = 0.15
GRID_M = (0.02, 0.03, 0.04)
GRID_E = (0.01, 0.02, 0.03)


def train_props(store: PointInTimeStore) -> pd.DataFrame:
    df = store.read_as_of(AS_OF)
    props = df[(df["market"] == "player_prop") & df["event_id"].str.match(r"2026_0[1-4]_")]
    props = props[(props["capture_time"] < props["event_start_time"]) & (props["event_start_time"] <= AS_OF)]
    assert props["event_id"].str[5:7].astype(int).max() <= 4, "Train must be Weeks 1-4 only"
    return props


def cell(props: pd.DataFrame, path: pd.DataFrame, m: float, e: float, drop_rushing: bool) -> dict:
    bets = stale_quotes(detect_moves(path, m), props, e)
    if bets.empty:
        return {"M": m, "E": e, "n": 0}
    scored = score(bets, path)
    scored = scored[scored["close_ev"].notna() & (scored["entry_ev"] <= BAD_QUOTE_EV)]
    if drop_rushing:
        scored = scored[scored["prop_stat"] != "rushing_yards"]
    boot = clustered_bootstrap(scored["close_ev"], scored["event_id"]) if scored["event_id"].nunique() >= 2 else {}
    return {"M": m, "E": e, "n": len(scored), "games": scored["event_id"].nunique(),
            "close_ev": scored["close_ev"].mean(), "ci_lo": boot.get("ci_lo"), "ci_hi": boot.get("ci_hi"),
            "p": boot.get("p_one_sided"), "reverted": scored["reverted"].mean()}


def main() -> None:
    props = train_props(PointInTimeStore())
    print(f"Train: {props['event_id'].nunique()} games, {len(props):,} pre-kickoff prop rows, as of {AS_OF}")
    path = pinnacle_fair_path(props)

    rows = [cell(props, path, m, e, drop_rushing=False) for m in GRID_M for e in GRID_E]
    print("\nH1 grid (closing EV, game-clustered 95% CI):")
    print(pd.DataFrame(rows).to_string(index=False, float_format=lambda v: f"{v:+.4f}"))

    h1b = cell(props, path, 0.0, 0.01, drop_rushing=True)
    print("\nH1b (M=0, E=1%, rushing excluded):")
    print(pd.Series(h1b).to_string())


if __name__ == "__main__":
    main()
