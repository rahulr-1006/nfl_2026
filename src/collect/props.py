"""Player-prop odds collection.

**Prepped, not active.** Live-checked 2026-08-17 (3.5 weeks before Week
1): across every region, only one book (DraftKings) had posted any prop
market at all, and only player_anytime_td -- no yardage/reception props,
no Pinnacle. NFL player props are typically posted Tuesday-Thursday of
game week, not weeks ahead like mainline spreads/totals, so this can't be
exercised against real data yet. This module exists so the moment props
actually start filling in, turning it on is a config/invocation change,
not a design-from-scratch scramble -- same pattern as
src/collect/preseason.py before the preseason window opened.

Structural differences from the mainline collector (src/collect/scheduler.py):
- Uses the per-event endpoint (OddsApiClient.get_event_odds), one call per
  game, not one call for the whole slate -- real nflverse game_ids exist
  for the regular season (unlike preseason), so matching reuses
  src/collect/transform.py's match_event/build_schedule_index directly.
- Only Over/Under-style prop markets (PROP_MARKET_TO_STAT) are parsed.
  Proposition-style markets (player_anytime_td and similar) were observed
  live as single-sided -- no complementary "No" price -- so they can't be
  devigged with the existing two-outcome methods (src/devig/methods.py)
  and are deliberately out of scope, not just unmapped.
- No launchd service, no budget-aware scheduling: meant to be invoked by
  hand (`python -m src.collect.props`) once props are actually observed
  to exist, the same "manual/sparse invocation" discipline
  src/collect/preseason.py uses and for the same reason -- credits are a
  shared, finite resource with the real collector.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

from src.collect.client import OddsApiClient, OddsApiError, RateLimitExceeded
from src.collect.transform import (
    MatchResult,
    ScheduleIndex,
    TransformError,
    UnmatchedEventError,
    match_event,
)
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, OddsSnapshot, Side

log = logging.getLogger(__name__)

# Odds API player-prop market key -> nflverse player_stats column name
# (src/store/prop_settlement.py looks this column up directly, so this
# mapping only needs to exist once, here, at ingestion).
PROP_MARKET_TO_STAT = {
    "player_pass_yds": "passing_yards",
    "player_pass_tds": "passing_tds",
    "player_rush_yds": "rushing_yards",
    "player_rush_tds": "rushing_tds",
    "player_reception_yds": "receiving_yards",
    "player_receptions": "receptions",
    "player_reception_tds": "receiving_tds",
}
DEFAULT_REGIONS = "us,eu"
DEFAULT_MARKETS = ",".join(PROP_MARKET_TO_STAT)


def _resolve_prop_side(name: str | None) -> Side | None:
    if name == "Over":
        return Side.OVER
    if name == "Under":
        return Side.UNDER
    return None  # single-sided/proposition outcome (e.g. anytime_td's "Yes") -- not supported, see module docstring


def event_odds_to_prop_snapshots(event_data: dict, capture_time: datetime, match: MatchResult) -> list[OddsSnapshot]:
    """Parse one /v4/sports/{sport}/events/{eventId}/odds response.
    Markets outside PROP_MARKET_TO_STAT, or outcomes that aren't
    Over/Under, are silently skipped -- not malformed data, just out of
    this module's current scope.
    """
    try:
        event_start_time = datetime.fromisoformat(event_data["commence_time"])
    except KeyError as exc:
        raise TransformError(f"event missing required field: {exc}") from exc

    snapshots: list[OddsSnapshot] = []
    for bookmaker in event_data.get("bookmakers", []):
        book = bookmaker["key"]
        for market_block in bookmaker.get("markets", []):
            stat = PROP_MARKET_TO_STAT.get(market_block.get("key"))
            if stat is None:
                continue
            for outcome in market_block.get("outcomes", []):
                side = _resolve_prop_side(outcome.get("name"))
                if side is None:
                    continue
                player_name = outcome.get("description")
                line = outcome.get("point")
                if not player_name or line is None:
                    raise TransformError(f"prop outcome missing player name or line: {outcome!r}")
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
                        market=Market.PLAYER_PROP,
                        side=side,
                        price_american=int(outcome["price"]),
                        line=float(line),
                        player_name=player_name,
                        prop_stat=stat,
                    )
                )
    return snapshots


def poll_event_props(
    client: OddsApiClient,
    event_id: str,
    match: MatchResult,
    regions: str = DEFAULT_REGIONS,
    markets: str = DEFAULT_MARKETS,
) -> list[OddsSnapshot]:
    """One event's worth of prop snapshots. Raises OddsApiError/RateLimitExceeded
    to the caller -- unlike the mainline collector's tick(), a single
    manual invocation should surface a failure loudly, not swallow it.
    """
    response = client.get_event_odds(event_id, regions, markets)
    event_data = response.events[0]
    return event_odds_to_prop_snapshots(event_data, response.fetched_at, match)


def poll_all_props(
    client: OddsApiClient,
    events: Iterable[tuple[str, str, str]],
    season: int,
    schedule_index: ScheduleIndex,
    name_to_abbr: Mapping[str, str],
    store: PointInTimeStore,
    regions: str = DEFAULT_REGIONS,
    markets: str = DEFAULT_MARKETS,
) -> dict[str, int]:
    """`events`: iterable of (odds_api_event_id, home_team_name, away_team_name)
    -- from the free /v4/sports/{sport}/events listing, not fetched here,
    so callers control which games to spend per-event credits on. Matches
    each to a real nflverse game_id via the same schedule index/matcher
    the mainline collector uses (unlike preseason, real games have real
    game_ids to match against).
    """
    matched = unmatched = malformed = failed = 0
    all_snapshots: list[OddsSnapshot] = []

    for odds_api_event_id, home_name, away_name in events:
        try:
            match = match_event(home_name, away_name, season, schedule_index, name_to_abbr)
        except UnmatchedEventError as exc:
            log.warning("props: unmatched event: %s", exc)
            unmatched += 1
            continue

        try:
            snapshots = poll_event_props(client, odds_api_event_id, match, regions, markets)
        except (OddsApiError, RateLimitExceeded) as exc:
            log.error("props: failed to poll event %s (%s): %s", odds_api_event_id, match.event_id, exc)
            failed += 1
            continue
        except TransformError as exc:
            log.error("props: malformed event %s (%s): %s", odds_api_event_id, match.event_id, exc)
            malformed += 1
            continue

        matched += 1
        all_snapshots.extend(snapshots)

    if all_snapshots:
        store.write(all_snapshots)

    total_events = matched + unmatched + malformed + failed
    log.info(
        "props poll ok: wrote %d snapshots across %d event(s) attempted, matched=%d unmatched=%d malformed=%d failed=%d",
        len(all_snapshots), total_events, matched, unmatched, malformed, failed,
    )
    return {"matched": matched, "unmatched": unmatched, "malformed": malformed, "failed": failed, "written": len(all_snapshots)}


def main() -> None:
    """Manual entrypoint: `python -m src.collect.props`. See module
    docstring -- not meant to run until real prop coverage exists.
    Defaults to only this week's games (commence_time within the next 7
    days) -- per-event calls scale with event count, and props aren't
    posted more than a few days ahead anyway (module docstring), so
    hitting the full ~272-game season schedule on every invocation would
    be pure waste, not extra coverage.
    """
    import sys
    from datetime import UTC, timedelta

    import requests

    from src.collect.config import load_config
    from src.collect.teams import load_team_name_map
    from src.collect.transform import build_schedule_index

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    load_dotenv()

    days_ahead = int(sys.argv[1]) if len(sys.argv) > 1 else 7

    config = load_config()
    schedule = pd.read_parquet(config.resolved_schedule_path)
    schedule = schedule[schedule["season"] == config.season]
    schedule_index = build_schedule_index(schedule)
    name_to_abbr = dict(load_team_name_map(config.season, config.resolved_schedule_path))

    events_resp = requests.get(
        f"https://api.the-odds-api.com/v4/sports/{config.sport_key}/events", params={"apiKey": config.api_key}
    )
    events_resp.raise_for_status()

    cutoff = datetime.now(UTC) + timedelta(days=days_ahead)
    upcoming = [
        e for e in events_resp.json() if datetime.fromisoformat(e["commence_time"]) <= cutoff
    ]
    log.info("%d event(s) within the next %d day(s) (of %d total)", len(upcoming), days_ahead, len(events_resp.json()))
    events = [(e["id"], e["home_team"], e["away_team"]) for e in upcoming]

    client = OddsApiClient(config.api_key, config.sport_key)
    store = PointInTimeStore(root=config.store_root)
    poll_all_props(client, events, config.season, schedule_index, name_to_abbr, store)


if __name__ == "__main__":
    main()
