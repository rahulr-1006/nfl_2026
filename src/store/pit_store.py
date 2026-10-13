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

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
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
    "player_name",
    "prop_stat",
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
            "player_name": s.player_name,
            "prop_stat": s.prop_stat,
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


# One price observation is identified by WHEN it was seen plus WHICH contract it
# is. `prop_stat` is load-bearing and easy to omit: a single player can carry
# `passing_tds` and `rushing_yards` at the same `line` value (2.5) from the same
# book at the same instant -- leaving it out makes two unrelated contracts look
# like one contract with two prices. (That mistake produced a false "2,752
# conflicting prices" reading on 2026-08-23; the real count is 1.)
CONTRACT_KEY = [
    "capture_time", "event_id", "book", "market", "side",
    "player_name", "prop_stat", "line",
]


class PointInTimeStore:
    def __init__(self, root: Path | str = Path("data/snapshots")):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        # The deduped full store, keyed by the exact file listing it was read
        # from -- see `_deduped_all` for why this is safe.
        self._cache_files: tuple[Path, ...] | None = None
        self._cache_frame: pd.DataFrame | None = None

    def write(self, snapshots: Sequence[OddsSnapshot]) -> Path:
        """Append one immutable batch. Never overwrites an existing file."""
        if not snapshots:
            raise ValueError("no snapshots to write")

        df = _to_dataframe(snapshots)
        capture_date = df["capture_time"].iloc[0].date()
        partition_dir = self.root / f"capture_date={capture_date.isoformat()}"
        partition_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%f')}_{uuid4().hex[:8]}.parquet"
        path = partition_dir / filename
        if path.exists():
            raise FileExistsError(f"refusing to overwrite existing snapshot file {path}")

        df.to_parquet(path, index=False)
        return path

    def read_as_of(
        self, decision_time: datetime, event_id: str | None = None, dedupe: bool = True
    ) -> pd.DataFrame:
        """The only read path. Returns rows visible at `decision_time`, and nothing later.

        **`dedupe` collapses repeat observations of the same contract at the same
        instant, so reads are deterministic.** The store is append-only by design
        and a re-run of a historical pull can legitimately re-record rows it
        already holds; measured on the real store, 6,300 such groups are
        byte-identical (pure re-writes) and exactly **one** carries two different
        prices (Khalil Herbert receptions 1.5, betonlineag, 2023-09-24: -119 and
        -125). Selectors like `engine.latest_fair_prob` pick via `idxmax` on
        `capture_time`, which is *ambiguous* across tied rows -- so without this
        the chosen price could differ between runs.

        The tie-break is last-in-sorted-file-order: stable across runs, and
        deliberately **neutral**. Picking the better price would flatter every EV
        and CLV number computed downstream, which is the one direction a betting
        system must never round toward.

        Nothing is mutated -- the store still holds every row. Pass
        `dedupe=False` to audit the raw record.
        """
        if decision_time.tzinfo is None:
            raise ValueError("decision_time must be tz-aware (use UTC)")

        if dedupe:
            df = self._deduped_all()
            if df.empty:
                return df.copy()  # never hand out the cached object itself
            result = self._filter(df, decision_time, event_id)
        else:
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

    def _files(self) -> list[Path]:
        return sorted(self.root.glob("**/*.parquet"))

    def _deduped_all(self) -> pd.DataFrame:
        """The whole store, deduped, read from disk only when the file listing
        has changed since the last call on this instance.

        **Why (2026-10-13):** every scanner in a monitor tick calls `read_as_of`,
        and each call re-read all ~7,400 files (10s interactively, ~80s under
        launchd's background priority) and re-deduped 7.2M rows. The tick had
        grown to a ~17-min median against a 5-min schedule, and survival of
        `prop_arb` alerts depends directly on that latency.

        **Why the result is identical to an uncached read:** files are
        immutable and only ever added (`write` refuses to overwrite), so an
        unchanged listing means unchanged contents, and a capture landing
        mid-tick changes the listing and forces a re-read. Deduping before
        filtering instead of after gives the same rows: duplicates share every
        CONTRACT_KEY column, `capture_time` and `event_id` included, so a
        time/event filter always keeps or drops a duplicate group whole, and
        both operations preserve file order for the `keep="last"` tie-break.
        Callers never receive the cached frame itself -- `_filter` returns a copy.
        """
        files = tuple(self._files())
        if files != self._cache_files or self._cache_frame is None:
            df = self._read_files(list(files))
            self._cache_frame = df.drop_duplicates(subset=CONTRACT_KEY, keep="last") if not df.empty else df
            self._cache_files = files
        return self._cache_frame

    def _read_all(self) -> pd.DataFrame:
        return self._read_files(self._files())

    @staticmethod
    def _read_files(files: list[Path]) -> pd.DataFrame:
        if not files:
            return pd.DataFrame(columns=_COLUMNS)
        frames = [pd.read_parquet(f) for f in files]
        # reindex to the current _COLUMNS, not just the union of whatever
        # columns happen to already be on disk -- a schema addition (e.g.
        # player_name/prop_stat) must be visible even before any file using
        # it has actually been written, or downstream code indexing that
        # column breaks until the first new-shaped snapshot lands.
        return pd.concat(frames, ignore_index=True).reindex(columns=_COLUMNS)


def kickoffs_from_store(store: PointInTimeStore, as_of: datetime | None = None) -> dict[str, datetime]:
    """event_id -> kickoff, from the store's own `event_start_time`.

    Lives here rather than in a consumer because it has no caller-specific
    logic -- it reads a column this module owns. It previously sat in
    `store/bet_log.py`, which forced the live alerting service to import the
    backtest engine and settlement machinery just to learn when games start.

    Preferred over joining a schedule file: the store already records the exact
    kickoff each quote was priced against, so this needs no column-name guessing
    and stays correct for any event the collector actually saw.
    """
    df = store.read_as_of(as_of or datetime.now(UTC))
    if df.empty:
        return {}
    return df.groupby("event_id")["event_start_time"].max().to_dict()
