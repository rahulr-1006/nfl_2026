"""Budget-aware polling schedule for player props.

Unlike the mainline collector, which polls the whole slate in one bulk call,
props are fetched per event and each game's props post on their own timeline.
This module decides, per event, whether to poll it now.

The schedule has four tiers, each buying something different:
  - early: daily probes from `POSTING_WINDOW_DAYS` out, to catch the moment
    props first appear. Probes on a game with no props cost 0 credits.
  - sparse: all markets every `SPARSE_POLL_INTERVAL_HOURS`, for slow drift.
  - dense: all markets every `DENSE_POLL_INTERVAL_HOURS` in the final
    `DENSE_WINDOW_HOURS`, for rolling CLV.
  - arb: a cheap market subset every `ARB_POLL_INTERVAL_HOURS` in the final
    `ARB_WINDOW_HOURS`, because cross-book arb windows are short-lived.

Props polling uses the paid key so it can never starve the mainline
collector's pre-kickoff polling.
"""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from src.collect.props import (
    DEFAULT_MARKETS as _ALL_PROP_MARKETS,
)

# Props have posted as early as 17 days before kickoff. A wide window is safe
# only because empty polls bill 0 credits and `props_scheduler` doesn't advance
# `poll_count` on an empty poll, so probes can't use up the schedule early.
POSTING_WINDOW_DAYS = 21.0
DENSE_WINDOW_HOURS = 48.0
DENSE_POLL_INTERVAL_HOURS = 4.0
SPARSE_POLL_INTERVAL_HOURS = 12.0
# The sparse tier starts here rather than at the posting window: 21 days of
# 12-hourly polling would cost far more than it's worth.
SPARSE_WINDOW_HOURS = 120.0
EARLY_POLL_INTERVAL_HOURS = 24.0
# CLV needs only an entry price and a close, so the dense tier is deliberately
# not denser than 4h; spare budget goes to the arb tier instead.
DEFAULT_COST_PER_POLL = 14  # regions=us,eu x 7 markets, worst case
DEFAULT_SAFETY_RESERVE_CREDITS = 500

# Credits bill per (market x region), so the arb tier asks only for the markets
# where cross-book arbs actually showed up: 57 of 65 historical spots were
# receptions or passing TDs. Re-measure before adding markets.
ARB_MARKETS = "player_receptions,player_pass_tds"
# Worst-case detection latency is this spacing plus the monitor's 5-minute
# cadence. It must stay >= props_scheduler.DEFAULT_TICK_MINUTES, which is a
# hard floor on how often any target can fire.
ARB_WINDOW_HOURS = 12.0
ARB_POLL_INTERVAL_HOURS = 0.25

# The yardage markets ride along on arb-tier calls for line-movement data, not
# arbs. Pre-kickoff movement can't be bought back later: historical props are
# a single near-kickoff snapshot.
MOVEMENT_MARKETS = "player_pass_yds,player_rush_yds,player_reception_yds"
ARB_TIER_MARKETS = f"{ARB_MARKETS},{MOVEMENT_MARKETS}"
ARB_COST_PER_POLL = 10  # regions=us,eu x 5 markets (2 arb + 3 movement)

# One full-market capture near kickoff, so every market has a closing price for
# CLV. Without it the arb tier's narrow subset would leave most markets with no
# close at all. 1.5h sits inside rolling_clv_2024.CLOSE_MAX (2.0h) and replaces
# the arb target at the same offset rather than adding a poll.
CLOSE_CAPTURE_HOURS = 1.5


def dense_poll_targets_hours(dense_window_hours: float = DENSE_WINDOW_HOURS, dense_poll_interval_hours: float = DENSE_POLL_INTERVAL_HOURS) -> list[float]:
    """Descending hours-before-kickoff targets for the dense tier."""
    n = max(1, round(dense_window_hours / dense_poll_interval_hours))
    return [dense_window_hours - i * dense_poll_interval_hours for i in range(n)]


def early_poll_targets_hours(
    posting_window_days: float = POSTING_WINDOW_DAYS,
    sparse_window_hours: float = SPARSE_WINDOW_HOURS,
    early_poll_interval_hours: float = EARLY_POLL_INTERVAL_HOURS,
) -> list[float]:
    """Coarse probes from the posting window down to the sparse tier.

    These exist to catch the moment props appear, not to sample movement.
    """
    span = posting_window_days * 24.0 - sparse_window_hours
    if span <= 0:
        return []
    # ceil, not round: round() can drop the last target and leave a gap before
    # the sparse tier starts. The last target is always above
    # sparse_window_hours, so it can't collide with the sparse tier.
    n = max(1, math.ceil(span / early_poll_interval_hours))
    return [posting_window_days * 24.0 - i * early_poll_interval_hours for i in range(n)]


