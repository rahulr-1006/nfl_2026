import pandas as pd
import pytest

from src.model.game_level_features import (
    aggregate_pass_rush_elo_to_game,
    aggregate_receiver_elo_to_game,
)

# --- aggregate_pass_rush_elo_to_game ---


def _pass_rush_ratings(rows):
    return pd.DataFrame(
        [
            {
                "game_id": gid,
                "play_id": play_id,
                "defteam": defteam,
                "posteam": posteam,
                "pre_pass_rush_elo": pre_rush,
                "pre_pass_protection_elo": pre_protection,
            }
            for gid, play_id, defteam, posteam, pre_rush, pre_protection in rows
        ]
    )


def _schedule(games):
    return pd.DataFrame(
        [{"game_id": gid, "home_team": home, "away_team": away} for gid, home, away in games]
    )


def test_pass_rush_aggregation_takes_the_first_play_value_per_team_role():
    ratings = _pass_rush_ratings(
        [
            # KC (home) defends first: pre_pass_rush_elo=1510 is KC's pre-game rush rating
            ("G1", 10, "KC", "LAC", 1510.0, 1490.0),
            ("G1", 40, "KC", "LAC", 1513.0, 1487.0),
            # LAC (away) defends later: pre_pass_rush_elo=1495 is LAC's pre-game rush rating
            ("G1", 60, "LAC", "KC", 1495.0, 1505.0),
            ("G1", 90, "LAC", "KC", 1497.0, 1503.0),
        ]
    )
    schedule = _schedule([("G1", "KC", "LAC")])
    result = aggregate_pass_rush_elo_to_game(ratings, schedule)

    row = result.iloc[0]
    assert row["home_pre_pass_rush_elo"] == 1510.0
    assert row["away_pre_pass_rush_elo"] == 1495.0
    # home's pass-protection rating comes from the row where home is posteam (play_id=60)
    assert row["home_pre_pass_protection_elo"] == 1505.0
    assert row["away_pre_pass_protection_elo"] == 1490.0


def test_pass_rush_aggregation_handles_multiple_games():
    ratings = _pass_rush_ratings(
        [
            ("G1", 10, "KC", "LAC", 1500.0, 1500.0),
            ("G1", 20, "LAC", "KC", 1500.0, 1500.0),
            ("G2", 10, "SF", "SEA", 1520.0, 1480.0),
            ("G2", 20, "SEA", "SF", 1480.0, 1520.0),
        ]
    )
    schedule = _schedule([("G1", "KC", "LAC"), ("G2", "SF", "SEA")])
    result = aggregate_pass_rush_elo_to_game(ratings, schedule)
    assert len(result) == 2
    g2 = result[result["game_id"] == "G2"].iloc[0]
    assert g2["home_pre_pass_rush_elo"] == 1520.0


# --- aggregate_receiver_elo_to_game ---


_RECEIVER_RATING_COLUMNS = ["game_id", "season", "week", "play_id", "receiver_player_id", "defteam", "post_receiver_elo", "pre_pass_defense_elo"]


def _receiver_ratings(rows, pre_pass_defense_elo=1500.0):
    if not rows:
        return pd.DataFrame(columns=_RECEIVER_RATING_COLUMNS)
    return pd.DataFrame(
        [
            {
                "game_id": gid,
                "season": season,
                "week": week,
                "play_id": play_id,
                "receiver_player_id": pid,
                "defteam": defteam,
                "post_receiver_elo": post_elo,
                "pre_pass_defense_elo": pre_pass_defense_elo,
            }
            for gid, season, week, play_id, pid, defteam, post_elo in rows
        ]
    )


def _rosters(rows):
    return pd.DataFrame(
        [
            {"season": season, "week": week, "team": team, "gsis_id": pid, "full_name": pid, "position": position, "status": status, "status_description_abbr": status}
            for season, week, team, pid, position, status in rows
        ]
    )


def _game_schedule(games):
    return pd.DataFrame(
        [{"game_id": gid, "season": season, "week": week, "home_team": home, "away_team": away} for gid, season, week, home, away in games]
    )


