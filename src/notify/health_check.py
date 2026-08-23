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

    A list today rather than a single dict because per-service checks (props vs.
    mainline write freshness) are the obvious next additions, and callers
    shouldn't have to change shape when they arrive.
    """
    return [check_collector_health(store, now=now, **kwargs)]


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

    **TODO after props start posting: promote this from diagnostic to alert.**
    From that point the same reading means the props collector has died, and
    the aggregate check structurally cannot see it.
    """
    now = _now(now)
    df = store.read_as_of(now)
    if df.empty:
        return pd.DataFrame(columns=["market", "last_write", "hours_ago", "n_snapshots"])

    out = df.groupby("market").agg(last_write=("capture_time", "max"), n_snapshots=("capture_time", "size")).reset_index()
    out["hours_ago"] = (now - out["last_write"]).dt.total_seconds() / 3600
    return out.sort_values("hours_ago")
