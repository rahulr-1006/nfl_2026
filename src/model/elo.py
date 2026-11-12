"""Elo rating system: opponent-adjusted team strength, sequential and
leakage-free by construction.

**Why Elo, and why now.** src/model/features.py's EPA-per-play features
have no opponent adjustment -- a team's rolling EPA looks the same whether
it was earned against a good defense or a bad one. Elo is the standard,
widely-cited fix for that specific gap in the sports-analytics literature
(this implementation follows FiveThirtyEight's NFL Elo methodology, the
most commonly referenced version): every team's rating is *relative to
who it played*, updated one game at a time.

**Leakage-free by construction, not by a shift() trick.** Unlike EPA
(where a rolling window has to be explicitly shifted so a game's own
result doesn't leak into its own feature -- see features.py's docstring),
Elo is inherently sequential: processing games in chronological order and
recording each team's rating *before* that game's update already means a
game can never influence its own pre-game rating. The discipline is the
same; the mechanism enforcing it is different.

**Known weakness, stated up front:** team-level Elo alone is a mediocre
game-outcome predictor -- it only knows "how good has this team been,"
not the richer play-level context EPA captures (this is well documented
in the sports-forecasting literature). It's built here as an
opponent-adjustment *feature* to fold into the existing EPA model, and as
groundwork for player-level Elo (head-to-head/positional matchups for
props), which is the more novel use of the same math -- not yet built,
see the player_props_infra memory for why player props themselves are
still gated on paid historical access.

**Franchise continuity across relocations.** nflverse's schedule data
uses the historical abbreviation for pre-relocation seasons (SD 2015-16,
OAK 2015-19, STL 2015) and the current one after (LAC, LV, LA
respectively) -- confirmed against the cached schedule, not guessed.
Naive per-abbreviation tracking would treat these as brand-new teams
starting over at the initial rating right when a relocated franchise
should carry its rating forward. FRANCHISE_ALIASES canonicalizes before
tracking, the same problem src/collect/teams.py already solved for live
team-name matching, solved again here for a different data source.
"""

from __future__ import annotations

import math

import pandas as pd

INITIAL_RATING = 1500.0
DEFAULT_K = 20.0  # FiveThirtyEight's NFL K-factor
DEFAULT_HOME_FIELD_ADVANTAGE = 48.0  # Elo points added to the home team pre-game
DEFAULT_SEASON_REVERSION = 1 / 3  # fraction reverted toward 1500 at the start of each new season

FRANCHISE_ALIASES: dict[str, str] = {"SD": "LAC", "OAK": "LV", "STL": "LA"}


def canonical_team(abbr: str) -> str:
    """Map a historical/relocated abbreviation to the current one a
    franchise's rating should be tracked under.
    """
    return FRANCHISE_ALIASES.get(abbr, abbr)


def elo_win_probability(rating_a: float, rating_b: float, home_field_advantage: float = 0.0) -> float:
    """Standard Elo logistic transform: P(a beats b), with `a` treated as
    the side `home_field_advantage` applies to (0 for a neutral matchup).
    """
    return 1.0 / (1.0 + 10 ** (-((rating_a + home_field_advantage) - rating_b) / 400.0))


def mov_multiplier(margin: float, elo_diff_of_winner: float) -> float:
    """FiveThirtyEight's margin-of-victory multiplier:
    ln(|margin| + 1) * (2.2 / (elo_diff_of_winner * 0.001 + 2.2))

    Bigger margins move the rating more (log-dampened, not linear), but a
    big favorite (large elo_diff_of_winner) winning big gets *less* credit
    per point of margin than an underdog would -- corrects for "beating up
    on a team you were already better than" inflating the rating further.
    A tie (margin=0) returns 1.0: the raw K*(S-E) term alone still moves
    the rating correctly on a tie, this multiplier should not zero it out.
    """
    if margin == 0:
        return 1.0
    return math.log(abs(margin) + 1) * (2.2 / (elo_diff_of_winner * 0.001 + 2.2))


def update_elo(
    rating_home: float,
    rating_away: float,
    home_score: int,
    away_score: int,
    k: float = DEFAULT_K,
    home_field_advantage: float = DEFAULT_HOME_FIELD_ADVANTAGE,
) -> tuple[float, float]:
    """One game's Elo update. Zero-sum: whatever the home team gains, the
    away team loses, and vice versa.
    """
    expected_home = elo_win_probability(rating_home, rating_away, home_field_advantage)
    if home_score > away_score:
        actual_home = 1.0
        elo_diff_of_winner = (rating_home + home_field_advantage) - rating_away
    elif home_score < away_score:
        actual_home = 0.0
        elo_diff_of_winner = (rating_away) - (rating_home + home_field_advantage)
    else:
        actual_home = 0.5
        elo_diff_of_winner = 0.0  # no winner; mov_multiplier(0, ...) short-circuits to 1.0 regardless

    margin = abs(home_score - away_score)
    multiplier = mov_multiplier(margin, elo_diff_of_winner)
    delta = k * multiplier * (actual_home - expected_home)

    return rating_home + delta, rating_away - delta


