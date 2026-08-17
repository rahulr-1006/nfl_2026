import numpy as np
import pandas as pd

from src.model.calibration import (
    compare_to_baseline,
    fit_calibrated_model,
    predict_calibrated_proba,
)
from src.model.train import fit_win_probability_model


def _synthetic_feature_frame(season: int, n: int = 25) -> pd.DataFrame:
    # CalibratedClassifierCV runs its own internal 5-fold stratified CV on
    # the calibration split to get unbiased calibration predictions (even
    # with a FrozenEstimator, which only skips refitting the base
    # classifier itself -- see src/model/calibration.py's docstring), so
    # each class needs at least 5 members here. home_win alternates
    # strictly rather than following the epa features, since these tests
    # exercise the calibration API's mechanics, not model signal quality
    # (that's covered in tests/test_train.py).
    rows = []
    for i in range(n):
        rows.append(
            {
                "season": season,
                "home_pre_off_epa": 0.05 * i,
                "home_pre_off_success": 0.4 + 0.001 * i,
                "home_pre_def_epa_allowed": -0.05 * i,
                "home_pre_def_success_allowed": 0.4 - 0.001 * i,
                "away_pre_off_epa": -0.05 * i,
                "away_pre_off_success": 0.4 - 0.001 * i,
                "away_pre_def_epa_allowed": 0.05 * i,
                "away_pre_def_success_allowed": 0.4 + 0.001 * i,
                "home_rest": 7,
                "away_rest": 7,
                "div_game": i % 2,
                "home_win": i % 2,
            }
        )
    return pd.DataFrame(rows)


def test_fit_calibrated_model_outputs_valid_probabilities():
    train_df = _synthetic_feature_frame(2020)
    calib_df = _synthetic_feature_frame(2021)
    test_df = _synthetic_feature_frame(2022)

    base_model = fit_win_probability_model(train_df)
    calibrated = fit_calibrated_model(base_model, calib_df, method="sigmoid")
    proba = predict_calibrated_proba(calibrated, test_df)

    assert proba.shape == (len(test_df),)
    assert np.all((proba >= 0) & (proba <= 1))


def test_fit_calibrated_model_does_not_refit_the_base_model():
    """CalibratedClassifierCV wraps a FrozenEstimator specifically so the
    calibration step can't silently retrain the base model on the
    calibration split -- that would defeat the point of the three-way
    train/calib/test split in src/model/train.py::time_based_split.
    """
    train_df = _synthetic_feature_frame(2020)
    calib_df = _synthetic_feature_frame(2021)

    base_model = fit_win_probability_model(train_df)
    coef_before = base_model.named_steps["logit"].coef_.copy()

    fit_calibrated_model(base_model, calib_df, method="sigmoid")

    coef_after = base_model.named_steps["logit"].coef_
    assert np.array_equal(coef_before, coef_after)


def test_compare_to_baseline_ranks_by_brier_score():
    y = pd.Series([1, 0, 1, 0])
    predictions = {
        "perfect": [1.0, 0.0, 1.0, 0.0],
        "coin_flip": [0.5, 0.5, 0.5, 0.5],
        "always_wrong": [0.0, 1.0, 0.0, 1.0],
    }
    report = compare_to_baseline(predictions, y)
    assert list(report["model"]) == ["perfect", "coin_flip", "always_wrong"]
    assert report.iloc[0]["brier"] == 0.0
