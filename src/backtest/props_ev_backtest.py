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

EXECUTION_BOOKS = ("draftkings", "fanduel", "betmgm", "betrivers", "williamhill_us")  # williamhill_us = Caesars Sportsbook's Odds API key
DEFAULT_EDGE_THRESHOLD = 0.02  # 2% EV per dollar staked, same default as live_scan.py
# Same reasoning and default as src/signal/live_scan.py::DEFAULT_MAX_CAPTURE_GAP --
# comfortably wider than normal single-poll write jitter, far tighter than a
# real stale-Pinnacle-fallback gap. Found via a 2026-08-21 adversarial audit:
# neither pinnacle_fair_probs nor find_prop_ev_spots ever checked capture_time
# at all -- safe today only because the historical batch-1 pull happens to
# carry exactly one capture_time per game (verified empirically), but the live
# props scheduler (already built, src/collect/props_scheduler.py) polls TWICE
# per event (entry + close, deliberately days apart) -- unguarded, this code
# would silently pair an entry-time execution-book price against a close-time
# Pinnacle read (or vice versa) the moment that data starts flowing through it.
DEFAULT_MAX_CAPTURE_GAP = pd.Timedelta(minutes=30)


def pinnacle_fair_probs(props: pd.DataFrame) -> pd.DataFrame:
    """One row per (event_id, player_name, prop_stat, line) with both a
    Pinnacle Over and Under price at the SAME line, from the LATEST
    capture_time where a COMPLETE (both Over AND Under) pair exists for
    that group -- devigged fair Over/Under probabilities, plus that
    `pinnacle_time` so `find_prop_ev_spots` can check it isn't stale
    relative to whatever execution-book price it gets compared against.

    **Deliberately not "the group's single latest capture_time overall"**
    (a real bug caught by code review 2026-08-21, fixed here): if the
    absolute-latest poll for a group only updated one side (e.g. Pinnacle
    re-priced the Over but the Under didn't move that cycle), taking the
    latest timestamp alone would pick up a one-sided snapshot and drop the
    whole group -- discarding a perfectly valid, fully simultaneous EARLIER
    pair that still exists. Finding the latest timestamp where both sides
    are actually present avoids that.

    Groups where Pinnacle's Over and Under lines don't match (rare -- 4 of
    4998 in the 2024-season pull) are dropped: can't devig a market where
    the two sides aren't quoting the same number.
    """
    group_cols = ["event_id", "player_name", "prop_stat", "line"]
    empty = pd.DataFrame(columns=[*group_cols, "over_fair", "under_fair", "pinnacle_time"])

    pin = props[props["book"] == "pinnacle"]
    if pin.empty:
        return empty

    has_over = pin.loc[pin["side"] == "over", [*group_cols, "capture_time"]].drop_duplicates()
    has_under = pin.loc[pin["side"] == "under", [*group_cols, "capture_time"]].drop_duplicates()
    complete_times = has_over.merge(has_under, on=[*group_cols, "capture_time"])
    if complete_times.empty:
        return empty
    latest_complete = complete_times.groupby(group_cols, as_index=False)["capture_time"].max()

    pin = pin.merge(latest_complete, on=[*group_cols, "capture_time"], how="inner")

    wide = pin.pivot_table(index=group_cols, columns="side", values="price_american", aggfunc="first").reset_index()
    if not {"over", "under"}.issubset(wide.columns):
        return empty

    wide = wide.merge(latest_complete.rename(columns={"capture_time": "pinnacle_time"}), on=group_cols, how="left")
    wide = wide.dropna(subset=["over", "under"])
    if wide.empty:
        return empty

    wide["over_fair"] = wide.apply(lambda r: market_baseline([int(r.over), int(r.under)], side_index=0), axis=1)
    wide["under_fair"] = wide.apply(lambda r: market_baseline([int(r.over), int(r.under)], side_index=1), axis=1)
    return wide[[*group_cols, "over_fair", "under_fair", "pinnacle_time"]]


