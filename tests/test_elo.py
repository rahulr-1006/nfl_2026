import pandas as pd
import pytest

from src.model.elo import (
    DEFAULT_HOME_FIELD_ADVANTAGE,
    canonical_team,
    compute_team_elo_ratings,
    elo_win_probability,
    mov_multiplier,
    update_elo,
)

# --- elo_win_probability ---


def test_equal_ratings_no_hfa_is_a_coin_flip():
    assert elo_win_probability(1500, 1500, 0) == pytest.approx(0.5)


def test_400_point_gap_is_the_classic_10_to_1_elo_property():
    # a defining property of the logistic Elo transform: exactly 400
    # rating points apart gives a 10:1 win-probability ratio
    assert elo_win_probability(1900, 1500, 0) == pytest.approx(10 / 11)


def test_home_field_advantage_shifts_probability_toward_home():
    even = elo_win_probability(1500, 1500, 0)
    with_hfa = elo_win_probability(1500, 1500, DEFAULT_HOME_FIELD_ADVANTAGE)
    assert with_hfa > even


# --- mov_multiplier ---


def test_mov_multiplier_is_one_for_a_tie():
    # margin=0 must not zero out a tie's rating update -- the raw
    # K*(S-E) term alone should still move ratings on a tie.
    assert mov_multiplier(0, 100) == 1.0


def test_mov_multiplier_increases_with_margin():
    small = mov_multiplier(3, 0)
    big = mov_multiplier(21, 0)
    assert big > small


def test_mov_multiplier_dampens_for_a_big_favorite_blowout():
    # same margin, but a huge favorite (elo_diff_of_winner large) gets
    # less credit per point of margin than a team that was an underdog
    underdog_win = mov_multiplier(14, -100)
    favorite_blowout = mov_multiplier(14, 400)
    assert favorite_blowout < underdog_win


# --- update_elo ---


def test_update_elo_is_zero_sum():
    new_home, new_away = update_elo(1500, 1500, 24, 17, home_field_advantage=0)
    assert (new_home - 1500) == pytest.approx(-(new_away - 1500))


def test_update_elo_home_win_increases_home_rating():
    new_home, new_away = update_elo(1500, 1500, 24, 17, home_field_advantage=0)
    assert new_home > 1500
    assert new_away < 1500


def test_update_elo_upset_moves_more_than_expected_win():
    # a big underdog winning should move ratings more than an equally
    # rated team winning by the same margin
    _, underdog_away_after = update_elo(1700, 1500, 17, 24, home_field_advantage=0)  # away was a big underdog, won
    _, even_away_after = update_elo(1500, 1500, 17, 24, home_field_advantage=0)  # away was even, won same margin
    underdog_gain = underdog_away_after - 1500
    even_gain = even_away_after - 1500
    assert underdog_gain > even_gain


def test_update_elo_tie_moves_favorite_down_and_underdog_up():
    new_home, new_away = update_elo(1700, 1500, 20, 20, home_field_advantage=0)
    assert new_home < 1700
    assert new_away > 1500


# --- canonical_team ---


def test_canonical_team_maps_relocated_franchises():
    assert canonical_team("SD") == "LAC"
    assert canonical_team("OAK") == "LV"
    assert canonical_team("STL") == "LA"


def test_canonical_team_passes_through_unmapped_abbrs():
    assert canonical_team("KC") == "KC"


# --- compute_team_elo_ratings ---


def _schedule(games):
    rows = [
        {"game_id": gid, "season": season, "gameday": day, "home_team": home, "away_team": away, "home_score": hs, "away_score": aws}
        for gid, season, day, home, away, hs, aws in games
    ]
    return pd.DataFrame(rows)


def test_compute_team_elo_ratings_first_game_starts_at_initial_rating():
    schedule = _schedule([("2024_01_KC_LAC", 2024, "2024-09-08", "KC", "LAC", 27, 20)])
    ratings = compute_team_elo_ratings(schedule)
    row = ratings.iloc[0]
    assert row["home_pre_elo"] == 1500.0
    assert row["away_pre_elo"] == 1500.0
    assert row["home_post_elo"] > 1500.0  # KC won, rating should have moved up


def test_compute_team_elo_ratings_second_game_uses_updated_rating_not_reset():
    # KC wins game 1, then plays again in week 2 -- its pre-elo for game 2
    # must be its post-game-1 rating, not reset to 1500.
    schedule = _schedule(
        [
            ("2024_01_KC_LAC", 2024, "2024-09-08", "KC", "LAC", 27, 20),
            ("2024_02_DEN_KC", 2024, "2024-09-15", "KC", "DEN", 24, 17),
        ]
    )
    ratings = compute_team_elo_ratings(schedule)
    game1_kc_post = ratings.iloc[0]["home_post_elo"]
    game2_kc_pre = ratings.iloc[1]["home_pre_elo"]
    assert game2_kc_pre == pytest.approx(game1_kc_post)
    assert game2_kc_pre > 1500.0


def test_compute_team_elo_ratings_carries_a_relocated_franchise_through():
    # SD (2015) and LAC (2017) are the same franchise -- SD's post-game
    # rating must be what LAC's next game's pre-rating starts from, not a
    # fresh 1500 for a "new" team called LAC.
    schedule = _schedule(
        [
            ("2015_01_SD_KC", 2015, "2015-09-13", "SD", "KC", 33, 3),  # SD blows out KC
            ("2017_01_LAC_DEN", 2017, "2017-09-11", "LAC", "DEN", 24, 21),
        ]
    )
    ratings = compute_team_elo_ratings(schedule, season_reversion=0.0)  # isolate the alias behavior from reversion
    sd_post = ratings.iloc[0]["home_post_elo"]
    lac_pre = ratings.iloc[1]["home_pre_elo"]
    assert lac_pre == pytest.approx(sd_post)
    assert lac_pre > 1500.0  # the blowout win should still show up two seasons later


def test_compute_team_elo_ratings_applies_season_reversion():
    schedule = _schedule(
        [
            ("2024_01_KC_LAC", 2024, "2024-09-08", "KC", "LAC", 45, 3),  # KC blows out, rating moves well above 1500
            ("2025_01_KC_DEN", 2025, "2025-09-07", "KC", "DEN", 24, 20),
        ]
    )
    ratings = compute_team_elo_ratings(schedule, season_reversion=1 / 3)
    kc_post_2024 = ratings.iloc[0]["home_post_elo"]
    kc_pre_2025 = ratings.iloc[1]["home_pre_elo"]
    assert kc_pre_2025 < kc_post_2024  # pulled back toward 1500
    assert kc_pre_2025 > 1500.0  # but not fully reset -- only partial reversion


def test_compute_team_elo_ratings_ignores_unplayed_games():
    schedule = _schedule([("2024_01_KC_LAC", 2024, "2024-09-08", "KC", "LAC", None, None)])
    ratings = compute_team_elo_ratings(schedule)
    assert ratings.empty
