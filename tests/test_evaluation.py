import numpy as np
import pandas as pd
import pytest

from src.backtest.evaluation import (
    compare_to_book,
    evaluate_at_threshold,
    evaluate_strategy,
    evaluate_threshold_sweep,
    random_bet_benchmark,
    sweep_is_monotonic,
)


def _bets(fair_prob, price_decimal, won, clv=None):
    frame = pd.DataFrame({"fair_prob": fair_prob, "price_decimal": price_decimal, "won": won})
    if clv is not None:
        frame["clv_probability"] = clv
    return frame


def _coinflip_bets(n, price_decimal, win_rate, seed=0):
    """n bets on true 50/50 events at a fixed price, with a controlled realized
    win rate -- lets a test dial in a known edge or lack of one.
    """
    rng = np.random.default_rng(seed)
    won = rng.random(n) < win_rate
    return _bets([0.5] * n, [price_decimal] * n, won)


# --- input validation: refuse to silently produce a fake result -------------


def test_missing_required_columns_raises():
    with pytest.raises(ValueError, match="missing required column"):
        evaluate_at_threshold(pd.DataFrame({"fair_prob": [0.5]}), threshold=0.0)


def test_rejects_probabilities_outside_the_open_unit_interval():
    """A vig'd 'probability' pair sums > 1 and individual legs can exceed 1;
    accepting them silently is the easiest way to manufacture a fake edge.
    """
    with pytest.raises(ValueError, match="fair_prob"):
        evaluate_at_threshold(_bets([1.0], [2.0], [True]), threshold=0.0)
    with pytest.raises(ValueError, match="fair_prob"):
        evaluate_at_threshold(_bets([0.0], [2.0], [True]), threshold=0.0)


def test_rejects_impossible_prices():
    with pytest.raises(ValueError, match="price_decimal"):
        evaluate_at_threshold(_bets([0.5], [1.0], [True]), threshold=0.0)


# --- core metrics -----------------------------------------------------------


def test_roi_and_total_return_are_computed_per_unit_staked():
    # 2 bets at even money (2.0): one win (+1), one loss (-1) -> ROI 0
    result = evaluate_at_threshold(_bets([0.5, 0.5], [2.0, 2.0], [True, False]), threshold=0.0)
    assert result["n_bets"] == 2
    assert result["total_return"] == pytest.approx(0.0)
    assert result["roi"] == pytest.approx(0.0)
    assert result["win_rate"] == pytest.approx(0.5)


def test_threshold_filters_to_bets_that_clear_it():
    # p=0.5 at 2.5 -> EV +0.25; p=0.5 at 1.9 -> EV -0.05
    bets = _bets([0.5, 0.5], [2.5, 1.9], [True, True])
    assert evaluate_at_threshold(bets, threshold=0.0)["n_bets"] == 1
    assert evaluate_at_threshold(bets, threshold=0.5)["n_bets"] == 0


def test_proportion_bet_is_relative_to_available_events_not_selected_ones():
    """The metric that exposes 'profitable on 4 of 900 games' as noise."""
    bets = _bets([0.5] * 10, [2.5] + [1.5] * 9, [True] * 10)
    result = evaluate_at_threshold(bets, threshold=0.1, n_events=10)
    assert result["n_bets"] == 1
    assert result["proportion_bet"] == pytest.approx(0.1)


def test_empty_selection_returns_nulls_not_a_crash():
    result = evaluate_at_threshold(_bets([0.5], [1.5], [True]), threshold=0.9)
    assert result["n_bets"] == 0
    assert result["roi"] is None and result["win_rate"] is None
    assert result["total_return"] == 0.0


def test_clv_is_summarised_when_present_and_skipped_when_absent():
    with_clv = _bets([0.5, 0.5], [2.0, 2.0], [True, False], clv=[0.02, -0.01])
    result = evaluate_at_threshold(with_clv, threshold=0.0)
    assert result["mean_clv"] == pytest.approx(0.005)
    assert result["clv_beat_rate"] == pytest.approx(0.5)

    assert evaluate_at_threshold(_bets([0.5], [2.0], [True]), threshold=0.0)["mean_clv"] is None


# --- sweep + monotonicity ---------------------------------------------------


