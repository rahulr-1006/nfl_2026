"""Project a player's stat against the book's posted prop line.

**The formulation Phase 3 arrived at after two of its own hypotheses were killed
by the data.** Both are recorded here because they are the kind of thing that
looks reasonable on paper and wastes weeks if not checked first:

1. *"Train on features at the open, target the close."* Not buildable. The
   historical store holds **exactly one snapshot per game** (570 mainline games,
   all 0.24-0.66h before kickoff) -- those are closes; there are no opens. The
   live 2026 store has 19 snapshots/game but all 423-746h out: opens with no
   closes yet.
2. *"Predict Pinnacle's closing fair probability for a prop."* Buildable but
   pointless. Measured across all 16,953 two-sided historical prop contracts,
   that probability is **~0.5 by construction**: mean 0.4945, std 0.056, with
   46.8% falling within +/-0.02 of exactly 0.50. Pinnacle moves the *line* until
   the two sides are balanced, so the probability carries almost no information
   and predicting it perfectly would give you nothing to bet on.

**What the market actually exposes is the LINE.** "Puka Nacua 62.5 receiving
yards" is Pinnacle's estimate of that player's median outcome, and it is a real,
information-dense number. So this module projects the player's stat distribution
from pre-game form and compares it against that line -- which is how prop betting
actually works, and which the paid data supports directly: 16,953 real
(line, realized outcome) pairs to test against.

## Leakage discipline

Every feature is computed from **strictly prior games** (`prior_form`, expanding
means shifted by one), the same guarantee `src/model/features.py` gives for team
features. The posted line is a legitimate feature -- it is observable pre-kickoff
and is not derived from the outcome -- but the realized stat never touches the
feature set.

## What a result here does and does not mean

A model that beats the line more than half the time on paper still has to clear
the vig to be bettable. Route any candidate through
`src/backtest/evaluation.py::evaluate_strategy`, which applies the
threshold sweep, proportion-bet, bootstrap CI and random-side null. Accuracy here
is a necessary condition, never a sufficient one.

**PARKED 2026-08-23 (audit verdict).** Measured worse than the base rate. It is
a probability-estimation strategy, which must overcome 6.29% prop vig, and it
supplies none of it -- the same shape as every other failure here. Retained as
the record of a checked-and-rejected formulation (its docstring documents two
further hypotheses killed by pre-build data checks, which is worth keeping).
Do not re-propose without new evidence.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# Features are deliberately few and interpretable. With 7 straight
# feature-engineering failures on the moneyline model already on record, the
# prior on "more features fixes it" is poor -- this establishes whether the
# simplest real signal (a player's own recent production vs the posted line)
# carries anything before anything fancier is attempted.
PROP_FEATURE_COLUMNS = ["prior_mean", "prior_std", "prior_games", "line", "line_vs_prior_mean"]


def prior_form(player_games: pd.DataFrame, stat_column: str, min_games: int = 3) -> pd.DataFrame:
    """Per player-game: mean/std/count of `stat_column` over that player's
    STRICTLY PRIOR games, in chronological order.

    `.shift(1)` after an expanding aggregate is what makes this leakage-safe --
    without it a player's own current game leaks into the feature that predicts
    it, which would produce a spectacular and entirely fake result. Rows with
    fewer than `min_games` of history are dropped rather than imputed.

    `player_games` needs `player_display_name`, `season`, `week`, and
    `stat_column`.
    """
    df = player_games.sort_values(["player_display_name", "season", "week"]).copy()
    grp = df.groupby("player_display_name")[stat_column]
    df["prior_mean"] = grp.transform(lambda s: s.expanding().mean().shift(1))
    df["prior_std"] = grp.transform(lambda s: s.expanding().std().shift(1))
    df["prior_games"] = grp.transform(lambda s: s.expanding().count().shift(1))
    return df[df["prior_games"] >= min_games].dropna(subset=["prior_mean", "prior_std"])


def build_prop_training_frame(
    contracts: pd.DataFrame, player_games: pd.DataFrame, stat_column: str, min_games: int = 3
) -> pd.DataFrame:
    """Join posted prop contracts to leakage-safe prior form and the realized
    outcome.

    `contracts` needs `game_id`, `player_display_name`, `line`; `player_games`
    supplies `stat_column` and the history. Adds `went_over` (the label) and
    `line_vs_prior_mean` -- the single most direct expression of "does the book
    disagree with this player's recent production."
    """
    form = prior_form(player_games, stat_column, min_games=min_games)
    # `season`/`week` are carried through deliberately: every honest evaluation in
    # this project splits out-of-time by season (`validation.split_by_season`), so
    # dropping them here would force downstream code to re-join the schedule just
    # to build a legitimate train/test split.
    carried = ["game_id", "player_display_name", "season", "week", stat_column,
               "prior_mean", "prior_std", "prior_games"]
    merged = contracts.merge(
        form[[c for c in carried if c in form.columns]],
        on=["game_id", "player_display_name"],
        how="inner",
    )
    merged["went_over"] = merged[stat_column] > merged["line"]
    merged["line_vs_prior_mean"] = merged["line"] - merged["prior_mean"]
    return merged


def fit_prop_model(
    train_df: pd.DataFrame, feature_columns: Sequence[str] = PROP_FEATURE_COLUMNS
) -> Pipeline:
    """Logistic regression on P(went over). Same simple, regularised, scaled
    shape as `src/model/train.py::fit_win_probability_model` -- deliberately not
    a fancier model, so a positive result can't be attributed to capacity.
    """
    model = Pipeline([("scale", StandardScaler()), ("lr", LogisticRegression(max_iter=1000))])
    model.fit(train_df[list(feature_columns)], train_df["went_over"])
    return model


def predict_over_probability(
    model: Pipeline, df: pd.DataFrame, feature_columns: Sequence[str] = PROP_FEATURE_COLUMNS
) -> np.ndarray:
    return model.predict_proba(df[list(feature_columns)])[:, 1]


def to_bet_frame(
    df: pd.DataFrame,
    model_prob: np.ndarray,
    over_price_decimal: str | float = "over_price_decimal",
    under_price_decimal: str | float = "under_price_decimal",
) -> pd.DataFrame:
    """Turn projections into the shape `evaluation.evaluate_strategy` consumes:
    one row per bet, taking whichever side the model prefers.

    `fair_prob` is the MODEL's probability for the side taken and `price_decimal`
    is the real offered price for that same side -- so downstream EV is
    model-vs-market, which is the comparison that decides whether a projection is
    worth anything.
    """
    over_p = df[over_price_decimal] if isinstance(over_price_decimal, str) else pd.Series(over_price_decimal, index=df.index)
    under_p = df[under_price_decimal] if isinstance(under_price_decimal, str) else pd.Series(under_price_decimal, index=df.index)

    take_over = model_prob >= 0.5
    return pd.DataFrame({
        "fair_prob": np.where(take_over, model_prob, 1 - model_prob),
        "price_decimal": np.where(take_over, over_p.to_numpy(), under_p.to_numpy()),
        "won": np.where(take_over, df["went_over"].to_numpy(), ~df["went_over"].to_numpy()),
        "side": np.where(take_over, "over", "under"),
    })
