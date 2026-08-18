"""Budget-aware polling cadence for player props -- a different scheduling
problem than the mainline collector's `budget.py`.

The mainline collector polls the *whole slate* on a shared cadence (one
bulk call covers every game). Props can't work that way: they're fetched
per-event (`OddsApiClient.get_event_odds`, real credits per call), and
each game's props post independently -- typically Tue-Thu of that game's
own week, not on a fixed calendar schedule. So this module decides, per
event, whether to poll it *right now*: has it entered the posting window,
has it already gotten its scheduled polls, and is there budget for it.

**Two real polls per event, not one -- a genuine improvement over the
historical pull.** The historical props backfill (`props_historical.py`)
was forced to a single near-kickoff snapshot per game because the
historical endpoint costs 10x per call. Live polling doesn't have that
multiplier, so this schedules an "entry" poll (as soon as the event enters
the posting window) and a "close" poll (near kickoff) -- a real CLV pair
for props, not just a closing-line snapshot, for the first time.

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
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

POSTING_WINDOW_DAYS = 5.0  # start attempting once a game is this close -- props rarely post earlier (confirmed live-checked multiple times this project, e.g. player_props_infra memory)
CLOSING_WINDOW_HOURS = 6.0  # take the second ("close") poll once inside this window before kickoff
POLLS_PER_EVENT = 2  # "entry" + "close" -- see module docstring
DEFAULT_COST_PER_POLL = 14  # regions=us,eu x 7 markets, theoretical max (real blended cost runs lower -- see props_ev_backtest memory, ~101/10=~10/event on the historical endpoint's 10x rate)
DEFAULT_SAFETY_RESERVE_CREDITS = 500  # large relative to a single poll's cost -- props credits are meant to leave headroom for a possible future historical batch 2, not be spent to the floor


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
    posting_window_days: float = POSTING_WINDOW_DAYS,
    closing_window_hours: float = CLOSING_WINDOW_HOURS,
    polls_per_event: int = POLLS_PER_EVENT,
    cost_per_poll: int = DEFAULT_COST_PER_POLL,
    safety_reserve_credits: int = DEFAULT_SAFETY_RESERVE_CREDITS,
) -> PropsPollDecision:
    """Should this specific event be polled right now?

    Entry poll: fires once the event is within `posting_window_days` of
    kickoff and hasn't been polled yet. Close poll: fires once inside
    `closing_window_hours` of kickoff, if the entry poll already happened
    (or, if the entry window was somehow missed entirely -- e.g. the
    service was down -- this still takes a first poll here rather than
    getting nothing at all).
    """
    if event_state.poll_count >= polls_per_event:
        return PropsPollDecision(False, "already_fully_polled")

    if now >= kickoff:
        return PropsPollDecision(False, "event_started")

    if remaining_credits is not None and remaining_credits - safety_reserve_credits < cost_per_poll:
        return PropsPollDecision(False, "budget_exhausted")

    hours_to_kickoff = (kickoff - now).total_seconds() / 3600.0
    days_to_kickoff = hours_to_kickoff / 24.0

    if event_state.poll_count == 0:
        if days_to_kickoff <= posting_window_days:
            return PropsPollDecision(True, "ok")
        return PropsPollDecision(False, "not_yet_in_window")

    # poll_count == 1: waiting for the closing window
    if hours_to_kickoff <= closing_window_hours:
        return PropsPollDecision(True, "ok")
    return PropsPollDecision(False, "not_yet_in_window")
