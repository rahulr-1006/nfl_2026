"""Append-only log of bets actually placed, and the bridge to `BacktestBet`.

CLV needs an entry price, and this is the only place one is recorded for a
real bet. Two rules keep the record trustworthy:

1. Only record what a person knows at bet time. Fair probabilities, the close,
   CLV and settlement are all derived later from the point-in-time store by
   `to_backtest_bets`, so they can't be mistyped and can be recomputed.
2. Never rewrite a row. A log that can be edited after the close can be edited
   because of the close, which is exactly the bias CLV is meant to catch.
   Corrections are new rows that point at the original via `corrects`.

`strategy` is required, not inferred from `market`: prop arbitrage and prop EV
are both `player_prop` but have opposite track records, and `season_review`
segments on strategy.
"""

from __future__ import annotations

import logging
import pathlib
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, Field, field_validator, model_validator

from src.backtest.engine import BacktestBet, latest_fair_prob, payout_for
from src.clv.metrics import clv_price, clv_probability
from src.devig.convert import american_to_decimal
from src.store.pit_store import PointInTimeStore, kickoffs_from_store
from src.store.prop_settlement import (
    build_player_stats_index,
    normalize_player_name,
    settle_prop,
)
from src.store.schema import Market, Side
from src.store.settlement import Outcome, build_results_index, settle

# Re-exported for settlement callers that import it alongside settle_bets.
__all__ = ["kickoffs_from_store"]

log = logging.getLogger(__name__)

BET_LOG_PATH = Path("data/bet_log.jsonl")

# Closed set on purpose: free text would split one strategy into several
# spellings, and season_review would then review small fragments instead.
STRATEGIES = frozenset({
    "prop_arb",        # cross-book prop arbitrage -- structural, validated
    "prop_ev",         # anchored prop EV -- experimental, tested null
    "moneyline_ev",    # moneyline vs devigged Pinnacle
    "team_total",      # team-total O/U vs moneyline, validated buckets only
    "middle",          # line-movement middling
    "steam",           # synchronized cross-book movement
    "manual",          # placed on judgement, no scanner -- tracked separately on purpose
    "h1_pinnacle_lag",  # pre-registered (preregistration_wk5-9.md), log-only until scored
    "h1b_stale_price",  # pre-registered, log-only until scored
})

PINNACLE = "pinnacle"


class LoggedBet(BaseModel):
    """One placed bet, as known at placement time. Immutable once written."""

    placed_at: datetime
    event_id: str
    market: Market
    side: Side
    book: str
    price_american: int
    stake: float = Field(gt=0)
    strategy: str
    line: float | None = None
    player_name: str | None = None
    prop_stat: str | None = None
    alert_key: str | None = None
    note: str | None = None
    corrects: str | None = None  # placed_at ISO string of the row this supersedes

    @field_validator("strategy")
    @classmethod
    def _known_strategy(cls, v: str) -> str:
        if v not in STRATEGIES:
            raise ValueError(f"unknown strategy {v!r}; expected one of {sorted(STRATEGIES)}")
        return v

    @model_validator(mode="after")
    def _market_and_side_agree(self) -> LoggedBet:
        """Reject bets that could never be settled, while the person typing them can fix it.

        Props also need player, stat and line: without them the contract is
        unidentifiable and the bet would sit ungraded forever.
        """
        over_under = {Side.OVER, Side.UNDER}
        home_away = {Side.HOME, Side.AWAY}
        expected = over_under if self.market in (Market.PLAYER_PROP, Market.TOTAL) else home_away
        if self.side not in expected:
            raise ValueError(
                f"market {self.market.value!r} requires side in "
                f"{sorted(s.value for s in expected)}, got {self.side.value!r}"
            )
        if self.market == Market.PLAYER_PROP:
            missing = [f for f in ("player_name", "prop_stat", "line") if getattr(self, f) is None]
            if missing:
                raise ValueError(
                    f"player_prop bets need {missing} to identify the contract -- "
                    f"without them the bet can never be settled"
                )
        return self

    @field_validator("placed_at")
    @classmethod
    def _tz_aware(cls, v: datetime) -> datetime:
        # A naive timestamp compares wrong against the store's UTC capture_time.
        if v.tzinfo is None:
            raise ValueError("placed_at must be timezone-aware (use UTC)")
        return v

    @property
    def price_decimal(self) -> float:
        return american_to_decimal(self.price_american)

    def is_prop(self) -> bool:
        return self.market == Market.PLAYER_PROP


