"""Roll the play-level receiver Elo and pass-rush Elo ratings
(`receiver_elo.py`, `pass_rush_elo.py`) up to one row per game -- the
missing piece that makes either usable by a game-outcome model at all.
Neither is reachable by `train.py`'s feature set without this: both
produce a row per target/dropback, not per game.

**Pass-rush is nearly free.** `pass_rush_elo.py`'s output is already
team-level (`defteam`/`posteam` per play) -- it just needs the pre-game
snapshot, not a roster rollup. A team's rating *entering* a game is
already sitting on that game's first play by construction (every `pre_*`
column reflects only plays strictly before it), so this is a groupby-first,
not a new computation.

**Receiver Elo needs a real aggregation decision**, because a "team's
receiving corps" is a set of players, not one entity, and most rostered
receivers don't get targeted in a given game (so their rating can't be
read off that game's own rows the way pass-rush's can). Three real design
choices, stated plainly rather than hidden in the code:

1. **Roster join, not target history.** Which WR/TEs count as "on this
   team" for a game comes from `src/features/player_status.py::current_team`
   (the existing trade-safe, as-of-week lookup) filtered to
   `position in {WR, TE}` and `roster_status == "ACT"` -- not from who
   happened to get targeted that game, which would leak the outcome
   (target share isn't known pre-game).
2. **Rating carries forward across games a player didn't get targeted
   in.** A receiver's "current" rating entering week W is his most recent
   POST rating from strictly before week W (`pd.merge_asof`, backward,
   no exact match -- leakage-free the same way every other pre-game
   rating in this project is). A receiver with no prior target defaults
   to `INITIAL_RATING`, matching `receiver_elo.py`'s own default.
3. **Top-N by rating, not a flat mean across the whole roster.** A QB1's
   supporting cast shouldn't be diluted by 4th/5th-string bodies who
   rarely see the field. Target-share weighting is the natural v2 (gated
   on data this project doesn't have leakage-safely pre-game) -- this is
   a deliberate v1 simplification, not a hidden shortcut.
"""

from __future__ import annotations

import pandas as pd

from src.model.elo import INITIAL_RATING, canonical_team

DEFAULT_TOP_N_RECEIVERS = 3


def aggregate_pass_rush_elo_to_game(pass_rush_elo_ratings: pd.DataFrame, schedule: pd.DataFrame) -> pd.DataFrame:
    """One row per `game_id`: each team's pre-game pass-rush Elo (as the
    defense) and pass-protection Elo (as the offense). `pass_rush_elo.py`'s
    `defteam`/`posteam` flip possession-by-possession within a single
    game, so this resolves them to `home_team`/`away_team` via `schedule`.
    """
    ratings = pass_rush_elo_ratings.sort_values(["game_id", "play_id"])
    rush_first = ratings.groupby(["game_id", "defteam"], as_index=False).first()[
        ["game_id", "defteam", "pre_pass_rush_elo"]
    ]
    protection_first = ratings.groupby(["game_id", "posteam"], as_index=False).first()[
        ["game_id", "posteam", "pre_pass_protection_elo"]
    ]

    games = schedule[["game_id", "home_team", "away_team"]].copy()
    games["home_team"] = games["home_team"].map(canonical_team)
    games["away_team"] = games["away_team"].map(canonical_team)

    out = games.merge(
        rush_first.rename(columns={"defteam": "home_team", "pre_pass_rush_elo": "home_pre_pass_rush_elo"}),
        on=["game_id", "home_team"], how="left",
    )
    out = out.merge(
        rush_first.rename(columns={"defteam": "away_team", "pre_pass_rush_elo": "away_pre_pass_rush_elo"}),
        on=["game_id", "away_team"], how="left",
    )
    out = out.merge(
        protection_first.rename(columns={"posteam": "home_team", "pre_pass_protection_elo": "home_pre_pass_protection_elo"}),
        on=["game_id", "home_team"], how="left",
    )
    out = out.merge(
        protection_first.rename(columns={"posteam": "away_team", "pre_pass_protection_elo": "away_pre_pass_protection_elo"}),
        on=["game_id", "away_team"], how="left",
    )
    return out[
        ["game_id", "home_pre_pass_rush_elo", "away_pre_pass_rush_elo", "home_pre_pass_protection_elo", "away_pre_pass_protection_elo"]
    ]


