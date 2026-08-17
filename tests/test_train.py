import numpy as np
import pandas as pd
import pytest

from src.model.baseline import market_baseline
from src.model.train import (
    build_training_frame,
    fit_gbm_model,
    fit_win_probability_model,
    predict_home_win_proba,
    time_based_split,
)

# --- build_training_frame: integration fixture (real pbp -> features -> frame) ---

# Two teams alternate home/away across 3 weeks in one season, so by week 2
# both have one prior game's worth of history (build_game_features's
# leakage guard requires this -- see tests/test_features.py). Week 3 is a
# tie, which build_training_frame must drop since a binary win label can't
# encode it.


def _plays(game_id: str, week: int, offense: str, defense: str, epas: list[float]) -> pd.DataFrame:
    n = len(epas)
    return pd.DataFrame(
        {
            "game_id": [game_id] * n,
            "season": [2023] * n,
            "week": [week] * n,
            "season_type": ["REG"] * n,
            "posteam": [offense] * n,
            "defteam": [defense] * n,
            "play_type": ["pass"] * n,
            "pass": [1] * n,
            "rush": [0] * n,
            "epa": epas,
            "success": [1.0 if e > 0 else 0.0 for e in epas],
            "wp": [0.5] * n,
        }
    )


def _pbp_fixture() -> pd.DataFrame:
    rows = [
        _plays("2023_01_A_B", 1, "A", "B", [0.4, 0.6]),
        _plays("2023_01_A_B", 1, "B", "A", [-0.2, -0.2]),
        _plays("2023_02_B_A", 2, "B", "A", [0.3, 0.3]),
        _plays("2023_02_B_A", 2, "A", "B", [0.0, 0.0]),
        _plays("2023_03_A_B", 3, "A", "B", [0.1, 0.1]),
        _plays("2023_03_A_B", 3, "B", "A", [0.1, 0.1]),
    ]
    return pd.concat(rows, ignore_index=True)


def _schedule_fixture() -> pd.DataFrame:
    games = [
        # game_id,        week, gameday,      home, away, home_score, away_score, home_ml, away_ml
        ("2023_01_A_B", 1, "2023-09-10", "A", "B", 24, 17, -150, 130),
        ("2023_02_B_A", 2, "2023-09-17", "B", "A", 20, 27, 110, -130),
        ("2023_03_A_B", 3, "2023-09-24", "A", "B", 20, 20, -110, -110),  # tie
    ]
    df = pd.DataFrame(
        games,
        columns=["game_id", "week", "gameday", "home_team", "away_team", "home_score", "away_score", "home_moneyline", "away_moneyline"],
    )
    df["season"] = 2023
    for col in ["home_rest", "away_rest", "div_game", "roof", "surface", "temp", "wind", "spread_line", "total_line"]:
        df[col] = 0
    return df


def test_build_training_frame_drops_ties_and_first_week_rows():
    df = build_training_frame(_pbp_fixture(), _schedule_fixture())
    # Only week 2 survives: week 1 has no prior-game history (NaN
    # features), week 3 is a tie -- both must be dropped, not just one.
    assert list(df["game_id"]) == ["2023_02_B_A"]
    assert df.iloc[0]["home_win"] == 0  # B (home) lost 20-27


def test_market_prob_home_matches_baseline_directly():
    df = build_training_frame(_pbp_fixture(), _schedule_fixture())
    row = df.iloc[0]
    expected = market_baseline([int(row["home_moneyline"]), int(row["away_moneyline"])], side_index=0)
    assert row["market_prob_home"] == pytest.approx(expected)


# --- time_based_split / fit_win_probability_model / predict_home_win_proba:
# unit-tested against a hand-built feature frame, decoupled from
# build_training_frame's assembly logic above. ---


def _synthetic_feature_frame() -> pd.DataFrame:
    # 15 rows, 5 per season (2020 train / 2021 calib / 2022 test). home_win
    # is a deterministic function of home_pre_off_epa vs away_pre_off_epa
    # so the model has an actual signal to fit, not noise.
    rows = []
    for season in (2020, 2021, 2022):
        for i in range(5):
            home_epa = 0.05 * i
            away_epa = -0.05 * i
            rows.append(
                {
                    "season": season,
                    "home_pre_off_epa": home_epa,
                    "home_pre_off_success": 0.4 + 0.01 * i,
                    "home_pre_def_epa_allowed": -0.05 * i,
                    "home_pre_def_success_allowed": 0.4 - 0.01 * i,
                    "away_pre_off_epa": away_epa,
                    "away_pre_off_success": 0.4 - 0.01 * i,
                    "away_pre_def_epa_allowed": 0.05 * i,
                    "away_pre_def_success_allowed": 0.4 + 0.01 * i,
                    "home_rest": 7,
                    "away_rest": 7,
                    "div_game": i % 2,
                    "home_win": int(home_epa >= away_epa) if i > 0 else i % 2,
                }
            )
    return pd.DataFrame(rows)


