import numpy as np
import pandas as pd
import pytest

from src.backtest.correlated_props import measure_leg_correlation
from src.backtest.validation import (
    benjamini_hochberg,
    expanding_season_folds,
    permutation_test_lift,
    split_by_season,
)

# --- split_by_season ---


def test_split_by_season_separates_rows_correctly():
    df = pd.DataFrame({"season": [2021, 2021, 2022, 2023, 2023], "x": [1, 2, 3, 4, 5]})
    train, test = split_by_season(df, test_seasons=[2023])
    assert sorted(train["season"].unique()) == [2021, 2022]
    assert sorted(test["season"].unique()) == [2023]
    assert len(train) + len(test) == len(df)


def test_split_by_season_accepts_multiple_test_seasons():
    df = pd.DataFrame({"season": [2021, 2022, 2023, 2024], "x": [1, 2, 3, 4]})
    train, test = split_by_season(df, test_seasons=[2023, 2024])
    assert sorted(train["season"]) == [2021, 2022]
    assert sorted(test["season"]) == [2023, 2024]


def test_split_by_season_resets_index():
    df = pd.DataFrame({"season": [2021, 2022, 2023]}, index=[10, 20, 30])
    train, test = split_by_season(df, test_seasons=[2023])
    assert list(train.index) == list(range(len(train)))
    assert list(test.index) == list(range(len(test)))


def test_split_by_season_missing_column_raises():
    df = pd.DataFrame({"year": [2021, 2022]})
    with pytest.raises(ValueError):
        split_by_season(df, test_seasons=[2022])


def test_split_by_season_empty_test_seasons_raises():
    df = pd.DataFrame({"season": [2021, 2022]})
    with pytest.raises(ValueError):
        split_by_season(df, test_seasons=[])


def test_split_by_season_custom_column_name():
    df = pd.DataFrame({"yr": [2021, 2022, 2023]})
    _train, test = split_by_season(df, test_seasons=[2022], season_col="yr")
    assert list(test["yr"]) == [2022]


# --- expanding_season_folds ---


def test_expanding_season_folds_produces_correct_boundaries():
    folds = expanding_season_folds(range(2015, 2025), min_train_seasons=6)
    assert len(folds) == 4  # 10 seasons - 6 min-train = 4 test seasons (2021-2024)
    train0, test0 = folds[0]
    assert train0 == [2015, 2016, 2017, 2018, 2019, 2020]
    assert test0 == 2021
    train_last, test_last = folds[-1]
    assert train_last == [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023]
    assert test_last == 2024


def test_expanding_season_folds_never_trains_on_a_later_season_than_it_tests():
    folds = expanding_season_folds(range(2015, 2025), min_train_seasons=6)
    for train_seasons, test_season in folds:
        assert all(s < test_season for s in train_seasons)


def test_expanding_season_folds_dedupes_and_sorts_input():
    folds = expanding_season_folds([2022, 2020, 2021, 2020, 2023], min_train_seasons=2)
    assert len(folds) == 2
    assert folds[0] == ([2020, 2021], 2022)
    assert folds[1] == ([2020, 2021, 2022], 2023)


def test_expanding_season_folds_rejects_non_positive_min_train_seasons():
    with pytest.raises(ValueError):
        expanding_season_folds([2020, 2021, 2022], min_train_seasons=0)


def test_expanding_season_folds_rejects_min_train_seasons_leaving_no_test_season():
    with pytest.raises(ValueError):
        expanding_season_folds([2020, 2021, 2022], min_train_seasons=3)
    with pytest.raises(ValueError):
        expanding_season_folds([2020, 2021, 2022], min_train_seasons=5)


# --- permutation_test_lift ---


def test_permutation_test_lift_matches_measure_leg_correlation_formula():
    rng = np.random.default_rng(0)
    a = pd.Series(rng.random(2000) < 0.4)
    b = pd.Series(rng.random(2000) < 0.3)
    result = permutation_test_lift(a, b, n_permutations=200, random_state=1)
    expected = measure_leg_correlation(a, b)["lift"]
    assert result["observed_lift"] == pytest.approx(expected)


def test_permutation_test_lift_flags_a_real_strong_association():
    # a and b co-occur (or both fail) 90% of the time -- a strong, real
    # signal that should sit far outside a shuffled null.
    rng = np.random.default_rng(0)
    base = rng.random(3000) < 0.5
    noise = rng.random(3000) < 0.10
    a = pd.Series(base)
    b = pd.Series(np.where(noise, ~base, base))

    result = permutation_test_lift(a, b, n_permutations=2000, random_state=42)
    assert result["observed_lift"] > 1.5
    assert result["p_value_empirical"] < 0.01
    assert result["observed_lift"] > result["null_mean"] + 5 * result["null_std"]


def test_permutation_test_lift_does_not_flag_genuine_independence():
    rng = np.random.default_rng(7)
    a = pd.Series(rng.random(2000) < 0.4)
    b = pd.Series(rng.random(2000) < 0.3)  # independently drawn, no real link to a

    result = permutation_test_lift(a, b, n_permutations=2000, random_state=8)
    # Not a tiny p-value -- genuinely independent data should look
    # unremarkable against its own null the large majority of the time.
    assert result["p_value_empirical"] > 0.05


