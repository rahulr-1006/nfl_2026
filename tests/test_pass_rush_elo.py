import pandas as pd
import pytest

from src.model.elo import elo_win_probability
from src.model.pass_rush_elo import (
    DEFAULT_BASE_PRESSURE_OFFSET,
    compute_pass_rush_elo_ratings,
    credited_pressure_counts,
)


def test_base_pressure_offset_recenters_expectation_to_the_measured_base_rate():
    # At rating parity (1500 vs 1500), the offset should make the expected
    # pressure probability land near the ~13.6% base rate it was derived
    # from -- not 50%, which is what an uncorrected contest would assume.
    expected = elo_win_probability(1500.0, 1500.0, DEFAULT_BASE_PRESSURE_OFFSET)
    assert expected == pytest.approx(0.13639, abs=1e-4)


def _pbp(plays):
    rows = [
        {
            "season": season,
            "week": week,
            "game_id": gid,
            "play_id": play_id,
            "posteam": posteam,
            "defteam": defteam,
            "pass": 1.0,
            "sack": sack,
            "qb_hit": qb_hit,
        }
        for season, week, gid, play_id, posteam, defteam, sack, qb_hit in plays
    ]
    return pd.DataFrame(rows)


def test_first_dropback_begins_at_initial_rating():
    pbp = _pbp([(2024, 1, "2024_01_PIT_BAL", 10, "PIT", "BAL", 0.0, 0.0)])
    ratings = compute_pass_rush_elo_ratings(pbp)

    row = ratings.iloc[0]
    assert row["pre_pass_rush_elo"] == 1500.0
    assert row["pre_pass_protection_elo"] == 1500.0


def test_sack_raises_rush_elo_and_lowers_protection_elo():
    pbp = _pbp([(2024, 1, "2024_01_PIT_BAL", 10, "PIT", "BAL", 1.0, 0.0)])
    ratings = compute_pass_rush_elo_ratings(pbp)

    row = ratings.iloc[0]
    assert row["post_pass_rush_elo"] > row["pre_pass_rush_elo"]
    assert row["post_pass_protection_elo"] < row["pre_pass_protection_elo"]


def test_qb_hit_also_counts_as_a_pass_rush_win():
    pbp = _pbp([(2024, 1, "2024_01_PIT_BAL", 10, "PIT", "BAL", 0.0, 1.0)])
    ratings = compute_pass_rush_elo_ratings(pbp)

    row = ratings.iloc[0]
    assert row["pressure"] == 1.0
    assert row["post_pass_rush_elo"] > row["pre_pass_rush_elo"]


def test_clean_pocket_lowers_rush_elo_and_raises_protection_elo():
    pbp = _pbp([(2024, 1, "2024_01_PIT_BAL", 10, "PIT", "BAL", 0.0, 0.0)])
    ratings = compute_pass_rush_elo_ratings(pbp)

    row = ratings.iloc[0]
    assert row["post_pass_rush_elo"] < row["pre_pass_rush_elo"]
    assert row["post_pass_protection_elo"] > row["pre_pass_protection_elo"]


def test_update_is_symmetric_zero_sum():
    pbp = _pbp([(2024, 1, "2024_01_PIT_BAL", 10, "PIT", "BAL", 1.0, 0.0)])
    ratings = compute_pass_rush_elo_ratings(pbp)

    row = ratings.iloc[0]
    rush_gain = row["post_pass_rush_elo"] - row["pre_pass_rush_elo"]
    protection_loss = row["pre_pass_protection_elo"] - row["post_pass_protection_elo"]
    assert rush_gain == pytest.approx(protection_loss)


def test_rating_carries_across_plays_not_reset():
    pbp = _pbp(
        [
            (2024, 1, "2024_01_PIT_BAL", 10, "PIT", "BAL", 1.0, 0.0),
            (2024, 1, "2024_01_PIT_BAL", 40, "PIT", "BAL", 0.0, 0.0),
        ]
    )
    ratings = compute_pass_rush_elo_ratings(pbp)

    play1_post = ratings.iloc[0]["post_pass_rush_elo"]
    play2_pre = ratings.iloc[1]["pre_pass_rush_elo"]
    assert play2_pre == pytest.approx(play1_post)


