from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from src.notify import monitor_run
from src.notify.sms import SmsError
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, OddsSnapshot, Side

# monitor_run.run() scans "as of now" with no injectable decision_time, so
# fixture snapshots must sit safely in the real past -- a hardcoded future
# calendar date would be silently excluded by PointInTimeStore's own
# leakage filter (capture_time <= decision_time).
CAPTURE_TIME = datetime.now(UTC) - timedelta(hours=1)
EVENT_START = CAPTURE_TIME + timedelta(days=3)


def _snapshot(book, side, price_american) -> OddsSnapshot:
    return OddsSnapshot.from_american(
        capture_time=CAPTURE_TIME,
        event_id="2026_01_NE_SEA",
        season=2026,
        week=1,
        home_team="SEA",
        away_team="NE",
        event_start_time=EVENT_START,
        book=book,
        market=Market.MONEYLINE,
        side=side,
        price_american=price_american,
    )


def _seed_store(root):
    store = PointInTimeStore(root=root)
    store.write(
        [
            _snapshot("pinnacle", Side.HOME, -150),
            _snapshot("pinnacle", Side.AWAY, 130),
            _snapshot("fanduel", Side.HOME, 120),
            _snapshot("fanduel", Side.AWAY, -140),
        ]
    )
    return store


def test_run_sends_and_records_alert_when_phone_configured(tmp_path, monkeypatch):
    store_root = tmp_path / "snapshots"
    _seed_store(store_root)
    monkeypatch.setenv("ALERT_PHONE_NUMBER", "+15551234567")
    monkeypatch.setattr(monitor_run, "load_alert_state", dict)
    saved = {}
    monkeypatch.setattr(monitor_run, "save_alert_state", lambda state: saved.update(state))

    with patch("src.notify.monitor_run.send_message") as mock_send:
        sent = monitor_run.run(store_root=str(store_root))

    assert sent == 1
    mock_send.assert_called_once()
    assert "2026_01_NE_SEA|home|fanduel" in saved


def test_run_does_not_send_or_record_when_phone_not_configured(tmp_path, monkeypatch):
    store_root = tmp_path / "snapshots"
    _seed_store(store_root)
    monkeypatch.delenv("ALERT_PHONE_NUMBER", raising=False)
    monkeypatch.setattr(monitor_run, "load_alert_state", dict)
    save_called = []
    monkeypatch.setattr(monitor_run, "save_alert_state", lambda state: save_called.append(state))

    with patch("src.notify.monitor_run.send_message") as mock_send:
        sent = monitor_run.run(store_root=str(store_root))

    assert sent == 0
    mock_send.assert_not_called()
    assert save_called == []  # nothing was actually communicated, so nothing should be marked alerted


def test_run_does_not_record_a_spot_whose_send_failed(tmp_path, monkeypatch):
    store_root = tmp_path / "snapshots"
    _seed_store(store_root)
    monkeypatch.setenv("ALERT_PHONE_NUMBER", "+15551234567")
    monkeypatch.setattr(monitor_run, "load_alert_state", dict)
    save_called = []
    monkeypatch.setattr(monitor_run, "save_alert_state", lambda state: save_called.append(state))

    with patch("src.notify.monitor_run.send_message", side_effect=SmsError("boom")):
        sent = monitor_run.run(store_root=str(store_root))  # must not raise

    assert sent == 0
    assert save_called == []


def test_run_returns_zero_when_no_spots_found(tmp_path, monkeypatch):
    store_root = tmp_path / "snapshots"
    store = PointInTimeStore(root=store_root)
    store.write([_snapshot("pinnacle", Side.HOME, -150), _snapshot("pinnacle", Side.AWAY, 130)])
    monkeypatch.setenv("ALERT_PHONE_NUMBER", "+15551234567")

    with patch("src.notify.monitor_run.send_message") as mock_send:
        sent = monitor_run.run(store_root=str(store_root))

    assert sent == 0
    mock_send.assert_not_called()
