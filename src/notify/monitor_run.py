"""Live +EV monitor entrypoint: `python -m src.notify.monitor_run`.

Meant to be invoked repeatedly by launchd's StartInterval
(ops/com.nflclv.monitor.plist), not run as a long-lived process -- each
invocation reads the current point-in-time store, scans for new/improved
+EV spots (src/signal/live_scan.py), texts about them, and exits. Cheap:
no network calls of its own, just local parquet reads, so it can run far
more often than the collector without touching the Odds API credit
budget at all.
"""

from __future__ import annotations

import logging
import os

import pandas as pd
from dotenv import load_dotenv

from src.notify.sms import SmsError, send_message
from src.signal.live_scan import (
    DEFAULT_EDGE_THRESHOLD,
    find_positive_ev_spots,
    format_alert_message,
    load_alert_state,
    new_or_improved_spots,
    record_alerts,
    save_alert_state,
)
from src.store.pit_store import PointInTimeStore

log = logging.getLogger(__name__)


def run(store_root: str = "data/snapshots", threshold: float = DEFAULT_EDGE_THRESHOLD) -> int:
    """One scan-and-alert cycle. Returns the number of alerts actually
    sent. Never raises for expected failure modes (no phone number
    configured, a single SMS send failing) -- this runs unattended and a
    single bad tick must not stop the next one.
    """
    phone_number = os.environ.get("ALERT_PHONE_NUMBER")
    if not phone_number:
        log.warning("ALERT_PHONE_NUMBER not set in .env -- scanning but not sending any alerts")

    store = PointInTimeStore(root=store_root)
    spots = find_positive_ev_spots(store, threshold=threshold)
    if spots.empty:
        log.info("scan ok: no +EV spots >= %.1f%% threshold", threshold * 100)
        return 0

    state = load_alert_state()
    to_alert = new_or_improved_spots(spots, state)
    if to_alert.empty:
        log.info("scan ok: %d spot(s) found, none new/improved since last alert", len(spots))
        return 0

    sent_rows = []
    for _, row in to_alert.iterrows():
        message = format_alert_message(row)
        if not phone_number:
            log.info("would alert (no phone configured): %s", message)
            continue
        try:
            send_message(message, phone_number)
            sent_rows.append(row)
            log.info("sent alert: %s", message)
        except SmsError as exc:
            log.error("failed to send alert for %s: %s", row["event_id"], exc)

    # Only spots that actually reached the phone get marked alerted -- an
    # unconfigured number or a failed send must not silently suppress
    # future attempts at the same spot.
    if sent_rows:
        state = record_alerts(pd.DataFrame(sent_rows), state)
        save_alert_state(state)

    return len(sent_rows)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    load_dotenv()
    run()


if __name__ == "__main__":
    main()
