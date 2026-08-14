"""Append-only, point-in-time odds store.

This is the leakage guard for the whole project: the backtester must never
see a price that did not exist yet at decision time. `read_as_of` is the
only read path, it always filters on `capture_time <= decision_time`, and
it re-checks its own output before returning (belt and suspenders — if this
invariant ever breaks, tests must fail loudly rather than silently leak
future data into a backtest).

Writes never overwrite: each batch lands in a new file named with a
timestamp + uuid, inside a directory partitioned by the UTC date of the
batch's capture time.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence
from uuid import uuid4

import pandas as pd

from src.store.schema import OddsSnapshot

_COLUMNS = [
    "capture_time",
    "event_id",
    "season",
    "week",
    "home_team",
    "away_team",
    "event_start_time",
    "book",
    "market",
    "side",
    "line",
    "price_american",
    "price_decimal",
    "implied_prob_raw",
]


def _to_dataframe(snapshots: Sequence[OddsSnapshot]) -> pd.DataFrame:
    rows = [
        {
            "capture_time": s.capture_time,
            "event_id": s.event_id,
            "season": s.season,
            "week": s.week,
            "home_team": s.home_team,
            "away_team": s.away_team,
            "event_start_time": s.event_start_time,
            "book": s.book,
            "market": s.market.value,
            "side": s.side.value,
            "line": s.line,
            "price_american": s.price_american,
            "price_decimal": s.price_decimal,
            "implied_prob_raw": s.implied_prob_raw,
        }
        for s in snapshots
    ]
    df = pd.DataFrame(rows, columns=_COLUMNS)
    df["capture_time"] = pd.to_datetime(df["capture_time"], utc=True)
    df["event_start_time"] = pd.to_datetime(df["event_start_time"], utc=True)
    return df


class LeakageError(RuntimeError):
    """Raised if a query would return (or returned) data from after decision_time."""


class PointInTimeStore:
    def __init__(self, root: Path | str = Path("data/snapshots")):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def write(self, snapshots: Sequence[OddsSnapshot]) -> Path:
        """Append one immutable batch. Never overwrites an existing file."""
        if not snapshots:
            raise ValueError("no snapshots to write")

        df = _to_dataframe(snapshots)
        capture_date = df["capture_time"].iloc[0].date()
        partition_dir = self.root / f"capture_date={capture_date.isoformat()}"
        partition_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}_{uuid4().hex[:8]}.parquet"
        path = partition_dir / filename
        if path.exists():
            raise FileExistsError(f"refusing to overwrite existing snapshot file {path}")

        df.to_parquet(path, index=False)
        return path

    def read_as_of(self, decision_time: datetime, event_id: str | None = None) -> pd.DataFrame:
        """The only read path. Returns rows visible at `decision_time`, and nothing later."""
        if decision_time.tzinfo is None:
            raise ValueError("decision_time must be tz-aware (use UTC)")

        df = self._read_all()
        if df.empty:
            return df

        result = self._filter(df, decision_time, event_id)

        if not result.empty and result["capture_time"].max() > decision_time:
            raise LeakageError(
                f"read_as_of({decision_time}) returned a row captured at "
                f"{result['capture_time'].max()} — this must never happen"
            )
        return result

    @staticmethod
    def _filter(df: pd.DataFrame, decision_time: datetime, event_id: str | None) -> pd.DataFrame:
        mask = df["capture_time"] <= decision_time
        if event_id is not None:
            mask &= df["event_id"] == event_id
        return df.loc[mask].reset_index(drop=True)

    def _read_all(self) -> pd.DataFrame:
        files = sorted(self.root.glob("**/*.parquet"))
        if not files:
            return pd.DataFrame(columns=_COLUMNS)
        frames = [pd.read_parquet(f) for f in files]
        return pd.concat(frames, ignore_index=True)
