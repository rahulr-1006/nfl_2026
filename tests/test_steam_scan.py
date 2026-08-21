from datetime import UTC, datetime, timedelta

from src.backtest import steam_scan
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, OddsSnapshot, Side

# steam_scan.run() scans "as of now" (find_steam_opportunities defaults
# as_of to datetime.now(UTC)), so fixture snapshots must sit in the real
# past -- same discipline as test_middle_scan.py, for the same reason.
NOW = datetime.now(UTC)
OLD = NOW - timedelta(hours=2)
NEW = NOW - timedelta(hours=1)
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


def _seed_store_with_real_steam(root):
    store = PointInTimeStore(root=root)
    store.write(
        [
            _snapshot("fanduel", Side.HOME, -110, -3.0, OLD),
            _snapshot("fanduel", Side.HOME, -105, -5.0, NEW),
            _snapshot("draftkings", Side.HOME, -110, -3.0, OLD),
            _snapshot("draftkings", Side.HOME, -105, -5.0, NEW + timedelta(minutes=5)),
            _snapshot("betmgm", Side.HOME, -110, -3.0, OLD),
            _snapshot("betmgm", Side.HOME, -105, -5.0, NEW + timedelta(minutes=10)),
            _snapshot("betrivers", Side.HOME, -110, -3.0, OLD),  # stale -- hasn't joined
            _snapshot("pinnacle", Side.HOME, -220, -6.0, NEW),
            _snapshot("pinnacle", Side.AWAY, 180, 6.0, NEW),
        ]
    )
    return store


def test_run_finds_and_logs_a_real_steam_move(tmp_path, monkeypatch, caplog):
    store_root = tmp_path / "snapshots"
    _seed_store_with_real_steam(store_root)
    monkeypatch.setattr(steam_scan, "fit_residual_stds", lambda: (13.0, 10.0))

    import logging

    with caplog.at_level(logging.INFO, logger="src.backtest.steam_scan"):
        report = steam_scan.run(store_root=str(store_root))

    assert len(report) == 1
    assert report.iloc[0]["stale_book"] == "betrivers"
    assert any("2026_01_NE_SEA" in record.message for record in caplog.records)


def test_run_returns_empty_when_nothing_moves(tmp_path, monkeypatch):
    store_root = tmp_path / "snapshots"
    store = PointInTimeStore(root=store_root)
    store.write(
        [
            _snapshot("fanduel", Side.HOME, -110, -3.0, OLD),
            _snapshot("draftkings", Side.HOME, -110, -3.0, OLD),
            _snapshot("pinnacle", Side.HOME, -110, -3.0, OLD),
            _snapshot("pinnacle", Side.AWAY, -110, 3.0, OLD),
        ]
    )
    monkeypatch.setattr(steam_scan, "fit_residual_stds", lambda: (13.0, 10.0))

    report = steam_scan.run(store_root=str(store_root))
    assert report.empty


def test_run_filters_out_spots_below_min_ev(tmp_path, monkeypatch):
    store_root = tmp_path / "snapshots"
    _seed_store_with_real_steam(store_root)
    monkeypatch.setattr(steam_scan, "fit_residual_stds", lambda: (13.0, 10.0))

    unfiltered = steam_scan.run(store_root=str(store_root), min_ev=0.0)
    assert not unfiltered.empty
    real_edge = unfiltered.iloc[0]["edge"]

    filtered = steam_scan.run(store_root=str(store_root), min_ev=real_edge + 1.0)
    assert filtered.empty


def test_run_never_calls_any_notification_path(tmp_path, monkeypatch):
    # Deliberately silent, print/log-only tool -- same discipline as
    # middle_scan.py, no live track record yet to trust with an unattended
    # alert channel.
    import src.notify.sms as sms_module

    calls = []
    monkeypatch.setattr(sms_module, "send_message", lambda *a, **kw: calls.append((a, kw)))
    monkeypatch.setattr(steam_scan, "fit_residual_stds", lambda: (13.0, 10.0))

    store_root = tmp_path / "snapshots"
    _seed_store_with_real_steam(store_root)
    steam_scan.run(store_root=str(store_root))

    assert calls == []
