"""Pull free static nflverse data (schedules + closing lines) into data/static/.

This is the zero-cost dataset: opening/closing spread, total, and moneyline
lines plus final scores, back to 1999. It has no intraday snapshots — that's
what the live collector (src/collect/) exists to capture, starting this
season. This module only backs the backtester's settlement join and the
market baseline.

nflverse's `spread_line` column uses the opposite sign convention from a
sportsbook-posted side line: use home_spread_line() below to convert it
before passing to src/store/settlement.settle(), never the raw column.
"""

from __future__ import annotations

from pathlib import Path

import nflreadpy as nfl

STATIC_DIR = Path("data/static")


def load_schedules(seasons: list[int], out_dir: Path = STATIC_DIR) -> Path:
    """Fetch nflverse schedules (scores + closing lines) and cache as parquet."""
    out_dir.mkdir(parents=True, exist_ok=True)
    df = nfl.load_schedules(seasons=seasons)
    path = out_dir / f"schedules_{min(seasons)}_{max(seasons)}.parquet"
    df.write_parquet(path)
    return path


def home_spread_line(spread_line: float) -> float:
    """Convert nflverse's spread_line into the sportsbook side-line
    convention that OddsSnapshot.line / settlement.settle() expect.

    nflverse signs spread_line as the home team's projected margin
    (positive = home favored, e.g. +7.5 means home projected to win by
    7.5). A sportsbook-posted side line does the opposite (negative =
    favored, e.g. -7.5 to bet the home favorite). They're the same number
    with flipped sign -- this function is that flip, named so the
    conversion can't be silently skipped or gotten backwards again.
    """
    return -float(spread_line)


if __name__ == "__main__":
    # Ten most recent completed seasons: enough for feature/calibration work
    # without pulling the full 1999-present history on first run.
    path = load_schedules(list(range(2015, 2025)))
    print(f"wrote {path}")
