"""Budget-aware polling cadence for player props -- a different scheduling
problem than the mainline collector's `budget.py`.

The mainline collector polls the *whole slate* on a shared cadence (one
bulk call covers every game). Props can't work that way: they're fetched
per-event (`OddsApiClient.get_event_odds`, real credits per call), and
each game's props post independently -- typically Tue-Thu of that game's
own week, not on a fixed calendar schedule. So this module decides, per
event, whether to poll it *right now*: has it entered the posting window,
has it already gotten its scheduled polls, and is there budget for it.

**A two-tier schedule -- sparse "basic" polls, then dense rolling CLV
polls -- not just an entry/close pair. A genuine improvement over the
historical pull.** The historical props backfill (`props_historical.py`)
was forced to a single near-kickoff snapshot per game because the
historical endpoint costs 10x per call. Live polling doesn't have that
multiplier, so this schedules two tiers: a **sparse** tier covering the
period from when an event enters the `POSTING_WINDOW_DAYS` window down to
`DENSE_WINDOW_HOURS` before kickoff (a "basic" poll every
`SPARSE_POLL_INTERVAL_HOURS`, catching early posting and slow drift), then
a **dense** tier for the final `DENSE_WINDOW_HOURS` before kickoff (every
`DENSE_POLL_INTERVAL_HOURS`) -- real rolling CLV movement through the
window that actually matters most, not just two point-in-time snapshots.
Mirrors the mainline collector's own dense-window-near-kickoff philosophy
(`src/collect/budget.py`'s `dense_window_hours`) rather than inventing a
new schedule shape.

**2026-08-22 correction: credits were never the real constraint on this --
the schedule shape was.** At `DEFAULT_COST_PER_POLL` (14 credits, live
per-event rate, no 10x historical multiplier), even this two-tier default
costs well under the paid plan's monthly headroom for a full 285-game
season -- see `props_polling_density` in project memory. The old 2-poll
(entry+close) design undersampled movement not because credits ran out,
but because nothing asked for more.

**Uses the paid key, not the free one -- a deliberate resource-contention
call.** The mainline collector's dense pre-kickoff polling (the actual
CLV thesis) runs on the free tier's 500 credits/month. Props polling at
~10-14 credits/event, twice per event, across ~16 games/week would burn
through that same free-tier budget in days and starve the mainline
collector right when it matters most (game week). The paid key
(`ODDS_API_KEY_PAID`, ~20K credits/month) has the headroom this needs
without touching the free tier at all -- see `src/collect/props_run.py`.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

POSTING_WINDOW_DAYS = 5.0  # start attempting once a game is this close -- props rarely post earlier (confirmed live-checked multiple times this project, e.g. player_props_infra memory)
DENSE_WINDOW_HOURS = 48.0  # the most critical window: dense rolling-CLV polling covers this many hours before kickoff -- matches the mainline collector's own "48h pre-slate" dense window
DENSE_POLL_INTERVAL_HOURS = 3.0  # spacing between dense polls -- tune this (not POLLS_PER_EVENT directly) to go denser/sparser
SPARSE_POLL_INTERVAL_HOURS = 12.0  # spacing for "basic" polls covering the period BEFORE the dense window kicks in (POSTING_WINDOW_DAYS out down to DENSE_WINDOW_HOURS)
# 2026-08-22: trimmed from 2h/8h (33 polls/event, ~94K blended season cost) to 3h/12h
# (22 polls/event, ~62.7K blended) after confirming the paid plan is a ONE-TIME ~100K
# grant (resets 9/1, no rollover, user isn't renewing past that) rather than recurring
# monthly -- the tighter schedule left ~6K margin for a whole season, this leaves ~37K.
# Costs almost nothing methodologically: the core CLV metric only needs an entry price
# and a closing price (2 points), not dense intermediate sampling -- see
# props_polling_density memory. Trimming only reduces live props arb/middling catch
# rate, an already-secondary strategy, not any validated finding.
DEFAULT_COST_PER_POLL = 14  # regions=us,eu x 7 markets, theoretical max (real blended cost runs lower -- see props_ev_backtest memory, ~101/10=~10/event on the historical endpoint's 10x rate)
DEFAULT_SAFETY_RESERVE_CREDITS = 500  # large relative to a single poll's cost -- props credits are meant to leave headroom for a possible future historical batch 2, not be spent to the floor


def dense_poll_targets_hours(dense_window_hours: float = DENSE_WINDOW_HOURS, dense_poll_interval_hours: float = DENSE_POLL_INTERVAL_HOURS) -> list[float]:
    """Descending list of hours-before-kickoff targets for the dense
    ("most critical") polling tier, from `dense_window_hours` out down to
    one interval before kickoff -- default 48/2 = 24 targets.
    """
    n = max(1, round(dense_window_hours / dense_poll_interval_hours))
    return [dense_window_hours - i * dense_poll_interval_hours for i in range(n)]


def sparse_poll_targets_hours(
    posting_window_days: float = POSTING_WINDOW_DAYS,
    dense_window_hours: float = DENSE_WINDOW_HOURS,
    sparse_poll_interval_hours: float = SPARSE_POLL_INTERVAL_HOURS,
) -> list[float]:
    """Descending list of hours-before-kickoff targets for the sparse
    ("basic") polling tier -- covers the gap between an event entering the
    `posting_window_days` window and the dense tier taking over at
    `dense_window_hours`. The first target lands exactly at
    `posting_window_days*24` hours before kickoff, so this tier's first
    poll fires as soon as the event enters the window (same "catch it
    early" behavior the old single entry poll had) -- default 8h spacing
    across the 120h-to-48h gap = 9 targets.
    """
    span_hours = posting_window_days * 24.0 - dense_window_hours
    n = max(1, round(span_hours / sparse_poll_interval_hours))
    return [dense_window_hours + span_hours - i * sparse_poll_interval_hours for i in range(n)]


SPARSE_POLL_TARGETS_HOURS = sparse_poll_targets_hours()
DENSE_POLL_TARGETS_HOURS = dense_poll_targets_hours()
POLL_TARGETS_HOURS = SPARSE_POLL_TARGETS_HOURS + DENSE_POLL_TARGETS_HOURS  # combined, descending -- what decide_props_poll actually walks
POLLS_PER_EVENT = len(POLL_TARGETS_HOURS)  # derived, don't hardcode this elsewhere


@dataclass(frozen=True)
class EventPollState:
    poll_count: int = 0
    last_polled_at: datetime | None = None

    def to_json(self) -> dict:
        return {"poll_count": self.poll_count, "last_polled_at": self.last_polled_at.isoformat() if self.last_polled_at else None}

    @classmethod
    def from_json(cls, d: dict) -> EventPollState:
        return cls(
            poll_count=d["poll_count"],
            last_polled_at=datetime.fromisoformat(d["last_polled_at"]) if d["last_polled_at"] else None,
        )


@dataclass(frozen=True)
class PropsCollectorState:
    """Persisted to disk between process restarts (default: data/props_collect_state.json).

    Keyed per-event (unlike the mainline collector's single `last_poll_time`)
    since each game is scheduled independently.
    """

    events: dict[str, EventPollState] = field(default_factory=dict)
    remaining_credits: int | None = None

    def to_json(self) -> str:
        return json.dumps(
            {
                "events": {event_id: s.to_json() for event_id, s in self.events.items()},
                "remaining_credits": self.remaining_credits,
            }
        )

    @classmethod
    def from_json(cls, raw: str) -> PropsCollectorState:
        d = json.loads(raw)
        return cls(
            events={event_id: EventPollState.from_json(s) for event_id, s in d["events"].items()},
            remaining_credits=d["remaining_credits"],
        )


def load_state(path: Path) -> PropsCollectorState:
    if not path.exists():
        return PropsCollectorState()
    return PropsCollectorState.from_json(path.read_text())


def save_state(path: Path, state: PropsCollectorState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(state.to_json())


@dataclass(frozen=True)
class PropsPollDecision:
    should_poll: bool
    reason: str  # "ok" | "not_yet_in_window" | "already_fully_polled" | "budget_exhausted" | "event_started"


def decide_props_poll(
    now: datetime,
    kickoff: datetime,
    event_state: EventPollState,
    remaining_credits: int | None,
    *,
    poll_targets_hours: Sequence[float] = POLL_TARGETS_HOURS,
    cost_per_poll: int = DEFAULT_COST_PER_POLL,
    safety_reserve_credits: int = DEFAULT_SAFETY_RESERVE_CREDITS,
) -> PropsPollDecision:
    """Should this specific event be polled right now?

    `poll_targets_hours` is a single descending list of hours-before-kickoff
    targets -- the sparse ("basic") tier concatenated with the dense
    ("most critical," 48h pre-kickoff) tier, see `sparse_poll_targets_hours()`
    / `dense_poll_targets_hours()`. Poll N (`event_state.poll_count == N`)
    fires once `now` has crossed `poll_targets_hours[N]`. The first target
    sits at exactly `POSTING_WINDOW_DAYS*24` hours before kickoff, so poll 0
    fires as soon as the event enters the posting window -- if that window
    was somehow missed entirely (e.g. the service was down), this still
    fires on whatever the next un-taken target is, rather than waiting for
    every earlier target to "catch up" -- better a late poll than none.
    """
    if event_state.poll_count >= len(poll_targets_hours):
        return PropsPollDecision(False, "already_fully_polled")

    if now >= kickoff:
        return PropsPollDecision(False, "event_started")

    if remaining_credits is not None and remaining_credits - safety_reserve_credits < cost_per_poll:
        return PropsPollDecision(False, "budget_exhausted")

    hours_to_kickoff = (kickoff - now).total_seconds() / 3600.0
    next_target = poll_targets_hours[event_state.poll_count]
    if hours_to_kickoff <= next_target:
        return PropsPollDecision(True, "ok")
    return PropsPollDecision(False, "not_yet_in_window")
