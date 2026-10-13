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
import pandas as pd

STATIC_DIR = Path("data/static")

# nflverse publishes `gameday`/`gametime` as US/Eastern wall-clock time for every
# game, international ones included. Parsing them with `utc=True` (the old code
# in collect/run.py and backtest/engine.py) put every kickoff 4h early under EDT,
# 5h under EST -- measured 2026-10-04: 2026_04_PIT_CLE read 20:15 UTC against a
# real 00:15 UTC. The collector then believed TNF/MNF had already started and
# dropped to its sparse cadence for the last ~4h before kickoff.
NFLVERSE_TZ = "America/New_York"


def kickoffs_utc(schedule: pd.DataFrame) -> pd.Series:
    """Real UTC kickoff per schedule row, from nflverse's Eastern-time columns."""
    local = pd.to_datetime(schedule["gameday"].astype(str) + " " + schedule["gametime"].astype(str))
    return local.dt.tz_localize(NFLVERSE_TZ).dt.tz_convert("UTC")


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


PLAYER_STATS_COLUMNS = [
    "player_id",
    "player_display_name",
    "position",
    "season",
    "week",
    "game_id",
    "team",
    "opponent_team",
    "passing_yards",
    "passing_tds",
    "rushing_yards",
    "rushing_tds",
    "receiving_yards",
    "receptions",
    "receiving_tds",
]


def load_player_stats(seasons: list[int], out_dir: Path = STATIC_DIR) -> Path:
    """Fetch nflverse's weekly player stats, trim to PLAYER_STATS_COLUMNS,
    and cache as parquet -- the free per-player-per-game box score
    (passing/rushing/receiving yards and TDs, receptions), used for prop
    settlement (`src/store/prop_settlement.py`) and correlated-outcome
    analysis (`src/backtest/correlated_props.py`).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    df = nfl.load_player_stats(seasons=seasons).select(PLAYER_STATS_COLUMNS)
    path = out_dir / f"player_stats_{min(seasons)}_{max(seasons)}.parquet"
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


SNAP_COUNTS_COLUMNS = [
    "game_id",
    "pfr_game_id",
    "season",
    "week",
    "player",
    "pfr_player_id",
    "position",
    "team",
    "defense_snaps",
]


def load_snap_counts(seasons: list[int], out_dir: Path = STATIC_DIR) -> Path:
    """Fetch nflverse's per-player-per-game snap counts and cache as parquet.

    `defense_snaps` is the denominator `src/model/individual_pass_rush_elo.py`
    needs -- 2026-08-21 finding: this project previously assumed no free
    participation/exposure data existed for individual pass-rush players
    (see `src/model/pass_rush_elo.py`'s docstring), but joined against
    `load_pfr_advstats(stat_type="def")` on `pfr_player_id`/`pfr_game_id`
    (100% match rate, verified), total defensive snaps is a real, usable
    proxy for pass-rush opportunity for true rush positions (DE/DT/EDGE) --
    not the same as literal per-play rush assignment, but a genuine
    denominator where none was available before.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    df = nfl.load_snap_counts(seasons=seasons).select(SNAP_COUNTS_COLUMNS)
    path = out_dir / f"snap_counts_{min(seasons)}_{max(seasons)}.parquet"
    df.write_parquet(path)
    return path


PFR_DEF_ADVSTATS_COLUMNS = [
    "game_id",
    "pfr_game_id",
    "season",
    "week",
    "team",
    "pfr_player_id",
    "pfr_player_name",
    "def_times_blitzed",
    "def_times_hurried",
    "def_times_hitqb",
    "def_sacks",
    "def_pressures",
]


def load_pfr_pass_rush_advstats(seasons: list[int], out_dir: Path = STATIC_DIR) -> Path:
    """Fetch Pro Football Reference's advanced DEFENSIVE stats
    (`stat_type="def"`) and cache as parquet, trimmed to the pass-rush
    columns -- drops the coverage/DB-specific columns in the same raw
    table (`def_completions_allowed`, `def_yards_allowed`, etc.), which
    aren't relevant to a pass-rush rating.

    **Only available from 2018 onward** (nflreadpy's own documented floor
    for this source) -- narrower than every other cached table in this
    project, which mostly starts at 2015. `src/model/pass_rush_elo.py`'s
    team-level rating still covers the full 2015+ range; this is a
    narrower-coverage individual-level companion, not a replacement.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    df = nfl.load_pfr_advstats(seasons=seasons, stat_type="def").select(PFR_DEF_ADVSTATS_COLUMNS)
    path = out_dir / f"pfr_def_advstats_{min(seasons)}_{max(seasons)}.parquet"
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
    # Eleven most recent completed seasons: enough for feature/calibration work
    # without pulling the full 1999-present history on first run. Update this
    # range each time a new season completes (2026-08-21: extended from
    # 2015-2024 to 2015-2025 after discovering the cache had gone stale by a
    # full completed season -- re-run this file whenever that happens again).
    seasons = list(range(2015, 2026))
    print(f"wrote {load_schedules(seasons)}")
    print(f"wrote {load_pbp(seasons)}")
    print(f"wrote {load_players()}")
    print(f"wrote {load_weekly_rosters(seasons)}")
    print(f"wrote {load_injuries(seasons)}")
    print(f"wrote {load_player_stats(seasons)}")

    # 2018+ only -- see load_pfr_pass_rush_advstats's docstring for why.
    pfr_seasons = [s for s in seasons if s >= 2018]
    print(f"wrote {load_snap_counts(pfr_seasons)}")
    print(f"wrote {load_pfr_pass_rush_advstats(pfr_seasons)}")
