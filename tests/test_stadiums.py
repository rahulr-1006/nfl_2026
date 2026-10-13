from datetime import date

import pandas as pd
import pytest

from src.model.stadiums import (
    STADIUM_COORDINATES,
    haversine_miles,
    team_home_stadium_by_season,
    timezone_offset_hours,
)

# --- haversine_miles ---


def test_haversine_zero_distance_for_the_same_point():
    lat, lon, _ = STADIUM_COORDINATES["NYC01"]
    assert haversine_miles(lat, lon, lat, lon) == pytest.approx(0.0, abs=1e-6)


def test_haversine_matches_a_real_known_distance():
    # MetLife Stadium (NYC) to SoFi Stadium (LA) -- real distance ~2,450
    # miles (verified against a public great-circle-distance reference).
    lat1, lon1, _ = STADIUM_COORDINATES["NYC01"]
    lat2, lon2, _ = STADIUM_COORDINATES["LAX01"]
    assert haversine_miles(lat1, lon1, lat2, lon2) == pytest.approx(2450, abs=25)


def test_haversine_is_symmetric():
    lat1, lon1, _ = STADIUM_COORDINATES["GNB00"]
    lat2, lon2, _ = STADIUM_COORDINATES["MIA00"]
    assert haversine_miles(lat1, lon1, lat2, lon2) == pytest.approx(haversine_miles(lat2, lon2, lat1, lon1))


# --- timezone_offset_hours ---


def test_timezone_offset_handles_dst_for_eastern():
    assert timezone_offset_hours("America/New_York", date(2024, 7, 1)) == pytest.approx(-4.0)
    assert timezone_offset_hours("America/New_York", date(2024, 1, 1)) == pytest.approx(-5.0)


def test_timezone_offset_arizona_never_observes_dst():
    # The exact reason this is computed per-date via zoneinfo rather than a
    # hardcoded table -- Arizona is a real, structural exception.
    assert timezone_offset_hours("America/Phoenix", date(2024, 7, 1)) == pytest.approx(-7.0)
    assert timezone_offset_hours("America/Phoenix", date(2024, 1, 1)) == pytest.approx(-7.0)


def test_timezone_offset_london_vs_new_york_gap_during_the_nfl_season():
    gap = timezone_offset_hours("Europe/London", date(2024, 9, 10)) - timezone_offset_hours("America/New_York", date(2024, 9, 10))
    assert gap == pytest.approx(5.0)


# --- STADIUM_COORDINATES coverage ---


def test_stadium_coordinates_covers_every_real_stadium_id_in_the_cached_schedule():
    schedule = pd.read_parquet("data/static/schedules_2015_2025.parquet")
    real_ids = set(schedule["stadium_id"].unique())
    missing = real_ids - set(STADIUM_COORDINATES)
    assert missing == set(), f"STADIUM_COORDINATES is missing real stadium_id(s): {missing}"


def test_stadium_coordinates_covers_every_real_stadium_id_in_the_live_2026_schedule():
    # The historical-only version of this check (above) doesn't guard the
    # file the LIVE pipeline actually runs on -- a missing entry here
    # would silently fall back to distance=0.0/tz_diff=0.0 for every game
    # at that venue (add_rest_travel_features's defensive fallback),
    # feeding a wrong, silently-zeroed feature into a live prediction
    # instead of failing loudly. Caught by code review 2026-08-21.
    schedule = pd.read_parquet("data/static/schedules_2026_2026.parquet")
    real_ids = set(schedule["stadium_id"].dropna().unique())
    missing = real_ids - set(STADIUM_COORDINATES)
    assert missing == set(), f"STADIUM_COORDINATES is missing real live-2026 stadium_id(s): {missing}"


def test_stadium_coordinates_has_no_stale_unused_entries():
    # Guards the table from silently drifting out of sync with the data --
    # a stadium_id here that's no longer in the real schedule is a signal
    # something upstream changed and this table needs a look.
    #
    # Checked against the UNION of both cached vintages (widened 2026-09-27).
    # The historical file alone was the wrong denominator: the current season
    # lives in its own parquet, so every venue that appears only in 2026 --
    # the five international sites added when the stale 2026-08-14 schedule
    # was refreshed mid-season -- read as "stale" while actually being the
    # newest real data in the repo. "Stale" must mean present in NEITHER file.
    real_ids: set = set()
    for vintage in ("schedules_2015_2025.parquet", "schedules_2026_2026.parquet"):
        schedule = pd.read_parquet(f"data/static/{vintage}")
        real_ids |= set(schedule["stadium_id"].dropna().unique())
    stale = set(STADIUM_COORDINATES) - real_ids
    assert stale == set(), f"STADIUM_COORDINATES has stale stadium_id(s) not in the real schedule: {stale}"


# --- team_home_stadium_by_season ---


def _schedule_row(home_team, season, stadium_id, location="Home", away_team="XXX"):
    return {"home_team": home_team, "away_team": away_team, "season": season, "stadium_id": stadium_id, "location": location}


def test_team_home_stadium_by_season_picks_the_most_common_venue():
    schedule = pd.DataFrame(
        [
            _schedule_row("GB", 2020, "GNB00"),
            _schedule_row("GB", 2020, "GNB00"),
            _schedule_row("GB", 2020, "GNB00"),
            _schedule_row("GB", 2020, "LON00", location="Neutral"),  # a "home" game hosted abroad -- must not count
        ]
    )
    result = team_home_stadium_by_season(schedule)
    row = result[(result["team"] == "GB") & (result["season"] == 2020)].iloc[0]
    assert row["stadium_id"] == "GNB00"


def test_team_home_stadium_by_season_reflects_a_real_relocation():
    # The Rams: St. Louis through 2015, LA from 2016 on -- this must show
    # up automatically from the data, not require a hand-maintained
    # relocation table.
    schedule = pd.DataFrame(
        [
            *[_schedule_row("STL", 2015, "STL00") for _ in range(8)],
            *[_schedule_row("LA", 2016, "LAX99") for _ in range(8)],
            *[_schedule_row("LA", 2020, "LAX01") for _ in range(8)],  # SoFi opened 2020
        ]
    )
    result = team_home_stadium_by_season(schedule)
    assert result[(result["team"] == "STL") & (result["season"] == 2015)].iloc[0]["stadium_id"] == "STL00"
    assert result[(result["team"] == "LA") & (result["season"] == 2016)].iloc[0]["stadium_id"] == "LAX99"
    assert result[(result["team"] == "LA") & (result["season"] == 2020)].iloc[0]["stadium_id"] == "LAX01"


def test_team_home_stadium_by_season_on_real_cached_data_finds_the_rams_relocation():
    # End-to-end check against the real 2015-2024 schedule, not a synthetic
    # fixture -- confirms the empirical-derivation approach actually works
    # on the data it was built for.
    schedule = pd.read_parquet("data/static/schedules_2015_2025.parquet")
    result = team_home_stadium_by_season(schedule)
    stl_2015 = result[(result["team"] == "STL") & (result["season"] == 2015)]
    la_2018 = result[(result["team"] == "LA") & (result["season"] == 2018)]
    assert not stl_2015.empty and stl_2015.iloc[0]["stadium_id"] == "STL00"
    assert not la_2018.empty and la_2018.iloc[0]["stadium_id"] in {"LAX99", "LAX01"}
