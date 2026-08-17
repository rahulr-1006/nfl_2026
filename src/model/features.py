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


def team_game_epa(pbp: pd.DataFrame) -> pd.DataFrame:
    """Collapse play-by-play to one row per (game_id, team): offensive and
    defensive (allowed) EPA-per-play and success rate for that single game.
    """
    # Real plays only: nflverse marks penalties, no-plays, kneels, spikes,
    # and timeouts with pass == 0 and rush == 0 (`pass`/`rush` are Python
    # keywords, so this can't be a DataFrame.query() string).
    is_real_play = (pbp["pass"] == 1) | (pbp["rush"] == 1)
    plays = pbp[is_real_play].dropna(subset=["epa", "posteam", "defteam"])

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


def build_game_features(pbp: pd.DataFrame, schedule: pd.DataFrame, window: int | None = None) -> pd.DataFrame:
    """One row per game_id: home/away pre-game rolling EPA features plus
    the schedule context columns (rest, divisional, roof/surface/weather)
    the blueprint lists as part of the "modest feature set."

    Rows where either team is playing its first game in the cached window
    (pre_* is NaN, no prior games to average) are kept, not dropped --
    callers doing model training should drop or impute explicitly rather
    than have that decision made silently here.
    """
    team_game = team_game_epa(pbp)
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
