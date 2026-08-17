from datetime import UTC, datetime, timedelta

import pytest

from src.clv.preseason_report import clv_movement_report
from src.devig.convert import american_to_decimal
from src.model.baseline import market_baseline
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, OddsSnapshot, Side

EVENT_START = datetime(2026, 8, 21, 0, 0, tzinfo=UTC)
ENTRY_TIME = datetime(2026, 8, 17, 12, 0, tzinfo=UTC)
CLOSE_TIME = datetime(2026, 8, 20, 12, 0, tzinfo=UTC)


def _moneyline_snapshot(capture_time, side, price_american, book="fanduel") -> OddsSnapshot:
    return OddsSnapshot.from_american(
        capture_time=capture_time,
        event_id="2026_PRE_abc123",
        season=2026,
        week=0,
        home_team="HOU",
        away_team="LV",
        event_start_time=EVENT_START,
        book=book,
        market=Market.MONEYLINE,
        side=side,
        price_american=price_american,
    )


def test_clv_movement_report_computes_price_and_probability_clv(tmp_path):
    store = PointInTimeStore(root=tmp_path / "snapshots_preseason")
    store.write(
        [
            _moneyline_snapshot(ENTRY_TIME, Side.HOME, -180),
            _moneyline_snapshot(ENTRY_TIME, Side.AWAY, 150),
        ]
    )
    store.write(
        [
            _moneyline_snapshot(CLOSE_TIME, Side.HOME, -220),  # home price shortened -- market moved toward home
            _moneyline_snapshot(CLOSE_TIME, Side.AWAY, 180),
        ]
    )

    report = clv_movement_report(store, as_of=CLOSE_TIME + timedelta(hours=1))

    assert len(report) == 1
    row = report.iloc[0]
    assert row["event_id"] == "2026_PRE_abc123"
    assert row["home_team"] == "HOU"
    assert row["n_snapshots"] == 2

    # clv_price(d_entry, d_close) = d_entry/d_close - 1: home shortened from
    # -180 to -220, so the entry price was better (higher decimal odds)
    # than the close -- positive CLV, "beat the close."
    expected_home_price_clv = american_to_decimal(-180) / american_to_decimal(-220) - 1
    assert row["home_price_clv"] == pytest.approx(expected_home_price_clv)
    assert row["home_price_clv"] > 0

    expected_home_prob_entry = market_baseline([-180, 150], side_index=0)
    expected_home_prob_close = market_baseline([-220, 180], side_index=0)
    assert row["home_prob_clv"] == pytest.approx(expected_home_prob_close - expected_home_prob_entry)
    assert row["home_prob_clv"] > 0  # market moved toward home between entry and close


def test_clv_movement_report_skips_events_with_only_one_snapshot(tmp_path):
    store = PointInTimeStore(root=tmp_path / "snapshots_preseason")
    store.write(
        [
            _moneyline_snapshot(ENTRY_TIME, Side.HOME, -180),
            _moneyline_snapshot(ENTRY_TIME, Side.AWAY, 150),
        ]
    )

    report = clv_movement_report(store, as_of=ENTRY_TIME + timedelta(hours=1))

    assert report.empty


def test_clv_movement_report_ignores_non_reference_books(tmp_path):
    store = PointInTimeStore(root=tmp_path / "snapshots_preseason")
    store.write(
        [
            _moneyline_snapshot(ENTRY_TIME, Side.HOME, -180, book="mybookieag"),
            _moneyline_snapshot(ENTRY_TIME, Side.AWAY, 150, book="mybookieag"),
            _moneyline_snapshot(CLOSE_TIME, Side.HOME, -220, book="mybookieag"),
            _moneyline_snapshot(CLOSE_TIME, Side.AWAY, 180, book="mybookieag"),
        ]
    )

    report = clv_movement_report(store, book="fanduel", as_of=CLOSE_TIME + timedelta(hours=1))

    assert report.empty  # only mybookieag data exists; fanduel-filtered report has nothing


def test_clv_movement_report_returns_empty_frame_for_empty_store(tmp_path):
    store = PointInTimeStore(root=tmp_path / "snapshots_preseason")
    report = clv_movement_report(store)
    assert report.empty
