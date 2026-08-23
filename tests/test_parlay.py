import pytest

from src.backtest.parlay import (
    ParlayLeg,
    parlay_ev,
    parlay_independent_probability,
    parlay_price_decimal,
    parlay_true_probability,
    two_leg_parlay_ev,
)

EVEN = ParlayLeg(label="even", fair_prob=0.5, price_decimal=2.0)
FAV = ParlayLeg(label="fav", fair_prob=0.6, price_decimal=1.6)


def test_parlay_price_is_the_product_of_leg_prices():
    assert parlay_price_decimal([EVEN, EVEN]) == pytest.approx(4.0)
    assert parlay_price_decimal([EVEN, EVEN, EVEN]) == pytest.approx(8.0)
    assert parlay_price_decimal([EVEN, FAV]) == pytest.approx(3.2)


def test_independent_probability_is_the_product_of_leg_probabilities():
    assert parlay_independent_probability([EVEN, EVEN]) == pytest.approx(0.25)
    assert parlay_independent_probability([EVEN, FAV]) == pytest.approx(0.30)


def test_empty_parlay_rejected():
    with pytest.raises(ValueError):
        parlay_price_decimal([])
    with pytest.raises(ValueError):
        parlay_independent_probability([])


def test_leg_validates_probability_and_price():
    with pytest.raises(ValueError, match="fair_prob"):
        ParlayLeg(label="bad", fair_prob=0.0, price_decimal=2.0)
    with pytest.raises(ValueError, match="price_decimal"):
        ParlayLeg(label="bad", fair_prob=0.5, price_decimal=1.0)


def test_lift_of_one_leaves_the_independent_probability_unchanged():
    assert parlay_true_probability([EVEN, EVEN], joint_lift=1.0) == pytest.approx(0.25)


def test_positive_lift_raises_the_joint_probability_above_independence():
    # The measured same-game correlation effect: true joint > independent product.
    assert parlay_true_probability([EVEN, EVEN], joint_lift=1.4) == pytest.approx(0.35)


def test_joint_probability_can_never_exceed_the_smallest_leg():
    # A leg that hits 30% of the time caps any parlay containing it at 30%,
    # no matter how large the lift -- clipping only at 1.0 would allow an
    # arithmetically impossible joint probability.
    small = ParlayLeg(label="small", fair_prob=0.30, price_decimal=4.0)
    big = ParlayLeg(label="big", fair_prob=0.90, price_decimal=1.2)
    assert parlay_true_probability([small, big], joint_lift=10.0) == pytest.approx(0.30)


def test_lift_must_be_positive():
    with pytest.raises(ValueError, match="joint_lift"):
        parlay_true_probability([EVEN, EVEN], joint_lift=0.0)


def test_correlation_turns_a_negative_ev_parlay_positive():
    """The whole thesis in one test: a fairly-priced-under-independence
    parlay is break-even; the same parlay with real measured positive
    correlation is +EV, because the book's price assumed independence.
    """
    independent = parlay_ev([EVEN, EVEN], joint_lift=1.0)
    correlated = parlay_ev([EVEN, EVEN], joint_lift=1.4)

    assert independent["ev"] == pytest.approx(0.0)  # 0.25 * 4.0 = fair
    assert correlated["ev"] > 0
    assert correlated["p_true"] > correlated["p_independent"]


def test_parlay_ev_reports_both_independent_and_correlated_ev():
    result = parlay_ev([EVEN, FAV], joint_lift=1.2)
    assert "ev_independent" in result and "ev" in result
    assert result["ev"] > result["ev_independent"]  # correlation only helps here
    assert result["n_legs"] == 2
    assert result["labels"] == ["even", "fav"]


def test_parlay_stake_respects_the_bankroll_cap():
    # A hugely +EV parlay still cannot stake more than the 2%-of-bankroll cap.
    result = parlay_ev([EVEN, EVEN], joint_lift=1.9, bankroll=100.0)
    assert result["suggested_stake"] <= 2.0


def test_no_edge_parlay_suggests_no_stake():
    # Priced worse than fair under independence, with no correlation help.
    bad = ParlayLeg(label="bad", fair_prob=0.5, price_decimal=1.5)
    assert parlay_ev([bad, bad], joint_lift=1.0)["suggested_stake"] == 0.0


def test_two_leg_helper_requires_an_explicit_measured_lift():
    # Signature-level check: measured_lift is positional-required, so a
    # same-game 2-leg parlay can't be silently priced as independent.
    with pytest.raises(TypeError):
        two_leg_parlay_ev(EVEN, EVEN)


def test_two_leg_helper_matches_parlay_ev_with_the_same_lift():
    assert two_leg_parlay_ev(EVEN, FAV, measured_lift=1.3)["ev"] == pytest.approx(
        parlay_ev([EVEN, FAV], joint_lift=1.3)["ev"]
    )
