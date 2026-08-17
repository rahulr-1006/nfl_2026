"""Feature builder (blueprint Part E): team-strength proxies from play-by-play.

"Start simple: a modest feature set (team strength proxies, line movement,
opener versus current, cross-book dispersion)." This module builds the first
one -- pre-game rolling offensive/defensive EPA-per-play -- since it's the
only feature derivable from free historical data back to 2015. Line
movement and cross-book dispersion need the live collector's snapshots,
which only exist from 2026 onward, so they can't backfill a historical
training set the way EPA can.

Leakage guard: every team-strength feature for a game is computed only
from that team's games strictly before it (shift(1) before the rolling
window), the same "no reading the future" discipline as
src/store/pit_store.py's read_as_of, just applied to pbp instead of odds.
"""

from __future__ import annotations

import pandas as pd

# Standard nflverse-community garbage-time convention: 4th quarter or
# overtime, with win probability outside this band -- the outcome is no
# longer competitively in doubt, and both offenses and defenses commonly
# stop playing "real" football (backups in, prevent defense, running out
# the clock, desperation deep shots). EPA earned in that window doesn't
# reflect true team strength the way an in-doubt possession does.
GARBAGE_TIME_WP_LOW = 0.05
GARBAGE_TIME_WP_HIGH = 0.95
GARBAGE_TIME_QTR = 4  # applies to this quarter and any quarter after it (5 = OT)


def _is_garbage_time(plays: pd.DataFrame, wp_low: float, wp_high: float, qtr_threshold: int) -> pd.Series:
    """True where a play should be excluded. Missing `wp` (nflverse leaves
    ~0.6% of plays without a modeled win probability) is never treated as
    garbage -- there's no basis to call it garbage time, so the play stays
    in rather than being silently dropped for an unrelated reason.
    """
    has_wp = plays["wp"].notna()
    extreme_wp = ~plays["wp"].between(wp_low, wp_high)
    late = plays["qtr"] >= qtr_threshold
    return has_wp & late & extreme_wp


def team_game_epa(
    pbp: pd.DataFrame,
    exclude_garbage_time: bool = False,
    garbage_wp_low: float = GARBAGE_TIME_WP_LOW,
    garbage_wp_high: float = GARBAGE_TIME_WP_HIGH,
    garbage_qtr: int = GARBAGE_TIME_QTR,
) -> pd.DataFrame:
    """Collapse play-by-play to one row per (game_id, team): offensive and
    defensive (allowed) EPA-per-play and success rate for that single game.

    `exclude_garbage_time` defaults to False -- the original EPA feature
    set (and every Brier/log-loss number already reported for it in the
    paper/README) was built without this filter, and changing the default
    would silently change what those numbers mean on a re-run. Pass
    True explicitly to build the filtered variant for comparison, the
    same "new variant, old default preserved" pattern src/model/elo.py's
    integration into train.py already uses.
    """
    # Real plays only: nflverse marks penalties, no-plays, kneels, spikes,
    # and timeouts with pass == 0 and rush == 0 (`pass`/`rush` are Python
    # keywords, so this can't be a DataFrame.query() string).
    is_real_play = (pbp["pass"] == 1) | (pbp["rush"] == 1)
    plays = pbp[is_real_play].dropna(subset=["epa", "posteam", "defteam"])
    if exclude_garbage_time:
        plays = plays[~_is_garbage_time(plays, garbage_wp_low, garbage_wp_high, garbage_qtr)]

    off = (
        plays.groupby(["game_id", "posteam"])
        .agg(off_epa=("epa", "mean"), off_success=("success", "mean"), n_plays_off=("epa", "size"))
        .reset_index()
        .rename(columns={"posteam": "team"})
    )
    deff = (
        plays.groupby(["game_id", "defteam"])
        .agg(def_epa_allowed=("epa", "mean"), def_success_allowed=("success", "mean"), n_plays_def=("epa", "size"))
        .reset_index()
        .rename(columns={"defteam": "team"})
    )
    return off.merge(deff, on=["game_id", "team"], how="outer")


def rolling_team_strength(team_game: pd.DataFrame, schedule: pd.DataFrame, window: int | None = None) -> pd.DataFrame:
    """Pre-game rolling team-strength features, one row per (game_id, team).

    `window` is trailing games (e.g. 8 = last 8 games, crossing season
    boundaries). None means season-to-date expanding mean, reset each
    season -- the simpler default, since early-season trailing windows mix
    in the prior year's personnel.

    Every value is shifted one game before aggregating, so the feature
    attached to game N reflects only games 1..N-1 -- game N's own EPA never
    leaks into its own pre-game feature.
    """
    dated = team_game.merge(
        schedule[["game_id", "season", "gameday"]].drop_duplicates("game_id"),
        on="game_id",
        how="left",
    )
    dated = dated.sort_values(["team", "gameday", "game_id"])

    metrics = ["off_epa", "off_success", "def_epa_allowed", "def_success_allowed"]
    grouped = dated.groupby("team", group_keys=False)

    for col in metrics:
        shifted = grouped[col].shift(1)
        if window is None:
            season_grouped = pd.DataFrame({"team": dated["team"], "season": dated["season"], col: shifted}).groupby(
                ["team", "season"]
            )[col]
            dated[f"pre_{col}"] = season_grouped.transform(lambda s: s.expanding(min_periods=1).mean())
        else:
            dated[f"pre_{col}"] = shifted.groupby(dated["team"]).transform(
                lambda s: s.rolling(window, min_periods=1).mean()
            )

    pre_cols = [f"pre_{c}" for c in metrics]
    return dated[["game_id", "team", "season", "gameday", *pre_cols]]


def build_game_features(
    pbp: pd.DataFrame, schedule: pd.DataFrame, window: int | None = None, exclude_garbage_time: bool = False
) -> pd.DataFrame:
    """One row per game_id: home/away pre-game rolling EPA features plus
    the schedule context columns (rest, divisional, roof/surface/weather)
    the blueprint lists as part of the "modest feature set."

    Rows where either team is playing its first game in the cached window
    (pre_* is NaN, no prior games to average) are kept, not dropped --
    callers doing model training should drop or impute explicitly rather
    than have that decision made silently here.

    `exclude_garbage_time`: see `team_game_epa` -- defaults to False to
    preserve the original feature set's behavior.
    """
    team_game = team_game_epa(pbp, exclude_garbage_time=exclude_garbage_time)
    strength = rolling_team_strength(team_game, schedule, window=window)

    pre_cols = ["pre_off_epa", "pre_off_success", "pre_def_epa_allowed", "pre_def_success_allowed"]
    # Merge keys on (game_id, home_team)/(game_id, away_team) rather than
    # game_id alone: `strength` has one row per team per game (two rows per
    # game_id), so a game_id-only merge would fan out and attach both
    # teams' stats to each side.
    home = strength[["game_id", "team", *pre_cols]].rename(
        columns={"team": "home_team", **{c: f"home_{c}" for c in pre_cols}}
    )
    away = strength[["game_id", "team", *pre_cols]].rename(
        columns={"team": "away_team", **{c: f"away_{c}" for c in pre_cols}}
    )

    context_cols = [
        "game_id",
        "season",
        "week",
        "gameday",
        "home_team",
        "away_team",
        "home_rest",
        "away_rest",
        "div_game",
        "roof",
        "surface",
        "temp",
        "wind",
        "spread_line",
        "total_line",
    ]
    context = schedule[context_cols].copy()

    out = context.merge(home, on=["game_id", "home_team"], how="left")
    out = out.merge(away, on=["game_id", "away_team"], how="left")
    return out
