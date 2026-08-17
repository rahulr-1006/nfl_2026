"""QB-level Elo: a residual rating crediting individual quarterback
performance separately from team strength.

**Design, stated plainly: this is this project's own simplification, not
a replication of a published QB-rating model** (e.g. FiveThirtyEight's
NFL QB Elo, which builds QB value from a separate ANY/A regression --
real, more sophisticated, and out of scope for a first benchmark).

**The idea:** `src/model/elo.py`'s team ratings already capture team
strength. A QB's own rating should move based on how much the team's
*actual result* over- or under-performed what the team's own pre-game
Elo *alone* (ignoring who's starting at QB) would have predicted -- not
based on the raw win/loss the way team Elo updates. A backup starting for
a strong team and losing anyway isn't blamed for the team's own baseline
strength; a QB whose team wins despite a weak team-Elo expectation gets
credited for the surprise. This isolates a QB-specific residual signal
without needing play-level QB stats (ANY/A, EPA/dropback, etc.) this
project doesn't have cached yet.

**Data:** nflverse's schedule already carries `home_qb_id`/`away_qb_id`
(the starting QB) for every game, for free -- confirmed zero missing
values across the full 2015-2024 cache. No new data pull needed, unlike
player props.

**Leakage-free the same way team Elo is:** sequential processing, a QB's
rating entering a game reflects only starts strictly before it.

**Deliberately no season reversion for QB ratings (v1 simplification).**
Team Elo reverts 1/3 toward the mean each season to account for roster
turnover; a starting QB's own skill is more stable year to year than a
full 53-man roster, and simplicity was chosen over guessing at a QB-specific
reversion rate with no data to justify one. Revisit if ratings look wrong
for long-tenured QBs.
"""

from __future__ import annotations

import pandas as pd

from src.model.elo import (
    DEFAULT_HOME_FIELD_ADVANTAGE,
    INITIAL_RATING,
    canonical_team,
    elo_win_probability,
    mov_multiplier,
)

DEFAULT_QB_K = 8.0  # smaller than team Elo's K=20 -- a QB explains part of a team's result, not all of it


def compute_qb_elo_ratings(
    schedule: pd.DataFrame,
    team_elo_ratings: pd.DataFrame,
    k: float = DEFAULT_QB_K,
    home_field_advantage: float = DEFAULT_HOME_FIELD_ADVANTAGE,
    initial_rating: float = INITIAL_RATING,
) -> pd.DataFrame:
    """One row per game: each starting QB's Elo rating *entering* that
    game (pre-game, leakage-free), plus post-game ratings for reference.

    `team_elo_ratings`: the output of `src/model/elo.py::compute_team_elo_ratings`
    on the SAME schedule -- read for its `home_pre_elo`/`away_pre_elo`
    columns, the "team-only" expectation baseline a QB's rating moves
    relative to. Must cover every game in `schedule` (same schedule,
    same completed-games filter) or the merge below will raise.
    """
    team_lookup = team_elo_ratings.set_index("game_id")[["home_pre_elo", "away_pre_elo"]]

    games = schedule.dropna(subset=["home_score", "away_score"]).copy()
    games["home_team"] = games["home_team"].map(canonical_team)
    games["away_team"] = games["away_team"].map(canonical_team)
    games = games.sort_values(["season", "gameday", "game_id"])

    ratings: dict[str, float] = {}
    rows = []

    for row in games.itertuples():
        team_pre = team_lookup.loc[row.game_id]
        home_team_elo, away_team_elo = float(team_pre["home_pre_elo"]), float(team_pre["away_pre_elo"])

        home_qb, away_qb = row.home_qb_id, row.away_qb_id
        for qb in (home_qb, away_qb):
            if qb not in ratings:
                ratings[qb] = initial_rating

        pre_home_qb, pre_away_qb = ratings[home_qb], ratings[away_qb]

        # Expectation from TEAM Elo alone (QB identity plays no part here)
        expected_home = elo_win_probability(home_team_elo, away_team_elo, home_field_advantage)
        if row.home_score > row.away_score:
            actual_home = 1.0
            elo_diff_of_winner = (home_team_elo + home_field_advantage) - away_team_elo
        elif row.home_score < row.away_score:
            actual_home = 0.0
            elo_diff_of_winner = away_team_elo - (home_team_elo + home_field_advantage)
        else:
            actual_home = 0.5
            elo_diff_of_winner = 0.0

        margin = abs(row.home_score - row.away_score)
        multiplier = mov_multiplier(margin, elo_diff_of_winner)
        surprise = k * multiplier * (actual_home - expected_home)

        post_home_qb = pre_home_qb + surprise
        post_away_qb = pre_away_qb - surprise
        ratings[home_qb], ratings[away_qb] = post_home_qb, post_away_qb

        rows.append(
            {
                "game_id": row.game_id,
                "season": row.season,
                "home_qb_id": home_qb,
                "away_qb_id": away_qb,
                "home_qb_name": row.home_qb_name,
                "away_qb_name": row.away_qb_name,
                "home_pre_qb_elo": pre_home_qb,
                "away_pre_qb_elo": pre_away_qb,
                "home_post_qb_elo": post_home_qb,
                "away_post_qb_elo": post_away_qb,
            }
        )

    return pd.DataFrame(rows)
