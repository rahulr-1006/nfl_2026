"""Settlement for player-prop (Over/Under) bets against nflverse's
per-player game stats.

Deliberately a separate module from src/store/settlement.py rather than
an extra branch in settle(): team-market settlement grades against a
GameResult (home_score/away_score); prop settlement grades against a
single player's single stat value for that game, a different shape of
"result" entirely. Sharing the Outcome enum is enough shared surface --
forcing one function signature to cover both would be the wrong
abstraction.

`prop_stat` on OddsSnapshot (src/store/schema.py) is already the nflverse
player_stats column name (translated once at ingestion in
src/collect/props.py), so no market-key translation happens here --
this module just looks the column up.

Player names need the same "book vs. nflverse" reconciliation team names
already needed (src/collect/teams.py): odds books don't always format a
name the way nflverse's player_display_name does. Confirmed live
2026-08-18 pulling real historical props (KC/DEN, PHI/DAL, HOU/DET,
2024 week 10): "AJ Brown" (book) vs. "A.J. Brown" (nflverse) is pure
punctuation, normalize_player_name() alone fixes it; "Kenneth Gainwell"
vs. "Kenny Gainwell" is a real name difference, needs an explicit
PLAYER_NAME_OVERRIDES entry the way team-name overrides do. Two other
mismatches in that same test (Tim Patrick, Brock Wright) turned out to
have no player_stats row for that game at all -- not a name problem,
genuinely nothing to grade against -- so don't assume every unmatched
name needs an override; check nflverse's own game log first.
"""

from __future__ import annotations

import re

import pandas as pd

from src.store.schema import Side
from src.store.settlement import Outcome

# Confirmed player-name mismatches between odds books and nflverse's
# player_display_name that punctuation-stripping alone doesn't fix. Add an
# entry here only after confirming nflverse actually has a stat row for
# that player/game under a different name -- not every unmatched name is
# an override candidate (see module docstring).
PLAYER_NAME_OVERRIDES: dict[str, str] = {
    "Kenneth Gainwell": "Kenny Gainwell",
    # Found 2026-10-13: both had props on played 2026 games that never settled.
    "Hollywood Brown": "Marquise Brown",
    "Joshua Palmer": "Josh Palmer",
}

# Generational suffixes, which books and nflverse attach inconsistently in BOTH
# directions (measured 2026-10-13 on Weeks 1-5): books send "Michael Pittman Jr."
# where nflverse has "Michael Pittman", but "Chris Godwin" where nflverse has
# "Chris Godwin Jr." -- and "Deebo Samuel" vs "Deebo Samuel Sr.". Every such
# prop silently returned `None`, so a placed bet would never settle. Dropping
# the suffix on both sides is safe because matching is already scoped to one
# game: two players differing only by suffix would have to be in the same game.
_SUFFIX = re.compile(r"\s+(jr|sr|ii|iii|iv|v)$")


def normalize_player_name(name: str) -> str:
    """Collapse punctuation/whitespace differences between an odds book's
    player name and nflverse's player_display_name (e.g. "AJ Brown" vs.
    "A.J. Brown") into the same key, case-insensitively. Genuine name
    differences (nicknames) go through PLAYER_NAME_OVERRIDES first, since
    no amount of punctuation-stripping turns "Kenneth" into "Kenny".
    """
    resolved = PLAYER_NAME_OVERRIDES.get(name, name)
    no_periods = resolved.replace(".", "")  # "A.J." -> "AJ", not "A J" -- periods drop out, they don't become spaces
    collapsed = re.sub(r"\s+", " ", no_periods).strip().lower()
    return _SUFFIX.sub("", collapsed)


def build_player_stats_index(player_stats: pd.DataFrame) -> dict[tuple[str, str], dict[str, float]]:
    """(game_id, player_display_name) -> {stat_column: value}, from
    nflreadpy's load_player_stats() output (or any frame with the same
    game_id / player_display_name columns). Keyed by nflverse's own name
    exactly as given -- settle_prop_snapshots does its own normalized
    lookup on top of this for matching against odds-book names, which
    don't always agree with nflverse's formatting.

    Rows with no player_display_name at all are skipped -- confirmed
    against real 2024 data that nflverse itself carries a handful of
    these (22 of 18,983 rows that season), and there's no name to key or
    match against for them regardless.
    """
    stat_columns = [c for c in player_stats.columns if c not in ("game_id", "player_display_name")]
    index: dict[tuple[str, str], dict[str, float]] = {}
    for row in player_stats.itertuples(index=False):
        if pd.isna(row.player_display_name):
            continue
        key = (row.game_id, row.player_display_name)
        index[key] = {col: getattr(row, col) for col in stat_columns}
    return index


def settle_prop(side: Side, line: float, actual_value: float) -> Outcome:
    """Grade a single Over/Under prop bet. Pushes are real for integer-valued
    stats (receptions, TDs) landing exactly on the line -- unlike spread/total
    lines, which are usually set at a half-point specifically to avoid this,
    prop lines land on whole numbers often enough that push must be handled,
    not assumed away.
    """
    if side not in (Side.OVER, Side.UNDER):
        raise ValueError(f"prop side must be OVER or UNDER, got {side}")
    margin = (actual_value - line) if side == Side.OVER else (line - actual_value)
    if margin > 0:
        return Outcome.WIN
    if margin < 0:
        return Outcome.LOSS
    return Outcome.PUSH


def settle_prop_snapshots(snapshots: pd.DataFrame, player_stats: pd.DataFrame) -> pd.DataFrame:
    """Batch-grade prop-shaped rows (event_id/game_id, player_name,
    prop_stat, side, line columns) against player_stats. Adds an `outcome`
    column; `None` where the player's stat for that game isn't in
    player_stats yet (game not played, or a name that didn't match --
    never silently dropped, same discipline as settle_snapshots).

    Matches on normalize_player_name(), not the raw name, so "AJ Brown"
    (a book) and "A.J. Brown" (nflverse) resolve to the same player --
    see module docstring for the real mismatches this was built against.
    """
    stats_index = {
        (game_id, normalize_player_name(name)): stats for (game_id, name), stats in build_player_stats_index(player_stats).items()
    }

    def _grade(row: pd.Series) -> str | None:
        game_stats = stats_index.get((row.event_id, normalize_player_name(row.player_name)))
        if game_stats is None or row.prop_stat not in game_stats:
            return None
        actual_value = game_stats[row.prop_stat]
        if pd.isna(actual_value):
            return None
        side = row.side if isinstance(row.side, Side) else Side(row.side)
        return settle_prop(side, row.line, actual_value).value

    graded = snapshots.copy()
    graded["outcome"] = graded.apply(_grade, axis=1)
    return graded
