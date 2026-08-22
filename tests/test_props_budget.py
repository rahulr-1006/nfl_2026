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


def test_second_target_poll_fires_once_inside_its_window():
    # poll_targets_hours=[100.0, 10.0] -> poll #1 (poll_count=1) fires once <=10h to kickoff
    kickoff = NOW + timedelta(hours=3)
    state = EventPollState(poll_count=1, last_polled_at=NOW - timedelta(days=2))
    decision = decide_props_poll(NOW, kickoff, state, remaining_credits=10000, poll_targets_hours=[100.0, 10.0])
    assert decision.should_poll
    assert decision.reason == "ok"


def test_second_target_poll_does_not_fire_too_far_before_its_target():
    kickoff = NOW + timedelta(hours=20)
    state = EventPollState(poll_count=1, last_polled_at=NOW - timedelta(days=2))
    decision = decide_props_poll(NOW, kickoff, state, remaining_credits=10000, poll_targets_hours=[100.0, 10.0])
    assert not decision.should_poll
    assert decision.reason == "not_yet_in_window"


def test_later_polls_walk_through_the_target_list_in_order():
    # poll_targets_hours=[100.0, 10.0, 4.0] -> poll #2 (poll_count=2) waits
    # for the THIRD target (4h), not the second (10h) -- confirms indexing.
    kickoff = NOW + timedelta(hours=6)
    state = EventPollState(poll_count=2, last_polled_at=NOW - timedelta(hours=4))
    decision = decide_props_poll(NOW, kickoff, state, remaining_credits=10000, poll_targets_hours=[100.0, 10.0, 4.0])
    assert not decision.should_poll
    assert decision.reason == "not_yet_in_window"


def test_dense_poll_targets_hours_produces_the_expected_default_schedule():
    from src.collect.props_budget import dense_poll_targets_hours

    targets = dense_poll_targets_hours(dense_window_hours=48.0, dense_poll_interval_hours=2.0)
    assert len(targets) == 24
    assert targets[0] == 48.0
    assert targets[-1] == 2.0


def test_sparse_poll_targets_hours_covers_the_gap_before_the_dense_window():
    from src.collect.props_budget import sparse_poll_targets_hours

    targets = sparse_poll_targets_hours(posting_window_days=5.0, dense_window_hours=48.0, sparse_poll_interval_hours=8.0)
    assert len(targets) == 9  # (120 - 48) / 8
    assert targets[0] == 120.0  # fires as soon as the event enters the 5-day posting window
    assert targets[-1] == 56.0  # last sparse target, just above the 48h dense-tier boundary
    assert all(t > 48.0 for t in targets)  # sparse tier never overlaps the dense tier's own range


def test_combined_poll_targets_hours_is_sparse_then_dense_in_descending_order():
    from src.collect.props_budget import POLL_TARGETS_HOURS

    assert list(POLL_TARGETS_HOURS) == sorted(POLL_TARGETS_HOURS, reverse=True)
    assert POLL_TARGETS_HOURS[0] == 120.0  # first sparse target
    assert POLL_TARGETS_HOURS[-1] == 2.0  # last dense target


def test_already_fully_polled_events_are_skipped():
    kickoff = NOW + timedelta(hours=1)
    state = EventPollState(poll_count=1, last_polled_at=NOW - timedelta(hours=5))
    decision = decide_props_poll(NOW, kickoff, state, remaining_credits=10000, poll_targets_hours=[10.0])
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


def test_missed_first_poll_still_fires_close_to_kickoff():
    # poll_count still 0 (first poll never happened, e.g. service was down)
    # but we're now close to kickoff -- better one late poll than none.
    # hours_to_kickoff=2 is well inside every target in the default combined
    # schedule (first target is 120h out), so this should still fire.
    kickoff = NOW + timedelta(hours=2)
    decision = decide_props_poll(NOW, kickoff, EventPollState(poll_count=0), remaining_credits=10000)
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
