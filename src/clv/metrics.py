"""Closing Line Value metrics (blueprint Part B.3).

CLV is measured two ways -- probability space and price space -- and always
reported alongside a bootstrap confidence interval on the mean, per the
blueprint's "honest math" framing: a single point-estimate CLV number
without an interval is exactly the kind of unearned confidence this project
is built to avoid.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np


def clv_probability(p_entry_fair: float, p_close_fair: float) -> float:
    """How far the fair market moved toward your side after you bet.

    Positive means the closing fair probability for your side rose above
    the fair probability when you entered -- you beat the close.
    """
    return p_close_fair - p_entry_fair


def clv_price(d_entry: float, d_close: float) -> float:
    """Whether the decimal price you took beats the closing price for the
    same side. Positive means your price was better than the close.
    """
    return (d_entry / d_close) - 1


def beat_rate(clv_series: Sequence[float]) -> float:
    """Fraction of bets with positive CLV."""
    values = np.asarray(clv_series, dtype=float)
    if values.size == 0:
        raise ValueError("beat_rate requires at least one CLV observation")
    return float((values > 0).mean())


def bootstrap_ci(
    clv_series: Sequence[float],
    n_resamples: int = 10000,
    ci: float = 0.95,
    random_state: int | None = None,
) -> tuple[float, float]:
    """Percentile bootstrap CI on mean CLV.

    Resamples clv_series with replacement n_resamples times, takes the mean
    of each resample, and returns the (100*(1-ci)/2, 100*(1+ci)/2)
    percentiles of that distribution of means.
    """
    values = np.asarray(clv_series, dtype=float)
    if values.size < 2:
        raise ValueError("bootstrap_ci requires at least two CLV observations")
    if not 0 < ci < 1:
        raise ValueError("ci must be in (0, 1)")

    rng = np.random.default_rng(random_state)
    n = values.size
    resample_indices = rng.integers(0, n, size=(n_resamples, n))
    resample_means = values[resample_indices].mean(axis=1)

    alpha = 1 - ci
    lower = float(np.percentile(resample_means, 100 * alpha / 2))
    upper = float(np.percentile(resample_means, 100 * (1 - alpha / 2)))
    return lower, upper
