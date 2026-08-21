"""Portfolio validation: leakage-safe splitting, walk-forward folds,
permutation nulls, and multiple-comparison correction.

**Why this module exists, stated plainly.** Every strategy in this project
so far has been validated with its own bespoke check (a chi-square test
here, a per-season persistence check there, a vig sensitivity sweep
somewhere else) -- real, useful checks, but ad hoc and not applied
consistently. Two concrete gaps motivated this module:

1. `src/backtest/correlated_props.py`'s bucket-lift pricing (§4.5's
   "game-specific" edge, 2026-08-20) computed bucket lift on the FULL
   2015-2024 pool and then applied it to "test" 2024 games that were
   THEMSELVES part of that pool -- real in-sample contamination, not a
   true held-out test, despite the paper's "applied to real test-season
   games" language implying otherwise. `split_by_season` and
   `expanding_season_folds` exist to fix this, here and for any future
   strategy that needs an honest season-based train/test boundary.
2. This project has now run ~57 real hypothesis tests (`chi2_contingency`
   calls in correlated-props' pooled/per-season/bucket analyses, plus 2
   Shapiro-Wilk normality checks) each judged against its own p<0.05 in
   isolation. With that many tests, ~1-2 false positives are expected BY
   CHANCE ALONE even if nothing were real. `benjamini_hochberg` is the
   project-wide correction that was missing.

`permutation_test_lift` is the fourth piece: an empirical, simulation-based
significance check that doesn't lean on `chi2_contingency`'s asymptotic
approximation, and -- more importantly -- tests the METHODOLOGY itself
(does this pipeline manufacture significance from data that has no real
structure?), not just any one finding.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd


def split_by_season(df: pd.DataFrame, test_seasons: Sequence[int], season_col: str = "season") -> tuple[pd.DataFrame, pd.DataFrame]:
    """(train_df, test_df): rows with `season_col` in `test_seasons` go to
    test, everything else to train. The minimum honest boundary a
    season-indexed backtest needs -- deliberately this simple, no
    shuffling, no randomness, so a caller can reason about exactly which
    rows landed where.
    """
    if season_col not in df.columns:
        raise ValueError(f"{season_col!r} not in DataFrame columns: {list(df.columns)}")
    test_seasons = set(test_seasons)
    if not test_seasons:
        raise ValueError("test_seasons must be non-empty")

    is_test = df[season_col].isin(test_seasons)
    return df.loc[~is_test].reset_index(drop=True), df.loc[is_test].reset_index(drop=True)


def expanding_season_folds(seasons: Sequence[int], min_train_seasons: int) -> list[tuple[list[int], int]]:
    """Expanding-window walk-forward folds: `(train_seasons, test_season)`
    pairs where each fold's train set is every earlier season and the test
    season is the very next one -- e.g. for seasons 2015-2024 with
    `min_train_seasons=6`: fold 1 trains on [2015..2020], tests 2021; fold
    2 trains on [2015..2021], tests 2022; ... fold 4 trains on
    [2015..2023], tests 2024. Never trains on a season that comes after
    the one it's tested against -- the walk-forward analogue of
    `src/model/train.py::time_based_split`'s single static split, applied
    as multiple folds instead of one.

    `min_train_seasons` must leave at least one season free to test against
    -- fewer than that produces zero folds, which is almost certainly a
    caller mistake, so it raises rather than silently returning `[]`.
    """
    unique_seasons = sorted(set(seasons))
    if min_train_seasons < 1:
        raise ValueError(f"min_train_seasons must be >= 1, got {min_train_seasons}")
    if min_train_seasons >= len(unique_seasons):
        raise ValueError(
            f"min_train_seasons={min_train_seasons} leaves no season to test against "
            f"(only {len(unique_seasons)} unique season(s) given)"
        )

    return [(unique_seasons[:i], unique_seasons[i]) for i in range(min_train_seasons, len(unique_seasons))]


def _lift(a: np.ndarray, b: np.ndarray) -> float:
    """P(a and b) / (P(a) x P(b)) -- the exact formula
    `src/backtest/correlated_props.py::measure_leg_correlation` uses,
    reimplemented here in pure numpy (no chi-square, no DataFrame
    overhead) so `permutation_test_lift` can call it thousands of times
    cheaply. `test_lift_matches_measure_leg_correlation` guards against
    this ever drifting from the original formula.
    """
    p_a = a.mean()
    p_b = b.mean()
    p_ab = (a & b).mean()
    denom = p_a * p_b
    return float(p_ab / denom) if denom > 0 else float("nan")


def permutation_test_lift(
    indicator_a: pd.Series, indicator_b: pd.Series, n_permutations: int = 10000, random_state: int | None = None
) -> dict:
    """An empirical, simulation-based alternative to
    `measure_leg_correlation`'s `chi2_contingency` p-value: repeatedly
    shuffles `indicator_b` (breaking any real association with
    `indicator_a` while preserving both marginal rates exactly) and
    recomputes lift each time, building an empirical null distribution of
    "what lift looks like under pure chance, given these exact base
    rates." The empirical p-value is the fraction of shuffles that
    produced a lift at least as extreme as the one actually observed.

    One-sided by construction (`null_lifts >= observed_lift`): every
    finding this project has reported claims a POSITIVE correlation
    (lift > 1), so the relevant question is "how often does chance alone
    produce a lift this high or higher," not a two-sided deviation from 1.
    Uses the "add-one" correction (`(1 + count) / (n_permutations + 1)`)
    so the reported p-value is never exactly 0 and stays a valid
    (slightly conservative) estimate regardless of how extreme the
    observed lift is.

    Doesn't just corroborate `chi2_contingency`'s asymptotic p-value with
    another number -- it tests the METHODOLOGY: if `build_team_game_outcomes`
    or `measure_leg_correlation` had a hidden bug that manufactures
    apparent structure from unstructured data, a permutation test built
    from the same raw indicators would still show it, since it makes no
    distributional assumption at all.
    """
    a = np.asarray(indicator_a, dtype=bool)
    b = np.asarray(indicator_b, dtype=bool)
    if len(a) != len(b):
        raise ValueError(f"indicator_a and indicator_b must be the same length, got {len(a)} and {len(b)}")
    if n_permutations < 1:
        raise ValueError(f"n_permutations must be >= 1, got {n_permutations}")

    observed = _lift(a, b)

    rng = np.random.default_rng(random_state)
    n = len(b)
    # Vectorized shuffle: argsort of independent random keys per row gives
    # `n_permutations` independent permutations of b in one shot, the same
    # "build an (n_permutations, n) matrix, no Python-level loop" style
    # `src/clv/metrics.py::bootstrap_ci` already uses for its resampling.
    random_keys = rng.random((n_permutations, n))
    perm_order = np.argsort(random_keys, axis=1)
    shuffled_b = b[perm_order]

    p_a = a.mean()
    p_b = b.mean()  # invariant under permutation -- b's own marginal rate never changes
    p_ab_null = (a[None, :] & shuffled_b).mean(axis=1)
    denom = p_a * p_b
    null_lifts = p_ab_null / denom if denom > 0 else np.full(n_permutations, np.nan)

    p_empirical = float((1 + np.sum(null_lifts >= observed)) / (n_permutations + 1))

    return {
        "observed_lift": observed,
        "null_mean": float(np.mean(null_lifts)),
        "null_std": float(np.std(null_lifts, ddof=1)),
        "p_value_empirical": p_empirical,
        "n_permutations": n_permutations,
    }


def benjamini_hochberg(p_values: Sequence[float], q: float = 0.05) -> np.ndarray:
    """Benjamini-Hochberg false-discovery-rate correction. Returns a
    boolean array, in the SAME order as `p_values`, of which hypotheses
    remain significant after correcting for the number of tests run
    together.

    Procedure (standard BH, not a shortcut): sort p-values ascending,
    compare each to its own rank-scaled threshold `(rank / m) * q`, find
    the LARGEST rank where the p-value clears its threshold, and reject
    every hypothesis at or below that rank -- including any individual
    p-value that failed its OWN threshold along the way (a p-value at
    rank 2 can still be rejected because rank 4 cleared its threshold,
    even if rank 2 didn't clear its own; see
    `test_benjamini_hochberg_rejects_ranks_below_the_last_passing_one_even_if_they_individually_failed`
    for a worked, hand-verified example of exactly this).
    """
    p = np.asarray(p_values, dtype=float)
    m = len(p)
    if m == 0:
        raise ValueError("p_values must be non-empty")
    if not 0 < q < 1:
        raise ValueError(f"q must be in (0, 1), got {q}")
    if np.any((p < 0) | (p > 1)):
        raise ValueError("all p_values must be in [0, 1]")

    order = np.argsort(p)
    sorted_p = p[order]
    ranks = np.arange(1, m + 1)
    thresholds = (ranks / m) * q

    passed = sorted_p <= thresholds
    reject_sorted = np.zeros(m, dtype=bool)
    if passed.any():
        k_max = int(np.max(np.nonzero(passed)[0]))
        reject_sorted[: k_max + 1] = True

    reject = np.empty(m, dtype=bool)
    reject[order] = reject_sorted
    return reject
