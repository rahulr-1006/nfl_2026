import pytest

from src.devig.methods import DEVIG_METHODS, devig_multiplicative
from src.model.baseline import market_baseline


def test_symmetric_market_gives_half_regardless_of_method():
    assert market_baseline([-110, -110], side_index=0) == pytest.approx(0.5)
    assert market_baseline([-110, -110], side_index=1, devig_method="multiplicative") == pytest.approx(0.5)


def test_default_method_is_shin():
    # Confirms market_baseline's default actually routes through shin (not
    # silently falling back to another method) by matching it against a
    # direct shin computation on the same raw probabilities.
    odds = [-300, 250]
    shin_default = market_baseline(odds, side_index=0)
    assert shin_default == pytest.approx(DEVIG_METHODS["shin"]((300 / 400, 100 / 350)).probabilities[0])


def test_side_index_selects_the_right_side():
    odds = [-300, 250]
    home = market_baseline(odds, side_index=0, devig_method="multiplicative")
    away = market_baseline(odds, side_index=1, devig_method="multiplicative")
    assert home == pytest.approx(devig_multiplicative((300 / 400, 100 / 350)).probabilities[0])
    assert away == pytest.approx(devig_multiplicative((300 / 400, 100 / 350)).probabilities[1])
    assert home + away == pytest.approx(1.0)