def test_sweep_returns_one_row_per_threshold():
    sweep = evaluate_threshold_sweep(_coinflip_bets(200, 2.0, 0.5), thresholds=(0.0, 0.05, 0.10))
    assert list(sweep["threshold"]) == [0.0, 0.05, 0.10]


def test_monotonicity_check_ignores_thin_tail_rows():
    """The tail of any sweep is a handful of bets and will wobble; letting it
    decide the verdict would make this check useless.
    """
    sweep = pd.DataFrame({
        "threshold": [0.0, 0.05, 0.10],
        "roi": [0.01, 0.02, -0.99],   # last row is garbage...
        "n_bets": [500, 400, 3],      # ...on 3 bets
    })
    assert sweep_is_monotonic(sweep, min_bets=30) is True


def test_degrading_sweep_is_flagged_non_monotonic():
    """The real signature of noise -- exactly what props-EV showed
    (+3.1% at 2%, -6.3% at 4%).
    """
    sweep = pd.DataFrame({
        "threshold": [0.0, 0.02, 0.04],
        "roi": [0.016, 0.031, -0.063],
        "n_bets": [824, 333, 111],
    })
    assert sweep_is_monotonic(sweep, min_bets=30) is False


# --- random-side null -------------------------------------------------------


def test_random_benchmark_places_a_fair_coinflip_strategy_mid_distribution():
    """A strategy with no real selection skill should not stand out against
    randomly chosen sides on the same games.
    """
    result = random_bet_benchmark(_coinflip_bets(400, 2.0, 0.5, seed=1), n_simulations=300)
    assert 0.05 < result["percentile"] < 0.95


def test_random_benchmark_flags_a_genuinely_strong_result():
    result = random_bet_benchmark(_coinflip_bets(400, 2.0, 0.75, seed=2), n_simulations=300)
    assert result["percentile"] > 0.95


def test_random_benchmark_on_empty_input_returns_nulls():
    assert random_bet_benchmark(_bets([], [], []))["observed_roi"] is None


# --- the acceptance tests: the harness must agree with known results --------


def test_reproduces_the_known_props_ev_null_result():
    """**Acceptance test.** `props_ev_backtest` found no detectable edge on real
    2024 props: 49.85% win rate (166/333), realized +3.07% return, bootstrap CI
    (-8.3%, +14.3%) spanning zero, and a non-monotonic threshold sweep.

    Reconstructed here at that exact win rate and price. If this harness reports
    a bettable edge on it, the harness is wrong -- that is the whole point of
    pinning it to a result already established by other means.
    """
    n, wins = 333, 166
    won = [True] * wins + [False] * (n - wins)
    # ~+3% realized return at a 49.85% win rate implies roughly even-money pricing.
    bets = _bets([0.5] * n, [2.06] * n, won)

    report = evaluate_strategy(bets, thresholds=(0.0, 0.02, 0.04), min_bets=30)

    assert report["verdict"] == "no demonstrated edge"
    assert not report["ci_excludes_zero"], "a CI spanning zero must not read as an edge"


def test_detects_a_real_edge_when_one_actually_exists():
    """The negative control for the acceptance test above: a harness that always
    says 'no edge' would trivially pass it and be worthless. A large, genuine,
    well-sampled edge must come back positive.
    """
    # 1500 bets at even money with a true 60% win rate -- an enormous, real edge.
    bets = _coinflip_bets(1500, 2.0, 0.60, seed=7)
    report = evaluate_strategy(bets, thresholds=(0.0,), min_bets=30)

    assert report["best_threshold"]["roi"] > 0
    assert report["ci_excludes_zero"]
    assert report["beats_random_null"]
    assert report["verdict"] == "bettable edge"


def test_verdict_requires_every_condition_not_just_a_positive_roi():
    """Four bets at a huge price that all happened to win: positive ROI, but
    nothing else holds. Must not read as an edge.
    """
    report = evaluate_strategy(_bets([0.5] * 4, [3.0] * 4, [True] * 4), thresholds=(0.0,), min_bets=30)
    assert report["verdict"] == "no demonstrated edge"
    assert report["best_threshold"] is None  # below min_bets, not eligible at all


# --- forecast-quality comparison -------------------------------------------


