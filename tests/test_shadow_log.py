from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from src.signal.shadow_log import (
    ShadowObservation,
    append,
    legs_from_spot,
    load,
    recheck,
    record_alert,
    survival_report,
)
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, OddsSnapshot, Side

KICKOFF = datetime(2026, 9, 10, 0, 15, tzinfo=UTC)
T0 = KICKOFF - timedelta(hours=5)


def _key(row: pd.Series) -> str:
    if "book_over" in row.index:
        return f"arb|{row['event_id']}|{row['player_name']}|{row['prop_stat']}|{row['line']}"
    return f"ev|{row['event_id']}|{row['player_name']}|{row['prop_stat']}|{row['line']}|{row['side']}|{row['book']}"


def _arb_spot() -> pd.DataFrame:
    return pd.DataFrame([{
        "event_id": "2026_01_NE_SEA", "player_name": "A Player", "prop_stat": "receptions",
        "line": 4.5, "book_over": "fanduel", "price_american_over": 110,
        "book_under": "betrivers", "price_american_under": -105,
        "arb_margin": 0.012, "capture_time": T0,
    }])


def _ev_spot(price: int = -110) -> pd.DataFrame:
    return pd.DataFrame([{
        "event_id": "2026_01_NE_SEA", "player_name": "A Player", "prop_stat": "receptions",
        "line": 4.5, "side": "over", "book": "fanduel", "price_american": price,
        "edge": 0.06, "capture_time": T0,
    }])


def _snap(price: int, capture: datetime, book: str = "fanduel", side: Side = Side.OVER) -> OddsSnapshot:
    return OddsSnapshot.from_american(
        capture_time=capture, event_id="2026_01_NE_SEA", event_start_time=KICKOFF,
        book=book, market=Market.PLAYER_PROP, side=side,
        price_american=price, line=4.5, player_name="A Player", prop_stat="receptions",
        season=2026, week=1, home_team="SEA", away_team="NE",
    )


def _store(tmp_path, snapshots) -> PointInTimeStore:
    s = PointInTimeStore(root=str(tmp_path / "snap"))
    s.write(snapshots)
    return s


def test_arb_spot_becomes_two_legs_because_an_arb_needs_both():
    legs = legs_from_spot(_arb_spot().iloc[0], "prop_arb", "k")
    assert [leg["leg"] for leg in legs] == ["over", "under"]
    assert {leg["book"] for leg in legs} == {"fanduel", "betrivers"}
    assert [leg["price_american"] for leg in legs] == [110, -105]


def test_single_sided_spot_becomes_one_leg():
    legs = legs_from_spot(_ev_spot().iloc[0], "prop_ev", "k")
    assert len(legs) == 1
    assert legs[0]["leg"] == "single"
    assert legs[0]["side"] is Side.OVER


def test_unknown_strategy_is_rejected_at_write_time():
    with pytest.raises(ValueError, match="unknown strategy"):
        ShadowObservation(
            alert_key="k", strategy="not_a_strategy", leg="single",
            alerted_at=T0, observed_at=T0, is_alert=True,
            event_id="e", market=Market.PLAYER_PROP, side=Side.OVER,
            book="fanduel", price_american=-110,
        )


def test_naive_timestamp_is_rejected_so_elapsed_times_cannot_be_wrong():
    with pytest.raises(ValueError, match="timezone-aware"):
        ShadowObservation(
            alert_key="k", strategy="prop_ev", leg="single",
            # DTZ001 intentional: the naive timestamp IS the thing under test.
            alerted_at=datetime(2026, 9, 9, 12, 0),  # noqa: DTZ001
            observed_at=T0, is_alert=True,
            event_id="e", market=Market.PLAYER_PROP, side=Side.OVER,
            book="fanduel", price_american=-110,
        )


def test_record_alert_writes_one_row_per_leg(tmp_path):
    p = tmp_path / "shadow.jsonl"
    n = record_alert(_arb_spot(), "prop_arb", _key, now=T0, path=p)
    assert n == 2
    rows = load(p)
    assert all(r.is_alert for r in rows)
    assert {r.leg for r in rows} == {"over", "under"}
    assert all(r.capture_time == T0 for r in rows)


def test_empty_spots_write_nothing(tmp_path):
    p = tmp_path / "shadow.jsonl"
    assert record_alert(pd.DataFrame(), "prop_arb", _key, now=T0, path=p) == 0
    assert load(p) == []


def test_missing_file_reads_as_empty_not_an_error(tmp_path):
    assert load(tmp_path / "nope.jsonl") == []
    assert survival_report(tmp_path / "nope.jsonl").empty


