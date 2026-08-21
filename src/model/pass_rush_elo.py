"""Pass-rush Elo: a play-level, team-level rating of pass-rush vs.
pass-protection strength, for player-prop pricing (sack props, QB-under-
pressure props) rather than game outcomes.

**Why team-level, not player-level like `receiver_elo.py` -- CORRECTED
2026-08-21, see `src/model/individual_pass_rush_elo.py`.** This module was
originally built on the assumption that free nflverse play-by-play records
*who got credit* for a sack or QB hit, but not who was rushing (and being
blocked) on the plays where nobody did -- no full pass-rush participation
list, so a player-level Elo built only from credited plays would only ever
see wins, never losses. **That was true using only nflverse's own trimmed
play-by-play, but not true of nflverse's broader table menu**: joining
`load_pfr_advstats(stat_type="def")`'s per-player pressure counts against
`load_snap_counts`'s `defense_snaps` (on PFR's own player/game IDs, 100%
match rate) supplies exactly the missing denominator, for real pass-rush
positions where snaps are a reasonable proxy for pass-rush opportunity.
See `individual_pass_rush_elo.py`'s module docstring for the full design
and its own honest limits (2018+ coverage only, a rate-based rating not a
literal play-by-play sequential one). This team-level module remains real
and useful in its own right -- full 2015+ coverage, and a genuinely
different (team-vs-team, not individual) question -- not superseded, just
no longer the only option.

This module rates the two units that ARE fully observed on every dropback
from nflverse's own play-by-play alone: the offense's pass protection
(`posteam`) and the defense's pass rush (`defteam`).

**Design, same mechanic as `receiver_elo.py`:** every dropback (`pass == 1`,
including sacks -- nflverse's `pass` flag already covers them) is a
two-sided Elo match between `defteam`'s pass-rush rating and `posteam`'s
pass-protection rating. The outcome is "did the rush win the play" -- a
sack or a QB hit (`sack == 1` or `qb_hit == 1`), a combined ~13.6% base
rate across the 2015-2024 cache, checked before building this. K=4, same
order as `receiver_elo.py`'s target-level K -- many dropbacks per game, not
one game-level contest.

**Leakage-free the same way:** plays processed in strict chronological
order (season, week, game_id, then `play_id`).

**A base-rate offset, unlike `receiver_elo.py`.** A target's `success` rate
is close to 50/50 (~49.5% measured) -- close enough that two ratings starting
at 1500 need no correction. Pressure events are not: ~13.6% base rate. Without
a correction, every single play would surprise the rush side downward on
average, so both ratings would drift monotonically away from 1500 forever
with no informative center -- not a fair signal, just the base rate leaking
into the numbers. `DEFAULT_BASE_PRESSURE_OFFSET` fixes this exactly the way
`elo.py`'s `home_field_advantage` fixes the ~50-55% home-win base rate: it's
handed to `elo_win_probability` as the third argument, so a league-average
rush unit (1500) vs. a league-average protection unit (1500) is *expected* to
produce a pressure ~13.6% of the time, not 50%. Rating differences from 1500
then reflect real above/below-average strength, not the mechanical base rate.
Derived from the 2015-2024 cache's own measured pressure rate (`p`):
`-400 * log10(1/p - 1)`, the inverse of the logistic transform at rating
parity -- not an arbitrary guess, the same spirit as `DEFAULT_HOME_FIELD_ADVANTAGE`.

**A separate, explicitly-not-Elo companion:** `credited_pressure_counts()`
below is a raw per-player count of sacks/half-sacks/QB hits from nflverse's
own play-by-play alone -- useful as a named-player leaderboard for context,
still deliberately not blended into the Elo rating above (raw pbp still has
no exposure denominator on its own). For an actual individual-level rating
with a real denominator, see `individual_pass_rush_elo.py` instead.
"""

from __future__ import annotations

import pandas as pd

from src.model.elo import INITIAL_RATING, canonical_team, elo_win_probability

DEFAULT_PRESSURE_K = 4.0
DEFAULT_BASE_PRESSURE_OFFSET = -320.6  # see module docstring -- derived from the ~13.6% measured 2015-2024 pressure rate