def test_compare_to_book_reports_both_sides_and_who_wins():
    outcome = [1, 0, 1, 0, 1, 0, 1, 0]
    sharp = [0.9, 0.1, 0.9, 0.1, 0.9, 0.1, 0.9, 0.1]   # nearly perfect
    vague = [0.5] * 8
    result = compare_to_book(model_prob=sharp, book_prob=vague, outcome=outcome)

    assert result["model_brier"] < result["book_brier"]
    assert result["model_beats_book_brier"] is True
    assert len(result["model_calibration"]) > 0


def test_beating_the_book_on_brier_is_reported_separately_from_bettability():
    """These are different questions and the API keeps them apart -- a model can
    win on Brier and still have no bettable edge.
    """
    result = compare_to_book([0.6] * 10, [0.5] * 10, [1] * 10)
    assert "model_beats_book_brier" in result
    assert "verdict" not in result  # bettability lives in evaluate_strategy, not here


def test_unmeasurable_monotonicity_is_none_not_false():
    """"Cannot be assessed" and "degrades" are different answers. Collapsing
    them made any single-threshold sweep permanently un-passable -- caught by
    the negative-control test above.
    """
    single_row = pd.DataFrame({"threshold": [0.0], "roi": [0.05], "n_bets": [500]})
    assert sweep_is_monotonic(single_row, min_bets=30) is None

    all_thin = pd.DataFrame({"threshold": [0.0, 0.05], "roi": [0.05, 0.04], "n_bets": [3, 2]})
    assert sweep_is_monotonic(all_thin, min_bets=30) is None


def test_degrading_sweep_still_disqualifies_even_with_everything_else_passing():
    """Monotonicity is a disqualifier when measurable -- a strong-looking result
    that decays under tighter selection must not pass.
    """
    rng = np.random.default_rng(11)
    # Loose bets win big; the selective subset (higher EV) does worse -- backwards.
    loose = _bets([0.5] * 400, [2.0] * 400, rng.random(400) < 0.70)
    tight = _bets([0.5] * 200, [3.0] * 200, rng.random(200) < 0.20)
    report = evaluate_strategy(pd.concat([loose, tight], ignore_index=True),
                               thresholds=(0.0, 0.4), min_bets=30)
    assert report["sweep_monotonic"] is False
    assert report["verdict"] == "no demonstrated edge"


# --- opposite-side pricing (fixed 2026-10-13) --------------------------------


def test_random_benchmark_does_not_pay_the_listed_price_to_the_opposite_side():
    """At +200 with a fair 1/3, the listed side is zero EV and the opposite side
    at its own fair price is zero EV too -- so the null mean must sit near 0,
    not near price/2 - 1 = +50% as the old version produced."""
    n = 2000
    bets = _bets([1 / 3] * n, [3.0] * n, [False] * n)
    result = random_bet_benchmark(bets, n_simulations=300)
    assert abs(result["null_mean_roi"]) < 0.03
    assert result["opposite_price_source"] == "fair (no-vig, conservative)"


def test_random_benchmark_uses_the_real_opposite_price_when_given():
    n = 2000
    bets = _bets([0.5] * n, [2.0] * n, [False] * n)
    bets["opposite_price_decimal"] = 1.8  # vig'd other side: -10% EV
    result = random_bet_benchmark(bets, n_simulations=300)
    # half the draws are 0 EV, half are -10% EV
    assert result["null_mean_roi"] == pytest.approx(-0.05, abs=0.02)
    assert result["opposite_price_source"] == "real"


def test_random_benchmark_falls_back_to_fair_only_where_the_real_price_is_missing():
    bets = _bets([0.5] * 4, [2.0] * 4, [True, False, True, False])
    bets["opposite_price_decimal"] = [1.9, np.nan, 1.9, np.nan]
    assert random_bet_benchmark(bets, n_simulations=10)["opposite_price_source"] == "real for 2/4, fair for the rest"


def test_random_benchmark_p_value_is_the_complement_of_the_percentile():
    result = random_bet_benchmark(_coinflip_bets(400, 2.0, 0.75, seed=2), n_simulations=300)
    assert result["p_one_sided"] < 0.05
    assert result["p_one_sided"] + result["percentile"] == pytest.approx(1.0)
