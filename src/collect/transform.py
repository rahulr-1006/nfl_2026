"""Raw Odds API JSON -> OddsSnapshot list, and event -> schedule matching.

nflverse schedules never contain preseason games (confirmed against both
the 2024 and 2026 schedules: game_type is only REG/WC/DIV/CON/SB), and
within one season a (home_abbr, away_abbr) pair is unique — a divisional
rematch just swaps home/away, producing a different pair. So event
matching is a plain dict lookup, no fuzzy datetime logic required.

The corollary: right now (preseason), matches will legitimately fail for
most or all events. That's expected, not a bug — see match_event's
docstring.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from src.store.schema import Market, OddsSnapshot, Side


class UnmatchedEventError(RuntimeError):
    """Raised when an Odds API event can't be joined to a schedule row."""


class TransformError(RuntimeError):
    """Raised when a single event's payload has an unexpected shape."""


@dataclass(frozen=True)
class MatchResult:
    event_id: str
    season: int
    week: int
    home_abbr: str
    away_abbr: str


ScheduleIndex = Mapping[tuple[int, str, str], MatchResult]

_TOTAL_SIDE_BY_NAME = {"Over": Side.OVER, "Under": Side.UNDER}
_MARKET_KEY_TO_MARKET = {
    "h2h": Market.MONEYLINE,
    "spreads": Market.SPREAD,
    "totals": Market.TOTAL,
}


def build_schedule_index(schedule: pd.DataFrame) -> dict[tuple[int, str, str], MatchResult]:
    """(season, home_abbr, away_abbr) -> MatchResult, built once at startup."""
    index: dict[tuple[int, str, str], MatchResult] = {}
    for row in schedule.itertuples():
        key = (int(row.season), row.home_team, row.away_team)
        index[key] = MatchResult(
            event_id=row.game_id,
            season=int(row.season),
            week=int(row.week),
            home_abbr=row.home_team,
            away_abbr=row.away_team,
        )
    return index


def match_event(
    home_name: str,
    away_name: str,
    season: int,
    schedule_index: ScheduleIndex,
    name_to_abbr: Mapping[str, str],
) -> MatchResult:
    """Join an API event to a schedule row via (season, home_abbr, away_abbr).

    Raises UnmatchedEventError distinguishing two failure modes:
    - unknown team name (not in name_to_abbr at all): a real bug worth
      logging loudly, since it means our team-name map is stale.
    - no schedule row for (season, home_abbr, away_abbr): expected right
      now for preseason games, since nflverse schedules never include
      PRE — this is a normal, permanent condition until the 2026-09-09
      opener, not a defect.
    """
    home_abbr = name_to_abbr.get(home_name)
    away_abbr = name_to_abbr.get(away_name)
    if home_abbr is None or away_abbr is None:
        unknown = [n for n, a in [(home_name, home_abbr), (away_name, away_abbr)] if a is None]
        raise UnmatchedEventError(f"unknown team name(s), team-name map may be stale: {unknown}")

    match = schedule_index.get((season, home_abbr, away_abbr))
    if match is None:
        raise UnmatchedEventError(
            f"no schedule row for season={season} home={home_abbr} away={away_abbr} "
            "(expected for preseason games; nflverse schedules never include PRE)"
        )
    return match


def event_to_snapshots(
    event: dict,
    capture_time: datetime,
    match: MatchResult,
) -> list[OddsSnapshot]:
    """All bookmakers in the event, not just Pinnacle — extra bookmakers cost
    nothing (Odds API billing is regions x markets, not event/bookmaker
    count) and cross-book dispersion is a planned feature (blueprint Part E).
    """
    try:
        home_name = event["home_team"]
        away_name = event["away_team"]
        event_start_time = datetime.fromisoformat(event["commence_time"])
        bookmakers = event["bookmakers"]
    except KeyError as exc:
        raise TransformError(f"event missing required field: {exc}") from exc

    snapshots: list[OddsSnapshot] = []
    for bookmaker in bookmakers:
        book = bookmaker["key"]
        for market_block in bookmaker.get("markets", []):
            market_key = market_block["key"]
            market = _MARKET_KEY_TO_MARKET.get(market_key)
            if market is None:
                continue  # unrequested market type, ignore rather than fail the batch

            for outcome in market_block["outcomes"]:
                side, line = _resolve_side_and_line(market, outcome, home_name, away_name)
                if side is None:
                    raise TransformError(
                        f"unrecognized outcome name {outcome.get('name')!r} for market {market_key}"
                    )
                snapshots.append(
                    OddsSnapshot.from_american(
                        capture_time=capture_time,
                        event_id=match.event_id,
                        season=match.season,
                        week=match.week,
                        home_team=match.home_abbr,
                        away_team=match.away_abbr,
                        event_start_time=event_start_time,
                        book=book,
                        market=market,
                        side=side,
                        price_american=int(outcome["price"]),
                        line=line,
                    )
                )
    return snapshots


def _resolve_side_and_line(
    market: Market, outcome: dict, home_name: str, away_name: str
) -> tuple[Side | None, float | None]:
    name = outcome.get("name")
    if market == Market.TOTAL:
        return _TOTAL_SIDE_BY_NAME.get(name), outcome.get("point")
    if market == Market.SPREAD:
        if name == home_name:
            return Side.HOME, outcome.get("point")
        if name == away_name:
            return Side.AWAY, outcome.get("point")
        return None, None
    if market == Market.MONEYLINE:
        if name == home_name:
            return Side.HOME, None
        if name == away_name:
            return Side.AWAY, None
        return None, None
    return None, None
