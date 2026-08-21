import pandas as pd
import pytest

from src.model.features import add_rest_travel_features
from src.model.stadiums import STADIUM_COORDINATES


def _game_row(game_id, season, home_team, away_team, home_rest, away_rest, stadium_id, gameday="2024-09-08"):
    return {
        "game_id": game_id,
        "season": season,
        "home_team": home_team,
        "away_team": away_team,
        "home_rest": home_rest,
        "away_rest": away_rest,
        "stadium_id": stadium_id,
        "gameday": gameday,
    }


def _schedule_row(home_team, season, stadium_id, location="Home", away_team="XXX", gameday="2024-09-08"):
    return {"home_team": home_team, "away_team": away_team, "season": season, "stadium_id": stadium_id, "location": location, "gameday": gameday}


def _schedule_with_home_games(*teams_seasons_stadiums):
    """teams_seasons_stadiums: iterable of (team, season, stadium_id) --
    generates enough repeated home games for `team_home_stadium_by_season`'s
    mode-based derivation to pick that stadium unambiguously."""
    rows = []
    for team, season, stadium_id in teams_seasons_stadiums:
        rows.extend(_schedule_row(team, season, stadium_id) for _ in range(4))
    return pd.DataFrame(rows)


# --- rest re-encoding: thresholds and boundaries ---


def test_short_week_flag_set_at_the_four_day_threshold():
    df = pd.DataFrame([_game_row("g1", 2024, "GB", "CHI", 4, 7, "GNB00")])
    schedule = _schedule_with_home_games(("GB", 2024, "GNB00"))
    out = add_rest_travel_features(df, schedule)
    row = out.iloc[0]
    assert row["home_short_week"] == 1.0
    assert row["away_short_week"] == 0.0
    assert row["rest_differential"] == -3


def test_short_week_flag_not_set_at_five_days():
    df = pd.DataFrame([_game_row("g1", 2024, "GB", "CHI", 5, 7, "GNB00")])
    schedule = _schedule_with_home_games(("GB", 2024, "GNB00"))
    out = add_rest_travel_features(df, schedule)
    assert out.iloc[0]["home_short_week"] == 0.0


def test_missing_rest_propagates_as_nan_not_a_silent_false():
    # Caught by code review 2026-08-21: NaN <= 4 evaluates to False, which
    # would otherwise silently encode "missing" as "not short week" rather
    # than surfacing the missingness -- same discipline the stadium
    # lookups already use for a missing venue.
    df = pd.DataFrame([_game_row("g1", 2024, "GB", "CHI", None, 7, "GNB00")])
    schedule = _schedule_with_home_games(("GB", 2024, "GNB00"))
    out = add_rest_travel_features(df, schedule)
    row = out.iloc[0]
    assert pd.isna(row["home_short_week"])
    assert pd.isna(row["home_bye_week"])
    assert pd.isna(row["rest_differential"])
    # The other team's own flags, unaffected by home's missing rest, must
    # still compute normally.
    assert row["away_short_week"] == 0.0


def test_bye_week_flag_set_at_the_fourteen_day_threshold():
    df = pd.DataFrame([_game_row("g1", 2024, "GB", "CHI", 14, 7, "GNB00")])
    schedule = _schedule_with_home_games(("GB", 2024, "GNB00"))
    out = add_rest_travel_features(df, schedule)
    row = out.iloc[0]
    assert row["home_bye_week"] == 1.0
    assert row["rest_differential"] == 7


def test_bye_week_flag_not_set_at_thirteen_days():
    df = pd.DataFrame([_game_row("g1", 2024, "GB", "CHI", 13, 7, "GNB00")])
    schedule = _schedule_with_home_games(("GB", 2024, "GNB00"))
    out = add_rest_travel_features(df, schedule)
    assert out.iloc[0]["home_bye_week"] == 0.0


def test_both_teams_can_be_on_short_week_simultaneously():
    # A real, distinct situation a pure differential would collapse to 0 --
    # confirms the four binaries are kept, not just the differential.
    df = pd.DataFrame([_game_row("g1", 2024, "GB", "CHI", 4, 4, "GNB00")])
    schedule = _schedule_with_home_games(("GB", 2024, "GNB00"))
    out = add_rest_travel_features(df, schedule)
    row = out.iloc[0]
    assert row["home_short_week"] == 1.0
    assert row["away_short_week"] == 1.0
    assert row["rest_differential"] == 0


# --- travel: non-neutral baseline ---


def test_home_team_travels_zero_distance_in_a_normal_home_game():
    df = pd.DataFrame([_game_row("g1", 2024, "GB", "MIA", 7, 7, "GNB00")])
    schedule = _schedule_with_home_games(("GB", 2024, "GNB00"), ("MIA", 2024, "MIA00"))
    out = add_rest_travel_features(df, schedule)
    row = out.iloc[0]
    assert row["home_travel_distance"] == 0.0
    assert row["away_travel_distance"] > 0.0


def test_away_travel_distance_matches_a_known_real_route():
    # Green Bay to Miami is a well-known long road trip -- real distance
    # ~1,500 miles, sanity-checked against a public great-circle reference.
    df = pd.DataFrame([_game_row("g1", 2024, "GB", "MIA", 7, 7, "GNB00")])
    schedule = _schedule_with_home_games(("GB", 2024, "GNB00"), ("MIA", 2024, "MIA00"))
    out = add_rest_travel_features(df, schedule)
    assert out.iloc[0]["away_travel_distance"] == pytest.approx(1500, abs=150)


