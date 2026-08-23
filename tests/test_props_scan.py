from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from src.signal.live_scan import AlertRecord, new_or_improved_spots, record_alerts
from src.signal.props_scan import (
    find_live_prop_arb_spots,
    find_live_prop_ev_spots,
    format_arb_alert_message,
    format_prop_ev_alert_message,
    prop_alert_key,
)
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, OddsSnapshot, Side

KICKOFF = datetime(2026, 9, 7, 17, 0, tzinfo=UTC)
NOW = KICKOFF - timedelta(hours=2)
LATER = KICKOFF - timedelta(hours=1)


def _prop(book, side, price, player="Star Receiver", line=45.5, capture=NOW, stat="receiving_yards"):
    return OddsSnapshot.from_american(
        capture_time=capture, event_id="2026_01_KC_LAC", season=2026, week=1,
        home_team="LAC", away_team="KC", event_start_time=KICKOFF,
        book=book, market=Market.PLAYER_PROP, side=side, price_american=price,
        line=line, player_name=player, prop_stat=stat,
    )


# --- arbitrage ---


def test_finds_a_real_cross_book_arb(tmp_path):
    """+120 over at one book vs +120 under at another sums to ~90.9% implied
    -- a genuine risk-free lock across two placeable books.
    """
    store = PointInTimeStore(root=tmp_path)
    store.write([_prop("draftkings", Side.OVER, 120), _prop("fanduel", Side.UNDER, 120)])

    spots = find_live_prop_arb_spots(store, as_of=NOW)

    assert len(spots) == 1
    assert spots.iloc[0]["arb_margin"] > 0
    assert {spots.iloc[0]["book_over"], spots.iloc[0]["book_under"]} == {"draftkings", "fanduel"}


