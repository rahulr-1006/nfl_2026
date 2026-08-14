"""Scheduler wiring: one `tick()` per poll opportunity, run on an interval.

`tick()` never raises for ordinary failures (network errors, unmatched
events, malformed single events) — it logs and persists state so a
long-running process survives them. It only raises CollectorHalted when
`max_consecutive_failures` is exceeded, which build_scheduler's caller is
expected to let kill the process (a stuck collector should show up as a
dead process, not limp along silently for weeks).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from apscheduler.schedulers.blocking import BlockingScheduler

from src.collect.budget import (
    CollectorState,
    current_period_end,
    decide_poll,
    load_state,
    parse_quota_headers,
    save_state,
)
from src.collect.client import OddsApiClient, OddsApiError, RateLimitExceeded
from src.collect.config import Config
from src.collect.transform import (
    MatchResult,
    ScheduleIndex,
    TransformError,
    UnmatchedEventError,
    event_to_snapshots,
    match_event,
)
from src.store.pit_store import PointInTimeStore

log = logging.getLogger(__name__)


class CollectorHalted(RuntimeError):
    """Raised when consecutive failures exceed the configured limit."""


@dataclass
class CollectorContext:
    config: Config
    client: OddsApiClient
    store: PointInTimeStore
    schedule_index: ScheduleIndex
    name_to_abbr: dict[str, str]
    upcoming_kickoffs: Sequence[datetime]


def _bootstrap_state(config: Config, now: datetime) -> CollectorState:
    anchor = config.budget_period_anchor or now.date()
    return CollectorState(last_poll_time=None, remaining_credits=None, period_anchor=anchor)


def tick(ctx: CollectorContext) -> None:
    """Wraps _tick(ctx) so one unexpected bug in a single poll never kills a
    long-running process. CollectorHalted (too many consecutive failures) is
    the one exception allowed to propagate — that's a deliberate shutdown.
    """
    try:
        _tick(ctx)
    except CollectorHalted:
        raise
    except Exception:
        log.exception("unexpected error in tick(), skipping this cycle")


def _tick(ctx: CollectorContext) -> None:
    now = datetime.now(UTC)
    state = load_state(ctx.config.state_path) or _bootstrap_state(ctx.config, now)

    period_end = current_period_end(now, state.period_anchor, ctx.config.budget_period_days)
    decision = decide_poll(
        now=now,
        upcoming_kickoffs=ctx.upcoming_kickoffs,
        remaining_credits=state.remaining_credits,
        period_end=period_end,
        last_poll_time=state.last_poll_time,
        full_regions=ctx.config.regions,
        full_markets=ctx.config.markets,
        reduced_markets=ctx.config.reduced_markets,
        full_cost=len(ctx.config.regions.split(",")) * len(ctx.config.markets.split(",")),
        reduced_cost=len(ctx.config.regions.split(",")) * len(ctx.config.reduced_markets.split(",")),
        dense_window_hours=ctx.config.dense_window_hours,
        dense_interval_minutes=ctx.config.dense_interval_minutes,
        sparse_interval_minutes=ctx.config.sparse_interval_minutes,
        min_interval_minutes=ctx.config.min_interval_minutes,
        safety_reserve_credits=ctx.config.safety_reserve_credits,
    )

    if not decision.should_poll:
        log.debug("skip poll: reason=%s next_interval=%.1fmin", decision.reason, decision.effective_interval_minutes)
        return

    try:
        response = ctx.client.get_odds(decision.regions, decision.markets, ctx.config.odds_format)
    except (RateLimitExceeded, OddsApiError) as exc:
        log.warning("poll failed: %s", exc)
        new_state = CollectorState(
            last_poll_time=state.last_poll_time,
            remaining_credits=state.remaining_credits,
            period_anchor=state.period_anchor,
            consecutive_failures=state.consecutive_failures + 1,
        )
        save_state(ctx.config.state_path, new_state)
        if new_state.consecutive_failures > ctx.config.max_consecutive_failures:
            raise CollectorHalted(
                f"{new_state.consecutive_failures} consecutive poll failures, last error: {exc}"
            ) from exc
        return

    snapshots = []
    matched, unmatched, malformed = 0, 0, 0
    for event in response.events:
        try:
            match: MatchResult = match_event(
                event["home_team"], event["away_team"], ctx.config.season,
                ctx.schedule_index, ctx.name_to_abbr,
            )
        except UnmatchedEventError:
            unmatched += 1
            continue
        except KeyError as exc:
            log.error("event missing field %s, skipping event: %r", exc, event)
            malformed += 1
            continue

        try:
            snapshots.extend(event_to_snapshots(event, response.fetched_at, match))
            matched += 1
        except TransformError as exc:
            log.error("failed to transform event %s: %s", match.event_id, exc)
            malformed += 1

    if snapshots:
        ctx.store.write(snapshots)

    log.info(
        "poll ok: wrote %d snapshots, matched=%d unmatched=%d malformed=%d credits_remaining=%s",
        len(snapshots), matched, unmatched, malformed, response.remaining_credits,
    )

    quota = parse_quota_headers({
        k: str(v) for k, v in {
            "x-requests-remaining": response.remaining_credits,
            "x-requests-used": response.used_credits,
            "x-requests-last": response.last_cost,
        }.items() if v is not None
    })
    save_state(
        ctx.config.state_path,
        CollectorState(
            last_poll_time=now,
            remaining_credits=quota.remaining if quota.remaining is not None else state.remaining_credits,
            period_anchor=state.period_anchor,
            consecutive_failures=0,
        ),
    )


def build_scheduler(ctx: CollectorContext) -> BlockingScheduler:
    scheduler = BlockingScheduler()
    scheduler.add_job(
        tick,
        "interval",
        minutes=ctx.config.tick_minutes,
        args=[ctx],
        max_instances=1,
        coalesce=True,
        misfire_grace_time=int(ctx.config.tick_minutes * 60),
    )
    return scheduler
