"""Budget-aware polling cadence.

The Odds API bills `regions x markets` credits per call, independent of
event count. On a 500-credit/month free tier, a fixed "poll every 30
minutes" cadence (as the blueprint originally sketched) would exhaust the
whole month's quota in the first week or two. `decide_poll` is the pure
function that fixes that: it spreads remaining credits evenly across the
remaining time in the billing period, tightens cadence near kickoffs, and
degrades to a cheaper market set before giving up entirely.

Kept free of I/O (no requests, no filesystem) so it's fully unit-testable
with plain datetimes and ints. State persistence (CollectorState) and
header parsing live in this module too since they're small, but callers
own the actual file/network I/O.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path


@dataclass(frozen=True)
class QuotaState:
    remaining: int | None
    used: int | None
    last_cost: int | None
    observed_at: datetime


def parse_quota_headers(headers: Mapping[str, str]) -> QuotaState:
    def _int_or_none(key: str) -> int | None:
        value = headers.get(key)
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    return QuotaState(
        remaining=_int_or_none("x-requests-remaining"),
        used=_int_or_none("x-requests-used"),
        last_cost=_int_or_none("x-requests-last"),
        observed_at=datetime.now(UTC),
    )


@dataclass(frozen=True)
class CollectorState:
    """Persisted to disk between process restarts (default: data/collect_state.json)."""

    last_poll_time: datetime | None
    remaining_credits: int | None
    period_anchor: date
    consecutive_failures: int = 0

    def to_json(self) -> str:
        d = asdict(self)
        d["last_poll_time"] = self.last_poll_time.isoformat() if self.last_poll_time else None
        d["period_anchor"] = self.period_anchor.isoformat()
        return json.dumps(d)

    @classmethod
    def from_json(cls, raw: str) -> CollectorState:
        d = json.loads(raw)
        return cls(
            last_poll_time=datetime.fromisoformat(d["last_poll_time"]) if d["last_poll_time"] else None,
            remaining_credits=d["remaining_credits"],
            period_anchor=date.fromisoformat(d["period_anchor"]),
            consecutive_failures=d.get("consecutive_failures", 0),
        )


def load_state(path: Path) -> CollectorState | None:
    if not path.exists():
        return None
    return CollectorState.from_json(path.read_text())


def save_state(path: Path, state: CollectorState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(state.to_json())


def current_period_end(now: datetime, anchor: date, period_days: int = 30) -> datetime:
    """Rolls `anchor` forward by `period_days` until the result is after `now`.

    Correctness here only affects pacing smoothness, not budget safety —
    `remaining_credits` always comes from the live response header, so an
    anchor that's off by a few days just makes the spread-evenly math
    slightly uneven, never lets us overspend.
    """
    anchor_dt = datetime(anchor.year, anchor.month, anchor.day, tzinfo=UTC)
    period = timedelta(days=period_days)
    end = anchor_dt + period
    while end <= now:
        end += period
    return end


@dataclass(frozen=True)
class PollDecision:
    should_poll: bool
    reason: str  # "ok" | "too_soon" | "budget_exhausted"
    regions: str
    markets: str
    effective_interval_minutes: float


def _nearest_upcoming_hours(now: datetime, upcoming_kickoffs: Sequence[datetime]) -> float | None:
    future = [k for k in upcoming_kickoffs if k >= now]
    if not future:
        return None
    return (min(future) - now).total_seconds() / 3600.0


def _game_interval_minutes(
    now: datetime,
    upcoming_kickoffs: Sequence[datetime],
    dense_window_hours: float,
    dense_interval_minutes: float,
    sparse_interval_minutes: float,
) -> float:
    hours_to_nearest = _nearest_upcoming_hours(now, upcoming_kickoffs)
    if hours_to_nearest is not None and hours_to_nearest <= dense_window_hours:
        return dense_interval_minutes
    return sparse_interval_minutes


def _minutes_since(now: datetime, last_poll_time: datetime | None) -> float:
    if last_poll_time is None:
        return float("inf")
    return (now - last_poll_time).total_seconds() / 60.0


def decide_poll(
    now: datetime,
    upcoming_kickoffs: Sequence[datetime],
    remaining_credits: int | None,
    period_end: datetime,
    *,
    last_poll_time: datetime | None,
    full_regions: str,
    full_markets: str,
    reduced_markets: str,
    full_cost: int,
    reduced_cost: int,
    dense_window_hours: float,
    dense_interval_minutes: float,
    sparse_interval_minutes: float,
    min_interval_minutes: float,
    safety_reserve_credits: int,
) -> PollDecision:
    game_interval = _game_interval_minutes(
        now, upcoming_kickoffs, dense_window_hours, dense_interval_minutes, sparse_interval_minutes
    )
    minutes_since_last = _minutes_since(now, last_poll_time)

    if remaining_credits is None:
        # Never polled yet this process: bootstrap. We need one real response
        # to learn quota at all, and the cost is small relative to the
        # monthly ceiling, so allow it (subject only to the floor interval).
        effective_interval = max(game_interval, min_interval_minutes)
        should_poll = minutes_since_last >= effective_interval
        return PollDecision(should_poll, "ok" if should_poll else "too_soon", full_regions, full_markets, effective_interval)

    period_minutes_left = max((period_end - now).total_seconds() / 60.0, 1.0)

    for markets, cost in ((full_markets, full_cost), (reduced_markets, reduced_cost)):
        affordable_polls = max(0, remaining_credits - safety_reserve_credits) // cost
        if affordable_polls <= 0:
            continue
        budget_interval = period_minutes_left / affordable_polls
        effective_interval = max(game_interval, budget_interval, min_interval_minutes)
        should_poll = minutes_since_last >= effective_interval
        return PollDecision(should_poll, "ok" if should_poll else "too_soon", full_regions, markets, effective_interval)

    return PollDecision(False, "budget_exhausted", full_regions, reduced_markets, float("inf"))
