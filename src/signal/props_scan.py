"""Live player-prop scanning: cross-book arbitrage and Pinnacle-anchored EV,
wired to the same SMS alert path the moneyline scanner already uses.

**Why this module exists at all.** Until 2026-08-23 the only market with live
alerting was moneyline (`src/signal/live_scan.py`) -- the one market this
project's own backtests show reliably LOSES to Pinnacle. Every
out-of-sample-validated edge here is prop-adjacent (props cross-book arb,
correlated/team-total props), and none of it had a live path. The pricing
functions already existed and were tested; they were just never wired to live
data. This module is that wiring.

**A separate module, not more branches in `live_scan.py`.** That module is
moneyline-shaped end to end -- `_latest_two_sided_pinnacle` pivots on
home/away, `format_alert_message` names teams and says "ML". Props are keyed by
(event, player, stat, line) and need their own alert text. Sharing the alert
*state machine* (`new_or_improved_spots`/`record_alerts`) while keeping the
scanning separate is the right split.

**Two signals with deliberately different confidence, and the code says so.**
  - `find_live_prop_arb_spots` -- cross-book arbitrage. Mathematically
    guaranteed if both legs are actually placeable: no model, no fair-value
    estimate, just two books whose prices sum under 100%. This project measured
    65 real such spots in 2024, concentrated in receptions/passing-TDs, traced
    to a systematic vig-skew rather than noise. Alerts confidently.
  - `find_live_prop_ev_spots` -- execution book vs. Pinnacle's devigged fair
    value. **This tested NULL on real 2024 data** (49.85% win rate, bootstrap CI
    spanning zero, non-monotonic threshold sweep -- see the props_ev_backtest
    memory). It is included because the live setting genuinely differs from that
    batch test (real intraday prices, not one near-kickoff snapshot), but it is
    labeled EXPERIMENTAL in the alert text and gated behind a higher default
    threshold. Presenting it as confirmed edge would contradict this project's
    own recorded finding.

Both delegate to `src/backtest/props_ev_backtest.py`'s existing, tested
`find_arbitrage_spots`/`find_prop_ev_spots` -- the pricing is not reimplemented
here.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import pandas as pd

from src.backtest.props_ev_backtest import (
    DEFAULT_MAX_CAPTURE_GAP,
    EXECUTION_BOOKS,
    find_arbitrage_spots,
    find_prop_ev_spots,
)
from src.signal.live_scan import upcoming_only
from src.store.pit_store import PointInTimeStore

# Deliberately higher than live_scan.py's 2% moneyline threshold: the props-EV
# signal tested null, so it has to clear a materially larger bar before it's
# worth interrupting someone's day. Not tuned on data -- chosen to be visibly
# conservative given a null backtest.
DEFAULT_PROP_EV_THRESHOLD = 0.05
# Arb margins in this project's real 2024 data ran 0.79% mean / 1.61% max, and
# the props_arbitrage memory flags that sub-2% margins are likely eaten by
# execution latency. A floor above 0 keeps the alert channel from filling with
# spots too thin to actually execute.
DEFAULT_ARB_MARGIN_THRESHOLD = 0.005
# An ABSOLUTE freshness bound, distinct from `DEFAULT_MAX_CAPTURE_GAP` (which only
# bounds the RELATIVE gap between two prices being compared). Without it, "latest
# quote for this contract" can be arbitrarily old: a player is ruled out Thursday,
# both books pull the prop, and its last-ever quote -- carrying a real arb margin --
# still looks current on Sunday morning because the game hasn't kicked off yet.
# The scanner would text a lock that no longer exists on any board. Wider than the
# 30-min dense polling interval so a single missed poll doesn't suppress real spots,
# tight enough that a pulled contract goes quiet quickly.
DEFAULT_MAX_QUOTE_AGE = pd.Timedelta(hours=2)


def _fresh_only(df: pd.DataFrame, as_of: datetime, max_age: pd.Timedelta) -> pd.DataFrame:
    """Drop quotes older than `max_age` -- see `DEFAULT_MAX_QUOTE_AGE` for why
    an absolute bound is needed on top of `upcoming_only`.
    """
    if df.empty:
        return df
    return df[(as_of - df["capture_time"]) <= max_age]


def _live_props(store: PointInTimeStore, as_of: datetime | None = None) -> pd.DataFrame:
    """Every player-prop snapshot for an UPCOMING game, via the store's own
    leakage-guarded read path (not a raw file scan).

    `upcoming_only` is essential, not defensive: this store also holds the
    full 2023-2024 historical props backfill, and without the filter a live
    scan flags hundreds of spots on games finished months ago -- see that
    function's docstring for the real dry-run numbers.
    """
    as_of = as_of or datetime.now(UTC)
    df = upcoming_only(store.read_as_of(as_of), as_of)
    if df.empty:
        return df
    return df[df["market"] == "player_prop"]


def find_live_prop_arb_spots(
    store: PointInTimeStore,
    as_of: datetime | None = None,
    books: Sequence[str] = EXECUTION_BOOKS,
    min_margin: float = DEFAULT_ARB_MARGIN_THRESHOLD,
    max_quote_age: pd.Timedelta = DEFAULT_MAX_QUOTE_AGE,
) -> pd.DataFrame:
    """Cross-book prop arbitrage currently on the board, margin-filtered.

    Only the LATEST capture_time per contract is considered -- `find_arbitrage_spots`
    reports every historical arb in whatever frame it's given, which is right
    for a backtest and wrong for a live alert (a lock that existed six hours
    ago is not actionable now).

    `max_quote_age` then bounds that latest quote in ABSOLUTE terms: "newest
    price for this contract" is not the same as "current", and a pulled
    contract's final quote would otherwise alert indefinitely.
    """
    as_of = as_of or datetime.now(UTC)
    props = _fresh_only(_live_props(store, as_of), as_of, max_quote_age)
    if props.empty:
        return pd.DataFrame()

    group_cols = ["event_id", "player_name", "prop_stat", "line"]
    latest = props.groupby(group_cols)["capture_time"].transform("max")
    props = props[props["capture_time"] == latest]

    spots = find_arbitrage_spots(props, books=books)
    if spots.empty:
        return spots
    return spots[spots["arb_margin"] >= min_margin].reset_index(drop=True)


def find_live_prop_ev_spots(
    store: PointInTimeStore,
    as_of: datetime | None = None,
    threshold: float = DEFAULT_PROP_EV_THRESHOLD,
    books: Sequence[str] = EXECUTION_BOOKS,
    max_capture_gap: pd.Timedelta = DEFAULT_MAX_CAPTURE_GAP,
    max_quote_age: pd.Timedelta = DEFAULT_MAX_QUOTE_AGE,
) -> pd.DataFrame:
    """Execution-book prop prices beating Pinnacle's devigged fair value.

    **Experimental** -- see the module docstring: this signal tested null on
    real 2024 data. `threshold` defaults deliberately high.

    `max_capture_gap` bounds the RELATIVE gap between the book price and the
    Pinnacle price it's compared against; `max_quote_age` bounds both in
    ABSOLUTE terms. Two stale-but-mutually-consistent prices pass the former
    and fail the latter, which is the correct outcome for a live alert.

    **Only the LATEST capture per contract**, same as `find_live_prop_arb_spots`
    and for the same reason -- this was missing until 2026-09-21 and it was a
    real defect, not a nicety. Inside the 2h freshness window a contract can have
    several captures, and without the filter each one became its own "spot": one
    scan emitted the same player/stat/line/book twice at two prices (e.g. 122 and
    118). That inflated the shadow log with non-independent observations --
    measured at **22 of 96 prop_ev alert legs redundant** -- which narrows the CI
    on a metric the go/no-go decision reads.
    """
    as_of = as_of or datetime.now(UTC)
    props = _fresh_only(_live_props(store, as_of), as_of, max_quote_age)
    if props.empty:
        return pd.DataFrame()

    # Keyed per SIDE as well as contract, unlike the arb scanner: arb pairs the
    # two sides against each other so it wants them together, while an EV spot is
    # one-sided and over/under are independently priced quotes.
    group_cols = ["event_id", "player_name", "prop_stat", "line", "book", "side"]
    present = [c for c in group_cols if c in props.columns]
    latest = props.groupby(present)["capture_time"].transform("max")
    props = props[props["capture_time"] == latest]

    return find_prop_ev_spots(props, threshold=threshold, books=books, max_capture_gap=max_capture_gap)


def _fmt_american(price: float) -> str:
    price = int(price)
    return f"+{price}" if price > 0 else str(price)


def format_arb_alert_message(row: pd.Series) -> str:
    """Arb alerts name BOTH legs and both books -- an arb is only real if both
    are actually placed, so an alert missing one leg is not actionable.
    """
    return (
        f"ARB {row['arb_margin'] * 100:.2f}%: {row['player_name']} {row['prop_stat']} {row['line']} | "
        f"OVER {_fmt_american(row['price_american_over'])} @ {str(row['book_over']).title()} + "
        f"UNDER {_fmt_american(row['price_american_under'])} @ {str(row['book_under']).title()} "
        f"({row['event_id']})"
    )


def format_prop_ev_alert_message(row: pd.Series) -> str:
    return (
        f"[EXPERIMENTAL] Prop EV {row['edge'] * 100:.1f}%: {row['player_name']} {row['prop_stat']} "
        f"{row['side'].upper()} {row['line']} {_fmt_american(row['price_american'])} @ "
        f"{str(row['book']).title()} vs Pinnacle fair {row['fair_prob']:.3f} ({row['event_id']})"
    )


def prop_alert_key(row: pd.Series) -> str:
    """Dedup key for a prop alert.

    **Must include player/stat/line** -- `live_scan.py::_alert_key` is
    `event_id|side|book`, which is unique for moneyline but collides across
    every prop contract in a game, so reusing it would let one alerted player
    suppress alerts for everyone else in the same game.
    """
    if "book_over" in row.index:  # arb: two books, no single side
        return f"arb|{row['event_id']}|{row['player_name']}|{row['prop_stat']}|{row['line']}|{row['book_over']}|{row['book_under']}"
    return f"ev|{row['event_id']}|{row['player_name']}|{row['prop_stat']}|{row['line']}|{row['side']}|{row['book']}"
