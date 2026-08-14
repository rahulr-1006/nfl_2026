from datetime import UTC, date, datetime, timedelta

from src.collect.budget import (
    CollectorState,
    current_period_end,
    decide_poll,
    load_state,
    parse_quota_headers,
    save_state,
)

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)

_DEFAULTS = {
    "full_regions": "eu",
    "full_markets": "h2h,spreads,totals",
    "reduced_markets": "spreads,totals",
    "full_cost": 3,
    "reduced_cost": 2,
    "dense_window_hours": 48.0,
    "dense_interval_minutes": 30.0,
    "sparse_interval_minutes": 60.0,
    "min_interval_minutes": 15.0,
    "safety_reserve_credits": 20,
}


def _decide(**overrides):
    kwargs = {
        "now": NOW,
        "upcoming_kickoffs": [NOW + timedelta(hours=10)],
        "remaining_credits": 400,
        "period_end": NOW + timedelta(days=20),
        "last_poll_time": None,
        **_DEFAULTS,
    }
    kwargs.update(overrides)
    return decide_poll(**kwargs)


def test_dense_cadence_near_kickoff_with_ample_budget():
    # Budget so generous that budget_interval collapses below the floor,
    # isolating game_interval as the binding constraint.
    decision = _decide(upcoming_kickoffs=[NOW + timedelta(hours=10)], remaining_credits=1_000_000)
    assert decision.should_poll is True
    assert decision.effective_interval_minutes == 30.0


def test_sparse_cadence_midweek_with_ample_budget():
    decision = _decide(upcoming_kickoffs=[NOW + timedelta(hours=96)], remaining_credits=1_000_000)
    assert decision.should_poll is True
    assert decision.effective_interval_minutes == 60.0


def test_tight_budget_degrades_cadence_below_game_driven_interval():
    ample = _decide(remaining_credits=400, period_end=NOW + timedelta(days=20))
    tight = _decide(remaining_credits=25, period_end=NOW + timedelta(days=20))
    assert tight.effective_interval_minutes > ample.effective_interval_minutes


def test_credits_at_or_below_safety_reserve_exhausts_budget():
    decision = _decide(remaining_credits=20)  # == safety_reserve_credits
    assert decision.should_poll is False
    assert decision.reason == "budget_exhausted"


def test_tight_budget_falls_back_to_reduced_markets_tier():
    # remaining - reserve = 30; full_cost=3 -> 10 affordable; reduced_cost=2 -> 15 affordable.
    # Force full tier unaffordable by shrinking remaining so only reduced tier clears.
    decision = _decide(remaining_credits=22, period_end=NOW + timedelta(minutes=1))
    # remaining-reserve=2, full_cost=3 -> 0 affordable full polls; reduced_cost=2 -> 1 affordable
    assert decision.markets == "spreads,totals"
    assert decision.reason in ("ok", "too_soon")


def test_both_tiers_unaffordable_is_budget_exhausted():
    decision = _decide(remaining_credits=21)  # remaining-reserve=1, less than either cost
    assert decision.should_poll is False
    assert decision.reason == "budget_exhausted"


def test_too_soon_when_within_effective_interval_of_last_poll():
    decision = _decide(
        upcoming_kickoffs=[NOW + timedelta(hours=96)],
        remaining_credits=400,
        last_poll_time=NOW - timedelta(minutes=10),
    )
    assert decision.should_poll is False
    assert decision.reason == "too_soon"


def test_no_upcoming_kickoffs_still_produces_sparse_decision_not_a_crash():
    decision = _decide(upcoming_kickoffs=[], remaining_credits=1_000_000)
    assert decision.should_poll is True
    assert decision.effective_interval_minutes == 60.0


def test_remaining_credits_none_bootstraps_with_full_tier():
    decision = _decide(remaining_credits=None)
    assert decision.should_poll is True
    assert decision.markets == "h2h,spreads,totals"
    assert decision.reason == "ok"


def test_parse_quota_headers_present():
    quota = parse_quota_headers(
        {"x-requests-remaining": "494", "x-requests-used": "6", "x-requests-last": "6"}
    )
    assert quota.remaining == 494
    assert quota.used == 6
    assert quota.last_cost == 6


def test_parse_quota_headers_missing():
    quota = parse_quota_headers({})
    assert quota.remaining is None
    assert quota.used is None
    assert quota.last_cost is None


def test_parse_quota_headers_malformed():
    quota = parse_quota_headers({"x-requests-remaining": "not-a-number"})
    assert quota.remaining is None


def test_current_period_end_rolls_forward_past_now():
    anchor = date(2026, 8, 1)
    end = current_period_end(NOW, anchor, period_days=30)
    assert end > NOW
    assert end <= NOW + timedelta(days=30)


def test_current_period_end_stable_for_anchor_already_in_future_window():
    anchor = date(2026, 9, 1)
    end = current_period_end(NOW, anchor, period_days=30)
    assert end == datetime(2026, 10, 1, tzinfo=UTC)


def test_state_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    state = CollectorState(
        last_poll_time=NOW, remaining_credits=100, period_anchor=date(2026, 8, 1), consecutive_failures=2
    )
    save_state(path, state)
    loaded = load_state(path)
    assert loaded == state


def test_load_state_missing_file_returns_none(tmp_path):
    assert load_state(tmp_path / "missing.json") is None
