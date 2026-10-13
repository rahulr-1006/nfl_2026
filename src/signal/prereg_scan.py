"""Live, log-only scanning for the pre-registered H1 / H1b (preregistration_wk5-9.md).

**Logged, never texted.** The pre-registration requires these to accrue a live
record without influencing what gets bet until they pass on the Weeks 5-9
holdout. Nothing here imports the SMS path.

**A separate log file, on purpose.** `decision_report`, `shadow-report` and
`clv-report` all read `data/shadow_log.jsonl`. Writing H1/H1b there would put
their holdout CLV on screen before 2026-11-10 -- the "no peeking" rule broken by
a routine command. `data/shadow_log_prereg.jsonl` keeps the record intact and
out of every existing report; `shadow_log.recheck(path=...)` still measures
survival on it, which the pre-registration allows.

**Same code as the backtest.** Detection is `backtest.pinnacle_lag` with the
frozen parameters -- not a reimplementation -- so the live record and the Train
numbers cannot drift apart in definition. Its "first trigger per (contract,
side)" rule is enforced across ticks by skipping keys already in the log.

**Logs everything the rule selects**, including quotes above the 15% bad-quote
cap and rushing-yards legs: those exclusions are scoring decisions in the
pre-registration, applied when the holdout is scored, not filters on the record.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from src.backtest.pinnacle_lag import detect_moves, pinnacle_fair_path, stale_quotes
from src.signal.live_scan import upcoming_only
from src.signal.shadow_log import load, record_alert
from src.store.pit_store import PointInTimeStore

log = logging.getLogger(__name__)

PREREG_SHADOW_LOG_PATH = Path("data/shadow_log_prereg.jsonl")


@dataclass(frozen=True)
class FrozenStrategy:
    name: str
    min_move: float
    min_ev: float


# Frozen 2026-10-04 (preregistration_wk5-9.md §4). Changing either is a
# deviation that must be logged in the pre-registration's §6, not edited here.
H1 = FrozenStrategy("h1_pinnacle_lag", min_move=0.02, min_ev=0.01)
H1B = FrozenStrategy("h1b_stale_price", min_move=0.0, min_ev=0.01)
FROZEN_STRATEGIES = (H1, H1B)


class ReadOnceStore:
    """One `read_as_of` shared by the prereg scan and its survival recheck.

    Both read the whole store, and inside the launchd service each read took
    ~80s on 2026-10-04, so the two together added ~2m50s to every monitor tick
    -- delaying the NEXT tick's real alerts. The second caller gets the first
    read, filtered to its own `as_of`; the two calls are seconds apart, so it can
    miss at most a capture landing in between, which the next tick picks up.
    """

    def __init__(self, store: PointInTimeStore) -> None:
        self._store = store
        self._frame: pd.DataFrame | None = None

    def read_as_of(self, decision_time: datetime, event_id: str | None = None, dedupe: bool = True) -> pd.DataFrame:
        if self._frame is None:
            self._frame = self._store.read_as_of(decision_time)
        frame = self._frame[self._frame["capture_time"] <= decision_time]
        return frame if event_id is None else frame[frame["event_id"] == event_id]


def prereg_key(row: pd.Series, strategy: str) -> str:
    return f"{strategy}|{row['event_id']}|{row['player_name']}|{row['prop_stat']}|{row['line']}|{row['side']}"


def live_props(snapshots: pd.DataFrame, as_of: datetime) -> pd.DataFrame:
    """Upcoming games' player props, quotes captured before kickoff only."""
    props = upcoming_only(snapshots[snapshots["market"] == "player_prop"], as_of)
    return props[props["capture_time"] < props["event_start_time"]]


def find_spots(props: pd.DataFrame, strategy: FrozenStrategy) -> pd.DataFrame:
    """The bets `strategy` selects from `props`, shaped for the shadow log
    (`edge` = entry EV against Pinnacle's devigged fair)."""
    if props.empty:
        return pd.DataFrame()
    path = pinnacle_fair_path(props)
    if path.empty:
        return pd.DataFrame()
    spots = stale_quotes(detect_moves(path, strategy.min_move), props, strategy.min_ev)
    return spots.rename(columns={"entry_ev": "edge"}) if not spots.empty else spots


def run(store: PointInTimeStore, as_of: datetime | None = None, path: Path = PREREG_SHADOW_LOG_PATH) -> dict[str, int]:
    """One log-only pass. Returns legs newly recorded, per strategy."""
    as_of = as_of or datetime.now(UTC)
    props = live_props(store.read_as_of(as_of), as_of)
    already = {o.alert_key for o in load(path) if o.is_alert}
    recorded: dict[str, int] = {}
    for strategy in FROZEN_STRATEGIES:
        spots = find_spots(props, strategy)
        if not spots.empty:
            keys = spots.apply(lambda r, s=strategy.name: prereg_key(r, s), axis=1)
            spots = spots[~keys.isin(already)]
        recorded[strategy.name] = record_alert(
            spots, strategy.name, lambda r, s=strategy.name: prereg_key(r, s), now=as_of, path=path,
        ) if not spots.empty else 0
    log.info("prereg (log-only): recorded %s", recorded)
    return recorded
