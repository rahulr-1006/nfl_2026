"""Market baseline (blueprint Part E).

"Your baseline is the devigged Pinnacle probability. Every model is
measured against 'just trust the sharp close.'" Most fancy outcome models
fail to beat this, because the market already is the model -- set this
first, so nothing downstream gets to fool itself.
"""

from __future__ import annotations

from collections.abc import Sequence

from src.devig.convert import american_to_implied_prob
from src.devig.methods import DEVIG_METHODS


def market_baseline(
    odds_american: Sequence[int], side_index: int = 0, devig_method: str = "shin"
) -> float:
    """Fair probability for the side at `side_index`, from Pinnacle's raw
    American close odds, devigged with `devig_method`.

    Defaults to Shin, matching src/backtest/engine.py's default anchor
    method -- see blueprint B.2 for why Shin is the project's choice for
    the close (it models informed money, giving the best fair
    probabilities near an efficient close).
    """
    raw_probs = tuple(american_to_implied_prob(o) for o in odds_american)
    fair = DEVIG_METHODS[devig_method](raw_probs)
    return fair.probabilities[side_index]
