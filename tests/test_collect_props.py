from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from src.collect.client import OddsApiError, OddsApiResponse
from src.collect.props import event_odds_to_prop_snapshots, poll_all_props
from src.collect.transform import MatchResult, TransformError
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, Side

NOW = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)
MATCH = MatchResult(event_id="2026_01_KC_LAC", season=2026, week=1, home_abbr="LAC", away_abbr="KC")


def _event_payload(bookmakers):
    return {
        "id": "abc123",
        "home_team": "Los Angeles Chargers",
        "away_team": "Kansas City Chiefs",
        "commence_time": "2026-09-10T20:00:00Z",
        "bookmakers": bookmakers,
    }


def test_event_odds_to_prop_snapshots_parses_over_under_pair():
    payload = _event_payload(
        [
            {
                "key": "draftkings",
                "markets": [
                    {
                        "key": "player_pass_yds",
                        "outcomes": [
                            {"name": "Over", "description": "Patrick Mahomes", "point": 275.5, "price": -110},
                            {"name": "Under", "description": "Patrick Mahomes", "point": 275.5, "price": -110},
                        ],
                    }
                ],
            }
        ]
    )

    snapshots = event_odds_to_prop_snapshots(payload, NOW, MATCH)

    assert len(snapshots) == 2
    over, under = snapshots
    assert over.side == Side.OVER
    assert over.player_name == "Patrick Mahomes"
    assert over.prop_stat == "passing_yards"
    assert over.market == Market.PLAYER_PROP
    assert over.line == 275.5
    assert over.event_id == "2026_01_KC_LAC"
    assert under.side == Side.UNDER


def test_event_odds_to_prop_snapshots_skips_unsupported_markets():
    payload = _event_payload(
        [
            {
                "key": "draftkings",
                "markets": [
                    {"key": "player_anytime_td", "outcomes": [{"name": "Yes", "description": "A.J. Brown", "price": 2.5}]}
                ],
            }
        ]
    )
    assert event_odds_to_prop_snapshots(payload, NOW, MATCH) == []


def test_event_odds_to_prop_snapshots_skips_non_over_under_outcomes_in_a_supported_market():
    # A market key we support, but with a stray non-O/U outcome mixed in
    # (shouldn't happen per the API, but must not crash if it does).
    payload = _event_payload(
        [
            {
                "key": "draftkings",
                "markets": [
                    {
                        "key": "player_pass_yds",
                        "outcomes": [
                            {"name": "Over", "description": "Patrick Mahomes", "point": 275.5, "price": -110},
                            {"name": "Yes", "description": "Patrick Mahomes", "price": 100},
                        ],
                    }
                ],
            }
        ]
    )
    snapshots = event_odds_to_prop_snapshots(payload, NOW, MATCH)
    assert len(snapshots) == 1
    assert snapshots[0].side == Side.OVER


def test_event_odds_to_prop_snapshots_raises_on_missing_player_name():
    payload = _event_payload(
        [
            {
                "key": "draftkings",
                "markets": [
                    {"key": "player_pass_yds", "outcomes": [{"name": "Over", "point": 275.5, "price": -110}]}
                ],
            }
        ]
    )
    with pytest.raises(TransformError):
        event_odds_to_prop_snapshots(payload, NOW, MATCH)


def test_event_odds_to_prop_snapshots_raises_on_missing_commence_time():
    payload = _event_payload([])
    del payload["commence_time"]
    with pytest.raises(TransformError):
        event_odds_to_prop_snapshots(payload, NOW, MATCH)


# --- poll_all_props ---

NAME_TO_ABBR = {"Los Angeles Chargers": "LAC", "Kansas City Chiefs": "KC"}
SCHEDULE_INDEX = {(2026, "LAC", "KC"): MATCH}


def test_poll_all_props_writes_snapshots_for_matched_events(tmp_path):
    client = MagicMock()
    client.get_event_odds.return_value = OddsApiResponse(
        events=[
            _event_payload(
                [
                    {
                        "key": "draftkings",
                        "markets": [
                            {
                                "key": "player_pass_yds",
                                "outcomes": [
                                    {"name": "Over", "description": "Patrick Mahomes", "point": 275.5, "price": -110},
                                    {"name": "Under", "description": "Patrick Mahomes", "point": 275.5, "price": -110},
                                ],
                            }
                        ],
                    }
                ]
            )
        ],
        remaining_credits=440,
        used_credits=10,
        last_cost=2,
        fetched_at=NOW,
    )
    store = PointInTimeStore(root=tmp_path / "snapshots")

    counts = poll_all_props(
        client, [("abc123", "Los Angeles Chargers", "Kansas City Chiefs")], 2026, SCHEDULE_INDEX, NAME_TO_ABBR, store
    )

    assert counts == {"matched": 1, "unmatched": 0, "malformed": 0, "failed": 0, "written": 2}
    files = list((tmp_path / "snapshots").glob("**/*.parquet"))
    assert len(files) == 1


def test_poll_all_props_skips_unmatched_events_without_calling_the_api(tmp_path):
    client = MagicMock()
    store = PointInTimeStore(root=tmp_path / "snapshots")

    counts = poll_all_props(client, [("xyz", "Unknown Team", "Kansas City Chiefs")], 2026, SCHEDULE_INDEX, NAME_TO_ABBR, store)

    assert counts == {"matched": 0, "unmatched": 1, "malformed": 0, "failed": 0, "written": 0}
    client.get_event_odds.assert_not_called()  # unmatched events must not spend a per-event credit


def test_poll_all_props_records_failed_calls_without_raising(tmp_path):
    client = MagicMock()
    client.get_event_odds.side_effect = OddsApiError("boom")
    store = PointInTimeStore(root=tmp_path / "snapshots")

    counts = poll_all_props(
        client, [("abc123", "Los Angeles Chargers", "Kansas City Chiefs")], 2026, SCHEDULE_INDEX, NAME_TO_ABBR, store
    )

    assert counts == {"matched": 0, "unmatched": 0, "malformed": 0, "failed": 1, "written": 0}
