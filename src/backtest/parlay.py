"""Parlay pricing and EV -- multi-leg bets, priced against REAL leg prices.

**Why this is a separate module from `correlated_props.py`, not more
functions inside it.** `correlated_props.py` answers a research question:
"is the correlation between two same-game outcomes real, and would a book
pricing them independently be mispricing them?" -- using modeled leg
probabilities and a modeled naive SGP price, because no real posted SGP
odds exist in this project's data. This module answers an execution
question: "given N real leg prices I can actually bet right now, what does
this parlay pay, what is its true win probability, and what is its EV
against a tracked bankroll?" Real prices in, real stake out.

**The one thing that makes parlay EV genuinely different from N single
bets, and the reason this can't just be a loop:** a parlay's payout
multiplies, so its EV is driven by the JOINT probability of every leg
hitting, not the sum of the legs' individual edges. If the legs are
positively correlated -- and this project has already *measured* that
same-game legs are (`correlated_props.py`: lift 1.07-1.48, p-values 1e-12
to 1e-142, out-of-sample validated for the underdog/narrow buckets) --
then the true joint probability is HIGHER than independence implies, while
the book's price is typically built assuming independence. That gap is the
entire thesis, and computing it requires joint probabilities, not
per-leg EVs.

**Honest limit on N > 2 legs, stated up front rather than buried.** This
project has measured *pairwise* correlation between same-game outcome
pairs. It has not measured three-way or higher joint distributions, and
the sample sizes to do so credibly (a 4-leg joint on ~5,500 team-games)
do not exist. So `parlay_true_probability` takes the joint probability as
an argument for the general case rather than inventing an N-way
correlation model -- and `two_leg_parlay_ev` is the one convenience path
that fills it in automatically, because 2-leg is exactly where this
project has real measured lift to fill it in WITH. A 5-leg parlay priced
here under `assume_independent=True` is honestly labeled as such; it is
not a correlation-aware number.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from src.signal.sizing import apply_bankroll_caps, expected_value, fractional_kelly


@dataclass(frozen=True)
class ParlayLeg:
    """One leg of a parlay, priced at a REAL book price.

    `fair_prob` is the leg's devigged fair win probability (e.g. from
    `src/backtest/engine.py::latest_fair_prob` against Pinnacle);
    `price_decimal` is the price actually available at the book being bet.
    Keeping them separate is deliberate -- the whole point is comparing a
    true probability against a real offered price, so collapsing them
    would erase the edge being measured.
    """

    label: str
    fair_prob: float
    price_decimal: float

    def __post_init__(self) -> None:
        if not 0 < self.fair_prob < 1:
            raise ValueError(f"leg {self.label!r}: fair_prob must be in (0, 1), got {self.fair_prob}")
        if self.price_decimal <= 1:
            raise ValueError(f"leg {self.label!r}: price_decimal must be > 1, got {self.price_decimal}")


def parlay_price_decimal(legs: Sequence[ParlayLeg]) -> float:
    """The real payout multiplier of an N-leg parlay: the product of every
    leg's decimal price. This is how books actually pay parlays -- it is
    not an approximation, and it is the one piece of parlay math that
    involves no assumptions at all.
    """
    if not legs:
        raise ValueError("a parlay needs at least one leg")
    return math.prod(leg.price_decimal for leg in legs)


def parlay_independent_probability(legs: Sequence[ParlayLeg]) -> float:
    """Joint win probability assuming every leg is INDEPENDENT -- the
    product of the legs' fair probabilities.

    For same-game legs this is known to be wrong in a measured direction
    (see module docstring): real same-game legs are positively correlated,
    so this UNDERSTATES the true joint probability. That is precisely why
    it's useful as a reference point -- the gap between this and the true
    joint probability is the correlation edge.
    """
    if not legs:
        raise ValueError("a parlay needs at least one leg")
    return math.prod(leg.fair_prob for leg in legs)


def parlay_true_probability(legs: Sequence[ParlayLeg], joint_lift: float = 1.0) -> float:
    """Correlation-adjusted joint win probability: the independent product
    scaled by `joint_lift`, then clipped to a valid probability.

    `joint_lift` is `P(all legs) / prod(P(leg))` -- exactly the `lift`
    quantity `correlated_props.py::measure_leg_correlation` already measures
    and validates out-of-sample. 1.0 means independence (no adjustment).

    **Clipped at the smallest leg probability, not at 1.0.** A joint
    probability can never exceed any of its marginals: if a leg hits 30% of
    the time, no combination including it can hit more than 30% of the time.
    Clipping only at 1.0 would let an aggressive lift produce a joint
    probability that is arithmetically impossible -- the same clip
    `estimate_game_specific_joint_prob` already applies for the 2-leg case.
    """
    if joint_lift <= 0:
        raise ValueError(f"joint_lift must be positive, got {joint_lift}")
    independent = parlay_independent_probability(legs)
    return min(independent * joint_lift, min(leg.fair_prob for leg in legs))


def parlay_ev(
    legs: Sequence[ParlayLeg],
    joint_lift: float = 1.0,
    bankroll: float = 100.0,
    kelly_fraction_k: float = 0.375,
) -> dict:
    """Full EV/sizing for one parlay, reusing `src/signal/sizing.py`'s
    `expected_value`/`fractional_kelly`/`apply_bankroll_caps` completely
    unchanged -- the same sizing math every other +EV signal in this
    project uses, not a bespoke parlay calculation.

    Returns the independent-assumption probability alongside the
    correlation-adjusted one so the correlation contribution is always
    visible rather than silently baked in.
    """
    price = parlay_price_decimal(legs)
    p_independent = parlay_independent_probability(legs)
    p_true = parlay_true_probability(legs, joint_lift)

    ev = expected_value(p_true, price)
    stake = apply_bankroll_caps(fractional_kelly(p_true, price, k=kelly_fraction_k) * bankroll, bankroll=bankroll)

    return {
        "n_legs": len(legs),
        "labels": [leg.label for leg in legs],
        "parlay_price_decimal": price,
        "p_independent": p_independent,
        "joint_lift": joint_lift,
        "p_true": p_true,
        "ev_independent": expected_value(p_independent, price),
        "ev": ev,
        "suggested_stake": stake,
    }


def two_leg_parlay_ev(
    leg_a: ParlayLeg,
    leg_b: ParlayLeg,
    measured_lift: float,
    bankroll: float = 100.0,
    kelly_fraction_k: float = 0.375,
) -> dict:
    """The one case this project has real measured correlation for: two
    same-game legs, with `measured_lift` from
    `correlated_props.py::measure_leg_correlation_by_bucket` (or
    `team_total_props.py`'s equivalent) fit on TRAIN data only.

    Deliberately requires `measured_lift` rather than defaulting it to 1.0:
    a 2-leg same-game parlay priced as if independent is exactly the
    mistake this whole line of work exists to identify, so the caller has
    to say what correlation they're assuming.
    """
    return parlay_ev([leg_a, leg_b], joint_lift=measured_lift, bankroll=bankroll, kelly_fraction_k=kelly_fraction_k)
