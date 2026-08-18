"""Current player status: which team a player is on, and their injury/game
status, resolved *as of a given week* -- not a static season-long label.

**Why this exists.** Every Elo rating in `src/model/` (`qb_elo.py`,
`receiver_elo.py`, `pass_rush_elo.py`) is already trade-safe by construction:
each rating is keyed by `gsis_id`, and a player's rating carries with them
regardless of which team they're on in a given game row -- a trade doesn't
reset or corrupt anything there. What's missing is the *lookup* layer: given
a player, which team are they on right now, and are they hurt? That's a
separate question from rating skill, and free nflverse data (weekly roster
snapshots + weekly injury reports, both loaded by
`src/features/load_static.py::load_weekly_rosters`/`load_injuries`) answers
it directly.

**Resolution rule:** "current" means the most recent row at or before the
requested week within a season -- so a bye week, or a week with no new
injury report, still resolves to the last known state instead of a gap.
"""

from __future__ import annotations

import pandas as pd


def current_team(rosters: pd.DataFrame, season: int, as_of_week: int) -> pd.DataFrame:
    """One row per player: their most recent roster team/status at or
    before `as_of_week` in `season`. `status` is nflverse's raw roster code
    (ACT=active, DEV=practice squad, CUT, TRD=traded this week, RES=reserve/IR,
    RET=retired, etc.) -- callers filtering to "actually on the field" should
    check `status == "ACT"` explicitly, this function doesn't assume that
    for them.
    """
    snapshot = rosters[(rosters["season"] == season) & (rosters["week"] <= as_of_week)]
    snapshot = snapshot.sort_values("week").drop_duplicates("gsis_id", keep="last")
    return snapshot.rename(columns={"team": "current_team", "week": "roster_as_of_week", "status": "roster_status"})[
        ["gsis_id", "full_name", "position", "current_team", "roster_status", "roster_as_of_week"]
    ]


def current_injury_status(injuries: pd.DataFrame, season: int, as_of_week: int) -> pd.DataFrame:
    """One row per player with an injury-report history: their most recent
    `report_status` (Out/Doubtful/Questionable/null) at or before
    `as_of_week` in `season`. Players never on an injury report don't
    appear here at all -- join with `current_team`'s output (left join) to
    get a "no report" row for everyone else rather than losing them.
    """
    snapshot = injuries[(injuries["season"] == season) & (injuries["week"] <= as_of_week)]
    snapshot = snapshot.sort_values("week").drop_duplicates("gsis_id", keep="last")
    return snapshot.rename(columns={"week": "injury_as_of_week"})[
        ["gsis_id", "report_status", "report_primary_injury", "practice_status", "injury_as_of_week"]
    ]


def player_status_snapshot(rosters: pd.DataFrame, injuries: pd.DataFrame, season: int, as_of_week: int) -> pd.DataFrame:
    """One row per rostered player: current team (trade-aware) + current
    injury/game status, both resolved as of `as_of_week`. `report_status`
    is null for a player with no injury-report history at or before this
    week -- that's "no report on file," not missing data.
    """
    team = current_team(rosters, season, as_of_week)
    injury = current_injury_status(injuries, season, as_of_week)
    return team.merge(injury, on="gsis_id", how="left")
