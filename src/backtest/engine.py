"""Leakage-free point-in-time backtester (blueprint Part C, B.3, B.4).

Reuses src/store/pit_store.PointInTimeStore (the real leakage-guarded
store, already live-collecting) and src/store/settlement (win/loss/push
grading) rather than reimplementing either. This module is the
strategy-execution and CLV/P&L bookkeeping layer on top of them -- not a
second source of truth for odds or outcomes.

CLV is anchored to Pinnacle throughout, per blueprint B.2/B.3: probability
CLV compares Pinnacle's own fair probability at your decision time against
Pinnacle's fair probability at close (pure market movement, independent of
which book you actually bet at). Price CLV compares the price you actually
took (whatever book) against Pinnacle's closing price for the same side.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from src.clv.metrics import clv_price, clv_probability
from src.devig.methods import DEVIG_METHODS
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, Side
from src.store.settlement import GameResult, Outcome, build_results_index, settle


@dataclass(frozen=True)
class DecisionPoint:
    """What a strategy sees when it's given a chance to act.

    `visible_snapshots` is fetched fresh from PointInTimeStore.read_as_of()
    for this exact decision_time -- it is never a locally-sliced subset of
    a larger pull -- so a strategy's view is only ever as trustworthy as
    the store's own leakage guard.
    """

    event_id: str
    decision_time: datetime
    visible_snapshots: pd.DataFrame


@dataclass(frozen=True)
class BetOrder:
    """A strategy's decision to bet, returned from a Strategy callable.
    None means "no bet at this decision point"."""

    market: Market
    side: Side
    line: float | None
    book: str
    stake: float


Strategy = Callable[[DecisionPoint], "BetOrder | None"]


@dataclass(frozen=True)
class BacktestBet:
    event_id: str
    decision_time: datetime
    market: Market
    side: Side
    line: float | None
    book: str
    stake: float
    price_american: int
    price_decimal: float
    entry_prob_fair: float | None
    close_price_decimal: float | None
    close_prob_fair: float | None
    clv_price: float | None
    clv_probability: float | None
    outcome: Outcome | None
    payout: float | None


def _latest_fair_prob(
    snapshots: pd.DataFrame,
    book: str,
    market: Market,
    side: Side,
    as_of: datetime,
    devig_method: str,
) -> float | None:
    """Fair probability for `side`, devigged from `book`'s most recent
    two-sided quote at or before `as_of`. None if `book` never quoted both
    sides of `market` by `as_of`.
    """
    candidates = snapshots[
        (snapshots["book"] == book)
        & (snapshots["market"] == market.value)
        & (snapshots["capture_time"] <= as_of)
    ]
    if candidates.empty:
        return None
    latest_time = candidates["capture_time"].max()
    rows = candidates[candidates["capture_time"] == latest_time]
    if len(rows) != 2 or side.value not in set(rows["side"]):
        return None
    raw = rows.set_index("side")["implied_prob_raw"]
    fair = DEVIG_METHODS[devig_method](tuple(raw.to_numpy()))
    return dict(zip(raw.index, fair.probabilities, strict=True))[side.value]


def _latest_price(
    snapshots: pd.DataFrame, book: str, market: Market, side: Side, as_of: datetime
) -> pd.Series | None:
    candidates = snapshots[
        (snapshots["book"] == book)
        & (snapshots["market"] == market.value)
        & (snapshots["side"] == side.value)
        & (snapshots["capture_time"] <= as_of)
    ]
    if candidates.empty:
        return None
    return candidates.loc[candidates["capture_time"].idxmax()]


def _parse_kickoffs(schedule: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(
        schedule["gameday"].astype(str) + " " + schedule["gametime"].astype(str), utc=True
    )


class BacktestEngine:
    def __init__(
        self,
        store: PointInTimeStore,
        schedule: pd.DataFrame,
        devig_method: str = "shin",
        closing_book: str = "pinnacle",
    ):
        self.store = store
        self.schedule = schedule.assign(kickoff=_parse_kickoffs(schedule))
        self.devig_method = devig_method
        self.closing_book = closing_book
        self._results = build_results_index(schedule)

    def run(self, strategy: Strategy) -> list[BacktestBet]:
        """Iterates every game in the schedule, in kickoff order, giving
        the strategy a chance to bet at each real decision point (each
        distinct capture_time observed pre-kickoff) until it either places
        one bet or the game starts.
        """
        bets = []
        for row in self.schedule.sort_values("kickoff").itertuples():
            bet = self._run_one_game(strategy, row.game_id, row.kickoff)
            if bet is not None:
                bets.append(bet)
        return bets

    def _run_one_game(self, strategy: Strategy, event_id: str, kickoff: datetime) -> BacktestBet | None:
        pre_kickoff = self.store.read_as_of(kickoff, event_id=event_id)
        if pre_kickoff.empty:
            return None

        order = None
        decision_time = None
        visible = None
        for t in sorted(pre_kickoff["capture_time"].unique()):
            # Re-derived via the store's own leakage guard for every
            # decision point, not sliced locally from pre_kickoff -- a
            # strategy's view must only ever come from the guarded path.
            visible = self.store.read_as_of(t, event_id=event_id)
            order = strategy(DecisionPoint(event_id=event_id, decision_time=t, visible_snapshots=visible))
            if order is not None:
                decision_time = t
                break
        if order is None:
            return None

        entry = _latest_price(visible, order.book, order.market, order.side, decision_time)
        if entry is None:
            raise ValueError(
                f"strategy ordered a bet on {order.book}/{order.market}/{order.side} "
                f"not visible at decision_time={decision_time} for event {event_id}"
            )

        entry_prob_fair = _latest_fair_prob(
            visible, self.closing_book, order.market, order.side, decision_time, self.devig_method
        )
        close = _latest_price(pre_kickoff, self.closing_book, order.market, order.side, kickoff)
        close_price_decimal = float(close["price_decimal"]) if close is not None else None
        close_prob_fair = _latest_fair_prob(
            pre_kickoff, self.closing_book, order.market, order.side, kickoff, self.devig_method
        )

        result: GameResult | None = self._results.get(event_id)
        outcome = settle(order.market, order.side, order.line, result) if result is not None else None
        payout = _payout(outcome, order.stake, float(entry["price_decimal"]))

        return BacktestBet(
            event_id=event_id,
            decision_time=decision_time,
            market=order.market,
            side=order.side,
            line=order.line,
            book=order.book,
            stake=order.stake,
            price_american=int(entry["price_american"]),
            price_decimal=float(entry["price_decimal"]),
            entry_prob_fair=entry_prob_fair,
            close_price_decimal=close_price_decimal,
            close_prob_fair=close_prob_fair,
            clv_price=clv_price(float(entry["price_decimal"]), close_price_decimal)
            if close_price_decimal is not None
            else None,
            clv_probability=clv_probability(entry_prob_fair, close_prob_fair)
            if entry_prob_fair is not None and close_prob_fair is not None
            else None,
            outcome=outcome,
            payout=payout,
        )


def _payout(outcome: Outcome | None, stake: float, price_decimal: float) -> float | None:
    if outcome is None:
        return None
    if outcome == Outcome.WIN:
        return stake * (price_decimal - 1)
    if outcome == Outcome.LOSS:
        return -stake
    return 0.0
