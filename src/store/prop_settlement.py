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
"""

from __future__ import annotations

import pandas as pd

from src.store.schema import Side
from src.store.settlement import Outcome


def build_player_stats_index(player_stats: pd.DataFrame) -> dict[tuple[str, str], dict[str, float]]:
    """(game_id, player_display_name) -> {stat_column: value}, from
    nflreadpy's load_player_stats() output (or any frame with the same
    game_id / player_display_name columns).
    """
    stat_columns = [c for c in player_stats.columns if c not in ("game_id", "player_display_name")]
    index: dict[tuple[str, str], dict[str, float]] = {}
    for row in player_stats.itertuples(index=False):
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
    """
    stats_index = build_player_stats_index(player_stats)

    def _grade(row: pd.Series) -> str | None:
        game_stats = stats_index.get((row.event_id, row.player_name))
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
