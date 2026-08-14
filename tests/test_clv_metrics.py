import pytest

from src.clv.metrics import beat_rate, bootstrap_ci, clv_price, clv_probability


def test_clv_probability_hand_computed():
    assert clv_probability(p_entry_fair=0.50, p_close_fair=0.55) == pytest.approx(0.05)
    assert clv_probability(p_entry_fair=0.55, p_close_fair=0.50) == pytest.approx(-0.05)


def test_clv_price_hand_computed():
    # entry at 2.0, close shortens to 1.9 -> you beat the close
    assert clv_price(d_entry=2.0, d_close=1.9) == pytest.approx(2.0 / 1.9 - 1)
    assert clv_price(d_entry=2.0, d_close=1.9) > 0
    # entry at 1.9, close drifts to 2.0 -> you got the worse price
    assert clv_price(d_entry=1.9, d_close=2.0) < 0


def test_clv_price_zero_when_entry_equals_close():
    assert clv_price(d_entry=1.91, d_close=1.91) == pytest.approx(0.0)


def test_beat_rate_hand_computed():
    clv_series = [0.01, -0.02, 0.03, -0.01, 0.05]
    assert beat_rate(clv_series) == pytest.approx(3 / 5)


def test_beat_rate_all_positive_and_all_negative():
    assert beat_rate([0.01, 0.02, 0.03]) == pytest.approx(1.0)
    assert beat_rate([-0.01, -0.02]) == pytest.approx(0.0)


def test_beat_rate_rejects_empty_series():
    with pytest.raises(ValueError):
        beat_rate([])


def test_bootstrap_ci_brackets_the_sample_mean():
    # A percentile bootstrap CI must be centered on (and contain) the
    # observed sample mean it's resampling from -- that's true regardless
    # of what the unknown "true" generating mean happens to be.
    import numpy as np

    rng = np.random.default_rng(7)
    clv_series = 0.02 + rng.normal(scale=0.01, size=500)
    sample_mean = clv_series.mean()
    low, high = bootstrap_ci(clv_series, n_resamples=2000, ci=0.95, random_state=42)
    assert low < high
    assert low < sample_mean < high


def test_bootstrap_ci_collapses_tightly_for_constant_series():
    low, high = bootstrap_ci([0.03] * 100, n_resamples=1000, random_state=1)
    assert low == pytest.approx(0.03, abs=1e-9)
    assert high == pytest.approx(0.03, abs=1e-9)


def test_bootstrap_ci_is_reproducible_with_same_random_state():
    series = [0.01, -0.02, 0.03, 0.04, -0.01, 0.02, 0.01]
    a = bootstrap_ci(series, n_resamples=500, random_state=123)
    b = bootstrap_ci(series, n_resamples=500, random_state=123)
    assert a == b


def test_bootstrap_ci_requires_at_least_two_observations():
    with pytest.raises(ValueError):
        bootstrap_ci([0.01])


def test_bootstrap_ci_rejects_invalid_confidence_level():
    with pytest.raises(ValueError):
        bootstrap_ci([0.01, 0.02, 0.03], ci=1.5)