def test_time_based_split_partitions_by_season_without_overlap():
    df = _synthetic_feature_frame()
    train, calib, test = time_based_split(df, train_seasons=[2020], calib_seasons=[2021], test_seasons=[2022])
    assert set(train["season"]) == {2020}
    assert set(calib["season"]) == {2021}
    assert set(test["season"]) == {2022}
    assert len(train) + len(calib) + len(test) == len(df)


def test_fit_win_probability_model_outputs_valid_probabilities():
    df = _synthetic_feature_frame()
    train, _, test = time_based_split(df, train_seasons=[2020], calib_seasons=[2021], test_seasons=[2022])
    model = fit_win_probability_model(train)
    proba = predict_home_win_proba(model, test)
    assert proba.shape == (len(test),)
    assert np.all((proba >= 0) & (proba <= 1))
    assert list(model.named_steps.keys()) == ["scale", "logit"]


def test_fit_gbm_model_outputs_valid_probabilities():
    df = _synthetic_feature_frame()
    train, _, test = time_based_split(df, train_seasons=[2020], calib_seasons=[2021], test_seasons=[2022])
    model = fit_gbm_model(train)
    proba = predict_home_win_proba(model, test)
    assert proba.shape == (len(test),)
    assert np.all((proba >= 0) & (proba <= 1))


def test_fit_gbm_model_kwargs_override_the_conservative_defaults():
    df = _synthetic_feature_frame()
    train, _, _ = time_based_split(df, train_seasons=[2020], calib_seasons=[2021], test_seasons=[2022])
    model = fit_gbm_model(train, max_iter=5, max_depth=1)
    assert model.max_iter == 5
    assert model.max_depth == 1
    assert model.learning_rate == 0.1  # untouched default still applies


def test_fit_win_probability_model_accepts_a_custom_feature_list():
    # e.g. ELO_FEATURE_COLUMNS or COMBINED_FEATURE_COLUMNS -- the same
    # feature_columns must be passed to both fit and predict.
    from src.model.train import ELO_FEATURE_COLUMNS

    df = _synthetic_feature_frame()
    df["home_pre_elo"] = 1500 + df["home_pre_off_epa"] * 100
    df["away_pre_elo"] = 1500 + df["away_pre_off_epa"] * 100
    train, _, test = time_based_split(df, train_seasons=[2020], calib_seasons=[2021], test_seasons=[2022])

    model = fit_win_probability_model(train, feature_columns=ELO_FEATURE_COLUMNS)
    proba = predict_home_win_proba(model, test, feature_columns=ELO_FEATURE_COLUMNS)

    assert proba.shape == (len(test),)
    assert np.all((proba >= 0) & (proba <= 1))
    assert model.named_steps["logit"].coef_.shape == (1, len(ELO_FEATURE_COLUMNS))


# --- build_training_frame with elo_ratings ---


def test_build_training_frame_merges_elo_ratings_when_given():
    from src.model.train import ELO_FEATURE_COLUMNS

    df = build_training_frame(_pbp_fixture(), _schedule_fixture())
    elo_ratings = pd.DataFrame(
        [{"game_id": "2023_02_B_A", "home_pre_elo": 1520.0, "away_pre_elo": 1480.0}]
    )

    with_elo = build_training_frame(_pbp_fixture(), _schedule_fixture(), elo_ratings=elo_ratings)

    assert list(df["game_id"]) == list(with_elo["game_id"])  # same rows survive
    assert set(ELO_FEATURE_COLUMNS).issubset(with_elo.columns)
    assert with_elo.iloc[0]["home_pre_elo"] == 1520.0


def test_build_training_frame_drops_rows_elo_ratings_does_not_cover():
    # elo_ratings missing the one surviving game entirely -- that row must
    # be dropped, not silently kept with a NaN elo feature.
    empty_elo = pd.DataFrame(columns=["game_id", "home_pre_elo", "away_pre_elo"])
    with_elo = build_training_frame(_pbp_fixture(), _schedule_fixture(), elo_ratings=empty_elo)
    assert with_elo.empty
