from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from src.backtest.steam import (
    BookMove,
    _largest_time_cluster,
    book_moves,
    detect_steam_move,
    find_steam_opportunities,
    price_stale_book_opportunity,
)
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, OddsSnapshot, Side

CAPTURE_TIME = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
EVENT_START = datetime(2026, 9, 13, 17, 0, tzinfo=UTC)


def _snapshot(book, market, side, price_american, line=None, capture_time=CAPTURE_TIME, event_id="2026_01_NE_SEA") -> OddsSnapshot:
    return OddsSnapshot.from_american(
        capture_time=capture_time,
        event_id=event_id,
        season=2026,
        week=1,
        home_team="SEA",
        away_team="NE",
        event_start_time=EVENT_START,
        book=book,
        market=market,
        side=side,
        price_american=price_american,
        line=line,
    )


def _rows_df(rows: list[dict]) -> pd.DataFrame:
    base = {"event_id": "2026_01_NE_SEA"}
    return pd.DataFrame([{**base, **r} for r in rows])


# --- book_moves ---


def test_book_moves_reports_each_books_own_earliest_to_latest_change():
    df = _rows_df(
        [
            {"book": "fanduel", "market": "spread", "side": "home", "line": -3.0, "price_decimal": 1.91, "capture_time": CAPTURE_TIME},
            {"book": "fanduel", "market": "spread", "side": "home", "line": -5.0, "price_decimal": 1.87, "capture_time": CAPTURE_TIME + timedelta(hours=2)},
            {"book": "draftkings", "market": "spread", "side": "home", "line": -3.0, "price_decimal": 1.91, "capture_time": CAPTURE_TIME},
        ]
    )
    moves = book_moves(df, Market.SPREAD, Side.HOME)
    assert len(moves) == 2
    fd = next(m for m in moves if m.book == "fanduel")
    dk = next(m for m in moves if m.book == "draftkings")
    assert fd.direction == pytest.approx(-2.0)
    assert dk.direction == pytest.approx(0.0)  # only one real quote -- no movement


def test_book_moves_ignores_rows_with_no_line():
    df = _rows_df(
        [
            {"book": "fanduel", "market": "spread", "side": "home", "line": None, "price_decimal": 1.91, "capture_time": CAPTURE_TIME},
            {"book": "fanduel", "market": "spread", "side": "home", "line": -3.0, "price_decimal": 1.91, "capture_time": CAPTURE_TIME + timedelta(hours=1)},
        ]
    )
    moves = book_moves(df, Market.SPREAD, Side.HOME)
    assert len(moves) == 1
    assert moves[0].from_line == pytest.approx(-3.0)  # the null row dropped, only one real quote remains


# --- _largest_time_cluster ---


def _move(book, to_time, direction=1.0):
    return BookMove(book=book, from_line=0.0, to_line=direction, from_time=to_time, to_time=to_time)


def test_largest_time_cluster_finds_a_tight_group():
    base = CAPTURE_TIME
    moves = [
        _move("a", base),
        _move("b", base + timedelta(minutes=10)),
        _move("c", base + timedelta(minutes=20)),
        _move("d", base + timedelta(hours=5)),  # far outlier
    ]
    cluster = _largest_time_cluster(moves, pd.Timedelta(hours=1))
    assert {m.book for m in cluster} == {"a", "b", "c"}


def test_largest_time_cluster_returns_all_when_everything_fits():
    base = CAPTURE_TIME
    moves = [_move("a", base), _move("b", base + timedelta(minutes=5))]
    cluster = _largest_time_cluster(moves, pd.Timedelta(hours=1))
    assert len(cluster) == 2


def test_largest_time_cluster_picks_the_bigger_of_two_separated_groups():
    base = CAPTURE_TIME
    moves = [
        _move("a", base),
        _move("b", base + timedelta(minutes=5)),
        _move("c", base + timedelta(hours=10)),
        _move("d", base + timedelta(hours=10, minutes=5)),
        _move("e", base + timedelta(hours=10, minutes=10)),
    ]
    cluster = _largest_time_cluster(moves, pd.Timedelta(hours=1))
    assert {m.book for m in cluster} == {"c", "d", "e"}


# --- detect_steam_move ---


