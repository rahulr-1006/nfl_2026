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

**Player props are first-class here as of 2026-08-23**, not a mainline
afterthought -- this project's only out-of-sample-validated edges live in
prop-adjacent markets (`team_total_props.py`, `props_arbitrage`), while the
moneyline model reliably loses to the market, so props CLV is the measurement
that actually matters for what gets bet. Three things had to be true for that
to work, none of which were before:
  1. Contract-level price selection (`_market_rows`) -- a game carries a quote
     for every listed player, so (book, market, side) alone selects the wrong
     one.
  2. Settlement dispatch (`BacktestEngine._grade`) -- props grade against a
     player's real stat line, not the final score.
  3. Multiple bets per game, under a tracked bankroll -- one prop per game is
     not a real props strategy.

**Honest scope limit on props CLV, stated up front:** this project's
*historical* props pull is a single near-kickoff snapshot per game, so there
is no earlier entry price to measure a close against -- props CLV remains
un-backtestable on 2023-2024 data, for COST rather than impossibility (a prop
series is ~700 credits/game at 7 markets). Mainline is no longer in that
position: 105 games of 2024 now carry a real 6-point series.
It is validated pre-season against synthetic data with known ground truth
(`src/backtest/synthetic_market.py`, `notebooks/clv_tracker_validation.ipynb`)
and measured for real only once the live props scheduler accrues 2026 data.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from src.clv.metrics import clv_price, clv_probability
from src.devig.methods import DEVIG_METHODS
from src.store.pit_store import PointInTimeStore
from src.store.prop_settlement import (
    build_player_stats_index,
    normalize_player_name,
    settle_prop,
)
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
    None means "no bet at this decision point".

    A strategy may return a single order or a list of orders at one
    decision point (2026-08-23) -- props strategies naturally want several
    player props in the same game, unlike the one-contract-per-game
    mainline case this engine originally assumed.

    `player_name`/`prop_stat` are required for `Market.PLAYER_PROP` and must
    be None otherwise -- validated in `__post_init__` so a malformed order
    fails at construction rather than silently pricing the wrong contract.
    """

    market: Market
    side: Side
    line: float | None
    book: str
    stake: float
    player_name: str | None = None
    prop_stat: str | None = None

    def __post_init__(self) -> None:
        if self.market == Market.PLAYER_PROP:
            if not (self.player_name and self.prop_stat):
                raise ValueError("PLAYER_PROP orders require both player_name and prop_stat")
            if self.line is None:
                raise ValueError("PLAYER_PROP orders require a line")
        elif self.player_name is not None or self.prop_stat is not None:
            raise ValueError(f"{self.market} orders must not carry player_name/prop_stat")


Strategy = Callable[[DecisionPoint], "BetOrder | list[BetOrder] | None"]


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
    player_name: str | None = None
    prop_stat: str | None = None
    bankroll_before: float | None = None
    bankroll_after: float | None = None
    # Which scanner produced the bet. None for backtested bets (the strategy is
    # whatever was passed to `run`); set for LIVE bets from `store/bet_log.py`,
    # where `season_review` segments on it. Market type cannot substitute:
    # prop arb and experimental prop EV are both `player_prop` with opposite
    # track records, and pooling them lets one mask the other.
    strategy: str | None = None


def _market_rows(
    snapshots: pd.DataFrame,
    book: str,
    market: Market,
    as_of: datetime,
    player_name: str | None = None,
    prop_stat: str | None = None,
    line: float | None = None,
) -> pd.DataFrame:
    """Rows for one book's quote on one specific *contract*, at or before
    `as_of`.

    **The `player_name`/`prop_stat`/`line` filtering is not optional
    bookkeeping -- it is what makes props correct at all.** A single game
    carries a PLAYER_PROP quote for every listed player (real 2024 data:
    ~650 prop rows per game per this project's own historical pull), so
    filtering on (book, market, side) alone -- which is all this module did
    before 2026-08-23 -- would silently select some *other* player's price.
    Mainline markets have exactly one contract per (book, market) and are
    unaffected; the filters below are no-ops when their arguments are None.

    **`line` is filtered for PLAYER_PROP only, and that asymmetry is
    load-bearing** (a real bug caught by `test_hand_computed_clv_and_win_payout`
    during this build, not a hypothetical): a prop's two sides share one
    line (Over 45.5 / Under 45.5), so filtering by it correctly isolates one
    contract among a player's alternate lines. A spread's two sides carry
    *mirrored* lines (home -4.5 / away +4.5), so filtering by either one
    would keep a single side and silently break the two-sided pair
    `latest_fair_prob` needs to devig at all -- turning every mainline CLV
    number into None. Mainline markets need no line filter regardless, since
    a (book, market) pair already identifies exactly one contract.
    """
    mask = (
        (snapshots["book"] == book)
        & (snapshots["market"] == market.value)
        & (snapshots["capture_time"] <= as_of)
    )
    if player_name is not None:
        mask &= snapshots["player_name"] == player_name
    if prop_stat is not None:
        mask &= snapshots["prop_stat"] == prop_stat
    if line is not None and market == Market.PLAYER_PROP:
        mask &= snapshots["line"] == line
    return snapshots[mask]


def latest_fair_prob(
    snapshots: pd.DataFrame,
    book: str,
    market: Market,
    side: Side,
    as_of: datetime,
    devig_method: str,
    player_name: str | None = None,
    prop_stat: str | None = None,
    line: float | None = None,
) -> float | None:
    """Fair probability for `side`, devigged from `book`'s most recent
    two-sided quote at or before `as_of`. None if `book` never quoted both
    sides of that contract by `as_of`.

    Public (2026-08-22, promoted from `_latest_fair_prob`) -- reused outside
    `BacktestEngine` to extract real Pinnacle fair probabilities from the new
    mainline historical pull for re-scoring the model comparison registry's
    market baseline (see `mainline_historical_odds_reconsidered` memory).

    `player_name`/`prop_stat`/`line` (2026-08-23) select a single prop
    contract -- required for PLAYER_PROP, ignored for mainline markets. See
    `_market_rows` for why omitting them on a prop is a correctness bug, not
    a convenience gap.
    """
    candidates = _market_rows(snapshots, book, market, as_of, player_name, prop_stat, line)
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
    snapshots: pd.DataFrame,
    book: str,
    market: Market,
    side: Side,
    as_of: datetime,
    player_name: str | None = None,
    prop_stat: str | None = None,
    line: float | None = None,
) -> pd.Series | None:
    candidates = _market_rows(snapshots, book, market, as_of, player_name, prop_stat, line)
    candidates = candidates[candidates["side"] == side.value]
    if candidates.empty:
        return None
    return candidates.loc[candidates["capture_time"].idxmax()]


def _parse_kickoffs(schedule: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(
        schedule["gameday"].astype(str) + " " + schedule["gametime"].astype(str), utc=True
    )


class BacktestEngine:
    """Replays a strategy against the real point-in-time store.

    **Bankroll is a hard, tracked constraint (2026-08-23), not a reporting
    afterthought.** This project runs a fixed $100 bankroll with no reloads
    (see `src/signal/sizing.py`'s own framing). Once strategies can place
    several bets per game -- which props require -- "can I actually afford
    this bet right now" becomes a real question that per-bet sizing caps
    alone cannot answer: ten $2 bets on one slate is $20 of simultaneous
    exposure, and nothing in `apply_bankroll_caps` knows about the other
    nine. Games are replayed in kickoff order and settled bet-by-bet, so
    the running bankroll below is chronologically honest: a bet is skipped
    (never silently shrunk) if the remaining bankroll can't cover it.

    `player_stats` is required only to settle `Market.PLAYER_PROP` bets --
    prop grading needs a player's actual stat line, which `GameResult`
    (final score) structurally cannot provide. Dispatching here rather than
    widening `settle()` respects `src/store/prop_settlement.py`'s own stated
    design decision: "forcing one function signature to cover both would be
    the wrong abstraction."
    """

    def __init__(
        self,
        store: PointInTimeStore,
        schedule: pd.DataFrame,
        devig_method: str = "shin",
        closing_book: str = "pinnacle",
        player_stats: pd.DataFrame | None = None,
        bankroll: float = 100.0,
    ):
        self.store = store
        self.schedule = schedule.assign(kickoff=_parse_kickoffs(schedule))
        self.devig_method = devig_method
        self.closing_book = closing_book
        self._results = build_results_index(schedule)
        self.starting_bankroll = bankroll
        self.bankroll = bankroll
        self._prop_stats_index: dict[tuple[str, str], dict[str, float]] | None = None
        if player_stats is not None:
            self._prop_stats_index = {
                (game_id, normalize_player_name(name)): stats
                for (game_id, name), stats in build_player_stats_index(player_stats).items()
            }

    def run(self, strategy: Strategy) -> list[BacktestBet]:
        """Iterates every game in the schedule, in kickoff order, giving
        the strategy a chance to bet at each real decision point (each
        distinct capture_time observed pre-kickoff) until it either places
        bets or the game starts.

        Resets the running bankroll to `starting_bankroll` first, so a
        repeated `run()` is reproducible rather than continuing from
        whatever the previous run left behind.
        """
        self.bankroll = self.starting_bankroll
        bets: list[BacktestBet] = []
        for row in self.schedule.sort_values("kickoff").itertuples():
            bets.extend(self._run_one_game(strategy, row.game_id, row.kickoff))
        return bets

    def _run_one_game(self, strategy: Strategy, event_id: str, kickoff: datetime) -> list[BacktestBet]:
        pre_kickoff = self.store.read_as_of(kickoff, event_id=event_id)
        if pre_kickoff.empty:
            return []

        orders: list[BetOrder] = []
        decision_time = None
        visible = None
        for t in sorted(pre_kickoff["capture_time"].unique()):
            # Re-derived via the store's own leakage guard for every
            # decision point, not sliced locally from pre_kickoff -- a
            # strategy's view must only ever come from the guarded path.
            visible = self.store.read_as_of(t, event_id=event_id)
            ordered = strategy(DecisionPoint(event_id=event_id, decision_time=t, visible_snapshots=visible))
            if ordered is not None:
                orders = [ordered] if isinstance(ordered, BetOrder) else list(ordered)
                if orders:
                    decision_time = t
                    break
        if not orders:
            return []

        # --- Phase 1: PLACE, against one shared decision-time bankroll -------
        # Every order here is placed at the SAME instant, before any of them can
        # possibly settle, so each must be checked against the bankroll as it
        # stands at decision time -- reserving stakes as we go, never crediting
        # a payout.
        #
        # **This was a real look-ahead bug (fixed 2026-08-23).** Payouts used to
        # be credited inside the per-order loop, so order N+1's affordability
        # check saw order N's *result*. On a $2.50 bankroll, two simultaneous $2
        # bets were both placed when the first won and only one when it lost --
        # the engine literally placed more bets in the branch where earlier bets
        # had won, biasing every downstream number optimistically. In a
        # backtester whose entire premise is leakage-free measurement, that
        # invalidated the results it produced.
        bankroll_at_decision = self.bankroll
        available = bankroll_at_decision
        placed: list[BetOrder] = []
        for order in orders:
            if order.stake > available:
                continue  # real simultaneous-exposure limit, not a shrunk stake
            available -= order.stake
            placed.append(order)

        # --- Phase 2: SETTLE, crediting payouts only now ---------------------
        return [
            self._settle_order(order, event_id, decision_time, visible, pre_kickoff, kickoff, bankroll_at_decision)
            for order in placed
        ]

    def _settle_order(
        self,
        order: BetOrder,
        event_id: str,
        decision_time: datetime,
        visible: pd.DataFrame,
        pre_kickoff: pd.DataFrame,
        kickoff: datetime,
        bankroll_at_decision: float,
    ) -> BacktestBet:
        """One already-affordable order -> one priced, CLV-measured, settled
        bet, crediting its payout to the running bankroll.

        Affordability is decided by the caller against a single decision-time
        balance (see `_run_one_game`) -- deliberately NOT here, because doing
        it per-order after settlement is exactly the look-ahead bug this
        split fixes.
        """
        contract = {"player_name": order.player_name, "prop_stat": order.prop_stat, "line": order.line}

        entry = _latest_price(visible, order.book, order.market, order.side, decision_time, **contract)
        if entry is None:
            raise ValueError(
                f"strategy ordered a bet on {order.book}/{order.market}/{order.side} "
                f"({order.player_name}/{order.prop_stat}/{order.line}) "
                f"not visible at decision_time={decision_time} for event {event_id}"
            )

        entry_prob_fair = latest_fair_prob(
            visible, self.closing_book, order.market, order.side, decision_time, self.devig_method, **contract
        )
        close = _latest_price(pre_kickoff, self.closing_book, order.market, order.side, kickoff, **contract)
        close_price_decimal = float(close["price_decimal"]) if close is not None else None
        close_prob_fair = latest_fair_prob(
            pre_kickoff, self.closing_book, order.market, order.side, kickoff, self.devig_method, **contract
        )

        outcome = self._grade(order, event_id)
        payout = payout_for(outcome, order.stake, float(entry["price_decimal"]))

        # `bankroll_before` is the balance at DECISION time -- identical for every
        # bet placed at the same decision point, since none of them had settled
        # when the bet was made. `bankroll_after` walks the running balance as
        # payouts land. Reporting the running balance as `before` would recreate
        # the same look-ahead this split exists to remove.
        if payout is not None:
            self.bankroll += payout

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
            player_name=order.player_name,
            prop_stat=order.prop_stat,
            bankroll_before=bankroll_at_decision,
            bankroll_after=self.bankroll,
        )

    def _grade(self, order: BetOrder, event_id: str) -> Outcome | None:
        """Dispatch to the right settlement path for this market -- game
        score for mainline, a player's real stat line for props. Returns
        None (never a guess) when the needed result isn't available.
        """
        if order.market == Market.PLAYER_PROP:
            if self._prop_stats_index is None:
                raise ValueError(
                    "PLAYER_PROP orders require BacktestEngine(player_stats=...) to settle -- "
                    "prop grading needs a player's stat line, which the schedule's final score can't provide"
                )
            game_stats = self._prop_stats_index.get((event_id, normalize_player_name(order.player_name)))
            if game_stats is None or order.prop_stat not in game_stats:
                return None
            actual = game_stats[order.prop_stat]
            if pd.isna(actual):
                return None
            return settle_prop(order.side, order.line, actual)

        result: GameResult | None = self._results.get(event_id)
        return settle(order.market, order.side, order.line, result) if result is not None else None


def payout_for(outcome: Outcome | None, stake: float, price_decimal: float) -> float | None:
    """Profit (not total return) for a graded bet. Public because live bets in
    `src/store/bet_log.py` settle through this exact function -- a second copy
    of the convention would let live P&L and backtest P&L disagree silently."""
    if outcome is None:
        return None
    if outcome == Outcome.WIN:
        return stake * (price_decimal - 1)
    if outcome == Outcome.LOSS:
        return -stake
    return 0.0
