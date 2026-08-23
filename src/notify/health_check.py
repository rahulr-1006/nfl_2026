"""Collector heartbeat: text if the snapshot store stops getting fresh writes.

**This closes a silent failure mode that has already fired once.** Measured
2026-08-23 across the live 2026 collection: the median gap between collector
polls is 9.1 hours, but **the maximum observed gap was 58.2 hours** -- nearly
two and a half days with no writes at all, which nobody noticed at the time
because nothing was watching. The only existing check was running
`make collector-service-status` by hand.

That matters far more once the season starts: a collector that dies overnight
on a game day costs entry prices that can never be recovered, and CLV needs an
entry price. There is no backfill for "we weren't looking."

**Why the threshold is proximity-aware rather than a single constant.** The
mainline collector is deliberately budget-aware (`src/collect/budget.py`): it
polls every ~30 min inside `dense_window_hours` (48h) of a kickoff and backs off
to hourly-or-slower when nothing is close, spreading a 500-credit/month free tier
across the period. A single fixed threshold therefore cannot work -- tight enough
to catch a game-day outage would false-alarm constantly in the quiet weeks, and
loose enough for the quiet weeks would sleep through a game-day outage. So the
allowed silence depends on whether a kickoff is near.

This is a *liveness* check, not a correctness check: it answers "is data still
arriving", not "is the data right".
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import pandas as pd

from src.signal.live_scan import upcoming_only
from src.store.pit_store import PointInTimeStore

log = logging.getLogger(__name__)

# Collector config is dense_interval=30min inside a 48h window, sparse=60min
# otherwise (`src/collect/config.py`). These allow generous multiples of that so
# ordinary budget throttling never pages anyone, while a real outage still
# surfaces well inside a single game day.
DENSE_WINDOW_HOURS = 48.0
MAX_SILENCE_NEAR_KICKOFF = timedelta(hours=6)
# Deliberately below the 58.2h gap actually observed in live collection -- that
# gap should have alerted.
MAX_SILENCE_OTHERWISE = timedelta(hours=30)

PROP_MARKET = "player_prop"

# The props collector polls on its own tiered schedule (`src/collect/props_budget.py`),
# which is coarser than the mainline collector's for most of an event's life:
# every 72h from 21 days out, 12h from 5 days out, 4h inside 48h, 30min inside 6h.
# So props need their own thresholds -- the mainline numbers above would false-alarm
# constantly in the early tier and sleep through a game-day props outage.
#
# Each allowance is a multiple of its tier's polling interval, loosest where a missed
# poll costs least (prices barely move 3 weeks out) and tightest where CLV is actually
# won or lost. The early allowance is deliberately well clear of 72h: with only one or
# two games in the window, aggregate prop writes really are that sparse, and a check
# that pages on a single slipped probe gets muted, which is worse than no check.
PROPS_DENSE_WINDOW_HOURS = 48.0
PROPS_SPARSE_WINDOW_HOURS = 120.0
MAX_PROP_SILENCE_DENSE = timedelta(hours=12)
MAX_PROP_SILENCE_SPARSE = timedelta(hours=30)
MAX_PROP_SILENCE_EARLY = timedelta(hours=120)


def _now(now: datetime | None) -> datetime:
    return now or datetime.now(UTC)


def check_collector_health(
    store: PointInTimeStore,
    now: datetime | None = None,
    dense_window_hours: float = DENSE_WINDOW_HOURS,
    max_silence_near_kickoff: timedelta = MAX_SILENCE_NEAR_KICKOFF,
    max_silence_otherwise: timedelta = MAX_SILENCE_OTHERWISE,
) -> dict:
    """Is the store still receiving writes at the rate its cadence implies?

    Returns a dict with `healthy`, `silence`, `threshold`, `near_kickoff` and a
    human-readable `message`. Never raises for expected conditions (an empty
    store is reported, not thrown) -- this runs unattended and must not become
    its own failure mode.
    """
    now = _now(now)
    df = store.read_as_of(now)

    if df.empty:
        return {"healthy": False, "silence": None, "threshold": None, "near_kickoff": False,
                "last_write": None, "message": "ALERT: snapshot store is empty -- collector has never written."}

    last_write = df["capture_time"].max()
    silence = now - last_write

    upcoming = df[df["event_start_time"] > now]["event_start_time"]
    hours_to_next = (upcoming.min() - now).total_seconds() / 3600 if not upcoming.empty else float("inf")
    near_kickoff = hours_to_next <= dense_window_hours

    threshold = max_silence_near_kickoff if near_kickoff else max_silence_otherwise
    healthy = silence <= threshold

    hrs = silence.total_seconds() / 3600
    where = f"{hours_to_next:.1f}h to next kickoff" if hours_to_next != float("inf") else "no upcoming games"
    message = (
        f"{'OK' if healthy else 'ALERT'}: collector last wrote {hrs:.1f}h ago "
        f"(limit {threshold.total_seconds()/3600:.0f}h, {where})"
    )
    return {"healthy": healthy, "silence": silence, "threshold": threshold,
            "near_kickoff": near_kickoff, "last_write": last_write, "message": message}


def check_all(store: PointInTimeStore, now: datetime | None = None, **kwargs) -> list[dict]:
    """Every liveness check, so the monitor has one thing to call.

    Two checks, not one, because the two collectors are separate services: the
    aggregate store-wide check cannot see a dead props service (the mainline
    service keeps the store-wide timestamp fresh), so props liveness has to be
    asked about separately. `**kwargs` is forwarded only to the aggregate check
    -- the two take different threshold names on purpose, since they watch
    services with different polling cadences.
    """
    return [
        check_collector_health(store, now=now, **kwargs),
        check_props_write_freshness(store, now=now),
    ]


def unhealthy_messages(results: list[dict]) -> list[str]:
    return [r["message"] for r in results if not r["healthy"]]


PINNACLE = "pinnacle"


def prop_book_coverage(store: PointInTimeStore, now: datetime | None = None) -> dict:
    """Which books are currently quoting props on UPCOMING games, and is
    Pinnacle among them?

    **Pinnacle's first appearance is a state change worth noticing, not a
    detail.** Three things become possible only once it quotes: anchored EV
    (`props_scan.find_live_prop_ev_spots` returns empty without a two-sided
    Pinnacle quote to devig), props CLV against the sharp anchor, and
    `team_total_scan`'s market-probability path.

    Until then those paths return empty, which is correct but **silent** -- and
    silence from "Pinnacle isn't quoting yet" is indistinguishable from silence
    from "no spots today". That exact indistinguishability is what hid a
    58-hour collector outage, so the transition is surfaced explicitly rather
    than inferred from an absence of alerts.

    Confirmed against the live store 2026-08-23: FanDuel and BetRivers quoting
    the 9/9 opener 17 days out, Pinnacle absent.
    """
    now = _now(now)
    df = upcoming_only(store.read_as_of(now), now)
    if df.empty or "prop_stat" not in df.columns:
        return {"pinnacle_present": False, "books": [], "n_prop_rows": 0, "n_games": 0}

    props = df[df["market"] == "player_prop"]
    if props.empty:
        return {"pinnacle_present": False, "books": [], "n_prop_rows": 0, "n_games": 0}

    books = sorted(props["book"].unique())
    return {
        "pinnacle_present": PINNACLE in books,
        "books": books,
        "n_prop_rows": len(props),
        "n_games": int(props["event_id"].nunique()),
    }


def pinnacle_arrival_message(coverage: dict) -> str | None:
    """The one-time announcement, or None if Pinnacle still isn't quoting.

    Caller is responsible for firing this only once -- `monitor_run` uses the
    existing alert-state dedup so a persistent condition doesn't text every tick.
    """
    if not coverage.get("pinnacle_present"):
        return None
    return (
        f"PINNACLE NOW QUOTING PROPS -- anchored EV, props CLV and team-total scanning "
        f"are live. {coverage['n_prop_rows']} prop rows across {coverage['n_games']} "
        f"upcoming game(s), books: {', '.join(coverage['books'])}."
    )


def check_props_write_freshness(
    store: PointInTimeStore,
    now: datetime | None = None,
    dense_window_hours: float = PROPS_DENSE_WINDOW_HOURS,
    sparse_window_hours: float = PROPS_SPARSE_WINDOW_HOURS,
    max_silence_dense: timedelta = MAX_PROP_SILENCE_DENSE,
    max_silence_sparse: timedelta = MAX_PROP_SILENCE_SPARSE,
    max_silence_early: timedelta = MAX_PROP_SILENCE_EARLY,
) -> dict:
    """Is the *props* collector still writing? The aggregate check cannot tell.

    **This closes a gap the aggregate check is structurally blind to.** Props and
    mainline are separate launchd services (`com.nflclv.props`,
    `com.nflclv.collector`) writing to one store, and `check_collector_health`
    looks at a single store-wide `max(capture_time)`. So the props service can
    die and the mainline service will hold that timestamp fresh indefinitely --
    the aggregate check reports OK the entire time. That is the same shape of
    blind spot that hid a 58-hour outage: absence of an alert meant nothing,
    because nothing was watching the thing that failed.

    **Freshness is measured over UPCOMING prop rows only.** The store also holds
    the 2023-24 historical prop backfill, whose `capture_time` values are the
    original snapshot times (~1.5 years stale). Filtering through `upcoming_only`
    makes it structurally impossible for backfill rows to be read as live
    collector activity -- the same confusion that once fired 874 of 879 alerts on
    already-played games.

    **Silence is not an alert until props actually post.** Books post props on
    their own schedule, not ours: the 2026 opener posted 17 days out, and before
    that no amount of healthy polling produces a prop row. So an empty upcoming-
    props set reports healthy with an explicit "not posting yet" message rather
    than paging about a collector that is working exactly as intended.
    """
    now = _now(now)
    df = store.read_as_of(now)

    base = {"check": "props_write_freshness", "silence": None, "threshold": None,
            "near_kickoff": False, "last_write": None}

    if df.empty or "prop_stat" not in df.columns:
        # An empty store is already the aggregate check's alert; don't double-page.
        return {**base, "healthy": True, "message": "OK: props freshness not evaluated (store empty)."}

    upcoming = upcoming_only(df, now)
    props = upcoming[upcoming["market"] == PROP_MARKET] if not upcoming.empty else upcoming

    if props.empty:
        return {**base, "healthy": True,
                "message": "OK: no props on upcoming games yet -- books have not posted, nothing to collect."}

    last_write = props["capture_time"].max()
    silence = now - last_write
    hours_to_next = (props["event_start_time"].min() - now).total_seconds() / 3600

    if hours_to_next <= dense_window_hours:
        threshold, tier = max_silence_dense, "dense"
    elif hours_to_next <= sparse_window_hours:
        threshold, tier = max_silence_sparse, "sparse"
    else:
        threshold, tier = max_silence_early, "early"

    healthy = silence <= threshold
    hrs = silence.total_seconds() / 3600
    message = (
        f"{'OK' if healthy else 'ALERT'}: props collector last wrote {hrs:.1f}h ago "
        f"(limit {threshold.total_seconds()/3600:.0f}h, {tier} tier, "
        f"{hours_to_next:.1f}h to next kickoff with props)"
    )
    return {**base, "healthy": healthy, "silence": silence, "threshold": threshold,
            "near_kickoff": hours_to_next <= dense_window_hours,
            "last_write": last_write, "tier": tier, "message": message}


def market_write_freshness(store: PointInTimeStore, now: datetime | None = None) -> pd.DataFrame:
    """Last write per market -- diagnostic, not an alert.

    Useful because the aggregate check can look healthy while ONE market has
    silently stopped: the mainline collector and the props collector are
    separate services writing to the same store, so props could die while
    moneyline keeps the aggregate timestamp fresh.

    **Confirmed against the real store 2026-08-23:** moneyline/spread/total were
    1.6h fresh while `player_prop` read 13,427h (~1.5 years) stale, and the
    aggregate check still said OK. That is *correct today* -- the only prop rows
    are the 2023-24 historical backfill and live props do not post until ~9/2.

    **Promoted to an alert 2026-08-23** once live props began posting: see
    `check_props_write_freshness`, which is the alerting form of the
    `player_prop` row here and runs in `check_all`. This function stays as the
    all-markets diagnostic -- it is the thing to read when you want to know
    *which* market went quiet, across the whole store including backfill.
    """
    now = _now(now)
    df = store.read_as_of(now)
    if df.empty:
        return pd.DataFrame(columns=["market", "last_write", "hours_ago", "n_snapshots"])

    out = df.groupby("market").agg(last_write=("capture_time", "max"), n_snapshots=("capture_time", "size")).reset_index()
    out["hours_ago"] = (now - out["last_write"]).dt.total_seconds() / 3600
    return out.sort_values("hours_ago")
