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
        sent = monitor_run.run(store_root=str(store_root), shadow_path=tmp_path / "shadow.jsonl")

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
        sent = monitor_run.run(store_root=str(store_root), shadow_path=tmp_path / "shadow.jsonl")

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
        sent = monitor_run.run(store_root=str(store_root), shadow_path=tmp_path / "shadow.jsonl")  # must not raise

    assert sent == 0
    assert save_called == []


def test_run_returns_zero_when_no_spots_found(tmp_path, monkeypatch):
    store_root = tmp_path / "snapshots"
    store = PointInTimeStore(root=store_root)
    store.write([_snapshot("pinnacle", Side.HOME, -150), _snapshot("pinnacle", Side.AWAY, 130)])
    monkeypatch.setenv("ALERT_PHONE_NUMBER", "+15551234567")

    with patch("src.notify.monitor_run.send_message") as mock_send:
        sent = monitor_run.run(store_root=str(store_root), shadow_path=tmp_path / "shadow.jsonl")

    assert sent == 0
    mock_send.assert_not_called()


def test_run_writes_shadow_rows_to_the_given_path_not_the_real_log(tmp_path, monkeypatch):
    """The suite used to append fixture alerts to the REAL `data/shadow_log.jsonl`.

    `_alert_batch` called `record_alert` with its default path, so every run of
    these tests wrote a synthetic +120 FanDuel alert into the live CLV record.
    It went unnoticed because the moneyline shadow write was *also* crashing on
    a column-name mismatch and the failure was swallowed -- fixing that bug is
    what turned a silent no-op into silent corruption of the measurement log.
    """
    from src.signal import shadow_log

    store_root = tmp_path / "snapshots"
    _seed_store(store_root)
    shadow_path = tmp_path / "shadow.jsonl"
    monkeypatch.setenv("ALERT_PHONE_NUMBER", "+15551234567")
    monkeypatch.setattr(monitor_run, "load_alert_state", dict)
    monkeypatch.setattr(monitor_run, "save_alert_state", lambda state: None)

    with patch("src.notify.monitor_run.send_message"):
        monitor_run.run(store_root=str(store_root), shadow_path=shadow_path)

    assert shadow_path.exists(), "the alert must be shadow-logged somewhere"
    assert [o.strategy for o in shadow_log.load(shadow_path)] == ["moneyline_ev"]
    assert shadow_log.SHADOW_LOG_PATH != shadow_path, "fixture must not point at the real log"


# --- line-movement signals wired in (2026-09-08) ------------------------------
#
# Middling and steam existed as working hand-run scripts (`middle_scan.py`,
# `steam_scan.py`) but nothing invoked them between runs, so the one class of
# signal that is worthless after the fact was the one nothing watched for.


def test_run_scans_middling_and_steam(tmp_path, monkeypatch):
    store_root = tmp_path / "snapshots"
    _seed_store(store_root)
    monkeypatch.setattr(monitor_run, "load_alert_state", dict)
    monkeypatch.setattr(monitor_run, "save_alert_state", lambda state: None)
    monkeypatch.setattr(monitor_run, "cached_residual_stds", lambda: (13.0, 10.0))

    called = []
    monkeypatch.setattr(
        monitor_run, "find_live_middle_spots",
        lambda *a, **k: called.append("middle") or __import__("pandas").DataFrame(),
    )
    monkeypatch.setattr(
        monitor_run, "find_live_steam_spots",
        lambda *a, **k: called.append("steam") or __import__("pandas").DataFrame(),
    )

    monitor_run.run(store_root=str(store_root), shadow_path=tmp_path / "shadow.jsonl")
    assert called == ["middle", "steam"]


