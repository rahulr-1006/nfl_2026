import pandas as pd
import pytest

from src.backtest.correlated_props import (
    bucket_favorite_strength,
    build_team_game_outcomes,
    correlated_edge,
    estimate_game_specific_joint_prob,
    measure_leg_correlation,
    measure_leg_correlation_by_bucket,
    naive_parlay_price,
)

# --- measure_leg_correlation ---


def test_perfectly_correlated_legs_give_a_lift_above_one_and_a_significant_p_value():
    # A and B always co-occur or both fail -- maximal positive correlation.
    a = pd.Series([True, True, False, False] * 20)
    b = pd.Series([True, True, False, False] * 20)
    result = measure_leg_correlation(a, b)
    assert result["lift"] > 1.5
    assert result["p_value"] < 0.05


def test_independent_legs_give_a_lift_near_one():
    # Deterministic interleave that makes A and B genuinely independent:
    # A cycles every 2 rows, B cycles every 4 -- every (A, B) combination
    # appears equally often, so no real association exists to detect.
    n = 400
    a = pd.Series([i % 2 == 0 for i in range(n)])
    b = pd.Series([(i // 2) % 2 == 0 for i in range(n)])
    result = measure_leg_correlation(a, b)
    assert result["lift"] == pytest.approx(1.0, abs=0.05)
    assert result["p_value"] > 0.05


def test_negatively_correlated_legs_give_a_lift_below_one():
    # A and B never co-occur -- maximal negative correlation.
    a = pd.Series([True, False] * 20)
    b = pd.Series([False, True] * 20)
    result = measure_leg_correlation(a, b)
    assert result["lift"] < 0.5


def test_probabilities_match_hand_computed_values():
    a = pd.Series([True, True, False, False])
    b = pd.Series([True, False, True, False])
    result = measure_leg_correlation(a, b)
    assert result["p_a"] == pytest.approx(0.5)
    assert result["p_b"] == pytest.approx(0.5)
    assert result["p_a_and_b"] == pytest.approx(0.25)
    assert result["independent_p_a_and_b"] == pytest.approx(0.25)
    assert result["lift"] == pytest.approx(1.0)


# --- build_team_game_outcomes ---


def _schedule_fixture():
    games = [
        # game_id, home, away, home_score, away_score, spread_line, total_line, home_qb, away_qb
        ("2024_01_A_B", "A", "B", 28, 14, -7.0, 45.0, "QB_A", "QB_B"),
    ]
    df = pd.DataFrame(
        games,
        columns=["game_id", "home_team", "away_team", "home_score", "away_score", "spread_line", "total_line", "home_qb_id", "away_qb_id"],
    )
    return df


def _player_stats_fixture():
    rows = [
        {"game_id": "2024_01_A_B", "team": "A", "player_id": "QB_A", "passing_tds": 3, "receiving_yards": 0, "rushing_yards": 0},
        {"game_id": "2024_01_A_B", "team": "A", "player_id": "WR_A1", "passing_tds": 0, "receiving_yards": 90, "rushing_yards": 0},
        {"game_id": "2024_01_A_B", "team": "A", "player_id": "RB_A1", "passing_tds": 0, "receiving_yards": 10, "rushing_yards": 60},
        {"game_id": "2024_01_A_B", "team": "B", "player_id": "QB_B", "passing_tds": 1, "receiving_yards": 0, "rushing_yards": 0},
        {"game_id": "2024_01_A_B", "team": "B", "player_id": "WR_B1", "passing_tds": 0, "receiving_yards": 40, "rushing_yards": 0},
        {"game_id": "2024_01_A_B", "team": "B", "player_id": "RB_B1", "passing_tds": 0, "receiving_yards": 5, "rushing_yards": 110},
    ]
    return pd.DataFrame(rows)


def test_team_game_outcomes_pools_home_and_away_perspectives():
    out = build_team_game_outcomes(_schedule_fixture(), _player_stats_fixture())
    assert len(out) == 2
    assert set(out["team"]) == {"A", "B"}


def test_team_won_is_correct_from_each_perspective():
    out = build_team_game_outcomes(_schedule_fixture(), _player_stats_fixture())
    a_row = out[out["team"] == "A"].iloc[0]
    b_row = out[out["team"] == "B"].iloc[0]
    assert a_row["team_won"] == True
    assert b_row["team_won"] == False


def test_team_covers_uses_each_teams_own_line_perspective():
    # margin = 28-14 = 14, home (A) spread_line=-7.0 -> 14 > -7.0 -> A covers.
    # away (B) perspective: team_margin=-14, covers_line=+7.0 -> -14 > 7.0 -> False.
    out = build_team_game_outcomes(_schedule_fixture(), _player_stats_fixture())
    a_row = out[out["team"] == "A"].iloc[0]
    b_row = out[out["team"] == "B"].iloc[0]
    assert a_row["team_covers"] == True
    assert b_row["team_covers"] == False


def test_game_over_is_shared_across_both_perspectives():
    # total_points = 28+14 = 42, total_line=45.0 -> under, not over
    out = build_team_game_outcomes(_schedule_fixture(), _player_stats_fixture())
    assert (out["game_over"] == False).all()


def test_qb_2plus_tds_uses_the_schedules_starting_qb_not_most_active_passer():
    out = build_team_game_outcomes(_schedule_fixture(), _player_stats_fixture())
    a_row = out[out["team"] == "A"].iloc[0]
    b_row = out[out["team"] == "B"].iloc[0]
    assert a_row["qb_2plus_tds"] == True  # QB_A threw 3
    assert b_row["qb_2plus_tds"] == False  # QB_B threw only 1


def test_leading_receiver_and_rusher_thresholds():
    out = build_team_game_outcomes(_schedule_fixture(), _player_stats_fixture())
    a_row = out[out["team"] == "A"].iloc[0]
    b_row = out[out["team"] == "B"].iloc[0]
    assert a_row["leading_receiver_75plus"] == True  # WR_A1 had 90
    assert a_row["leading_rusher_100plus"] == False  # RB_A1 had 60
    assert b_row["leading_receiver_75plus"] == False  # WR_B1 had 40
    assert b_row["leading_rusher_100plus"] == True  # RB_B1 had 110


# --- naive_parlay_price / correlated_edge ---


def test_naive_parlay_price_matches_hand_computed_value():
    # p_a=0.5, p_b=0.186174, vig=0.0575 -- hand-verified against the real
    # team_won x leading_rusher_100plus measurement before this test was written.
    price = naive_parlay_price(0.5, 0.186174, vig=0.0575)
    assert price == pytest.approx(9.6062, abs=1e-3)


def test_naive_parlay_price_is_shorter_than_the_no_vig_product_price():
    # Adding vig should always make the naive parlay price WORSE (lower)
    # than a no-vig product price -- that's what vig means.
    no_vig_price = 1 / (0.5 * 0.3)
    vigged_price = naive_parlay_price(0.5, 0.3, vig=0.05)
    assert vigged_price < no_vig_price


def test_naive_parlay_price_rejects_a_vig_that_pushes_probability_past_one():
    with pytest.raises(ValueError):
        naive_parlay_price(0.9, 0.9, vig=0.5)


def test_correlated_edge_gives_positive_ev_when_true_prob_exceeds_naive_implied():
    # Same real-data example: true joint prob (0.137345) is well above what
    # the naive vigged product implies (~0.104) -- must be a real positive edge.
    result = correlated_edge(0.5, 0.186174, 0.137345, vig=0.0575)
    assert result["edge"] > 0
    assert result["suggested_stake"] > 0
    assert result["true_prob"] > result["naive_implied_prob"]


def test_correlated_edge_gives_no_stake_when_legs_are_actually_independent():
    # If the true joint prob exactly matches the UN-vigged independence
    # product, the naive (vigged) price is worse than fair -- no edge, no stake.
    p_a, p_b = 0.5, 0.3
    true_independent_prob = p_a * p_b
    result = correlated_edge(p_a, p_b, true_independent_prob, vig=0.0575)
    assert result["edge"] < 0
    assert result["suggested_stake"] == 0.0


def test_correlated_edge_reuses_sizing_pys_own_ev_formula():
    result = correlated_edge(0.5, 0.186174, 0.137345, vig=0.0575)
    d = result["naive_parlay_price"]
    hand_ev = 0.137345 * (d - 1) - (1 - 0.137345)
    assert result["edge"] == pytest.approx(hand_ev)


# --- bucket_favorite_strength / measure_leg_correlation_by_bucket / estimate_game_specific_joint_prob ---


def test_bucket_favorite_strength_classifies_correctly():
    assert bucket_favorite_strength(0.20) == "underdog"
    assert bucket_favorite_strength(0.44) == "underdog"
    assert bucket_favorite_strength(0.45) == "narrow"
    assert bucket_favorite_strength(0.50) == "narrow"
    assert bucket_favorite_strength(0.55) == "favorite"
    assert bucket_favorite_strength(0.69) == "favorite"
    assert bucket_favorite_strength(0.70) == "heavy_favorite"
    assert bucket_favorite_strength(1.0) == "heavy_favorite"


def test_bucket_favorite_strength_rejects_out_of_range():
    with pytest.raises(ValueError):
        bucket_favorite_strength(1.5)


def test_measure_leg_correlation_by_bucket_splits_by_market_prob():
    # Two clearly separated groups: low market_prob rows have A and B always
    # co-occurring (or both failing); high market_prob rows have them
    # perfectly anti-correlated. The two buckets should show opposite lifts.
    n = 40
    a_lo = pd.Series([True, True, False, False] * (n // 4))
    b_lo = pd.Series([True, True, False, False] * (n // 4))
    p_lo = pd.Series([0.20] * n)

    a_hi = pd.Series([True, False] * (n // 2))
    b_hi = pd.Series([False, True] * (n // 2))
    p_hi = pd.Series([0.80] * n)

    a = pd.concat([a_lo, a_hi], ignore_index=True)
    b = pd.concat([b_lo, b_hi], ignore_index=True)
    p = pd.concat([p_lo, p_hi], ignore_index=True)

    table = measure_leg_correlation_by_bucket(a, b, p)
    underdog_lift = table[table["bucket"] == "underdog"]["lift"].iloc[0]
    heavy_fav_lift = table[table["bucket"] == "heavy_favorite"]["lift"].iloc[0]
    assert underdog_lift > 1.0
    assert heavy_fav_lift < 1.0


def test_estimate_game_specific_joint_prob_matches_hand_computation():
    result = estimate_game_specific_joint_prob(team_market_prob=0.30, historical_p_b=0.20, bucket_lift=1.5)
    assert result == pytest.approx(0.30 * 0.20 * 1.5)


def test_estimate_game_specific_joint_prob_is_clipped_to_a_valid_range():
    # lift=10 would push the raw product (0.5*0.5*10=2.5) far past 1.0 --
    # must clip to the tighter marginal (min(p_a, p_b) = 0.5), never exceed it.
    result = estimate_game_specific_joint_prob(team_market_prob=0.5, historical_p_b=0.5, bucket_lift=10.0)
    assert result == pytest.approx(0.5)
