"""Expected value and Kelly bet sizing (blueprint Part B.4).

Full Kelly is too volatile on a noisy edge, so this project sizes at
fractional Kelly (k in [0.25, 0.5]) and then clips to a hard 2%-of-bankroll
cap ($2 on a $100 bankroll). The cap binds before Kelly usually would at
this bankroll size -- that's intentional. Per the blueprint: "A 100
bankroll cannot compound in a meaningful way. Sizing here demonstrates
correct method, not bankroll growth."
"""

from __future__ import annotations


def _validate(p: float, d: float) -> None:
    if not 0 <= p <= 1:
        raise ValueError(f"p must be in [0, 1], got {p}")
    if d <= 1:
        raise ValueError(f"decimal odds d must be > 1, got {d}")


def expected_value(p: float, d: float) -> float:
    """EV of a unit bet at fair win probability p and decimal odds d."""
    _validate(p, d)
    return p * (d - 1) - (1 - p)


def kelly_fraction(p: float, d: float) -> float:
    """Full Kelly fraction of bankroll.

    Can be negative when the price is bad at this probability (no edge on
    this side) -- callers should not bet in that case. apply_bankroll_caps
    enforces that downstream: any non-positive or sub-minimum stake clamps
    to 0 rather than betting anyway.
    """
    _validate(p, d)
    b = d - 1
    q = 1 - p
    return (b * p - q) / b


def fractional_kelly(p: float, d: float, k: float = 0.375) -> float:
    """k * full Kelly. k in [0.25, 0.5] per the blueprint; default 0.375 is the midpoint."""
    if not 0 < k <= 1:
        raise ValueError(f"k must be in (0, 1], got {k}")
    return k * kelly_fraction(p, d)


def apply_bankroll_caps(
    stake: float, bankroll: float = 100, max_bet: float = 2.00, min_bet: float = 0.10
) -> float:
    """Clip a dollar stake to [min_bet, min(max_bet, bankroll)].

    Below min_bet -- including any non-positive stake from a Kelly
    fraction with no edge -- returns 0 (no bet) rather than rounding up to
    the floor, per the blueprint's "hard limits" framing.
    """
    effective_max = min(max_bet, bankroll)
    if stake < min_bet:
        return 0.0
    return min(stake, effective_max)
