"""Pull free static nflverse data (schedules + closing lines) into data/static/.

This is the zero-cost dataset: opening/closing spread, total, and moneyline
lines plus final scores, back to 1999. It has no intraday snapshots — that's
what the live collector (src/collect/) exists to capture, starting this
season. This module only backs the backtester's settlement join and the
market baseline.

nflverse's `spread_line` column uses the opposite sign convention from a
sportsbook-posted side line: use home_spread_line() below to convert it
before passing to src/store/settlement.settle(), never the raw column.
"""

from __future__ import annotations

from pathlib import Path

import nflreadpy as nfl

STATIC_DIR = Path("data/static")


def load_schedules(seasons: list[int], out_dir: Path = STATIC_DIR) -> Path:
    """Fetch nflverse schedules (scores + closing lines) and cache as parquet."""
    out_dir.mkdir(parents=True, exist_ok=True)
    df = nfl.load_schedules(seasons=seasons)
    path = out_dir / f"schedules_{min(seasons)}_{max(seasons)}.parquet"
    df.write_parquet(path)
    return path


# nflverse play-by-play carries ~370 columns (personnel, NGS, win prob
# deltas, etc.). The feature builder only needs the EPA/success columns
# behind a team-strength proxy, so cache a trimmed schema rather than the
# full raw pull -- keeps the parquet small and the feature builder's join
# surface explicit.
PBP_COLUMNS = [
    "game_id",
    "season",
    "week",
    "season_type",
    "posteam",
    "defteam",
    "play_type",
    "pass",
    "rush",
    "epa",
    "success",
    "wp",
    "qtr",  # needed for garbage-time exclusion (src/model/features.py) -- wp alone isn't enough, see that module
    "play_id",  # within-game play sequence number -- chronological ordering for src/model/receiver_elo.py
    "receiver_player_id",
    "receiver_player_name",
    "receiving_yards",
    "sack",  # pass-rush win flags for src/model/pass_rush_elo.py
    "qb_hit",
    "sack_player_id",
    "sack_player_name",
    "half_sack_1_player_id",
    "half_sack_1_player_name",
    "half_sack_2_player_id",
    "half_sack_2_player_name",
    "qb_hit_1_player_id",
    "qb_hit_1_player_name",
    "qb_hit_2_player_id",
    "qb_hit_2_player_name",
]


def load_pbp(seasons: list[int], out_dir: Path = STATIC_DIR) -> Path:
    """Fetch nflverse play-by-play, trim to PBP_COLUMNS, and cache as parquet.

    Regular-season and postseason rows only (season_type == "REG"/"POST");
    nflverse pbp has no preseason rows to begin with, matching schedules.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    df = nfl.load_pbp(seasons=seasons).select(PBP_COLUMNS)
    path = out_dir / f"pbp_{min(seasons)}_{max(seasons)}.parquet"
    df.write_parquet(path)
    return path


def load_players(out_dir: Path = STATIC_DIR) -> Path:
    """Fetch nflverse's player ID/position table and cache as parquet.

    `gsis_id` is the same ID format as pbp's `receiver_player_id` and the
    schedule's `home_qb_id`/`away_qb_id` -- the join key for labeling any
    player-level rating with a name/position. No season argument: this is
    nflverse's full all-time player table, not season-scoped.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    df = nfl.load_players().select(["gsis_id", "display_name", "position", "position_group"])
    path = out_dir / "players.parquet"
    df.write_parquet(path)
    return path


def load_weekly_rosters(seasons: list[int], out_dir: Path = STATIC_DIR) -> Path:
    """Fetch nflverse's weekly roster snapshots and cache as parquet.

    One row per player per team per week they were affiliated with (active
    roster, practice squad, injured reserve, etc. -- `status` distinguishes
    them). This is what makes a player's team assignment *fluid*: a trade
    shows up as a new row with a new `team` starting the week it happened,
    not a static season-long team label. `src/features/player_status.py`
    resolves this into a "current team as of week N" lookup.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    df = nfl.load_rosters_weekly(seasons=seasons).select(
        ["season", "week", "team", "gsis_id", "full_name", "position", "status", "status_description_abbr"]
    )
    path = out_dir / f"rosters_weekly_{min(seasons)}_{max(seasons)}.parquet"
    df.write_parquet(path)
    return path


def load_injuries(seasons: list[int], out_dir: Path = STATIC_DIR) -> Path:
    """Fetch nflverse's weekly injury reports and cache as parquet.

    One row per player per team per week with an injury report entry --
    `report_status` is the game-status field (Out/Doubtful/Questionable/
    null=no report that week). `src/features/player_status.py` resolves
    this into a "current status as of week N" lookup, same pattern as
    `load_weekly_rosters`.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    df = nfl.load_injuries(seasons=seasons).select(
        ["season", "week", "team", "gsis_id", "report_status", "report_primary_injury", "practice_status", "date_modified"]
    )
    path = out_dir / f"injuries_{min(seasons)}_{max(seasons)}.parquet"
    df.write_parquet(path)
    return path


def home_spread_line(spread_line: float) -> float:
    """Convert nflverse's spread_line into the sportsbook side-line
    convention that OddsSnapshot.line / settlement.settle() expect.

    nflverse signs spread_line as the home team's projected margin
    (positive = home favored, e.g. +7.5 means home projected to win by
    7.5). A sportsbook-posted side line does the opposite (negative =
    favored, e.g. -7.5 to bet the home favorite). They're the same number
    with flipped sign -- this function is that flip, named so the
    conversion can't be silently skipped or gotten backwards again.
    """
    return -float(spread_line)


if __name__ == "__main__":
    # Ten most recent completed seasons: enough for feature/calibration work
    # without pulling the full 1999-present history on first run.
    seasons = list(range(2015, 2025))
    print(f"wrote {load_schedules(seasons)}")
    print(f"wrote {load_pbp(seasons)}")
    print(f"wrote {load_players()}")
    print(f"wrote {load_weekly_rosters(seasons)}")
    print(f"wrote {load_injuries(seasons)}")
