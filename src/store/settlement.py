"""Settlement: grade win/loss/push outcomes against nflverse final scores.

Deliberately decoupled from PointInTimeStore -- it operates on any rows
shaped like an OddsSnapshot (event_id, market, side, line) plus a schedule
DataFrame with home_score/away_score, so both the eventual backtester and a
real bet log can reuse it. NFL games can end in a tie (9 in the last decade
across the cached 2015-2024 schedule alone, roughly one per season) so a
moneyline push is a real, non-rare outcome, not a hypothetical edge case --
it must never be silently folded into a win or loss.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pandas as pd

from src.store.schema import Market, Side


class Outcome(str, Enum):
    WIN = "win"
    LOSS = "loss"
    PUSH = "push"


@dataclass(frozen=True)
class GameResult:
    event_id: str
    home_score: int
    away_score: int


def build_results_index(schedule: pd.DataFrame) -> dict[str, GameResult]:
    """game_id -> GameResult, restricted to completed games (both scores present)."""
    completed = schedule.dropna(subset=["home_score", "away_score"])
    return {
        row.game_id: GameResult(
            event_id=row.game_id, home_score=int(row.home_score), away_score=int(row.away_score)
        )
        for row in completed.itertuples()
    }


def settle(market: Market, side: Side, line: float | None, result: GameResult) -> Outcome:
    """Grade a single (market, side, line) bet against a final score."""
    if market == Market.MONEYLINE:
        return _settle_moneyline(side, result)
    if market == Market.SPREAD:
        if line is None:
            raise ValueError("spread settlement requires a line")
        return _settle_spread(side, line, result)
    if market == Market.TOTAL:
        if line is None:
            raise ValueError("total settlement requires a line")
        return _settle_total(side, line, result)
    raise ValueError(f"unknown market: {market}")


def _settle_moneyline(side: Side, result: GameResult) -> Outcome:
    if side not in (Side.HOME, Side.AWAY):
        raise ValueError(f"moneyline side must be HOME or AWAY, got {side}")
    if result.home_score == result.away_score:
        return Outcome.PUSH
    home_won = result.home_score > result.away_score
    side_won = (side == Side.HOME) == home_won
    return Outcome.WIN if side_won else Outcome.LOSS


def _settle_spread(side: Side, line: float, result: GameResult) -> Outcome:
    if side == Side.HOME:
        margin = (result.home_score - result.away_score) + line
    elif side == Side.AWAY:
        margin = (result.away_score - result.home_score) + line
    else:
        raise ValueError(f"spread side must be HOME or AWAY, got {side}")
    return _outcome_from_margin(margin)


def _settle_total(side: Side, line: float, result: GameResult) -> Outcome:
    total_score = result.home_score + result.away_score
    if side == Side.OVER:
        margin = total_score - line
    elif side == Side.UNDER:
        margin = line - total_score
    else:
        raise ValueError(f"total side must be OVER or UNDER, got {side}")
    return _outcome_from_margin(margin)


def _outcome_from_margin(margin: float) -> Outcome:
    if margin > 0:
        return Outcome.WIN
    if margin < 0:
        return Outcome.LOSS
    return Outcome.PUSH


def settle_snapshots(snapshots: pd.DataFrame, schedule: pd.DataFrame) -> pd.DataFrame:
    """Batch-grade snapshot-shaped rows (event_id, market, side, line
    columns) against the schedule. Adds an `outcome` column, "win"/"loss"/
    "push" for completed games, `None` where the game hasn't been played
    yet -- rows are never dropped, so callers can see exactly what's
    unsettled rather than have it silently disappear.
    """
    results = build_results_index(schedule)

    def _grade(row: pd.Series) -> str | None:
        result = results.get(row.event_id)
        if result is None:
            return None
        market = row.market if isinstance(row.market, Market) else Market(row.market)
        side = row.side if isinstance(row.side, Side) else Side(row.side)
        return settle(market, side, row.line, result).value

    graded = snapshots.copy()
    graded["outcome"] = graded.apply(_grade, axis=1)
    return graded
