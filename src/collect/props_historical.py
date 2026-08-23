"""Historical player-prop odds backfill for backtesting.

**Blocked on paid access.** The historical endpoint 401s on the free tier
(confirmed live 2026-08-17: HISTORICAL_UNAVAILABLE_ON_FREE_USAGE_PLAN, 0
credits charged for the rejection). Historical player-prop coverage starts
2023-05-03T05:30:00Z (5-minute snapshot intervals from then), so 2023-2025
are reachable once upgraded -- 2015-2022 are not, at any price.

**Cost, and why this module scopes to one market/one game at a time
rather than pulling everything:** each historical per-event odds call
costs 10 x markets x regions credits (10x the live per-event rate), and
each call is a single point-in-time snapshot, not a range -- reconstructing
even a full season's closing lines for one market is thousands of credits
(see paper Sec 3.6 / the player_props_infra memory for the arithmetic).
The caller controls exactly which games get pulled (`games` argument
below), so a first run can be a handful of games to check feasibility --
does Pinnacle even show up -- before committing to anything larger.

**Cannot be live-verified yet, unlike everything else in this project.**
Every other module this session was built against a real API response
observed live. This one is built against the documented response shape
only (the "data"-wrapped historical envelope), because there is no way to
call the historical endpoint without paid access. Treat the parsing path
as unverified until the first real pull confirms it.

Reuses src/collect/props.py's parsing (event_odds_to_prop_snapshots)
unchanged -- the historical endpoint's response schema is documented as
"almost the same as the live per-event endpoint," just wrapped in an
envelope with a real snapshot timestamp this module unwraps before
handing off.

**PARKED 2026-08-23 (audit verdict).** A completed one-shot backfill: the full
2024 props pull finished at 285/285 games. Nothing should import this, and
re-running it spends real paid credits. Kept because it is the only record of
how that pull was done. Reopen only to run a genuinely new historical batch.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import datetime, timedelta

from src.collect.client import OddsApiClient, OddsApiError, RateLimitExceeded
from src.collect.props import DEFAULT_MARKETS, event_odds_to_prop_snapshots
from src.collect.transform import MatchResult, TransformError
from src.store.pit_store import PointInTimeStore
from src.store.schema import OddsSnapshot

log = logging.getLogger(__name__)

DEFAULT_REGIONS = "us,eu"


def find_historical_event_id(
    client: OddsApiClient, date: str, home_name: str, away_name: str
) -> str | None:
    """1 credit. Looks up the historical events list as of `date` and
    returns the Odds API event id matching (home_name, away_name), or
    None if not found -- callers decide whether that's a hard failure or
    a game to skip (e.g. too far back for this book to have listed it).
    """
    response = client.get_historical_events(date)
    for event in response.events:
        if event.get("home_team") == home_name and event.get("away_team") == away_name:
            return event.get("id")
    return None


def pull_historical_prop_snapshot(
    client: OddsApiClient,
    event_id: str,
    date: str,
    markets: str,
    match: MatchResult,
    regions: str = DEFAULT_REGIONS,
) -> list[OddsSnapshot]:
    """One historical snapshot (nearest available <= `date`) for one or
    more markets (comma-joined, e.g. props.DEFAULT_MARKETS for all seven
    supported O/U markets in a single call) at a single event. `date`
    should be close to the bet you're trying to reconstruct (e.g. near
    kickoff for a closing line) -- this pulls one point in time, not a
    range. Requesting N markets in one call costs the same as N separate
    single-market calls (10 x markets x regions either way), so combining
    them here only saves HTTP round-trips, not credits.
    """
    response = client.get_historical_event_odds(event_id, date, regions, markets)
    event_data = response.events[0]
    return event_odds_to_prop_snapshots(event_data, response.fetched_at, match)


def backfill_historical_props(
    client: OddsApiClient,
    games: Iterable[tuple[MatchResult, str, str, datetime]],
    store: PointInTimeStore,
    markets: str = DEFAULT_MARKETS,
    regions: str = DEFAULT_REGIONS,
    minutes_before_kickoff: int = 15,
) -> dict[str, int]:
    """`games`: iterable of (match, home_name, away_name, kickoff) --
    home_name/away_name are the book's own team-name strings (needed to
    look up the historical event id), kickoff is the game's real start
    time. Pulls one snapshot per game, `minutes_before_kickoff` before
    kickoff (an approximation of "the close" -- the historical endpoint
    snaps to the nearest available 5-minute interval, so this won't be
    exact to the minute).

    Deliberately synchronous and unhurried: this is a backfill run by
    hand for a deliberately small, chosen set of games (module docstring),
    not a service.
    """
    found = missing = failed = malformed = 0
    all_snapshots: list[OddsSnapshot] = []

    for match, home_name, away_name, kickoff in games:
        snapshot_date = (kickoff - timedelta(minutes=minutes_before_kickoff)).isoformat().replace("+00:00", "Z")
        event_id = find_historical_event_id(client, snapshot_date, home_name, away_name)
        if event_id is None:
            log.warning("historical props: no event found for %s @ %s on %s", away_name, home_name, snapshot_date)
            missing += 1
            continue

        try:
            snapshots = pull_historical_prop_snapshot(client, event_id, snapshot_date, markets, match, regions)
        except (OddsApiError, RateLimitExceeded) as exc:
            log.error("historical props: failed to pull %s (%s): %s", event_id, match.event_id, exc)
            failed += 1
            continue
        except TransformError as exc:
            log.error("historical props: malformed response for %s (%s): %s", event_id, match.event_id, exc)
            malformed += 1
            continue

        found += 1
        all_snapshots.extend(snapshots)

    if all_snapshots:
        store.write(all_snapshots)

    log.info(
        "historical props backfill: wrote %d snapshots, found=%d missing=%d failed=%d malformed=%d",
        len(all_snapshots), found, missing, failed, malformed,
    )
    return {"found": found, "missing": missing, "failed": failed, "malformed": malformed, "written": len(all_snapshots)}