def log_bet(bet: LoggedBet, path: Path = BET_LOG_PATH) -> LoggedBet:
    """Append one bet. Creates the file on first use."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(bet.model_dump_json() + "\n")
    log.info("logged %s bet: %s %s %s @ %+d for $%.2f",
             bet.strategy, bet.event_id, bet.side.value, bet.book, bet.price_american, bet.stake)
    return bet


def load_bet_log(path: Path = BET_LOG_PATH) -> list[LoggedBet]:
    """Every logged bet, oldest first. A missing file is an empty log, not an error."""
    if not path.exists():
        return []
    bets = [LoggedBet.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return sorted(bets, key=lambda b: b.placed_at)


def active_bets(path: Path = BET_LOG_PATH) -> list[LoggedBet]:
    """Logged bets with superseded rows removed.

    The raw log holds both a wrong row and its correction; downstream code
    wants only the live view. `load_bet_log` still returns everything.
    """
    bets = load_bet_log(path)

    # Compare parsed instants, not strings: pydantic writes `...Z` while
    # isoformat() writes `...+00:00`. Match by row index too, because a
    # correction usually carries the same `placed_at` as the row it replaces
    # (it's the time the bet was struck, not when it was typed). Matching on
    # the timestamp alone would drop the correction along with its target.
    corrections: list[tuple[int, datetime]] = []
    for i, b in enumerate(bets):
        if not b.corrects:
            continue
        try:
            corrections.append((i, datetime.fromisoformat(b.corrects)))
        except ValueError:
            log.warning("bet at %s has an unparseable `corrects` value %r -- ignoring it, so "
                        "the row it meant to supersede stays live", b.placed_at, b.corrects)
    return [
        b for i, b in enumerate(bets)
        if not any(j != i and target == b.placed_at for j, target in corrections)
    ]


def to_backtest_bets(
    bets: list[LoggedBet],
    store: PointInTimeStore,
    devig_method: str = "shin",
    anchor_book: str = PINNACLE,
    as_of: datetime | None = None,
    residual_stds: Callable[[], tuple[float, float]] | None = None,
) -> list[BacktestBet]:
    """Attach entry/closing fair probabilities and CLV to logged bets.

    Uses `engine.latest_fair_prob`, so live and backtested bets are scored by
    the same code. A bet whose anchor never posted a two-sided quote gets
    `None` CLV rather than a guess. `as_of` (default now) bounds which
    snapshots are visible, so a CLV number can be reproduced later.
    """
    if not bets:
        return []

    now_bound = as_of or datetime.now(UTC)
    snapshots = store.read_as_of(now_bound)
    if snapshots.empty:
        log.warning("snapshot store is empty -- no CLV can be computed")

    # Sigma is only needed for spread/total bets and is expensive on a cold cache.
    sigmas = _SigmaProvider(residual_stds)

    out: list[BacktestBet] = []
    for b in bets:
        kickoff = _kickoff_for(snapshots, b.event_id)
        entry_fair = _anchor_fair_for_bet(snapshots, b, anchor_book, b.placed_at, devig_method, sigmas)

        # Before kickoff, "the last quote before kickoff" is just the current
        # quote. Only report a close once the game has started.
        closed = kickoff is not None and kickoff <= now_bound
        close_fair = _anchor_fair_for_bet(snapshots, b, anchor_book, kickoff, devig_method, sigmas) if closed else None
        close_dec = _close_price_decimal(snapshots, b, kickoff) if closed else None

        out.append(BacktestBet(
            event_id=b.event_id,
            decision_time=b.placed_at,
            market=b.market,
            side=b.side,
            line=b.line,
            book=b.book,
            stake=b.stake,
            price_american=b.price_american,
            price_decimal=b.price_decimal,
            entry_prob_fair=entry_fair,
            close_price_decimal=close_dec,
            close_prob_fair=close_fair,
            clv_price=clv_price(b.price_decimal, close_dec) if close_dec is not None else None,
            clv_probability=clv_probability(entry_fair, close_fair)
            if entry_fair is not None and close_fair is not None else None,
            outcome=None,   # settled separately by settle_bets
            payout=None,
            player_name=b.player_name,
            prop_stat=b.prop_stat,
            strategy=b.strategy,
        ))
    return out


def _kickoff_for(snapshots: pd.DataFrame, event_id: str) -> datetime | None:
    """The kickoff time from the most recent capture of this event.

    Not `.max()`: schedules get revised, sometimes earlier. The largest value
    could be a stale later time, which would let an in-play quote count as
    the close.
    """
    if snapshots.empty:
        return None
    rows = snapshots[snapshots["event_id"] == event_id]
    if rows.empty:
        return None
    return rows.loc[rows["capture_time"].idxmax(), "event_start_time"]


class _SigmaProvider:
    """Lazily resolves (sigma_margin, sigma_total), fetching at most once.

    On a cold cache the fetch fits models on the full play-by-play data, so
    prop- or moneyline-only calls should never trigger it. Injectable for tests.
    """

    def __init__(self, fetch: Callable[[], tuple[float, float]] | None) -> None:
        self._fetch = fetch
        self._value: tuple[float, float] | None = None

    def for_market(self, market: Market) -> float | None:
        if self._value is None:
            fetch = self._fetch
            if fetch is None:
                from src.backtest.middle_scan import cached_residual_stds

                fetch = cached_residual_stds
            self._value = fetch()
        sigma_margin, sigma_total = self._value
        if market == Market.SPREAD:
            return sigma_margin
        return sigma_total if market == Market.TOTAL else None


def _anchor_fair_for_bet(
    snapshots: pd.DataFrame,
    bet: LoggedBet,
    book: str,
    as_of: datetime | None,
    devig_method: str,
    sigmas: _SigmaProvider,
) -> float | None:
    """The anchor's fair probability for this bet's exact contract at `as_of`.

    For spreads and totals the anchor may be on a different line. Rather than
    wait for an exact line match (which returns nothing or a stale quote), read
    the anchor's current line and translate it onto the bet's line via
    `src/clv/line_adjust.py`.
    """
    if as_of is None or snapshots.empty:
        return None
    if bet.line is None or bet.market not in (Market.SPREAD, Market.TOTAL):
        return _fair_at(snapshots, bet, book, as_of, devig_method)

    anchor_line = _anchor_line_at(snapshots, bet, book, as_of)
    if anchor_line is None:
        return None
    fair = latest_fair_prob(
        snapshots, book=book, market=bet.market, side=bet.side, as_of=as_of,
        devig_method=devig_method, line=anchor_line, event_id=bet.event_id,
    )
    if fair is None or anchor_line == bet.line:
        return fair

    sigma = sigmas.for_market(bet.market)
    if sigma is None:
        return None
    from src.clv.line_adjust import translate_fair_prob

    return translate_fair_prob(bet.market, bet.side, anchor_line, bet.line, fair, sigma)


def _anchor_line_at(
    snapshots: pd.DataFrame, bet: LoggedBet, book: str, as_of: datetime
) -> float | None:
    """The line `book` was quoting for this bet's market and side as of `as_of`."""
    rows = snapshots[
        (snapshots["event_id"] == bet.event_id)
        & (snapshots["book"] == book)
        & (snapshots["market"] == bet.market.value)
        & (snapshots["side"] == bet.side.value)
        & (snapshots["capture_time"] <= as_of)
    ]
    if rows.empty:
        return None
    return float(rows.loc[rows["capture_time"].idxmax(), "line"])


