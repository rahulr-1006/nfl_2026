"""Odds conversion: American <-> decimal <-> implied probability.

Single source of truth for these conversions -- src/store/schema.py imports
american_to_decimal/decimal_to_implied_prob from here rather than
redefining them, so OddsSnapshot's validation and any devig/backtest code
always agree on the same math.
"""

from __future__ import annotations


def american_to_decimal(odds: int) -> float:
    if odds > 0:
        return 1 + odds / 100
    return 1 + 100 / (-odds)


def decimal_to_implied_prob(d: float) -> float:
    return 1 / d


def american_to_implied_prob(odds: int) -> float:
    if odds > 0:
        return 100 / (odds + 100)
    return (-odds) / ((-odds) + 100)


def implied_prob_to_decimal(prob: float) -> float:
    if not 0 < prob < 1:
        raise ValueError(f"implied probability must be in (0, 1), got {prob}")
    return 1 / prob


def decimal_to_american(d: float) -> int:
    """Inverse of `american_to_decimal` -- added 2026-08-22 for
    `src/backtest/synthetic_market.py`, the first place in this project that
    needs to go from a probability *to* a price rather than the other way
    around (every existing consumer devigs a real quoted price; this
    generates one from a simulated true probability).
    """
    if d <= 1.0:
        raise ValueError(f"decimal odds must be > 1.0, got {d}")
    if d >= 2.0:
        return round((d - 1) * 100)
    return round(-100 / (d - 1))


def implied_prob_to_american(prob: float) -> int:
    return decimal_to_american(implied_prob_to_decimal(prob))
