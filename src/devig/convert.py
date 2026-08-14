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
