"""Preseason dry-run collector: same collection mechanics as the real
season (src/collect/run.py, src/collect/scheduler.py), a different
identity scheme.

Purpose: exercise the whole live pipeline -- poll, match, snapshot, store,
measure CLV movement (src/clv/preseason_report.py) -- against real
preseason odds before the regular season starts, so pipeline bugs surface
now instead of Week 1. No bets are placed on preseason games; this is
infrastructure validation, not a research result.

Two structural differences from the real collector, both deliberate:
- Event identity comes from The Odds API's own `id` field, not a nflverse
  `game_id` lookup. nflverse's load_schedules() never includes preseason
  rows (game_type is only REG/WC/DIV/CON/SB -- src/collect/transform.py),
  so there is no schedule to match against; that's a data-availability
  gap in nflverse, not in The Odds API, which does carry real preseason
  odds under the americanfootball_nfl_preseason sport key (verified live).
  Preseason event_ids are prefixed "PRE" (e.g. "2026_PRE_<odds-api-id>")
  specifically so they can never collide with or be mistaken for a real
  nflverse game_id downstream.
- Snapshots land in a separate store root (data/snapshots_preseason/ by
  default), never data/snapshots/ -- the real season's CLV headline
  result must never accidentally include preseason noise.

No Pinnacle here: confirmed live that americanfootball_nfl_preseason
carries only fanduel, mybookieag, and onexbet, across every region tested
(eu, us, us2). src/clv/preseason_report.py uses FanDuel as the reference
book for preseason CLV -- explicitly not a Pinnacle stand-in, and
preseason numbers must never be read as evidence for the real
Pinnacle-anchored thesis (paper Sec 3.1).

This module deliberately has no budget-aware scheduling
(src/collect/budget.py) -- it's meant to be invoked by hand a handful of
times during the preseason window (`python -m src.collect.preseason`),
not run as an unattended long-lived process. The Odds API credit pool is
account-wide, shared with the real season's collector, so an unattended
preseason loop would compete with the budget the real season needs.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from pathlib import Path

from src.collect.client import OddsApiClient, OddsApiError, RateLimitExceeded
from src.collect.teams import load_team_name_map
from src.collect.transform import (
    MatchResult,
    TransformError,
    UnmatchedEventError,
    event_to_snapshots,
)
from src.store.pit_store import PointInTimeStore

log = logging.getLogger(__name__)

SPORT_KEY = "americanfootball_nfl_preseason"
DEFAULT_STORE_ROOT = Path("data/snapshots_preseason")
# No Pinnacle in any region for preseason (verified live 2026-08-17) --
# grab every region so nothing available is left uncaptured.
REGIONS = "eu,us,us2"
MARKETS = "h2h,spreads,totals"


def build_preseason_match(event: dict, name_to_abbr: Mapping[str, str], season: int) -> MatchResult:
    """Build a MatchResult straight from the Odds API event, no nflverse
    schedule lookup involved. `event["id"]` is Odds API's own stable
    per-event identifier, so entry and close snapshots for the same game
    are guaranteed to share an event_id across separate polls.
    """
    home_name = event.get("home_team")
    away_name = event.get("away_team")
    odds_api_id = event.get("id")
    if not odds_api_id:
        raise TransformError(f"preseason event missing 'id' field: {event!r}")

    home_abbr = name_to_abbr.get(home_name)
    away_abbr = name_to_abbr.get(away_name)
    if home_abbr is None or away_abbr is None:
        unknown = [n for n, a in [(home_name, home_abbr), (away_name, away_abbr)] if a is None]
        raise UnmatchedEventError(f"unknown team name(s) in preseason event, team-name map may be stale: {unknown}")

    return MatchResult(
        event_id=f"{season}_PRE_{odds_api_id}",
        season=season,
        week=0,  # no real week number for preseason; 0 marks it distinctly from any real REG/POST week
        home_abbr=home_abbr,
        away_abbr=away_abbr,
    )


def poll_once(
    client: OddsApiClient,
    name_to_abbr: Mapping[str, str],
    store: PointInTimeStore,
    season: int,
    regions: str = REGIONS,
    markets: str = MARKETS,
) -> dict[str, int]:
    """One poll: fetch, match, transform, write. Returns counts for
    logging/testing -- mirrors src/collect/scheduler.py's _tick, minus the
    budget-aware cadence logic (see module docstring for why).
    """
    try:
        response = client.get_odds(regions, markets)
    except (RateLimitExceeded, OddsApiError) as exc:
        log.warning("preseason poll failed: %s", exc)
        return {"matched": 0, "unmatched": 0, "malformed": 0, "written": 0}

    snapshots = []
    matched, unmatched, malformed = 0, 0, 0
    for event in response.events:
        try:
            match = build_preseason_match(event, name_to_abbr, season)
        except UnmatchedEventError as exc:
            log.warning("preseason unmatched event: %s", exc)
            unmatched += 1
            continue
        except TransformError as exc:
            log.error("preseason malformed event: %s", exc)
            malformed += 1
            continue

        try:
            snapshots.extend(event_to_snapshots(event, response.fetched_at, match))
            matched += 1
        except TransformError as exc:
            log.error("failed to transform preseason event %s: %s", match.event_id, exc)
            malformed += 1

    if snapshots:
        store.write(snapshots)

    log.info(
        "preseason poll ok: wrote %d snapshots, matched=%d unmatched=%d malformed=%d credits_remaining=%s",
        len(snapshots), matched, unmatched, malformed, response.remaining_credits,
    )
    return {"matched": matched, "unmatched": unmatched, "malformed": malformed, "written": len(snapshots)}


def main() -> None:
    from dotenv import load_dotenv

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    load_dotenv()

    api_key = os.environ["ODDS_API_KEY"]
    season = int(os.environ.get("COLLECT_SEASON", "2026"))
    # The regular-season schedule, not a preseason one -- only used here to
    # resolve full team names to abbreviations (src/collect/teams.py), and
    # every preseason team is also a regular-season team.
    schedule_path = Path("data/static") / f"schedules_{season}_{season}.parquet"

    client = OddsApiClient(api_key, sport_key=SPORT_KEY)
    name_to_abbr = dict(load_team_name_map(season, schedule_path))
    store = PointInTimeStore(root=DEFAULT_STORE_ROOT)

    poll_once(client, name_to_abbr, store, season)


if __name__ == "__main__":
    main()
