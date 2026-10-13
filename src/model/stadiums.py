"""Stadium coordinates and travel-distance/timezone-crossing utilities for
`src/model/features.py::add_rest_travel_features`.

**Why this exists at all.** `home_rest`/`away_rest` (days of rest before the
game) have been in `FEATURE_COLUMNS` since day one -- every model this
project has ever evaluated already has raw rest data as an input. Travel
distance and timezone crossing are genuinely new information: nothing in
this repo (or nflverse's cached tables) carries stadium coordinates or
timezones. This module supplies exactly that, hand-built from public,
static facts (NFL stadium locations don't move), not derived from any paid
or unreliable source.

**Team relocations are handled by NOT hand-tracking them.** St. Louis -> LA
Rams (2016), San Diego -> LA Chargers (2017), and Oakland -> Las Vegas
Raiders (2020) all happened inside the cached 2015-2024 window. Rather than
hand-maintain a team -> stadium-history table (error-prone, easy to get an
exact season boundary wrong), `team_home_stadium_by_season` derives each
team's home stadium per season directly from the schedule's own real
`home_team`/`location`/`stadium_id` columns -- the data already recorded
the correct venue for every game; this just reads it back out empirically
instead of re-encoding it by hand.
"""

from __future__ import annotations

import math
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd

# stadium_id -> (latitude, longitude, IANA timezone name). Built from the
# 44 distinct `stadium_id` values actually present in
# data/static/schedules_2015_2025.parquet (verified via direct query, not
# guessed) -- city-level coordinate accuracy, which is all a travel-distance
# feature needs. Includes every international/neutral-site venue (London x3,
# Mexico City, Munich, Frankfurt, Sao Paulo) since those appear as real
# `stadium_id` values in real games, not just domestic team-home venues.
STADIUM_COORDINATES: dict[str, tuple[float, float, str]] = {
    "ATL00": (33.7573, -84.4006, "America/New_York"),  # Georgia Dome
    "ATL97": (33.7554, -84.4008, "America/New_York"),  # Mercedes-Benz Stadium
    "BAL00": (39.2780, -76.6227, "America/New_York"),  # M&T Bank Stadium
    "BOS00": (42.0909, -71.2643, "America/New_York"),  # Gillette Stadium
    "BUF00": (42.7738, -78.7870, "America/New_York"),  # Highmark/Ralph Wilson Stadium
    "CAR00": (35.2258, -80.8528, "America/New_York"),  # Bank of America Stadium
    "CHI98": (41.8623, -87.6167, "America/Chicago"),  # Soldier Field
    "CIN00": (39.0955, -84.5160, "America/New_York"),  # Paul Brown/Paycor Stadium
    "CLE00": (41.5061, -81.6995, "America/New_York"),  # FirstEnergy/Huntington Bank Field
    "DAL00": (32.7473, -97.0945, "America/Chicago"),  # AT&T Stadium
    "DEN00": (39.7439, -105.0201, "America/Denver"),  # Empower/Mile High
    "DET00": (42.3400, -83.0456, "America/New_York"),  # Ford Field
    "FRA00": (50.0686, 8.6455, "Europe/Berlin"),  # Deutsche Bank Park, Frankfurt
    "GER00": (48.2188, 11.6247, "Europe/Berlin"),  # Allianz Arena, Munich
    "GNB00": (44.5013, -88.0622, "America/Chicago"),  # Lambeau Field
    "HOU00": (29.6847, -95.4107, "America/Chicago"),  # NRG Stadium
    "IND00": (39.7601, -86.1639, "America/New_York"),  # Lucas Oil Stadium (Indiana observes Eastern)
    "JAX00": (30.3239, -81.6373, "America/New_York"),  # EverBank/TIAA Bank/UF Health Field
    "KAN00": (39.0489, -94.4839, "America/Chicago"),  # Arrowhead Stadium
    "LAX01": (33.9535, -118.3392, "America/Los_Angeles"),  # SoFi Stadium
    "LAX97": (33.8644, -118.2611, "America/Los_Angeles"),  # StubHub Center/Dignity Health Sports Park
    "LAX99": (34.0141, -118.2879, "America/Los_Angeles"),  # LA Memorial Coliseum
    "LON00": (51.5560, -0.2795, "Europe/London"),  # Wembley Stadium
    "LON01": (51.4548, -0.3418, "Europe/London"),  # Twickenham Stadium
    "LON02": (51.6043, -0.0665, "Europe/London"),  # Tottenham Hotspur Stadium
    # The 2026 international slate (added 2026-09-27). These five ids did not
    # exist in the cached schedule until it was refreshed mid-season: the
    # 2026-08-14 vintage carried NO international `stadium_id` at all and mapped
    # every neutral-site game to the nominal home team's domestic venue, so
    # `add_rest_travel_features` was computing a confidently wrong travel
    # distance (SF->LA for a game in Melbourne) rather than a missing one.
    # nflverse also issued MUN01 for the Munich venue already present as GER00;
    # both are Allianz Arena and both are kept, since either id can appear
    # depending on which schedule vintage a row came from.
    "MAD01": (40.4531, -3.6883, "Europe/Madrid"),  # Santiago Bernabeu, Madrid
    "MEL00": (-37.8199, 144.9834, "Australia/Melbourne"),  # Melbourne Cricket Ground
    "MUN01": (48.2188, 11.6247, "Europe/Berlin"),  # Allianz Arena, Munich (see GER00)
    "PAR00": (48.9244, 2.3601, "Europe/Paris"),  # Stade de France, Saint-Denis
    "RIO00": (-22.9122, -43.2302, "America/Sao_Paulo"),  # Maracana Stadium, Rio de Janeiro
    "MEX00": (19.3029, -99.1505, "America/Mexico_City"),  # Estadio Azteca
    "MIA00": (25.9580, -80.2389, "America/New_York"),  # Sun Life/Hard Rock Stadium
    "MIN01": (44.9738, -93.2575, "America/Chicago"),  # U.S. Bank Stadium
    "MIN98": (44.9762, -93.2244, "America/Chicago"),  # TCF Bank Stadium
    "NAS00": (36.1665, -86.7713, "America/Chicago"),  # Nissan Stadium (Nashville observes Central)
    "NOR00": (29.9511, -90.0812, "America/Chicago"),  # Caesars/Mercedes-Benz Superdome
    "NYC01": (40.8135, -74.0745, "America/New_York"),  # MetLife Stadium
    "OAK00": (37.7516, -122.2005, "America/Los_Angeles"),  # Oakland/O.co Coliseum
    "PHI00": (39.9008, -75.1675, "America/New_York"),  # Lincoln Financial Field
    "PHO00": (33.5276, -112.2626, "America/Phoenix"),  # State Farm Stadium (Arizona does not observe DST)
    "PIT00": (40.4468, -80.0158, "America/New_York"),  # Heinz/Acrisure Stadium
    "SAO00": (-23.5453, -46.4742, "America/Sao_Paulo"),  # Arena Corinthians, Sao Paulo
    "SDG00": (32.7831, -117.1195, "America/Los_Angeles"),  # Qualcomm Stadium
    "SEA00": (47.5952, -122.3316, "America/Los_Angeles"),  # Lumen/CenturyLink Field
    "SFO01": (37.4030, -121.9700, "America/Los_Angeles"),  # Levi's Stadium
    "STL00": (38.6329, -90.1886, "America/Chicago"),  # Edward Jones Dome
    "TAM00": (27.9759, -82.5033, "America/New_York"),  # Raymond James Stadium
    "VEG00": (36.0909, -115.1833, "America/Los_Angeles"),  # Allegiant Stadium
    "WAS00": (38.9077, -76.8645, "America/New_York"),  # FedExField
}

