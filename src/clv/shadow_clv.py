"""CLV for alerts that were never bet.

**The gap this closes.** CLV is computed in exactly two places: `engine.py`
(historical replay) and `bet_log.to_backtest_bets` (bets actually placed). Both
start from a *bet*. During a deliberate no-bet observation window -- the plan for
weeks 1-3 of 2026 -- `data/bet_log.jsonl` stays empty, so neither runs and **no
CLV data is produced at all.**

The shadow log does record every alert, but it answers a different question.
`shadow_log.recheck` re-samples for `DEFAULT_RECHECK_HORIZON` (6 hours) and
`survival_report` asks "did this price survive detection latency?". CLV asks "did
this price beat the CLOSE", and the close is typically days later -- 122 hours out
for the first steam alert of 2026. Survival and CLV are different measurements and
nothing bridged them.

**Why this reuses `LoggedBet` instead of computing CLV itself.** Every shadow row
already carries what a bet carries: contract, book, price, strategy, timestamp. So
an alert becomes a notional `LoggedBet` and goes through `to_backtest_bets`
unchanged -- identical devigging, identical anchor book, and identical handling of
the premature-close trap (a "close" is only read once kickoff has actually passed).
Reimplementing the CLV convention here would create a second definition that could
silently drift from the one every other consumer uses, which is precisely the
failure this project keeps finding in its own history.

`stake` is notional and carries no meaning: both `clv_price` and `clv_probability`
are stake-independent. It exists only because `LoggedBet` requires a positive stake
for real bets. Nothing here is written to the bet log -- these are hypotheticals,
and mixing them into the record of real money would corrupt the thing the bankroll
discipline exists to protect.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.backtest.engine import BacktestBet
from src.clv.seals import withheld
from src.signal.shadow_log import SHADOW_LOG_PATH, load
from src.store.bet_log import PINNACLE, LoggedBet, to_backtest_bets
from src.store.pit_store import PointInTimeStore

log = logging.getLogger(__name__)

# Notional only -- see the module docstring. Not a sizing recommendation.
NOTIONAL_STAKE = 1.0


def shadow_alerts_as_bets(
    path: Path = SHADOW_LOG_PATH, notional_stake: float = NOTIONAL_STAKE, now: datetime | None = None
) -> list[LoggedBet]:
    """Every alerted shadow leg as a notional `LoggedBet`.

    `placed_at` is the leg's `capture_time` -- the instant the price actually
    existed -- not `alerted_at`, which is merely when the scanner noticed. Entry
    fair probability is read at `placed_at`, so using our own detection clock
    would score the bet against a market state it was never offered at. Legs with
    no capture_time fall back to `alerted_at` (and legs with no price are dropped:
    a contract that was not quoted has no entry to value).

    **One bet per (alert_key, leg), keeping the EARLIEST** (added 2026-09-21).
    The same contract legitimately produces several alert rows -- `live_scan`
    re-alerts when an edge improves, and until the same day `props_scan` could
    emit one contract twice in a single scan. Both are correct for *alerting* and
    wrong for *measurement*: re-observations of one contract are not independent
    samples, so counting them narrows the CI and skews the beat rate that
    `decision_report` reads. Measured when found: **22 of 96 prop_ev and 18 of 65
    moneyline_ev alert legs were redundant** -- 23% and 28%.

    Earliest, not best-priced: it is the moment the opportunity was first
    detectable, and therefore the entry a human acting on the first text would
    have got. Keeping the best price would round the entry toward self-flattery,
    which is the one direction this project's tie-break rules forbid.

    **Sealed alerts are skipped** (`clv.seals`, added 2026-10-17): H5's Weeks
    10-14 `moneyline_ev` legs stay out of every CLV number until 2026-12-15.
    """
    seen: set[tuple[str, str]] = set()
    bets: list[LoggedBet] = []
    for o in sorted(load(path), key=lambda o: o.alerted_at):
        if not o.is_alert or o.price_american is None or withheld(o.strategy, o.event_id, now):
            continue
        key = (o.alert_key, o.leg)
        if key in seen:
            continue
        seen.add(key)
        bets.append(LoggedBet(
            placed_at=o.capture_time or o.alerted_at,
            event_id=o.event_id,
            market=o.market,
            side=o.side,
            book=o.book,
            price_american=o.price_american,
            stake=notional_stake,
            strategy=o.strategy,
            line=o.line,
            player_name=o.player_name,
            prop_stat=o.prop_stat,
            alert_key=o.alert_key,
            note="shadow alert (never bet)",
        ))
    return bets


def shadow_clv(
    store: PointInTimeStore,
    path: Path = SHADOW_LOG_PATH,
    as_of: datetime | None = None,
    devig_method: str = "shin",
    anchor_book: str = PINNACLE,
) -> list[BacktestBet]:
    """Shadow alerts enriched with entry/closing fair probabilities and CLV.

    Output is `BacktestBet`, so `clv_portfolio.clv_summary`, `clv_by_segment`,
    `evaluation.evaluate_strategy` and `season_review` all consume it unchanged.
    """
    bets = shadow_alerts_as_bets(path)
    if not bets:
        return []
    return to_backtest_bets(
        bets, store, devig_method=devig_method, anchor_book=anchor_book, as_of=as_of
    )


def shadow_clv_frame(
    store: PointInTimeStore,
    path: Path = SHADOW_LOG_PATH,
    as_of: datetime | None = None,
) -> pd.DataFrame:
    """`shadow_clv` as a frame, with `measurable` marking rows whose CLV is
    actually computable yet.

    Rows are kept rather than filtered: a report that silently drops unmeasurable
    alerts shrinks its own denominator, which is how a beat-rate starts looking
    better than it is. Early in a game week MOST rows are unmeasurable -- the game
    has not kicked off, so there is no close -- and that is expected, not a fault.
    """
    from src.backtest.clv_portfolio import bets_to_frame

    bets = shadow_clv(store, path=path, as_of=as_of)
    if not bets:
        return pd.DataFrame()
    frame = bets_to_frame(bets)
    frame["measurable"] = frame["clv_probability"].notna()
    return frame


def format_summary(frame: pd.DataFrame) -> str:
    """Human-readable CLV status for the no-bet observation window.

    Reports the measurable/unmeasurable split explicitly. Early in a week almost
    everything is unmeasurable (no kickoff yet, so no close) and that is healthy;
    a row still unmeasurable AFTER its game started is a real data-quality
    problem worth chasing, so the two cases are never collapsed into one number.
    """
    if frame.empty:
        return "shadow CLV: no alerts recorded yet"

    measurable = frame[frame["measurable"]]
    lines = [f"shadow CLV: {len(frame)} alerted leg(s), {len(measurable)} measurable"]
    if measurable.empty:
        lines.append("  (no game has closed yet -- expected before kickoff)")
        return "\n".join(lines)

    def _row(label: str, group: pd.DataFrame) -> str:
        beat = float((group["clv_probability"] > 0).mean())
        return (
            f"  {label:14} n={len(group):3d}  beat_rate={beat:6.1%}  "
            f"mean_clv={group['clv_probability'].mean():+.4f}"
        )

    for strategy, group in measurable.groupby("strategy"):
        lines.append(_row(str(strategy), group))
    lines.append(_row("ALL", measurable))

    stale = frame[~frame["measurable"] & frame["close_price_decimal"].isna()]
    if not stale.empty:
        lines.append(f"  ({len(stale)} leg(s) still awaiting a close)")
    return "\n".join(lines)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    store = PointInTimeStore(root="data/snapshots")
    print(format_summary(shadow_clv_frame(store)))


if __name__ == "__main__":
    main()
