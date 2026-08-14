"""Model evaluation (blueprint Part B.5).

"This section is where you prove you are honest, not lucky." Calibration
metrics measure whether predicted probabilities mean what they say;
power_analysis exists to be reported BEFORE any results, so the results
section is read in the context of what this sample size can and cannot
actually detect -- not after, as a excuse for a null finding.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
import pandas as pd
from scipy.stats import norm

_LOG_LOSS_EPS = 1e-15


def brier_score(p: Sequence[float], y: Sequence[float]) -> float:
    """mean((p - y)^2). Lower is better."""
    p_arr = np.asarray(p, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    _validate_same_shape(p_arr, y_arr)
    return float(np.mean((p_arr - y_arr) ** 2))


def log_loss(p: Sequence[float], y: Sequence[float]) -> float:
    """-mean(y*log(p) + (1-y)*log(1-p)). p is clipped away from exactly 0/1
    so a single confident-and-wrong prediction doesn't blow up to infinity.
    """
    p_arr = np.asarray(p, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    _validate_same_shape(p_arr, y_arr)
    p_clipped = np.clip(p_arr, _LOG_LOSS_EPS, 1 - _LOG_LOSS_EPS)
    return float(-np.mean(y_arr * np.log(p_clipped) + (1 - y_arr) * np.log(1 - p_clipped)))


def reliability_curve(p: Sequence[float], y: Sequence[float], n_bins: int = 10) -> pd.DataFrame:
    """Bin predicted probabilities into n_bins equal-width [0, 1] bins and
    compare mean predicted vs. mean observed frequency per bin. A well
    calibrated model plots close to the diagonal predicted == observed.

    Empty bins are kept (not dropped) with NaN predicted/observed and
    count 0, so a sparse region of the probability space is visible in the
    output rather than silently missing.
    """
    p_arr = np.asarray(p, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    _validate_same_shape(p_arr, y_arr)
    if p_arr.size == 0:
        raise ValueError("reliability_curve requires at least one observation")
    if n_bins < 1:
        raise ValueError("n_bins must be >= 1")

    edges = np.linspace(0, 1, n_bins + 1)
    bin_index = np.clip(np.digitize(p_arr, edges[1:-1], right=True), 0, n_bins - 1)

    df = pd.DataFrame({"bin": bin_index, "p": p_arr, "y": y_arr})
    grouped = df.groupby("bin").agg(predicted=("p", "mean"), observed=("y", "mean"), count=("p", "size"))
    grouped = grouped.reindex(range(n_bins))
    grouped["count"] = grouped["count"].fillna(0).astype(int)
    grouped["bin_lower"] = edges[:-1]
    grouped["bin_upper"] = edges[1:]
    return grouped.reset_index()[["bin", "bin_lower", "bin_upper", "predicted", "observed", "count"]]


def power_analysis(effect_size_clv: float, variance: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Required sample size (one-sample z-test) to detect a mean CLV of
    `effect_size_clv` against noise of `variance`, at two-sided
    significance `alpha` and statistical `power`.

    n = ((z_{alpha/2} + z_{power}) * sigma / effect_size)^2

    Report this BEFORE results: a small true edge needs a sample size that
    one NFL season (a few hundred bets at most) usually cannot reach.
    """
    if effect_size_clv == 0:
        raise ValueError("effect_size_clv must be non-zero")
    if variance <= 0:
        raise ValueError("variance must be positive")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be in (0, 1)")
    if not 0 < power < 1:
        raise ValueError("power must be in (0, 1)")

    sigma = math.sqrt(variance)
    z_alpha = norm.ppf(1 - alpha / 2)
    z_power = norm.ppf(power)
    n = ((z_alpha + z_power) * sigma / abs(effect_size_clv)) ** 2
    return math.ceil(n)


def _validate_same_shape(p_arr: np.ndarray, y_arr: np.ndarray) -> None:
    if p_arr.shape != y_arr.shape:
        raise ValueError(f"p and y must be the same shape, got {p_arr.shape} and {y_arr.shape}")
