import math

import numpy as np
import pytest
from scipy.stats import norm

from src.model.evaluate import brier_score, log_loss, power_analysis, reliability_curve


def test_brier_score_hand_computed():
    p = [0.9, 0.1, 0.5]
    y = [1, 0, 1]
    # (0.9-1)^2=0.01, (0.1-0)^2=0.01, (0.5-1)^2=0.25 -> mean 0.09
    assert brier_score(p, y) == pytest.approx(0.09)


def test_brier_score_perfect_predictions_are_zero():
    assert brier_score([1.0, 0.0, 1.0], [1, 0, 1]) == pytest.approx(0.0)


def test_brier_score_rejects_mismatched_shapes():
    with pytest.raises(ValueError):
        brier_score([0.5, 0.5], [1])


def test_log_loss_hand_computed():
    p = [0.9, 0.1, 0.5]
    y = [1, 0, 1]
    expected = -np.mean([math.log(0.9), math.log(0.9), math.log(0.5)])
    assert log_loss(p, y) == pytest.approx(expected)


def test_log_loss_clips_extreme_probabilities_instead_of_blowing_up():
    # p=0 with y=1 would be log(0) = -inf without clipping
    value = log_loss([0.0], [1.0])
    assert math.isfinite(value)
    assert value > 0


def test_log_loss_rejects_mismatched_shapes():
    with pytest.raises(ValueError):
        log_loss([0.5], [1, 0])


def test_reliability_curve_bins_single_observations_correctly():
    p = [0.05, 0.15, 0.95]
    y = [0, 1, 1]
    table = reliability_curve(p, y, n_bins=10)

    assert len(table) == 10
    bin0 = table[table["bin"] == 0].iloc[0]
    assert bin0["predicted"] == pytest.approx(0.05)
    assert bin0["observed"] == pytest.approx(0.0)
    assert bin0["count"] == 1

    bin9 = table[table["bin"] == 9].iloc[0]
    assert bin9["predicted"] == pytest.approx(0.95)
    assert bin9["observed"] == pytest.approx(1.0)
    assert bin9["count"] == 1


def test_reliability_curve_boundary_value_one_lands_in_last_bin():
    table = reliability_curve([1.0], [1.0], n_bins=10)
    bin9 = table[table["bin"] == 9].iloc[0]
    assert bin9["count"] == 1


def test_reliability_curve_empty_bins_kept_with_nan_not_dropped():
    table = reliability_curve([0.05], [0.0], n_bins=10)
    assert len(table) == 10
    empty_bin = table[table["bin"] == 5].iloc[0]
    assert empty_bin["count"] == 0
    assert math.isnan(empty_bin["predicted"])


def test_reliability_curve_averages_multiple_observations_in_same_bin():
    table = reliability_curve([0.51, 0.59], [1, 0], n_bins=10)
    bin5 = table[table["bin"] == 5].iloc[0]
    assert bin5["predicted"] == pytest.approx((0.51 + 0.59) / 2)
    assert bin5["observed"] == pytest.approx(0.5)
    assert bin5["count"] == 2


def test_reliability_curve_requires_at_least_one_observation():
    with pytest.raises(ValueError):
        reliability_curve([], [])


def test_power_analysis_hand_computed():
    z_alpha = norm.ppf(1 - 0.05 / 2)
    z_power = norm.ppf(0.8)
    expected_n = math.ceil(((z_alpha + z_power) * 1.0 / 1.0) ** 2)
    assert power_analysis(effect_size_clv=1.0, variance=1.0) == expected_n


def test_power_analysis_smaller_effect_needs_more_bets():
    n_large_effect = power_analysis(effect_size_clv=0.05, variance=1.0)
    n_small_effect = power_analysis(effect_size_clv=0.01, variance=1.0)
    assert n_small_effect > n_large_effect
    # n scales as 1/effect^2 -> a 5x smaller effect needs ~25x the sample
    assert n_small_effect / n_large_effect == pytest.approx(25, rel=0.05)


def test_power_analysis_matches_blueprint_claim_small_edges_need_thousands():
    # A small CLV edge (mean 0.5%) against realistic bet-to-bet noise (CLV
    # std ~10%) requires a sample size in the thousands -- this is the
    # exact honesty claim blueprint B.5 makes about one NFL season (a few
    # hundred bets at most) not being able to confirm a small true edge.
    n = power_analysis(effect_size_clv=0.005, variance=0.10**2)
    assert n > 1000


def test_power_analysis_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        power_analysis(effect_size_clv=0.0, variance=1.0)
    with pytest.raises(ValueError):
        power_analysis(effect_size_clv=0.05, variance=0.0)
    with pytest.raises(ValueError):
        power_analysis(effect_size_clv=0.05, variance=1.0, alpha=1.5)
    with pytest.raises(ValueError):
        power_analysis(effect_size_clv=0.05, variance=1.0, power=1.0)
