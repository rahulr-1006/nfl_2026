"""Cross-book EV backtest for player props: does comparing an execution
book's price against Pinnacle's devigged fair value, at a matching line,
find bets that actually win at the rate the edge implies?

**Scope, stated plainly: this is not a CLV backtest.** The historical props
pull (`src/collect/props_historical.py`) captures one snapshot per game,
near kickoff -- there's no earlier "entry" price to compare against a
"close" the way the CLV thesis (`src/clv/metrics.py`) works for mainline
markets. What this CAN test: whether, at a single point in time, an
execution book's price disagrees with Pinnacle's fair value enough to flag
a positive-EV bet, and whether those flagged bets actually win at a rate
consistent with the edge once graded against real outcomes -- a
same-moment cross-book mispricing test, not a market-timing one.

Reuses `src/signal/live_scan.py`'s exact approach (Pinnacle fair vs.
execution-book price, `expected_value` from `src/signal/sizing.py`), just
applied to props instead of moneyline, matched on the exact prop line --
no line-shopping across different numbers, same reasoning `live_scan.py`
gives for why it stays moneyline-only for now.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from src.model.baseline import market_baseline
from src.signal.sizing import expected_value

EXECUTION_BOOKS = ("draftkings", "fanduel", "betmgm")
DEFAULT_EDGE_THRESHOLD = 0.02  # 2% EV per dollar staked, same default as live_scan.py


def pinnacle_fair_probs(props: pd.DataFrame) -> pd.DataFrame:
    """One row per (event_id, player_name, prop_stat) with both a Pinnacle
    Over and Under price at the SAME line: devigged fair Over/Under
    probabilities. Groups where Pinnacle's Over and Under lines don't match
    (rare -- 4 of 4998 in the 2024-season pull) are dropped: can't devig a
    market where the two sides aren't quoting the same number.
    """
    pin = props[props["book"] == "pinnacle"]
    wide = pin.pivot_table(
        index=["event_id", "player_name", "prop_stat", "line"], columns="side", values="price_american", aggfunc="first"
    ).reset_index()
    if not {"over", "under"}.issubset(wide.columns):
        return pd.DataFrame(columns=["event_id", "player_name", "prop_stat", "line", "over_fair", "under_fair"])
    wide = wide.dropna(subset=["over", "under"])
    if wide.empty:
        return pd.DataFrame(columns=["event_id", "player_name", "prop_stat", "line", "over_fair", "under_fair"])
    wide["over_fair"] = wide.apply(lambda r: market_baseline([int(r.over), int(r.under)], side_index=0), axis=1)
    wide["under_fair"] = wide.apply(lambda r: market_baseline([int(r.over), int(r.under)], side_index=1), axis=1)
    return wide[["event_id", "player_name", "prop_stat", "line", "over_fair", "under_fair"]]


def find_prop_ev_spots(
    props: pd.DataFrame,
    threshold: float = DEFAULT_EDGE_THRESHOLD,
    books: Sequence[str] = EXECUTION_BOOKS,
) -> pd.DataFrame:
    """One row per (event, player, prop_stat, line, side, book) where
    `book`'s price beats Pinnacle's devigged fair probability by at least
    `threshold` in expected value, matched on the exact same line.
    """
    fair = pinnacle_fair_probs(props)
    if fair.empty:
        return pd.DataFrame()

    exe = props[props["book"].isin(books)].copy()
    merged = exe.merge(fair, on=["event_id", "player_name", "prop_stat", "line"], how="inner")
    if merged.empty:
        return pd.DataFrame()

    merged["fair_prob"] = merged.apply(lambda r: r.over_fair if r.side == "over" else r.under_fair, axis=1)
    merged["edge"] = merged.apply(lambda r: expected_value(r.fair_prob, r.price_decimal), axis=1)

    spots = merged[merged["edge"] >= threshold].copy()
    return spots.sort_values("edge", ascending=False).reset_index(drop=True)
