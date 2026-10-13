"""Betting-evaluation harness: is an edge *bettable*, not merely calibrated?

**Why this module exists.** Everything this project measured before it answered
"is the model well-calibrated" -- Brier, log loss, reliability curves, all scored
against the market. Those are the right questions for a forecaster and the wrong
ones for a bettor. A model can be better calibrated than the book on average and
still lose money, because you only ever bet the subset of games where you disagree
with the book -- and that subset is selected precisely where your model is most
likely to be wrong. Conversely a model can be worse calibrated overall and profit,
if its disagreements are concentrated where the book is soft.

So the metrics here are all *conditional on betting*: at each minimum-edge
threshold, what did you actually stake, win, and beat the close by, and on what
fraction of available events?

**The four traps this is built to catch**, each learned the hard way in this repo:

1. **Threshold mining.** Sweeping edge thresholds and reporting the best one is
   free lunch: with enough thresholds one will look profitable. `evaluate_threshold_sweep`
   returns the whole curve, and `random_bet_benchmark` gives the null -- betting the
   *same games* at the *same prices* with randomly chosen sides. If your "edge"
   isn't clear of that, it's threshold noise.
2. **Non-monotonicity.** A real edge should strengthen (or at least hold) as the
   threshold tightens -- fewer, better bets. This project's props-EV work found the
   opposite (+3.1% at 2%, -6.3% at 4%), which is the signature of noise, not edge.
   `sweep_is_monotonic` makes that check explicit instead of eyeballed.
3. **Tiny samples wearing a big number.** "Profitable!" on 4 bets is nothing.
   `proportion_bet` and `n_bets` are reported at every threshold, and every return
   figure carries a bootstrap CI.
4. **Vig'd-line EV.** Computing edge against the offered price rather than a
   devigged fair probability manufactures edges that don't exist. This module never
   devigs -- it *requires* `fair_prob` to already be no-vig (from
   `src/model/baseline.py::market_baseline` or
   `src/backtest/engine.py::latest_fair_prob`) and says so loudly, because silently
   accepting a vig'd probability is the single easiest way to fake a result here.

**Deliberately NOT a strategy runner.** It consumes settled bets (or scored
predictions) and reports. Reuses `src/model/evaluate.py`, `src/clv/metrics.py`, and
`src/signal/sizing.py` unchanged rather than reimplementing any of their math.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from src.clv.metrics import beat_rate, bootstrap_ci
from src.model.evaluate import brier_score, log_loss, reliability_curve
from src.signal.sizing import expected_value

DEFAULT_THRESHOLDS = (0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.075, 0.10)

# Columns a settled-bet frame must carry for the sweep to mean anything.
REQUIRED_COLUMNS = ("fair_prob", "price_decimal", "won")


def _validate_bets(bets: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in bets.columns]
    if missing:
        raise ValueError(f"bets frame missing required column(s): {missing}")
    if not bets.empty:
        p = bets["fair_prob"]
        if ((p <= 0) | (p >= 1)).any():
            raise ValueError("fair_prob must be a probability in (0, 1)")
        if (bets["price_decimal"] <= 1).any():
            raise ValueError("price_decimal must be > 1")


def compare_to_book(
    model_prob: Sequence[float], book_prob: Sequence[float], outcome: Sequence[float], n_bins: int = 10
) -> dict:
    """Forecast-quality comparison: model vs. book on the same events.

    Necessary but NOT sufficient -- beating the book on Brier/log loss does not
    imply a bettable edge (see module docstring). Reported so the two questions
    stay visibly separate rather than one standing in for the other.
    """
    return {
        "n": len(outcome),
        "model_brier": brier_score(model_prob, outcome),
        "book_brier": brier_score(book_prob, outcome),
        "model_log_loss": log_loss(model_prob, outcome),
        "book_log_loss": log_loss(book_prob, outcome),
        "model_beats_book_brier": brier_score(model_prob, outcome) < brier_score(book_prob, outcome),
        "model_calibration": reliability_curve(model_prob, outcome, n_bins=n_bins),
        "book_calibration": reliability_curve(book_prob, outcome, n_bins=n_bins),
    }


def _returns(bets: pd.DataFrame) -> np.ndarray:
    """Per-unit-staked return: (d-1) on a win, -1 on a loss."""
    return np.where(bets["won"].to_numpy(dtype=bool), bets["price_decimal"].to_numpy() - 1.0, -1.0)


def evaluate_at_threshold(
    bets: pd.DataFrame,
    threshold: float,
    n_events: int | None = None,
    clv_column: str = "clv_probability",
    random_state: int | None = 0,
) -> dict:
    """Metrics for the subset of `bets` whose edge clears `threshold`.

    `bets` needs `fair_prob` (**no-vig**), `price_decimal`, `won`; optionally a
    CLV column. `n_events` is the number of events that were *available* to bet,
    which is what makes `proportion_bet` meaningful -- default is len(bets),
    i.e. treating the frame as the full opportunity set.
    """
    _validate_bets(bets)
    n_events = len(bets) if n_events is None else n_events

    edge = np.array([expected_value(p, d) for p, d in zip(bets["fair_prob"], bets["price_decimal"], strict=True)])
    selected = bets[edge >= threshold]

    base = {
        "threshold": threshold,
        "n_bets": len(selected),
        "proportion_bet": (len(selected) / n_events) if n_events else 0.0,
    }
    if selected.empty:
        return {**base, "win_rate": None, "total_return": 0.0, "roi": None,
                "roi_ci_lo": None, "roi_ci_hi": None, "mean_clv": None, "clv_beat_rate": None}

    r = _returns(selected)
    lo, hi = (bootstrap_ci(r, random_state=random_state) if len(r) >= 2 else (None, None))

    clv_vals = selected[clv_column].dropna().to_numpy() if clv_column in selected.columns else np.array([])
    return {
        **base,
        "win_rate": float(selected["won"].mean()),
        "total_return": float(r.sum()),   # in units staked
        "roi": float(r.mean()),           # per unit staked
        "roi_ci_lo": lo,
        "roi_ci_hi": hi,
        "mean_clv": float(clv_vals.mean()) if clv_vals.size else None,
        "clv_beat_rate": beat_rate(clv_vals) if clv_vals.size else None,
    }


def evaluate_threshold_sweep(
    bets: pd.DataFrame,
    thresholds: Sequence[float] = DEFAULT_THRESHOLDS,
    clv_column: str = "clv_probability",
    random_state: int | None = 0,
) -> pd.DataFrame:
    """The whole curve, one row per threshold -- never just the best cell.

    Read `n_bets`/`proportion_bet` alongside `roi`: a high ROI on a handful of
    bets is the failure mode this table exists to expose, not a finding.
    """
    n_events = len(bets)
    return pd.DataFrame(
        [evaluate_at_threshold(bets, t, n_events=n_events, clv_column=clv_column, random_state=random_state)
         for t in thresholds]
    )


def sweep_is_monotonic(sweep: pd.DataFrame, metric: str = "roi", min_bets: int = 30) -> bool | None:
    """Does `metric` hold up as the threshold tightens?

    A real edge should not *degrade* when you bet more selectively. Rows below
    `min_bets` are ignored rather than allowed to decide the answer on noise --
    the tail of any sweep is a handful of bets and will wobble regardless.

    **Returns None when there aren't two usable rows to compare** -- "cannot be
    assessed" is a genuinely different answer from "degrades", and collapsing
    them to False made a single-threshold sweep permanently un-passable. Caught
    by this module's own negative-control test, which fed it a real 60%-win-rate
    edge and got "no demonstrated edge" back.
    """
    usable = sweep[(sweep["n_bets"] >= min_bets) & sweep[metric].notna()]
    if len(usable) < 2:
        return None
    vals = usable.sort_values("threshold")[metric].to_numpy()
    return bool(np.all(np.diff(vals) >= -1e-9))


def random_bet_benchmark(
    bets: pd.DataFrame, n_simulations: int = 1000, random_state: int | None = 0
) -> dict:
    """The null model: bet the SAME events, choosing sides at random, each side
    at ITS OWN price. Returns the null ROI distribution and the observed ROI's
    percentile within it.

    This is what separates "my selection rule works" from "these games happened
    to be profitable." A strategy whose ROI sits mid-distribution has
    demonstrated nothing, however positive the raw number looks.

    **The opposite side is paid the opposite side's price** (fixed 2026-10-13).
    The old version paid the listed side's price to both sides, so at +200 the
    "random" opposite side was a ~2/3 favourite paid at 3.0 -- a null mean near
    `price/2 - 1` that no plus-money strategy could beat, and one that minus-money
    strategies beat for free. Pass `opposite_price_decimal` (the real quote on the
    other side, same book and capture) wherever it exists. Without it the
    opposite side is priced at its no-vig fair odds, `1 / (1 - fair_prob)`: zero
    EV, which is better than any real vig'd quote, so the null is HARDER to beat
    than the truth -- conservative, never flattering. `opposite_price_source`
    says which one was used.

    `p_one_sided` is the share of null ROIs at or above the observed one: the
    p-value for "beats the random-side null".
    """
    _validate_bets(bets)
    if bets.empty:
        return {"observed_roi": None, "null_mean_roi": None, "percentile": None,
                "p_one_sided": None, "n_simulations": 0, "opposite_price_source": None}

    rng = np.random.default_rng(random_state)
    d = bets["price_decimal"].to_numpy(dtype=float)
    p = bets["fair_prob"].to_numpy(dtype=float)
    observed = float(_returns(bets).mean())

    fair_opposite = 1.0 / (1.0 - p)
    if "opposite_price_decimal" in bets.columns:
        real = bets["opposite_price_decimal"].to_numpy(dtype=float)
        if (real[~np.isnan(real)] <= 1).any():
            raise ValueError("opposite_price_decimal must be > 1")
        d_opp = np.where(np.isnan(real), fair_opposite, real)
        n_real = int((~np.isnan(real)).sum())
        source = "real" if n_real == len(bets) else f"real for {n_real}/{len(bets)}, fair for the rest"
    else:
        d_opp = fair_opposite
        source = "fair (no-vig, conservative)"

    null = np.empty(n_simulations)
    for i in range(n_simulations):
        took_listed_side = rng.random(len(bets)) < 0.5
        win_prob = np.where(took_listed_side, p, 1 - p)
        price = np.where(took_listed_side, d, d_opp)
        won = rng.random(len(bets)) < win_prob
        null[i] = np.where(won, price - 1.0, -1.0).mean()

    return {
        "observed_roi": observed,
        "null_mean_roi": float(null.mean()),
        "null_std_roi": float(null.std(ddof=1)),
        "percentile": float((null < observed).mean()),
        "p_one_sided": float((null >= observed).mean()),
        "n_simulations": n_simulations,
        "opposite_price_source": source,
    }


def evaluate_strategy(
    bets: pd.DataFrame,
    thresholds: Sequence[float] = DEFAULT_THRESHOLDS,
    clv_column: str = "clv_probability",
    min_bets: int = 30,
    random_state: int | None = 0,
) -> dict:
    """Full report: sweep + monotonicity + random-bet null + a plain verdict.

    `verdict` is deliberately conservative and requires ALL of: a positive-ROI
    threshold with at least `min_bets` bets, a bootstrap CI excluding zero, an
    observed ROI above the 95th percentile of the random-side null, and a sweep
    that does not *degrade* as the threshold tightens. Any single one of those
    passing alone is exactly the kind of result this project has repeatedly
    found to evaporate.

    **Monotonicity disqualifies when it fails, but is not required when it
    can't be measured** (a single-threshold sweep has nothing to compare). An
    earlier version treated unmeasurable as failing, which made a genuine
    60%-win-rate edge report "no demonstrated edge".
    """
    sweep = evaluate_threshold_sweep(bets, thresholds, clv_column, random_state)
    null = random_bet_benchmark(bets, random_state=random_state)
    monotonic = sweep_is_monotonic(sweep, min_bets=min_bets)

    usable = sweep[(sweep["n_bets"] >= min_bets) & sweep["roi"].notna()]
    best = usable.loc[usable["roi"].idxmax()].to_dict() if not usable.empty else None

    ci_excludes_zero = bool(best and best["roi_ci_lo"] is not None and best["roi_ci_lo"] > 0)
    beats_null = bool(null["percentile"] is not None and null["percentile"] >= 0.95)
    not_degrading = monotonic is not False  # None (unmeasurable) does not disqualify
    passes = bool(best and best["roi"] > 0 and ci_excludes_zero and not_degrading and beats_null)

    return {
        "sweep": sweep,
        "best_threshold": best,
        "random_benchmark": null,
        "sweep_monotonic": monotonic,
        "ci_excludes_zero": ci_excludes_zero,
        "beats_random_null": beats_null,
        "verdict": "bettable edge" if passes else "no demonstrated edge",
    }
