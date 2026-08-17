import math

import pandas as pd
import pytest

from src.model.features import build_game_features, rolling_team_strength, team_game_epa

# Team A is home in three straight games one season, with each game's
# per-play EPA on offense fixed so a rolling mean is easy to hand-check:
# game 1 -> 0.5, game 2 -> -0.5, game 3 -> 100 (a deliberate outlier used
# to prove game 3's own EPA can't leak into its own pre-game feature).


def _plays(game_id: str, week: int, offense: str, defense: str, epas: list[float]) -> pd.DataFrame:
    n = len(epas)
    return pd.DataFrame(
        {
            "game_id": [game_id] * n,
            "season": [2024] * n,
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


def _non_play(game_id: str, week: int, offense: str, defense: str) -> pd.DataFrame:
    """A penalty/no-play row: pass == 0 and rush == 0, should be excluded."""
    return pd.DataFrame(
        {
            "game_id": [game_id],
            "season": [2024],
            "week": [week],
            "season_type": ["REG"],
            "posteam": [offense],
            "defteam": [defense],
            "play_type": ["no_play"],
            "pass": [0],
            "rush": [0],
            "epa": [999.0],
            "success": [1.0],
            "wp": [0.5],
        }
    )


def _pbp_fixture() -> pd.DataFrame:
    rows = [
        _plays("2024_01_A_B", 1, "A", "B", [0.4, 0.6]),
        _plays("2024_01_A_B", 1, "B", "A", [0.0, 0.0]),
        _non_play("2024_01_A_B", 1, "A", "B"),
        _plays("2024_02_A_C", 2, "A", "C", [-0.4, -0.6]),
        _plays("2024_02_A_C", 2, "C", "A", [0.0, 0.0]),
        _plays("2024_03_A_D", 3, "A", "D", [99.0, 101.0]),
        _plays("2024_03_A_D", 3, "D", "A", [0.0, 0.0]),
    ]
    return pd.concat(rows, ignore_index=True)


def _schedule_fixture() -> pd.DataFrame:
    games = [
        ("2024_01_A_B", 1, "2024-09-08", "A", "B"),
        ("2024_02_A_C", 2, "2024-09-15", "A", "C"),
        ("2024_03_A_D", 3, "2024-09-22", "A", "D"),
    ]
    df = pd.DataFrame(games, columns=["game_id", "week", "gameday", "home_team", "away_team"])
    df["season"] = 2024
    for col in ["home_rest", "away_rest", "div_game", "roof", "surface", "temp", "wind", "spread_line", "total_line"]:
        df[col] = None
    return df


def test_team_game_epa_averages_real_plays_and_drops_non_plays():
    result = team_game_epa(_pbp_fixture())
    row = result[(result.game_id == "2024_01_A_B") & (result.team == "A")].iloc[0]
    assert row["off_epa"] == pytest.approx(0.5)
    assert row["n_plays_off"] == 2  # the no_play row must not count


def test_leakage_guard_excludes_the_games_own_epa():
    """Game 3's pre-game feature must reflect only games 1 and 2 (mean of
    0.5 and -0.5 == 0.0), never game 3's own +100 outlier EPA.
    """
    team_game = team_game_epa(_pbp_fixture())
    schedule = _schedule_fixture()
    strength = rolling_team_strength(team_game, schedule)

    game3_a = strength[(strength.game_id == "2024_03_A_D") & (strength.team == "A")].iloc[0]
    assert game3_a["pre_off_epa"] == pytest.approx(0.0)
    assert game3_a["pre_off_epa"] < 1.0  # sanity: nowhere near the +100 outlier


def test_first_game_of_season_has_no_prior_history():
    team_game = team_game_epa(_pbp_fixture())
    schedule = _schedule_fixture()
    strength = rolling_team_strength(team_game, schedule)

    game1_a = strength[(strength.game_id == "2024_01_A_B") & (strength.team == "A")].iloc[0]
    assert math.isnan(game1_a["pre_off_epa"])


def test_build_game_features_does_not_fan_out_rows():
    pbp = _pbp_fixture()
    schedule = _schedule_fixture()
    feats = build_game_features(pbp, schedule)
    assert len(feats) == len(schedule)

    game3 = feats[feats.game_id == "2024_03_A_D"].iloc[0]
    assert game3["home_team"] == "A"
    assert game3["home_pre_off_epa"] == pytest.approx(0.0)

