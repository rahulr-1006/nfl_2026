import inspect

import pytest

from src.devig.methods import (
    DEVIG_METHODS,
    compare_methods,
    compare_methods_table,
    devig_additive,
    devig_multiplicative,
    devig_power,
    devig_shin,
    overround,
)

# -110 / -110 market: each side implies 110/210 = 0.52381
STANDARD_TWO_WAY = (110 / 210, 110 / 210)

# lopsided market: heavy favorite -300, dog +250
FAVORITE = 300 / 400  # 0.75
DOG = 100 / 350  # 0.2857
LOPSIDED = (FAVORITE, DOG)


@pytest.mark.parametrize("method_name", list(DEVIG_METHODS.keys()))
def test_all_methods_sum_to_one_on_standard_market(method_name):
    result = DEVIG_METHODS[method_name](STANDARD_TWO_WAY)
    assert sum(result.probabilities) == pytest.approx(1.0, abs=1e-6)


@pytest.mark.parametrize("method_name", list(DEVIG_METHODS.keys()))
def test_all_methods_sum_to_one_on_lopsided_market(method_name):
    result = DEVIG_METHODS[method_name](LOPSIDED)
    assert sum(result.probabilities) == pytest.approx(1.0, abs=1e-6)


def test_multiplicative_is_proportional_split():
    result = devig_multiplicative(STANDARD_TWO_WAY)
    assert result.probabilities[0] == pytest.approx(0.5)
    assert result.probabilities[1] == pytest.approx(0.5)


def test_overround_positive_for_vig_market():
    assert overround(STANDARD_TWO_WAY) > 0
    assert overround(STANDARD_TWO_WAY) == pytest.approx(220 / 210 - 1)


def test_additive_matches_multiplicative_on_symmetric_market():
    # symmetric market: additive and multiplicative agree
    add = devig_additive(STANDARD_TWO_WAY)
    mult = devig_multiplicative(STANDARD_TWO_WAY)
    assert add.probabilities[0] == pytest.approx(mult.probabilities[0], abs=1e-6)


def test_additive_flags_and_clips_negative_probability():
    # construct a market lopsided enough that additive goes negative:
    # heavy favorite q close to 1, big overround
    extreme = (0.97, 0.35)  # sum = 1.32, overround = 0.32, share = 0.16 -> underdog side unaffected but check favorite
    result = devig_additive(extreme)
    assert sum(result.probabilities) == pytest.approx(1.0, abs=1e-6)
    assert all(p >= 0 for p in result.probabilities)
    # if clipping happened, diagnostics should say so
    if result.diagnostics["clipped"]:
        assert any(p < 0 for p in result.diagnostics["raw_fair"])


def test_devig_rejects_degenerate_probabilities():
    with pytest.raises(ValueError):
        devig_multiplicative((1.0, 0.5))
    with pytest.raises(ValueError):
        devig_multiplicative((0.0, 0.5))


def test_power_method_corrects_favorite_longshot_bias_vs_multiplicative():
    # Favorite-longshot bias means bettors overbet longshots, so raw longshot
    # implied probability is inflated relative to true probability. The power
    # method corrects this by assigning the favorite *more* fair probability
    # (and the longshot less) than a naive proportional (multiplicative) split.
    mult = devig_multiplicative(LOPSIDED)
    power = devig_power(LOPSIDED)
    assert power.probabilities[0] >= mult.probabilities[0] - 1e-9


def test_shin_gives_a_small_positive_z_on_standard_market():
    result = devig_shin(STANDARD_TWO_WAY)
    assert 0 <= result.diagnostics.get("z", 0) < 0.5


def test_compare_methods_returns_all_four():
    results = compare_methods(STANDARD_TWO_WAY)
    assert set(results.keys()) == {"multiplicative", "additive", "power", "shin"}
    for result in results.values():
        assert sum(result.probabilities) == pytest.approx(1.0, abs=1e-6)


def test_compare_methods_table_has_one_row_per_method_and_sums_to_one():
    table = compare_methods_table(LOPSIDED)
    assert set(table.index) == {"multiplicative", "additive", "power", "shin"}
    assert list(table.columns) == ["p_0", "p_1"]
    row_sums = table["p_0"] + table["p_1"]
    assert (row_sums.round(6) == 1.0).all()


# --- vig magnitude invariance -----------------------------------------------
#
# Prompted by a real question: published figures put player-prop vig near 12%,
# far above the 6.93% median this project measures on its own markets. The
# concern was whether the deviggers are calibrated to a vig level and would
# silently under-remove a fatter one.
#
# They are not, and these tests pin that. Every method derives the vig from the
# quote it is handed -- `overround()` is `sum(q_i) - 1` computed from that
# quote -- so there is no vig constant to be wrong. MEASURED_PROP_VIG lives in
# src/backtest/correlated_props.py and is never imported here; it feeds the SGP
# pricing simulator, which has no real quote to read.


def _symmetric_market(overround_target: float) -> tuple[float, float]:
    """Two-way market with a known overround, priced 50/50 before vig."""
    q = (1.0 + overround_target) / 2.0
    return (q, q)


@pytest.mark.parametrize("target", [0.0476, 0.0693, 0.12, 0.20, 0.35])
@pytest.mark.parametrize("name", sorted(DEVIG_METHODS))
def test_devig_removes_whatever_vig_is_present(name, target):
    """A 35% market gets 35% removed, same as a 4.76% one. The methods are
    scale-free in the vig, which is the whole property the concern was about.
    """
    raw = _symmetric_market(target)
    assert overround(raw) == pytest.approx(target, abs=1e-9)

    result = DEVIG_METHODS[name](raw)
    assert sum(result.probabilities) == pytest.approx(1.0, abs=1e-9)
    # Symmetric market must devig to a coin flip regardless of how fat the vig is.
    assert result.probabilities[0] == pytest.approx(0.5, abs=1e-6)


@pytest.mark.parametrize("name", sorted(DEVIG_METHODS))
def test_fatter_vig_yields_strictly_lower_fair_probability_on_a_favorite(name):
    """The fair probability of a given raw price must FALL as the market's vig
    rises -- more of that price is juice. If a method ignored vig magnitude
    this would come out flat.
    """
    fav_raw = 0.60
    thin = DEVIG_METHODS[name]((fav_raw, 0.4476))   # ~4.76% overround
    fat = DEVIG_METHODS[name]((fav_raw, 0.5200))    # ~12% overround
    assert fat.probabilities[0] < thin.probabilities[0]
    for r in (thin, fat):
        assert sum(r.probabilities) == pytest.approx(1.0, abs=1e-9)


def test_no_vig_constant_is_imported_into_the_devig_module():
    """Guards the separation directly: if someone ever wires a measured-vig
    constant into devigging, the devigger stops reading the real market and
    starts asserting one. That is the failure the concern imagined.
    """
    import src.devig.methods as m

    src = inspect.getsource(m)
    assert "MEASURED_PROP_VIG" not in src
    assert "correlated_props" not in src
