"""Calibration layer (blueprint Part E): Platt scaling / isotonic regression
on top of the raw logistic model, plus the honest comparison against both
the uncalibrated model and the market baseline.

"Calibrated probabilities matter more than raw accuracy here" -- a raw
logistic regression's predict_proba output isn't guaranteed to be
calibrated. This wraps a *frozen* (already-fit) model with sklearn's
CalibratedClassifierCV, fit on a held-out calibration split the base model
never trained on -- `src/model/train.py::time_based_split`'s three-way
split exists for exactly this reason, so the calibration mapping isn't
just correcting for the base model's own training-set overfit.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.pipeline import Pipeline

from src.model.evaluate import brier_score, log_loss, reliability_curve
from src.model.train import FEATURE_COLUMNS


def fit_calibrated_model(base_model: Pipeline, calib_df: pd.DataFrame, method: str = "isotonic") -> CalibratedClassifierCV:
    """`method`: "isotonic" (non-parametric, flexible, can overfit a small
    calibration split) or "sigmoid" (Platt scaling, parametric, safer with
    less calibration data).

    Wrapping `base_model` in FrozenEstimator stops CalibratedClassifierCV
    from refitting it -- but it still runs its own internal 5-fold
    stratified CV over `calib_df` to get unbiased predictions for the
    calibration mapping itself (`ensemble="auto"` resolves to `False` for a
    frozen estimator, routing through `cross_val_predict`). That's a
    separate concern from the base model's train/calib/test split; it just
    means `calib_df` needs at least ~5 examples of each class.
    """
    calibrated = CalibratedClassifierCV(FrozenEstimator(base_model), method=method)
    calibrated.fit(calib_df[FEATURE_COLUMNS], calib_df["home_win"])
    return calibrated


def predict_calibrated_proba(calibrated_model: CalibratedClassifierCV, df: pd.DataFrame):
    return calibrated_model.predict_proba(df[FEATURE_COLUMNS])[:, 1]


def fit_residual_std(model, calib_df: pd.DataFrame, feature_columns: Sequence[str], target_col: str) -> float:
    """Std of (actual - predicted) on `calib_df` -- a regression analogue
    of `fit_calibrated_model`'s split discipline: residuals measured on the
    same rows the model was fit on are optimistically small (the model fit
    those exact points), which would understate real uncertainty and
    oversharpen `predict_over_proba` below. Always pass the calibration
    split here, never `train_df`.
    """
    predicted = model.predict(calib_df[feature_columns])
    return float(np.std(calib_df[target_col].to_numpy() - predicted, ddof=1))


def predict_over_proba(
    model, df: pd.DataFrame, feature_columns: Sequence[str], line_col: str, residual_std: float
) -> np.ndarray:
    """P(actual > line) under Normal(predicted_mean, residual_std) -- a v1
    simplification, stated plainly: NFL margins/totals aren't guaranteed
    Gaussian (blowouts fat-tail the distribution). `line_col` is generic
    ("spread_line" or "total_line") so this one function serves both the
    margin and total models -- they differ only in which column and which
    fitted model/residual_std are passed in, not in the conversion logic
    itself. Compare against `predict_over_proba_empirical` before trusting
    a result -- if they diverge, the Gaussian assumption is the reason, not
    the underlying model.
    """
    predicted_mean = model.predict(df[feature_columns])
    return norm.sf(df[line_col].to_numpy(), loc=predicted_mean, scale=residual_std)


def predict_over_proba_empirical(
    model, calib_residuals: np.ndarray, df: pd.DataFrame, feature_columns: Sequence[str], line_col: str
) -> np.ndarray:
    """Same question as `predict_over_proba` -- P(actual > line) -- but
    without assuming the residual distribution is Normal: resamples the
    empirical calibration-split residuals around each test-row prediction
    instead of a fitted Gaussian. `calib_residuals` = `calib_df[target_col]
    - model.predict(calib_df[feature_columns])`, computed by the caller
    (same residuals `fit_residual_std` summarizes into a single number;
    this uses the full distribution instead of just its std).
    """
    predicted_mean = model.predict(df[feature_columns])
    lines = df[line_col].to_numpy()
    return np.mean(predicted_mean[:, None] + calib_residuals[None, :] > lines[:, None], axis=1)


def compare_to_baseline(predictions: dict[str, pd.Series | list[float]], y: pd.Series) -> pd.DataFrame:
    """`predictions` maps a label (e.g. "raw_model", "calibrated_model",
    "market_baseline") to predicted probabilities on the same rows as `y`.
    Returns one row per label with Brier score and log loss -- the
    blueprint's calibration-quality metrics (paper Sec 4.7), not accuracy,
    since a well-calibrated-but-unimpressive model beats a sharp-looking
    but overconfident one for this project's purposes.
    """
    rows = [{"model": name, "brier": brier_score(p, y), "log_loss": log_loss(p, y)} for name, p in predictions.items()]
    return pd.DataFrame(rows).sort_values("brier").reset_index(drop=True)


if __name__ == "__main__":
    from src.model.train import (
        build_training_frame,
        fit_win_probability_model,
        predict_home_win_proba,
        time_based_split,
    )

    pbp = pd.read_parquet("data/static/pbp_2015_2024.parquet")
    schedule = pd.read_parquet("data/static/schedules_2015_2024.parquet")
    df = build_training_frame(pbp, schedule)

    train_df, calib_df, test_df = time_based_split(
        df, train_seasons=range(2015, 2022), calib_seasons=[2022], test_seasons=[2023, 2024]
    )
    print(f"train={len(train_df)} calib={len(calib_df)} test={len(test_df)} games")

    raw_model = fit_win_probability_model(train_df)
    calibrated_model = fit_calibrated_model(raw_model, calib_df, method="isotonic")

    report = compare_to_baseline(
        {
            "market_baseline": test_df["market_prob_home"],
            "raw_logistic": predict_home_win_proba(raw_model, test_df),
            "calibrated_logistic": predict_calibrated_proba(calibrated_model, test_df),
        },
        test_df["home_win"],
    )
    print(report.to_string(index=False))

    print("\nreliability curve, calibrated model:")
    print(
        reliability_curve(predict_calibrated_proba(calibrated_model, test_df), test_df["home_win"].to_numpy()).to_string(
            index=False
        )
    )
