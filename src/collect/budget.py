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

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, replace
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


def key_fingerprint(api_key: str) -> str:
    """Short, non-reversible tag identifying WHICH key a cached credit balance
    belongs to. Never the key itself -- this is persisted to a plaintext state
    file next to the snapshots.
    """
    return hashlib.sha256(api_key.encode()).hexdigest()[:12]


@dataclass(frozen=True)
class CollectorState:
    """Persisted to disk between process restarts (default: data/collect_state.json)."""

    last_poll_time: datetime | None
    remaining_credits: int | None
    period_anchor: date
    consecutive_failures: int = 0
    # Which API key `remaining_credits` was observed on. A balance cached from
    # one key is meaningless on another: switching the mainline collector from
    # the free key to the paid one (2026-09-08) left a stale `206` on disk,
    # which the pacer would have read as near-exhaustion and used to stall the
    # first poll by ~15 hours -- with Week 1 kickoff 34 hours out. Since the
    # only way to LEARN the real balance is to poll, that is self-sustaining:
    # it never polls, so it never corrects itself. See `state_for_key`.
    api_key_fingerprint: str | None = None

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
            api_key_fingerprint=d.get("api_key_fingerprint"),
        )


def state_for_key(state: CollectorState, api_key: str) -> CollectorState:
    """`state` with its cached credit balance dropped if it was observed on a
    different key. Dropping it to `None` routes `decide_poll` down its bootstrap
    branch, which polls once to relearn the real quota from the response header.

    A state file written before fingerprints existed carries `None`, which is
    treated as "belongs to whatever key is configured now" -- the balance in
    that case was almost certainly the free key's, but assuming a mismatch on
    every legacy file would burn one needless bootstrap poll on every upgrade.
    """
    fingerprint = key_fingerprint(api_key)
    if state.api_key_fingerprint is None:
        return replace(state, api_key_fingerprint=fingerprint)
    if state.api_key_fingerprint == fingerprint:
        return state
    return replace(state, remaining_credits=None, api_key_fingerprint=fingerprint)


def load_state(path: Path) -> CollectorState | None:
    if not path.exists():
        return None
    return CollectorState.from_json(path.read_text())


def save_state(path: Path, state: CollectorState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(state.to_json())


def current_period_end(
    now: datetime, anchor: date, period_days: int = 30, mode: str = "rolling"
) -> datetime:
    """When the current credit quota refills.

    Two modes, because this project's two keys bill differently:

    - `"rolling"`: roll `anchor` forward by `period_days` until it is after
      `now`. The free key's original assumption.
    - `"calendar_month"`: 00:00 UTC on the first of next month. The PAID key
      refills on the calendar month boundary -- confirmed empirically from
      `logs/props.err.log`, where the balance jumped 3,675 -> 99,990 between
      the 2026-08-30 and 2026-08-31 20:40 EDT polls (= 2026-09-01 00:40 UTC).
      This corrected a standing project assumption that the 100K grant was a
      one-time allocation; it is recurring monthly.

    Correctness here only affects pacing smoothness, not budget safety —
    `remaining_credits` always comes from the live response header, so a
    period boundary that's off by a few days just makes the allocation math
    slightly uneven, never lets us overspend.
    """
    if mode == "calendar_month":
        year, month = (now.year + 1, 1) if now.month == 12 else (now.year, now.month + 1)
        return datetime(year, month, 1, tzinfo=UTC)

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


def _dense_minutes_remaining(
    now: datetime,
    period_end: datetime,
    upcoming_kickoffs: Sequence[datetime],
    dense_window_hours: float,
) -> float:
    """Minutes between `now` and `period_end` that sit inside the dense
    window of at least one upcoming kickoff.

    Windows are UNIONED, not summed: an NFL week kicks off Thu/Sun/Mon, so
    48-hour windows overlap heavily and naive summing would claim more dense
    time than the period actually contains, inflating the credit demand
    estimate and throttling the collector for no reason.
    """
    if period_end <= now:
        return 0.0

    window = timedelta(hours=dense_window_hours)
    spans: list[tuple[datetime, datetime]] = []
    for kickoff in upcoming_kickoffs:
        lo = max(kickoff - window, now)
        hi = min(kickoff, period_end)
        if hi > lo:
            spans.append((lo, hi))
    if not spans:
        return 0.0

    spans.sort()
    total = timedelta()
    cur_lo, cur_hi = spans[0]
    for lo, hi in spans[1:]:
        if lo <= cur_hi:
            cur_hi = max(cur_hi, hi)
        else:
            total += cur_hi - cur_lo
            cur_lo, cur_hi = lo, hi
    total += cur_hi - cur_lo
    return total.total_seconds() / 60.0


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

    # Credit demand for the IDEAL cadence over the rest of the period: dense
    # minutes polled at the dense rate, everything else at the sparse rate.
    dense_minutes = _dense_minutes_remaining(now, period_end, upcoming_kickoffs, dense_window_hours)
    sparse_minutes = max(period_minutes_left - dense_minutes, 0.0)
    desired_polls = max(
        dense_minutes / dense_interval_minutes + sparse_minutes / sparse_interval_minutes, 1e-9
    )

    for markets, cost in ((full_markets, full_cost), (reduced_markets, reduced_cost)):
        affordable_polls = max(0, remaining_credits - safety_reserve_credits) // cost
        if affordable_polls <= 0:
            continue
        # Scarcity STRETCHES the whole cadence proportionally rather than
        # flattening it to one uniform interval (fixed 2026-09-08). The old
        # `max(game_interval, period_minutes_left / affordable_polls, ...)`
        # spread credits evenly across wall-clock time, but a snapshot's value
        # is not uniform in time -- it is concentrated in the hours before
        # kickoff. On the free key that uniform term ALWAYS dominated (500
        # credits / 6 per poll over 30 days = one poll per 8.7h, vs. a 30-min
        # dense target), so `dense_interval_minutes` was dead code and the
        # collector sat at a 3.4h cadence 34 hours before Week 1 -- far too
        # coarse for the 1-hour window `src/backtest/steam.py` needs, which is
        # why the live steam scan had never once fired on a 2026 game.
        # Scaling keeps dense polling dense RELATIVE to sparse when tight, and
        # collapses to the true dense cadence the moment we can afford it.
        scale = max(desired_polls / affordable_polls, 1.0)
        effective_interval = max(game_interval * scale, min_interval_minutes)
        should_poll = minutes_since_last >= effective_interval
        return PollDecision(should_poll, "ok" if should_poll else "too_soon", full_regions, markets, effective_interval)

    return PollDecision(False, "budget_exhausted", full_regions, reduced_markets, float("inf"))