def _steam_df(n_books=3, direction=-1.0, spread_over_time=timedelta(minutes=0), execution_books=("fanduel", "draftkings", "betmgm")):
    """n_books move together (home line by `direction` points) within a
    tight window; any books in execution_books beyond n_books stay put
    (stale)."""
    rows = []
    books = list(execution_books)[:n_books] if n_books <= len(execution_books) else list(execution_books) + [f"book{i}" for i in range(n_books - len(execution_books))]
    for i, book in enumerate(books):
        t = CAPTURE_TIME + i * spread_over_time
        rows.append({"book": book, "market": "spread", "side": "home", "line": -3.0, "price_decimal": 1.91, "capture_time": CAPTURE_TIME - timedelta(hours=1)})
        rows.append({"book": book, "market": "spread", "side": "home", "line": -3.0 + direction, "price_decimal": 1.87, "capture_time": t})
    for book in execution_books[n_books:]:
        rows.append({"book": book, "market": "spread", "side": "home", "line": -3.0, "price_decimal": 1.91, "capture_time": CAPTURE_TIME - timedelta(hours=1)})
    return _rows_df(rows)


def test_detect_steam_move_finds_a_real_synchronized_move():
    df = _steam_df(n_books=3, direction=-1.0, execution_books=("fanduel", "draftkings", "betmgm", "betrivers"))
    steam = detect_steam_move(df, Market.SPREAD, Side.HOME, min_books=3, window=pd.Timedelta(hours=1))
    assert steam is not None
    assert steam.direction == -1.0
    assert set(steam.books_moved) == {"fanduel", "draftkings", "betmgm"}
    assert steam.stale_books == ["betrivers"]


def test_detect_steam_move_none_when_too_few_books_move():
    df = _steam_df(n_books=2, direction=-1.0, execution_books=("fanduel", "draftkings", "betmgm"))
    steam = detect_steam_move(df, Market.SPREAD, Side.HOME, min_books=3, window=pd.Timedelta(hours=1))
    assert steam is None


def test_detect_steam_move_none_when_moves_are_spread_out_over_days():
    # Real movement, but not synchronized -- this is middling's target,
    # not steam's.
    df = _steam_df(n_books=3, direction=-1.0, spread_over_time=timedelta(days=1), execution_books=("fanduel", "draftkings", "betmgm"))
    steam = detect_steam_move(df, Market.SPREAD, Side.HOME, min_books=3, window=pd.Timedelta(hours=1))
    assert steam is None


def test_detect_steam_move_does_not_mix_opposite_directions():
    rows = [
        {"book": "fanduel", "market": "spread", "side": "home", "line": -3.0, "price_decimal": 1.91, "capture_time": CAPTURE_TIME - timedelta(hours=1)},
        {"book": "fanduel", "market": "spread", "side": "home", "line": -5.0, "price_decimal": 1.87, "capture_time": CAPTURE_TIME},
        {"book": "draftkings", "market": "spread", "side": "home", "line": -3.0, "price_decimal": 1.91, "capture_time": CAPTURE_TIME - timedelta(hours=1)},
        {"book": "draftkings", "market": "spread", "side": "home", "line": -5.0, "price_decimal": 1.87, "capture_time": CAPTURE_TIME + timedelta(minutes=5)},
        # betmgm moves the OPPOSITE way -- shouldn't join the cluster
        {"book": "betmgm", "market": "spread", "side": "home", "line": -3.0, "price_decimal": 1.91, "capture_time": CAPTURE_TIME - timedelta(hours=1)},
        {"book": "betmgm", "market": "spread", "side": "home", "line": -1.0, "price_decimal": 1.95, "capture_time": CAPTURE_TIME + timedelta(minutes=10)},
    ]
    steam = detect_steam_move(_rows_df(rows), Market.SPREAD, Side.HOME, min_books=3, window=pd.Timedelta(hours=1))
    assert steam is None  # only 2 books agree on direction, below min_books=3


def test_detect_steam_move_stale_books_restricted_to_execution_books():
    rows = [
        {"book": "fanduel", "market": "spread", "side": "home", "line": -3.0, "price_decimal": 1.91, "capture_time": CAPTURE_TIME - timedelta(hours=1)},
        {"book": "fanduel", "market": "spread", "side": "home", "line": -5.0, "price_decimal": 1.87, "capture_time": CAPTURE_TIME},
        {"book": "draftkings", "market": "spread", "side": "home", "line": -3.0, "price_decimal": 1.91, "capture_time": CAPTURE_TIME - timedelta(hours=1)},
        {"book": "draftkings", "market": "spread", "side": "home", "line": -5.0, "price_decimal": 1.87, "capture_time": CAPTURE_TIME + timedelta(minutes=5)},
        {"book": "betmgm", "market": "spread", "side": "home", "line": -3.0, "price_decimal": 1.91, "capture_time": CAPTURE_TIME - timedelta(hours=1)},
        {"book": "betmgm", "market": "spread", "side": "home", "line": -5.0, "price_decimal": 1.87, "capture_time": CAPTURE_TIME + timedelta(minutes=10)},
        # pinnacle stays put -- counts toward the market-wide picture but
        # is NOT a bettable execution book, so must not appear in stale_books
        {"book": "pinnacle", "market": "spread", "side": "home", "line": -3.0, "price_decimal": 1.91, "capture_time": CAPTURE_TIME - timedelta(hours=1)},
    ]
    steam = detect_steam_move(
        _rows_df(rows), Market.SPREAD, Side.HOME, min_books=3, window=pd.Timedelta(hours=1), books=("fanduel", "draftkings", "betmgm")
    )
    assert steam is not None
    assert steam.stale_books == []  # pinnacle didn't move but isn't in `books`, so it's correctly excluded