def test_price_that_held_is_recorded_as_survived(tmp_path):
    p = tmp_path / "shadow.jsonl"
    record_alert(_ev_spot(-110), "prop_ev", _key, now=T0, path=p)
    later = T0 + timedelta(minutes=30)
    store = _store(tmp_path, [_snap(-110, later)])
    assert recheck(store, as_of=later, path=p) == 1

    rep = survival_report(p)
    assert rep["survived"].tolist() == [True]
    assert rep["elapsed_minutes"].tolist() == [30.0]


def test_price_that_moved_away_is_recorded_as_not_survived(tmp_path):
    p = tmp_path / "shadow.jsonl"
    record_alert(_ev_spot(-110), "prop_ev", _key, now=T0, path=p)
    later = T0 + timedelta(minutes=30)
    store = _store(tmp_path, [_snap(-140, later)])  # worse for the bettor
    recheck(store, as_of=later, path=p)
    assert survival_report(p)["survived"].tolist() == [False]


def test_survival_compares_decimal_payout_not_the_american_integer(tmp_path):
    """-105 is BETTER than -110 but numerically smaller. An integer comparison
    would score a price that improved as a price that decayed."""
    p = tmp_path / "shadow.jsonl"
    record_alert(_ev_spot(-110), "prop_ev", _key, now=T0, path=p)
    later = T0 + timedelta(minutes=30)
    recheck(_store(tmp_path, [_snap(-105, later)]), as_of=later, path=p)
    assert survival_report(p)["survived"].tolist() == [True]


def test_contract_pulled_entirely_is_not_survived_and_does_not_crash(tmp_path):
    p = tmp_path / "shadow.jsonl"
    record_alert(_ev_spot(-110), "prop_ev", _key, now=T0, path=p)
    later = T0 + timedelta(minutes=30)
    # Same game and book, but a different stat -- our contract is gone.
    other = _snap(-110, later)
    store = _store(tmp_path, [other.model_copy(update={"prop_stat": "rushing_yards"})])
    recheck(store, as_of=later, path=p)
    rep = survival_report(p)
    assert rep["last_price"].isna().all()
    assert rep["survived"].tolist() == [False]


def test_arb_survives_only_if_BOTH_legs_hold(tmp_path):
    p = tmp_path / "shadow.jsonl"
    record_alert(_arb_spot(), "prop_arb", _key, now=T0, path=p)
    later = T0 + timedelta(minutes=30)
    store = _store(tmp_path, [
        _snap(110, later, book="fanduel", side=Side.OVER),      # over holds
        _snap(-160, later, book="betrivers", side=Side.UNDER),  # under collapses
    ])
    recheck(store, as_of=later, path=p)

    rep = survival_report(p)
    assert sorted(rep["leg_survived"].tolist()) == [False, True]
    assert rep["survived"].tolist() == [False, False]  # the ALERT did not survive


def test_a_played_game_is_never_rechecked(tmp_path):
    """Re-checking a started game would fabricate survival data from a settled
    market -- the bug that once fired 874 of 879 alerts on finished games."""
    p = tmp_path / "shadow.jsonl"
    record_alert(_ev_spot(-110), "prop_ev", _key, now=T0, path=p)
    after_kickoff = KICKOFF + timedelta(hours=1)
    store = _store(tmp_path, [_snap(-110, KICKOFF - timedelta(minutes=5))])
    assert recheck(store, as_of=after_kickoff, path=p) == 0
    assert survival_report(p)["survived"].isna().all()


def test_alerts_past_the_horizon_stop_being_rechecked(tmp_path):
    p = tmp_path / "shadow.jsonl"
    record_alert(_ev_spot(-110), "prop_ev", _key, now=T0, path=p)
    later = T0 + timedelta(minutes=30)
    store = _store(tmp_path, [_snap(-110, later)])
    assert recheck(store, as_of=later, path=p, horizon=timedelta(minutes=10)) == 0


def test_recheck_without_a_newer_capture_does_not_duplicate_an_observation(tmp_path):
    """The monitor ticks every 5 min but props are polled every 30 -- most
    re-checks see the same snapshot. Appending it would double-count survival."""
    p = tmp_path / "shadow.jsonl"
    record_alert(_ev_spot(-110), "prop_ev", _key, now=T0, path=p)
    later = T0 + timedelta(minutes=30)
    store = _store(tmp_path, [_snap(-110, later)])
    assert recheck(store, as_of=later, path=p) == 1
    assert recheck(store, as_of=later + timedelta(minutes=5), path=p) == 0
    assert len([o for o in load(p) if not o.is_alert]) == 1


