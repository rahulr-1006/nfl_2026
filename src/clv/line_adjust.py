"""Translating a fair probability from one spread/total line to another.

**The gap this closes.** CLV compares the price you took against the anchor's
close. That comparison is only meaningful if both sides describe the SAME
contract -- and for spread/total they routinely do not, because the line itself
moves. The first real close of the 2026 season made this concrete: a steam alert
fired on Under 44.5 in 2026_01_NE_SEA, Pinnacle closed at 44.0, and the CLV
number reported was computed across the two without adjustment.

Filtering to an exact line match instead (the first fix attempted here) is
honest but vacuous for exactly the strategies that need it most: Pinnacle's
closing line matched the alert line on **0 of 6** alerted spread/total legs in
the live store. That is structural, not bad luck -- steam and middling fire
*because* a line is moving, so by kickoff it has moved off the number you took.
Requiring an exact match makes their CLV permanently unmeasurable.

So the close is translated onto the bet's own contract instead.

**The method.** The anchor's closing quote at its own line pins the market's
implied distribution over the true outcome (home margin for SPREAD, total score
for TOTAL). Invert the closing fair probability to recover that distribution's
mean, then re-evaluate the bet's actual contract against it. `win_interval` and
`line_threshold` come from `middling.py` rather than being re-derived, so a
line is priced by one definition in this project, not two -- the same Normal
model `middling.middle_ev` and `steam.price_stale_book_opportunity` already use.

Inverting the *devigged probability* rather than reading the line alone is
deliberate: a close of 44.0 at -120/+100 carries information a bare "44.0" does
not, and at an even price the two agree exactly.

**What this assumes, and where it is known to be imperfect.** The true outcome
is modelled as Normal(mu, sigma) with sigma from `middle_scan.cached_residual_stds`.
This project's own `margin_total_models` work measured **total** residuals as
non-normal (margin residuals are fine), so a translated total CLV carries a
model assumption the raw price CLV does not. The error is second-order for the
half-point and one-point gaps that dominate real line movement, and grows with
the gap. Any writeup quoting probability CLV on totals must say so; price CLV
(`clv_price`, own book, own contract) stays assumption-free and is the number to
lean on when the two disagree.
"""

from __future__ import annotations

import math

from scipy.stats import norm

from src.backtest.middling import line_threshold, win_interval
from src.store.schema import Market, Side

# Guards norm.ppf against +/-inf at a degenerate 0 or 1 fair probability, which
# would put mu at infinity and poison every downstream number with NaN.
_PROB_EPS = 1e-6


def implied_mean(market: Market, side: Side, line: float, fair_prob: float, sigma: float) -> float:
    """The mean of the Normal the market implies, given `fair_prob` for this
    (market, side, line) contract.

    A quote is one probability and the model has one free parameter once sigma
    is fixed, so this inversion is exact rather than a fit.
    """
    if sigma <= 0:
        raise ValueError(f"sigma must be positive, got {sigma}")
    p = min(max(fair_prob, _PROB_EPS), 1 - _PROB_EPS)
    threshold = line_threshold(market, side, line)
    _, hi = win_interval(market, side, line)
    # An upper-unbounded leg (OVER / HOME cover) wins on X > threshold, so a
    # high fair probability implies a mean ABOVE the line; a lower-unbounded
    # leg (UNDER / AWAY cover) implies one below it. Hence the sign flip.
    return threshold + sigma * norm.ppf(p) if math.isinf(hi) else threshold - sigma * norm.ppf(p)


def translate_fair_prob(
    market: Market,
    side: Side,
    from_line: float,
    to_line: float,
    fair_prob: float,
    sigma: float,
) -> float:
    """`fair_prob`, quoted for (market, side, `from_line`), restated as the fair
    probability of the SAME market/side at `to_line`.

    Returns `fair_prob` unchanged when the lines already agree, so calling this
    unconditionally costs nothing and cannot introduce model error where there
    was no gap to bridge.
    """
    if from_line == to_line:
        return fair_prob
    mu = implied_mean(market, side, from_line, fair_prob, sigma)
    lo, hi = win_interval(market, side, to_line)
    return float(norm.cdf(hi, loc=mu, scale=sigma) - norm.cdf(lo, loc=mu, scale=sigma))
