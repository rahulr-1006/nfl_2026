from datetime import UTC, datetime, timedelta

from src.backtest import middle_scan
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, OddsSnapshot, Side

# middle_scan.run() scans "as of now" (find_middle_opportunities defaults
# as_of to datetime.now(UTC)), so fixture snapshots must sit in the real
# past -- same discipline as test_monitor_run.py, for the same reason
# (PointInTimeStore's leakage filter would otherwise silently exclude a
# hardcoded future capture_time).
NOW = datetime.now(UTC)
EARLY = NOW - timedelta(days=3)
LATE = NOW - timedelta(hours=1)
EVENT_START = NOW + timedelta(days=2)


def _snapshot(book, side, price_american, line, capture_time) -> OddsSnapshot:
    return OddsSnapshot.from_american(
        capture_time=capture_time,
        event_id="2026_01_NE_SEA",
        season=2026,
        week=1,
        home_team="SEA",
        away_team="NE",
        event_start_time=EVENT_START,
        book=book,
        market=Market.SPREAD,
        side=side,
        price_american=price_american,
        line=line,
    )


def _seed_store_with_real_movement(root):
    store = PointInTimeStore(root=root)
    store.write(
        [
            _snapshot("pinnacle", Side.HOME, -150, -5.0, LATE),
            _snapshot("pinnacle", Side.AWAY, 130, 5.0, LATE),
            _snapshot("fanduel", Side.HOME, -110, -3.0, EARLY),
            _snapshot("draftkings", Side.AWAY, -105, 7.0, LATE),
        ]
    )
    return store


def test_run_finds_and_logs_a_real_middle(tmp_path, monkeypatch, caplog):
    store_root = tmp_path / "snapshots"
    _seed_store_with_real_movement(store_root)
    # Skip the real 2015-2024 model fit -- this test is about the
    # scan/report/log wiring, not re-validating the margin/total model
    # (that's `tests/test_margin_total.py`'s job). Fixed, hand-chosen
    # sigmas keep this test fast and hermetic.
    monkeypatch.setattr(middle_scan, "fit_residual_stds", lambda: (13.0, 10.0))

    import logging

    with caplog.at_level(logging.INFO, logger="src.backtest.middle_scan"):
        report = middle_scan.run(store_root=str(store_root))

    assert len(report) == 1
    assert report.iloc[0]["event_id"] == "2026_01_NE_SEA"
    assert any("2026_01_NE_SEA" in record.message for record in caplog.records)


def test_run_returns_empty_when_nothing_moved(tmp_path, monkeypatch):
    store_root = tmp_path / "snapshots"
    store = PointInTimeStore(root=store_root)
    store.write(
        [
            _snapshot("pinnacle", Side.HOME, -150, -3.0, EARLY),
            _snapshot("pinnacle", Side.AWAY, 130, 3.0, EARLY),
            _snapshot("fanduel", Side.HOME, -110, -3.0, LATE),
            _snapshot("draftkings", Side.AWAY, -105, 3.0, LATE),
        ]
    )
    monkeypatch.setattr(middle_scan, "fit_residual_stds", lambda: (13.0, 10.0))

    report = middle_scan.run(store_root=str(store_root))
    assert report.empty


def test_run_filters_out_windows_below_min_ev(tmp_path, monkeypatch):
    store_root = tmp_path / "snapshots"
    _seed_store_with_real_movement(store_root)
    monkeypatch.setattr(middle_scan, "fit_residual_stds", lambda: (13.0, 10.0))

    unfiltered = middle_scan.run(store_root=str(store_root), min_ev=0.0)
    assert not unfiltered.empty
    real_ev = unfiltered.iloc[0]["ev"]

    filtered = middle_scan.run(store_root=str(store_root), min_ev=real_ev + 1.0)
    assert filtered.empty


def test_run_never_calls_any_notification_path(tmp_path, monkeypatch):
    # This is a deliberately silent, print/log-only tool (see module
    # docstring) -- assert it doesn't import or touch the SMS path at all,
    # so a future edit can't accidentally wire it to unattended alerts
    # before this strategy has any live track record.
    import src.notify.sms as sms_module

    calls = []
    monkeypatch.setattr(sms_module, "send_message", lambda *a, **kw: calls.append((a, kw)))
    monkeypatch.setattr(middle_scan, "fit_residual_stds", lambda: (13.0, 10.0))

    store_root = tmp_path / "snapshots"
    _seed_store_with_real_movement(store_root)
    middle_scan.run(store_root=str(store_root))

    assert calls == []
