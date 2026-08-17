"""Non-stationarity / drift monitor (blueprint Part E, "the genuinely hard
part"). Books patch inefficiencies and edges decay; the question this
module exists to answer is "how do you know your edge died before your
bankroll tells you?"

Three independent signals, matching the blueprint directly:
- `rolling_mean_clv`: is mean CLV over the trailing window trending down?
- `cusum`: has CLV shifted away from its established baseline in a
  sustained way (not just noise)? Classic Page (1954) CUSUM.
- `rolling_calibration_drift`: has the model's Brier score gotten worse
  than its original (train/calib/test split) reference?

This is built and tested against synthetic series now, ahead of live data,
the same way src/clv/metrics.py and src/backtest/engine.py were -- there is
no live CLV time series yet (collection started 2026-08-14), so this
module's job today is to be correct and ready, not to have already fired
on anything real.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd


def rolling_mean_clv(clv_series: Sequence[float], window: int) -> np.ndarray:
    """Trailing rolling mean CLV, one value per bet. Uses whatever history
    exists so far for the first `window - 1` bets (min_periods=1) -- an
    honestly-partial number from bet 1 beats staying silent until the
    window fills.
    """
    if window < 1:
        raise ValueError("window must be >= 1")
    values = pd.Series(clv_series, dtype=float)
    return values.rolling(window, min_periods=1).mean().to_numpy()


def cusum(
    x: Sequence[float], target: float, threshold: float, drift: float = 0.0
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Two-sided CUSUM change-point detector.

    `upper` accumulates evidence of a sustained shift *above* `target`;
    `lower`, of a shift *below* it. `drift` (the allowance/slack) absorbs
    small, expected noise so it doesn't accumulate into a false alarm --
    set it too low and a random walk trips the detector eventually, too
    high and a real shift never crosses `threshold`.

    Returns `(upper, lower, flagged)`: `upper >= 0` and `lower <= 0` at
    every index; `flagged` is a bool array, True wherever `upper >
    threshold` or `lower < -threshold`. CUSUM is *not* reset to 0 after a
    flag -- the caller decides whether a flag means "stop watching" (the
    strategy is paused) or "reset and keep watching" (call `cusum` again
    on the remaining series with a fresh target).
    """
    if threshold <= 0:
        raise ValueError("threshold must be positive")
    if drift < 0:
        raise ValueError("drift must be non-negative")

    values = np.asarray(x, dtype=float)
    upper = np.zeros(values.size)
    lower = np.zeros(values.size)
    running_upper = 0.0
    running_lower = 0.0
    for i, v in enumerate(values):
        running_upper = max(0.0, running_upper + (v - target - drift))
        running_lower = min(0.0, running_lower + (v - target + drift))
        upper[i] = running_upper
        lower[i] = running_lower

    flagged = (upper > threshold) | (lower < -threshold)
    return upper, lower, flagged


def rolling_calibration_drift(p: Sequence[float], y: Sequence[float], window: int, reference_brier: float) -> np.ndarray:
    """Rolling Brier score over the trailing `window` predictions, minus a
    `reference_brier` established during a known-good period (e.g. the
    model's Brier score on its original holdout -- src/model/train.py's
    time_based_split test split). Positive means calibration has gotten
    worse than the reference; this is what "calibration drifts" (blueprint
    Part E) means operationally -- a specific number that can cross a
    threshold, not a vague impression.
    """
    p_arr = np.asarray(p, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    if p_arr.shape != y_arr.shape:
        raise ValueError(f"p and y must be the same shape, got {p_arr.shape} and {y_arr.shape}")
    if window < 1:
        raise ValueError("window must be >= 1")

    sq_err = pd.Series((p_arr - y_arr) ** 2)
    rolling_brier = sq_err.rolling(window, min_periods=1).mean().to_numpy()
    return rolling_brier - reference_brier


def first_flag_index(flagged: Sequence[bool]) -> int | None:
    """Index of the first True in `flagged`, or None if it never fires."""
    indices = np.flatnonzero(np.asarray(flagged, dtype=bool))
    return int(indices[0]) if indices.size else None
