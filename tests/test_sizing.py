import pytest

from src.signal.sizing import (
    apply_bankroll_caps,
    expected_value,
    fractional_kelly,
    kelly_fraction,
)

# p=0.55, d=2.0 (even money): b=1, q=0.45 -> EV = 0.55 - 0.45 = 0.10, f* = 0.10
POSITIVE_EDGE = (0.55, 2.0)
# p=0.45, d=2.0: EV = 0.45 - 0.55 = -0.10, f* = -0.10 (no edge on this side)
NEGATIVE_EDGE = (0.45, 2.0)


def test_expected_value_hand_computed():
    p, d = POSITIVE_EDGE
    assert expected_value(p, d) == pytest.approx(0.10)


def test_expected_value_negative_edge():
    p, d = NEGATIVE_EDGE
    assert expected_value(p, d) == pytest.approx(-0.10)


def test_expected_value_breakeven_is_zero():
    # fair coin at even money: EV = 0.5*1 - 0.5 = 0
    assert expected_value(0.5, 2.0) == pytest.approx(0.0)


def test_kelly_fraction_hand_computed():
    p, d = POSITIVE_EDGE
    assert kelly_fraction(p, d) == pytest.approx(0.10)


def test_kelly_fraction_negative_when_no_edge():
    p, d = NEGATIVE_EDGE
    assert kelly_fraction(p, d) == pytest.approx(-0.10)


def test_kelly_fraction_rejects_invalid_probability():
    with pytest.raises(ValueError):
        kelly_fraction(1.5, 2.0)
    with pytest.raises(ValueError):
        kelly_fraction(-0.1, 2.0)


def test_kelly_fraction_rejects_decimal_odds_at_or_below_one():
    with pytest.raises(ValueError):
        kelly_fraction(0.5, 1.0)
    with pytest.raises(ValueError):
        kelly_fraction(0.5, 0.9)


def test_fractional_kelly_default_is_midpoint_of_blueprint_range():
    p, d = POSITIVE_EDGE
    assert fractional_kelly(p, d) == pytest.approx(0.375 * kelly_fraction(p, d))


def test_fractional_kelly_custom_k():
    p, d = POSITIVE_EDGE
    assert fractional_kelly(p, d, k=0.25) == pytest.approx(0.25 * 0.10)
    assert fractional_kelly(p, d, k=0.5) == pytest.approx(0.5 * 0.10)


def test_fractional_kelly_rejects_invalid_k():
    with pytest.raises(ValueError):
        fractional_kelly(0.55, 2.0, k=0)
    with pytest.raises(ValueError):
        fractional_kelly(0.55, 2.0, k=1.5)


def test_apply_bankroll_caps_clips_large_stake_to_max_bet():
    # fractional_kelly(0.375) on a strong 10% edge -> 3.75% of $100 = $3.75, capped to $2
    assert apply_bankroll_caps(3.75, bankroll=100, max_bet=2.00, min_bet=0.10) == pytest.approx(2.00)


def test_apply_bankroll_caps_passes_through_stake_within_bounds():
    assert apply_bankroll_caps(0.507, bankroll=100, max_bet=2.00, min_bet=0.10) == pytest.approx(0.507)


def test_apply_bankroll_caps_returns_zero_below_min_bet_rather_than_rounding_up():
    assert apply_bankroll_caps(0.0075, bankroll=100, max_bet=2.00, min_bet=0.10) == 0.0


def test_apply_bankroll_caps_returns_zero_for_negative_stake():
    # a negative-edge Kelly fraction turned into a negative dollar stake -> no bet
    assert apply_bankroll_caps(-3.75, bankroll=100, max_bet=2.00, min_bet=0.10) == 0.0


def test_apply_bankroll_caps_never_exceeds_bankroll_even_if_max_bet_is_larger():
    assert apply_bankroll_caps(500, bankroll=100, max_bet=1000, min_bet=0.10) == pytest.approx(100)


def test_full_pipeline_positive_edge_hits_the_two_percent_cap():
    p, d = POSITIVE_EDGE
    fraction = fractional_kelly(p, d)  # 0.0375
    stake = apply_bankroll_caps(fraction * 100, bankroll=100, max_bet=2.00, min_bet=0.10)
    assert stake == pytest.approx(2.00)


def test_full_pipeline_negative_edge_produces_no_bet():
    p, d = NEGATIVE_EDGE
    fraction = fractional_kelly(p, d)
    stake = apply_bankroll_caps(fraction * 100, bankroll=100, max_bet=2.00, min_bet=0.10)
    assert stake == 0.0