def _fair_at(
    snapshots: pd.DataFrame, bet: LoggedBet, book: str, as_of: datetime | None, devig_method: str
) -> float | None:
    if snapshots.empty or as_of is None:
        return None
    return latest_fair_prob(
        snapshots, book=book, market=bet.market, side=bet.side, as_of=as_of,
        devig_method=devig_method, player_name=bet.player_name,
        prop_stat=bet.prop_stat, line=bet.line,
        # This frame is the whole store, not a per-event slice.
        event_id=bet.event_id,
    )


def _close_price_decimal(snapshots: pd.DataFrame, bet: LoggedBet, kickoff: datetime) -> float | None:
    """The bet's own book's last price before kickoff, on the same line.

    Lines move, so without the line filter the close for Under 44.5 could be
    read off a later Under 44.0 quote, a different contract.
    """
    if snapshots.empty:
        return None
    rows = snapshots[
        (snapshots["event_id"] == bet.event_id)
        & (snapshots["book"] == bet.book)
        & (snapshots["market"] == bet.market.value)
        & (snapshots["side"] == bet.side.value)
        & (snapshots["capture_time"] <= kickoff)
    ]
    if bet.is_prop():
        rows = rows[(rows["player_name"] == bet.player_name) & (rows["prop_stat"] == bet.prop_stat)]
    if bet.line is not None:
        rows = rows[rows["line"] == bet.line]
    if rows.empty:
        return None
    return float(rows.loc[rows["capture_time"].idxmax(), "price_decimal"])


