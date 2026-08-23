from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from src.backtest.synthetic_market import (
    simulate_market,
    simulate_true_probability_path,
)
from src.devig.convert import american_to_implied_prob
from src.store.schema import Market, Side

KICKOFF_START = datetime(2099, 9, 7, 17, 0, tzinfo=UTC)


# --- simulate_true_probability_path ---


def test_zero_drift_stays_centered_on_the_shrunk_opening_logit_on_average():
    # drift_strength=0 -> no deterministic pull toward p_true at all. Average
    # ending logit across many simulated paths should be close to the
    # (shrunk) opening logit, not p_true's logit.
    rng = np.random.default_rng(0)
    ends = [
        simulate_true_probability_path(0.8, n_steps=20, drift_strength=0.0, noise_scale=0.02, random_state=rng)[-1]
        for _ in range(500)
    ]
    from src.backtest.synthetic_market import _logit, _sigmoid

    expected_open = _sigmoid(0.4 * _logit(0.8))  # DEFAULT_INITIAL_SHRINKAGE=0.4
    assert np.mean(ends) == pytest.approx(expected_open, abs=0.03)


def test_full_drift_converges_close_to_p_true():
    rng = np.random.default_rng(1)
    path = simulate_true_probability_path(0.8, n_steps=50, drift_strength=1.0, noise_scale=0.01, random_state=rng)
    assert path[-1] == pytest.approx(0.8, abs=0.1)


def test_path_starts_shrunk_toward_half_not_at_p_true():
    path = simulate_true_probability_path(0.9, n_steps=10, drift_strength=0.5, noise_scale=0.0, random_state=0)
    assert 0.5 < path[0] < 0.9  # shrunk toward 0.5, not equal to p_true


def test_path_length_is_n_steps_plus_one():
    path = simulate_true_probability_path(0.6, n_steps=15, drift_strength=0.5, noise_scale=0.02, random_state=0)
    assert len(path) == 16


def test_path_stays_in_valid_probability_range():
    path = simulate_true_probability_path(0.95, n_steps=30, drift_strength=1.0, noise_scale=0.5, random_state=0)
    assert np.all(path > 0) and np.all(path < 1)


def test_rejects_p_true_out_of_range():
    with pytest.raises(ValueError):
        simulate_true_probability_path(0.0, n_steps=10, drift_strength=0.5, noise_scale=0.02)
    with pytest.raises(ValueError):
        simulate_true_probability_path(1.0, n_steps=10, drift_strength=0.5, noise_scale=0.02)


def test_jump_component_increases_path_variance():
    rng_no_jump = np.random.default_rng(7)
    rng_jump = np.random.default_rng(7)
    no_jump = simulate_true_probability_path(0.6, n_steps=40, drift_strength=0.3, noise_scale=0.01, random_state=rng_no_jump)
    with_jump = simulate_true_probability_path(
        0.6, n_steps=40, drift_strength=0.3, noise_scale=0.01, jump_rate=0.3, jump_scale=0.3, random_state=rng_jump
    )
    assert np.std(np.diff(with_jump)) > np.std(np.diff(no_jump))


# --- simulate_market ---


def test_simulate_market_produces_real_valid_odds_snapshots():
    snaps, truths = simulate_market(
        n_games=3, n_poll_steps=5, kickoff_start=KICKOFF_START, markets=(Market.MONEYLINE,), random_state=0
    )
    assert len(truths) == 3
    # 3 games x 6 poll steps x 4 books x 2 sides
    assert len(snaps) == 3 * 6 * 4 * 2
    assert all(s.market == Market.MONEYLINE for s in snaps)
    assert all(s.event_start_time.tzinfo is not None for s in snaps)


def test_simulate_market_event_ids_never_collide_with_real_seasons():
    _, truths = simulate_market(n_games=2, n_poll_steps=3, kickoff_start=KICKOFF_START, random_state=0)
    assert all(t.event_id.startswith("SYNTH_") for t in truths)


def test_simulate_market_supports_spread_and_total():
    snaps, _ = simulate_market(
        n_games=2, n_poll_steps=3, kickoff_start=KICKOFF_START,
        markets=(Market.MONEYLINE, Market.SPREAD, Market.TOTAL), random_state=0,
    )
    markets_present = {s.market for s in snaps}
    assert markets_present == {Market.MONEYLINE, Market.SPREAD, Market.TOTAL}
    spread_sides = {s.side for s in snaps if s.market == Market.SPREAD}
    assert spread_sides == {Side.HOME, Side.AWAY}
    total_sides = {s.side for s in snaps if s.market == Market.TOTAL}
    assert total_sides == {Side.OVER, Side.UNDER}


def test_each_book_quotes_independently_noisy_prices_not_identical():
    snaps, _ = simulate_market(
        n_games=1, n_poll_steps=1, kickoff_start=KICKOFF_START,
        books=("pinnacle", "draftkings", "fanduel", "betmgm"), book_noise_scale=0.2, random_state=0,
    )
    home_prices = {s.book: s.price_american for s in snaps if s.side == Side.HOME}
    assert len(set(home_prices.values())) > 1  # not all books quote the identical price


def test_vig_makes_both_sides_sum_to_more_than_one_implied_probability():
    snaps, _ = simulate_market(
        n_games=1, n_poll_steps=1, kickoff_start=KICKOFF_START, books=("pinnacle",), vig=0.05, random_state=0,
    )
    latest_time = max(s.capture_time for s in snaps)
    latest = [s for s in snaps if s.capture_time == latest_time]
    home = next(s for s in latest if s.side == Side.HOME)
    away = next(s for s in latest if s.side == Side.AWAY)
    total_implied = american_to_implied_prob(home.price_american) + american_to_implied_prob(away.price_american)
    assert total_implied > 1.0  # real vig, not a no-vig market


def test_poll_times_span_from_open_window_to_kickoff():
    poll_window = timedelta(hours=48)
    snaps, _ = simulate_market(
        n_games=1, n_poll_steps=4, kickoff_start=KICKOFF_START, poll_window=poll_window, books=("pinnacle",), random_state=0,
    )
    times = sorted({s.capture_time for s in snaps})
    assert times[0] == KICKOFF_START - poll_window
    assert times[-1] == KICKOFF_START


def test_different_games_get_independent_kickoffs():
    _, truths = simulate_market(
        n_games=3, n_poll_steps=2, kickoff_start=KICKOFF_START, kickoff_spacing=timedelta(hours=3), random_state=0
    )
    kickoffs = [t.kickoff for t in truths]
    assert kickoffs == sorted(kickoffs)
    assert len(set(kickoffs)) == 3


def test_props_only_simulation_still_returns_ground_truth():
    """Regression: truth records were previously gated on a moneyline path
    existing, so a props-only scenario silently returned zero truths and
    couldn't be validated at all.
    """
    snaps, truths = simulate_market(
        n_games=3, n_poll_steps=2, kickoff_start=KICKOFF_START,
        markets=(Market.PLAYER_PROP,), n_prop_players=2, books=("pinnacle",), random_state=0,
    )
    assert len(truths) == 3
    assert all(len(t.props) == 2 for t in truths)
    assert snaps  # and it still produced real snapshots
