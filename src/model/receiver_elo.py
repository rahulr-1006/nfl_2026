"""Receiver-level Elo: a play-level rating for pass-catchers, run against a
companion pass-defense Elo, for player-prop pricing rather than game outcomes.

**Why play-level, not game-level like `elo.py`/`qb_elo.py`.** Team and QB Elo
treat one game as one match with a win/loss outcome. A receiver doesn't have
a per-game win/loss -- what exists is a sequence of individual targets. So
this module treats every target as its own two-sided Elo match: the targeted
receiver vs. the opposing team's pass defense, with the play's `success` flag
(already in the cached pbp, standard EPA-success definition) as the binary
outcome. This is a legitimate, well-established Elo generalization (any
repeated pairwise binary contest), not a residual-vs-baseline hack the way
`qb_elo.py` is.

**What this is not:** true man-to-man coverage matchup data (which specific
cornerback was assigned to a given receiver on a given snap) isn't in free
nflverse play-by-play -- that's PFF/NGS charting, paywalled. `defteam` is the
finest opponent-side grain available for free, so the companion rating here
is a team-level **pass defense** Elo, not a corner-specific one. Still a real,
laggable signal for props: "this receiver is hot, this week's opponent pass
defense is Elo-weak" is information a book can be slow to fully price in.

**Leakage-free the same way team/QB Elo are:** plays processed in strict
chronological order (season, week, game_id, then `play_id` -- nflverse's
within-game play sequence number), a rating entering a play reflects only
targets/defensive snaps strictly before it.

**K is small (`DEFAULT_TARGET_K = 4.0`) relative to team Elo's K=20 or QB
Elo's K=8** -- deliberately, since a receiver sees many targets per game
(unlike one game-level contest), so each individual play should move the
rating only a little.
"""

from __future__ import annotations

import pandas as pd

from src.model.elo import INITIAL_RATING, canonical_team, elo_win_probability

DEFAULT_TARGET_K = 4.0


def compute_receiver_elo_ratings(
    pbp: pd.DataFrame,
    k: float = DEFAULT_TARGET_K,
    initial_rating: float = INITIAL_RATING,
) -> pd.DataFrame:
    """One row per target (pass play with a recorded receiver): the
    receiver's and the opposing pass defense's Elo ratings *entering* that
    play (pre-play, leakage-free), plus post-play ratings for reference.

    `pbp`: nflverse play-by-play with at least `season`, `week`, `game_id`,
    `play_id`, `defteam`, `receiver_player_id`, `receiver_player_name`,
    `success` -- see `src/features/load_static.py::PBP_COLUMNS`. Rows
    without a targeted receiver (`receiver_player_id` null -- non-pass
    plays, sacks, scrambles) or a null `success` are excluded; not every
    dropback has a recorded target.
    """
    targets = pbp.dropna(subset=["receiver_player_id", "success"]).copy()
    targets["defteam"] = targets["defteam"].map(canonical_team)
    targets = targets.sort_values(["season", "week", "game_id", "play_id"])

    receiver_ratings: dict[str, float] = {}
    defense_ratings: dict[str, float] = {}
    rows = []

    for row in targets.itertuples():
        receiver = row.receiver_player_id
        defense = row.defteam

        if receiver not in receiver_ratings:
            receiver_ratings[receiver] = initial_rating
        if defense not in defense_ratings:
            defense_ratings[defense] = initial_rating

        pre_receiver = receiver_ratings[receiver]
        pre_defense = defense_ratings[defense]

        expected = elo_win_probability(pre_receiver, pre_defense, 0.0)
        actual = float(row.success)
        surprise = k * (actual - expected)

        post_receiver = pre_receiver + surprise
        post_defense = pre_defense - surprise
        receiver_ratings[receiver] = post_receiver
        defense_ratings[defense] = post_defense

        rows.append(
            {
                "game_id": row.game_id,
                "season": row.season,
                "week": row.week,
                "play_id": row.play_id,
                "receiver_player_id": receiver,
                "receiver_player_name": row.receiver_player_name,
                "defteam": defense,
                "success": actual,
                "pre_receiver_elo": pre_receiver,
                "pre_pass_defense_elo": pre_defense,
                "post_receiver_elo": post_receiver,
                "post_pass_defense_elo": post_defense,
            }
        )

    return pd.DataFrame(rows)
