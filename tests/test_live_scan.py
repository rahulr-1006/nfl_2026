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


# --- max_capture_gap: 2026-08-21 adversarial-audit fix -- a spot must not be
# flagged from a stale Pinnacle read compared against a fresh execution-book
# price (e.g. Pinnacle missing from one poll cycle, falling back to an older
# quote) ---


def test_find_positive_ev_spots_ignores_a_spot_with_a_stale_pinnacle_price(tmp_path):
    store = PointInTimeStore(root=tmp_path / "snapshots")
    store.write(
        [
            # Pinnacle's only quote is from 3 hours before the execution book's --
            # e.g. Pinnacle dropped out of one poll cycle and this is a stale fallback.
            _snapshot("pinnacle", Side.HOME, -150, capture_time=CAPTURE_TIME - timedelta(hours=3)),
            _snapshot("pinnacle", Side.AWAY, 130, capture_time=CAPTURE_TIME - timedelta(hours=3)),
            _snapshot("fanduel", Side.HOME, 120, capture_time=CAPTURE_TIME),
            _snapshot("fanduel", Side.AWAY, -140, capture_time=CAPTURE_TIME),
        ]
    )

    spots = find_positive_ev_spots(store, threshold=0.02, as_of=CAPTURE_TIME + timedelta(minutes=1))
    assert spots.empty


def test_find_positive_ev_spots_allows_a_small_natural_capture_gap(tmp_path):
    store = PointInTimeStore(root=tmp_path / "snapshots")
    store.write(
        [
            # A few minutes apart -- normal single-poll write jitter, not a stale fallback.
            _snapshot("pinnacle", Side.HOME, -150, capture_time=CAPTURE_TIME),
            _snapshot("pinnacle", Side.AWAY, 130, capture_time=CAPTURE_TIME),
            _snapshot("fanduel", Side.HOME, 120, capture_time=CAPTURE_TIME + timedelta(minutes=5)),
            _snapshot("fanduel", Side.AWAY, -140, capture_time=CAPTURE_TIME + timedelta(minutes=5)),
        ]
    )

    spots = find_positive_ev_spots(store, threshold=0.02, as_of=CAPTURE_TIME + timedelta(minutes=10))
    assert len(spots) == 1


def test_find_positive_ev_spots_max_capture_gap_is_configurable(tmp_path):
    store = PointInTimeStore(root=tmp_path / "snapshots")
    store.write(
        [
            _snapshot("pinnacle", Side.HOME, -150, capture_time=CAPTURE_TIME),
            _snapshot("pinnacle", Side.AWAY, 130, capture_time=CAPTURE_TIME),
            _snapshot("fanduel", Side.HOME, 120, capture_time=CAPTURE_TIME + timedelta(minutes=5)),
            _snapshot("fanduel", Side.AWAY, -140, capture_time=CAPTURE_TIME + timedelta(minutes=5)),
        ]
    )

    # A gap that's fine under the default 30-minute window is rejected under
    # a caller-supplied, tighter one.
    spots = find_positive_ev_spots(
        store, threshold=0.02, as_of=CAPTURE_TIME + timedelta(minutes=10), max_capture_gap=timedelta(minutes=1)
    )
    assert spots.empty


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


# --- alert state pruning ----------------------------------------------------


def _rec(days_ago, now):
    from datetime import timedelta
    return AlertRecord(edge=0.05, alerted_at=now - timedelta(days=days_ago))


def test_prune_drops_entries_whose_game_has_started():
    """**Pruning must key on KICKOFF, not alert age.** Measured 2026-08-23: the
    state held 874 entries, 866 for already-played 2023-24 games -- residue from
    the pre-`upcoming_only` bug. That bug fired TODAY, so those entries carry
    recent `alerted_at` values and an age filter keeps every one of them. What
    makes an entry dead is that its event has started.
    """
    from datetime import timedelta

    from src.signal.live_scan import prune_alert_state

    now = datetime(2026, 9, 20, tzinfo=UTC)
    state = {
        "2026_01_KC_LAC|home|fanduel": _rec(0, now),
        "ev|2023_11_LAC_GB|Aaron Jones|receptions|3.5|under|betmgm": _rec(0, now),  # alerted today
    }
    kickoffs = {
        "2026_01_KC_LAC": now + timedelta(days=3),      # upcoming -> keep
        "2023_11_LAC_GB": now - timedelta(days=1000),   # long played -> drop
    }
    kept = prune_alert_state(state, now=now, kickoffs=kickoffs)
    assert list(kept) == ["2026_01_KC_LAC|home|fanduel"]


def test_event_id_parses_from_all_three_key_shapes():
    from src.signal.live_scan import event_id_from_alert_key

    assert event_id_from_alert_key("2026_01_KC_LAC|home|fanduel") == "2026_01_KC_LAC"
    assert event_id_from_alert_key("ev|2023_11_LAC_GB|A|receptions|3.5|under|betmgm") == "2023_11_LAC_GB"
    assert event_id_from_alert_key("arb|2024_06_WAS_BAL|B|passing_tds|1.5|betrivers|betmgm") == "2024_06_WAS_BAL"
    assert event_id_from_alert_key("__pinnacle_props_arrival__") is None


def test_prune_never_ages_out_a_one_shot_sentinel():
    """`__pinnacle_props_arrival__` is a latch, not a dedup entry. Dropping it
    would re-fire an announcement that must happen exactly once, ever.
    """
    from src.signal.live_scan import prune_alert_state

    now = datetime(2026, 9, 20, tzinfo=UTC)
    state = {"__pinnacle_props_arrival__": AlertRecord(edge=1.0, alerted_at=now)}
    assert list(prune_alert_state(state, now=now, kickoffs={})) == ["__pinnacle_props_arrival__"]


def test_unresolvable_event_falls_back_to_age_so_it_cannot_accumulate():
    from src.signal.live_scan import prune_alert_state

    now = datetime(2026, 9, 20, tzinfo=UTC)
    state = {"weird_key_shape": _rec(400, now), "recent_weird_key": _rec(1, now)}
    assert list(prune_alert_state(state, now=now, kickoffs={})) == ["recent_weird_key"]


def test_prune_window_exceeds_the_props_posting_window():
    """The fallback window must exceed how far ahead of kickoff an alert can
    fire (21 days), or a still-live alert would be deleted and re-sent.
    """
    from src.collect.props_budget import POSTING_WINDOW_DAYS
    from src.signal.live_scan import DEFAULT_ALERT_STATE_MAX_AGE

    assert DEFAULT_ALERT_STATE_MAX_AGE.days > POSTING_WINDOW_DAYS