def test_normal_vigged_market_is_not_an_arb(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    store.write([_prop("draftkings", Side.OVER, -110), _prop("fanduel", Side.UNDER, -110)])
    assert find_live_prop_arb_spots(store, as_of=NOW).empty


def test_thin_arb_below_the_margin_floor_is_filtered_out(tmp_path):
    """Sub-2% arb margins are documented as likely eaten by execution
    latency -- the floor keeps the alert channel actionable.
    """
    store = PointInTimeStore(root=tmp_path)
    store.write([_prop("draftkings", Side.OVER, 102), _prop("fanduel", Side.UNDER, -100)])

    assert find_live_prop_arb_spots(store, as_of=NOW, min_margin=0.05).empty
    assert not find_live_prop_arb_spots(store, as_of=NOW, min_margin=0.0).empty


def test_only_the_latest_quote_counts_for_a_live_arb(tmp_path):
    """A lock that existed earlier but is gone now must not alert -- live
    alerting differs from the backtest, which reports every historical arb.
    """
    store = PointInTimeStore(root=tmp_path)
    store.write([
        _prop("draftkings", Side.OVER, 120, capture=NOW),   # arb existed at NOW
        _prop("fanduel", Side.UNDER, 120, capture=NOW),
        _prop("draftkings", Side.OVER, -130, capture=LATER),  # gone by LATER
        _prop("fanduel", Side.UNDER, -130, capture=LATER),
    ])
    assert find_live_prop_arb_spots(store, as_of=LATER).empty


def test_pinnacle_is_never_used_as_an_arb_leg(tmp_path):
    """Pinnacle isn't a real execution book for this project -- an "arb"
    that requires betting there isn't placeable.
    """
    store = PointInTimeStore(root=tmp_path)
    store.write([_prop("pinnacle", Side.OVER, 120), _prop("pinnacle", Side.UNDER, 120)])
    assert find_live_prop_arb_spots(store, as_of=NOW).empty


def test_empty_store_returns_empty_not_a_crash(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    store.write([
        OddsSnapshot.from_american(
            capture_time=NOW, event_id="E", season=2026, week=1, home_team="A", away_team="B",
            event_start_time=KICKOFF, book="pinnacle", market=Market.MONEYLINE, side=Side.HOME,
            price_american=-110,
        )
    ])
    assert find_live_prop_arb_spots(store, as_of=NOW).empty  # moneyline only, no props
    assert find_live_prop_ev_spots(store, as_of=NOW).empty


# --- prop EV ---


def test_finds_a_prop_ev_spot_against_pinnacle_fair(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    store.write([
        _prop("pinnacle", Side.OVER, -110), _prop("pinnacle", Side.UNDER, -110),  # fair ~0.5
        _prop("draftkings", Side.OVER, 130),  # +130 on a ~50% shot is a big edge
    ])
    spots = find_live_prop_ev_spots(store, as_of=NOW, threshold=0.05)
    assert len(spots) == 1
    assert spots.iloc[0]["book"] == "draftkings"
    assert spots.iloc[0]["edge"] > 0.05


def test_prop_ev_threshold_is_respected(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    store.write([
        _prop("pinnacle", Side.OVER, -110), _prop("pinnacle", Side.UNDER, -110),
        _prop("draftkings", Side.OVER, -105),  # small edge only
    ])
    assert find_live_prop_ev_spots(store, as_of=NOW, threshold=0.50).empty


# --- alert formatting + dedup ---


def test_arb_alert_names_both_legs_and_both_books():
    row = pd.Series({
        "event_id": "2026_01_KC_LAC", "player_name": "Star Receiver", "prop_stat": "receiving_yards",
        "line": 45.5, "book_over": "draftkings", "book_under": "fanduel",
        "price_american_over": 120, "price_american_under": 120, "arb_margin": 0.0909,
    })
    msg = format_arb_alert_message(row)
    assert "Star Receiver" in msg and "45.5" in msg
    assert "Draftkings" in msg and "Fanduel" in msg
    assert "+120" in msg  # both legs' prices present
    assert "9.09%" in msg


def test_prop_ev_alert_is_labeled_experimental():
    """The props-EV signal tested null; the alert must say so rather than
    read like confirmed edge.
    """
    row = pd.Series({
        "event_id": "2026_01_KC_LAC", "player_name": "Star Receiver", "prop_stat": "receiving_yards",
        "line": 45.5, "side": "over", "book": "draftkings", "price_american": 130,
        "fair_prob": 0.5, "edge": 0.15,
    })
    msg = format_prop_ev_alert_message(row)
    assert "EXPERIMENTAL" in msg
    assert "Star Receiver" in msg and "+130" in msg


def test_alert_keys_do_not_collide_across_players_in_one_game():
    """The moneyline key (event|side|book) is identical for every prop in a
    game -- reusing it would let one alerted player mute all the others.
    """
    base = {"event_id": "G1", "prop_stat": "receiving_yards", "line": 45.5, "side": "over", "book": "draftkings"}
    a = prop_alert_key(pd.Series({**base, "player_name": "Player A"}))
    b = prop_alert_key(pd.Series({**base, "player_name": "Player B"}))
    assert a != b


def test_alert_keys_distinguish_arb_from_ev_on_the_same_contract():
    contract = {"event_id": "G1", "player_name": "A", "prop_stat": "receiving_yards", "line": 45.5}
    arb = prop_alert_key(pd.Series({**contract, "book_over": "dk", "book_under": "fd"}))
    ev = prop_alert_key(pd.Series({**contract, "side": "over", "book": "dk"}))
    assert arb != ev
    assert arb.startswith("arb|") and ev.startswith("ev|")


def test_unchanged_spot_does_not_realert_but_improved_one_does():
    spots = pd.DataFrame([{
        "event_id": "G1", "player_name": "A", "prop_stat": "receiving_yards", "line": 45.5,
        "book_over": "dk", "book_under": "fd", "arb_margin": 0.02,
    }])
    state: dict[str, AlertRecord] = {}

    first = new_or_improved_spots(spots, state, key_fn=prop_alert_key, edge_column="arb_margin")
    assert len(first) == 1
    state = record_alerts(first, state, key_fn=prop_alert_key, edge_column="arb_margin")

    again = new_or_improved_spots(spots, state, key_fn=prop_alert_key, edge_column="arb_margin")
    assert again.empty  # same spot, unchanged -> no re-alert

    better = spots.assign(arb_margin=0.05)
    improved = new_or_improved_spots(better, state, key_fn=prop_alert_key, edge_column="arb_margin")
    assert len(improved) == 1  # materially better -> alert again


# --- exposure cap ---


def test_exposure_cap_truncates_rather_than_shrinking_stakes():
    from src.notify.monitor_run import _apply_exposure_cap

    spots = pd.DataFrame({"suggested_stake": [2.0, 2.0, 2.0, 2.0, 2.0]})
    capped, remaining = _apply_exposure_cap(spots, remaining=6.0)
    assert len(capped) == 3
    assert list(capped["suggested_stake"]) == [2.0, 2.0, 2.0]  # unshrunk
    assert remaining == pytest.approx(0.0)


def test_exposure_cap_charges_rows_without_a_stake_column(tmp_path):
    """Arb spots carry no `suggested_stake` (legs are sized separately), but
    they are still real money leaving a $100 bankroll. Treating them as free
    -- the pre-2026-08-23 behavior -- let unlimited arb alerts through a cap
    whose entire purpose is bounding total exposure.
    """
    from src.notify.monitor_run import _apply_exposure_cap

    arb_like = pd.DataFrame({"arb_margin": [0.02, 0.03, 0.04]})
    capped, remaining = _apply_exposure_cap(arb_like, remaining=5.0, default_stake=2.0)
    assert len(capped) == 2  # 2 x $2 fits in $5, the third does not
    assert remaining == pytest.approx(1.0)


def test_exposure_budget_is_shared_across_successive_signals():
    """The cap is a per-CYCLE ceiling, not per-batch: spending it on the first
    signal must leave less for the next.
    """
    from src.notify.monitor_run import _apply_exposure_cap

    first = pd.DataFrame({"suggested_stake": [2.0, 2.0]})
    second = pd.DataFrame({"suggested_stake": [2.0, 2.0]})

    kept_first, remaining = _apply_exposure_cap(first, remaining=5.0)
    kept_second, remaining = _apply_exposure_cap(second, remaining=remaining)

    assert len(kept_first) == 2  # $4 of $5
    assert len(kept_second) == 0  # only $1 left, can't cover a $2 stake
    assert remaining == pytest.approx(1.0)


@pytest.mark.parametrize("remaining", [0.0, 100.0])
def test_exposure_cap_handles_extremes(remaining):
    from src.notify.monitor_run import _apply_exposure_cap

    spots = pd.DataFrame({"suggested_stake": [2.0, 2.0]})
    capped, _ = _apply_exposure_cap(spots, remaining=remaining)
    assert len(capped) == (0 if remaining == 0.0 else 2)


def test_stale_quote_does_not_alert_as_a_live_lock(tmp_path):
    """A contract pulled from the board keeps its last-ever quote, which
    `upcoming_only` happily passes (the game is still in the future). Without
    an absolute age bound the scanner texts a lock that no longer exists.
    """
    stale_capture = NOW - timedelta(hours=30)
    store = PointInTimeStore(root=tmp_path)
    store.write([
        _prop("draftkings", Side.OVER, 120, capture=stale_capture),
        _prop("fanduel", Side.UNDER, 120, capture=stale_capture),
    ])

    assert find_live_prop_arb_spots(store, as_of=NOW, min_margin=0.0).empty
    # ...but the same quote inside the freshness window still alerts.
    assert not find_live_prop_arb_spots(
        store, as_of=NOW, min_margin=0.0, max_quote_age=pd.Timedelta(hours=48)
    ).empty


# --- already-played games must never alert (real bug, found by a dry run) ---


def _past_prop(book, side, price, capture, kickoff):
    return OddsSnapshot.from_american(
        capture_time=capture, event_id="2023_01_OLD_GAME", season=2023, week=1,
        home_team="LAC", away_team="KC", event_start_time=kickoff,
        book=book, market=Market.PLAYER_PROP, side=side, price_american=price,
        line=45.5, player_name="Retired Guy", prop_stat="receiving_yards",
    )


def test_finished_games_never_produce_prop_alerts(tmp_path):
    """The store holds the 2023-2024 historical backfill alongside live
    collection. A dry run found 874 of 879 flagged spots were on games
    played months ago -- unbettable noise that would have flooded the phone.
    """
    old_kickoff = datetime(2023, 9, 10, 17, 0, tzinfo=UTC)
    old_capture = old_kickoff - timedelta(hours=2)
    store = PointInTimeStore(root=tmp_path)
    store.write([
        _past_prop("draftkings", Side.OVER, 120, old_capture, old_kickoff),  # a real arb, but long finished
        _past_prop("fanduel", Side.UNDER, 120, old_capture, old_kickoff),
    ])

    assert find_live_prop_arb_spots(store, as_of=NOW, min_margin=0.0).empty
    assert find_live_prop_ev_spots(store, as_of=NOW, threshold=0.0).empty


def test_upcoming_games_still_alert_alongside_finished_ones(tmp_path):
    """The filter must remove only the past, not suppress live spots that
    happen to share a store with historical data.
    """
    old_kickoff = datetime(2023, 9, 10, 17, 0, tzinfo=UTC)
    store = PointInTimeStore(root=tmp_path)
    store.write([
        _past_prop("draftkings", Side.OVER, 120, old_kickoff - timedelta(hours=2), old_kickoff),
        _past_prop("fanduel", Side.UNDER, 120, old_kickoff - timedelta(hours=2), old_kickoff),
        _prop("draftkings", Side.OVER, 120),   # upcoming (KICKOFF is in 2026)
        _prop("fanduel", Side.UNDER, 120),
    ])

    spots = find_live_prop_arb_spots(store, as_of=NOW, min_margin=0.0)
    assert len(spots) == 1
    assert spots.iloc[0]["event_id"] == "2026_01_KC_LAC"