def test_alert_with_no_recheck_reports_none_not_dropped(tmp_path):
    """A report must not quietly shrink its own denominator."""
    p = tmp_path / "shadow.jsonl"
    record_alert(_ev_spot(-110), "prop_ev", _key, now=T0, path=p)
    rep = survival_report(p)
    assert len(rep) == 1
    assert rep["survived"].isna().all()
    assert rep["n_rechecks"].tolist() == [0]


def test_log_is_append_only(tmp_path):
    p = tmp_path / "shadow.jsonl"
    record_alert(_ev_spot(-110), "prop_ev", _key, now=T0, path=p)
    first = load(p)
    later = T0 + timedelta(minutes=30)
    recheck(_store(tmp_path, [_snap(-140, later)]), as_of=later, path=p)
    after = load(p)
    assert len(after) == len(first) + 1
    assert after[0].model_dump() == first[0].model_dump()  # original untouched


def test_empty_store_recheck_is_a_noop_not_a_crash(tmp_path):
    p = tmp_path / "shadow.jsonl"
    record_alert(_ev_spot(-110), "prop_ev", _key, now=T0, path=p)
    store = PointInTimeStore(root=str(tmp_path / "empty"))
    assert recheck(store, as_of=T0 + timedelta(minutes=30), path=p) == 0


def test_append_returns_count_and_round_trips(tmp_path):
    p = tmp_path / "shadow.jsonl"
    obs = ShadowObservation(
        alert_key="k", strategy="team_total", leg="single",
        alerted_at=T0, observed_at=T0, is_alert=True,
        event_id="2026_01_NE_SEA", market=Market.PLAYER_PROP, side=Side.OVER,
        book="fanduel", price_american=-110, line=4.5,
        player_name="A Player", prop_stat="receptions",
    )
    assert append([obs], p) == 1
    assert load(p)[0].model_dump() == obs.model_dump()


# --- real scanner output, not a hand-built row ---------------------------
#
# Every test above feeds `legs_from_spot` a dict written by hand to match what
# the shadow log already expects, which is exactly why a live bug survived
# them: the moneyline scanner emitted `book_price_american`/`book_time` while
# `legs_from_spot` read `price_american`/`capture_time`, so every moneyline
# alert from 2026-09-03 onward was texted and then dropped by the shadow log
# (caught only as a swallowed `KeyError` in monitor.err.log). These tests run
# the REAL scanner output through the REAL sink so the two cannot drift again.


def _moneyline_spots(tmp_path):
    from src.signal.live_scan import find_positive_ev_spots

    store = PointInTimeStore(root=str(tmp_path / "ml"))
    store.write([
        OddsSnapshot.from_american(
            capture_time=T0, event_id="2026_01_NE_SEA", season=2026, week=1,
            home_team="SEA", away_team="NE", event_start_time=KICKOFF,
            book=book, market=Market.MONEYLINE, side=side, price_american=price,
        )
        for book, side, price in [
            ("pinnacle", Side.HOME, -150), ("pinnacle", Side.AWAY, 130),
            ("fanduel", Side.HOME, 120), ("fanduel", Side.AWAY, -140),
        ]
    ])
    return find_positive_ev_spots(store, threshold=0.02, as_of=T0 + timedelta(minutes=1))


def test_real_moneyline_scan_output_survives_the_shadow_log(tmp_path):
    from src.signal.live_scan import _alert_key

    spots = _moneyline_spots(tmp_path)
    assert not spots.empty, "fixture must produce a spot or this proves nothing"

    legs = legs_from_spot(spots.iloc[0], "moneyline_ev", _alert_key(spots.iloc[0]))

    assert len(legs) == 1
    assert legs[0]["market"] is Market.MONEYLINE
    assert legs[0]["side"] is Side.HOME
    assert legs[0]["price_american"] == 120
    assert legs[0]["player_name"] is None


def test_moneyline_alert_records_the_book_capture_time_not_none(tmp_path):
    """The whole point of the shadow log is latency against the market's own
    clock, so a moneyline leg landing with `capture_time=None` would silently
    make every survival number unmeasurable rather than wrong.
    """
    from src.signal.live_scan import _alert_key

    path = tmp_path / "shadow.jsonl"
    n = record_alert(_moneyline_spots(tmp_path), "moneyline_ev", _alert_key, path=path)

    assert n == 1
    obs = load(path)[0]
    assert obs.capture_time == T0


# --- middle / steam leg shapes (2026-09-08) ----------------------------------
#
# `legs_from_spot` previously understood exactly two row shapes: two-leg prop
# arb and a generic single leg, and hardcoded every non-prop row's market to
# MONEYLINE. Middling and steam trade SPREAD and TOTAL and carry neither a
# `book` nor a `price_american` column, so wiring them into the monitor without
# this would have raised KeyError inside the shadow-record path -- caught and
# logged, so the alerts would still have sent while their CLV rows silently
# vanished. That is exactly the failure mode that hid the moneyline gap.


