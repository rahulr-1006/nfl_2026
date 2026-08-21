import pandas as pd
import pytest

from src.model.elo import elo_win_probability
from src.model.individual_pass_rush_elo import (
    DEFAULT_INDIVIDUAL_BASE_PRESSURE_OFFSET,
    RUSH_POSITIONS,
    build_individual_pass_rush_frame,
    compute_individual_pass_rush_ratings,
)


def test_base_pressure_offset_recenters_expectation_to_the_measured_base_rate():
    # At rating parity (1500 vs 1500), the offset should make the expected
    # per-snap pressure probability land near the ~3.84% base rate it was
    # derived from, not 50%.
    expected = elo_win_probability(1500.0, 1500.0, DEFAULT_INDIVIDUAL_BASE_PRESSURE_OFFSET)
    assert expected == pytest.approx(0.0384, abs=1e-3)


# --- build_individual_pass_rush_frame ---


def _snap_row(pfr_player_id, pfr_game_id, position, defense_snaps):
    return {
        "pfr_player_id": pfr_player_id,
        "pfr_game_id": pfr_game_id,
        "position": position,
        "defense_snaps": defense_snaps,
        "game_id": "x",
        "season": 2024,
        "week": 1,
        "player": "x",
        "team": "PIT",
    }


def _pfr_row(pfr_player_id, pfr_game_id, pfr_player_name, def_pressures, season=2024, week=1, team="PIT"):
    return {
        "pfr_player_id": pfr_player_id,
        "pfr_game_id": pfr_game_id,
        "pfr_player_name": pfr_player_name,
        "def_pressures": def_pressures,
        "game_id": "x",
        "season": season,
        "week": week,
        "team": team,
        "def_times_blitzed": 0,
        "def_times_hurried": 0,
        "def_times_hitqb": 0,
        "def_sacks": 0,
    }


def test_build_frame_keeps_only_real_rush_positions():
    snaps = pd.DataFrame(
        [
            _snap_row("A", "g1", "DE", 40),
            _snap_row("B", "g1", "CB", 60),  # not a rush position
        ]
    )
    pfr = pd.DataFrame([_pfr_row("A", "g1", "Rusher A", 3), _pfr_row("B", "g1", "Corner B", 0)])
    out = build_individual_pass_rush_frame(snaps, pfr)
    assert list(out["pfr_player_id"]) == ["A"]


def test_build_frame_drops_zero_snap_rows():
    snaps = pd.DataFrame([_snap_row("A", "g1", "DE", 0)])
    pfr = pd.DataFrame([_pfr_row("A", "g1", "Rusher A", 0)])
    out = build_individual_pass_rush_frame(snaps, pfr)
    assert out.empty


def test_build_frame_covers_every_position_in_rush_positions():
    # Every position this project claims to rate should actually survive
    # the filter -- a typo in RUSH_POSITIONS would silently drop a whole
    # position group without this.
    snaps = pd.DataFrame([_snap_row(f"P{i}", "g1", pos, 30) for i, pos in enumerate(RUSH_POSITIONS)])
    pfr = pd.DataFrame([_pfr_row(f"P{i}", "g1", f"Player {i}", 1) for i in range(len(RUSH_POSITIONS))])
    out = build_individual_pass_rush_frame(snaps, pfr)
    assert len(out) == len(RUSH_POSITIONS)


# --- compute_individual_pass_rush_ratings ---


def _player_game(pfr_player_id, season, week, pfr_game_id, defense_snaps, def_pressures, name="Rusher"):
    return {
        "pfr_player_id": pfr_player_id,
        "pfr_player_name": name,
        "season": season,
        "week": week,
        "pfr_game_id": pfr_game_id,
        "team": "PIT",
        "defense_snaps": defense_snaps,
        "def_pressures": def_pressures,
    }


def test_first_game_begins_at_initial_rating():
    df = pd.DataFrame([_player_game("A", 2024, 1, "g1", 40, 2)])
    ratings = compute_individual_pass_rush_ratings(df)
    assert ratings.iloc[0]["pre_individual_pass_rush_elo"] == 1500.0


