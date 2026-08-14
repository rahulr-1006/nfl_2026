import pytest

from src.devig.convert import (
    american_to_decimal,
    american_to_implied_prob,
    decimal_to_implied_prob,
)


def test_favorite_and_underdog_decimal_conversion():
    assert american_to_decimal(-110) == pytest.approx(1.9090909, rel=1e-6)
    assert american_to_decimal(150) == pytest.approx(2.5)


def test_known_minus_110_implied_prob():
    assert american_to_implied_prob(-110) == pytest.approx(0.52381, rel=1e-4)


def test_american_to_implied_prob_matches_decimal_round_trip():
    for odds in (-110, -300, 100, 150, 250):
        via_decimal = decimal_to_implied_prob(american_to_decimal(odds))
        direct = american_to_implied_prob(odds)
        assert via_decimal == pytest.approx(direct, rel=1e-9)


def test_symmetric_favorite_underdog_pair_implies_same_no_vig_market():
    # A -110/-110 market: both sides identical, should each imply ~0.5238
    fav = american_to_implied_prob(-110)
    dog = american_to_implied_prob(-110)
    assert fav == pytest.approx(dog)
    assert fav == pytest.approx(0.52381, rel=1e-4)


def test_decimal_to_implied_prob_round_trips_to_one_over_d():
    assert decimal_to_implied_prob(2.0) == pytest.approx(0.5)
    assert decimal_to_implied_prob(1.5) == pytest.approx(2 / 3)


@pytest.mark.parametrize("odds", [-500, -200, -110, 100, 110, 200, 500])
def test_round_trip_decimal_and_prob_stay_consistent(odds):
    d = american_to_decimal(odds)
    p_via_decimal = decimal_to_implied_prob(d)
    p_direct = american_to_implied_prob(odds)
    assert p_via_decimal == pytest.approx(p_direct, rel=1e-9)
    assert 0 < p_direct < 1
