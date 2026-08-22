from datetime import UTC, datetime

import pandas as pd

from src.backtest.team_total_props import (
    build_team_total_lines,
    fit_team_total_residual_std,
    team_total_over_indicator,
)

CAPTURE = datetime(2024, 9, 5, 12, 0, tzinfo=UTC)


def _prop_row(event_id, player_name, side, line, book="pinnacle", capture_time=CAPTURE):
    return {
        "event_id": event_id,
        "book": book,
        "market": "player_prop",
        "prop_stat": "rushing_yards",
        "player_name": player_name,
        "side": side,
        "line": line,
        "capture_time": capture_time,
    }


def _stats_row(game_id, player_display_name, team, rushing_yards):
    return {"game_id": game_id, "player_display_name": player_display_name, "team": team, "rushing_yards": rushing_yards}


def test_build_team_total_lines_sums_every_matched_players_own_line():
    props = pd.DataFrame(
        [
            _prop_row("2024_01_KC_BAL", "Isiah Pacheco", "over", 60.5),
            _prop_row("2024_01_KC_BAL", "Isiah Pacheco", "under", 60.5),
            _prop_row("2024_01_KC_BAL", "Clyde Edwards-Helaire", "over", 15.5),
            _prop_row("2024_01_KC_BAL", "Clyde Edwards-Helaire", "under", 15.5),
        ]
    )
    stats = pd.DataFrame(
        [
            _stats_row("2024_01_KC_BAL", "Isiah Pacheco", "KC", 70.0),
            _stats_row("2024_01_KC_BAL", "Clyde Edwards-Helaire", "KC", 20.0),
        ]
    )
    out = build_team_total_lines(props, stats, "rushing_yards")
    assert len(out) == 1
    row = out.iloc[0]
    assert row["event_id"] == "2024_01_KC_BAL"
    assert row["team"] == "KC"
    assert row["implied_team_total_line"] == 76.0  # 60.5 + 15.5
    assert row["actual_team_total"] == 90.0  # 70 + 20


def test_build_team_total_lines_only_uses_over_side_not_double_counted():
    props = pd.DataFrame(
        [
            _prop_row("2024_01_KC_BAL", "Isiah Pacheco", "over", 60.5),
            _prop_row("2024_01_KC_BAL", "Isiah Pacheco", "under", 60.5),
        ]
    )
    stats = pd.DataFrame([_stats_row("2024_01_KC_BAL", "Isiah Pacheco", "KC", 70.0)])
    out = build_team_total_lines(props, stats, "rushing_yards")
    assert out.iloc[0]["implied_team_total_line"] == 60.5


def test_build_team_total_lines_drops_unmatched_players():
    props = pd.DataFrame(
        [
            _prop_row("2024_01_KC_BAL", "Isiah Pacheco", "over", 60.5),
            _prop_row("2024_01_KC_BAL", "Some Unmatched Guy", "over", 10.5),
        ]
    )
    stats = pd.DataFrame([_stats_row("2024_01_KC_BAL", "Isiah Pacheco", "KC", 70.0)])
    out = build_team_total_lines(props, stats, "rushing_yards")
    assert len(out) == 1
    assert out.iloc[0]["implied_team_total_line"] == 60.5


def test_build_team_total_lines_matches_names_despite_punctuation_differences():
    # book "AJ Brown" vs nflverse "A.J. Brown" -- the exact real mismatch
    # prop_settlement.py was built against.
    props = pd.DataFrame([_prop_row("2024_01_PHI_GB", "AJ Brown", "over", 5.5)])
    stats = pd.DataFrame([_stats_row("2024_01_PHI_GB", "A.J. Brown", "PHI", 6.0)])
    out = build_team_total_lines(props, stats, "rushing_yards")
    assert len(out) == 1
    assert out.iloc[0]["implied_team_total_line"] == 5.5


def test_build_team_total_lines_keeps_latest_capture_when_a_player_has_multiple_polls():
    props = pd.DataFrame(
        [
            _prop_row("2024_01_KC_BAL", "Isiah Pacheco", "over", 55.5, capture_time=datetime(2024, 9, 3, tzinfo=UTC)),
            _prop_row("2024_01_KC_BAL", "Isiah Pacheco", "over", 60.5, capture_time=datetime(2024, 9, 5, tzinfo=UTC)),
        ]
    )
    stats = pd.DataFrame([_stats_row("2024_01_KC_BAL", "Isiah Pacheco", "KC", 70.0)])
    out = build_team_total_lines(props, stats, "rushing_yards")
    assert out.iloc[0]["implied_team_total_line"] == 60.5


def test_build_team_total_lines_returns_empty_frame_when_no_matching_stat():
    props = pd.DataFrame([_prop_row("2024_01_KC_BAL", "Isiah Pacheco", "over", 60.5)])
    stats = pd.DataFrame([_stats_row("2024_01_KC_BAL", "Isiah Pacheco", "KC", 70.0)])
    out = build_team_total_lines(props, stats, "passing_yards")
    assert out.empty
    assert list(out.columns) == ["event_id", "team", "implied_team_total_line", "actual_team_total"]


def test_fit_team_total_residual_std_measures_real_bias_and_spread():
    team_totals = pd.DataFrame(
        {
            "implied_team_total_line": [80.0, 80.0, 80.0, 80.0],
            "actual_team_total": [90.0, 70.0, 85.0, 75.0],  # residuals: 10, -10, 5, -5 -> mean 0, std ~9.13
        }
    )
    mean_resid, std_resid = fit_team_total_residual_std(team_totals)
    assert mean_resid == 0.0
    assert std_resid > 0


def test_fit_team_total_residual_std_detects_a_real_bias():
    team_totals = pd.DataFrame(
        {"implied_team_total_line": [80.0, 80.0], "actual_team_total": [90.0, 100.0]}  # always +10/+20 over the line
    )
    mean_resid, _ = fit_team_total_residual_std(team_totals)
    assert mean_resid == 15.0


def test_team_total_over_indicator_matches_actual_vs_line():
    team_totals = pd.DataFrame(
        {"implied_team_total_line": [80.0, 80.0, 80.0], "actual_team_total": [90.0, 70.0, 80.0]}
    )
    result = team_total_over_indicator(team_totals)
    assert list(result) == [True, False, False]  # exactly-equal does not count as "over"
