import numpy as np
import pandas as pd
import pytest

from src.model.baseline import market_baseline
from src.model.calibration import (
    fit_residual_std,
    predict_over_proba,
    predict_over_proba_empirical,
)
from src.model.train import build_margin_total_frame, fit_margin_model, fit_total_model

# --- build_margin_total_frame: integration fixture, same shape as
# tests/test_train.py's build_training_frame fixture, plus spread/total odds. ---


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
    ]
    return pd.concat(rows, ignore_index=True)


def _schedule_fixture(spread_line=3.0, total_line=45.0, push_spread=False, push_total=False) -> pd.DataFrame:
    # Week 2: home=B 20, away=A 27 -> margin = -7, total_points = 47.
    home_score, away_score = 20, 27
    margin = home_score - away_score
    total_points = home_score + away_score
    if push_spread:
        spread_line = float(margin)
    if push_total:
        total_line = float(total_points)

    games = [
        ("2023_01_A_B", 1, "2023-09-10", "A", "B", 24, 17, -150, 130),
        ("2023_02_B_A", 2, "2023-09-17", "B", "A", home_score, away_score, 110, -130),
    ]
    df = pd.DataFrame(
        games,
        columns=["game_id", "week", "gameday", "home_team", "away_team", "home_score", "away_score", "home_moneyline", "away_moneyline"],
    )
    df["season"] = 2023
    for col in ["home_rest", "away_rest", "div_game", "roof", "surface", "temp", "wind"]:
        df[col] = 0
    df["spread_line"] = spread_line
    df["total_line"] = total_line
    df["home_spread_odds"] = -110
    df["away_spread_odds"] = -110
    df["over_odds"] = -110
    df["under_odds"] = -110
    return df


def test_build_margin_total_frame_computes_margin_and_total():
    df = build_margin_total_frame(_pbp_fixture(), _schedule_fixture())
    assert list(df["game_id"]) == ["2023_02_B_A"]  # week 1 dropped, no prior history
    row = df.iloc[0]
    assert row["margin"] == -7  # home (B) 20 - away (A) 27
    assert row["total_points"] == 47


def test_home_covers_matches_hand_computed_sign():
    # spread_line=3.0, margin=-7 -> -7 > 3.0 is False -> home did not cover
    df = build_margin_total_frame(_pbp_fixture(), _schedule_fixture(spread_line=3.0))
    assert df.iloc[0]["home_covers"] == 0.0


def test_home_covers_flips_when_home_is_a_big_enough_underdog():
    # spread_line=-10.0 (home favored by 10) would need margin > -10;
    # actual margin -7 > -10 -> True -> "covers" despite losing outright,
    # the standard spread-cover semantics.
    df = build_margin_total_frame(_pbp_fixture(), _schedule_fixture(spread_line=-10.0))
    assert df.iloc[0]["home_covers"] == 1.0


def test_push_produces_nan_not_zero_or_one():
    df = build_margin_total_frame(_pbp_fixture(), _schedule_fixture(push_spread=True, push_total=True))
    row = df.iloc[0]
    assert pd.isna(row["home_covers"])
    assert pd.isna(row["over"])


def test_market_prob_home_cover_matches_baseline_directly():
    df = build_margin_total_frame(_pbp_fixture(), _schedule_fixture())
    row = df.iloc[0]
    expected = market_baseline([int(row["home_spread_odds"]), int(row["away_spread_odds"])], side_index=0)
    assert row["market_prob_home_cover"] == pytest.approx(expected)


def test_market_prob_over_matches_baseline_directly():
    df = build_margin_total_frame(_pbp_fixture(), _schedule_fixture())
    row = df.iloc[0]
    expected = market_baseline([int(row["over_odds"]), int(row["under_odds"])], side_index=0)
    assert row["market_prob_over"] == pytest.approx(expected)


# --- fit_margin_model / fit_total_model / residual-based probability:
# unit-tested against a hand-built frame with a clear linear signal. ---