def test_a_failing_sigma_fit_does_not_stop_the_other_signals(tmp_path, monkeypatch):
    """The residual-sigma fit reads training parquet files that the arb and
    moneyline scans have nothing to do with. A missing or corrupt one must cost
    only middling and steam, not the whole tick.
    """
    store_root = tmp_path / "snapshots"
    _seed_store(store_root)
    monkeypatch.setenv("ALERT_PHONE_NUMBER", "+15551234567")
    monkeypatch.setattr(monitor_run, "load_alert_state", dict)
    monkeypatch.setattr(monitor_run, "save_alert_state", lambda state: None)

    def _boom():
        raise FileNotFoundError("pbp_2015_2025.parquet")

    monkeypatch.setattr(monitor_run, "cached_residual_stds", _boom)

    with patch.object(monitor_run, "send_message") as send:
        sent = monitor_run.run(store_root=str(store_root), shadow_path=tmp_path / "shadow.jsonl")

    # The moneyline spot in the shared fixture still alerts.
    assert sent == 1
    assert send.call_count == 1


def test_a_failing_movement_scan_does_not_stop_the_other_signals(tmp_path, monkeypatch):
    store_root = tmp_path / "snapshots"
    _seed_store(store_root)
    monkeypatch.setenv("ALERT_PHONE_NUMBER", "+15551234567")
    monkeypatch.setattr(monitor_run, "load_alert_state", dict)
    monkeypatch.setattr(monitor_run, "save_alert_state", lambda state: None)
    monkeypatch.setattr(monitor_run, "cached_residual_stds", lambda: (13.0, 10.0))

    def _boom(*a, **k):
        raise ValueError("malformed movement frame")

    monkeypatch.setattr(monitor_run, "find_live_middle_spots", _boom)
    monkeypatch.setattr(monitor_run, "find_live_steam_spots", _boom)

    with patch.object(monitor_run, "send_message"):
        assert monitor_run.run(store_root=str(store_root), shadow_path=tmp_path / "shadow.jsonl") == 1


def test_middle_alerts_charge_the_exposure_cap_both_legs(tmp_path, monkeypatch):
    """A middle risks two stakes, not one. Charging the shared bankroll cap a
    single default stake would let middles quietly double the exposure the cap
    exists to bound.
    """
    import pandas as pd

    store_root = tmp_path / "snapshots"
    _seed_store(store_root)
    monkeypatch.setenv("ALERT_PHONE_NUMBER", "+15551234567")
    monkeypatch.setattr(monitor_run, "load_alert_state", dict)
    monkeypatch.setattr(monitor_run, "save_alert_state", lambda state: None)
    monkeypatch.setattr(monitor_run, "cached_residual_stds", lambda: (13.0, 10.0))
    monkeypatch.setattr(monitor_run, "find_live_steam_spots", lambda *a, **k: pd.DataFrame())

    middles = pd.DataFrame([
        {
            "event_id": f"2026_01_GAME{i}", "market": "spread",
            "book_a": "fanduel", "side_a": "home", "line_a": -3.0, "price_decimal_a": 1.91,
            "book_b": "draftkings", "side_b": "away", "line_b": 7.0, "price_decimal_b": 1.95,
            "window_lo": 3.0, "window_hi": 7.0, "p_both_win": 0.12, "ev": 0.2,
            "total_risked": 8.0, "ev_rate": 0.05, "home_team": "SEA", "away_team": "NE",
        }
        for i in range(5)
    ])
    monkeypatch.setattr(monitor_run, "find_live_middle_spots", lambda *a, **k: middles)

    with patch.object(monitor_run, "send_message"):
        monitor_run.run(
            store_root=str(store_root), shadow_path=tmp_path / "shadow.jsonl", max_exposure=20.0,
        )

    # $20 cap, $2 already charged to the moneyline alert, $8 risked per middle
    # -> 2 middles fit, not 5 and not (20/2)=10.
    from src.signal.shadow_log import load

    middle_keys = {r.alert_key for r in load(tmp_path / "shadow.jsonl") if r.strategy == "middle"}
    assert len(middle_keys) == 2