_EARTH_RADIUS_MILES = 3958.8


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in miles between two lat/lon points -- exact
    for this purpose (travel distance between stadiums), no new dependency
    needed for something this simple.
    """
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return _EARTH_RADIUS_MILES * 2 * math.asin(math.sqrt(a))


def timezone_offset_hours(tz_name: str, on_date: date) -> float:
    """UTC offset in hours for `tz_name` on `on_date` -- computed at the
    actual game date (via `zoneinfo`, Python stdlib, no new dependency) so
    DST is handled correctly rather than assuming a fixed year-round
    offset. Arizona (`America/Phoenix`) never observes DST, which is
    exactly why computing this per-date instead of hardcoding a table of
    offsets matters -- a fixed table would need its own DST-schedule logic
    duplicated by hand, this reuses Python's own.
    """
    at_noon = datetime(on_date.year, on_date.month, on_date.day, 12, tzinfo=ZoneInfo(tz_name))
    return at_noon.utcoffset().total_seconds() / 3600.0


def team_home_stadium_by_season(schedule: pd.DataFrame) -> pd.DataFrame:
    """(team, season) -> stadium_id, derived from the schedule's own real
    home games -- the most common `stadium_id` a team hosted at that
    season, restricted to `location == "Home"` rows (excludes neutral-site
    "home" games, e.g. a London game credited to a team as the nominal
    home side, from corrupting the team's actual home-venue signal).
    Correctly reflects mid-window relocations (STL->LA Rams 2016, SD->LA
    Chargers 2017, OAK->LV Raiders 2020) automatically, since it reads
    each season's real games rather than assuming a static mapping.
    """
    home_games = schedule[schedule["location"] == "Home"]
    counts = home_games.groupby(["home_team", "season", "stadium_id"]).size().reset_index(name="n")
    idx = counts.groupby(["home_team", "season"])["n"].idxmax()
    result = counts.loc[idx, ["home_team", "season", "stadium_id"]].reset_index(drop=True)
    return result.rename(columns={"home_team": "team"})