def _synthetic_margin_total_frame() -> pd.DataFrame:
    feature_columns = [
        "home_pre_off_epa", "home_pre_off_success", "home_pre_def_epa_allowed", "home_pre_def_success_allowed",
        "away_pre_off_epa", "away_pre_off_success", "away_pre_def_epa_allowed", "away_pre_def_success_allowed",
        "home_rest", "away_rest", "div_game", "home_pre_elo", "away_pre_elo", "home_pre_qb_elo", "away_pre_qb_elo",
    ]
    rng = np.random.default_rng(0)
    rows = []
    for season in (2020, 2021, 2022):
        for i in range(20):
            home_elo = 1500 + 10 * i
            away_elo = 1500 - 10 * i
            row = {c: 0.0 for c in feature_columns}
            row["home_pre_elo"] = home_elo
            row["away_pre_elo"] = away_elo
            row["home_pre_qb_elo"] = 1500.0
            row["away_pre_qb_elo"] = 1500.0
            row["home_rest"] = 7
            row["away_rest"] = 7
            row["season"] = season
            # margin is a noisy linear function of the Elo gap -- a model
            # fit on this should recover a positive home_pre_elo coefficient.
            elo_gap = home_elo - away_elo
            row["margin"] = elo_gap / 20 + rng.normal(0, 1)
            row["total_points"] = 45 + rng.normal(0, 1)
            rows.append(row)
    return pd.DataFrame(rows)


FEATS = [
    "home_pre_off_epa", "home_pre_off_success", "home_pre_def_epa_allowed", "home_pre_def_success_allowed",
    "away_pre_off_epa", "away_pre_off_success", "away_pre_def_epa_allowed", "away_pre_def_success_allowed",
    "home_rest", "away_rest", "div_game", "home_pre_elo", "away_pre_elo", "home_pre_qb_elo", "away_pre_qb_elo",
]


def test_fit_margin_model_recovers_a_positive_elo_coefficient():
    df = _synthetic_margin_total_frame()
    train_df = df[df["season"].isin([2020, 2021])]
    model = fit_margin_model(train_df, feature_columns=FEATS)
    coefs = dict(zip(FEATS, model.named_steps["linreg"].coef_, strict=True))
    assert coefs["home_pre_elo"] > 0
    assert coefs["away_pre_elo"] < 0


def test_fit_total_model_predicts_near_the_true_constant_mean():
    # total_points is pure noise around 45 in the fixture (no signal) --
    # a correctly-fit model's predictions should cluster near 45, not be
    # wildly off, confirming it fits the target column and not margin by mistake.
    df = _synthetic_margin_total_frame()
    train_df = df[df["season"].isin([2020, 2021])]
    model = fit_total_model(train_df, feature_columns=FEATS)
    preds = model.predict(train_df[FEATS])
    assert preds.mean() == pytest.approx(45.0, abs=2.0)


def test_predict_over_proba_gives_high_probability_for_a_large_positive_gap():
    df = _synthetic_margin_total_frame()
    train_df = df[df["season"].isin([2020, 2021])]
    calib_df = df[df["season"] == 2022]
    model = fit_margin_model(train_df, feature_columns=FEATS)
    sigma = fit_residual_std(model, calib_df, FEATS, "margin")
    assert sigma > 0

    # A row where the model should predict a big positive margin (home
    # heavily Elo-favored) against a modest line -> high cover probability.
    row = pd.DataFrame([{**{c: 0.0 for c in FEATS}, "home_pre_elo": 1700, "away_pre_elo": 1300,
                          "home_pre_qb_elo": 1500.0, "away_pre_qb_elo": 1500.0, "home_rest": 7, "away_rest": 7,
                          "spread_line": 1.0}])
    prob = predict_over_proba(model, row, FEATS, "spread_line", sigma)
    assert prob[0] > 0.9


def test_normal_and_empirical_probabilities_agree_closely_on_a_near_normal_residual():
    df = _synthetic_margin_total_frame()
    train_df = df[df["season"].isin([2020, 2021])]
    calib_df = df[df["season"] == 2022]
    model = fit_margin_model(train_df, feature_columns=FEATS)
    sigma = fit_residual_std(model, calib_df, FEATS, "margin")
    calib_residuals = calib_df["margin"].to_numpy() - model.predict(calib_df[FEATS])

    test_row = calib_df.assign(spread_line=0.0).iloc[[0]]
    p_normal = predict_over_proba(model, test_row, FEATS, "spread_line", sigma)
    p_empirical = predict_over_proba_empirical(model, calib_residuals, test_row, FEATS, "spread_line")
    # residuals here are synthetic Gaussian noise -- the two methods should
    # land close together, unlike a genuinely fat-tailed real distribution.
    assert abs(p_normal[0] - p_empirical[0]) < 0.15
