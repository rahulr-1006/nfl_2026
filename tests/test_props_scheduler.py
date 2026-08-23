import logging
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
        events=[_event(commence_time=(NOW + timedelta(days=40)).isoformat().replace("+00:00", "Z"))],
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


def test_empty_poll_does_not_advance_the_schedule(tmp_path):
    """**The fix that makes a 21-day posting window safe.** Probing a game whose
    props have not posted costs 0 credits (the live endpoint bills only for
    markets that return data), but the schedule is a fixed ~34-slot budget per
    event. Counting free empty probes would burn the whole schedule during the
    weeks before props exist, leaving nothing for the pre-kickoff window that
    actually matters. The schedule must track CAPTURES, not API calls.
    """
    client = MagicMock()
    commence = (NOW + timedelta(days=15)).isoformat().replace("+00:00", "Z")
    client.get_events.return_value = OddsApiResponse(
        events=[_event(event_id="evt_early", commence_time=commence)],
        remaining_credits=None, used_credits=None, last_cost=None, fetched_at=NOW,
    )
    # A real API response carrying NO bookmakers -- props not posted yet.
    client.get_event_odds.return_value = OddsApiResponse(
        events=[{"home_team": "Seattle Seahawks", "away_team": "New England Patriots",
                 "commence_time": commence, "bookmakers": []}],
        remaining_credits=25000, used_credits=0, last_cost=0, fetched_at=NOW,
    )
    ctx = _ctx(tmp_path, client)

    tick(ctx, now=NOW)
    tick(ctx, now=NOW)

    client.get_event_odds.assert_called()          # it DID probe (free)
    state = load_state(ctx.state_path)
    assert state.events.get("evt_early", EventPollState()).poll_count == 0  # but banked nothing



def test_empty_probe_and_not_due_are_counted_separately(tmp_path, caplog):
    """**Dry-run finding, 2026-08-23.** Both paths were reported as one
    `skipped` number, which made "we contacted N games and they have no props
    yet" indistinguishable from "we never looked". Against the live services
    this read `polled=0 skipped=272` while ~10 events were in fact being probed
    every tick -- so props silently ceasing to post, or the endpoint returning
    empties, would have looked exactly like healthy out-of-window operation.
    `failed` already separated API errors; these two did not.
    """
    in_window = (NOW + timedelta(days=15)).isoformat().replace("+00:00", "Z")
    far_out = (NOW + timedelta(days=300)).isoformat().replace("+00:00", "Z")

    client = MagicMock()
    client.get_events.return_value = OddsApiResponse(
        events=[_event(event_id="evt_near", commence_time=in_window),
                _event(event_id="evt_far", commence_time=far_out)],
        remaining_credits=None, used_credits=None, last_cost=None, fetched_at=NOW,
    )
    client.get_event_odds.return_value = OddsApiResponse(
        events=[{"home_team": "Seattle Seahawks", "away_team": "New England Patriots",
                 "commence_time": in_window, "bookmakers": []}],   # probed, nothing posted
        remaining_credits=25000, used_credits=0, last_cost=0, fetched_at=NOW,
    )

    caplog.set_level(logging.INFO, logger="src.collect.props_scheduler")
    tick(_ctx(tmp_path, client), now=NOW)

    # Exactly one event was contacted; the far-out one never was.
    assert client.get_event_odds.call_count == 1
    assert "polled=0 empty=1 not_due=1" in caplog.text


def test_tick_never_polls_a_game_that_has_already_kicked_off(tmp_path):
    """**Pre-kickoff is the whole methodology.** Every strategy here is priced
    entry-vs-close, and in-play prop books re-price on every snap -- so an
    in-play quote is both expensive (a full per-event call) and useless. The
    guard lives in `decide_props_poll` (`event_started`) and fires BEFORE the
    budget check, so no API call is made at all. Previously untested, which
    meant a reordering of those checks would have gone unnoticed.
    """
    started = (NOW - timedelta(minutes=30)).isoformat().replace("+00:00", "Z")
    client = MagicMock()
    client.get_events.return_value = OddsApiResponse(
        events=[_event(event_id="evt_live", commence_time=started)],
        remaining_credits=None, used_credits=None, last_cost=None, fetched_at=NOW,
    )
    tick(_ctx(tmp_path, client), now=NOW)
    client.get_event_odds.assert_not_called()


def test_kickoff_guard_precedes_the_budget_check(tmp_path):
    """Order matters: if the budget check ran first, a well-funded key would
    happily pay for in-play polls.
    """
    from src.collect.props_budget import EventPollState, decide_props_poll

    started = NOW - timedelta(minutes=1)
    d = decide_props_poll(NOW, started, EventPollState(), remaining_credits=999_999)
    assert not d.should_poll
    assert d.reason == "event_started"
