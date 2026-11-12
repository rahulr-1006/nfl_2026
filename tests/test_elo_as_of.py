import pandas as pd
import pytest

from src.model.elo import DEFAULT_SEASON_REVERSION, INITIAL_RATING, team_elo_as_of

T = pd.Timestamp


def _ratings():
    # Team A: g1 (season 2025), then g2 and g3 in 2026. g3 is a Monday-night game.
    return pd.DataFrame([
        {"game_id": "g1", "season": 2025, "home_team": "A", "away_team": "B",
         "home_pre_elo": 1500.0, "away_pre_elo": 1500.0, "home_post_elo": 1560.0, "away_post_elo": 1440.0},
        {"game_id": "g2", "season": 2026, "home_team": "C", "away_team": "A",
         "home_pre_elo": 1500.0, "away_pre_elo": 1540.0, "home_post_elo": 1490.0, "away_post_elo": 1550.0},
        {"game_id": "g3", "season": 2026, "home_team": "A", "away_team": "D",
         "home_pre_elo": 1550.0, "away_pre_elo": 1500.0, "home_post_elo": 1530.0, "away_post_elo": 1520.0},
    ])


KICKOFFS = pd.Series({
    "g1": T("2025-12-28 18:00", tz="UTC"),
    "g2": T("2026-09-13 17:00", tz="UTC"),
    "g3": T("2026-09-22 00:15", tz="UTC"),  # Monday night
})
TARGET_KO = T("2026-09-27 17:00", tz="UTC")


def test_all_prior_games_finished_uses_last_post_rating():
    as_of = T("2026-09-23 12:00", tz="UTC")
    assert team_elo_as_of(_ratings(), KICKOFFS, "A", as_of, 2026, TARGET_KO) == 1530.0


def test_game_not_finished_by_as_of_is_excluded():
    # Early price posted Sunday evening, before Monday night's game was played:
    # the Monday result must not be in the rating.
    as_of = T("2026-09-21 22:00", tz="UTC")
    assert team_elo_as_of(_ratings(), KICKOFFS, "A", as_of, 2026, TARGET_KO) == 1550.0


def test_game_in_progress_counts_as_unfinished():
    as_of = KICKOFFS["g3"] + pd.Timedelta(hours=2)
    assert team_elo_as_of(_ratings(), KICKOFFS, "A", as_of, 2026, TARGET_KO) == 1550.0


def test_new_season_applies_reversion_to_last_post_rating():
    as_of = T("2026-09-05 12:00", tz="UTC")
    expected = INITIAL_RATING + (1560.0 - INITIAL_RATING) * (1 - DEFAULT_SEASON_REVERSION)
    target = T("2026-09-13 17:00", tz="UTC")
    # g2 is the target itself (kickoff not < target), so only g1 is history.
    assert team_elo_as_of(_ratings(), KICKOFFS, "A", as_of, 2026, target) == pytest.approx(expected)


def test_team_without_history_gets_initial_rating():
    as_of = T("2026-09-23 12:00", tz="UTC")
    assert team_elo_as_of(_ratings(), KICKOFFS, "Z", as_of, 2026, TARGET_KO) == INITIAL_RATING


def test_missing_kickoff_raises():
    with pytest.raises(ValueError):
        team_elo_as_of(_ratings(), KICKOFFS.drop("g2"), "A", T("2026-09-23", tz="UTC"), 2026, TARGET_KO)