def find_prop_ev_spots(
    props: pd.DataFrame,
    threshold: float = DEFAULT_EDGE_THRESHOLD,
    books: Sequence[str] = EXECUTION_BOOKS,
    max_capture_gap: pd.Timedelta = DEFAULT_MAX_CAPTURE_GAP,
) -> pd.DataFrame:
    """One row per (event, player, prop_stat, line, side, book) where
    `book`'s price beats Pinnacle's devigged fair probability by at least
    `threshold` in expected value, matched on the exact same line -- and
    captured within `max_capture_gap` of Pinnacle's own price, so a spot is
    never flagged from a stale-vs-fresh comparison (see
    `DEFAULT_MAX_CAPTURE_GAP`'s comment).
    """
    fair = pinnacle_fair_probs(props)
    if fair.empty:
        return pd.DataFrame()

    exe = props[props["book"].isin(books)].copy()
    merged = exe.merge(fair, on=["event_id", "player_name", "prop_stat", "line"], how="inner")
    if merged.empty:
        return pd.DataFrame()

    merged = merged[(merged["capture_time"] - merged["pinnacle_time"]).abs() <= max_capture_gap]
    if merged.empty:
        return pd.DataFrame()

    merged["fair_prob"] = merged.apply(lambda r: r.over_fair if r.side == "over" else r.under_fair, axis=1)
    merged["edge"] = merged.apply(lambda r: expected_value(r.fair_prob, r.price_decimal), axis=1)

    spots = merged[merged["edge"] >= threshold].copy()
    return spots.sort_values("edge", ascending=False).reset_index(drop=True)


def find_arbitrage_spots(props: pd.DataFrame, books: Sequence[str] = EXECUTION_BOOKS) -> pd.DataFrame:
    """One row per (event, player, prop_stat, line, capture_time) where the
    best available Over price and best available Under price at that SAME
    capture_time -- both from `books` (real, placeable execution books, no
    Pinnacle, no fair-value model at all) -- sum to less than 100% implied
    probability: a risk-free lock, bet both sides and win regardless of
    outcome. Same-book arbitrage can't happen (no bookmaker prices its own
    two-sided market under 100%, that's the vig it exists to collect) -- a
    real hit here means the two legs come from two different books that
    disagree with each other.

    Requires the two legs to share an EXACT `capture_time`, not just a
    close one -- matching this project's own established convention
    (`src/signal/live_scan.py::_latest_two_sided_pinnacle`: "a single poll
    always writes both outcomes together"). Without this, best Over and
    best Under were each picked as the single best-EVER price across all
    time independently, which can silently pair an early-poll Over against
    a much-later close-poll Under -- never actually simultaneously
    bettable, not a real arbitrage lock (see `DEFAULT_MAX_CAPTURE_GAP`'s
    comment on `find_prop_ev_spots` for the same failure mode in this
    module's other function). One real snapshot can still produce multiple
    genuine arbs across a game's history as the live props scheduler polls
    more than once -- each is reported as its own row, not collapsed to
    one "best ever" number.
    """
    exe = props[props["book"].isin(books)].copy()
    if exe.empty:
        return pd.DataFrame()

    group_cols = ["event_id", "player_name", "prop_stat", "line"]
    snap_cols = [*group_cols, "capture_time"]
    over = exe[exe["side"] == "over"]
    under = exe[exe["side"] == "under"]
    if over.empty or under.empty:
        return pd.DataFrame()

    best_over = over.loc[over.groupby(snap_cols)["price_decimal"].idxmax()]
    best_under = under.loc[under.groupby(snap_cols)["price_decimal"].idxmax()]

    merged = best_over.merge(best_under, on=snap_cols, suffixes=("_over", "_under"))
    if merged.empty:
        return pd.DataFrame()

    merged["implied_sum"] = 1 / merged["price_decimal_over"] + 1 / merged["price_decimal_under"]
    merged["arb_margin"] = 1 - merged["implied_sum"]

    arbs = merged[merged["arb_margin"] > 0].copy()
    keep = [*snap_cols, "book_over", "book_under", "price_american_over", "price_american_under", "arb_margin"]
    return arbs[keep].sort_values("arb_margin", ascending=False).reset_index(drop=True)