def test_permutation_test_lift_null_mean_is_close_to_one():
    # Shuffling destroys any real association -- the null distribution of
    # lift should center near 1.0 (independence) regardless of what the
    # real data's own association looks like.
    rng = np.random.default_rng(3)
    base = rng.random(2000) < 0.5
    a = pd.Series(base)
    b = pd.Series(np.where(rng.random(2000) < 0.05, ~base, base))  # strongly associated with a

    result = permutation_test_lift(a, b, n_permutations=3000, random_state=4)
    assert result["null_mean"] == pytest.approx(1.0, abs=0.05)


def test_permutation_test_lift_is_reproducible_with_a_fixed_seed():
    rng = np.random.default_rng(0)
    a = pd.Series(rng.random(500) < 0.4)
    b = pd.Series(rng.random(500) < 0.3)
    r1 = permutation_test_lift(a, b, n_permutations=500, random_state=99)
    r2 = permutation_test_lift(a, b, n_permutations=500, random_state=99)
    assert r1 == r2


def test_permutation_test_lift_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        permutation_test_lift(pd.Series([True, False]), pd.Series([True, False, True]))


def test_permutation_test_lift_rejects_non_positive_n_permutations():
    a, b = pd.Series([True, False, True]), pd.Series([True, True, False])
    with pytest.raises(ValueError):
        permutation_test_lift(a, b, n_permutations=0)


def test_lift_matches_measure_leg_correlation():
    # Guards against the fast numpy _lift() implementation ever drifting
    # from correlated_props.py's own formula -- both must agree exactly on
    # real-shaped data, not just by construction.
    from src.backtest.validation import _lift

    rng = np.random.default_rng(11)
    a = rng.random(1000) < 0.4
    b = rng.random(1000) < 0.35
    assert _lift(a, b) == pytest.approx(measure_leg_correlation(pd.Series(a), pd.Series(b))["lift"])


# --- benjamini_hochberg ---


def test_benjamini_hochberg_matches_hand_computation_simple_case():
    # thresholds at m=5, q=0.05: [0.01, 0.02, 0.03, 0.04, 0.05]
    # sorted p (already sorted): [0.001, 0.01, 0.02, 0.04, 0.5]
    # passes: [T, T, T, T, F] -> reject ranks 1-4
    p = [0.001, 0.01, 0.02, 0.04, 0.5]
    reject = benjamini_hochberg(p, q=0.05)
    assert list(reject) == [True, True, True, True, False]


def test_benjamini_hochberg_rejects_ranks_below_the_last_passing_one_even_if_they_individually_failed():
    # Real BH semantics: reject every hypothesis up through the LARGEST
    # rank that clears its own threshold, even if an intermediate rank
    # individually failed. thresholds at m=5, q=0.05: [.01, .02, .03, .04, .05]
    # original order: [0.001, 0.024, 0.021, 0.04, 0.5]
    # sorted ascending: [0.001, 0.021, 0.024, 0.04, 0.5] (original idx: 0, 2, 1, 3, 4)
    # passes: 0.001<=.01 T; 0.021<=.02 F; 0.024<=.03 T; 0.04<=.04 T; 0.5<=.05 F
    # -> last passing rank is index 3 (0.04) -> reject sorted ranks 0-3
    # -> in ORIGINAL order, indices 0, 1, 2, 3 are rejected (idx 4 is not)
    p = [0.001, 0.024, 0.021, 0.04, 0.5]
    reject = benjamini_hochberg(p, q=0.05)
    assert list(reject) == [True, True, True, True, False]


def test_benjamini_hochberg_all_significant():
    p = [0.001, 0.002, 0.003]
    reject = benjamini_hochberg(p, q=0.05)
    assert list(reject) == [True, True, True]


def test_benjamini_hochberg_none_significant():
    p = [0.5, 0.6, 0.99]
    reject = benjamini_hochberg(p, q=0.05)
    assert list(reject) == [False, False, False]


def test_benjamini_hochberg_single_p_value():
    assert list(benjamini_hochberg([0.03], q=0.05)) == [True]
    assert list(benjamini_hochberg([0.06], q=0.05)) == [False]


def test_benjamini_hochberg_is_more_conservative_than_uncorrected_alpha():
    # A real, general property: BH-rejected set is always a subset of the
    # naive "p < q" set (BH can only reject fewer, never more).
    rng = np.random.default_rng(5)
    p = rng.random(200)
    bh_reject = benjamini_hochberg(p, q=0.05)
    naive_reject = p < 0.05
    assert np.all(bh_reject <= naive_reject)  # bh_reject implies naive_reject


def test_benjamini_hochberg_rejects_empty_input():
    with pytest.raises(ValueError):
        benjamini_hochberg([])


def test_benjamini_hochberg_rejects_invalid_q():
    with pytest.raises(ValueError):
        benjamini_hochberg([0.01, 0.02], q=0.0)
    with pytest.raises(ValueError):
        benjamini_hochberg([0.01, 0.02], q=1.0)


def test_benjamini_hochberg_rejects_out_of_range_p_values():
    with pytest.raises(ValueError):
        benjamini_hochberg([0.01, 1.5])
    with pytest.raises(ValueError):
        benjamini_hochberg([-0.1, 0.5])
