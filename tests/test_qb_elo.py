import pandas as pd
import pytest

from src.model.elo import compute_team_elo_ratings
from src.model.qb_elo import compute_qb_elo_ratings


def _schedule(games):
    rows = [
        {
            "game_id": gid,
            "season": season,
            "gameday": day,
            "home_team": home,
            "away_team": away,
            "home_score": hs,
            "away_score": aws,
            "home_qb_id": home_qb,
            "away_qb_id": away_qb,
            "home_qb_name": home_qb,
            "away_qb_name": away_qb,
        }
        for gid, season, day, home, away, hs, aws, home_qb, away_qb in games
    ]
    return pd.DataFrame(rows)


def test_first_start_for_every_qb_begins_at_initial_rating():
    schedule = _schedule([("2024_01_KC_LAC", 2024, "2024-09-08", "KC", "LAC", 27, 20, "Mahomes", "Herbert")])
    team_elo = compute_team_elo_ratings(schedule)
    qb_elo = compute_qb_elo_ratings(schedule, team_elo)

    row = qb_elo.iloc[0]
    assert row["home_pre_qb_elo"] == 1500.0
    assert row["away_pre_qb_elo"] == 1500.0


def test_upset_win_credits_the_underdog_qb_more_than_the_teams_own_elo_would():
    # KC (strong team Elo) hosts a much weaker LAC and LOSES anyway -- a
    # surprise relative to what team Elo alone predicted. Herbert (the
    # underdog's QB) should be credited; Mahomes (favorite's QB) penalized.
    schedule = _schedule(
        [
            # build up KC's team Elo first with a blowout win over a third team
            ("2024_01_KC_DEN", 2024, "2024-09-08", "KC", "DEN", 45, 3, "Mahomes", "BackupA"),
            ("2024_02_LAC_KC", 2024, "2024-09-15", "KC", "LAC", 17, 24, "Mahomes", "Herbert"),
        ]
    )
    team_elo = compute_team_elo_ratings(schedule)
    qb_elo = compute_qb_elo_ratings(schedule, team_elo)

    game2 = qb_elo.iloc[1]
    assert game2["home_post_qb_elo"] < game2["home_pre_qb_elo"]  # Mahomes penalized
    assert game2["away_post_qb_elo"] > game2["away_pre_qb_elo"]  # Herbert credited


def test_qb_rating_carries_across_games_not_reset():
    schedule = _schedule(
        [
            ("2024_01_KC_LAC", 2024, "2024-09-08", "KC", "LAC", 27, 20, "Mahomes", "Herbert"),
            ("2024_02_DEN_KC", 2024, "2024-09-15", "KC", "DEN", 24, 17, "Mahomes", "BackupA"),
        ]
    )
    team_elo = compute_team_elo_ratings(schedule)
    qb_elo = compute_qb_elo_ratings(schedule, team_elo)

    game1_mahomes_post = qb_elo.iloc[0]["home_post_qb_elo"]
    game2_mahomes_pre = qb_elo.iloc[1]["home_pre_qb_elo"]
    assert game2_mahomes_pre == pytest.approx(game1_mahomes_post)


def test_backup_qb_starts_are_tracked_as_a_distinct_rating_from_the_starter():
    # Same team (KC), different QBs across two games -- each QB's rating
    # must be tracked independently, not blended into one "team QB" value.
    schedule = _schedule(
        [
            ("2024_01_KC_LAC", 2024, "2024-09-08", "KC", "LAC", 27, 20, "Mahomes", "Herbert"),
            ("2024_02_KC_DEN", 2024, "2024-09-15", "KC", "DEN", 10, 30, "BackupA", "Nix"),  # Mahomes injured, backup starts and loses big
        ]
    )
    team_elo = compute_team_elo_ratings(schedule)
    qb_elo = compute_qb_elo_ratings(schedule, team_elo)

    game2 = qb_elo.iloc[1]
    assert game2["home_qb_id"] == "BackupA"
    assert game2["home_pre_qb_elo"] == 1500.0  # BackupA's first start, unaffected by Mahomes' rating


def test_ties_produce_zero_movement_when_team_expectation_was_even():
    schedule = _schedule([("2024_01_KC_LAC", 2024, "2024-09-08", "KC", "LAC", 20, 20, "Mahomes", "Herbert")])
    team_elo = compute_team_elo_ratings(schedule)
    # force an even team-Elo matchup by zeroing home_field_advantage in the QB computation
    qb_elo = compute_qb_elo_ratings(schedule, team_elo, home_field_advantage=0.0)

    row = qb_elo.iloc[0]
    assert row["home_post_qb_elo"] == pytest.approx(row["home_pre_qb_elo"])
    assert row["away_post_qb_elo"] == pytest.approx(row["away_pre_qb_elo"])
