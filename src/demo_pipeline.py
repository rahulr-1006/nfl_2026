"""End-to-end pipeline demo: pull -> store -> compare -> decide -> notify.

`make demo` walks the whole live architecture in one run, on made-up odds
(no API call, no credits spent) -- proof that the pieces actually fit
together, not a claim about real market data. Every step after the first
calls the exact same production code the real collector/monitor use:

  1. PULL       synthetic OddsSnapshot rows (Pinnacle + FanDuel), the only
                fake part -- stands in for what src/collect/run.py or
                src/collect/props.py would hand back from a real poll.
  2. STORE      src/store/pit_store.py::PointInTimeStore.write() -- the
                real append-only store code, just pointed at a throwaway
                demo root (data/demo_snapshots/, gitignored) instead of
                data/snapshots/, so this can never touch real season data.
  3. COMPARE    src/signal/live_scan.py::find_positive_ev_spots() -- devigs
                Pinnacle's price into a fair probability and checks it
                against FanDuel's price for real edge. This *is* "the
                backtester" in the sense that matters here: the same
                market_baseline() fair-value anchor src/backtest/engine.py
                uses for historical replay is what this live comparison
                runs against too. (The batch historical backtester itself
                replays *settled* games from the point-in-time store and
                doesn't fit a single-decision live demo -- see
                tests/test_backtest_engine.py for that one, already
                exercised on synthetic fixtures.)
  4. DECIDE     src/signal/live_scan.py::format_alert_message() -- turns a
                qualifying spot into the same message text a real alert
                would carry.
  5. NOTIFY     src/notify/sms.py::send_message() -- sends a REAL text to
                ALERT_PHONE_NUMBER (from .env), clearly labeled as a demo.
                Skips sending (prints instead) if that's not configured.

**To tweak:** edit the constants right below the imports -- the fake
prices, which side is mispriced, the EV threshold -- and re-run. Nothing
else in the file needs to change for a different demo scenario.

**Reproducible:** the demo store is wiped and rebuilt every run, and this
script talks to src/signal/live_scan.py's functions directly rather than
through the dedup-state layer (data/alert_state.json) monitor_run.py uses
-- a real alert only fires once per new/improved spot, but this is a demo,
so it fires every time you run it.
"""

from __future__ import annotations

import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

from src.notify.sms import SmsError, send_message
from src.signal.live_scan import find_positive_ev_spots, format_alert_message
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, OddsSnapshot, Side

# --- tweak these ---
DEMO_STORE_ROOT = Path("data/demo_snapshots")
DEMO_EVENT_ID = "2026_DEMO_SEA_NE"
DEMO_HOME_TEAM, DEMO_AWAY_TEAM = "SEA", "NE"
PINNACLE_HOME_PRICE, PINNACLE_AWAY_PRICE = -150, 130  # the "sharp" fair-value anchor
EXECUTION_BOOK = "fanduel"
EXECUTION_HOME_PRICE, EXECUTION_AWAY_PRICE = 120, -140  # deliberately much better on home than Pinnacle implies
EV_THRESHOLD = 0.02  # 2%, matches src/signal/live_scan.py's production default
# ---


def _step(n: int, title: str) -> None:
    print(f"\n[{n}/5] {title}")
    print("-" * 60)


def make_synthetic_snapshots(capture_time: datetime) -> list[OddsSnapshot]:
    event_start = capture_time.replace(hour=23, minute=59)
    return [
        OddsSnapshot.from_american(
            capture_time=capture_time,
            event_id=DEMO_EVENT_ID,
            season=2026,
            week=0,
            home_team=DEMO_HOME_TEAM,
            away_team=DEMO_AWAY_TEAM,
            event_start_time=event_start,
            book="pinnacle",
            market=Market.MONEYLINE,
            side=Side.HOME,
            price_american=PINNACLE_HOME_PRICE,
        ),
        OddsSnapshot.from_american(
            capture_time=capture_time,
            event_id=DEMO_EVENT_ID,
            season=2026,
            week=0,
            home_team=DEMO_HOME_TEAM,
            away_team=DEMO_AWAY_TEAM,
            event_start_time=event_start,
            book="pinnacle",
            market=Market.MONEYLINE,
            side=Side.AWAY,
            price_american=PINNACLE_AWAY_PRICE,
        ),
        OddsSnapshot.from_american(
            capture_time=capture_time,
            event_id=DEMO_EVENT_ID,
            season=2026,
            week=0,
            home_team=DEMO_HOME_TEAM,
            away_team=DEMO_AWAY_TEAM,
            event_start_time=event_start,
            book=EXECUTION_BOOK,
            market=Market.MONEYLINE,
            side=Side.HOME,
            price_american=EXECUTION_HOME_PRICE,
        ),
        OddsSnapshot.from_american(
            capture_time=capture_time,
            event_id=DEMO_EVENT_ID,
            season=2026,
            week=0,
            home_team=DEMO_HOME_TEAM,
            away_team=DEMO_AWAY_TEAM,
            event_start_time=event_start,
            book=EXECUTION_BOOK,
            market=Market.MONEYLINE,
            side=Side.AWAY,
            price_american=EXECUTION_AWAY_PRICE,
        ),
    ]


def main() -> None:
    load_dotenv()
    now = datetime.now(UTC)

    _step(1, "PULL (synthetic) -- standing in for a real collector poll")
    snapshots = make_synthetic_snapshots(now)
    for s in snapshots:
        print(f"  {s.book:10s} {s.side.value:5s} {s.price_american:+d}")

    _step(2, "STORE -- src/store/pit_store.py::PointInTimeStore.write()")
    if DEMO_STORE_ROOT.exists():
        shutil.rmtree(DEMO_STORE_ROOT)  # fresh store every run -- reproducible, no stale demo data
    store = PointInTimeStore(root=DEMO_STORE_ROOT)
    path = store.write(snapshots)
    print(f"  wrote {len(snapshots)} snapshots -> {path}")

    _step(3, "COMPARE -- src/signal/live_scan.py::find_positive_ev_spots()")
    print(f"  devigging Pinnacle's price into a fair probability, checking {EXECUTION_BOOK}'s price against it")
    spots = find_positive_ev_spots(store, threshold=EV_THRESHOLD, books=(EXECUTION_BOOK,), as_of=now)
    if spots.empty:
        print(f"  no spot cleared the {EV_THRESHOLD:.0%} threshold -- tweak the prices above and re-run")
        return
    print(f"  found {len(spots)} spot(s) clearing {EV_THRESHOLD:.0%} EV:")
    print(spots[["side", "book", "pinnacle_fair_prob", "book_price_american", "edge", "suggested_stake"]].to_string(index=False))

    _step(4, "DECIDE -- src/signal/live_scan.py::format_alert_message()")
    top = spots.iloc[0]
    message = format_alert_message(top)
    print(f'  "{message}"')

    _step(5, "NOTIFY -- src/notify/sms.py::send_message()")
    phone_number = os.environ.get("ALERT_PHONE_NUMBER")
    demo_message = f"[DEMO] {message}"
    if not phone_number:
        print("  ALERT_PHONE_NUMBER not set in .env -- would send, but printing instead:")
        print(f"  {demo_message}")
        return
    try:
        send_message(demo_message, phone_number)
        print(f"  sent to {phone_number}")
    except SmsError as exc:
        print(f"  send failed: {exc}")


if __name__ == "__main__":
    main()
