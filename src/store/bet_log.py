"""Append-only record of bets actually placed, and the bridge from that record
to `BacktestBet` so the existing CLV/review machinery can read live bets.

**Why this exists: without it, CLV cannot be computed for a single real bet.**
CLV needs an entry price, and until now nothing stored one. `BacktestBet` was
constructed in exactly one place -- `BacktestEngine.run()`, a backtest -- and
`data/alert_state.json` records only which alerts were *sent*, never what was
staked, at what price, or at which book. Bets are placed manually across five
books and nothing came back. That made `season_review`, `clv_portfolio`,
`evaluation` and `drift/monitor` unreachable in practice: all four are
downstream of an input that did not exist (audit, 2026-08-23).

## Two rules that make the record trustworthy

**1. Only type what a human can know at bet time.** Everything derived --
entry fair probability, closing price, CLV, settlement -- is computed later
from the point-in-time store by `to_backtest_bets`. Nothing derived is ever
typed, so it cannot be mistyped, and it can always be recomputed if the
methodology changes. That is the same separation `PointInTimeStore` already
enforces between observed prices and modelled quantities.

**2. Append-only, never rewritten.** A bet log that can be edited after the
close is a bet log that can be edited *because* of the close, which is exactly
the bias CLV exists to detect. Corrections are appended as new rows referencing
the original via `corrects`, so the original stays visible.

## Strategy attribution is explicit, not inferred

`strategy` is a required field rather than something derived from `market`,
because `season_review` segments on it to decide continue/monitor/retire, and
market type does not identify the scanner: prop arbitrage and experimental prop
EV are both `player_prop` but have opposite track records (arb is structural
and validated; prop EV tested null on 6,812 bets). Pooling them would let one
mask the other -- the same failure `clv_portfolio.clv_by_segment` was built to
avoid. `alert_key` cross-references `data/alert_state.json` so a logged bet can
be traced back to the alert that triggered it.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, Field, field_validator

from src.backtest.engine import BacktestBet, latest_fair_prob
from src.clv.metrics import clv_price, clv_probability
from src.devig.convert import american_to_decimal
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, Side

log = logging.getLogger(__name__)

BET_LOG_PATH = Path("data/bet_log.jsonl")

# The scanners that can produce a bet. Closed set on purpose: a free-text
# strategy field silently fragments a segment ("prop_arb" vs "prop-arb" vs
# "arb") and `season_review` would then review three tiny groups instead of one
# real one, which is how a dying strategy hides.
STRATEGIES = frozenset({
    "prop_arb",        # cross-book prop arbitrage -- structural, validated
    "prop_ev",         # anchored prop EV -- EXPERIMENTAL, tested null on 6,812 bets
    "moneyline_ev",    # moneyline vs devigged Pinnacle
    "team_total",      # team-total O/U vs moneyline, validated buckets only
    "middle",          # line-movement middling
    "steam",           # synchronized cross-book movement
    "manual",          # placed on judgement, no scanner -- tracked separately on purpose
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

    @field_validator("placed_at")
    @classmethod
    def _tz_aware(cls, v: datetime) -> datetime:
        # A naive timestamp silently compares wrong against the store's UTC
        # capture_time, which would corrupt every CLV number downstream.
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
    """Every logged bet, oldest first. Missing file is an empty log, not an
    error -- this is read by unattended reporting.
    """
    if not path.exists():
        return []
    bets = [LoggedBet.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return sorted(bets, key=lambda b: b.placed_at)


def active_bets(path: Path = BET_LOG_PATH) -> list[LoggedBet]:
    """Logged bets with superseded rows removed.

    Corrections are appended, never edited in place, so the raw log holds both
    the wrong row and its replacement. Everything downstream wants only the
    live view; the raw log stays available via `load_bet_log` for auditing.
    """
    bets = load_bet_log(path)
    superseded = {b.corrects for b in bets if b.corrects}
    return [b for b in bets if b.placed_at.isoformat() not in superseded]


def to_backtest_bets(
    bets: list[LoggedBet],
    store: PointInTimeStore,
    devig_method: str = "shin",
    anchor_book: str = PINNACLE,
    as_of: datetime | None = None,
) -> list[BacktestBet]:
    """Enrich logged bets with entry/closing fair probabilities and CLV, so
    `season_review` / `clv_portfolio` / `evaluation` can consume them unchanged.

    Reuses `engine.latest_fair_prob` rather than reimplementing devigging, so a
    live bet and a backtested bet are scored by identical code -- if they
    diverged, no live-vs-backtest comparison would mean anything.

    A bet whose anchor never posted a two-sided quote gets `None` CLV rather
    than a guess. That is common and correct early: Pinnacle does not quote
    props until close to kickoff, and `_clv_series` drops unmeasurable bets.

    `as_of` bounds which snapshots are visible, defaulting to now. It is a real
    parameter rather than a hardcoded `now()` for the same reason every other
    read path here takes one: pinning it is what lets a CLV number be
    recomputed identically later instead of drifting with wall-clock.
    """
    if not bets:
        return []

    snapshots = store.read_as_of(as_of or datetime.now(UTC))
    if snapshots.empty:
        log.warning("snapshot store is empty -- no CLV can be computed")

    out: list[BacktestBet] = []
    for b in bets:
        kickoff = _kickoff_for(snapshots, b.event_id)
        entry_fair = _fair_at(snapshots, b, anchor_book, b.placed_at, devig_method)
        # "Close" = the last quote before kickoff. Without a known kickoff there
        # is no defensible close, so CLV stays None rather than silently using
        # the newest quote (which may be mid-game or another week entirely).
        close_fair = _fair_at(snapshots, b, anchor_book, kickoff, devig_method) if kickoff else None
        close_dec = _close_price_decimal(snapshots, b, kickoff) if kickoff else None

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
            outcome=None,   # settlement is a separate pass (src/store/settlement.py)
            payout=None,
            player_name=b.player_name,
            prop_stat=b.prop_stat,
            strategy=b.strategy,
        ))
    return out


def _kickoff_for(snapshots: pd.DataFrame, event_id: str) -> datetime | None:
    if snapshots.empty:
        return None
    rows = snapshots[snapshots["event_id"] == event_id]
    return None if rows.empty else rows["event_start_time"].max()


def _fair_at(
    snapshots: pd.DataFrame, bet: LoggedBet, book: str, as_of: datetime | None, devig_method: str
) -> float | None:
    if snapshots.empty or as_of is None:
        return None
    return latest_fair_prob(
        snapshots, book=book, market=bet.market, side=bet.side, as_of=as_of,
        devig_method=devig_method, player_name=bet.player_name,
        prop_stat=bet.prop_stat, line=bet.line,
    )


def _close_price_decimal(snapshots: pd.DataFrame, bet: LoggedBet, kickoff: datetime) -> float | None:
    """The bet's OWN book's last decimal price before kickoff -- price CLV asks
    whether you beat the number you actually took, at the book you took it from.
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
    ap.add_argument("--list", action="store_true", help="print the current log and exit")
    a = ap.parse_args()

    if a.list:
        for b in active_bets():
            print(f"{b.placed_at.isoformat()}  {b.strategy:<13} {b.event_id} {b.side.value} "
                  f"{b.book} {b.price_american:+d} ${b.stake:.2f}")
        return

    # Validated here rather than via argparse `required=True` so `--list` works
    # on its own -- a listing command that demands the fields you are trying to
    # look up is a command nobody runs.
    missing = [n for n in ("event_id", "market", "side", "book", "price", "stake", "strategy")
               if getattr(a, n) is None]
    if missing:
        ap.error("missing required argument(s): " + ", ".join("--" + m.replace("_", "-") for m in missing))

    log_bet(LoggedBet(
        placed_at=datetime.now(UTC), event_id=a.event_id, market=Market(a.market), side=Side(a.side),
        book=a.book, price_american=a.price, stake=a.stake, strategy=a.strategy, line=a.line,
        player_name=a.player, prop_stat=a.prop_stat, alert_key=a.alert_key, note=a.note,
    ))


if __name__ == "__main__":
    main()
