"""Devig methods: turn raw (vig-inflated) implied probabilities into fair ones.

All four methods take a sequence of raw implied probabilities for one market
(e.g. [q_home, q_away]) and return fair probabilities that sum to 1. They
generalize to n-way markets, though NFL markets here are two-way.

See Part B.2 of nfl_clv_case_study_blueprint.md for the derivations. Pinnacle
close, devigged with Shin's method, is the project's reference "true"
probability for CLV.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import pandas as pd
from scipy.optimize import brentq


@dataclass(frozen=True)
class DevigResult:
    probabilities: tuple[float, ...]
    method: str
    diagnostics: dict = field(default_factory=dict)


def overround(raw_probs: Sequence[float]) -> float:
    """sum(q_i) - 1. Positive for any market with vig."""
    return sum(raw_probs) - 1


def _validate(raw_probs: Sequence[float]) -> None:
    if len(raw_probs) < 2:
        raise ValueError("need at least two outcomes to devig a market")
    if any(q <= 0 or q >= 1 for q in raw_probs):
        raise ValueError(f"raw probabilities must be in (0, 1): {raw_probs}")


def devig_multiplicative(raw_probs: Sequence[float]) -> DevigResult:
    """Split the vig proportionally. Biases favorite-longshot."""
    _validate(raw_probs)
    total = sum(raw_probs)
    probs = tuple(q / total for q in raw_probs)
    return DevigResult(probabilities=probs, method="multiplicative")


def devig_additive(raw_probs: Sequence[float]) -> DevigResult:
    """Remove an equal share of the vig from each side.

    Can produce negative probabilities on lopsided markets (a large
    favorite's raw q can be less than its share of the overround). When
    that happens we clip to 0 and renormalize, and flag it in diagnostics
    rather than silently returning a garbage probability.
    """
    _validate(raw_probs)
    n = len(raw_probs)
    share = (sum(raw_probs) - 1) / n
    raw_fair = [q - share for q in raw_probs]

    clipped = any(p < 0 for p in raw_fair)
    if clipped:
        clipped_vals = [max(p, 0.0) for p in raw_fair]
        total = sum(clipped_vals)
        probs = tuple(p / total for p in clipped_vals)
    else:
        probs = tuple(raw_fair)

    return DevigResult(
        probabilities=probs,
        method="additive",
        diagnostics={"clipped": clipped, "raw_fair": tuple(raw_fair)},
    )


def devig_power(raw_probs: Sequence[float], tol: float = 1e-10, max_iter: int = 100) -> DevigResult:
    """Solve p_i = q_i^(1/k) for k such that sum(p_i) = 1. Reduces favorite-longshot bias."""
    _validate(raw_probs)

    def total_at(k: float) -> float:
        return sum(q ** (1 / k) for q in raw_probs) - 1

    # k=1 -> sum(raw_probs) - 1 = overround > 0 (assuming a real vig market)
    # k->0+ -> sum -> 0, so total_at -> -1
    lo, hi = 1e-6, 1.0
    if total_at(hi) <= 0:
        # no vig (or negative overround, shouldn't happen with real quotes)
        return DevigResult(probabilities=tuple(raw_probs), method="power", diagnostics={"k": 1.0, "iterations": 0})

    k = brentq(total_at, lo, hi, xtol=tol, maxiter=max_iter)
    probs = tuple(q ** (1 / k) for q in raw_probs)
    return DevigResult(probabilities=probs, method="power", diagnostics={"k": k})


def devig_shin(raw_probs: Sequence[float], tol: float = 1e-10, max_iter: int = 100) -> DevigResult:
    """Solve for the proportion of informed money z, then back out fair probabilities.

    p_i = (sqrt(z^2 + 4(1-z) q_i^2 / sum(q)) - z) / (2(1-z))
    """
    _validate(raw_probs)
    total_q = sum(raw_probs)

    def shin_probs(z: float) -> tuple[float, ...]:
        if z <= 0:
            return tuple(q / total_q for q in raw_probs)  # limit at z=0 is a sqrt-normalized split
        return tuple(
            (((z**2 + 4 * (1 - z) * q**2 / total_q) ** 0.5) - z) / (2 * (1 - z)) for q in raw_probs
        )

    def total_at(z: float) -> float:
        return sum(shin_probs(z)) - 1

    lo, hi = 0.0, 0.999
    f_lo, f_hi = total_at(lo), total_at(hi)
    if f_lo * f_hi > 0:
        # degenerate market (e.g. essentially no vig); fall back to multiplicative
        fallback = devig_multiplicative(raw_probs)
        return DevigResult(
            probabilities=fallback.probabilities,
            method="shin_fallback_multiplicative",
            diagnostics={"reason": "no sign change in root-finding bracket"},
        )

    z = brentq(total_at, lo, hi, xtol=tol, maxiter=max_iter)
    probs = shin_probs(z)
    return DevigResult(probabilities=probs, method="shin", diagnostics={"z": z})


DEVIG_METHODS = {
    "multiplicative": devig_multiplicative,
    "additive": devig_additive,
    "power": devig_power,
    "shin": devig_shin,
}


def compare_methods(raw_probs: Sequence[float]) -> dict[str, DevigResult]:
    """Run all four methods on the same market. This is the Part B.2 deliverable table."""
    return {name: fn(raw_probs) for name, fn in DEVIG_METHODS.items()}


def compare_methods_table(raw_probs: Sequence[float]) -> pd.DataFrame:
    """compare_methods() as a DataFrame -- one row per method, one p_i column
    per side -- for the Part B.2 write-up ("a table showing how the four
    methods disagree on the same market").
    """
    results = compare_methods(raw_probs)
    rows = [
        {"method": name, **{f"p_{i}": p for i, p in enumerate(result.probabilities)}}
        for name, result in results.items()
    ]
    return pd.DataFrame(rows).set_index("method")