def compute_team_elo_ratings(
    schedule: pd.DataFrame,
    k: float = DEFAULT_K,
    home_field_advantage: float = DEFAULT_HOME_FIELD_ADVANTAGE,
    season_reversion: float = DEFAULT_SEASON_REVERSION,
    initial_rating: float = INITIAL_RATING,
) -> pd.DataFrame:
    """One row per game: each team's Elo rating *entering* that game (pre-game,
    leakage-free) plus the post-game ratings for reference. Processes
    `schedule` in chronological order (season, then gameday) so every
    team's pre-game rating reflects only games strictly before it.

    At the first game of a new season for a given team, its rating is
    partially reverted toward `initial_rating` first (roster turnover
    between seasons) -- `season_reversion` is the fraction reverted, not
    the fraction kept (0.0 = no reversion, 1.0 = full reset).

    Only completed games (both scores present) update ratings; future/
    unplayed games are not expected in `schedule` here -- pass a schedule
    already filtered to played games, same expectation as
    src/store/settlement.py::build_results_index.
    """
    games = schedule.dropna(subset=["home_score", "away_score"]).copy()
    games["home_team"] = games["home_team"].map(canonical_team)
    games["away_team"] = games["away_team"].map(canonical_team)
    games = games.sort_values(["season", "gameday", "game_id"])

    ratings: dict[str, float] = {}
    last_season_seen: dict[str, int] = {}
    rows = []

    for row in games.itertuples():
        for team in (row.home_team, row.away_team):
            if team not in ratings:
                ratings[team] = initial_rating
                last_season_seen[team] = row.season
            elif row.season > last_season_seen[team]:
                ratings[team] = initial_rating + (ratings[team] - initial_rating) * (1 - season_reversion)
                last_season_seen[team] = row.season

        pre_home, pre_away = ratings[row.home_team], ratings[row.away_team]
        post_home, post_away = update_elo(
            pre_home, pre_away, int(row.home_score), int(row.away_score), k=k, home_field_advantage=home_field_advantage
        )
        ratings[row.home_team], ratings[row.away_team] = post_home, post_away

        rows.append(
            {
                "game_id": row.game_id,
                "season": row.season,
                "home_team": row.home_team,
                "away_team": row.away_team,
                "home_pre_elo": pre_home,
                "away_pre_elo": pre_away,
                "home_post_elo": post_home,
                "away_post_elo": post_away,
            }
        )

    return pd.DataFrame(rows)


# A game's result is treated as known this long after kickoff. NFL games run
# about 3h15m; 4h leaves room for overtime and a slow final score feed, and errs
# toward treating a game as still unplayed (never the leaky direction).
GAME_DURATION = pd.Timedelta(hours=4)


def team_elo_as_of(
    ratings: pd.DataFrame,
    kickoffs: pd.Series,
    team: str,
    as_of: pd.Timestamp,
    target_season: int,
    target_kickoff: pd.Timestamp,
    initial_rating: float = INITIAL_RATING,
    season_reversion: float = DEFAULT_SEASON_REVERSION,
) -> float:
    """`team`'s rating using only games that had FINISHED by `as_of`.

    `compute_team_elo_ratings`' `*_pre_elo` is the rating entering a game, which
    assumes every earlier game is already known. An early price posted 5 days out
    can predate the team's previous game (Monday night -> next week's lookahead
    line), so the plain pre-game rating would contain a result the market hadn't
    seen. This returns what was knowable at `as_of` instead:

    - the team has a game that kicked off before `target_kickoff` but hadn't
      finished by `as_of` -> the rating entering the EARLIEST such game, which is
      exactly "all games finished by `as_of`" (and already carries any
      season-start reversion);
    - otherwise -> the post-game rating of its last finished game, reverted toward
      `initial_rating` if `target_season` is a later season (the same reversion
      `compute_team_elo_ratings` applies at a team's first game of a season);
    - no finished game at all -> `initial_rating`.

    `ratings` is `compute_team_elo_ratings`' output; `kickoffs` maps its
    `game_id` to a UTC kickoff. Team names must already be canonical.
    """
    games = ratings[(ratings["home_team"] == team) | (ratings["away_team"] == team)]
    ko = games["game_id"].map(kickoffs)
    if ko.isna().any():
        raise ValueError(f"missing kickoff for {games.loc[ko.isna(), 'game_id'].tolist()}")
    is_home = games["home_team"] == team
    pre = games["home_pre_elo"].where(is_home, games["away_pre_elo"])
    post = games["home_post_elo"].where(is_home, games["away_post_elo"])

    unfinished = (ko + GAME_DURATION > as_of) & (ko < target_kickoff)
    if unfinished.any():
        return float(pre[unfinished].loc[ko[unfinished].idxmin()])

    finished = ko + GAME_DURATION <= as_of
    if not finished.any():
        return initial_rating
    last = ko[finished].idxmax()
    rating = float(post.loc[last])
    if target_season > int(games.loc[last, "season"]):
        rating = initial_rating + (rating - initial_rating) * (1 - season_reversion)
    return rating
