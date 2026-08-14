"""Team full-name -> abbreviation resolution.

nflreadpy.load_teams() carries legacy/relocated aliases (LAR/LA, SD/LAC,
OAK/LV, STL/LA), so a naive full_name -> abbr dict has duplicate values
across seasons. We resolve that by restricting to whichever abbreviation
actually appears in the season's own schedule.

The Odds API's team-name strings are expected to match nflverse's
`team_name` exactly (e.g. "Kansas City Chiefs"). If a live poll ever
returns a name not in this map, match_event (src/collect/transform.py)
raises loudly rather than guessing — add an explicit override below only
if a real mismatch is found, don't pre-guess exceptions.
"""

from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path

import nflreadpy as nfl
import pandas as pd

# Confirmed mismatches between The Odds API's team names and nflverse's
# team_name, found by running the collector against a live poll. Empty
# until proven otherwise.
NAME_OVERRIDES: dict[str, str] = {}


def build_team_name_map(schedule: pd.DataFrame, teams: pd.DataFrame) -> dict[str, str]:
    """full team name -> abbreviation, restricted to abbrs used in `schedule`."""
    live_abbrs = set(schedule["home_team"]) | set(schedule["away_team"])
    name_map = {
        row.team_name: row.team_abbr
        for row in teams.itertuples()
        if row.team_abbr in live_abbrs
    }
    name_map.update(NAME_OVERRIDES)
    return name_map


@lru_cache(maxsize=1)
def load_team_name_map(season: int, schedule_path: Path) -> Mapping[str, str]:
    schedule = pd.read_parquet(schedule_path)
    schedule = schedule[schedule["season"] == season]
    teams = nfl.load_teams().to_pandas()
    return build_team_name_map(schedule, teams)