def _grade(bet: BacktestBet, results: dict, stats_index: dict) -> Outcome | None:
    """One bet's outcome, or None if it cannot be graded yet.

    Returns None for an unplayed game, an unmatched player or a missing stat.
    An ungraded bet must never count as a loss.
    """
    if bet.market == Market.PLAYER_PROP:
        if bet.player_name is None or bet.prop_stat is None or bet.line is None:
            return None
        stats = stats_index.get((bet.event_id, normalize_player_name(bet.player_name)))
        if stats is None or bet.prop_stat not in stats:
            return None
        actual = stats[bet.prop_stat]
        if pd.isna(actual):
            return None
        return settle_prop(bet.side, bet.line, actual)

    result = results.get(bet.event_id)
    return None if result is None else settle(bet.market, bet.side, bet.line, result)


def settle_bets(
    bets: list[BacktestBet],
    schedule: pd.DataFrame,
    kickoffs: dict[str, datetime],
    player_stats: pd.DataFrame | None = None,
    starting_bankroll: float = 100.0,
) -> list[BacktestBet]:
    """Grade logged bets and track the realized bankroll.

    Bets come back in kickoff order, not decision order, because
    `clv_portfolio.bankroll_path` reads `bankroll_after` positionally and only
    settlement order describes the bankroll. Ungraded bets sort last and leave
    the bankroll untouched.
    """
    if not bets:
        return []

    results = build_results_index(schedule) if schedule is not None and not schedule.empty else {}
    stats_index: dict = {}
    if player_stats is not None and not player_stats.empty:
        stats_index = {
            (gid, normalize_player_name(name)): st
            for (gid, name), st in build_player_stats_index(player_stats).items()
        }

    graded = []
    for b in bets:
        # One bad row must not abort settlement for every other bet.
        try:
            outcome = _grade(b, results, stats_index)
        except Exception:
            log.exception("could not grade %s %s %s @ %s -- leaving it unsettled",
                          b.event_id, b.market.value, b.side.value, b.book)
            outcome = None
        graded.append(replace(b, outcome=outcome, payout=payout_for(outcome, b.stake, b.price_decimal)))

    far_future = datetime.max.replace(tzinfo=UTC)
    graded.sort(key=lambda b: (b.outcome is None, kickoffs.get(b.event_id, far_future), b.decision_time))

    bankroll = starting_bankroll
    out = []
    for b in graded:
        before = bankroll
        if b.payout is not None:
            bankroll += b.payout
        out.append(replace(b, bankroll_before=before, bankroll_after=bankroll))
    return out


