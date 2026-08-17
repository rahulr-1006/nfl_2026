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

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
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
COMBINED_FEATURE_COLUMNS = FEATURE_COLUMNS + ELO_FEATURE_COLUMNS


def build_training_frame(
    pbp: pd.DataFrame,
    schedule: pd.DataFrame,
    window: int | None = None,
    elo_ratings: pd.DataFrame | None = None,
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

    Ties are rare (9 of 2743 games in 2015-2024) but undefined for a binary
    win label, so they're excluded rather than coded as 0 or 0.5.
    """
    feats = build_game_features(pbp, schedule, window=window)
    outcomes = schedule[["game_id", "home_score", "away_score", "home_moneyline", "away_moneyline"]]
    df = feats.merge(outcomes, on="game_id", how="left")

    required = ["home_score", "away_score", "home_moneyline", "away_moneyline", *FEATURE_COLUMNS]
    if elo_ratings is not None:
        df = df.merge(elo_ratings[["game_id", *ELO_FEATURE_COLUMNS]], on="game_id", how="left")
        required = required + ELO_FEATURE_COLUMNS

    df = df.dropna(subset=required)
    df = df[df["home_score"] != df["away_score"]].copy()
    df["home_win"] = (df["home_score"] > df["away_score"]).astype(int)
    df["market_prob_home"] = [
        market_baseline([int(h), int(a)], side_index=0)
        for h, a in zip(df["home_moneyline"], df["away_moneyline"], strict=True)
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


def predict_home_win_proba(model: Pipeline, df: pd.DataFrame, feature_columns: Sequence[str] = FEATURE_COLUMNS) -> np.ndarray:
    return model.predict_proba(df[feature_columns])[:, 1]