def sparse_poll_targets_hours(
    posting_window_days: float = POSTING_WINDOW_DAYS,
    dense_window_hours: float = DENSE_WINDOW_HOURS,
    sparse_poll_interval_hours: float = SPARSE_POLL_INTERVAL_HOURS,
    sparse_window_hours: float = SPARSE_WINDOW_HOURS,
) -> list[float]:
    """Descending targets covering the gap between the early and dense tiers."""
    span_hours = sparse_window_hours - dense_window_hours
    n = max(1, round(span_hours / sparse_poll_interval_hours))
    return [sparse_window_hours - i * sparse_poll_interval_hours for i in range(n)]


def arb_poll_targets_hours(
    arb_window_hours: float = ARB_WINDOW_HOURS,
    arb_poll_interval_hours: float = ARB_POLL_INTERVAL_HOURS,
) -> list[float]:
    """Descending targets for the cheap, high-frequency arb tier."""
    n = max(1, round(arb_window_hours / arb_poll_interval_hours))
    return [arb_window_hours - i * arb_poll_interval_hours for i in range(n)]


@dataclass(frozen=True)
class PollTarget:
    """One scheduled poll: when it fires, which markets it requests, what it costs.

    Markets and cost live on the target, not in globals, because tiers request
    different market subsets at different prices. A single global cost would
    make the budget guard wrong.
    """

    hours_before_kickoff: float
    markets: str
    cost: int
    tier: str


def build_poll_targets(
    full_markets: str = _ALL_PROP_MARKETS,
    arb_markets: str = ARB_TIER_MARKETS,
) -> list[PollTarget]:
    """The full per-event schedule, descending by hours before kickoff.

    Targets at the same hour are deduplicated keeping the first, more complete
    tier, so a narrow arb poll never replaces a full-market one.
    """
    targets = (
        [PollTarget(h, full_markets, DEFAULT_COST_PER_POLL, "early") for h in early_poll_targets_hours()]
        + [PollTarget(h, full_markets, DEFAULT_COST_PER_POLL, "sparse") for h in sparse_poll_targets_hours()]
        + [PollTarget(h, full_markets, DEFAULT_COST_PER_POLL, "dense") for h in dense_poll_targets_hours()]
        # Listed before the arb tier so it wins the dedupe at its offset.
        + [PollTarget(CLOSE_CAPTURE_HOURS, full_markets, DEFAULT_COST_PER_POLL, "close")]
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


EARLY_POLL_TARGETS_HOURS = early_poll_targets_hours()
SPARSE_POLL_TARGETS_HOURS = sparse_poll_targets_hours()
DENSE_POLL_TARGETS_HOURS = dense_poll_targets_hours()
ARB_POLL_TARGETS_HOURS = arb_poll_targets_hours()
POLL_TARGETS = build_poll_targets()
POLL_TARGETS_HOURS = [t.hours_before_kickoff for t in POLL_TARGETS]
POLLS_PER_EVENT = len(POLL_TARGETS)


def season_credit_cost(n_games: int, targets: list[PollTarget] | None = None) -> int:
    """Worst-case credits for `n_games`: every poll returns data at full price.

    Use `realistic_season_credit_cost` for planning; free empty probes make
    this ceiling unreachable.
    """
    targets = targets if targets is not None else POLL_TARGETS
    return n_games * sum(t.cost for t in targets)


def realistic_season_credit_cost(
    n_games: int,
    targets: list[PollTarget] | None = None,
    early_capture_rate: float = 0.15,
    returned_market_fraction: float = 5 / 7,
) -> int:
    """Planning estimate that accounts for how the endpoint actually bills.

    Empty polls are free, so only `early_capture_rate` of early probes cost
    anything (0.15 is a deliberate over-estimate). Even when props exist, not
    every market returns, hence `returned_market_fraction`. Both are
    parameters so they can be re-measured.
    """
    targets = targets if targets is not None else POLL_TARGETS
    early = sum(t.cost for t in targets if t.tier == "early")
    rest = sum(t.cost for t in targets if t.tier != "early")
    per_game = early * early_capture_rate + rest * returned_market_fraction
    return int(n_games * per_game)


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
    """Per-event poll state, persisted between restarts (data/props_collect_state.json)."""

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
    markets: str | None = None
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
    """Should this event be polled now, and for which markets?

    Poll N fires once `now` crosses `poll_targets[N].hours_before_kickoff`. If
    the service was down and missed targets, the next untaken target fires
    immediately rather than replaying the missed ones: a late poll beats none.
    The budget check uses this target's own cost.
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
