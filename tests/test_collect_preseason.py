from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from src.collect.client import OddsApiError, OddsApiResponse
from src.collect.preseason import build_preseason_match, poll_once
from src.collect.transform import TransformError, UnmatchedEventError
from src.store.pit_store import PointInTimeStore

NOW = datetime(2026, 8, 17, 12, 0, tzinfo=UTC)
NAME_TO_ABBR = {"Houston Texans": "HOU", "Las Vegas Raiders": "LV"}


def _preseason_event(event_id="abc123", home="Houston Texans", away="Las Vegas Raiders"):
    return {
        "id": event_id,
        "home_team": home,
        "away_team": away,
        "commence_time": "2026-08-21T00:00:00Z",
        "bookmakers": [
            {
                "key": "fanduel",
                "markets": [{"key": "h2h", "outcomes": [{"name": away, "price": 150}, {"name": home, "price": -180}]}],
            }
        ],
    }


def test_build_preseason_match_uses_odds_api_id_with_pre_prefix():
    match = build_preseason_match(_preseason_event(event_id="xyz789"), NAME_TO_ABBR, season=2026)
    assert match.event_id == "2026_PRE_xyz789"
    assert match.season == 2026
    assert match.week == 0
    assert match.home_abbr == "HOU"
    assert match.away_abbr == "LV"


def test_build_preseason_match_raises_on_unknown_team_name():
    event = _preseason_event(home="Unknown Team")
    with pytest.raises(UnmatchedEventError):
        build_preseason_match(event, NAME_TO_ABBR, season=2026)


def test_build_preseason_match_raises_on_missing_odds_api_id():
    event = _preseason_event()
    del event["id"]
    with pytest.raises(TransformError):
        build_preseason_match(event, NAME_TO_ABBR, season=2026)


def test_poll_once_writes_snapshots_for_matched_events(tmp_path):
    client = MagicMock()
    client.get_odds.return_value = OddsApiResponse(
        events=[_preseason_event()], remaining_credits=480, used_credits=20, last_cost=9, fetched_at=NOW
    )
    store = PointInTimeStore(root=tmp_path / "snapshots_preseason")

    counts = poll_once(client, NAME_TO_ABBR, store, season=2026)

    assert counts == {"matched": 1, "unmatched": 0, "malformed": 0, "written": 2}  # 1 bookmaker x 1 market x 2 outcomes (home, away)
    files = list((tmp_path / "snapshots_preseason").glob("**/*.parquet"))
    assert len(files) == 1


def test_poll_once_skips_unmatched_events_without_writing_them(tmp_path):
    client = MagicMock()
    unmatched_event = _preseason_event(home="Unknown Team")
    client.get_odds.return_value = OddsApiResponse(
        events=[unmatched_event], remaining_credits=480, used_credits=20, last_cost=9, fetched_at=NOW
    )
    store = PointInTimeStore(root=tmp_path / "snapshots_preseason")

    counts = poll_once(client, NAME_TO_ABBR, store, season=2026)

    assert counts == {"matched": 0, "unmatched": 1, "malformed": 0, "written": 0}
    files = list((tmp_path / "snapshots_preseason").glob("**/*.parquet"))
    assert files == []


def test_poll_once_never_raises_on_api_error(tmp_path):
    client = MagicMock()
    client.get_odds.side_effect = OddsApiError("boom")
    store = PointInTimeStore(root=tmp_path / "snapshots_preseason")

    counts = poll_once(client, NAME_TO_ABBR, store, season=2026)  # must not raise

    assert counts == {"matched": 0, "unmatched": 0, "malformed": 0, "written": 0}


def test_two_polls_of_the_same_game_share_an_event_id(tmp_path):
    """The whole point of keying off Odds API's own event id: entry and
    close snapshots for the same preseason game must land under the same
    event_id across separate polls, with no schedule join required.
    """
    client = MagicMock()
    client.get_odds.return_value = OddsApiResponse(
        events=[_preseason_event(event_id="same-game")], remaining_credits=480, used_credits=20, last_cost=9, fetched_at=NOW
    )
    store = PointInTimeStore(root=tmp_path / "snapshots_preseason")

    poll_once(client, NAME_TO_ABBR, store, season=2026)
    poll_once(client, NAME_TO_ABBR, store, season=2026)

    df = store.read_as_of(NOW + timedelta(hours=1))
    assert df["event_id"].unique().tolist() == ["2026_PRE_same-game"]
