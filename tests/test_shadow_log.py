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
