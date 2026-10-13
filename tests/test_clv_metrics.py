import pytest

from src.clv.metrics import (
    beat_rate,
    bootstrap_ci,
    clustered_bootstrap,
    clv_price,
    clv_probability,
)


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


def test_clustered_bootstrap_is_wider_than_per_bet_when_legs_share_a_game():
    """20 games x 10 legs, each game's legs nearly identical: the per-bet CI
    sees 200 confirmations, the honest one sees 20."""
    import numpy as np

    rng = np.random.default_rng(1)
    game_effect = rng.normal(0.0, 0.03, size=20)
    values = np.repeat(game_effect, 10) + rng.normal(0.0, 0.001, size=200)
    games = np.repeat(np.arange(20), 10)

    naive_lo, naive_hi = bootstrap_ci(values, random_state=0)
    clustered = clustered_bootstrap(values, games, random_state=0)

    assert clustered["n_clusters"] == 20
    assert (clustered["ci_hi"] - clustered["ci_lo"]) > 2.5 * (naive_hi - naive_lo)


def test_clustered_bootstrap_matches_per_bet_when_each_game_has_one_leg():
    import numpy as np

    values = np.random.default_rng(2).normal(0.01, 0.02, size=200)
    naive_lo, naive_hi = bootstrap_ci(values, random_state=0)
    clustered = clustered_bootstrap(values, np.arange(200), random_state=0)
    assert clustered["ci_hi"] - clustered["ci_lo"] == pytest.approx(naive_hi - naive_lo, rel=0.1)


def test_clustered_bootstrap_p_value_tracks_the_sign_of_the_edge():
    import numpy as np

    rng = np.random.default_rng(3)
    games = np.repeat(np.arange(40), 3)
    strong = clustered_bootstrap(rng.normal(0.02, 0.01, size=120), games)
    null = clustered_bootstrap(rng.normal(0.0, 0.01, size=120), games)
    assert strong["p_one_sided"] < 0.01
    assert 0.05 < null["p_one_sided"] < 0.95


def test_clustered_bootstrap_rejects_a_single_cluster_and_mismatched_lengths():
    with pytest.raises(ValueError):
        clustered_bootstrap([0.01, 0.02], ["g1", "g1"])
    with pytest.raises(ValueError):
        clustered_bootstrap([0.01, 0.02], ["g1"])
