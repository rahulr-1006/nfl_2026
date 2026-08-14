from datetime import UTC, datetime

import pandas as pd
import pytest

from src.collect.teams import build_team_name_map
from src.collect.transform import (
    MatchResult,
    TransformError,
    UnmatchedEventError,
    build_schedule_index,
    event_to_snapshots,
    match_event,
)
from src.store.schema import Market, Side

CAPTURE_TIME = datetime(2026, 8, 14, 21, 39, 14, tzinfo=UTC)


def _schedule():
    return pd.DataFrame(
        [
            {"season": 2026, "week": 1, "game_id": "2026_01_NE_SEA", "home_team": "SEA", "away_team": "NE"},
            {"season": 2026, "week": 2, "game_id": "2026_02_LA_ARI", "home_team": "ARI", "away_team": "LA"},
        ]
    )


def _teams():
    return pd.DataFrame(
        [
            {"team_abbr": "SEA", "team_name": "Seattle Seahawks"},
            {"team_abbr": "NE", "team_name": "New England Patriots"},
            {"team_abbr": "ARI", "team_name": "Arizona Cardinals"},
            {"team_abbr": "LA", "team_name": "Los Angeles Rams"},
            {"team_abbr": "LAR", "team_name": "Los Angeles Rams"},  # legacy alias, must not survive
        ]
    )


def _event(home="Seattle Seahawks", away="New England Patriots", bookmakers=None):
    return {
        "id": "abc123",
        "sport_key": "americanfootball_nfl",
        "commence_time": "2026-09-10T00:15:00Z",
        "home_team": home,
        "away_team": away,
        "bookmakers": bookmakers if bookmakers is not None else [_pinnacle_block(home, away)],
    }


def _pinnacle_block(home, away):
    return {
        "key": "pinnacle",
        "title": "Pinnacle",
        "markets": [
            {"key": "h2h", "outcomes": [{"name": away, "price": 177}, {"name": home, "price": -204}]},
            {
                "key": "spreads",
                "outcomes": [
                    {"name": away, "price": -119, "point": 4.5},
                    {"name": home, "price": 106, "point": -4.5},
                ],
            },
            {
                "key": "totals",
                "outcomes": [
                    {"name": "Over", "price": -117, "point": 43.5},
                    {"name": "Under", "price": 100, "point": 43.5},
                ],
            },
        ],
    }


def test_build_team_name_map_resolves_alias_duplicates():
    name_map = build_team_name_map(_schedule(), _teams())
    assert name_map["Los Angeles Rams"] == "LA"  # not LAR, since only LA appears in the schedule
    assert name_map["Seattle Seahawks"] == "SEA"
    assert len(name_map) == 4  # SEA, NE, ARI, LA -- LAR alias dropped


def test_match_event_success():
    schedule_index = build_schedule_index(_schedule())
    name_to_abbr = build_team_name_map(_schedule(), _teams())
    match = match_event("Seattle Seahawks", "New England Patriots", 2026, schedule_index, name_to_abbr)
    assert match == MatchResult(
        event_id="2026_01_NE_SEA", season=2026, week=1, home_abbr="SEA", away_abbr="NE"
    )


def test_match_event_unknown_team_name_raises():
    schedule_index = build_schedule_index(_schedule())
    name_to_abbr = build_team_name_map(_schedule(), _teams())
    with pytest.raises(UnmatchedEventError, match="unknown team name"):
        match_event("Not A Real Team", "New England Patriots", 2026, schedule_index, name_to_abbr)


def test_match_event_no_schedule_row_raises_distinct_message():
    # Both teams known, but this pairing/season isn't in the schedule (e.g. preseason).
    schedule_index = build_schedule_index(_schedule())
    name_to_abbr = build_team_name_map(_schedule(), _teams())
    with pytest.raises(UnmatchedEventError, match="no schedule row"):
        match_event("Arizona Cardinals", "Seattle Seahawks", 2026, schedule_index, name_to_abbr)


def test_event_to_snapshots_maps_markets_and_sides():
    match = MatchResult(event_id="2026_01_NE_SEA", season=2026, week=1, home_abbr="SEA", away_abbr="NE")
    snapshots = event_to_snapshots(_event(), CAPTURE_TIME, match)

    assert len(snapshots) == 6  # 3 markets x 2 outcomes, one bookmaker
    by_market_side = {(s.market, s.side): s for s in snapshots}

    ml_home = by_market_side[(Market.MONEYLINE, Side.HOME)]
    assert ml_home.price_american == -204
    assert ml_home.line is None

    spread_away = by_market_side[(Market.SPREAD, Side.AWAY)]
    assert spread_away.price_american == -119
    assert spread_away.line == 4.5

    total_over = by_market_side[(Market.TOTAL, Side.OVER)]
    assert total_over.price_american == -117
    assert total_over.line == 43.5

    assert all(s.event_id == "2026_01_NE_SEA" for s in snapshots)
    assert all(s.home_team == "SEA" and s.away_team == "NE" for s in snapshots)
    assert all(s.book == "pinnacle" for s in snapshots)


def test_event_to_snapshots_includes_all_bookmakers():
    match = MatchResult(event_id="2026_01_NE_SEA", season=2026, week=1, home_abbr="SEA", away_abbr="NE")
    two_books = [
        _pinnacle_block("Seattle Seahawks", "New England Patriots"),
        {**_pinnacle_block("Seattle Seahawks", "New England Patriots"), "key": "draftkings"},
    ]
    snapshots = event_to_snapshots(_event(bookmakers=two_books), CAPTURE_TIME, match)
    assert {s.book for s in snapshots} == {"pinnacle", "draftkings"}


def test_event_to_snapshots_bad_outcome_name_raises_transform_error():
    match = MatchResult(event_id="2026_01_NE_SEA", season=2026, week=1, home_abbr="SEA", away_abbr="NE")
    bad_block = {
        "key": "pinnacle",
        "markets": [{"key": "h2h", "outcomes": [{"name": "Some Other Team", "price": 100}]}],
    }
    with pytest.raises(TransformError):
        event_to_snapshots(_event(bookmakers=[bad_block]), CAPTURE_TIME, match)


def test_event_to_snapshots_missing_field_raises_transform_error():
    match = MatchResult(event_id="2026_01_NE_SEA", season=2026, week=1, home_abbr="SEA", away_abbr="NE")
    broken = {"id": "x", "commence_time": "2026-09-10T00:15:00Z", "bookmakers": []}
    with pytest.raises(TransformError):
        event_to_snapshots(broken, CAPTURE_TIME, match)


def test_unrequested_market_key_is_ignored_not_fatal():
    match = MatchResult(event_id="2026_01_NE_SEA", season=2026, week=1, home_abbr="SEA", away_abbr="NE")
    block = {
        "key": "pinnacle",
        "markets": [{"key": "player_props_weird", "outcomes": [{"name": "whatever", "price": 100}]}],
    }
    snapshots = event_to_snapshots(_event(bookmakers=[block]), CAPTURE_TIME, match)
    assert snapshots == []
