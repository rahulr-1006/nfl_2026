from datetime import UTC, datetime, timedelta

import pytest

from src.model.baseline import market_baseline
from src.signal.live_scan import (
    AlertRecord,
    find_positive_ev_spots,
    format_alert_message,
    new_or_improved_spots,
    record_alerts,
)
from src.signal.sizing import expected_value
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, OddsSnapshot, Side

CAPTURE_TIME = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)
EVENT_START = datetime(2026, 9, 13, 17, 0, tzinfo=UTC)


def _snapshot(book, side, price_american, capture_time=CAPTURE_TIME) -> OddsSnapshot:
    return OddsSnapshot.from_american(
        capture_time=capture_time,
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


def test_find_positive_ev_spots_flags_a_book_beating_pinnacle_fair(tmp_path):
    store = PointInTimeStore(root=tmp_path / "snapshots")
    store.write(
        [
            _snapshot("pinnacle", Side.HOME, -150),
            _snapshot("pinnacle", Side.AWAY, 130),
            # FanDuel offers a much better home price than Pinnacle's fair value implies.
            _snapshot("fanduel", Side.HOME, 120),
            _snapshot("fanduel", Side.AWAY, -140),
        ]
    )

    spots = find_positive_ev_spots(store, threshold=0.02, as_of=CAPTURE_TIME + timedelta(minutes=1))

    assert len(spots) == 1
    row = spots.iloc[0]
    assert row["book"] == "fanduel"
    assert row["side"] == "home"
    assert row["event_id"] == "2026_01_NE_SEA"

    expected_fair = market_baseline([-150, 130], side_index=0)
    assert row["pinnacle_fair_prob"] == pytest.approx(expected_fair)
    from src.devig.convert import american_to_decimal

    assert row["edge"] == pytest.approx(expected_value(expected_fair, american_to_decimal(120)))
    assert row["edge"] >= 0.02


def test_find_positive_ev_spots_ignores_books_with_no_edge(tmp_path):
    store = PointInTimeStore(root=tmp_path / "snapshots")
    store.write(
        [
            _snapshot("pinnacle", Side.HOME, -150),
            _snapshot("pinnacle", Side.AWAY, 130),
            # BetMGM roughly matches Pinnacle's own price -- no real edge.
            _snapshot("betmgm", Side.HOME, -148),
            _snapshot("betmgm", Side.AWAY, 128),
        ]
    )

    spots = find_positive_ev_spots(store, threshold=0.02, as_of=CAPTURE_TIME + timedelta(minutes=1))
    assert spots.empty


def test_find_positive_ev_spots_ignores_non_execution_books(tmp_path):
    store = PointInTimeStore(root=tmp_path / "snapshots")
    store.write(
        [
            _snapshot("pinnacle", Side.HOME, -150),
            _snapshot("pinnacle", Side.AWAY, 130),
            # A great price, but at a book not in EXECUTION_BOOKS -- must be ignored.
            _snapshot("onexbet", Side.HOME, 200),
            _snapshot("onexbet", Side.AWAY, -250),
        ]
    )

    spots = find_positive_ev_spots(store, threshold=0.02, as_of=CAPTURE_TIME + timedelta(minutes=1))
    assert spots.empty


def test_find_positive_ev_spots_empty_store_returns_empty_frame(tmp_path):
    store = PointInTimeStore(root=tmp_path / "snapshots")
    assert find_positive_ev_spots(store).empty


def test_format_alert_message_names_the_bet_and_book():
    import pandas as pd

    row = pd.Series(
        {
            "event_id": "2026_01_NE_SEA",
            "home_team": "SEA",
            "away_team": "NE",
            "side": "home",
            "book": "fanduel",
            "book_price_american": 120,
            "edge": 0.034,
            "suggested_stake": 2.0,
        }
    )
    message = format_alert_message(row)
    assert "NE @ SEA" in message
    assert "Fanduel" in message
    assert "SEA" in message
    assert "+120" in message
    assert "3.4%" in message


def test_new_or_improved_spots_dedupes_unchanged_and_keeps_improved():
    import pandas as pd

    spots = pd.DataFrame(
        [
            {"event_id": "A", "side": "home", "book": "fanduel", "edge": 0.03},
            {"event_id": "B", "side": "away", "book": "draftkings", "edge": 0.05},
        ]
    )
    now = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)
    state = {
        "A|home|fanduel": AlertRecord(edge=0.029, alerted_at=now),  # unchanged in substance
        "B|away|draftkings": AlertRecord(edge=0.02, alerted_at=now),  # improved by 3pp
    }

    kept = new_or_improved_spots(spots, state, min_edge_increase=0.01)

    assert list(kept["event_id"]) == ["B"]


def test_record_alerts_adds_new_keys_and_preserves_existing():
    import pandas as pd

    now = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)
    existing = {"X|home|fanduel": AlertRecord(edge=0.05, alerted_at=now)}
    new_spots = pd.DataFrame([{"event_id": "A", "side": "home", "book": "fanduel", "edge": 0.03}])

    updated = record_alerts(new_spots, existing, now=now)

    assert "X|home|fanduel" in updated
    assert updated["A|home|fanduel"].edge == pytest.approx(0.03)
