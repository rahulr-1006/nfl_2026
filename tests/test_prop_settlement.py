import pandas as pd
import pytest

from src.store.prop_settlement import (
    build_player_stats_index,
    settle_prop,
    settle_prop_snapshots,
)
from src.store.schema import Side
from src.store.settlement import Outcome

PLAYER_STATS = pd.DataFrame(
    [
        {
            "game_id": "2026_01_KC_LAC",
            "player_display_name": "Patrick Mahomes",
            "passing_yards": 275.0,
            "passing_tds": 2.0,
            "receptions": None,
        },
        {
            "game_id": "2026_01_KC_LAC",
            "player_display_name": "Travis Kelce",
            "passing_yards": None,
            "passing_tds": None,
            "receptions": 6.0,
        },
    ]
)


# --- settle_prop ---


def test_settle_prop_over_wins_when_actual_exceeds_line():
    assert settle_prop(Side.OVER, 250.5, 275.0) == Outcome.WIN


def test_settle_prop_over_loses_when_actual_is_under_line():
    assert settle_prop(Side.OVER, 250.5, 200.0) == Outcome.LOSS


def test_settle_prop_under_wins_when_actual_is_below_line():
    assert settle_prop(Side.UNDER, 250.5, 200.0) == Outcome.WIN


def test_settle_prop_exact_push_on_a_whole_number_line():
    # receptions lines often land on whole numbers, unlike spread/total
    assert settle_prop(Side.OVER, 6.0, 6.0) == Outcome.PUSH
    assert settle_prop(Side.UNDER, 6.0, 6.0) == Outcome.PUSH


def test_settle_prop_rejects_non_over_under_side():
    with pytest.raises(ValueError, match="OVER or UNDER"):
        settle_prop(Side.HOME, 250.5, 275.0)


# --- build_player_stats_index ---


def test_build_player_stats_index_keys_by_game_and_player():
    index = build_player_stats_index(PLAYER_STATS)
    assert index[("2026_01_KC_LAC", "Patrick Mahomes")]["passing_yards"] == 275.0
    assert index[("2026_01_KC_LAC", "Travis Kelce")]["receptions"] == 6.0


# --- settle_prop_snapshots ---


def _prop_row(event_id, player_name, prop_stat, side, line):
    return {
        "event_id": event_id,
        "player_name": player_name,
        "prop_stat": prop_stat,
        "side": side.value,
        "line": line,
    }


def test_settle_prop_snapshots_grades_matched_players():
    snapshots = pd.DataFrame(
        [
            _prop_row("2026_01_KC_LAC", "Patrick Mahomes", "passing_yards", Side.OVER, 250.5),
            _prop_row("2026_01_KC_LAC", "Travis Kelce", "receptions", Side.UNDER, 7.5),
        ]
    )
    graded = settle_prop_snapshots(snapshots, PLAYER_STATS)
    assert list(graded["outcome"]) == ["win", "win"]


def test_settle_prop_snapshots_leaves_unmatched_player_as_none_not_dropped():
    snapshots = pd.DataFrame([_prop_row("2026_01_KC_LAC", "Some Backup QB", "passing_yards", Side.OVER, 50.5)])
    graded = settle_prop_snapshots(snapshots, PLAYER_STATS)
    assert len(graded) == 1
    assert graded["outcome"].iloc[0] is None


def test_settle_prop_snapshots_leaves_missing_stat_value_as_none():
    # Mahomes has no receptions row (NaN) -- he's a real player in this
    # game, just not one who logged this stat, which must not be
    # silently graded rather than left unsettled.
    snapshots = pd.DataFrame([_prop_row("2026_01_KC_LAC", "Patrick Mahomes", "receptions", Side.OVER, 0.5)])
    graded = settle_prop_snapshots(snapshots, PLAYER_STATS)
    assert graded["outcome"].iloc[0] is None
