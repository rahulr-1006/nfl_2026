from datetime import UTC, datetime, timedelta

from src.collect.props_budget import (
    EventPollState,
    PropsCollectorState,
    decide_props_poll,
    load_state,
    save_state,
)

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)


def test_entry_poll_fires_once_inside_the_posting_window():
    kickoff = NOW + timedelta(days=3)  # inside the default 5-day posting window
    decision = decide_props_poll(NOW, kickoff, EventPollState(), remaining_credits=10000)
    assert decision.should_poll
    assert decision.reason == "ok"


def test_entry_poll_does_not_fire_too_far_before_kickoff():
    kickoff = NOW + timedelta(days=10)  # outside the 5-day posting window
    decision = decide_props_poll(NOW, kickoff, EventPollState(), remaining_credits=10000)
    assert not decision.should_poll
    assert decision.reason == "not_yet_in_window"


def test_close_poll_fires_once_inside_the_closing_window():
    kickoff = NOW + timedelta(hours=3)  # inside the default 6-hour closing window
    state = EventPollState(poll_count=1, last_polled_at=NOW - timedelta(days=2))
    decision = decide_props_poll(NOW, kickoff, state, remaining_credits=10000)
    assert decision.should_poll
    assert decision.reason == "ok"


def test_close_poll_does_not_fire_too_far_before_kickoff():
    kickoff = NOW + timedelta(hours=20)  # outside the 6-hour closing window
    state = EventPollState(poll_count=1, last_polled_at=NOW - timedelta(days=2))
    decision = decide_props_poll(NOW, kickoff, state, remaining_credits=10000)
    assert not decision.should_poll
    assert decision.reason == "not_yet_in_window"


def test_already_fully_polled_events_are_skipped():
    kickoff = NOW + timedelta(hours=1)
    state = EventPollState(poll_count=2, last_polled_at=NOW - timedelta(hours=5))
    decision = decide_props_poll(NOW, kickoff, state, remaining_credits=10000)
    assert not decision.should_poll
    assert decision.reason == "already_fully_polled"


def test_started_events_are_never_polled_even_if_under_polled():
    kickoff = NOW - timedelta(minutes=5)  # already kicked off
    decision = decide_props_poll(NOW, kickoff, EventPollState(), remaining_credits=10000)
    assert not decision.should_poll
    assert decision.reason == "event_started"


def test_budget_exhaustion_blocks_a_poll_that_would_otherwise_fire():
    kickoff = NOW + timedelta(days=1)
    # remaining_credits(510) - safety_reserve(500) = 10 < cost_per_poll(14) -> blocked
    decision = decide_props_poll(NOW, kickoff, EventPollState(), remaining_credits=510, safety_reserve_credits=500, cost_per_poll=14)
    assert not decision.should_poll
    assert decision.reason == "budget_exhausted"


def test_budget_exhaustion_is_ignored_when_credits_are_unknown():
    # remaining_credits=None means "haven't observed a real API response yet" --
    # same bootstrap behavior as the mainline collector's decide_poll.
    kickoff = NOW + timedelta(days=1)
    decision = decide_props_poll(NOW, kickoff, EventPollState(), remaining_credits=None)
    assert decision.should_poll


def test_missed_entry_window_still_takes_a_first_poll_inside_closing_window():
    # poll_count still 0 (entry never happened, e.g. service was down) but
    # we're now inside the closing window -- better one late poll than none.
    kickoff = NOW + timedelta(hours=2)
    decision = decide_props_poll(NOW, kickoff, EventPollState(poll_count=0), remaining_credits=10000, closing_window_hours=6.0)
    # Entry-poll branch only checks posting_window_days, and 2 hours is well
    # inside the 5-day posting window too, so this should still fire as an
    # entry poll -- confirms it doesn't fall through the cracks.
    assert decision.should_poll


def test_state_round_trips_through_json():
    state = PropsCollectorState(
        events={
            "2026_01_KC_LAC": EventPollState(poll_count=1, last_polled_at=NOW),
            "2026_01_BAL_IND": EventPollState(poll_count=0, last_polled_at=None),
        },
        remaining_credits=19500,
    )
    restored = PropsCollectorState.from_json(state.to_json())
    assert restored == state


def test_state_persists_to_disk_and_reloads(tmp_path):
    path = tmp_path / "props_state.json"
    state = PropsCollectorState(events={"E1": EventPollState(poll_count=1, last_polled_at=NOW)}, remaining_credits=100)
    save_state(path, state)
    reloaded = load_state(path)
    assert reloaded == state


def test_load_state_with_no_file_returns_empty_state(tmp_path):
    state = load_state(tmp_path / "does_not_exist.json")
    assert state == PropsCollectorState()
