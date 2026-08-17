import pandas as pd
import pytest

from src.model.receiver_elo import compute_receiver_elo_ratings


def _pbp(plays):
    rows = [
        {
            "season": season,
            "week": week,
            "game_id": gid,
            "play_id": play_id,
            "defteam": defteam,
            "receiver_player_id": receiver_id,
            "receiver_player_name": receiver_id,
            "success": success,
        }
        for season, week, gid, play_id, defteam, receiver_id, success in plays
    ]
    return pd.DataFrame(rows)


def test_first_target_begins_at_initial_rating():
    pbp = _pbp([(2024, 1, "2024_01_KC_LAC", 10, "LAC", "Kelce", 1.0)])
    ratings = compute_receiver_elo_ratings(pbp)

    row = ratings.iloc[0]
    assert row["pre_receiver_elo"] == 1500.0
    assert row["pre_pass_defense_elo"] == 1500.0


def test_successful_target_raises_receiver_and_lowers_defense():
    pbp = _pbp([(2024, 1, "2024_01_KC_LAC", 10, "LAC", "Kelce", 1.0)])
    ratings = compute_receiver_elo_ratings(pbp)

    row = ratings.iloc[0]
    assert row["post_receiver_elo"] > row["pre_receiver_elo"]
    assert row["post_pass_defense_elo"] < row["pre_pass_defense_elo"]


def test_failed_target_lowers_receiver_and_raises_defense():
    pbp = _pbp([(2024, 1, "2024_01_KC_LAC", 10, "LAC", "Kelce", 0.0)])
    ratings = compute_receiver_elo_ratings(pbp)

    row = ratings.iloc[0]
    assert row["post_receiver_elo"] < row["pre_receiver_elo"]
    assert row["post_pass_defense_elo"] > row["pre_pass_defense_elo"]


def test_update_is_symmetric_zero_sum():
    pbp = _pbp([(2024, 1, "2024_01_KC_LAC", 10, "LAC", "Kelce", 1.0)])
    ratings = compute_receiver_elo_ratings(pbp)

    row = ratings.iloc[0]
    receiver_gain = row["post_receiver_elo"] - row["pre_receiver_elo"]
    defense_loss = row["pre_pass_defense_elo"] - row["post_pass_defense_elo"]
    assert receiver_gain == pytest.approx(defense_loss)


def test_rating_carries_across_plays_not_reset():
    pbp = _pbp(
        [
            (2024, 1, "2024_01_KC_LAC", 10, "LAC", "Kelce", 1.0),
            (2024, 1, "2024_01_KC_LAC", 40, "LAC", "Kelce", 1.0),
        ]
    )
    ratings = compute_receiver_elo_ratings(pbp)

    play1_post = ratings.iloc[0]["post_receiver_elo"]
    play2_pre = ratings.iloc[1]["pre_receiver_elo"]
    assert play2_pre == pytest.approx(play1_post)


def test_plays_are_processed_in_chronological_order_within_a_game():
    # Rows given out of play_id order -- the function must sort before
    # processing, or the second play's "pre" rating would be wrong.
    pbp = _pbp(
        [
            (2024, 1, "2024_01_KC_LAC", 40, "LAC", "Kelce", 1.0),
            (2024, 1, "2024_01_KC_LAC", 10, "LAC", "Kelce", 1.0),
        ]
    )
    ratings = compute_receiver_elo_ratings(pbp)

    assert list(ratings["play_id"]) == [10, 40]
    assert ratings.iloc[1]["pre_receiver_elo"] == pytest.approx(ratings.iloc[0]["post_receiver_elo"])


def test_different_receivers_and_defenses_tracked_independently():
    pbp = _pbp(
        [
            (2024, 1, "2024_01_KC_LAC", 10, "LAC", "Kelce", 1.0),
            (2024, 1, "2024_01_DEN_SF", 15, "SF", "Sutton", 0.0),
        ]
    )
    ratings = compute_receiver_elo_ratings(pbp)

    row2 = ratings.iloc[1]
    assert row2["pre_receiver_elo"] == 1500.0  # Sutton unaffected by Kelce's play
    assert row2["pre_pass_defense_elo"] == 1500.0  # SF defense unaffected by LAC's play


def test_rows_missing_a_recorded_target_are_excluded():
    pbp = pd.DataFrame(
        [
            {
                "season": 2024,
                "week": 1,
                "game_id": "2024_01_KC_LAC",
                "play_id": 10,
                "defteam": "LAC",
                "receiver_player_id": None,
                "receiver_player_name": None,
                "success": 0.0,
            },
            {
                "season": 2024,
                "week": 1,
                "game_id": "2024_01_KC_LAC",
                "play_id": 40,
                "defteam": "LAC",
                "receiver_player_id": "Kelce",
                "receiver_player_name": "Kelce",
                "success": 1.0,
            },
        ]
    )
    ratings = compute_receiver_elo_ratings(pbp)
    assert len(ratings) == 1
    assert ratings.iloc[0]["play_id"] == 40