# --- travel: real relocation case ---


def test_home_stadium_lookup_reflects_a_relocation_across_seasons():
    # Atlanta: Georgia Dome through 2016, Mercedes-Benz Stadium from 2017.
    # A single hardcoded team->stadium mapping would get one of these two
    # seasons wrong; the empirical per-season derivation must not.
    df = pd.DataFrame(
        [
            _game_row("g1", 2016, "ATL", "NO", 7, 7, "ATL00"),
            _game_row("g2", 2018, "ATL", "NO", 7, 7, "ATL97"),
        ]
    )
    schedule = _schedule_with_home_games(("ATL", 2016, "ATL00"), ("ATL", 2018, "ATL97"), ("NO", 2016, "NOR00"), ("NO", 2018, "NOR00"))
    out = add_rest_travel_features(df, schedule)
    # Home team never traveled in either season, regardless of which
    # stadium was "home" that year.
    assert (out["home_travel_distance"] == 0.0).all()


# --- travel: real neutral-site case ---


def test_neutral_site_game_gives_both_teams_nonzero_travel():
    # The naive "home team always travels 0" design is wrong for a
    # neutral-site game (e.g. a Super Bowl) -- both teams travel from
    # their own city. Denver vs Carolina at Levi's Stadium (Santa Clara)
    # is a real historical case (Super Bowl 50).
    df = pd.DataFrame([_game_row("g1", 2015, "DEN", "CAR", 7, 7, "SFO01")])
    schedule = _schedule_with_home_games(("DEN", 2015, "DEN00"), ("CAR", 2015, "CAR00"))
    out = add_rest_travel_features(df, schedule)
    row = out.iloc[0]
    assert row["home_travel_distance"] > 0.0
    assert row["away_travel_distance"] > 0.0


# --- timezone: DST and Arizona edge cases ---


def test_timezone_diff_is_computed_per_game_date_not_a_fixed_offset():
    # Same route, two dates straddling the November DST transition -- a
    # static hardcoded offset table would be wrong for one of these two
    # real games. NE (Eastern) at DEN (Mountain): both observe DST the
    # same way, so the gap should be a stable 2 hours on both dates --
    # confirms the per-date zoneinfo computation is at least consistent,
    # not silently using a stale cached value.
    df = pd.DataFrame(
        [
            _game_row("g1", 2024, "DEN", "NE", 7, 7, "DEN00", gameday="2024-10-01"),
            _game_row("g2", 2024, "DEN", "NE", 7, 7, "DEN00", gameday="2024-12-01"),
        ]
    )
    schedule = _schedule_with_home_games(("DEN", 2024, "DEN00"), ("NE", 2024, "BOS00"))
    out = add_rest_travel_features(df, schedule)
    assert (out["away_tz_diff_hours"] == 2.0).all()


def test_arizona_gap_to_eastern_shifts_with_the_other_sides_dst_not_its_own():
    # Arizona's own offset (UTC-7) never changes -- but the GAP to Eastern
    # still shifts, because Eastern does observe DST (UTC-4 in July,
    # UTC-5 in December). A static hardcoded gap table would get one of
    # these two real dates wrong; the per-date zoneinfo computation must
    # produce the correct, DIFFERENT gap for each.
    df = pd.DataFrame(
        [
            _game_row("g1", 2024, "ARI", "NE", 7, 7, "PHO00", gameday="2024-07-01"),
            _game_row("g2", 2024, "ARI", "NE", 7, 7, "PHO00", gameday="2024-12-01"),
        ]
    )
    schedule = _schedule_with_home_games(("ARI", 2024, "PHO00"), ("NE", 2024, "BOS00"))
    out = add_rest_travel_features(df, schedule)
    assert out.iloc[0]["away_tz_diff_hours"] == 3.0  # July: AZ (-7) vs Eastern DST (-4)
    assert out.iloc[1]["away_tz_diff_hours"] == 2.0  # December: AZ (-7) vs Eastern standard (-5)


# --- missing-lookup fallback ---


def test_missing_home_venue_lookup_falls_back_to_zero_rather_than_raising():
    # A team with no recorded home game in this synthetic schedule --
    # team_home_stadium_by_season has nothing to derive from.
    df = pd.DataFrame([_game_row("g1", 2024, "GB", "MIA", 7, 7, "GNB00")])
    schedule = _schedule_with_home_games(("MIA", 2024, "MIA00"))  # GB missing on purpose
    out = add_rest_travel_features(df, schedule)
    row = out.iloc[0]
    assert row["home_travel_distance"] == 0.0
    assert row["home_tz_diff_hours"] == 0.0


# --- coverage sanity ---


def test_every_stadium_used_in_these_fixtures_has_real_coordinates():
    used = {"GNB00", "MIA00", "ATL00", "ATL97", "NOR00", "SFO01", "DEN00", "CAR00", "BOS00", "PHO00"}
    missing = used - set(STADIUM_COORDINATES)
    assert missing == set()