def test_never_targeted_receiver_defaults_to_initial_rating():
    # Some other player (OTHER) has target history -- P1 (on the roster
    # we're aggregating) does not, so this exercises the real merge_asof
    # "no match for this player" path, not just a globally-empty input.
    ratings = _receiver_ratings([("G0", 2024, 1, 10, "OTHER", "LAC", 1600.0)])
    rosters = _rosters([(2024, 1, "KC", "P1", "WR", "ACT")])
    schedule = _game_schedule([("G1", 2024, 1, "KC", "LAC")])

    result = aggregate_receiver_elo_to_game(ratings, rosters, schedule, top_n=1)
    assert result.iloc[0]["home_receiving_corps_elo"] == pytest.approx(1500.0)


def test_receiver_rating_carries_forward_from_a_prior_week():
    ratings = _receiver_ratings(
        [
            ("G0", 2024, 1, 10, "P1", "LAC", 1600.0),
        ]
    )
    rosters = _rosters(
        [
            (2024, 1, "KC", "P1", "WR", "ACT"),
            (2024, 2, "KC", "P1", "WR", "ACT"),
        ]
    )
    # P1 not targeted in week 2 at all -- his week-2 rating must still
    # come from his last known (week 1) post-rating, not reset to default.
    schedule = _game_schedule([("G0", 2024, 1, "KC", "LAC"), ("G1", 2024, 2, "KC", "DEN")])

    result = aggregate_receiver_elo_to_game(ratings, rosters, schedule, top_n=1)
    week2_row = result[result["game_id"] == "G1"].iloc[0]
    assert week2_row["home_receiving_corps_elo"] == pytest.approx(1600.0)


def test_injured_reserve_receiver_is_excluded_and_next_man_up_counts():
    ratings = _receiver_ratings(
        [
            ("G0", 2024, 1, 10, "STAR", "LAC", 1650.0),
            ("G0", 2024, 1, 20, "BACKUP", "LAC", 1480.0),
        ]
    )
    rosters = _rosters(
        [
            (2024, 1, "KC", "STAR", "WR", "ACT"),
            (2024, 1, "KC", "BACKUP", "WR", "ACT"),
            (2024, 2, "KC", "STAR", "WR", "RES"),  # placed on IR for week 2
            (2024, 2, "KC", "BACKUP", "WR", "ACT"),
        ]
    )
    schedule = _game_schedule([("G0", 2024, 1, "KC", "LAC"), ("G1", 2024, 2, "KC", "DEN")])

    result = aggregate_receiver_elo_to_game(ratings, rosters, schedule, top_n=1)
    week2_row = result[result["game_id"] == "G1"].iloc[0]
    # top_n=1 should now pick BACKUP (1480), not STAR (still 1650 but on IR)
    assert week2_row["home_receiving_corps_elo"] == pytest.approx(1480.0)


def test_top_n_averages_the_best_rated_receivers_only():
    ratings = _receiver_ratings(
        [
            ("G0", 2024, 1, 10, "A", "LAC", 1600.0),
            ("G0", 2024, 1, 20, "B", "LAC", 1550.0),
            ("G0", 2024, 1, 30, "C", "LAC", 1400.0),
        ]
    )
    rosters = _rosters(
        [
            (2024, 2, "KC", "A", "WR", "ACT"),
            (2024, 2, "KC", "B", "WR", "ACT"),
            (2024, 2, "KC", "C", "WR", "ACT"),
        ]
    )
    schedule = _game_schedule([("G0", 2024, 1, "KC", "LAC"), ("G1", 2024, 2, "KC", "DEN")])

    result = aggregate_receiver_elo_to_game(ratings, rosters, schedule, top_n=2)
    week2_row = result[result["game_id"] == "G1"].iloc[0]
    # top 2 of {1600, 1550, 1400} = mean(1600, 1550) = 1575, C (1400) excluded
    assert week2_row["home_receiving_corps_elo"] == pytest.approx(1575.0)


def test_opponent_pass_defense_elo_comes_from_the_opposing_team():
    ratings = _receiver_ratings(
        [
            ("G1", 2024, 1, 10, "P1", "LAC", 1600.0),  # LAC is defending -> away team's defense
        ],
        pre_pass_defense_elo=1450.0,
    )
    rosters = _rosters([(2024, 1, "KC", "P1", "WR", "ACT")])
    schedule = _game_schedule([("G1", 2024, 1, "KC", "LAC")])

    result = aggregate_receiver_elo_to_game(ratings, rosters, schedule, top_n=1)
    row = result.iloc[0]
    assert row["home_opp_pass_defense_elo"] == pytest.approx(1450.0)
