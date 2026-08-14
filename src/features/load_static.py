"""Pull free static nflverse data (schedules + closing lines) into data/static/.

This is the zero-cost dataset: opening/closing spread, total, and moneyline
lines plus final scores, back to 1999. It has no intraday snapshots — that's
what the live collector (src/collect/) exists to capture, starting this
season. This module only backs the backtester's settlement join and the
market baseline.
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


if __name__ == "__main__":
    # Ten most recent completed seasons: enough for feature/calibration work
    # without pulling the full 1999-present history on first run.
    path = load_schedules(list(range(2015, 2025)))
    print(f"wrote {path}")
