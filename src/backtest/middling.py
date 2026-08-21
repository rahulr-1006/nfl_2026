"""Middling: betting opposite sides of the SAME game's spread/total at two
different real quotes -- collected at different times and/or from
different books -- such that a real range of final scores wins BOTH bets.

**Why this is a different mechanism than everything else in this project.**
Every other strategy here (`src/signal/live_scan.py`, `src/backtest/props_ev_backtest.py`,
`src/backtest/correlated_props.py`) compares prices at a single point in
time -- cross-book divergence or model-vs-market disagreement. Middling
instead exploits the SAME market moving over real time: bet Team A -3
today, and if the line later drifts to Team A -7 (injury news, sharp
money), bet Team B +7. If the final margin lands in (3, 7), both bets win
outright -- not a hedge, a genuine double win. Outside that window, exactly
one leg wins (never both lose -- see `test_middle_ev_never_loses_both_legs`
for the proof this module relies on and checks empirically).

**Why this had to be built live-first, unlike every other strategy here.**
nflverse's 2015-2024 schedule data is closing-line-only -- there is no
public historical record of a line moving over time, so middling cannot be
backtested against the past the way correlated-props or margin/total
regression were. `PointInTimeStore` (this project's own leakage-safe
odds history) is the only source of real intraday line movement that
exists for this purpose, and it only starts on 2026-08-14. This module is
therefore built and tested against synthetic data now, with its real
track record beginning only once real 2026 games are played -- see
`nfl_clv_case_study.md` for the honest status.

**Pricing reuses this project's own established finding, deliberately not
its regression models' own predictions.** `mu` (the assumed true mean of
the final margin/total) is Pinnacle's own current line
(`pinnacle_reference_line`), not `src/model/train.py`'s margin/total
model output -- because every backtest in this project found the market
beats the model (see paper Sec. 4.5, [[margin_total_models]] in memory).
Using the model's prediction here would knowingly plug in a worse
estimate. `sigma` still comes from the model's own machinery
(`src/model/calibration.py::fit_residual_std`) -- that's a real, useful
reuse, since the model's residual spread around a *good* mu (whichever
mu is used) is a reasonable estimate of the game's actual unpredictability.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import pandas as pd
from scipy.stats import norm

from src.signal.live_scan import EXECUTION_BOOKS
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, Side

# The two sides that make up each middle-able market. Order matters only in
# that it's the order `best_middle_for_game` iterates -- window math itself
# doesn't care which side is "a" or "b".
_MARKET_SIDES: dict[Market, tuple[Side, Side]] = {
    Market.SPREAD: (Side.HOME, Side.AWAY),
    Market.TOTAL: (Side.OVER, Side.UNDER),
}

# Which side of a middle-pair is the "opposite" of which -- a HOME/AWAY or
# OVER/UNDER pair is a valid middle candidate; anything else (same side
# twice, or a cross-market mismatch) is not.
_OPPOSITE_SIDE: dict[Side, Side] = {
    Side.HOME: Side.AWAY,
    Side.AWAY: Side.HOME,
    Side.OVER: Side.UNDER,
    Side.UNDER: Side.OVER,
}


def win_interval(market: Market, side: Side, line: float) -> tuple[float, float]:
    """(lo, hi) bounds, in "true outcome" space (home_margin for SPREAD,
    total_score for TOTAL), where this (market, side, line) leg wins --
    i.e. the exact region `src.store.settlement.settle` would grade WIN.

    Derived directly from `settle`'s own arithmetic, not re-derived from
    scratch:
      - SPREAD/HOME wins iff `home_margin + line > 0` -> `home_margin > -line`
      - SPREAD/AWAY wins iff `away_margin + line > 0`, `away_margin = -home_margin`
        -> `home_margin < line`
      - TOTAL/OVER  wins iff `total - line > 0` -> `total > line`
      - TOTAL/UNDER wins iff `line - total > 0` -> `total < line`

    Only SPREAD and TOTAL are supported -- MONEYLINE has no continuous line
    to move against (there's no window between two moneyline bets), and
    PLAYER_PROP middling would need this project's separate prop-odds path
    (`src/collect/props.py`), not built here (out of scope for this pass,
    the live mainline collector's spread/total data is what's real and
    accumulating right now).
    """
    if market == Market.SPREAD:
        if side == Side.HOME:
            return (-line, math.inf)
        if side == Side.AWAY:
            return (-math.inf, line)
        raise ValueError(f"spread win_interval requires HOME or AWAY, got {side}")
    if market == Market.TOTAL:
        if side == Side.OVER:
            return (line, math.inf)
        if side == Side.UNDER:
            return (-math.inf, line)
        raise ValueError(f"total win_interval requires OVER or UNDER, got {side}")
    raise ValueError(f"middling only supports SPREAD/TOTAL, got {market}")


def line_threshold(market: Market, side: Side, line: float) -> float:
    """The single "true outcome" value this (market, side, line) quote
    implies -- whichever bound of `win_interval` is finite. A mirrored
    HOME -3 / AWAY +3 pair (or OVER 47 / UNDER 47) both imply the same
    threshold (3, or 47) despite opposite signs/directions in `line`
    itself -- this is what makes `pinnacle_reference_line` able to average
    both sides of a quote into one consistent number.
    """
    lo, hi = win_interval(market, side, line)
    return hi if math.isfinite(hi) else lo


def middle_window(
    market: Market, side_a: Side, line_a: float, side_b: Side, line_b: float
) -> tuple[float, float] | None:
    """The overlap of two opposite-side legs' win regions, or None if no
    real (finite, non-empty) window exists.

    Requires `side_a`/`side_b` to be genuine opposites (HOME/AWAY or
    OVER/UNDER) -- same-side pairs would intersect to an unbounded region
    (e.g. two HOME bets at different lines), which isn't a middle and isn't
    even a well-posed probability question, so it's explicitly rejected
    rather than silently returning something misleading.
    """
    if _OPPOSITE_SIDE.get(side_a) != side_b:
        return None
    lo_a, hi_a = win_interval(market, side_a, line_a)
    lo_b, hi_b = win_interval(market, side_b, line_b)
    lo, hi = max(lo_a, lo_b), min(hi_a, hi_b)
    if not math.isfinite(lo) or not math.isfinite(hi) or lo >= hi:
        return None
    return (lo, hi)


@dataclass(frozen=True)
class MiddleOpportunity:
    """One real, concrete middle: two actual quotes (any book/time) on
    opposite sides of the same game's spread or total, whose win regions
    overlap into a genuine window.
    """

    event_id: str
    market: Market
    side_a: Side
    line_a: float
    price_decimal_a: float
    book_a: str
    capture_time_a: pd.Timestamp
    side_b: Side
    line_b: float
    price_decimal_b: float
    book_b: str
    capture_time_b: pd.Timestamp
    window_lo: float
    window_hi: float

    def __post_init__(self) -> None:
        if self.window_hi <= self.window_lo:
            raise ValueError(f"invalid window ({self.window_lo}, {self.window_hi}) -- must be lo < hi")

    @property
    def window_width(self) -> float:
        return self.window_hi - self.window_lo


def _best_line(lines: pd.Series, side: Side) -> float:
    """The single most favorable real line observed for this side, exploiting
    `win_interval`'s monotonicity in `line`: HOME/AWAY/UNDER bettors are
    always better off with a numerically LARGER line (it widens their win
    region); OVER bettors are better off with a numerically SMALLER one
    (see `test_win_interval_is_monotonic_in_line`, which this claim relies
    on and which is checked directly).
    """
    if side in (Side.HOME, Side.AWAY, Side.UNDER):
        return float(lines.max())
    if side == Side.OVER:
        return float(lines.min())
    raise ValueError(f"unsupported side for middling: {side}")


def best_middle_for_game(snapshots: pd.DataFrame, market: Market) -> MiddleOpportunity | None:
    """The single WIDEST middle window achievable from real quotes for one
    game, one market -- across every book and every capture_time present
    in `snapshots` (already restricted to a single event_id and market by
    the caller; this function doesn't group).

    Uses each side's single best-ever quote, not an exhaustive pairwise
    scan across every (quote_a, quote_b) combination. That's not a
    shortcut that loses information: because `win_interval` is monotonic
    in `line` for each side (see `_best_line`), any middle built from two
    *lesser* quotes is a strict subset of the window built from each
    side's best quote -- the best-vs-best window dominates every other
    real pairing available. O(n) per game instead of O(n^2), and the
    number returned is the true best case, not an arbitrary sample of it.

    Returns None if either side has no quote at all, or if the best
    available window doesn't clear a real (positive-width) middle.
    """
    if market not in _MARKET_SIDES:
        raise ValueError(f"middling only supports SPREAD/TOTAL, got {market}")

    df = snapshots.dropna(subset=["line"])
    side_a, side_b = _MARKET_SIDES[market]

    rows: dict[Side, pd.Series] = {}
    for side in (side_a, side_b):
        side_df = df[df["side"] == side.value]
        if side_df.empty:
            return None
        best_line = _best_line(side_df["line"], side)
        # Tie-break on price, not row order: among real quotes at the best
        # line, take the one that actually pays the most -- an arbitrary
        # first-match pick would silently understate the real opportunity.
        candidates = side_df[side_df["line"] == best_line]
        rows[side] = candidates.loc[candidates["price_decimal"].idxmax()]

    row_a, row_b = rows[side_a], rows[side_b]
    window = middle_window(market, side_a, float(row_a["line"]), side_b, float(row_b["line"]))
    if window is None:
        return None

    return MiddleOpportunity(
        event_id=str(row_a["event_id"]),
        market=market,
        side_a=side_a,
        line_a=float(row_a["line"]),
        price_decimal_a=float(row_a["price_decimal"]),
        book_a=str(row_a["book"]),
        capture_time_a=row_a["capture_time"],
        side_b=side_b,
        line_b=float(row_b["line"]),
        price_decimal_b=float(row_b["price_decimal"]),
        book_b=str(row_b["book"]),
        capture_time_b=row_b["capture_time"],
        window_lo=window[0],
        window_hi=window[1],
    )


def pinnacle_reference_line(snapshots: pd.DataFrame, market: Market) -> float | None:
    """A market-consensus estimate of the true outcome (home_margin for
    SPREAD, total_score for TOTAL), for use as `mu` in `middle_ev` --
    Pinnacle's own most recent quote, deliberately NOT this project's
    regression models (see module docstring for why).

    Averages both sides of Pinnacle's latest quote via `line_threshold`
    (which puts HOME/AWAY or OVER/UNDER on the same numeric scale) rather
    than trusting one side alone -- real books' own two sides aren't
    always perfectly mirrored, and the average is the more honest "current
    market view" of the two. Returns None if Pinnacle has no quote for
    this market/game at all (unlike moneyline, spread/total Pinnacle
    coverage isn't guaranteed in this project's live collector -- don't
    assume it silently).
    """
    if market not in _MARKET_SIDES:
        raise ValueError(f"middling only supports SPREAD/TOTAL, got {market}")

    pin = snapshots[(snapshots["book"] == "pinnacle") & (snapshots["market"] == market.value)]
    pin = pin.dropna(subset=["line"])
    if pin.empty:
        return None

    latest_time = pin["capture_time"].max()
    latest = pin[pin["capture_time"] == latest_time]

    thresholds = []
    for side in _MARKET_SIDES[market]:
        side_rows = latest[latest["side"] == side.value]
        if not side_rows.empty:
            thresholds.append(line_threshold(market, side, float(side_rows["line"].iloc[0])))

    if not thresholds:
        return None
    return sum(thresholds) / len(thresholds)


def _interval_prob(lo: float, hi: float, mu: float, sigma: float) -> float:
    """P(lo < X < hi) for X ~ Normal(mu, sigma). Handles +/-inf bounds
    correctly via scipy's own norm.cdf (cdf(inf)=1, cdf(-inf)=0)."""
    return float(norm.cdf(hi, loc=mu, scale=sigma) - norm.cdf(lo, loc=mu, scale=sigma))


def middle_ev(opp: MiddleOpportunity, mu: float, sigma: float, stake_a: float = 2.0, stake_b: float = 2.0) -> dict:
    """Prices a `MiddleOpportunity`'s expected value under a Normal(mu,
    sigma) model of the true outcome, staking `stake_a`/`stake_b` dollars
    on each leg. Defaults to $2 each -- this project's own existing
    per-bet cap (`src/signal/sizing.py::apply_bankroll_caps`), not a new
    convention. Deliberately does NOT attempt a joint 2-leg Kelly
    optimization over `stake_a`/`stake_b` -- that's a real, harder
    problem this project's existing sizing math (single-outcome fractional
    Kelly) doesn't cover, and with zero live track record for this
    strategy yet, optimizing stake split ahead of any real confirmation
    would be tuning a model on vibes. Equal fixed stakes, honestly priced,
    is the appropriate v1.

    Three outcomes, not two: unlike a hedge, a middle usually wins exactly
    one leg (`net_a_only`/`net_b_only`) and sometimes wins BOTH
    (`net_both`). There is no "lose both" outcome for a genuine middle --
    `p_neither` is computed here and should be ~0 by construction (see
    `test_middle_ev_never_loses_both_legs`, which checks this numerically
    across real-shaped inputs); if it's ever meaningfully nonzero for a
    real `MiddleOpportunity`, something upstream built an invalid window.
    """
    if sigma <= 0:
        raise ValueError(f"sigma must be positive, got {sigma}")

    lo_a, hi_a = win_interval(opp.market, opp.side_a, opp.line_a)
    lo_b, hi_b = win_interval(opp.market, opp.side_b, opp.line_b)

    p_win_a = _interval_prob(lo_a, hi_a, mu, sigma)
    p_win_b = _interval_prob(lo_b, hi_b, mu, sigma)
    p_both = _interval_prob(opp.window_lo, opp.window_hi, mu, sigma)
    p_a_only = p_win_a - p_both
    p_b_only = p_win_b - p_both
    p_neither = 1.0 - p_win_a - p_win_b + p_both

    net_both = stake_a * (opp.price_decimal_a - 1) + stake_b * (opp.price_decimal_b - 1)
    net_a_only = stake_a * (opp.price_decimal_a - 1) - stake_b
    net_b_only = stake_b * (opp.price_decimal_b - 1) - stake_a
    net_neither = -(stake_a + stake_b)

    ev = p_both * net_both + p_a_only * net_a_only + p_b_only * net_b_only + p_neither * net_neither

    return {
        "p_both_win": p_both,
        "p_a_only": p_a_only,
        "p_b_only": p_b_only,
        "p_neither": p_neither,
        "net_both_win": net_both,
        "net_a_only": net_a_only,
        "net_b_only": net_b_only,
        "ev": ev,
        "stake_a": stake_a,
        "stake_b": stake_b,
        "total_risked": stake_a + stake_b,
    }


def find_middle_opportunities(
    store: PointInTimeStore,
    sigma_margin: float,
    sigma_total: float,
    books: Sequence[str] = EXECUTION_BOOKS,
    stake: float = 2.0,
    as_of: datetime | None = None,
) -> pd.DataFrame:
    """One row per game where a real, bettable middle exists right now --
    the top-level live scan this module exists to support, mirroring
    `src/signal/live_scan.py::find_positive_ev_spots`'s shape (same
    `store.read_as_of`/`as_of` pattern, same "empty DataFrame if nothing
    found" contract).

    Restricts the two actual legs to `EXECUTION_BOOKS` (this project's five
    real, GPS-verified accounts -- reused from `live_scan.py`, not
    redefined, so a book-list change only ever needs updating in one
    place) -- Pinnacle itself is not bettable and is used only as the `mu`
    reference via `pinnacle_reference_line`, read from the FULL snapshot
    set for that reason, not the execution-book-restricted subset.
    """
    as_of = as_of or datetime.now(UTC)
    df = store.read_as_of(as_of)
    if df.empty:
        return pd.DataFrame()

    df = df[df["market"].isin([Market.SPREAD.value, Market.TOTAL.value])]
    if df.empty:
        return pd.DataFrame()

    bettable = df[df["book"].isin(books)]
    event_meta = df[["event_id", "home_team", "away_team", "event_start_time"]].drop_duplicates("event_id")

    rows = []
    for (event_id, market_str), group in bettable.groupby(["event_id", "market"]):
        market = Market(market_str)
        opp = best_middle_for_game(group, market)
        if opp is None:
            continue

        mu = pinnacle_reference_line(df[df["event_id"] == event_id], market)
        if mu is None:
            continue

        sigma = sigma_margin if market == Market.SPREAD else sigma_total
        pricing = middle_ev(opp, mu=mu, sigma=sigma, stake_a=stake, stake_b=stake)

        rows.append(
            {
                "event_id": event_id,
                "market": market.value,
                "side_a": opp.side_a.value,
                "line_a": opp.line_a,
                "book_a": opp.book_a,
                "price_decimal_a": opp.price_decimal_a,
                "side_b": opp.side_b.value,
                "line_b": opp.line_b,
                "book_b": opp.book_b,
                "price_decimal_b": opp.price_decimal_b,
                "window_lo": opp.window_lo,
                "window_hi": opp.window_hi,
                "window_width": opp.window_width,
                "mu": mu,
                "sigma": sigma,
                **pricing,
            }
        )

    if not rows:
        return pd.DataFrame()

    report = pd.DataFrame(rows).merge(event_meta, on="event_id", how="left")
    return report.sort_values("ev", ascending=False).reset_index(drop=True)
