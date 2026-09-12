"""Predict Pinnacle's CLOSING fair probability from pre-game features.

**This is the first place in the project where the paid odds data is a training
TARGET rather than a scoreboard.** Every other model here predicts `home_win` and
is then *scored against* the market. This one predicts the market itself.

## Why a different target, and why it's worth having

`home_win` is a single Bernoulli draw: enormously noisy, one observation per game.
The closing fair probability is the market's own aggregated estimate of that same
quantity -- far lower variance, and (per this project's own repeated finding) more
accurate than any model here. Regressing onto it asks a different, more tractable
question: *given what was knowable pre-game, where does the sharp price end up?*

Operationally that is the CLV thesis stated as a model. If you can predict the close
from features available days earlier, then any current price that disagrees with your
predicted close is a candidate bet -- which is how CLV is earned, rather than
measured after the fact.

## The formulation the data actually supports (verified, not assumed)

The plan for this phase was "features at the open, target the close." **That is not
buildable here.** Checked 2026-08-23: the historical store holds **exactly one
snapshot per game** (570 games, all 0.24-0.66h before kickoff) -- those are closes,
and there are no opens. The live 2026 store has 19 snapshots/game but all 423-746
hours out, i.e. opens with no closes yet.

**Partly lifted 2026-08-23:** 105 games of 2024 now carry a real 6-point series
(T-120h..close) bought via `collect/mainline_historical.py` -- the "no opens"
constraint was cost, not impossibility. This module is still PARKED on its own
merits (its result was an honest negative), but a future re-run has real early
prices available for those 105 games.

So the target is the close and the features are **pre-game, not pre-open**: rolling
EPA, Elo, QB Elo, rest -- all computed from strictly prior games by
`src/model/features.py`'s existing leakage-safe builders. That keeps the leakage
discipline the plan called for (no closing information may reach a feature) while
being honest that "at the open" is not something this data can express.

## What this does NOT establish

Predicting the close accurately is **not** the same as profit. To bet on it you need
a real price that differs from your predicted close by more than the vig, and this
module says nothing about whether such prices exist or persist. Route any candidate
strategy through `src/backtest/evaluation.py::evaluate_strategy` before calling it an
edge -- a good R^2 here is a necessary condition, not a sufficient one.

**PARKED 2026-08-23 (audit verdict).** Phase 3 research that reached an honest
NEGATIVE result: recent form adds nothing beyond the line itself. The question
it asked was worth asking -- it is the one model here that predicts the market
rather than being scored against it -- but the answer was no, and nothing
downstream consumes it. Reopen only with a new feature family, not a re-run.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.backtest.engine import latest_fair_prob
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, Side

# Far enough past any real kickoff that read_as_of returns the whole store; the
# closing quote is then the latest one available for that event.
_ALL_TIME = datetime(2099, 1, 1, tzinfo=UTC)


def closing_fair_probabilities(
    store: PointInTimeStore,
    event_ids: Sequence[str],
    book: str = "pinnacle",
    devig_method: str = "shin",
) -> pd.DataFrame:
    """`event_id` -> `close_fair_prob`, the devigged closing home-win probability.

    Deduplicates snapshots before devigging: this project's own smoke-test runs
    re-pulled a handful of games at an identical `capture_time`, and
    `latest_fair_prob` correctly refuses to guess between duplicate rows (it
    requires exactly two sides at the latest timestamp) -- so without the dedup
    those games silently drop out.
    """
    rows = []
    for event_id in event_ids:
        snaps = store.read_as_of(_ALL_TIME, event_id=event_id)
        if snaps.empty:
            continue
        snaps = snaps.drop_duplicates(subset=["capture_time", "event_id", "book", "market", "side", "line"])
        p = latest_fair_prob(
            snaps, book, Market.MONEYLINE, Side.HOME, _ALL_TIME, devig_method, event_id=event_id
        )
        if p is not None:
            rows.append({"game_id": event_id, "close_fair_prob": p})
    return pd.DataFrame(rows)


def build_closing_line_frame(
    training_frame: pd.DataFrame,
    store: PointInTimeStore,
    book: str = "pinnacle",
    devig_method: str = "shin",
) -> pd.DataFrame:
    """`training_frame` (from `src/model/train.py::build_training_frame`) joined to
    the real closing fair probability, inner -- games without a real close are
    dropped rather than imputed.

    Every feature in `training_frame` is pre-game by construction (see
    `features.py`'s leakage guard); the only new column is the target.
    """
    closes = closing_fair_probabilities(store, training_frame["game_id"].unique(), book, devig_method)
    return training_frame.merge(closes, on="game_id", how="inner")


def fit_closing_line_model(
    train_df: pd.DataFrame, feature_columns: Sequence[str], alpha: float = 1.0
) -> Pipeline:
    """Ridge regression onto `close_fair_prob`.

    Ridge rather than plain OLS because the feature set is deliberately
    collinear -- `training_frame_exploration.ipynb` measured team Elo and QB Elo
    at r=0.65, and the EPA columns overlap with both. Regularisation is the
    honest response to that, and with only ~570 labelled games the variance
    reduction matters more than the small bias.
    """
    model = Pipeline([("scale", StandardScaler()), ("ridge", Ridge(alpha=alpha))])
    model.fit(train_df[list(feature_columns)], train_df["close_fair_prob"])
    return model


def predict_closing_prob(model: Pipeline, df: pd.DataFrame, feature_columns: Sequence[str]) -> np.ndarray:
    """Predicted closing probability, clipped to a valid range -- an unclipped
    linear model will happily predict 1.03.
    """
    return np.clip(model.predict(df[list(feature_columns)]), 1e-4, 1 - 1e-4)


def evaluate_closing_line_model(
    model: Pipeline,
    test_df: pd.DataFrame,
    feature_columns: Sequence[str],
    naive_baseline: float | None = None,
) -> dict:
    """How well does it predict the close, against two baselines that matter?

    - **Naive**: always predict the training mean (or `naive_baseline`). Beating
      this only proves the features carry *some* signal.
    - **Own-outcome-model**: `market_prob_home` is already in the training frame.
      Comparing against it answers the question that actually matters -- does
      modelling the close beat just reading the market's own number? A model that
      can't beat the thing it's predicting has no independent value.

    Returns RMSE/MAE/R^2 for each, plus the residual series for downstream use
    (the residual, not the prediction, is what a strategy would trade on).
    """
    y = test_df["close_fair_prob"].to_numpy()
    pred = predict_closing_prob(model, test_df, feature_columns)
    naive = np.full_like(y, naive_baseline if naive_baseline is not None else y.mean())

    def _stats(p):
        err = p - y
        ss_res = float((err**2).sum())
        ss_tot = float(((y - y.mean()) ** 2).sum())
        return {
            "rmse": float(np.sqrt((err**2).mean())),
            "mae": float(np.abs(err).mean()),
            "r2": 1 - ss_res / ss_tot if ss_tot > 0 else float("nan"),
        }

    out = {"n": len(y), "model": _stats(pred), "naive": _stats(naive), "residuals": pred - y}
    if "market_prob_home" in test_df.columns:
        out["own_outcome_model"] = _stats(test_df["market_prob_home"].to_numpy())
    return out
