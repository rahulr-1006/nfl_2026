"""Live +EV monitor entrypoint: `python -m src.notify.monitor_run`.

Meant to be invoked repeatedly by launchd's StartInterval
(ops/com.nflclv.monitor.plist), not run as a long-lived process -- each
invocation reads the current point-in-time store, scans for new/improved
spots, texts about them, and exits. Cheap: no network calls of its own,
just local parquet reads, so it can run far more often than the collector
without touching the Odds API credit budget at all.

**Scans five signals as of 2026-09-08**, in descending order of how much
this project actually trusts them:
  1. **Prop cross-book arbitrage** (`src/signal/props_scan.py`) --
     mathematically guaranteed if both legs place. Highest confidence.
  2. **Moneyline +EV vs Pinnacle** (`src/signal/live_scan.py`) -- the
     original signal.
  3. **Prop EV vs Pinnacle** -- EXPERIMENTAL, tested null on real 2024 data,
     labeled as such in the alert text and gated behind a higher threshold.
  4. **Middling** and 5. **steam** (`src/signal/movement_scan.py`) --
     EXPERIMENTAL, no live track record yet, labeled as such.

Props were previously invisible here, which was the project's biggest
structural gap: the only alerted market was the one the model reliably loses
to, while every validated edge was prop-adjacent.

**The two LINE-MOVEMENT strategies were invisible here too until 2026-09-08.**
`middle_scan.py` and `steam_scan.py` existed and worked, but only as hand-run
scripts, so nothing watched for line movement between the times someone
happened to run them -- and line movement is the one signal that is worthless
after the fact. Their pricing needs a residual sigma, which is why this module
pulls in `cached_residual_stds`; the cache is what makes a ~5-minute cadence
affordable (see `src/backtest/middle_scan.py`).
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from src.backtest.middle_scan import cached_residual_stds
from src.notify.health_check import (
    check_all,
    pinnacle_arrival_message,
    prop_book_coverage,
    unhealthy_messages,
)
from src.notify.sms import SmsError, send_message
from src.signal.live_scan import (
    DEFAULT_EDGE_THRESHOLD,
    AlertRecord,
    find_positive_ev_spots,
    format_alert_message,
    load_alert_state,
    new_or_improved_spots,
    prune_alert_state,
    record_alerts,
    save_alert_state,
)
from src.signal.movement_scan import (
    DEFAULT_MIDDLE_EV_THRESHOLD,
    DEFAULT_STEAM_EDGE_THRESHOLD,
    find_live_middle_spots,
    find_live_steam_spots,
    format_middle_alert_message,
    format_steam_alert_message,
    middle_alert_key,
    steam_alert_key,
)
from src.signal.prereg_scan import PREREG_SHADOW_LOG_PATH, ReadOnceStore
from src.signal.prereg_scan import run as prereg_run
from src.signal.props_scan import (
    DEFAULT_ARB_MARGIN_THRESHOLD,
    DEFAULT_PROP_EV_THRESHOLD,
    find_live_prop_arb_spots,
    find_live_prop_ev_spots,
    format_arb_alert_message,
    format_prop_ev_alert_message,
    prop_alert_key,
)
from src.signal.shadow_log import SHADOW_LOG_PATH
from src.signal.shadow_log import recheck as shadow_recheck
from src.signal.shadow_log import record_alert as shadow_record
from src.store.pit_store import PointInTimeStore, kickoffs_from_store

log = logging.getLogger(__name__)

# Hard ceiling on how much this monitor will suggest staking across all
# still-open alerts in one cycle. The bankroll is $100 with at most 2 manual
# reloads ($300 total risk capital, decided 2026-10-04; paper sec. on sizing), and
# per-bet caps cannot see each other: ten separate
# 2%-of-bankroll suggestions is $20 of simultaneous exposure that no individual
# `apply_bankroll_caps` call knows about. Props make this real rather than
# theoretical -- a single slate can produce many prop alerts at once, unlike
# the one-per-game moneyline case this monitor was built for.
DEFAULT_MAX_SUGGESTED_EXPOSURE = 20.0

# Sentinel key in the shared alert state marking that the Pinnacle-arrival
# announcement has already fired. Namespaced so it can never collide with a
# real spot key (those are event/side/book or prop-contract shaped).
PINNACLE_ARRIVAL_KEY = "__pinnacle_props_arrival__"


def _apply_exposure_cap(
    spots: pd.DataFrame,
    remaining: float,
    stake_column: str = "suggested_stake",
    default_stake: float = 2.0,
) -> tuple[pd.DataFrame, float]:
    """Keep alerts in priority order until their suggested stakes exhaust
    `remaining`, then stop. Returns `(kept, remaining_after)`.

    Truncates rather than shrinking stakes: a suggestion the bankroll can't
    actually support shouldn't be quietly resized into one it can, because
    the sizing that produced it was computed against the real edge.

    **Threads `remaining` through every signal rather than resetting per
    batch (fixed 2026-08-23).** The cap was previously applied only to the
    moneyline batch -- the one signal it wasn't built for -- while props,
    which is what makes simultaneous exposure real, bypassed it entirely.
    A per-batch cap also isn't the "ceiling across all still-open alerts in
    one cycle" the constant claims to be.

    **Rows with no stake column are charged `default_stake`, not zero.**
    Arbitrage spots carry no `suggested_stake` (each leg is sized
    separately), but they are still real money leaving the bankroll --
    treating them as free would let unlimited arb alerts through a cap whose
    whole purpose is bounding total exposure.
    """
    if spots.empty:
        return spots, remaining
    stakes = (
        spots[stake_column].fillna(default_stake)
        if stake_column in spots.columns
        else pd.Series(default_stake, index=spots.index)
    )
    running = stakes.cumsum()
    kept = spots[running <= remaining]
    return kept, remaining - float(stakes[running <= remaining].sum())


def _alert_batch(
    spots: pd.DataFrame,
    state: dict[str, AlertRecord],
    formatter: Callable[[pd.Series], str],
    key_fn: Callable[[pd.Series], str],
    edge_column: str,
    phone_number: str | None,
    label: str,
    strategy: str,
    shadow_path: Path = SHADOW_LOG_PATH,
) -> tuple[list[pd.Series], dict[str, AlertRecord]]:
    """Dedup -> format -> send one class of alert. Shared by all three
    signals so they can't drift apart in dedup or error handling.
    """
    if spots.empty:
        return [], state

    to_alert = new_or_improved_spots(spots, state, key_fn=key_fn, edge_column=edge_column)
    if to_alert.empty:
        log.info("%s: %d spot(s) found, none new/improved since last alert", label, len(spots))
        return [], state

    sent_rows: list[pd.Series] = []
    for _, row in to_alert.iterrows():
        message = formatter(row)
        if not phone_number:
            log.info("would alert (no phone configured): %s", message)
            continue
        try:
            send_message(message, phone_number)
            sent_rows.append(row)
            log.info("sent alert: %s", message)
        except SmsError as exc:
            log.error("failed to send %s alert for %s: %s", label, row["event_id"], exc)

    # Only spots that actually reached the phone get marked alerted -- an
    # unconfigured number or a failed send must not silently suppress
    # future attempts at the same spot.
    if sent_rows:
        state = record_alerts(pd.DataFrame(sent_rows), state, key_fn=key_fn, edge_column=edge_column)
        # Shadow log: record what the price WAS at alert time, so the next
        # re-check can measure whether it survived the ~35min detection
        # latency. Guarded because this is measurement, not alerting -- a
        # shadow-log failure must never cost a real alert.
        try:
            shadow_record(pd.DataFrame(sent_rows), strategy, key_fn, path=shadow_path)
        except Exception:
            log.exception("shadow log: failed to record %s alerts (alerts still sent)", label)
    return sent_rows, state


def run(
    store_root: str = "data/snapshots",
    threshold: float = DEFAULT_EDGE_THRESHOLD,
    prop_ev_threshold: float = DEFAULT_PROP_EV_THRESHOLD,
    arb_margin_threshold: float = DEFAULT_ARB_MARGIN_THRESHOLD,
    middle_ev_threshold: float = DEFAULT_MIDDLE_EV_THRESHOLD,
    steam_edge_threshold: float = DEFAULT_STEAM_EDGE_THRESHOLD,
    max_exposure: float = DEFAULT_MAX_SUGGESTED_EXPOSURE,
    shadow_path: Path = SHADOW_LOG_PATH,
    prereg_path: Path | None = None,
) -> int:
    """One scan-and-alert cycle across all five signals. Returns the number
    of alerts actually sent. Never raises for expected failure modes (no
    phone number configured, a single SMS send failing, one scan erroring)
    -- this runs unattended and a single bad tick must not stop the next one.
    """
    phone_number = os.environ.get("ALERT_PHONE_NUMBER")
    if not phone_number:
        log.warning("ALERT_PHONE_NUMBER not set in .env -- scanning but not sending any alerts")

    store = PointInTimeStore(root=store_root)
    # Prune before use: this state is never otherwise cleaned and grew to 874
    # entries, 866 of them for games played in 2023-24. Stale keys are dead
    # weight rather than a correctness bug (a played game's spot cannot recur),
    # but an alert history nobody can trust is not much of an audit trail.
    loaded = load_alert_state()
    state = prune_alert_state(loaded, kickoffs=kickoffs_from_store(store))
    pruned = len(loaded) - len(state)
    all_sent: list[pd.Series] = []

    # Liveness first, and OUTSIDE the spot-alert dedup: if the collector has
    # stopped, the scanners below will quietly find nothing and this tick would
    # otherwise look like a clean "no opportunities" cycle. Silence from a dead
    # collector and silence from a quiet market are indistinguishable downstream,
    # which is exactly how a 58-hour outage went unnoticed in live collection.
    try:
        for message in unhealthy_messages(check_all(store)):
            log.error(message)
            if phone_number:
                try:
                    send_message(message, phone_number)
                except SmsError as exc:
                    log.error("failed to send health alert: %s", exc)
    except Exception:
        log.exception("health check failed, continuing with scans")

    # One-time announcement when Pinnacle starts quoting props. Deduped through
    # the SAME alert state the spot scanners use, so a persistent condition
    # texts once rather than every 30 minutes forever. Worth an alert because
    # three capabilities switch on at that moment (anchored EV, props CLV,
    # team-total scanning) and until then they return empty indistinguishably
    # from "no spots found".
    try:
        arrival = pinnacle_arrival_message(prop_book_coverage(store))
        if arrival and PINNACLE_ARRIVAL_KEY not in state:
            log.info(arrival)
            if phone_number:
                try:
                    send_message(arrival, phone_number)
                except SmsError as exc:
                    log.error("failed to send Pinnacle-arrival alert: %s", exc)
            state = {**state, PINNACLE_ARRIVAL_KEY: AlertRecord(edge=1.0, alerted_at=datetime.now(UTC))}
            save_alert_state(state)
    except Exception:
        log.exception("pinnacle-arrival check failed, continuing with scans")

    # Each scan is independently guarded: a malformed props frame must not
    # stop the moneyline scan (or vice versa) on an unattended run.
    def _safe(scan: Callable[[], pd.DataFrame], label: str) -> pd.DataFrame:
        try:
            return scan()
        except Exception:
            log.exception("%s scan failed, skipping it this cycle", label)
            return pd.DataFrame()

    # One exposure budget shared across all five signals, spent in confidence
    # order: guaranteed arbitrage first, then moneyline, then the experimental
    # props-EV signal last -- so a flood of low-confidence alerts can never
    # crowd out a real lock.
    remaining = max_exposure

    arb_spots = _safe(lambda: find_live_prop_arb_spots(store, min_margin=arb_margin_threshold), "prop arb")
    arb_spots, remaining = _apply_exposure_cap(arb_spots, remaining)
    sent, state = _alert_batch(
        arb_spots, state, format_arb_alert_message, prop_alert_key, "arb_margin", phone_number,
        "prop arb", "prop_arb", shadow_path=shadow_path,
    )
    all_sent.extend(sent)

    ml_spots = _safe(lambda: find_positive_ev_spots(store, threshold=threshold), "moneyline")
    ml_spots, remaining = _apply_exposure_cap(ml_spots, remaining)
    sent, state = _alert_batch(
        ml_spots, state, format_alert_message, lambda r: f"{r['event_id']}|{r['side']}|{r['book']}",
        "edge", phone_number, "moneyline", "moneyline_ev", shadow_path=shadow_path,
    )
    all_sent.extend(sent)

    prop_ev_spots = _safe(
        lambda: find_live_prop_ev_spots(store, threshold=prop_ev_threshold), "prop EV"
    )
    prop_ev_spots, remaining = _apply_exposure_cap(prop_ev_spots, remaining)
    sent, state = _alert_batch(
        prop_ev_spots, state, format_prop_ev_alert_message, prop_alert_key, "edge", phone_number,
        "prop EV", "prop_ev", shadow_path=shadow_path,
    )
    all_sent.extend(sent)

    # Line movement (middling + steam). Both need the margin/total residual
    # sigma; `cached_residual_stds` keeps that to a dict lookup after the first
    # call instead of refitting Elo + two regressions on every tick. Guarded
    # like every other scan -- and guarded around the FIT as well, because a
    # missing or corrupt training parquet would otherwise take down the arb and
    # moneyline alerts that have nothing to do with it.
    try:
        sigma_margin, sigma_total = cached_residual_stds()
    except Exception:
        log.exception("residual sigma fit failed, skipping middling and steam this cycle")
        sigma_margin = sigma_total = None

    if sigma_margin is not None:
        middle_spots = _safe(
            lambda: find_live_middle_spots(
                store, sigma_margin=sigma_margin, sigma_total=sigma_total,
                threshold=middle_ev_threshold,
            ),
            "middling",
        )
        # A middle risks BOTH legs, so charge the cap their combined stake.
        middle_spots, remaining = _apply_exposure_cap(middle_spots, remaining, stake_column="total_risked")
        sent, state = _alert_batch(
            middle_spots, state, format_middle_alert_message, middle_alert_key, "ev_rate",
            phone_number, "middling", "middle", shadow_path=shadow_path,
        )
        all_sent.extend(sent)

        steam_spots = _safe(
            lambda: find_live_steam_spots(
                store, sigma_margin=sigma_margin, sigma_total=sigma_total,
                threshold=steam_edge_threshold,
            ),
            "steam",
        )
        steam_spots, remaining = _apply_exposure_cap(steam_spots, remaining)
        sent, state = _alert_batch(
            steam_spots, state, format_steam_alert_message, steam_alert_key, "edge",
            phone_number, "steam", "steam", shadow_path=shadow_path,
        )
        all_sent.extend(sent)

    # Re-observe still-open alerted spots. Store-only, 0 credits. Runs after
    # the scans so an alert fired this cycle is recorded before its first
    # re-check, and guarded like everything else here: this is measurement,
    # and it must not be able to break the alert path.
    try:
        shadow_recheck(store, path=shadow_path)
    except Exception:
        log.exception("shadow log: re-check failed, continuing")

    # Pre-registered H1/H1b (preregistration_wk5-9.md): LOGGED, NEVER TEXTED, and
    # to their own file so no existing report shows holdout results before
    # 2026-11-10. Last in the tick on purpose -- it adds a store read, and it must
    # never delay or break a real alert. The path is derived from `shadow_path`
    # so a test that redirects the shadow log redirects this one too.
    prereg = prereg_path or shadow_path.with_name(PREREG_SHADOW_LOG_PATH.name)
    try:
        once = ReadOnceStore(store)
        prereg_run(once, path=prereg)
        shadow_recheck(once, path=prereg)
    except Exception:
        log.exception("prereg log-only scan failed, continuing")

    # Persist if anything changed -- alerts sent OR entries pruned. Saving only
    # on `all_sent` would leave the prune in memory and re-do it every cycle
    # forever, so the file would never actually shrink.
    if all_sent or pruned:
        save_alert_state(state)
    if pruned:
        log.info("pruned %d stale alert-state entr(ies)", pruned)
    if not all_sent:
        log.info("scan ok: no new alerts this cycle")

    return len(all_sent)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    load_dotenv()
    run()


if __name__ == "__main__":
    main()
