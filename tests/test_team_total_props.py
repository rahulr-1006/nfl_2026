from datetime import UTC, datetime

import pandas as pd
import pytest

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


# --- lift derivation: the constants must be reproducible from data ----------


def _outcome_snaps(event_id, home_price, away_price, capture, kickoff):
    from src.store.schema import Market, OddsSnapshot, Side
    return [
        OddsSnapshot.from_american(
            capture_time=capture, event_id=event_id, season=2024, week=1,
            home_team="KC", away_team="LAC", event_start_time=kickoff,
            book="pinnacle", market=Market.MONEYLINE, side=side, price_american=price,
        )
        for side, price in ((Side.HOME, home_price), (Side.AWAY, away_price))
    ]


def test_build_team_outcomes_emits_both_sides_with_complementary_results():
    from datetime import UTC, datetime, timedelta

    from src.backtest.team_total_props import build_team_outcomes

    ko = datetime(2024, 9, 8, 17, 0, tzinfo=UTC)
    snaps = _outcome_snaps("2024_01_LAC_KC", -200, 170, ko - timedelta(hours=1), ko)
    df = pd.DataFrame([s.model_dump() for s in snaps])
    df["market"] = df["market"].map(lambda m: getattr(m, "value", m))
    df["side"] = df["side"].map(lambda s: getattr(s, "value", s))
    sched = pd.DataFrame([{"game_id": "2024_01_LAC_KC", "home_team": "KC", "away_team": "LAC",
                           "home_score": 27, "away_score": 20, "season": 2024}])

    out = build_team_outcomes(df, sched)
    assert len(out) == 2
    assert set(out.team) == {"KC", "LAC"}
    # Exactly one winner, and the devigged probabilities sum to 1.
    assert out.team_won.sum() == 1
    assert out[out.team == "KC"].team_won.iloc[0] == 1
    assert out.team_market_prob.sum() == pytest.approx(1.0, abs=1e-9)


def test_build_team_outcomes_drops_games_with_no_result():
    """An unplayed game has no `team_won`; including it would silently grade
    every pending game as a loss."""
    from datetime import UTC, datetime, timedelta

    from src.backtest.team_total_props import build_team_outcomes

    ko = datetime(2026, 9, 10, 17, 0, tzinfo=UTC)
    snaps = _outcome_snaps("2026_01_LAC_KC", -200, 170, ko - timedelta(hours=1), ko)
    df = pd.DataFrame([s.model_dump() for s in snaps])
    df["market"] = df["market"].map(lambda m: getattr(m, "value", m))
    df["side"] = df["side"].map(lambda s: getattr(s, "value", s))
    sched = pd.DataFrame([{"game_id": "2026_01_LAC_KC", "home_team": "KC", "away_team": "LAC",
                           "home_score": None, "away_score": None, "season": 2026}])
    assert build_team_outcomes(df, sched).empty


def test_fit_lift_by_bucket_recovers_a_planted_correlation():
    """Independent legs give lift ~1.0; a planted co-occurrence gives lift > 1.
    Without this the constants the live scanner prices with are unfalsifiable."""
    from src.backtest.team_total_props import fit_team_total_lift_by_bucket

    # 200 underdog team-games. In HALF of them the team both wins and goes over,
    # which is far more co-occurrence than independence would produce.
    n = 200
    won = [1] * 100 + [0] * 100
    over = [1] * 100 + [0] * 100          # perfectly coupled -> lift ~2.0
    totals = pd.DataFrame({
        "event_id": [f"g{i}" for i in range(n)], "team": ["KC"] * n,
        "implied_team_total_line": [50.0] * n,
        "actual_team_total": [60.0 if o else 40.0 for o in over],
    })
    outcomes = pd.DataFrame({
        "event_id": [f"g{i}" for i in range(n)], "team": ["KC"] * n,
        "team_market_prob": [0.30] * n, "team_won": won, "season": [2024] * n,
    })

    class _Stub:
        @staticmethod
        def build(*_a, **_k):
            return totals

    import src.backtest.team_total_props as mod
    real = mod.build_team_total_lines
    mod.build_team_total_lines = lambda *a, **k: totals
    try:
        got = fit_team_total_lift_by_bucket(pd.DataFrame(), pd.DataFrame(), outcomes, "rushing_yards")
    finally:
        mod.build_team_total_lines = real

    under = got[got.bucket == "underdog"]
    assert not under.empty
    assert float(under.lift.iloc[0]) > 1.5      # planted coupling is detected
    assert int(under["n"].iloc[0]) == n


def test_fit_lift_by_bucket_on_empty_inputs_is_empty_not_a_crash():
    from src.backtest.team_total_props import fit_team_total_lift_by_bucket

    out = fit_team_total_lift_by_bucket(
        pd.DataFrame(), pd.DataFrame(),
        pd.DataFrame(columns=["event_id", "team", "team_market_prob", "team_won", "season"]),
        "rushing_yards",
    )
    assert out.empty