def _middle_row():
    return pd.Series({
        "event_id": "2026_01_NE_SEA", "market": "spread",
        "book_a": "fanduel", "side_a": "home", "line_a": -3.0, "price_decimal_a": 1.91,
        "book_b": "draftkings", "side_b": "away", "line_b": 7.0, "price_decimal_b": 1.95,
        "ev": 0.2, "total_risked": 4.0, "ev_rate": 0.05,
    })


def _steam_row():
    return pd.Series({
        "event_id": "2026_01_NE_SEA", "market": "total", "side": "over",
        "stale_book": "fanduel", "stale_line": 44.5, "price_decimal": 1.91,
        "edge": 0.03, "suggested_stake": 1.25,
    })


def test_middle_row_becomes_two_legs_with_per_leg_lines():
    from src.signal.shadow_log import legs_from_spot

    legs = legs_from_spot(_middle_row(), "middle", "k")
    assert [leg["leg"] for leg in legs] == ["a", "b"]
    assert [leg["book"] for leg in legs] == ["fanduel", "draftkings"]
    # Each leg keeps its OWN line -- a middle is two different numbers, and
    # collapsing them to one would make the window unrecoverable from the log.
    assert [leg["line"] for leg in legs] == [-3.0, 7.0]
    assert [leg["side"].value for leg in legs] == ["home", "away"]
    assert all(leg["edge"] == 0.05 for leg in legs)


def test_middle_and_steam_legs_record_their_real_market():
    from src.signal.shadow_log import legs_from_spot
    from src.store.schema import Market

    assert all(leg["market"] == Market.SPREAD for leg in legs_from_spot(_middle_row(), "middle", "k"))
    assert legs_from_spot(_steam_row(), "steam", "k")[0]["market"] == Market.TOTAL


def test_steam_row_becomes_one_leg_on_the_stale_book():
    from src.signal.shadow_log import legs_from_spot

    legs = legs_from_spot(_steam_row(), "steam", "k")
    assert len(legs) == 1
    assert legs[0]["book"] == "fanduel"
    assert legs[0]["line"] == 44.5
    assert legs[0]["edge"] == 0.03


def test_decimal_prices_are_converted_to_american():
    """Middling and steam price in decimal; the shadow log stores American.
    An unconverted 1.91 would round to an integer 1 and corrupt every CLV
    comparison made against it.
    """
    from src.signal.shadow_log import legs_from_spot

    assert legs_from_spot(_steam_row(), "steam", "k")[0]["price_american"] == -110
    legs = legs_from_spot(_middle_row(), "middle", "k")
    assert legs[0]["price_american"] == -110
    assert legs[1]["price_american"] == -105  # decimal 1.95, still a favourite


def test_moneyline_rows_still_default_to_the_moneyline_market():
    """The market resolver must not change behaviour for rows that carry no
    `market` column -- that is every existing moneyline scanner row.
    """
    from src.signal.shadow_log import legs_from_spot
    from src.store.schema import Market

    row = pd.Series({
        "event_id": "2026_01_NE_SEA", "side": "home", "book": "fanduel",
        "price_american": -110, "edge": 0.04,
    })
    assert legs_from_spot(row, "moneyline_ev", "k")[0]["market"] == Market.MONEYLINE


def test_unrecognised_market_value_falls_back_rather_than_raising():
    from src.signal.shadow_log import legs_from_spot
    from src.store.schema import Market

    row = pd.Series({
        "event_id": "2026_01_NE_SEA", "market": "not_a_market", "side": "home",
        "book": "fanduel", "price_american": -110, "edge": 0.04,
    })
    assert legs_from_spot(row, "moneyline_ev", "k")[0]["market"] == Market.MONEYLINE


def test_middle_and_steam_rows_survive_a_full_record_alert_roundtrip(tmp_path):
    """End-to-end: the shape the scanner emits must actually persist, not just
    build a leg dict. This is the assertion whose absence let the moneyline
    rows disappear.
    """
    from src.signal.movement_scan import middle_alert_key, steam_alert_key
    from src.signal.shadow_log import load, record_alert

    path = tmp_path / "shadow.jsonl"
    assert record_alert(pd.DataFrame([_middle_row()]), "middle", middle_alert_key, path=path) == 2
    assert record_alert(pd.DataFrame([_steam_row()]), "steam", steam_alert_key, path=path) == 1

    rows = load(path)
    assert len(rows) == 3
    assert {r.strategy for r in rows} == {"middle", "steam"}
    assert {r.market.value for r in rows} == {"spread", "total"}
