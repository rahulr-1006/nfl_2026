"""Live-alerting adapters for middling and steam (`src/signal/movement_scan.py`).

The behaviour these pin is the difference between a hand-run script and an
unattended texter: a finished-game filter, an EV floor, and stable dedup keys.
"""

from datetime import UTC, datetime, timedelta

import pandas as pd

from src.signal.movement_scan import (
    find_live_middle_spots,
    find_live_steam_spots,
    format_middle_alert_message,
    format_steam_alert_message,
    middle_alert_key,
    steam_alert_key,
)
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, OddsSnapshot, Side

NOW = datetime.now(UTC)
EARLY = NOW - timedelta(days=3)
LATE = NOW - timedelta(hours=1)

SIGMAS = {"sigma_margin": 13.0, "sigma_total": 10.0}


def _snapshot(book, side, price_american, line, capture_time, event_start, event_id="2026_01_NE_SEA"):
    return OddsSnapshot.from_american(
        capture_time=capture_time,
        event_id=event_id,
        season=2026,
        week=1,
        home_team="SEA",
        away_team="NE",
        event_start_time=event_start,
        book=book,
        market=Market.SPREAD,
        side=side,
        price_american=price_american,
        line=line,
    )


def _seed(root, event_start, event_id="2026_01_NE_SEA"):
    store = PointInTimeStore(root=root)
    store.write([
        _snapshot("pinnacle", Side.HOME, -150, -5.0, LATE, event_start, event_id),
        _snapshot("pinnacle", Side.AWAY, 130, 5.0, LATE, event_start, event_id),
        # FanDuel still quotes home -3.0 in the latest poll (see
        # tests/test_middling.py's leg-freshness tests for why both rows exist).
        _snapshot("fanduel", Side.HOME, -110, -3.0, EARLY, event_start, event_id),
        _snapshot("fanduel", Side.HOME, -110, -3.0, LATE, event_start, event_id),
        _snapshot("draftkings", Side.AWAY, -105, 7.0, LATE, event_start, event_id),
    ])
    return store


# --- the finished-game filter ------------------------------------------------


def test_middle_finds_an_upcoming_game():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        store = _seed(tmp, event_start=NOW + timedelta(days=2))
        spots = find_live_middle_spots(store, threshold=0.0, **SIGMAS)
    assert len(spots) == 1
    assert spots.iloc[0]["event_id"] == "2026_01_NE_SEA"


def test_middle_drops_a_game_that_already_kicked_off():
    """The backtest scanner happily reports finished games -- it was built for
    historical replay. Alerting on one is the 874-of-879 bug from the props dry
    run, and middling was one `upcoming_only` call away from repeating it.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        store = _seed(tmp, event_start=NOW - timedelta(minutes=30))
        spots = find_live_middle_spots(store, threshold=0.0, **SIGMAS)
    assert spots.empty


def test_steam_drops_a_game_that_already_kicked_off():
    import tempfile

    from src.backtest.steam import find_steam_opportunities

    with tempfile.TemporaryDirectory() as tmp:
        store = _seed(tmp, event_start=NOW - timedelta(minutes=30))
        # Whatever the underlying scanner reports, none of it may survive the
        # live filter once the game has started.
        raw = find_steam_opportunities(store, **SIGMAS)
        live = find_live_steam_spots(store, threshold=0.0, **SIGMAS)
    assert live.empty
    assert raw.empty or not live.equals(raw)


# --- the EV floor ------------------------------------------------------------


def test_middle_threshold_filters_on_ev_per_dollar_not_dollars():
    """`ev` is dollars on `total_risked`; a threshold applied to it directly
    would mean something different from every other `edge` the monitor handles.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        store = _seed(tmp, event_start=NOW + timedelta(days=2))
        spots = find_live_middle_spots(store, threshold=0.0, **SIGMAS)
        assert "ev_rate" in spots.columns
        expected = spots.iloc[0]["ev"] / spots.iloc[0]["total_risked"]
        assert spots.iloc[0]["ev_rate"] == expected

        above = find_live_middle_spots(store, threshold=expected - 1e-9, **SIGMAS)
        below = find_live_middle_spots(store, threshold=expected + 1e-3, **SIGMAS)
    assert len(above) == 1
    assert below.empty


def test_empty_store_returns_empty_not_a_crash():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        store = PointInTimeStore(root=tmp)
        assert find_live_middle_spots(store, threshold=0.0, **SIGMAS).empty
        assert find_live_steam_spots(store, threshold=0.0, **SIGMAS).empty


# --- dedup keys --------------------------------------------------------------


def _middle_row(**overrides):
    row = {
        "event_id": "2026_01_NE_SEA", "market": "spread",
        "book_a": "fanduel", "side_a": "home", "line_a": -3.0, "price_decimal_a": 1.91,
        "book_b": "draftkings", "side_b": "away", "line_b": 7.0, "price_decimal_b": 1.95,
        "window_lo": 3.0, "window_hi": 7.0, "p_both_win": 0.12, "ev": 0.2,
        "total_risked": 4.0, "ev_rate": 0.05, "home_team": "SEA", "away_team": "NE",
    }
    row.update(overrides)
    return pd.Series(row)


def _steam_row(**overrides):
    row = {
        "event_id": "2026_01_NE_SEA", "market": "total", "side": "over",
        "stale_book": "fanduel", "stale_line": 44.5, "price_decimal": 1.91,
        "n_books_moved": 6, "steam_direction": 1.0, "mu": 46.5, "edge": 0.03,
        "suggested_stake": 1.25, "home_team": "SEA", "away_team": "NE",
    }
    row.update(overrides)
    return pd.Series(row)


def test_middle_key_covers_both_legs():
    base = _middle_row()
    assert middle_alert_key(base) == middle_alert_key(_middle_row())
    # A different book on either leg is a different opportunity.
    assert middle_alert_key(base) != middle_alert_key(_middle_row(book_b="betmgm"))
    assert middle_alert_key(base) != middle_alert_key(_middle_row(line_a=-2.5))


def test_steam_key_changes_once_the_stale_book_moves():
    base = _steam_row()
    assert steam_alert_key(base) == steam_alert_key(_steam_row())
    assert steam_alert_key(base) != steam_alert_key(_steam_row(stale_line=45.5))
    assert steam_alert_key(base) != steam_alert_key(_steam_row(stale_book="betmgm"))


# --- message text ------------------------------------------------------------


def test_messages_are_labelled_experimental():
    """Neither strategy has a live track record. The prop-EV signal set the
    precedent: say so in the text itself, not just in a docstring.
    """
    assert format_middle_alert_message(_middle_row()).startswith("[EXPERIMENTAL]")
    assert format_steam_alert_message(_steam_row()).startswith("[EXPERIMENTAL]")


def test_middle_message_names_both_books_and_the_window():
    msg = format_middle_alert_message(_middle_row())
    assert "Fanduel" in msg and "Draftkings" in msg
    assert "(3, 7)" in msg
    assert "2026_01_NE_SEA" in msg


def test_steam_message_names_the_stale_book_and_the_move():
    msg = format_steam_alert_message(_steam_row())
    assert "Fanduel" in msg
    assert "6 books moved" in msg
    assert "44.5" in msg
