import pandas as pd

from src.features.player_status import (
    current_injury_status,
    current_team,
    player_status_snapshot,
)


def _rosters(rows):
    return pd.DataFrame(
        [
            {
                "season": season,
                "week": week,
                "team": team,
                "gsis_id": gsis_id,
                "full_name": gsis_id,
                "position": "WR",
                "status": status,
                "status_description_abbr": status,
            }
            for season, week, team, gsis_id, status in rows
        ]
    )


_INJURY_COLUMNS = ["season", "week", "team", "gsis_id", "report_status", "report_primary_injury", "practice_status", "date_modified"]


def _injuries(rows):
    if not rows:
        return pd.DataFrame(columns=_INJURY_COLUMNS)
    return pd.DataFrame(
        [
            {
                "season": season,
                "week": week,
                "team": team,
                "gsis_id": gsis_id,
                "report_status": report_status,
                "report_primary_injury": "Ankle",
                "practice_status": "Limited Participation",
                "date_modified": None,
            }
            for season, week, team, gsis_id, report_status in rows
        ]
    )


def test_current_team_resolves_to_most_recent_row_at_or_before_the_week():
    rosters = _rosters(
        [
            (2024, 1, "GB", "P1", "ACT"),
            (2024, 3, "NYG", "P1", "ACT"),
            (2024, 10, "WAS", "P1", "TRD"),
        ]
    )
    result = current_team(rosters, season=2024, as_of_week=7)
    row = result[result["gsis_id"] == "P1"].iloc[0]
    assert row["current_team"] == "NYG"  # week-10 row is after as_of_week=7, shouldn't be picked
    assert row["roster_as_of_week"] == 3


def test_current_team_reflects_a_trade_once_it_happens():
    rosters = _rosters(
        [
            (2024, 3, "NYG", "P1", "ACT"),
            (2024, 10, "WAS", "P1", "TRD"),
        ]
    )
    result = current_team(rosters, season=2024, as_of_week=12)
    row = result[result["gsis_id"] == "P1"].iloc[0]
    assert row["current_team"] == "WAS"
    assert row["roster_as_of_week"] == 10


def test_current_team_ignores_a_different_season():
    rosters = _rosters(
        [
            (2023, 5, "GB", "P1", "ACT"),
            (2024, 3, "NYG", "P1", "ACT"),
        ]
    )
    result = current_team(rosters, season=2024, as_of_week=12)
    row = result[result["gsis_id"] == "P1"].iloc[0]
    assert row["current_team"] == "NYG"


def test_current_injury_status_resolves_to_most_recent_report():
    injuries = _injuries(
        [
            (2024, 5, "NYG", "P1", "Questionable"),
            (2024, 6, "NYG", "P1", "Out"),
        ]
    )
    result = current_injury_status(injuries, season=2024, as_of_week=8)
    row = result[result["gsis_id"] == "P1"].iloc[0]
    assert row["report_status"] == "Out"
    assert row["injury_as_of_week"] == 6


def test_player_status_snapshot_gives_no_report_row_for_a_healthy_player():
    rosters = _rosters([(2024, 3, "NYG", "P1", "ACT")])
    injuries = _injuries([])  # no injury history at all
    result = player_status_snapshot(rosters, injuries, season=2024, as_of_week=8)
    row = result[result["gsis_id"] == "P1"].iloc[0]
    assert row["current_team"] == "NYG"
    assert pd.isna(row["report_status"])


def test_player_status_snapshot_combines_trade_and_injury_state():
    rosters = _rosters(
        [
            (2024, 3, "NYG", "P1", "ACT"),
            (2024, 10, "WAS", "P1", "TRD"),
        ]
    )
    injuries = _injuries([(2024, 12, "WAS", "P1", "Questionable")])
    result = player_status_snapshot(rosters, injuries, season=2024, as_of_week=13)
    row = result[result["gsis_id"] == "P1"].iloc[0]
    assert row["current_team"] == "WAS"
    assert row["report_status"] == "Questionable"