STATIC_DIR = Path("data/static")


def load_settlement_inputs(static_dir: Path = STATIC_DIR) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(schedule, player_stats) for settlement, merged across cached vintages.

    Files overlap, so later vintages win on duplicate keys. Missing files give
    empty frames: nothing settles, and that's reported rather than guessed.
    """
    def _concat(pattern: str, key: list[str]) -> pd.DataFrame:
        frames = [pd.read_parquet(f) for f in sorted(static_dir.glob(pattern))]
        if not frames:
            return pd.DataFrame()
        out = pd.concat(frames, ignore_index=True)
        present = [k for k in key if k in out.columns]
        return out.drop_duplicates(subset=present, keep="last") if present else out

    return (
        _concat("schedules_*.parquet", ["game_id"]),
        _concat("player_stats_*.parquet", ["game_id", "player_display_name"]),
    )


def main() -> None:
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Append a placed bet to the bet log.")
    ap.add_argument("--event-id")
    ap.add_argument("--market", choices=[m.value for m in Market])
    ap.add_argument("--side", choices=[s.value for s in Side])
    ap.add_argument("--book")
    ap.add_argument("--price", type=int, help="American odds, e.g. -110 or 145")
    ap.add_argument("--stake", type=float)
    ap.add_argument("--strategy", choices=sorted(STRATEGIES))
    ap.add_argument("--line", type=float)
    ap.add_argument("--player")
    ap.add_argument("--prop-stat")
    ap.add_argument("--alert-key", help="key from data/alert_state.json, for traceability")
    ap.add_argument("--note")
    # Bets are often logged after the fact. Entry fair probability is read at
    # placed_at, so defaulting to now() would measure against a later market.
    ap.add_argument("--placed-at", help="ISO-8601 UTC time the bet was actually placed "
                                        "(default: now). Use this when logging after the fact.")
    ap.add_argument("--corrects", help="`placed_at` of an earlier row this supersedes "
                                       "(copy it from data/bet_log.jsonl)")
    ap.add_argument("--list", action="store_true", help="print the current log and exit")
    # For dry runs: the real log is append-only and can't be cleaned up.
    ap.add_argument("--path", default=str(BET_LOG_PATH),
                    help=f"bet log to write/read (default {BET_LOG_PATH})")
    a = ap.parse_args()

    path = pathlib.Path(a.path)
    if a.list:
        for b in active_bets(path):
            print(f"{b.placed_at.isoformat()}  {b.strategy:<13} {b.event_id} {b.side.value} "
                  f"{b.book} {b.price_american:+d} ${b.stake:.2f}")
        return

    # Checked here instead of required=True so `--list` works on its own.
    missing = [n for n in ("event_id", "market", "side", "book", "price", "stake", "strategy")
               if getattr(a, n) is None]
    if missing:
        ap.error("missing required argument(s): " + ", ".join("--" + m.replace("_", "-") for m in missing))

    if a.placed_at:
        placed_at = datetime.fromisoformat(a.placed_at)
        if placed_at.tzinfo is None:
            ap.error("--placed-at must be timezone-aware (e.g. 2026-09-07T18:30:00Z)")
    else:
        placed_at = datetime.now(UTC)

    log_bet(LoggedBet(
        placed_at=placed_at, event_id=a.event_id, market=Market(a.market), side=Side(a.side),
        book=a.book, price_american=a.price, stake=a.stake, strategy=a.strategy, line=a.line,
        player_name=a.player, prop_stat=a.prop_stat, alert_key=a.alert_key, note=a.note,
        corrects=a.corrects,
    ), path=path)


if __name__ == "__main__":
    main()
