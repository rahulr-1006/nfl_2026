import numpy as np
import pytest

from src.drift.monitor import (
    cusum,
    first_flag_index,
    rolling_calibration_drift,
    rolling_mean_clv,
)


def test_rolling_mean_clv_uses_available_history_before_window_fills():
    result = rolling_mean_clv([1, 2, 3, 4, 5], window=3)
    # window=3, min_periods=1: [mean(1), mean(1,2), mean(1,2,3), mean(2,3,4), mean(3,4,5)]
    assert result == pytest.approx([1, 1.5, 2, 3, 4])


def test_rolling_mean_clv_rejects_non_positive_window():
    with pytest.raises(ValueError):
        rolling_mean_clv([1, 2, 3], window=0)


def test_cusum_flags_a_sustained_shift_above_target():
    # Five bets at the target (0), then ten bets shifted up by 1.0. With
    # drift=0.1, each in-band step contributes at most (1.0 - 0.1) = 0.9
    # to the running upper statistic: 0, 0.9, 1.8, 2.7, ... crossing
    # threshold=2.0 on the 3rd shifted bet (index 7, 0-indexed).
    x = [0.0] * 5 + [1.0] * 10
    upper, lower, flagged = cusum(x, target=0.0, threshold=2.0, drift=0.1)

    assert upper[:5] == pytest.approx([0.0] * 5)
    assert lower == pytest.approx([0.0] * 15)  # x never dips below target, lower never leaves 0
    assert not flagged[:7].any()
    assert flagged[7:].all()
    assert first_flag_index(flagged) == 7


def test_cusum_stays_quiet_under_noise_within_the_drift_band():
    # Every step's deviation from target is +/-0.05, inside the drift=0.1
    # allowance, so both running statistics get clamped back to 0 every
    # single step and never accumulate.
    x = [0.05, -0.05] * 10
    upper, lower, flagged = cusum(x, target=0.0, threshold=1.0, drift=0.1)

    assert upper == pytest.approx(np.zeros(20))
    assert lower == pytest.approx(np.zeros(20))
    assert not flagged.any()
    assert first_flag_index(flagged) is None


def test_cusum_rejects_invalid_threshold_and_drift():
    with pytest.raises(ValueError):
        cusum([0.0, 0.1], target=0.0, threshold=0.0)
    with pytest.raises(ValueError):
        cusum([0.0, 0.1], target=0.0, threshold=1.0, drift=-0.1)


def test_rolling_calibration_drift_matches_hand_computed_brier():
    p = [0.5, 0.5, 0.9, 0.9]
    y = [1, 0, 1, 0]
    # squared errors: 0.25, 0.25, 0.01, 0.81
    # window=2, min_periods=1 rolling mean: 0.25, 0.25, 0.13, 0.41
    result = rolling_calibration_drift(p, y, window=2, reference_brier=0.25)
    assert result == pytest.approx([0.0, 0.0, -0.12, 0.16])


def test_rolling_calibration_drift_rejects_shape_mismatch():
    with pytest.raises(ValueError):
        rolling_calibration_drift([0.5, 0.5], [1], window=1, reference_brier=0.25)


def test_first_flag_index_returns_none_when_never_flagged():
    assert first_flag_index([False, False, False]) is None
    assert first_flag_index([False, False, True, True]) == 2
