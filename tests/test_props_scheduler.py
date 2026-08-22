from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from src.collect.client import OddsApiError, OddsApiResponse
from src.collect.props_budget import (
    POLLS_PER_EVENT,
    EventPollState,
    PropsCollectorState,
    load_state,
    save_state,
)
from src.collect.props_scheduler import PropsCollectorContext, tick
from src.collect.transform import MatchResult
from src.store.pit_store import PointInTimeStore

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)


def _ctx(tmp_path, client, tick_minutes=30.0):
    return PropsCollectorContext(
        season=2026,
        client=client,
        store=PointInTimeStore(root=tmp_path / "snapshots"),
        schedule_index={
            (2026, "SEA", "NE"): MatchResult(
                event_id="2026_01_NE_SEA", season=2026, week=1, home_abbr="SEA", away_abbr="NE"
            )
        },
        name_to_abbr={"Seattle Seahawks": "SEA", "New England Patriots": "NE"},
        state_path=tmp_path / "props_state.json",
        tick_minutes=tick_minutes,
    )


def _event(event_id="odds_api_evt_1", home="Seattle Seahawks", away="New England Patriots", commence_time="2026-09-06T00:15:00Z"):
    return {"id": event_id, "home_team": home, "away_team": away, "commence_time": commence_time}


def _prop_event_odds(home="Seattle Seahawks", away="New England Patriots"):
    return {
        "home_team": home,
        "away_team": away,
        "commence_time": "2026-09-06T00:15:00Z",
        "bookmakers": [
            {
                "key": "pinnacle",
                "markets": [
                    {
                        "key": "player_reception_yds",
                        "outcomes": [
                            {"name": "Over", "description": "Player X", "price": -110, "point": 45.5},
                            {"name": "Under", "description": "Player X", "price": -110, "point": 45.5},
                        ],
                    }
                ],
            }
        ],
    }


def test_tick_polls_an_eligible_event_and_writes_snapshots(tmp_path):
    client = MagicMock()
    # commence_time is ~2 days out -- inside the default 5-day posting window
    client.get_events.return_value = OddsApiResponse(
        events=[_event(commence_time=(NOW + timedelta(days=2)).isoformat().replace("+00:00", "Z"))],
        remaining_credits=None, used_credits=None, last_cost=None, fetched_at=NOW,
    )
    client.get_event_odds.return_value = OddsApiResponse(
        events=[_prop_event_odds()], remaining_credits=19900, used_credits=100, last_cost=14, fetched_at=NOW,
    )
    ctx = _ctx(tmp_path, client)

    tick(ctx, now=NOW)

    client.get_event_odds.assert_called_once()
    files = list((tmp_path / "snapshots").glob("**/*.parquet"))
    assert len(files) == 1


def test_tick_skips_an_event_outside_the_posting_window(tmp_path):
    client = MagicMock()
    client.get_events.return_value = OddsApiResponse(
        events=[_event(commence_time=(NOW + timedelta(days=10)).isoformat().replace("+00:00", "Z"))],
        remaining_credits=None, used_credits=None, last_cost=None, fetched_at=NOW,
    )
    ctx = _ctx(tmp_path, client)

    tick(ctx, now=NOW)

    client.get_event_odds.assert_not_called()


def test_tick_persists_per_event_poll_state(tmp_path):
    client = MagicMock()
    commence = (NOW + timedelta(days=2)).isoformat().replace("+00:00", "Z")
    client.get_events.return_value = OddsApiResponse(
        events=[_event(event_id="evt_abc", commence_time=commence)],
        remaining_credits=None, used_credits=None, last_cost=None, fetched_at=NOW,
    )
    client.get_event_odds.return_value = OddsApiResponse(
        events=[_prop_event_odds()], remaining_credits=19900, used_credits=100, last_cost=14, fetched_at=NOW,
    )
    ctx = _ctx(tmp_path, client)

    tick(ctx, now=NOW)

    state = load_state(ctx.state_path)
    assert state.events["evt_abc"].poll_count == 1
    assert state.remaining_credits == 19900


def test_tick_does_not_repoll_an_event_already_fully_polled(tmp_path):
    client = MagicMock()
    commence = (NOW + timedelta(hours=3)).isoformat().replace("+00:00", "Z")
    client.get_events.return_value = OddsApiResponse(
        events=[_event(event_id="evt_done", commence_time=commence)],
        remaining_credits=None, used_credits=None, last_cost=None, fetched_at=NOW,
    )
    save_state(
        tmp_path / "props_state.json",
        PropsCollectorState(events={"evt_done": EventPollState(poll_count=POLLS_PER_EVENT, last_polled_at=NOW - timedelta(days=1))}),
    )
    ctx = _ctx(tmp_path, client)

    tick(ctx, now=NOW)

    client.get_event_odds.assert_not_called()


def test_tick_skips_unmatched_events_without_crashing(tmp_path):
    client = MagicMock()
    commence = (NOW + timedelta(days=2)).isoformat().replace("+00:00", "Z")
    client.get_events.return_value = OddsApiResponse(
        events=[_event(home="Arizona Cardinals", away="Seattle Seahawks", commence_time=commence)],
        remaining_credits=None, used_credits=None, last_cost=None, fetched_at=NOW,
    )
    ctx = _ctx(tmp_path, client)

    tick(ctx, now=NOW)  # must not raise

    client.get_event_odds.assert_not_called()


def test_tick_swallows_events_listing_failure_without_raising(tmp_path):
    client = MagicMock()
    client.get_events.side_effect = OddsApiError("boom")
    ctx = _ctx(tmp_path, client)

    tick(ctx, now=NOW)  # must not raise


def test_tick_never_propagates_unexpected_bug(tmp_path):
    client = MagicMock()
    client.get_events.side_effect = RuntimeError("totally unexpected bug")
    ctx = _ctx(tmp_path, client)

    tick(ctx, now=NOW)  # the outer try/except in tick() must catch this