def _roster_grid(rosters: pd.DataFrame, schedule: pd.DataFrame) -> pd.DataFrame:
    """One row per (gsis_id, season, week, team): every active WR/TE on a
    team's roster, for every (season, week) that appears in `schedule`.
    Uses `week` itself (not week-1) -- nflverse's own weekly roster
    snapshot for week W already reflects that week's actual roster, a
    fact determinable pre-game, not a look-ahead.
    """
    from src.features.player_status import current_team

    frames = []
    for season, week in schedule[["season", "week"]].drop_duplicates().itertuples(index=False):
        snap = current_team(rosters, season, week)
        snap = snap[snap["position"].isin(["WR", "TE"]) & (snap["roster_status"] == "ACT")]
        if snap.empty:
            continue
        snap = snap.assign(season=season, week=week)
        frames.append(snap[["gsis_id", "season", "week", "current_team"]].rename(columns={"current_team": "team"}))
    if not frames:
        return pd.DataFrame(columns=["gsis_id", "season", "week", "team"])
    return pd.concat(frames, ignore_index=True)


def _current_receiver_ratings(receiver_elo_ratings: pd.DataFrame, roster_grid: pd.DataFrame) -> pd.DataFrame:
    """Adds `current_elo` to `roster_grid`: each rostered receiver's
    rating entering that (season, week) -- his most recent POST rating
    from strictly before it (`merge_asof`, backward, no exact match).
    Never targeted before -> `INITIAL_RATING`, same default
    `receiver_elo.py` itself uses for a first-time target.
    """
    timeline = (
        receiver_elo_ratings.sort_values(["receiver_player_id", "season", "week", "play_id"])
        .groupby(["receiver_player_id", "season", "week"], as_index=False)
        .last()
    )
    timeline["sort_key"] = timeline["season"] * 100 + timeline["week"]
    timeline = timeline[["receiver_player_id", "sort_key", "post_receiver_elo"]].sort_values("sort_key")

    grid = roster_grid.rename(columns={"gsis_id": "receiver_player_id"}).copy()
    grid["sort_key"] = grid["season"] * 100 + grid["week"]
    grid = grid.sort_values("sort_key")

    merged = pd.merge_asof(
        grid, timeline, on="sort_key", by="receiver_player_id", direction="backward", allow_exact_matches=False
    )
    merged["current_elo"] = merged["post_receiver_elo"].fillna(INITIAL_RATING)
    return merged


def aggregate_receiver_elo_to_game(
    receiver_elo_ratings: pd.DataFrame,
    rosters: pd.DataFrame,
    schedule: pd.DataFrame,
    top_n: int = DEFAULT_TOP_N_RECEIVERS,
) -> pd.DataFrame:
    """One row per `game_id`: each team's receiving-corps Elo (mean of its
    top-`top_n` rostered WR/TE by current pre-game rating -- see module
    docstring for why top-N, not a flat mean) and the opposing team's
    pass-defense Elo at kickoff (same first-play-of-game cut
    `aggregate_pass_rush_elo_to_game` uses).
    """
    grid = _roster_grid(rosters, schedule)
    rated = _current_receiver_ratings(receiver_elo_ratings, grid)

    corps = (
        rated.sort_values("current_elo", ascending=False)
        .groupby(["team", "season", "week"])
        .head(top_n)
        .groupby(["team", "season", "week"], as_index=False)["current_elo"]
        .mean()
        .rename(columns={"current_elo": "receiving_corps_elo"})
    )

    pass_def_first = (
        receiver_elo_ratings.sort_values(["game_id", "play_id"])
        .groupby(["game_id", "defteam"], as_index=False)
        .first()[["game_id", "defteam", "pre_pass_defense_elo"]]
    )

    games = schedule[["game_id", "season", "week", "home_team", "away_team"]].copy()
    games["home_team"] = games["home_team"].map(canonical_team)
    games["away_team"] = games["away_team"].map(canonical_team)

    out = games.merge(
        corps.rename(columns={"team": "home_team", "receiving_corps_elo": "home_receiving_corps_elo"}),
        on=["season", "week", "home_team"], how="left",
    )
    out = out.merge(
        corps.rename(columns={"team": "away_team", "receiving_corps_elo": "away_receiving_corps_elo"}),
        on=["season", "week", "away_team"], how="left",
    )
    out = out.merge(
        pass_def_first.rename(columns={"defteam": "away_team", "pre_pass_defense_elo": "home_opp_pass_defense_elo"}),
        on=["game_id", "away_team"], how="left",
    )
    out = out.merge(
        pass_def_first.rename(columns={"defteam": "home_team", "pre_pass_defense_elo": "away_opp_pass_defense_elo"}),
        on=["game_id", "home_team"], how="left",
    )
    return out[
        ["game_id", "home_receiving_corps_elo", "away_receiving_corps_elo", "home_opp_pass_defense_elo", "away_opp_pass_defense_elo"]
    ]