def test_above_average_pressure_rate_raises_the_rating():
    # 40 snaps, 5 pressures -> 12.5% rate, well above the ~3.84% baseline.
    df = pd.DataFrame([_player_game("A", 2024, 1, "g1", 40, 5)])
    ratings = compute_individual_pass_rush_ratings(df)
    assert ratings.iloc[0]["post_individual_pass_rush_elo"] > 1500.0


def test_zero_pressures_lowers_the_rating():
    df = pd.DataFrame([_player_game("A", 2024, 1, "g1", 40, 0)])
    ratings = compute_individual_pass_rush_ratings(df)
    assert ratings.iloc[0]["post_individual_pass_rush_elo"] < 1500.0


def test_more_snaps_produces_a_larger_update_for_the_same_rate():
    # Same observed rate (10%), different snap counts -- more snaps should
    # move the rating further, since it's a batch of `defense_snaps`
    # per-snap updates, not one update regardless of sample size.
    small = compute_individual_pass_rush_ratings(pd.DataFrame([_player_game("A", 2024, 1, "g1", 10, 1)]))
    large = compute_individual_pass_rush_ratings(pd.DataFrame([_player_game("B", 2024, 1, "g1", 40, 4)]))
    small_move = small.iloc[0]["post_individual_pass_rush_elo"] - 1500.0
    large_move = large.iloc[0]["post_individual_pass_rush_elo"] - 1500.0
    assert large_move > small_move > 0


def test_rating_carries_across_games_not_reset():
    df = pd.DataFrame(
        [
            _player_game("A", 2024, 1, "g1", 40, 5),
            _player_game("A", 2024, 2, "g2", 35, 1),
        ]
    )
    ratings = compute_individual_pass_rush_ratings(df)
    game1_post = ratings.iloc[0]["post_individual_pass_rush_elo"]
    game2_pre = ratings.iloc[1]["pre_individual_pass_rush_elo"]
    assert game2_pre == pytest.approx(game1_post)


def test_games_are_processed_in_chronological_order():
    df = pd.DataFrame(
        [
            _player_game("A", 2024, 3, "g3", 40, 5),
            _player_game("A", 2024, 1, "g1", 40, 5),
            _player_game("A", 2024, 2, "g2", 40, 5),
        ]
    )
    ratings = compute_individual_pass_rush_ratings(df)
    assert list(ratings["week"]) == [1, 2, 3]


def test_different_players_rate_independently():
    df = pd.DataFrame(
        [
            _player_game("A", 2024, 1, "g1", 40, 5),
            _player_game("B", 2024, 1, "g1", 40, 0),
        ]
    )
    ratings = compute_individual_pass_rush_ratings(df)
    a_row = ratings[ratings["pfr_player_id"] == "A"].iloc[0]
    b_row = ratings[ratings["pfr_player_id"] == "B"].iloc[0]
    assert a_row["post_individual_pass_rush_elo"] > 1500.0
    assert b_row["post_individual_pass_rush_elo"] < 1500.0
    # neither player's update leaked into the other's rating
    assert a_row["pre_individual_pass_rush_elo"] == 1500.0
    assert b_row["pre_individual_pass_rush_elo"] == 1500.0


def test_a_league_average_rate_holds_the_rating_roughly_steady():
    # A player whose observed rate matches the measured league baseline
    # (~3.84%) should see only a small move, not a big swing in either
    # direction -- confirms the offset is well-calibrated, same "check
    # the mean" discipline pass_rush_elo.py's own memory establishes.
    df = pd.DataFrame([_player_game("A", 2024, 1, "g1", 100, 4)])  # 4% observed, close to baseline
    ratings = compute_individual_pass_rush_ratings(df)
    assert abs(ratings.iloc[0]["post_individual_pass_rush_elo"] - 1500.0) < 10.0
