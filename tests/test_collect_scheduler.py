from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from src.collect.budget import CollectorState, load_state, save_state
from src.collect.client import OddsApiError, OddsApiResponse
from src.collect.config import Config
from src.collect.scheduler import CollectorContext, CollectorHalted, tick
from src.collect.transform import MatchResult, TransformError
from src.store.pit_store import PointInTimeStore

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)


def _config(tmp_path, **overrides):
    defaults = {
        "api_key": "key",
        "store_root": tmp_path / "snapshots",
        "state_path": tmp_path / "state.json",
        "max_consecutive_failures": 2,
        "min_interval_minutes": 15.0,
    }
    defaults.update(overrides)
    return Config(**defaults)


def _ctx(tmp_path, client, config=None, upcoming_kickoffs=None):
    config = config or _config(tmp_path)
    return CollectorContext(
        config=config,
        client=client,
        store=PointInTimeStore(root=config.store_root),
        schedule_index={
            (2026, "SEA", "NE"): MatchResult(
                event_id="2026_01_NE_SEA", season=2026, week=1, home_abbr="SEA", away_abbr="NE"
            )
        },
        name_to_abbr={"Seattle Seahawks": "SEA", "New England Patriots": "NE"},
        upcoming_kickoffs=upcoming_kickoffs or [NOW + timedelta(hours=10)],
    )


def _pinnacle_event(home="Seattle Seahawks", away="New England Patriots"):
    return {
        "home_team": home,
        "away_team": away,
        "commence_time": "2026-09-10T00:15:00Z",
        "bookmakers": [
            {
                "key": "pinnacle",
                "markets": [{"key": "h2h", "outcomes": [{"name": away, "price": 150}, {"name": home, "price": -180}]}],
            }
        ],
    }


def test_tick_writes_snapshots_for_matched_events(tmp_path):
    client = MagicMock()
    client.get_odds.return_value = OddsApiResponse(
        events=[_pinnacle_event()], remaining_credits=490, used_credits=10, last_cost=3, fetched_at=NOW
    )
    config = _config(tmp_path)
    ctx = _ctx(tmp_path, client, config)

    tick(ctx)

    files = list(config.store_root.glob("**/*.parquet"))
    assert len(files) == 1


def test_tick_skips_unmatched_events_without_writing_them(tmp_path):
    client = MagicMock()
    unmatched = _pinnacle_event(home="Arizona Cardinals", away="Seattle Seahawks")
    client.get_odds.return_value = OddsApiResponse(
        events=[unmatched], remaining_credits=490, used_credits=10, last_cost=3, fetched_at=NOW
    )
    config = _config(tmp_path)
    ctx = _ctx(tmp_path, client, config)

    tick(ctx)  # must not raise

    files = list(config.store_root.glob("**/*.parquet"))
    assert files == []


def test_tick_persists_state_after_successful_poll(tmp_path):
    client = MagicMock()
    client.get_odds.return_value = OddsApiResponse(
        events=[], remaining_credits=488, used_credits=12, last_cost=3, fetched_at=NOW
    )
    config = _config(tmp_path)
    ctx = _ctx(tmp_path, client, config)

    tick(ctx)

    state = load_state(config.state_path)
    assert state.remaining_credits == 488
    assert state.consecutive_failures == 0
    assert state.last_poll_time is not None


def test_tick_does_not_poll_when_too_soon(tmp_path):
    client = MagicMock()
    config = _config(tmp_path)
    save_state(
        config.state_path,
        CollectorState(
            last_poll_time=datetime.now(UTC), remaining_credits=490,
            period_anchor=datetime.now(UTC).date(),
        ),
    )
    ctx = _ctx(tmp_path, client, config)

    tick(ctx)

    client.get_odds.assert_not_called()


def test_tick_records_failure_on_api_error_without_raising(tmp_path):
    client = MagicMock()
    client.get_odds.side_effect = OddsApiError("boom")
    config = _config(tmp_path, max_consecutive_failures=5)
    ctx = _ctx(tmp_path, client, config)

    tick(ctx)  # must not raise

    state = load_state(config.state_path)
    assert state.consecutive_failures == 1


def test_tick_raises_collector_halted_after_too_many_failures(tmp_path):
    client = MagicMock()
    client.get_odds.side_effect = OddsApiError("boom")
    config = _config(tmp_path, max_consecutive_failures=1)
    ctx = _ctx(tmp_path, client, config)

    tick(ctx)  # 1st failure, under threshold
    with pytest.raises(CollectorHalted):
        tick(ctx)  # 2nd failure, exceeds threshold


def test_tick_swallows_unexpected_exception_from_a_single_event(tmp_path, monkeypatch):
    client = MagicMock()
    good_event = _pinnacle_event()
    client.get_odds.return_value = OddsApiResponse(
        events=[good_event], remaining_credits=490, used_credits=10, last_cost=3, fetched_at=NOW
    )
    config = _config(tmp_path)
    ctx = _ctx(tmp_path, client, config)

    def _boom(*args, **kwargs):
        raise TransformError("malformed")

    monkeypatch.setattr("src.collect.scheduler.event_to_snapshots", _boom)

    tick(ctx)  # must not raise, and must not blow up the whole tick

    files = list(config.store_root.glob("**/*.parquet"))
    assert files == []


def test_tick_never_propagates_unexpected_bug(tmp_path, monkeypatch):
    client = MagicMock()
    client.get_odds.side_effect = RuntimeError("totally unexpected bug")
    config = _config(tmp_path)
    ctx = _ctx(tmp_path, client, config)

    tick(ctx)  # the outer try/except in tick() must catch this
