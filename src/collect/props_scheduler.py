"""Scheduler wiring for player-prop polling -- one `tick()` per
opportunity, mirroring `src/collect/scheduler.py`'s structure but
deciding *per event* (`src/collect/props_budget.py`) instead of per-slate,
since props post on each game's own schedule, not a shared one.

`tick()` never raises for ordinary failures (network errors, an unmatched
event, one bad poll) -- it logs and moves to the next event, same
discipline as the mainline collector. A free `get_events()` call opens
every tick (0 credits) so the eligible-event list is always current; only
`get_event_odds` calls, gated by `decide_props_poll`, cost real credits.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler

from src.collect.client import OddsApiClient, OddsApiError, RateLimitExceeded
from src.collect.props import (
    DEFAULT_MARKETS,
    DEFAULT_REGIONS,
    event_odds_to_prop_snapshots,
)
from src.collect.props_budget import (
    POLLS_PER_EVENT,
    EventPollState,
    PropsCollectorState,
    decide_props_poll,
    load_state,
    save_state,
)
from src.collect.transform import ScheduleIndex, UnmatchedEventError, match_event
from src.store.pit_store import PointInTimeStore

log = logging.getLogger(__name__)

DEFAULT_STATE_PATH = Path("data/props_collect_state.json")
DEFAULT_TICK_MINUTES = 30.0  # cheap (free events list + gated per-event polls), no need for the mainline collector's 5-min cadence


@dataclass
class PropsCollectorContext:
    season: int
    client: OddsApiClient
    store: PointInTimeStore
    schedule_index: ScheduleIndex
    name_to_abbr: dict[str, str]
    state_path: Path = DEFAULT_STATE_PATH
    regions: str = DEFAULT_REGIONS
    markets: str = DEFAULT_MARKETS
    tick_minutes: float = DEFAULT_TICK_MINUTES


def tick(ctx: PropsCollectorContext, now: datetime | None = None) -> None:
    """Wraps _tick(ctx) so one unexpected bug never kills a long-running
    process -- same discipline as src/collect/scheduler.py's tick().

    `now` is injectable (defaults to wall-clock time) so every poll
    decision -- inherently time-relative-to-kickoff -- is deterministically
    testable, not dependent on when the test happens to run.
    """
    try:
        _tick(ctx, now or datetime.now(UTC))
    except Exception:
        log.exception("unexpected error in props tick(), skipping this cycle")


def _tick(ctx: PropsCollectorContext, now: datetime) -> None:
    state = load_state(ctx.state_path)

    try:
        events_resp = ctx.client.get_events()
    except (RateLimitExceeded, OddsApiError) as exc:
        log.warning("props tick: failed to list events: %s", exc)
        return

    events = dict(state.events)
    remaining_credits = state.remaining_credits
    polled = skipped = unmatched = failed = 0

    for event in events_resp.events:
        event_id = event.get("id")
        commence_time = event.get("commence_time")
        if event_id is None or commence_time is None:
            continue
        kickoff = datetime.fromisoformat(commence_time)

        event_state = events.get(event_id, EventPollState())
        decision = decide_props_poll(now, kickoff, event_state, remaining_credits)
        if not decision.should_poll:
            skipped += 1
            continue

        try:
            match = match_event(event["home_team"], event["away_team"], ctx.season, ctx.schedule_index, ctx.name_to_abbr)
        except UnmatchedEventError:
            log.warning("props tick: unmatched event %s (%s @ %s)", event_id, event.get("away_team"), event.get("home_team"))
            unmatched += 1
            continue

        try:
            # This poll's OWN markets, not ctx.markets -- the arb tier deliberately
            # requests a narrow, cheap subset (see props_budget.ARB_MARKETS). Using
            # ctx.markets here would silently pay full price for every arb poll and
            # blow the season budget the tiering exists to protect.
            response = ctx.client.get_event_odds(event_id, ctx.regions, decision.markets or ctx.markets)
        except (RateLimitExceeded, OddsApiError) as exc:
            log.warning("props tick: failed to poll %s (%s): %s", event_id, match.event_id, exc)
            failed += 1
            continue

        snapshots = event_odds_to_prop_snapshots(response.events[0], response.fetched_at, match)
        if not snapshots:
            # **Do NOT advance poll_count on an empty poll** (2026-08-23). The
            # live per-event endpoint bills only for markets that actually
            # return data, so probing a game whose props haven't posted costs
            # **0 credits** -- verified against three real games. But the poll
            # schedule is a fixed budget of ~29 slots per event, so counting
            # these free empty probes would burn the entire schedule during the
            # weeks before props exist and leave nothing for the pre-kickoff
            # window that actually matters.
            #
            # The schedule must track *captures*, not API calls. This is what
            # makes a wide POSTING_WINDOW_DAYS safe: we can probe early and
            # often for free, and the real schedule only starts advancing once
            # there is something to capture.
            skipped += 1
            continue

        ctx.store.write(snapshots)
        events[event_id] = EventPollState(poll_count=event_state.poll_count + 1, last_polled_at=now)
        if response.remaining_credits is not None:
            remaining_credits = response.remaining_credits
        polled += 1
        log.info(
            "props tick: polled %s (%s) tier=%s cost=%s, wrote %d snapshots, poll #%d/%d, credits_remaining=%s",
            match.event_id, event_id, decision.tier, decision.cost, len(snapshots),
            events[event_id].poll_count, POLLS_PER_EVENT, response.remaining_credits,
        )

    save_state(ctx.state_path, PropsCollectorState(events=events, remaining_credits=remaining_credits))
    log.info("props tick complete: polled=%d skipped=%d unmatched=%d failed=%d", polled, skipped, unmatched, failed)


def build_scheduler(ctx: PropsCollectorContext) -> BlockingScheduler:
    scheduler = BlockingScheduler()
    scheduler.add_job(
        tick,
        "interval",
        minutes=ctx.tick_minutes,
        args=[ctx],
        max_instances=1,
        coalesce=True,
        misfire_grace_time=int(ctx.tick_minutes * 60),
    )
    return scheduler
