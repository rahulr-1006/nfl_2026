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


# --- kickoff-weighted allocation (2026-09-08) ---------------------------------
#
# The pre-existing dense-cadence test above passes `remaining_credits=1_000_000`
# to make the budget term collapse, which is exactly why the real bug shipped
# unnoticed: at REALISTIC credit levels the old uniform `period_minutes_left /
# affordable_polls` term always dominated `max(...)`, so the dense window was
# dead code. These tests pin the behaviour at budgets the collector actually
# runs at.


def test_dense_stays_tighter_than_sparse_under_a_tight_budget():
    """The old uniform pacer flattened dense and sparse to the SAME interval
    whenever the budget term dominated. Scarcity must stretch the cadence, not
    erase the distinction between 'hours before kickoff' and 'midweek'.
    """
    kickoff = NOW + timedelta(hours=10)
    dense = _decide(upcoming_kickoffs=[kickoff], remaining_credits=100)
    sparse = _decide(upcoming_kickoffs=[NOW + timedelta(hours=96)], remaining_credits=100)
    assert dense.effective_interval_minutes < sparse.effective_interval_minutes


def test_free_key_week_one_regression():
    """The exact live state on 2026-09-08: 206 credits on the free key, 6 per
    poll, Week 1 opener ~34h out (inside the 48h dense window), period ending
    2026-09-13. The old code returned a 3.4-HOUR interval here -- coarser than
    steam detection's 1-hour window (`src/backtest/steam.py`), which is why the
    live steam scan had never fired on a 2026 game. The kickoff-weighted
    allocation must do materially better than that.
    """
    now = datetime(2026, 9, 8, 14, 0, tzinfo=UTC)
    decision = decide_poll(
        now=now,
        upcoming_kickoffs=[
            datetime(2026, 9, 10, 0, 20, tzinfo=UTC),
            datetime(2026, 9, 11, 0, 35, tzinfo=UTC),
            datetime(2026, 9, 13, 17, 0, tzinfo=UTC),
        ],
        remaining_credits=206,
        period_end=datetime(2026, 9, 13, 0, 0, tzinfo=UTC),
        last_poll_time=None,
        **{**_DEFAULTS, "full_cost": 6, "reduced_cost": 4},
    )
    assert decision.effective_interval_minutes < 3.4 * 60


def test_paid_key_affords_the_true_dense_cadence():
    """With the paid key's recurring 100K pool, `scale` collapses to 1.0 and the
    collector polls at exactly `dense_interval_minutes` inside the window -- the
    whole point of moving the mainline collector onto it.
    """
    now = datetime(2026, 9, 8, 14, 0, tzinfo=UTC)
    kickoffs = [now + timedelta(hours=h) for h in (34, 58, 75, 99, 123)]
    decision = decide_poll(
        now=now,
        upcoming_kickoffs=kickoffs,
        remaining_credits=97_790,
        period_end=datetime(2026, 10, 1, 0, 0, tzinfo=UTC),
        last_poll_time=None,
        **{**_DEFAULTS, "full_cost": 6, "reduced_cost": 4},
    )
    assert decision.effective_interval_minutes == 30.0
    assert decision.should_poll is True


def test_overlapping_dense_windows_are_unioned_not_summed():
    """Thu/Sun/Mon kickoffs with 48h windows overlap heavily. Summing them would
    claim more dense minutes than the period contains, inflating demand and
    throttling the collector for no reason.
    """
    from src.collect.budget import _dense_minutes_remaining

    period_end = NOW + timedelta(days=5)
    clustered = _dense_minutes_remaining(
        NOW, period_end, [NOW + timedelta(hours=h) for h in (10, 11, 12)], 48.0
    )
    single = _dense_minutes_remaining(NOW, period_end, [NOW + timedelta(hours=12)], 48.0)
    # Three kickoffs an hour apart cover the same span as the latest one alone.
    assert clustered == single
    # And never more wall-clock time than the period actually has left.
    assert clustered <= (period_end - NOW).total_seconds() / 60.0


def test_dense_minutes_ignores_kickoffs_beyond_the_period_end():
    from src.collect.budget import _dense_minutes_remaining

    period_end = NOW + timedelta(hours=2)
    assert _dense_minutes_remaining(NOW, period_end, [NOW + timedelta(hours=40)], 48.0) == 120.0


