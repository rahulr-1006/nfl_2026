"""Live +EV monitor entrypoint: `python -m src.notify.monitor_run`.

Meant to be invoked repeatedly by launchd's StartInterval
(ops/com.nflclv.monitor.plist), not run as a long-lived process -- each
invocation reads the current point-in-time store, scans for new/improved
spots, texts about them, and exits. Cheap: no network calls of its own,
just local parquet reads, so it can run far more often than the collector
without touching the Odds API credit budget at all.

**Scans three signals as of 2026-08-23**, in descending order of how much
this project actually trusts them:
  1. **Prop cross-book arbitrage** (`src/signal/props_scan.py`) --
     mathematically guaranteed if both legs place. Highest confidence.
  2. **Moneyline +EV vs Pinnacle** (`src/signal/live_scan.py`) -- the
     original signal.
  3. **Prop EV vs Pinnacle** -- EXPERIMENTAL, tested null on real 2024 data,
     labeled as such in the alert text and gated behind a higher threshold.

Props were previously invisible here, which was the project's biggest
structural gap: the only alerted market was the one the model reliably loses
to, while every validated edge was prop-adjacent.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable

import pandas as pd
from dotenv import load_dotenv

from src.notify.sms import SmsError, send_message
from src.signal.live_scan import (
    DEFAULT_EDGE_THRESHOLD,
    AlertRecord,
    find_positive_ev_spots,
    format_alert_message,
    load_alert_state,
    new_or_improved_spots,
    record_alerts,
    save_alert_state,
)
from src.signal.props_scan import (
    DEFAULT_ARB_MARGIN_THRESHOLD,
    DEFAULT_PROP_EV_THRESHOLD,
    find_live_prop_arb_spots,
    find_live_prop_ev_spots,
    format_arb_alert_message,
    format_prop_ev_alert_message,
    prop_alert_key,
)
from src.store.pit_store import PointInTimeStore

log = logging.getLogger(__name__)

# Hard ceiling on how much this monitor will suggest staking across all
# still-open alerts in one cycle. The bankroll is a fixed $100 with no reloads
# (src/signal/sizing.py), and per-bet caps cannot see each other: ten separate
# 2%-of-bankroll suggestions is $20 of simultaneous exposure that no individual
# `apply_bankroll_caps` call knows about. Props make this real rather than
# theoretical -- a single slate can produce many prop alerts at once, unlike
# the one-per-game moneyline case this monitor was built for.
DEFAULT_MAX_SUGGESTED_EXPOSURE = 20.0


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
    return sent_rows, state


def run(
    store_root: str = "data/snapshots",
    threshold: float = DEFAULT_EDGE_THRESHOLD,
    prop_ev_threshold: float = DEFAULT_PROP_EV_THRESHOLD,
    arb_margin_threshold: float = DEFAULT_ARB_MARGIN_THRESHOLD,
    max_exposure: float = DEFAULT_MAX_SUGGESTED_EXPOSURE,
) -> int:
    """One scan-and-alert cycle across all three signals. Returns the number
    of alerts actually sent. Never raises for expected failure modes (no
    phone number configured, a single SMS send failing, one scan erroring)
    -- this runs unattended and a single bad tick must not stop the next one.
    """
    phone_number = os.environ.get("ALERT_PHONE_NUMBER")
    if not phone_number:
        log.warning("ALERT_PHONE_NUMBER not set in .env -- scanning but not sending any alerts")

    store = PointInTimeStore(root=store_root)
    state = load_alert_state()
    all_sent: list[pd.Series] = []

    # Each scan is independently guarded: a malformed props frame must not
    # stop the moneyline scan (or vice versa) on an unattended run.
    def _safe(scan: Callable[[], pd.DataFrame], label: str) -> pd.DataFrame:
        try:
            return scan()
        except Exception:
            log.exception("%s scan failed, skipping it this cycle", label)
            return pd.DataFrame()

    # One exposure budget shared across all three signals, spent in confidence
    # order: guaranteed arbitrage first, then moneyline, then the experimental
    # props-EV signal last -- so a flood of low-confidence alerts can never
    # crowd out a real lock.
    remaining = max_exposure

    arb_spots = _safe(lambda: find_live_prop_arb_spots(store, min_margin=arb_margin_threshold), "prop arb")
    arb_spots, remaining = _apply_exposure_cap(arb_spots, remaining)
    sent, state = _alert_batch(
        arb_spots, state, format_arb_alert_message, prop_alert_key, "arb_margin", phone_number, "prop arb"
    )
    all_sent.extend(sent)

    ml_spots = _safe(lambda: find_positive_ev_spots(store, threshold=threshold), "moneyline")
    ml_spots, remaining = _apply_exposure_cap(ml_spots, remaining)
    sent, state = _alert_batch(
        ml_spots, state, format_alert_message, lambda r: f"{r['event_id']}|{r['side']}|{r['book']}",
        "edge", phone_number, "moneyline",
    )
    all_sent.extend(sent)

    prop_ev_spots = _safe(
        lambda: find_live_prop_ev_spots(store, threshold=prop_ev_threshold), "prop EV"
    )
    prop_ev_spots, remaining = _apply_exposure_cap(prop_ev_spots, remaining)
    sent, state = _alert_batch(
        prop_ev_spots, state, format_prop_ev_alert_message, prop_alert_key, "edge", phone_number, "prop EV"
    )
    all_sent.extend(sent)

    if all_sent:
        save_alert_state(state)
    else:
        log.info("scan ok: no new alerts this cycle")

    return len(all_sent)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    load_dotenv()
    run()


if __name__ == "__main__":
    main()
