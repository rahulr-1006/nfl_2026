import pandas as pd
import pytest

from src.store.schema import Market, Side
from src.store.settlement import (
    GameResult,
    Outcome,
    build_results_index,
    settle,
    settle_snapshots,
)

# LAC beat KC 27-20 (favorite home team wins outright)
WIN_RESULT = GameResult(event_id="2026_01_KC_LAC", home_score=27, away_score=20)
# NFL tie: home 20, away 20
TIE_RESULT = GameResult(event_id="2026_01_IND_HOU", home_score=20, away_score=20)


# --- moneyline ---


def test_moneyline_home_win():
    assert settle(Market.MONEYLINE, Side.HOME, None, WIN_RESULT) == Outcome.WIN


def test_moneyline_away_loss():
    assert settle(Market.MONEYLINE, Side.AWAY, None, WIN_RESULT) == Outcome.LOSS


def test_moneyline_tie_is_push_for_both_sides():
    assert settle(Market.MONEYLINE, Side.HOME, None, TIE_RESULT) == Outcome.PUSH
    assert settle(Market.MONEYLINE, Side.AWAY, None, TIE_RESULT) == Outcome.PUSH


def test_moneyline_rejects_over_under_side():
    with pytest.raises(ValueError, match="HOME or AWAY"):
        settle(Market.MONEYLINE, Side.OVER, None, WIN_RESULT)


# --- spread ---


def test_spread_home_favorite_covers():
    # home -4.5, won by 7 -> covers
    assert settle(Market.SPREAD, Side.HOME, -4.5, WIN_RESULT) == Outcome.WIN


def test_spread_away_underdog_fails_to_cover():
    # away +4.5, lost by 7 -> does not cover
    assert settle(Market.SPREAD, Side.AWAY, 4.5, WIN_RESULT) == Outcome.LOSS


def test_spread_exact_push():
    # home -7, won by exactly 7 -> push
    assert settle(Market.SPREAD, Side.HOME, -7.0, WIN_RESULT) == Outcome.PUSH
    assert settle(Market.SPREAD, Side.AWAY, 7.0, WIN_RESULT) == Outcome.PUSH


def test_spread_requires_a_line():
    with pytest.raises(ValueError, match="requires a line"):
        settle(Market.SPREAD, Side.HOME, None, WIN_RESULT)


def test_spread_rejects_over_under_side():
    with pytest.raises(ValueError, match="HOME or AWAY"):
        settle(Market.SPREAD, Side.OVER, -4.5, WIN_RESULT)


# --- total ---


def test_total_over_wins():
    # total score 47, line 43.5 -> over wins
    assert settle(Market.TOTAL, Side.OVER, 43.5, WIN_RESULT) == Outcome.WIN
    assert settle(Market.TOTAL, Side.UNDER, 43.5, WIN_RESULT) == Outcome.LOSS


def test_total_under_wins():
    assert settle(Market.TOTAL, Side.UNDER, 50.5, WIN_RESULT) == Outcome.WIN
    assert settle(Market.TOTAL, Side.OVER, 50.5, WIN_RESULT) == Outcome.LOSS


def test_total_exact_push():
    assert settle(Market.TOTAL, Side.OVER, 47.0, WIN_RESULT) == Outcome.PUSH
    assert settle(Market.TOTAL, Side.UNDER, 47.0, WIN_RESULT) == Outcome.PUSH


def test_total_requires_a_line():
    with pytest.raises(ValueError, match="requires a line"):
        settle(Market.TOTAL, Side.OVER, None, WIN_RESULT)


def test_total_rejects_home_away_side():
    with pytest.raises(ValueError, match="OVER or UNDER"):
        settle(Market.TOTAL, Side.HOME, 43.5, WIN_RESULT)


# --- build_results_index ---


def test_build_results_index_excludes_unplayed_games():
    schedule = pd.DataFrame(
        [
            {"game_id": "2026_01_KC_LAC", "home_score": 27.0, "away_score": 20.0},
            {"game_id": "2026_02_NE_SEA", "home_score": None, "away_score": None},
        ]
    )
    index = build_results_index(schedule)
    assert list(index.keys()) == ["2026_01_KC_LAC"]
    assert index["2026_01_KC_LAC"] == GameResult(event_id="2026_01_KC_LAC", home_score=27, away_score=20)


# --- settle_snapshots ---


def _snapshot_row(event_id, market, side, line):
    return {"event_id": event_id, "market": market.value, "side": side.value, "line": line}


def test_settle_snapshots_grades_completed_games():
    schedule = pd.DataFrame(
        [{"game_id": "2026_01_KC_LAC", "home_score": 27.0, "away_score": 20.0}]
    )
    snapshots = pd.DataFrame(
        [
            _snapshot_row("2026_01_KC_LAC", Market.MONEYLINE, Side.HOME, None),
            _snapshot_row("2026_01_KC_LAC", Market.SPREAD, Side.HOME, -4.5),
        ]
    )
    graded = settle_snapshots(snapshots, schedule)
    assert list(graded["outcome"]) == ["win", "win"]


def test_settle_snapshots_leaves_unplayed_games_as_none_not_dropped():
    schedule = pd.DataFrame(
        [{"game_id": "2026_01_KC_LAC", "home_score": None, "away_score": None}]
    )
    snapshots = pd.DataFrame([_snapshot_row("2026_01_KC_LAC", Market.MONEYLINE, Side.HOME, None)])

    graded = settle_snapshots(snapshots, schedule)

    assert len(graded) == 1  # not dropped
    assert graded["outcome"].iloc[0] is None
