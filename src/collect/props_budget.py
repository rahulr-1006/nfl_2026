"""Budget-aware polling cadence for player props -- a different scheduling
problem than the mainline collector's `budget.py`.

The mainline collector polls the *whole slate* on a shared cadence (one
bulk call covers every game). Props can't work that way: they're fetched
per-event (`OddsApiClient.get_event_odds`, real credits per call), and
each game's props post independently -- typically Tue-Thu of that game's
own week, not on a fixed calendar schedule. So this module decides, per
event, whether to poll it *right now*: has it entered the posting window,
has it already gotten its scheduled polls, and is there budget for it.

**A three-tier schedule, each tier buying a different thing.** The
historical props backfill (`props_historical.py`) was forced to a single
near-kickoff snapshot per game because the historical endpoint costs 10x
per call. Live polling doesn't have that multiplier, so:
  - **sparse** (`POSTING_WINDOW_DAYS` -> `DENSE_WINDOW_HOURS`, every
    `SPARSE_POLL_INTERVAL_HOURS`, all 7 markets): catches early posting and
    slow drift.
  - **dense** (final `DENSE_WINDOW_HOURS`, every `DENSE_POLL_INTERVAL_HOURS`,
    all 7 markets): real rolling CLV movement through the window that
    matters most. Mirrors the mainline collector's own
    dense-window-near-kickoff philosophy (`src/collect/budget.py`).
  - **arb** (final `ARB_WINDOW_HOURS`, every `ARB_POLL_INTERVAL_HOURS`,
    `ARB_MARKETS` only): cheap high-frequency coverage for the one signal
    that genuinely needs density -- see the `ARB_MARKETS` block below.

`build_poll_targets` merges all three into one time-ordered schedule and
deduplicates colliding hours **keeping the full-market poll**, so a cheap
2-market arb poll never shadows a 7-market one and silently drops CLV
coverage on five markets.

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

from src.collect.props import (
    DEFAULT_MARKETS as _ALL_PROP_MARKETS,  # single source of truth for the 7 O/U prop markets
)

POSTING_WINDOW_DAYS = 5.0  # start attempting once a game is this close -- props rarely post earlier (confirmed live-checked multiple times this project, e.g. player_props_infra memory)
DENSE_WINDOW_HOURS = 48.0  # the most critical window: dense rolling-CLV polling covers this many hours before kickoff -- matches the mainline collector's own "48h pre-slate" dense window
DENSE_POLL_INTERVAL_HOURS = 4.0  # spacing between dense polls -- tune this (not POLLS_PER_EVENT directly) to go denser/sparser
SPARSE_POLL_INTERVAL_HOURS = 12.0  # spacing for "basic" polls covering the period BEFORE the dense window kicks in (POSTING_WINDOW_DAYS out down to DENSE_WINDOW_HOURS)
# 2026-08-22: trimmed from 2h/8h (33 polls/event, ~94K blended season cost) to 3h/12h
# after confirming the paid plan is a ONE-TIME ~100K grant (resets 9/1, no rollover,
# user isn't renewing past that) rather than recurring monthly.
#
# 2026-08-23: dense interval trimmed again, 3h -> 4h. Adding the arb tier below had
# pushed the schedule to 99,180 credits -- **99.2% of the entire grant**, which is not
# a margin, it's a rounding error away from props collection silently stopping in
# January when the safety reserve starts blocking polls. Trimming the DENSE tier
# (rather than the arb tier) is the principled cut: CLV needs only an entry price and
# a close, so intermediate sampling density costs almost nothing methodologically,
# whereas 30-minute arb density is exactly what the one validated live edge depends
# on. Result: 29 polls/event, 84,360 theoretical (~84% of grant, ~15.6K margin).
DEFAULT_COST_PER_POLL = 14  # regions=us,eu x 7 markets, theoretical max (real blended cost runs lower -- see props_ev_backtest memory, ~101/10=~10/event on the historical endpoint's 10x rate)
DEFAULT_SAFETY_RESERVE_CREDITS = 500  # large relative to a single poll's cost -- props credits are meant to leave headroom for a possible future historical batch 2, not be spent to the floor

# --- arb tier (2026-08-23) ---------------------------------------------------
# The 3h dense interval above was chosen for CLV, which only needs an entry price
# and a close. **Arbitrage is the one signal that genuinely needs density** --
# cross-book arb windows are fleeting, and this project's own props-arb work flags
# that sub-2% margins get eaten by execution latency. Polling ALL markets densely
# doesn't fit the budget (1h interval across 7 markets = ~153,900 blended for a
# season, against a one-time ~100K grant).
#
# The lever: credits bill per (market x region), and `markets` is a per-call
# parameter. The measured arb finding is highly concentrated -- **57 of 65 real
# spots were receptions + passing TDs** (see props_arbitrage memory: 29/31 of the
# original narrower run were a single FanDuel/BetMGM book pair on exactly these
# two market types, traced to a systematic vig-skew, not scattered noise). So
# these two markets alone can be polled densely for ~4 credits instead of 14.
#
# This is a MEASURED subset, not a guess. If a future session widens it, re-derive
# it from a fresh arb concentration check rather than adding markets by intuition.
ARB_MARKETS = "player_receptions,player_pass_tds"
ARB_WINDOW_HOURS = 6.0  # final hours before kickoff, where prices move most and arb windows actually open
ARB_POLL_INTERVAL_HOURS = 0.5
ARB_COST_PER_POLL = 4  # regions=us,eu x 2 markets


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


def arb_poll_targets_hours(
    arb_window_hours: float = ARB_WINDOW_HOURS,
    arb_poll_interval_hours: float = ARB_POLL_INTERVAL_HOURS,
) -> list[float]:
    """Descending hours-before-kickoff targets for the cheap, dense ARB tier
    -- see `ARB_MARKETS` for why this tier exists and why it's a narrow
    market subset rather than more full-price polls.
    """
    n = max(1, round(arb_window_hours / arb_poll_interval_hours))
    return [arb_window_hours - i * arb_poll_interval_hours for i in range(n)]


@dataclass(frozen=True)
class PollTarget:
    """One scheduled poll: when to fire it, which markets to request, and
    what that costs.

    **Markets and cost travel WITH the target, not as global constants**,
    because the tiers deliberately request different market subsets at
    different prices (see `ARB_MARKETS`). A single global
    `DEFAULT_COST_PER_POLL` can't express "this poll costs 4, that one
    costs 14," and getting that wrong would make the budget guard
    systematically wrong in the direction of overspending.
    """

    hours_before_kickoff: float
    markets: str
    cost: int
    tier: str


def build_poll_targets(
    full_markets: str = _ALL_PROP_MARKETS,
    arb_markets: str = ARB_MARKETS,
) -> list[PollTarget]:
    """The full per-event schedule, descending by hours-before-kickoff:
    sparse (all markets) -> dense (all markets) -> arb (narrow subset,
    cheap, high frequency). Deduplicated on `hours_before_kickoff` keeping
    the FIRST (more comprehensive) tier, so the arb tier's final-hours
    targets never shadow a full-market dense poll scheduled at the same
    hour -- losing a 7-market poll to a 2-market one would silently drop
    CLV coverage on five markets.
    """
    targets = (
        [PollTarget(h, full_markets, DEFAULT_COST_PER_POLL, "sparse") for h in sparse_poll_targets_hours()]
        + [PollTarget(h, full_markets, DEFAULT_COST_PER_POLL, "dense") for h in dense_poll_targets_hours()]
        + [PollTarget(h, arb_markets, ARB_COST_PER_POLL, "arb") for h in arb_poll_targets_hours()]
    )
    targets.sort(key=lambda t: -t.hours_before_kickoff)

    seen: set[float] = set()
    deduped = []
    for t in targets:
        if t.hours_before_kickoff in seen:
            continue
        seen.add(t.hours_before_kickoff)
        deduped.append(t)
    return deduped


SPARSE_POLL_TARGETS_HOURS = sparse_poll_targets_hours()
DENSE_POLL_TARGETS_HOURS = dense_poll_targets_hours()
ARB_POLL_TARGETS_HOURS = arb_poll_targets_hours()
POLL_TARGETS = build_poll_targets()
POLL_TARGETS_HOURS = [t.hours_before_kickoff for t in POLL_TARGETS]  # kept for callers that only need the schedule shape
POLLS_PER_EVENT = len(POLL_TARGETS)  # derived, don't hardcode this elsewhere


def season_credit_cost(n_games: int, targets: list[PollTarget] | None = None) -> int:
    """Total credits to poll `n_games` at this schedule -- the real
    projection, summed from the actual tier definitions rather than
    multiplying an average. Use this to check a schedule change against the
    budget instead of recomputing arithmetic by hand.
    """
    targets = targets if targets is not None else POLL_TARGETS
    return n_games * sum(t.cost for t in targets)


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
    markets: str | None = None  # which markets THIS poll should request -- varies by tier, see PollTarget
    cost: int | None = None
    tier: str | None = None


def decide_props_poll(
    now: datetime,
    kickoff: datetime,
    event_state: EventPollState,
    remaining_credits: int | None,
    *,
    poll_targets: Sequence[PollTarget] = tuple(POLL_TARGETS),
    safety_reserve_credits: int = DEFAULT_SAFETY_RESERVE_CREDITS,
) -> PropsPollDecision:
    """Should this specific event be polled right now, and if so, for which
    markets?

    `poll_targets` is a single descending schedule across all three tiers
    (sparse -> dense -> arb, see `build_poll_targets`). Poll N
    (`event_state.poll_count == N`) fires once `now` has crossed
    `poll_targets[N].hours_before_kickoff`. The first target sits at exactly
    `POSTING_WINDOW_DAYS*24` hours before kickoff, so poll 0 fires as soon as
    the event enters the posting window -- if that window was somehow missed
    entirely (e.g. the service was down), this still fires on whatever the
    next un-taken target is, rather than waiting for every earlier target to
    "catch up" -- better a late poll than none.

    **The budget check uses THIS target's own cost**, not a global constant:
    the arb tier requests a narrow market subset at ~4 credits while the
    other tiers request all 7 at ~14, so a single global cost would reject
    affordable arb polls and accept unaffordable full ones.
    """
    if event_state.poll_count >= len(poll_targets):
        return PropsPollDecision(False, "already_fully_polled")

    if now >= kickoff:
        return PropsPollDecision(False, "event_started")

    target = poll_targets[event_state.poll_count]

    if remaining_credits is not None and remaining_credits - safety_reserve_credits < target.cost:
        return PropsPollDecision(False, "budget_exhausted")

    hours_to_kickoff = (kickoff - now).total_seconds() / 3600.0
    if hours_to_kickoff <= target.hours_before_kickoff:
        return PropsPollDecision(True, "ok", markets=target.markets, cost=target.cost, tier=target.tier)
    return PropsPollDecision(False, "not_yet_in_window")