def compute_pass_rush_elo_ratings(
    pbp: pd.DataFrame,
    k: float = DEFAULT_PRESSURE_K,
    initial_rating: float = INITIAL_RATING,
    base_pressure_offset: float = DEFAULT_BASE_PRESSURE_OFFSET,
) -> pd.DataFrame:
    """One row per dropback: `posteam`'s pass-protection Elo and
    `defteam`'s pass-rush Elo *entering* that play (pre-play, leakage-free),
    plus post-play ratings for reference.

    `pbp`: nflverse play-by-play with at least `season`, `week`, `game_id`,
    `play_id`, `posteam`, `defteam`, `pass`, `sack`, `qb_hit` -- see
    `src/features/load_static.py::PBP_COLUMNS`. Rows with `pass != 1` or a
    null `sack`/`qb_hit` are excluded (nflverse leaves both null on a
    handful of non-standard plays, e.g. penalties before the snap).
    """
    dropbacks = pbp[pbp["pass"] == 1].dropna(subset=["sack", "qb_hit"]).copy()
    dropbacks["posteam"] = dropbacks["posteam"].map(canonical_team)
    dropbacks["defteam"] = dropbacks["defteam"].map(canonical_team)
    dropbacks = dropbacks.sort_values(["season", "week", "game_id", "play_id"])

    rush_ratings: dict[str, float] = {}
    protection_ratings: dict[str, float] = {}
    rows = []

    for row in dropbacks.itertuples():
        rush_team = row.defteam
        protection_team = row.posteam

        if rush_team not in rush_ratings:
            rush_ratings[rush_team] = initial_rating
        if protection_team not in protection_ratings:
            protection_ratings[protection_team] = initial_rating

        pre_rush = rush_ratings[rush_team]
        pre_protection = protection_ratings[protection_team]

        expected = elo_win_probability(pre_rush, pre_protection, base_pressure_offset)
        actual = 1.0 if (row.sack == 1 or row.qb_hit == 1) else 0.0
        surprise = k * (actual - expected)

        post_rush = pre_rush + surprise
        post_protection = pre_protection - surprise
        rush_ratings[rush_team] = post_rush
        protection_ratings[protection_team] = post_protection

        rows.append(
            {
                "game_id": row.game_id,
                "season": row.season,
                "week": row.week,
                "play_id": row.play_id,
                "defteam": rush_team,
                "posteam": protection_team,
                "pressure": actual,
                "pre_pass_rush_elo": pre_rush,
                "pre_pass_protection_elo": pre_protection,
                "post_pass_rush_elo": post_rush,
                "post_pass_protection_elo": post_protection,
            }
        )

    return pd.DataFrame(rows)


def credited_pressure_counts(pbp: pd.DataFrame) -> pd.DataFrame:
    """Raw per-player counts of sacks (full credit), half-sacks (0.5
    credit), and QB hits -- **not an Elo rating**, a production leaderboard.
    Deliberately separate from `compute_pass_rush_elo_ratings`: see this
    module's docstring for why a fair individual pass-rush Elo isn't
    buildable on free participation data.
    """
    sack_credit: dict[str, float] = {}
    hit_count: dict[str, int] = {}
    names: dict[str, str] = {}

    full_sack_cols = [("sack_player_id", "sack_player_name", 1.0)]
    half_sack_cols = [
        ("half_sack_1_player_id", "half_sack_1_player_name", 0.5),
        ("half_sack_2_player_id", "half_sack_2_player_name", 0.5),
    ]
    hit_cols = [
        ("qb_hit_1_player_id", "qb_hit_1_player_name", None),
        ("qb_hit_2_player_id", "qb_hit_2_player_name", None),
    ]

    for id_col, name_col, credit in full_sack_cols + half_sack_cols:
        credited = pbp.dropna(subset=[id_col])
        for player_id, player_name in zip(credited[id_col], credited[name_col], strict=True):
            sack_credit[player_id] = sack_credit.get(player_id, 0.0) + credit
            names[player_id] = player_name

    for id_col, name_col, _ in hit_cols:
        credited = pbp.dropna(subset=[id_col])
        for player_id, player_name in zip(credited[id_col], credited[name_col], strict=True):
            hit_count[player_id] = hit_count.get(player_id, 0) + 1
            names[player_id] = player_name

    all_ids = set(sack_credit) | set(hit_count)
    return pd.DataFrame(
        [
            {
                "player_id": pid,
                "player_name": names[pid],
                "sacks": sack_credit.get(pid, 0.0),
                "qb_hits": hit_count.get(pid, 0),
            }
            for pid in all_ids
        ]
    )