def test_current_period_end_calendar_month_refills_on_the_first():
    """The paid key refills at 00:00 UTC on the 1st -- confirmed from the
    2026-08-31 -> 2026-09-01 balance jump in logs/props.err.log.
    """
    end = current_period_end(
        datetime(2026, 9, 8, 14, 0, tzinfo=UTC), date(2026, 8, 14), mode="calendar_month"
    )
    assert end == datetime(2026, 10, 1, 0, 0, tzinfo=UTC)


def test_current_period_end_calendar_month_rolls_over_the_year():
    end = current_period_end(
        datetime(2026, 12, 20, 0, 0, tzinfo=UTC), date(2026, 8, 14), mode="calendar_month"
    )
    assert end == datetime(2027, 1, 1, 0, 0, tzinfo=UTC)


def test_current_period_end_defaults_to_rolling_mode():
    """Omitting `mode` must not silently change the free key's pacing."""
    now = datetime(2026, 9, 8, tzinfo=UTC)
    assert current_period_end(now, date(2026, 8, 14)) == current_period_end(
        now, date(2026, 8, 14), 30, "rolling"
    )


# --- key-change guard (2026-09-08) -------------------------------------------


def test_state_for_key_drops_a_balance_cached_on_a_different_key():
    """Switching the mainline collector free -> paid left `remaining_credits=206`
    on disk. Trusting it would stall the first poll for ~15h, and since polling
    is the ONLY way to learn the real balance, it would never self-correct.
    """
    from src.collect.budget import CollectorState, key_fingerprint, state_for_key

    state = CollectorState(
        last_poll_time=NOW,
        remaining_credits=206,
        period_anchor=date(2026, 8, 14),
        api_key_fingerprint=key_fingerprint("free-key"),
    )
    fresh = state_for_key(state, "paid-key")
    assert fresh.remaining_credits is None
    assert fresh.api_key_fingerprint == key_fingerprint("paid-key")
    # Everything else survives -- only the balance is key-specific.
    assert fresh.last_poll_time == NOW
    assert fresh.period_anchor == date(2026, 8, 14)


def test_state_for_key_keeps_the_balance_on_the_same_key():
    from src.collect.budget import CollectorState, key_fingerprint, state_for_key

    state = CollectorState(
        last_poll_time=NOW,
        remaining_credits=206,
        period_anchor=date(2026, 8, 14),
        api_key_fingerprint=key_fingerprint("free-key"),
    )
    assert state_for_key(state, "free-key").remaining_credits == 206


def test_state_for_key_adopts_a_legacy_file_without_burning_a_poll():
    """State written before fingerprints exist carries None. Treating that as a
    mismatch would throw away a valid balance on every upgrade.
    """
    from src.collect.budget import CollectorState, key_fingerprint, state_for_key

    legacy = CollectorState(
        last_poll_time=NOW, remaining_credits=206, period_anchor=date(2026, 8, 14)
    )
    adopted = state_for_key(legacy, "free-key")
    assert adopted.remaining_credits == 206
    assert adopted.api_key_fingerprint == key_fingerprint("free-key")


def test_key_fingerprint_never_leaks_the_key():
    from src.collect.budget import key_fingerprint

    secret = "super-secret-api-key"
    fp = key_fingerprint(secret)
    assert secret not in fp
    assert len(fp) == 12
    assert fp != key_fingerprint(secret + "x")


def test_dropped_balance_bootstraps_into_an_immediate_poll():
    """The point of dropping the balance: `decide_poll`'s bootstrap branch polls
    right away and relearns the quota from the response header.
    """
    decision = _decide(remaining_credits=None, last_poll_time=None)
    assert decision.should_poll is True
    assert decision.reason == "ok"


def test_state_roundtrip_preserves_the_fingerprint(tmp_path):
    from src.collect.budget import (
        CollectorState,
        key_fingerprint,
        load_state,
        save_state,
    )

    path = tmp_path / "collect_state.json"
    state = CollectorState(
        last_poll_time=NOW,
        remaining_credits=500,
        period_anchor=date(2026, 9, 1),
        api_key_fingerprint=key_fingerprint("paid-key"),
    )
    save_state(path, state)
    assert load_state(path).api_key_fingerprint == key_fingerprint("paid-key")
