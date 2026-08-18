"""Model training (blueprint Part E): first outcome model + time-based split.

**Historical (nflverse) odds vs. live (Pinnacle) odds -- read this before
trusting any number this module produces.**

- This module trains and validates on 2015-2024 games using nflverse's
  schedule odds (`home_moneyline`/`away_moneyline`), which nflverse sources
  as a market-consensus close. That close is NOT confirmed to be Pinnacle.
- The project's actual CLV thesis (blueprint Part A; paper Sec 3.4/4.3) is
  anchored to Pinnacle specifically, captured by the live collector
  (`src/collect/`) only from 2026-08-14 onward. Pinnacle-anchored CLV
  cannot be computed on 2015-2024 data at all -- there is no historical
  intraday snapshot to measure "entry vs. close" against, only a single
  closing number.
- So what this module can honestly produce is **calibration quality**
  (Brier, log loss, reliability -- `src/model/evaluate.py`) against a
  market-consensus baseline, not a CLV backtest. The CLV headline result
  stays a live-2026-season-only claim, reported once collector data
  accrues (paper Sec 5.3).

The model deliberately excludes market odds as an input feature: it's
scored against `src/model/baseline.py`'s devigged market price using
`evaluate.py`'s metrics, so the comparison stays "model vs. market" rather
than the model just re-deriving the market's own price.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.model.baseline import market_baseline
from src.model.features import build_game_features

FEATURE_COLUMNS = [
    "home_pre_off_epa",
    "home_pre_off_success",
    "home_pre_def_epa_allowed",
    "home_pre_def_success_allowed",
    "away_pre_off_epa",
    "away_pre_off_success",
    "away_pre_def_epa_allowed",
    "away_pre_def_success_allowed",
    "home_rest",
    "away_rest",
    "div_game",
]
EPA_FEATURE_COLUMNS = FEATURE_COLUMNS  # backward-compat alias, now that a second feature set (Elo) exists
ELO_FEATURE_COLUMNS = ["home_pre_elo", "away_pre_elo"]
QB_FEATURE_COLUMNS = ["home_pre_qb_elo", "away_pre_qb_elo"]
COMBINED_FEATURE_COLUMNS = FEATURE_COLUMNS + ELO_FEATURE_COLUMNS
COMBINED_QB_FEATURE_COLUMNS = COMBINED_FEATURE_COLUMNS + QB_FEATURE_COLUMNS


def build_training_frame(
    pbp: pd.DataFrame,
    schedule: pd.DataFrame,
    window: int | None = None,
    elo_ratings: pd.DataFrame | None = None,
    qb_elo_ratings: pd.DataFrame | None = None,
    exclude_garbage_time: bool = False,
) -> pd.DataFrame:
    """One row per game: `build_game_features()` output plus the home-win
    label and the devigged market-consensus probability, with ties and
    missing-feature rows (a team's first game in the cached window, no
    prior-game history to average -- see features.py's leakage guard)
    dropped.

    `elo_ratings`: optional output of `src/model/elo.py::compute_team_elo_ratings`,
    built from the same schedule. When given, merges in `home_pre_elo`/
    `away_pre_elo` (see `ELO_FEATURE_COLUMNS`) and drops any row it
    doesn't cover -- shouldn't happen when both come from the same
    schedule, but not assumed.

    `qb_elo_ratings`: optional output of `src/model/qb_elo.py::compute_qb_elo_ratings`,
    built from the same schedule (and the same `elo_ratings`, since QB Elo
    reads team Elo as its expectation baseline). When given, merges in
    `home_pre_qb_elo`/`away_pre_qb_elo` (see `QB_FEATURE_COLUMNS`), same
    drop-if-uncovered behavior as `elo_ratings`.

    `exclude_garbage_time`: see `features.py::team_game_epa` -- defaults to
    False so the original EPA feature set's numbers stay reproducible.

    Ties are rare (9 of 2743 games in 2015-2024) but undefined for a binary
    win label, so they're excluded rather than coded as 0 or 0.5.
    """
    feats = build_game_features(pbp, schedule, window=window, exclude_garbage_time=exclude_garbage_time)
    outcomes = schedule[["game_id", "home_score", "away_score", "home_moneyline", "away_moneyline"]]
    df = feats.merge(outcomes, on="game_id", how="left")

    required = ["home_score", "away_score", "home_moneyline", "away_moneyline", *FEATURE_COLUMNS]
    if elo_ratings is not None:
        df = df.merge(elo_ratings[["game_id", *ELO_FEATURE_COLUMNS]], on="game_id", how="left")
        required = required + ELO_FEATURE_COLUMNS
    if qb_elo_ratings is not None:
        df = df.merge(qb_elo_ratings[["game_id", *QB_FEATURE_COLUMNS]], on="game_id", how="left")
        required = required + QB_FEATURE_COLUMNS

    df = df.dropna(subset=required)
    df = df[df["home_score"] != df["away_score"]].copy()
    df["home_win"] = (df["home_score"] > df["away_score"]).astype(int)
    df["market_prob_home"] = [
        market_baseline([int(h), int(a)], side_index=0)
        for h, a in zip(df["home_moneyline"], df["away_moneyline"], strict=True)
    ]
    return df


def build_margin_total_frame(
    pbp: pd.DataFrame,
    schedule: pd.DataFrame,
    window: int | None = None,
    elo_ratings: pd.DataFrame | None = None,
    qb_elo_ratings: pd.DataFrame | None = None,
    exclude_garbage_time: bool = False,
) -> pd.DataFrame:
    """`build_training_frame()`'s output plus spread/total regression
    targets and their market-baseline comparison probabilities -- a
    separate function, not an edit to `build_training_frame`, since that
    function's `required` dropna list and its callers' fixtures don't
    carry spread/total odds columns; extending it in place would silently
    drop rows for every existing moneyline caller.

    New columns:
    - `margin` = home_score - away_score. A tie's margin (0) is a valid
      regression target, unlike the home-win label -- ties are NOT
      dropped here the way `build_training_frame` drops them.
    - `total_points` = home_score + away_score.
    - `home_covers` / `over`: nullable 0/1 labels for the probability-
      comparison harness, NaN on a push (`margin == spread_line` /
      `total_points == total_line`). Pushes are common on key numbers (3,
      7) -- expect a real NaN rate (3-4 of ~285 games/season observed),
      not a rounding edge case. Callers must filter on `.notna()` before
      scoring, the same way `build_training_frame`'s tie-drop keeps a
      binary label well-defined.
    - `market_prob_home_cover` / `market_prob_over`: devigged fair
      probabilities from the spread/total odds pair, via the same
      `market_baseline()` used for `market_prob_home` -- it's already
      generic over any two-outcome American-odds pair, no new devig code.

    Sign convention, hand-verified against `src/store/settlement.py::settle()`
    on real 2024 games before trusting it here: `home_covers = margin >
    spread_line` using nflverse's raw (unflipped) `spread_line` column
    directly -- NOT `home_spread_line()`, which exists to convert to the
    sportsbook-posted line convention `settle()` expects, a different
    representation of the same number. `over = total_points > total_line`
    needs no conversion at all (total has no home/away sign ambiguity).
    """
    df = build_training_frame(
        pbp, schedule, window=window, elo_ratings=elo_ratings, qb_elo_ratings=qb_elo_ratings,
        exclude_garbage_time=exclude_garbage_time,
    )
    # spread_line/total_line already flow through build_game_features's context
    # columns -- only the odds (needed to devig a fair cover/over probability)
    # are new here.
    odds = schedule[["game_id", "home_spread_odds", "away_spread_odds", "over_odds", "under_odds"]]
    df = df.merge(odds, on="game_id", how="left")
    required = ["spread_line", "home_spread_odds", "away_spread_odds", "total_line", "over_odds", "under_odds"]
    df = df.dropna(subset=required)

    df["margin"] = df["home_score"] - df["away_score"]
    df["total_points"] = df["home_score"] + df["away_score"]

    df["home_covers"] = np.where(
        df["margin"] == df["spread_line"], np.nan, (df["margin"] > df["spread_line"]).astype(float)
    )
    df["over"] = np.where(
        df["total_points"] == df["total_line"], np.nan, (df["total_points"] > df["total_line"]).astype(float)
    )

    df["market_prob_home_cover"] = [
        market_baseline([int(h), int(a)], side_index=0)
        for h, a in zip(df["home_spread_odds"], df["away_spread_odds"], strict=True)
    ]
    df["market_prob_over"] = [
        market_baseline([int(o), int(u)], side_index=0)
        for o, u in zip(df["over_odds"], df["under_odds"], strict=True)
    ]
    return df


def time_based_split(
    df: pd.DataFrame, train_seasons: Sequence[int], calib_seasons: Sequence[int], test_seasons: Sequence[int]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Three-way, out-of-time split: fit the model on `train_seasons`, fit
    the calibration layer (`src/model/calibration.py`) on `calib_seasons`,
    and report final numbers only on `test_seasons` -- no season is used
    for more than one of {fit model, fit calibration, report results}.
    """
    train = df[df["season"].isin(train_seasons)].copy()
    calib = df[df["season"].isin(calib_seasons)].copy()
    test = df[df["season"].isin(test_seasons)].copy()
    return train, calib, test


class _ProbaClassifier(Protocol):
    def predict_proba(self, X) -> np.ndarray: ...


def fit_win_probability_model(train_df: pd.DataFrame, feature_columns: Sequence[str] = FEATURE_COLUMNS) -> Pipeline:
    """Standardized logistic regression on `feature_columns` (default:
    EPA only -- "start simple" per blueprint Part E, before reaching for
    a gradient-boosted model). Pass `ELO_FEATURE_COLUMNS` or
    `COMBINED_FEATURE_COLUMNS` for the Elo-only / EPA+Elo variants --
    whichever list is used here must be passed again to
    `predict_home_win_proba`, the fitted Pipeline doesn't remember it.
    """
    model = Pipeline([("scale", StandardScaler()), ("logit", LogisticRegression(max_iter=1000))])
    model.fit(train_df[feature_columns], train_df["home_win"])
    return model


def fit_gbm_model(
    train_df: pd.DataFrame,
    feature_columns: Sequence[str] = FEATURE_COLUMNS,
    **kwargs,
) -> HistGradientBoostingClassifier:
    """Gradient-boosted trees on `feature_columns` -- blueprint Part E's
    other suggested option ("logistic OR GBM"), actually tried now.
    sklearn's HistGradientBoostingClassifier, not a new dependency (scikit-learn
    is already required). No StandardScaler -- tree splits are scale-invariant,
    unlike the logistic model.

    Defaults are the best of a small hand-swept grid on this dataset's
    size (~1700 training games, a dozen features) -- not sklearn's own
    defaults, which grow deeper/more numerous trees than a set this small
    can support without overfitting, and not an arbitrary first guess
    either (an earlier max_depth=3/max_iter=200 config scored notably
    worse; see notebooks/model_backtest_results.ipynb for the sweep).
    Even at this best-found setting, GBM does not beat the logistic model
    on this feature set (§4.5 of the paper) -- shallow trees and few
    rounds narrow the gap, they don't close it. `**kwargs` overrides any
    default for further sweeping.
    """
    defaults = {"max_iter": 50, "max_depth": 2, "learning_rate": 0.1, "l2_regularization": 1.0, "random_state": 0}
    model = HistGradientBoostingClassifier(**{**defaults, **kwargs})
    model.fit(train_df[feature_columns], train_df["home_win"])
    return model


def predict_home_win_proba(
    model: _ProbaClassifier, df: pd.DataFrame, feature_columns: Sequence[str] = FEATURE_COLUMNS
) -> np.ndarray:
    return model.predict_proba(df[feature_columns])[:, 1]


def fit_margin_model(train_df: pd.DataFrame, feature_columns: Sequence[str] = COMBINED_QB_FEATURE_COLUMNS) -> Pipeline:
    """Standardized linear regression predicting `margin` (home_score -
    away_score) -- "start simple" the same way `fit_win_probability_model`
    did before GBM was tried; a GBM regressor is a natural follow-up, not
    part of this first cut. Reuses the same feature set the win-probability
    model uses -- no new feature engineering, the point of this model is a
    richer *target* (continuous margin vs. binary win/loss), not richer inputs.

    The raw margin prediction isn't a bet by itself -- pair with
    `src/model/calibration.py::fit_residual_std`/`predict_over_proba` to
    turn it into a cover probability comparable against
    `market_prob_home_cover` (`build_margin_total_frame`).
    """
    model = Pipeline([("scale", StandardScaler()), ("linreg", LinearRegression())])
    model.fit(train_df[feature_columns], train_df["margin"])
    return model


def fit_total_model(train_df: pd.DataFrame, feature_columns: Sequence[str] = COMBINED_QB_FEATURE_COLUMNS) -> Pipeline:
    """Same as `fit_margin_model`, predicting `total_points` (home_score +
    away_score) instead of margin -- pair with `predict_over_proba` against
    `market_prob_over`.
    """
    model = Pipeline([("scale", StandardScaler()), ("linreg", LinearRegression())])
    model.fit(train_df[feature_columns], train_df["total_points"])
    return model
