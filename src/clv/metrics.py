"""Closing Line Value metrics (blueprint Part B.3).

CLV is measured two ways -- probability space and price space -- and always
reported alongside a bootstrap confidence interval on the mean, per the
blueprint's "honest math" framing: a single point-estimate CLV number
without an interval is exactly the kind of unearned confidence this project
is built to avoid.
"""

from __future__ import annotations

from collections.abc import Sequence

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


def clustered_bootstrap(
    clv_series: Sequence[float],
    clusters: Sequence[object],
    n_resamples: int = 10000,
    ci: float = 0.95,
    random_state: int | None = 0,
) -> dict:
    """Mean CLV with a CI that resamples whole CLUSTERS (games), not bets.

    `bootstrap_ci` treats every bet as independent. Props break that: one game
    yields many legs that share its weather, its injury news and its Sunday
    money, so their CLVs move together. Resampling bets then counts one game's
    shared move as many confirmations and returns an interval that is too
    narrow -- exactly the unearned confidence this module exists to prevent.

    Each resample draws games with replacement and takes the bet-weighted mean
    over the drawn games, so a game with 12 legs still counts as 12 legs, but
    those 12 rise and fall together. `p_one_sided` is the share of resampled
    means <= 0: the percentile-bootstrap p-value for "mean CLV > 0", fed to
    `validation.benjamini_hochberg` across a pre-registered family.

    **Untrustworthy below ~15 clusters.** With 2 games every resample is one of
    three combinations, and the interval looks tight because there is almost
    nothing to resample (measured 2026-10-04: `middle`, 6 legs in 2 games, came
    out "significant"). The pre-registration's `>= 15 games` floor is what makes
    this number usable; callers must enforce it, not read `n_clusters` as a footnote.
    """
    values = np.asarray(clv_series, dtype=float)
    labels = np.asarray(clusters, dtype=object)
    if values.size != labels.size:
        raise ValueError("clv_series and clusters must be the same length")
    if not 0 < ci < 1:
        raise ValueError("ci must be in (0, 1)")

    _, codes = np.unique(labels.astype(str), return_inverse=True)
    sums = np.bincount(codes, weights=values)
    counts = np.bincount(codes).astype(float)
    g = sums.size
    if g < 2:
        raise ValueError("clustered_bootstrap requires at least two clusters")

    rng = np.random.default_rng(random_state)
    # How many times each game is drawn in each resample; one multinomial row
    # per resample is the vectorised form of "draw g games with replacement".
    draws = rng.multinomial(g, np.full(g, 1.0 / g), size=n_resamples)
    means = (draws @ sums) / (draws @ counts)

    alpha = 1 - ci
    return {
        "n": int(values.size),
        "n_clusters": int(g),
        "mean": float(values.mean()),
        "ci_lo": float(np.percentile(means, 100 * alpha / 2)),
        "ci_hi": float(np.percentile(means, 100 * (1 - alpha / 2))),
        "p_one_sided": float((means <= 0).mean()),
    }