def test_plays_are_processed_in_chronological_order_within_a_game():
    pbp = _pbp(
        [
            (2024, 1, "2024_01_PIT_BAL", 40, "PIT", "BAL", 1.0, 0.0),
            (2024, 1, "2024_01_PIT_BAL", 10, "PIT", "BAL", 1.0, 0.0),
        ]
    )
    ratings = compute_pass_rush_elo_ratings(pbp)

    assert list(ratings["play_id"]) == [10, 40]
    assert ratings.iloc[1]["pre_pass_rush_elo"] == pytest.approx(ratings.iloc[0]["post_pass_rush_elo"])


def test_rows_missing_sack_or_qb_hit_are_excluded():
    pbp = pd.DataFrame(
        [
            {
                "season": 2024,
                "week": 1,
                "game_id": "2024_01_PIT_BAL",
                "play_id": 10,
                "posteam": "PIT",
                "defteam": "BAL",
                "pass": 1.0,
                "sack": None,
                "qb_hit": None,
            },
            {
                "season": 2024,
                "week": 1,
                "game_id": "2024_01_PIT_BAL",
                "play_id": 40,
                "posteam": "PIT",
                "defteam": "BAL",
                "pass": 1.0,
                "sack": 0.0,
                "qb_hit": 0.0,
            },
        ]
    )
    ratings = compute_pass_rush_elo_ratings(pbp)
    assert len(ratings) == 1
    assert ratings.iloc[0]["play_id"] == 40


def test_non_dropback_plays_are_excluded():
    pbp = pd.DataFrame(
        [
            {
                "season": 2024,
                "week": 1,
                "game_id": "2024_01_PIT_BAL",
                "play_id": 10,
                "posteam": "PIT",
                "defteam": "BAL",
                "pass": 0.0,
                "sack": 0.0,
                "qb_hit": 0.0,
            }
        ]
    )
    ratings = compute_pass_rush_elo_ratings(pbp)
    assert len(ratings) == 0


def test_credited_pressure_counts_gives_full_and_half_sack_credit():
    pbp = pd.DataFrame(
        [
            {
                "sack_player_id": "A",
                "sack_player_name": "Rusher A",
                "half_sack_1_player_id": None,
                "half_sack_1_player_name": None,
                "half_sack_2_player_id": None,
                "half_sack_2_player_name": None,
                "qb_hit_1_player_id": None,
                "qb_hit_1_player_name": None,
                "qb_hit_2_player_id": None,
                "qb_hit_2_player_name": None,
            },
            {
                "sack_player_id": None,
                "sack_player_name": None,
                "half_sack_1_player_id": "B",
                "half_sack_1_player_name": "Rusher B",
                "half_sack_2_player_id": "C",
                "half_sack_2_player_name": "Rusher C",
                "qb_hit_1_player_id": None,
                "qb_hit_1_player_name": None,
                "qb_hit_2_player_id": None,
                "qb_hit_2_player_name": None,
            },
            {
                "sack_player_id": None,
                "sack_player_name": None,
                "half_sack_1_player_id": None,
                "half_sack_1_player_name": None,
                "half_sack_2_player_id": None,
                "half_sack_2_player_name": None,
                "qb_hit_1_player_id": "A",
                "qb_hit_1_player_name": "Rusher A",
                "qb_hit_2_player_id": None,
                "qb_hit_2_player_name": None,
            },
        ]
    )
    counts = credited_pressure_counts(pbp).set_index("player_id")

    assert counts.loc["A", "sacks"] == 1.0
    assert counts.loc["A", "qb_hits"] == 1
    assert counts.loc["B", "sacks"] == 0.5
    assert counts.loc["C", "sacks"] == 0.5
