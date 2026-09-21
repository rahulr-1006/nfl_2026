"""Budget-aware polling cadence for player props -- a different scheduling
problem than the mainline collector's `budget.py`.

The mainline collector polls the *whole slate* on a shared cadence (one
bulk call covers every game). Props can't work that way: they're fetched
per-event (`OddsApiClient.get_event_odds`, real credits per call), and
each game's props post independently -- typically Tue-Thu of that game's
own week, not on a fixed calendar schedule. So this module decides, per
event, whether to poll it *right now*: has it entered the posting window,
has it already gotten its scheduled polls, and is there budget for it.

**A four-tier schedule, each tier buying a different thing.** The
historical props backfill (`props_historical.py`) was forced to a single
near-kickoff snapshot per game because the historical endpoint costs 10x
per call. Live polling doesn't have that multiplier, so:
  - **early** (`POSTING_WINDOW_DAYS` -> `SPARSE_WINDOW_HOURS`, every
    `EARLY_POLL_INTERVAL_HOURS`): coarse, mostly-free probes to catch the
    moment props first appear. Added 2026-08-23 after the opener posted 17
    days out and a 5-day window skipped it.
  - **sparse** (`SPARSE_WINDOW_HOURS` -> `DENSE_WINDOW_HOURS`, every
    `SPARSE_POLL_INTERVAL_HOURS`, all 7 markets): catches early posting and
    slow drift.
  - **dense** (final `DENSE_WINDOW_HOURS`, every `DENSE_POLL_INTERVAL_HOURS`,
    all 7 markets): real rolling CLV movement through the window that
    matters most. Mirrors the mainline collector's own
    dense-window-near-kickoff philosophy (`src/collect/budget.py`).
  - **arb** (final `ARB_WINDOW_HOURS`, every `ARB_POLL_INTERVAL_HOURS`,
    `ARB_MARKETS` only): cheap high-frequency coverage for the one signal
    that genuinely needs density -- see the `ARB_MARKETS` block below.

`build_poll_targets` merges all four into one time-ordered schedule and
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
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from src.collect.props import (
    DEFAULT_MARKETS as _ALL_PROP_MARKETS,  # single source of truth for the 7 O/U prop markets
)

# Start attempting once a game is this close. **Widened 5.0 -> 21.0 on
# 2026-08-23 after the 5-day assumption was proven wrong by live data.** Props
# for the 2026-09-09 opener were already posted on 08-23 -- 17 days out, with
# FanDuel and BetRivers quoting 5 markets each -- and the 5-day window was
# silently skipping them. Every skipped day is entry-price data that cannot be
# recovered, and CLV is undefined without an entry price.
#
# Safe to widen this far only because of two measured facts:
#   1. The live per-event endpoint bills **only for markets that return data**,
#      so probing a game with no props posted costs **0 credits** (verified on
#      three real games).
#   2. `props_scheduler` no longer advances `poll_count` on an empty poll, so
#      free probes cannot exhaust the ~29-slot schedule before props exist.
# Without (2), widening this would be actively harmful.
POSTING_WINDOW_DAYS = 21.0
DENSE_WINDOW_HOURS = 48.0  # the most critical window: dense rolling-CLV polling covers this many hours before kickoff -- matches the mainline collector's own "48h pre-slate" dense window
DENSE_POLL_INTERVAL_HOURS = 4.0  # spacing between dense polls -- tune this (not POLLS_PER_EVENT directly) to go denser/sparser
SPARSE_POLL_INTERVAL_HOURS = 12.0  # spacing for "basic" polls covering the period BEFORE the dense window kicks in
# The sparse tier now starts here rather than at POSTING_WINDOW_DAYS. Widening the
# posting window to 21 days must NOT mean 21 days of 12-hourly polling -- that
# would be 38 sparse polls per event (~212K credits worst case, double the grant).
# The early period gets its own coarse tier instead: cheap probes to catch the
# moment props appear, then the real schedule takes over.
SPARSE_WINDOW_HOURS = 120.0
# 2026-09-02: 72.0 -> 24.0 (daily). Two reasons, both measured on live 2026 data:
#
# 1. **The old spacing left a 96h blind spot.** See the `ceil` fix in
#    `early_poll_targets_hours` -- at 72h the tier's last target was 216h (9 days)
#    and the sparse tier does not begin until 120h (5 days). On 2026-09-02 the
#    live store showed prop captures stopping dead at 215.6h with the opener
#    180.6h out: 60.6h of posted, moving lines with zero capture scheduled.
# 2. **Pinnacle was mid-ramp inside that gap** (2 of 16 games quoted on 09-02),
#    and this window is not re-collectable -- every historical prop row in this
#    project is a single ~20-minutes-to-kickoff snapshot, so pre-kickoff movement
#    can only ever be observed live, once, as it happens.
#
# Cost is an upper bound: empty probes bill 0 and `poll_count` advances only on
# capture, so the daily probes before a book posts are free.
EARLY_POLL_INTERVAL_HOURS = 24.0  # daily probing across the 21-day -> 5-day stretch
# 2026-08-22: trimmed from 2h/8h (33 polls/event, ~94K blended season cost) to 3h/12h
# after recording the paid plan as a ONE-TIME ~100K grant (resets 9/1, no rollover,
# user isn't renewing past that) rather than recurring monthly.
#
# **2026-08-25: that premise was WRONG and both trims below were made under it.**
# The plan resets to 100K on the 1st of every month (user-confirmed; the "resets
# 9/1" clause above was right, the "isn't renewing" clause was not). The binding
# constraint is therefore a MONTHLY cap, not a season total -- and the season total
# is no longer a meaningful number. Simulated against the real 2026 schedule (272
# REG games, credits attributed to the month each poll actually fires):
#
#     Aug 924 | Sep 19,710 | Oct 23,780 | Nov 22,996 | Dec 23,728 | Jan 8,414
#
# Peak month is **23.8% of the monthly allowance**. The 99,552 season figure that
# drove the compression below is ~24% utilization, not 99%. Density is no longer
# budget-constrained; see the arb-tier widening under ARB_WINDOW_HOURS.
#
# 2026-08-23: dense interval trimmed again, 3h -> 4h. Adding the arb tier below had
# pushed the schedule to 99,180 credits -- **99.2% of the entire grant**, which is not
# a margin, it's a rounding error away from props collection silently stopping in
# January when the safety reserve starts blocking polls. Trimming the DENSE tier
# (rather than the arb tier) is the principled cut: CLV needs only an entry price and
# a close, so intermediate sampling density costs almost nothing methodologically,
# whereas 30-minute arb density is exactly what the one validated live edge depends
# on. Result: 29 polls/event, 84,360 theoretical (~84% of grant, ~15.6K margin).
#
# 2026-08-25: the reasoning above still holds on the METHODOLOGY (CLV genuinely does
# not need intermediate density), so the dense tier is deliberately left at 4h even
# though the budget would now allow 2h. Reverting it would buy ~0 methodologically
# and cost 34.5% of the monthly cap instead of 23.8%. The arb tier is the one that
# was starved for budget reasons, so that is the one being widened.
DEFAULT_COST_PER_POLL = 14  # regions=us,eu x 7 markets, theoretical max (real blended cost runs lower -- see props_ev_backtest memory, ~101/10=~10/event on the historical endpoint's 10x rate)
DEFAULT_SAFETY_RESERVE_CREDITS = 500  # large relative to a single poll's cost -- props credits are meant to leave headroom for a possible future historical batch 2, not be spent to the floor. 2026-08-25: that rationale was written against a non-renewing balance; under the monthly reset the reserve now just guards the tail of each month, which is a weaker but still valid reason to keep it.

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
# 2026-08-25: widened 6.0 -> 12.0 once the monthly-reset correction above removed the
# budget ceiling. Arb is the one signal density genuinely helps (fleeting cross-book
# windows) and one of only two validated edges here, so it gets the freed headroom
# rather than the dense tier. Measured cost: **44 polls/event, 406 credits/event,
# peak month 26,208 (26.2% of the monthly cap, up from 23.8%)**. Cheaper than the
# +12.8pp a naive count suggests, because the arb tier now overlaps the dense tier
# below 48h and `build_poll_targets` dedupes on `hours_before_kickoff` -- the
# collision keeps the dense target (all 7 markets) rather than adding a second poll.
#
# **The 2026-08-25 widening above bought COVERAGE, not detection latency.** Worst-case
# time from a price appearing to a text arriving is bounded by the poll spacing plus
# the monitor's own cadence. More sampling points inside the window does not make any
# single detection faster; only the spacing does.
#
# 2026-09-14: **latency halved, 0.5h -> 0.25h.** Done together with
# `props_scheduler.DEFAULT_TICK_MINUTES` 30.0 -> 15.0, and the two MUST move together
# -- the service tick is a hard floor, so a 0.25h target cannot fire on a 30-minute
# tick and halving one alone buys nothing.
#
#     price appears -> <=15 min (this spacing, floored by the 15-min tick)
#                   -> <= 5 min (com.nflclv.monitor StartInterval 300s)
#                   = ~20 min worst case, down from ~35
#
# Why it is worth paying for: arb is one of only two validated edges here, its windows
# are fleeting, and `shadow_log.py` exists precisely because whether an alerted price
# survives the detection latency has never been measured. Cutting the latency is the
# one lever that improves the answer rather than just measuring it.
#
# Cost, simulated against the real 272-game 2026 REG schedule at the measured billing
# rates (empty early probes free, 5-of-7 markets returning) rather than worst case:
#
#     month     current      new     delta
#     2026-09    14,669   17,960   +3,291
#     2026-10    18,190   22,304   +4,114
#     2026-11    17,888   22,756   +4,868   <- peak
#     2026-12    18,161   22,413   +4,252
#     2027-01     7,065    9,191   +2,126
#
# **Peak month 22.8% of the 100K monthly cap** (was 18.2%). POLLS_PER_EVENT 55 -> 79.
# The binding constraint is monthly, not seasonal -- see the 2026-08-25 correction
# above. This tier is deliberately the one that gets the headroom.
ARB_WINDOW_HOURS = 12.0  # final hours before kickoff, where prices move most and arb windows actually open
ARB_POLL_INTERVAL_HOURS = 0.25  # must stay >= props_scheduler.DEFAULT_TICK_MINUTES -- see above
ARB_COST_PER_POLL = 4  # regions=us,eu x 2 markets

# --- close tier (2026-09-02) -------------------------------------------------
# **One full-market capture inside CLOSE_MAX, so props CLV can be computed at
# all.** The dense tier bottoms out at DENSE_POLL_INTERVAL_HOURS (4.0h) and
# everything below it is the arb tier, which requests only ARB_MARKETS. That left
# `player_pass_yds`, `player_rush_yds`, `player_rush_tds`, `player_reception_yds`
# and `player_reception_tds` with an entry series and **no close** -- five of the
# seven markets silently uncomputable for CLV, this project's headline metric.
#
# The cause was not a CLV bug: it was the arb tier's market-narrowing (a cost
# optimisation for a different signal) deciding what CLV was allowed to measure.
# `build_poll_targets` already dedupes keeping the more comprehensive tier for
# exactly this reason -- but no full-market target existed down here to keep.
#
# 1.5h rather than 0.5h deliberately: it sits inside rolling_clv_2024.py's
# CLOSE_MAX (2.0h) while leaving the arb tier's 1.0h and 0.5h captures untouched,
# so the one validated live edge keeps its densest pre-kickoff sampling.
#
# Cost is ~0.4pp of the monthly cap (peak month 27,408 -> 27,780 at the measured
# 10 credits/poll) and POLLS_PER_EVENT does not change, because this REPLACES the
# arb target at the same offset instead of adding one.
CLOSE_CAPTURE_HOURS = 1.5


def dense_poll_targets_hours(dense_window_hours: float = DENSE_WINDOW_HOURS, dense_poll_interval_hours: float = DENSE_POLL_INTERVAL_HOURS) -> list[float]:
    """Descending list of hours-before-kickoff targets for the dense
    ("most critical") polling tier, from `dense_window_hours` out down to
    one interval before kickoff -- default 48/2 = 24 targets.
    """
    n = max(1, round(dense_window_hours / dense_poll_interval_hours))
    return [dense_window_hours - i * dense_poll_interval_hours for i in range(n)]


def early_poll_targets_hours(
    posting_window_days: float = POSTING_WINDOW_DAYS,
    sparse_window_hours: float = SPARSE_WINDOW_HOURS,
    early_poll_interval_hours: float = EARLY_POLL_INTERVAL_HOURS,
) -> list[float]:
    """Coarse probes across the far-out stretch (21 days -> 5 days).

    These exist to CATCH THE MOMENT props appear, not to sample movement. Props
    for the 2026-09-09 opener posted 17 days out, and a 5-day window skipped them
    entirely. Because the live endpoint bills only for markets that return data,
    a probe on a game with no props posted costs 0 credits -- and
    `props_scheduler` does not advance `poll_count` on an empty poll, so these
    probes cannot consume the real schedule.
    """
    span = posting_window_days * 24.0 - sparse_window_hours
    if span <= 0:
        return []
    # `ceil`, not `round` (2026-09-02). With round(), a span that is not a whole
    # number of intervals drops the final target instead of adding one: at the old
    # 72h spacing, span=384h gave round(5.33)=5 targets ending at 216h, while the
    # sparse tier does not start until `sparse_window_hours` (120h) -- a 96h hole in
    # the middle of the posting window, wider than either neighbouring interval.
    # ceil() closes the tier down to the sparse handoff. The last target is always
    # > sparse_window_hours by construction (span excludes it), so this cannot
    # collide with or overshoot the sparse tier.
    n = max(1, math.ceil(span / early_poll_interval_hours))
    return [posting_window_days * 24.0 - i * early_poll_interval_hours for i in range(n)]


def sparse_poll_targets_hours(
    posting_window_days: float = POSTING_WINDOW_DAYS,
    dense_window_hours: float = DENSE_WINDOW_HOURS,
    sparse_poll_interval_hours: float = SPARSE_POLL_INTERVAL_HOURS,
    sparse_window_hours: float = SPARSE_WINDOW_HOURS,
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
    span_hours = sparse_window_hours - dense_window_hours
    n = max(1, round(span_hours / sparse_poll_interval_hours))
    return [sparse_window_hours - i * sparse_poll_interval_hours for i in range(n)]


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
        [PollTarget(h, full_markets, DEFAULT_COST_PER_POLL, "early") for h in early_poll_targets_hours()]
        + [PollTarget(h, full_markets, DEFAULT_COST_PER_POLL, "sparse") for h in sparse_poll_targets_hours()]
        + [PollTarget(h, full_markets, DEFAULT_COST_PER_POLL, "dense") for h in dense_poll_targets_hours()]
        # Before the arb tier: dedupe keeps the FIRST target at a given hour, and
        # this one must win over the arb target at the same offset (see
        # CLOSE_CAPTURE_HOURS -- it is the only full-market close there is).
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
POLL_TARGETS_HOURS = [t.hours_before_kickoff for t in POLL_TARGETS]  # kept for callers that only need the schedule shape
POLLS_PER_EVENT = len(POLL_TARGETS)  # derived, don't hardcode this elsewhere


def season_credit_cost(n_games: int, targets: list[PollTarget] | None = None) -> int:
    """**Worst case** credits to poll `n_games` at this schedule: every poll
    returns data and bills full price.

    Summed from the actual tier definitions rather than multiplying an average.
    Use `realistic_season_credit_cost` for planning -- this number is a ceiling
    that the `early` tier makes structurally unreachable (see below).
    """
    targets = targets if targets is not None else POLL_TARGETS
    return n_games * sum(t.cost for t in targets)


def realistic_season_credit_cost(
    n_games: int,
    targets: list[PollTarget] | None = None,
    early_capture_rate: float = 0.15,
    returned_market_fraction: float = 5 / 7,
) -> int:
    """A planning estimate that accounts for two measured facts the worst case
    ignores.

    1. **Empty polls are free.** The live per-event endpoint bills only for
       markets that actually return data, so an `early`-tier probe on a game
       whose props have not posted costs **0 credits** (verified on three real
       games, 2026-08-23). Only marquee games post ~3 weeks out --
       `early_capture_rate` is the fraction of early probes expected to find
       anything. 0.15 is a deliberate over-estimate; on 2026-08-23 exactly 2 of
       272 upcoming games had props (0.7%).
    2. **Partial market coverage.** Even when props exist, not all 7 markets
       return -- the real opener poll billed 10, not 14 (5 of 7 markets), hence
       `returned_market_fraction`.

    Both are stated as parameters rather than baked in, so a future session can
    re-measure them instead of trusting these figures.
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
