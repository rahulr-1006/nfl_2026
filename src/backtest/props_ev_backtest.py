"""Cross-book player-prop strategies that don't rely on market timing:
(1) a Pinnacle-anchored EV backtest, and (2) pure cross-book arbitrage.

**Scope, stated plainly: neither is a CLV backtest.** The historical props
pull (`src/collect/props_historical.py`) captures one snapshot per game,
near kickoff -- there's no earlier "entry" price to compare against a
"close" the way the CLV thesis (`src/clv/metrics.py`) works for mainline
markets. Both strategies here work at a single point in time instead.

**`find_prop_ev_spots`**: does an execution book's price disagree with
Pinnacle's devigged fair value enough to flag a positive-EV bet, and do
those flagged bets actually win at a rate consistent with the edge once
graded against real outcomes? Reuses `src/signal/live_scan.py`'s exact
approach (Pinnacle fair vs. execution-book price, `expected_value` from
`src/signal/sizing.py`), applied to props instead of moneyline, matched on
the exact prop line -- no line-shopping across different numbers, same
reasoning `live_scan.py` gives for staying moneyline-only for now.

**`find_arbitrage_spots`**: needs no fair-value model and no Pinnacle at
all -- does the best available Over price at one execution book plus the
best available Under price at another sum to under 100% implied
probability? If so, both sides are placeable and the outcome doesn't
matter -- a risk-free lock, not a predictive edge.
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


def find_arbitrage_spots(props: pd.DataFrame, books: Sequence[str] = EXECUTION_BOOKS) -> pd.DataFrame:
    """One row per (event, player, prop_stat, line) where the best available
    Over price and best available Under price -- both from `books` (real,
    placeable execution books, no Pinnacle, no fair-value model at all) --
    sum to less than 100% implied probability: a risk-free lock, bet both
    sides and win regardless of outcome. Same-book arbitrage can't happen
    (no bookmaker prices its own two-sided market under 100%, that's the
    vig it exists to collect) -- a real hit here means the two legs come
    from two different books that disagree with each other.
    """
    exe = props[props["book"].isin(books)].copy()
    if exe.empty:
        return pd.DataFrame()

    group_cols = ["event_id", "player_name", "prop_stat", "line"]
    over = exe[exe["side"] == "over"]
    under = exe[exe["side"] == "under"]
    if over.empty or under.empty:
        return pd.DataFrame()

    best_over = over.loc[over.groupby(group_cols)["price_decimal"].idxmax()]
    best_under = under.loc[under.groupby(group_cols)["price_decimal"].idxmax()]

    merged = best_over.merge(best_under, on=group_cols, suffixes=("_over", "_under"))
    if merged.empty:
        return pd.DataFrame()

    merged["implied_sum"] = 1 / merged["price_decimal_over"] + 1 / merged["price_decimal_under"]
    merged["arb_margin"] = 1 - merged["implied_sum"]

    arbs = merged[merged["arb_margin"] > 0].copy()
    keep = [*group_cols, "book_over", "book_under", "price_american_over", "price_american_under", "arb_margin"]
    return arbs[keep].sort_values("arb_margin", ascending=False).reset_index(drop=True)
