"""Individual pass-rush rating: a real, previously-blocked capability.

**Corrects a claim in `src/model/pass_rush_elo.py`'s own docstring.** That
module's team-level design was justified by: "free nflverse play-by-play
records who got credit for a sack/QB hit, but not who was rushing (and
being blocked) on the plays where nobody did -- there's no full pass-rush
participation list." That was true using only nflverse's trimmed
play-by-play. It stopped being true once checked against nflverse's own
broader table menu (2026-08-21): `load_pfr_advstats(stat_type="def")` gives
real per-player-per-game pressure/hurry/hit/blitz counts, and
`load_snap_counts` gives the real missing piece -- a genuine denominator
(`defense_snaps`) -- joined on Pro Football Reference's own player/game IDs
at a verified 100% match rate. That denominator is exactly what was missing:
a player who rushed 40 times and got 0 pressures now looks different from
one who rushed 5 times and got 0 -- a fair, two-sided signal, not raw
production wearing a rating costume the way `pass_rush_elo.py::credited_pressure_counts`
explicitly avoided calling itself.

**Honest limits, not glossed over:**
- `defense_snaps` is total defensive snaps played, not literally "snaps
  where this player rushed the passer." For true pass-rush positions
  (`RUSH_POSITIONS` below), snaps are dominated by rush opportunities --
  DEs/DTs/NTs/EDGEs rarely drop into coverage -- so this is a reasonable
  proxy, not an exact one. Restricting to those positions (excluding LBs
  who split time between rushing and coverage more evenly) is the
  deliberate scope boundary that keeps the proxy honest.
- `load_pfr_advstats` is only available from **2018 onward** -- narrower
  than `pass_rush_elo.py`'s full 2015+ coverage. This is a companion, not
  a replacement.
- This is a **game-level rate rating**, not a literal play-by-play
  sequential Elo like `pass_rush_elo.py`'s team-level version (which
  updates after every single dropback). The update below is the closed-form
  equivalent of running that same per-play update `defense_snaps` times
  within one game, holding the pre-game rating's implied expectation fixed
  for the whole game rather than re-computing it after each snap -- a real
  simplification (this project doesn't have play-by-play rush assignment
  to do better), stated plainly rather than presented as identical to the
  team-level mechanic.

**Base rate, measured not guessed, same discipline as `pass_rush_elo.py`.**
Aggregate pressure rate across all real (position-filtered, `defense_snaps
> 0`) player-games in the 2018-2025 cache: 22,067 pressures / 574,315
snaps = **3.84%** -- lower than `pass_rush_elo.py`'s ~13.6% per-DROPBACK
rate, expected since this is per-SNAP (includes run-support snaps) for one
individual rather than per-dropback for a whole defense.
`DEFAULT_INDIVIDUAL_BASE_PRESSURE_OFFSET` is `-400 * log10(1/p - 1)` at that
measured `p`, the identical formula `pass_rush_elo.py`'s own offset uses.
"""

from __future__ import annotations

import pandas as pd

from src.model.elo import INITIAL_RATING, elo_win_probability

RUSH_POSITIONS = ("DE", "DT", "NT", "EDGE", "OLB")
DEFAULT_INDIVIDUAL_PRESSURE_K = 4.0  # per-snap K -- same value pass_rush_elo.py uses per-dropback
DEFAULT_INDIVIDUAL_BASE_PRESSURE_OFFSET = -559.5  # see module docstring -- measured from the 2018-2025 cache


def build_individual_pass_rush_frame(snap_counts: pd.DataFrame, pfr_advstats: pd.DataFrame) -> pd.DataFrame:
    """One row per player-game at a real pass-rush position with at least
    one defensive snap: `defense_snaps`, `def_pressures`, plus identifying
    columns. Joins on `pfr_player_id`/`pfr_game_id` (PFR's own IDs, shared
    by both tables -- verified 100% match rate, not a fuzzy name join).
    """
    merged = pfr_advstats.merge(
        snap_counts[["pfr_player_id", "pfr_game_id", "defense_snaps", "position"]],
        on=["pfr_player_id", "pfr_game_id"],
        how="inner",
    )
    return merged[merged["position"].isin(RUSH_POSITIONS) & (merged["defense_snaps"] > 0)].copy()


def compute_individual_pass_rush_ratings(
    player_games: pd.DataFrame,
    k: float = DEFAULT_INDIVIDUAL_PRESSURE_K,
    initial_rating: float = INITIAL_RATING,
    base_pressure_offset: float = DEFAULT_INDIVIDUAL_BASE_PRESSURE_OFFSET,
) -> pd.DataFrame:
    """One row per player-game: this player's individual pass-rush rating
    *entering* that game (pre-game, leakage-free) and after it.

    `player_games`: `build_individual_pass_rush_frame`'s output, needs at
    least `season`, `week`, `pfr_game_id`, `pfr_player_id`,
    `pfr_player_name`, `defense_snaps`, `def_pressures`.

    Update rule, in closed form (see module docstring for the "held fixed
    for the whole game" simplification this represents):
    `post = pre + k * defense_snaps * (observed_rate - expected_rate)`,
    where `expected_rate` compares the player's pre-game rating against a
    fixed league-average reference (`initial_rating`, 1500 -- there's no
    natural "opposing" individual rating the way team-vs-team or
    posteam-vs-defteam pass protection work, so this rates each player
    against the league baseline directly, the simplest defensible choice).
    """
    ordered = player_games.sort_values(["season", "week", "pfr_game_id", "pfr_player_id"])
    ratings: dict[str, float] = {}
    rows = []

    for row in ordered.itertuples():
        player_id = row.pfr_player_id
        if player_id not in ratings:
            ratings[player_id] = initial_rating

        pre_rating = ratings[player_id]
        expected_rate = elo_win_probability(pre_rating, initial_rating, base_pressure_offset)
        observed_rate = row.def_pressures / row.defense_snaps
        post_rating = pre_rating + k * row.defense_snaps * (observed_rate - expected_rate)
        ratings[player_id] = post_rating

        rows.append(
            {
                "pfr_player_id": player_id,
                "pfr_player_name": row.pfr_player_name,
                "season": row.season,
                "week": row.week,
                "team": row.team,
                "defense_snaps": row.defense_snaps,
                "def_pressures": row.def_pressures,
                "pre_individual_pass_rush_elo": pre_rating,
                "post_individual_pass_rush_elo": post_rating,
            }
        )

    return pd.DataFrame(rows)
