"""Steam-move detection: synchronized, same-direction line movement across
multiple books at once -- a classic sharp-money tell, distinct from every
other live signal in this project.

**Why this is a different mechanism than middling or the live scanner.**
`src/backtest/middling.py` exploits ONE line drifting over time (or across
books) into a genuine double-win window. `src/signal/live_scan.py` compares
ONE execution book against Pinnacle at a single instant. Steam is neither:
it's the observation that when several INDEPENDENT books move their price in
the SAME direction within a tight time window, that's a real signal
professional/sharp money hit the market hard enough to move it broadly, not
just one book's own line-setting choice. The actionable follow-through: any
book that HASN'T yet joined the steam is still quoting the pre-steam price --
a real, live, stale number worth betting before it corrects.

**Same honest ceiling as middling.** This is built and tested against
synthetic data now; its real track record only starts once enough live 2026
line movement accumulates (`src/backtest/middling.py`'s module docstring
explains why nflverse has no historical intraday data to backtest this kind
of thing against at all -- the same applies here).

**Deliberately reuses, not reinvents, this project's existing pricing math.**
`win_interval`/`line_threshold`/`pinnacle_reference_line` come straight from
`middling.py` -- the "true outcome" region a bet wins in, and the
market-consensus estimate of that outcome, are exactly the same questions
here as they are there. `expected_value`/`fractional_kelly`/
`apply_bankroll_caps` come from `src/signal/sizing.py`, unchanged, the same
sizing math every other +EV spot in this project uses.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import pandas as pd
from scipy.stats import norm

from src.backtest.middling import pinnacle_reference_line, win_interval
from src.signal.live_scan import EXECUTION_BOOKS
from src.signal.sizing import apply_bankroll_caps, expected_value, fractional_kelly
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, Side

DEFAULT_STEAM_WINDOW = pd.Timedelta(hours=1)


@dataclass(frozen=True)
class BookMove:
    """One book's net line change for one game/market/side, from its
    earliest to latest real snapshot in the window being scanned.
    `direction == 0` means that book never moved (or was only quoted once).
    """

    book: str
    from_line: float
    to_line: float
    from_time: pd.Timestamp
    to_time: pd.Timestamp

    @property
    def direction(self) -> float:
        return self.to_line - self.from_line


def book_moves(snapshots: pd.DataFrame, market: Market, side: Side) -> list[BookMove]:
    """One `BookMove` per book with real quotes for this game/market/side --
    each book's own earliest-to-latest line change. `snapshots` is already
    restricted to a single event_id (mirrors `middling.py::best_middle_for_game`'s
    precondition -- this function doesn't group across games, callers do).
    """
    df = snapshots[(snapshots["market"] == market.value) & (snapshots["side"] == side.value)].dropna(subset=["line"])
    moves = []
    for book, group in df.groupby("book"):
        ordered = group.sort_values("capture_time")
        first, last = ordered.iloc[0], ordered.iloc[-1]
        moves.append(
            BookMove(
                book=str(book),
                from_line=float(first["line"]),
                to_line=float(last["line"]),
                from_time=first["capture_time"],
                to_time=last["capture_time"],
            )
        )
    return moves


def _largest_time_cluster(moves: Sequence[BookMove], window: pd.Timedelta) -> list[BookMove]:
    """The largest subset of `moves` whose `to_time`s all fall within
    `window` of each other -- classic "max points in a sliding window"
    over a small n (this project's book list is at most a handful of real
    accounts plus Pinnacle), so the simple O(n^2) scan is more than fast
    enough and easy to verify correct by hand.
    """
    ordered = sorted(moves, key=lambda m: m.to_time)
    best: list[BookMove] = []
    for i in range(len(ordered)):
        cluster = [ordered[i]]
        for j in range(i + 1, len(ordered)):
            if ordered[j].to_time - ordered[i].to_time <= window:
                cluster.append(ordered[j])
            else:
                break
        if len(cluster) > len(best):
            best = cluster
    return best


@dataclass(frozen=True)
class SteamMove:
    """A real, detected steam move: `min_books` or more books moved the
    same direction within `window`, for one game/market/side.
    `stale_books` are the ones (restricted to real, bettable
    `EXECUTION_BOOKS`) that have NOT joined the move yet -- the actionable
    part of a steam detection, not just the observation itself.
    """

    event_id: str
    market: Market
    side: Side
    direction: float  # +1 or -1, the sign of the synchronized move
    books_moved: list[str]
    window_start: pd.Timestamp
    window_end: pd.Timestamp
    stale_books: list[str]


def detect_steam_move(
    snapshots: pd.DataFrame,
    market: Market,
    side: Side,
    min_books: int = 3,
    window: pd.Timedelta = DEFAULT_STEAM_WINDOW,
    books: Sequence[str] = EXECUTION_BOOKS,
) -> SteamMove | None:
    """Scans one game's real snapshot history (already restricted to a
    single event_id) for a genuine steam move on `market`/`side`.

    A steam move requires at least `min_books` DISTINCT books to have moved
    their line in the SAME direction, with all of those moves' `to_time`s
    landing within `window` of each other (via `_largest_time_cluster`) --
    a handful of books drifting independently over days is normal line
    movement (`middling.py`'s target), not steam; several books moving
    together in a tight window is the synchronized signal steam actually
    means. Not restricted to `books` for DETECTING the move (Pinnacle and
    every quoted book count toward `min_books`/the cluster -- a real steam
    move is a market-wide phenomenon, not specific to which books are
    bettable) -- only `stale_books` is restricted to `EXECUTION_BOOKS`,
    since that's the part that has to be a real, placeable bet.

    Returns `None` if no direction clears `min_books` within the window.
    """
    all_moves = book_moves(snapshots, market, side)
    moving = [m for m in all_moves if m.direction != 0]
    if len(moving) < min_books:
        return None

    for sign in (1, -1):
        same_direction = [m for m in moving if (m.direction > 0) == (sign > 0)]
        if len(same_direction) < min_books:
            continue
        cluster = _largest_time_cluster(same_direction, window)
        if len(cluster) < min_books:
            continue

        moved_books = {m.book for m in cluster}
        stale_books = sorted(m.book for m in all_moves if m.book in books and m.book not in moved_books)
        event_id = str(snapshots["event_id"].iloc[0])
        return SteamMove(
            event_id=event_id,
            market=market,
            side=side,
            direction=float(sign),
            books_moved=sorted(moved_books),
            window_start=min(m.to_time for m in cluster),
            window_end=max(m.to_time for m in cluster),
            stale_books=stale_books,
        )
    return None


def _interval_prob(lo: float, hi: float, mu: float, sigma: float) -> float:
    """P(lo < X < hi) for X ~ Normal(mu, sigma) -- same formula as
    `middling.py::_interval_prob`, kept as a small local copy rather than
    importing a private helper across modules."""
    return float(norm.cdf(hi, loc=mu, scale=sigma) - norm.cdf(lo, loc=mu, scale=sigma))


def price_stale_book_opportunity(
    stale_line: float,
    stale_price_decimal: float,
    market: Market,
    side: Side,
    mu: float,
    sigma: float,
    stake: float = 2.0,
) -> dict:
    """Prices betting a stale book's CURRENT (pre-steam) line/price as a
    single straight bet, under a Normal(mu, sigma) model of the true
    outcome -- `mu` should be Pinnacle's post-steam reference line
    (`pinnacle_reference_line`, already incorporating the steam), `sigma`
    the relevant model's residual std (`fit_residual_std` on the margin or
    total regression, same reuse `middling.py` makes).

    A single-leg analogue of `middling.py::middle_ev`'s pricing -- reuses
    the exact same `win_interval` + Normal-CDF approach, just for one bet
    instead of a two-leg window.
    """
    if sigma <= 0:
        raise ValueError(f"sigma must be positive, got {sigma}")
    lo, hi = win_interval(market, side, stale_line)
    p_win = _interval_prob(lo, hi, mu, sigma)
    edge = expected_value(p_win, stale_price_decimal)
    raw_stake = fractional_kelly(p_win, stale_price_decimal) * 100
    suggested_stake = apply_bankroll_caps(raw_stake) if raw_stake > 0 else 0.0

    return {
        "p_win": p_win,
        "price_decimal": stale_price_decimal,
        "edge": edge,
        "suggested_stake": suggested_stake,
    }


def find_steam_opportunities(
    store: PointInTimeStore,
    sigma_margin: float,
    sigma_total: float,
    min_books: int = 3,
    window: pd.Timedelta = DEFAULT_STEAM_WINDOW,
    books: Sequence[str] = EXECUTION_BOOKS,
    as_of: datetime | None = None,
) -> pd.DataFrame:
    """One row per (game, market, side, stale book) where a real steam
    move was detected AND at least one real execution book hasn't joined
    it yet -- mirrors `middling.py::find_middle_opportunities`'s shape
    (same `store.read_as_of`/`as_of` pattern, same "empty DataFrame if
    nothing found" contract).
    """
    as_of = as_of or datetime.now(UTC)
    df = store.read_as_of(as_of)
    if df.empty:
        return pd.DataFrame()

    df = df[df["market"].isin([Market.SPREAD.value, Market.TOTAL.value])]
    if df.empty:
        return pd.DataFrame()

    event_meta = df[["event_id", "home_team", "away_team", "event_start_time"]].drop_duplicates("event_id")

    market_sides = {Market.SPREAD: (Side.HOME, Side.AWAY), Market.TOTAL: (Side.OVER, Side.UNDER)}
    rows = []
    for event_id, event_df in df.groupby("event_id"):
        for market, sides in market_sides.items():
            for side in sides:
                steam = detect_steam_move(event_df, market, side, min_books=min_books, window=window, books=books)
                if steam is None or not steam.stale_books:
                    continue

                mu = pinnacle_reference_line(event_df, market)
                if mu is None:
                    continue
                sigma = sigma_margin if market == Market.SPREAD else sigma_total

                for stale_book in steam.stale_books:
                    book_rows = event_df[
                        (event_df["market"] == market.value)
                        & (event_df["side"] == side.value)
                        & (event_df["book"] == stale_book)
                    ].dropna(subset=["line"])
                    if book_rows.empty:
                        continue
                    latest = book_rows.sort_values("capture_time").iloc[-1]
                    pricing = price_stale_book_opportunity(
                        stale_line=float(latest["line"]),
                        stale_price_decimal=float(latest["price_decimal"]),
                        market=market,
                        side=side,
                        mu=mu,
                        sigma=sigma,
                    )
                    if pricing["edge"] <= 0:
                        continue
                    rows.append(
                        {
                            "event_id": event_id,
                            "market": market.value,
                            "side": side.value,
                            "stale_book": stale_book,
                            "stale_line": float(latest["line"]),
                            # When the stale price was actually sampled -- the
                            # clock CLV latency is measured against.
                            "capture_time": latest["capture_time"],
                            "books_moved": ",".join(steam.books_moved),
                            "n_books_moved": len(steam.books_moved),
                            "steam_direction": steam.direction,
                            "window_start": steam.window_start,
                            "window_end": steam.window_end,
                            "mu": mu,
                            "sigma": sigma,
                            **pricing,
                        }
                    )

    if not rows:
        return pd.DataFrame()

    report = pd.DataFrame(rows).merge(event_meta, on="event_id", how="left")
    return report.sort_values("edge", ascending=False).reset_index(drop=True)
