from datetime import UTC, datetime
from unittest.mock import MagicMock

from src.collect.client import OddsApiError, OddsApiResponse
from src.collect.props_historical import (
    backfill_historical_props,
    find_historical_event_id,
    pull_historical_prop_snapshot,
)
from src.collect.transform import MatchResult
from src.store.pit_store import PointInTimeStore

MATCH = MatchResult(event_id="2024_10_LAC_KC", season=2024, week=10, home_abbr="KC", away_abbr="LAC")
KICKOFF = datetime(2024, 11, 10, 18, 0, tzinfo=UTC)


def _historical_event_payload(prop_market="player_pass_yds"):
    return {
        "id": "hist-abc",
        "home_team": "Kansas City Chiefs",
        "away_team": "Los Angeles Chargers",
        "commence_time": "2024-11-10T18:00:00Z",
        "bookmakers": [
            {
                "key": "draftkings",
                "markets": [
                    {
                        "key": prop_market,
                        "outcomes": [
                            {"name": "Over", "description": "Patrick Mahomes", "point": 275.5, "price": -110},
                            {"name": "Under", "description": "Patrick Mahomes", "point": 275.5, "price": -110},
                        ],
                    }
                ],
            }
        ],
    }


# --- find_historical_event_id ---


def test_find_historical_event_id_matches_on_team_names():
    client = MagicMock()
    client.get_historical_events.return_value = OddsApiResponse(
        events=[
            {"id": "hist-other", "home_team": "Dallas Cowboys", "away_team": "Philadelphia Eagles"},
            {"id": "hist-abc", "home_team": "Kansas City Chiefs", "away_team": "Los Angeles Chargers"},
        ],
        remaining_credits=999, used_credits=1, last_cost=1, fetched_at=KICKOFF,
    )

    event_id = find_historical_event_id(client, "2024-11-10T17:45:00Z", "Kansas City Chiefs", "Los Angeles Chargers")

    assert event_id == "hist-abc"


def test_find_historical_event_id_returns_none_when_not_found():
    client = MagicMock()
    client.get_historical_events.return_value = OddsApiResponse(
        events=[], remaining_credits=999, used_credits=1, last_cost=1, fetched_at=KICKOFF
    )

    event_id = find_historical_event_id(client, "2024-11-10T17:45:00Z", "Kansas City Chiefs", "Los Angeles Chargers")

    assert event_id is None


# --- pull_historical_prop_snapshot ---


def test_pull_historical_prop_snapshot_parses_via_the_shared_props_parser():
    client = MagicMock()
    client.get_historical_event_odds.return_value = OddsApiResponse(
        events=[_historical_event_payload()], remaining_credits=990, used_credits=10, last_cost=10, fetched_at=KICKOFF
    )

    snapshots = pull_historical_prop_snapshot(client, "hist-abc", "2024-11-10T17:45:00Z", "player_pass_yds", MATCH)

    assert len(snapshots) == 2
    assert snapshots[0].player_name == "Patrick Mahomes"
    assert snapshots[0].event_id == "2024_10_LAC_KC"
    assert snapshots[0].capture_time == KICKOFF  # the response's own fetched_at, not wall-clock now


# --- backfill_historical_props ---


def test_backfill_historical_props_writes_snapshots_for_found_games(tmp_path):
    client = MagicMock()
    client.get_historical_events.return_value = OddsApiResponse(
        events=[{"id": "hist-abc", "home_team": "Kansas City Chiefs", "away_team": "Los Angeles Chargers"}],
        remaining_credits=999, used_credits=1, last_cost=1, fetched_at=KICKOFF,
    )
    client.get_historical_event_odds.return_value = OddsApiResponse(
        events=[_historical_event_payload()], remaining_credits=989, used_credits=11, last_cost=10, fetched_at=KICKOFF
    )
    store = PointInTimeStore(root=tmp_path / "snapshots")

    counts = backfill_historical_props(
        client,
        [(MATCH, "Kansas City Chiefs", "Los Angeles Chargers", KICKOFF)],
        "player_pass_yds",
        store,
    )

    assert counts == {"found": 1, "missing": 0, "failed": 0, "malformed": 0, "written": 2}
    files = list((tmp_path / "snapshots").glob("**/*.parquet"))
    assert len(files) == 1


def test_backfill_historical_props_counts_missing_games_without_calling_odds_endpoint(tmp_path):
    client = MagicMock()
    client.get_historical_events.return_value = OddsApiResponse(
        events=[], remaining_credits=999, used_credits=1, last_cost=1, fetched_at=KICKOFF
    )
    store = PointInTimeStore(root=tmp_path / "snapshots")

    counts = backfill_historical_props(
        client, [(MATCH, "Kansas City Chiefs", "Los Angeles Chargers", KICKOFF)], "player_pass_yds", store
    )

    assert counts == {"found": 0, "missing": 1, "failed": 0, "malformed": 0, "written": 0}
    client.get_historical_event_odds.assert_not_called()  # no event id -- must not spend a 10x-cost credit call


def test_backfill_historical_props_records_api_failures_without_raising(tmp_path):
    client = MagicMock()
    client.get_historical_events.return_value = OddsApiResponse(
        events=[{"id": "hist-abc", "home_team": "Kansas City Chiefs", "away_team": "Los Angeles Chargers"}],
        remaining_credits=999, used_credits=1, last_cost=1, fetched_at=KICKOFF,
    )
    client.get_historical_event_odds.side_effect = OddsApiError("boom")
    store = PointInTimeStore(root=tmp_path / "snapshots")

    counts = backfill_historical_props(
        client, [(MATCH, "Kansas City Chiefs", "Los Angeles Chargers", KICKOFF)], "player_pass_yds", store
    )

    assert counts == {"found": 0, "missing": 0, "failed": 1, "malformed": 0, "written": 0}
