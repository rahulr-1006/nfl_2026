"""The Pinnacle-arrival announcement must fire exactly once, ever."""
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from src.notify import monitor_run
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, OddsSnapshot, Side

NOW = datetime.now(UTC)
KICKOFF = NOW + timedelta(days=10)


def _prop(book, side=Side.OVER, price=-110):
    return OddsSnapshot.from_american(
        capture_time=NOW - timedelta(minutes=5), event_id="2026_01_KC_LAC", season=2026, week=1,
        home_team="LAC", away_team="KC", event_start_time=KICKOFF, book=book,
        market=Market.PLAYER_PROP, side=side, price_american=price, line=45.5,
        player_name="Star Receiver", prop_stat="receiving_yards",
    )


@pytest.fixture
def isolated_state(monkeypatch):
    """Swap the shared alert state for an in-memory dict.

    Necessary because `monitor_run` persists to a real file at
    `data/alert_state.json`; without this a test would read, and clobber, the
    live monitor's dedup state.
    """
    store: dict = {}
    monkeypatch.setattr(monitor_run, "load_alert_state", lambda: dict(store))
    monkeypatch.setattr(monitor_run, "save_alert_state", lambda st: store.update(st))
    return store


def test_arrival_fires_once_then_never_again(tmp_path, isolated_state, monkeypatch):
    store_root = tmp_path / "snaps"
    store = PointInTimeStore(root=store_root)
    store.write([_prop("pinnacle"), _prop("pinnacle", Side.UNDER, -110)])
    monkeypatch.setenv("ALERT_PHONE_NUMBER", "+15550000000")

    sent = []
    with patch.object(monitor_run, "send_message", side_effect=lambda m, p: sent.append(m)):
        monitor_run.run(store_root=str(store_root))
        first = [m for m in sent if "PINNACLE NOW QUOTING" in m]
        monitor_run.run(store_root=str(store_root))
        monitor_run.run(store_root=str(store_root))
        again = [m for m in sent if "PINNACLE NOW QUOTING" in m]

    assert len(first) == 1, "should announce on the tick Pinnacle first appears"
    assert len(again) == 1, "a persistent condition must not re-text every tick"


def test_no_arrival_alert_while_pinnacle_is_absent(tmp_path, isolated_state, monkeypatch):
    store_root = tmp_path / "snaps2"
    store = PointInTimeStore(root=store_root)
    store.write([_prop("fanduel"), _prop("betrivers")])   # today's real state
    monkeypatch.setenv("ALERT_PHONE_NUMBER", "+15550000000")

    sent = []
    with patch.object(monitor_run, "send_message", side_effect=lambda m, p: sent.append(m)):
        monitor_run.run(store_root=str(store_root))

    assert not [m for m in sent if "PINNACLE" in m]