# --- price_stale_book_opportunity ---


def test_price_stale_book_opportunity_matches_expected_value_directly():
    result = price_stale_book_opportunity(
        stale_line=-3.0, stale_price_decimal=1.91, market=Market.SPREAD, side=Side.HOME, mu=6.0, sigma=13.0
    )
    from src.signal.sizing import expected_value

    assert result["edge"] == pytest.approx(expected_value(result["p_win"], 1.91))


def test_price_stale_book_opportunity_rejects_non_positive_sigma():
    with pytest.raises(ValueError):
        price_stale_book_opportunity(stale_line=-3.0, stale_price_decimal=1.91, market=Market.SPREAD, side=Side.HOME, mu=6.0, sigma=0.0)


def test_price_stale_book_opportunity_zero_stake_when_no_edge():
    # mu far from favoring this side -- no real edge, no stake.
    result = price_stale_book_opportunity(
        stale_line=-3.0, stale_price_decimal=1.91, market=Market.SPREAD, side=Side.HOME, mu=-10.0, sigma=13.0
    )
    assert result["suggested_stake"] == 0.0


# --- find_steam_opportunities (integration, real PointInTimeStore) ---


def test_find_steam_opportunities_end_to_end(tmp_path):
    store = PointInTimeStore(root=tmp_path / "snapshots")
    old, new = CAPTURE_TIME - timedelta(hours=1), CAPTURE_TIME
    snaps = [
        _snapshot("fanduel", Market.SPREAD, Side.HOME, -110, line=-3.0, capture_time=old),
        _snapshot("fanduel", Market.SPREAD, Side.HOME, -105, line=-5.0, capture_time=new),
        _snapshot("draftkings", Market.SPREAD, Side.HOME, -110, line=-3.0, capture_time=old),
        _snapshot("draftkings", Market.SPREAD, Side.HOME, -105, line=-5.0, capture_time=new + timedelta(minutes=5)),
        _snapshot("betmgm", Market.SPREAD, Side.HOME, -110, line=-3.0, capture_time=old),
        _snapshot("betmgm", Market.SPREAD, Side.HOME, -105, line=-5.0, capture_time=new + timedelta(minutes=10)),
        # betrivers hasn't moved -- the stale, actionable book
        _snapshot("betrivers", Market.SPREAD, Side.HOME, -110, line=-3.0, capture_time=old),
        # pinnacle already reflects the post-steam consensus
        _snapshot("pinnacle", Market.SPREAD, Side.HOME, -220, line=-6.0, capture_time=new),
        _snapshot("pinnacle", Market.SPREAD, Side.AWAY, 180, line=6.0, capture_time=new),
    ]
    store.write(snaps)

    report = find_steam_opportunities(
        store, sigma_margin=13.0, sigma_total=10.0, min_books=3, window=pd.Timedelta(hours=1),
        books=("fanduel", "draftkings", "betmgm", "betrivers"), as_of=new + timedelta(hours=1),
    )
    assert not report.empty
    row = report.iloc[0]
    assert row["stale_book"] == "betrivers"
    assert row["market"] == "spread"
    assert row["n_books_moved"] == 3


def test_find_steam_opportunities_empty_when_nothing_moves(tmp_path):
    store = PointInTimeStore(root=tmp_path / "snapshots")
    store.write(
        [
            _snapshot("fanduel", Market.SPREAD, Side.HOME, -110, line=-3.0, capture_time=CAPTURE_TIME),
            _snapshot("draftkings", Market.SPREAD, Side.HOME, -110, line=-3.0, capture_time=CAPTURE_TIME),
            _snapshot("pinnacle", Market.SPREAD, Side.HOME, -110, line=-3.0, capture_time=CAPTURE_TIME),
            _snapshot("pinnacle", Market.SPREAD, Side.AWAY, -110, line=3.0, capture_time=CAPTURE_TIME),
        ]
    )
    report = find_steam_opportunities(store, sigma_margin=13.0, sigma_total=10.0, as_of=CAPTURE_TIME + timedelta(hours=1))
    assert report.empty
