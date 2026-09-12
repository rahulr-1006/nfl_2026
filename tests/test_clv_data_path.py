"""The CLV data path, end to end: shadow alert -> notional bet -> close -> CLV.

Written 2026-09-08 after finding two gaps that between them meant a deliberate
no-bet observation window would have produced NO usable CLV data at all:

  1. `latest_fair_prob` had no `event_id` filter. Given a whole-store frame it
     matched one book's quotes across EVERY game, so its "exactly two sides at
     the latest timestamp" check saw 2 rows per event and returned None. Mainline
     CLV was silently unmeasurable for every logged bet. Props escaped by
     accident (player_name + prop_stat isolate a game). Nothing tested it.
  2. Nothing computed CLV from shadow alerts at all -- CLV existed only for
     placed bets and historical replay.
"""

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from src.backtest.engine import latest_fair_prob
from src.clv.shadow_clv import shadow_alerts_as_bets, shadow_clv, shadow_clv_frame
from src.signal.shadow_log import record_alert
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, OddsSnapshot, Side

NOW = datetime.now(UTC)
ENTRY_TIME = NOW - timedelta(days=2)
KICKOFF = NOW - timedelta(hours=1)  # already started, so a close exists
CLOSE_TIME = KICKOFF - timedelta(minutes=20)


def _snap(event_id, book, market, side, price, capture_time, line=None, home="SEA", away="NE"):
    return OddsSnapshot.from_american(
        capture_time=capture_time, event_id=event_id, season=2026, week=1,
        home_team=home, away_team=away, event_start_time=KICKOFF,
        book=book, market=market, side=side, price_american=price, line=line,
    )


def _two_event_store(root):
    """Two games quoted by the same book at the same instants -- the shape that
    broke `latest_fair_prob`. With one event it passes trivially.
    """
    store = PointInTimeStore(root=root)
    rows = []
    for event_id, home, away, drift in (
        ("2026_01_NE_SEA", "SEA", "NE", 0), ("2026_01_GB_MIN", "MIN", "GB", 40),
    ):
        for t, (h, a) in ((ENTRY_TIME, (-110, -110)), (CLOSE_TIME, (-150, 130))):
            rows += [
                _snap(event_id, "pinnacle", Market.MONEYLINE, Side.HOME, h - drift, t, home=home, away=away),
                _snap(event_id, "pinnacle", Market.MONEYLINE, Side.AWAY, a + drift, t, home=home, away=away),
                _snap(event_id, "fanduel", Market.MONEYLINE, Side.HOME, h + 5, t, home=home, away=away),
                _snap(event_id, "fanduel", Market.MONEYLINE, Side.AWAY, a - 5, t, home=home, away=away),
            ]
    store.write(rows)
    return store


# --- the event_id regression -------------------------------------------------


def test_latest_fair_prob_scopes_to_one_event(tmp_path):
    """The bug: on a multi-event frame every mainline lookup returned None."""
    store = _two_event_store(tmp_path / "snaps")
    snaps = store.read_as_of(NOW)
    assert snaps["event_id"].nunique() == 2, "fixture must span >1 event or it cannot catch this"

    p = latest_fair_prob(
        snaps, "pinnacle", Market.MONEYLINE, Side.HOME, NOW, "shin", event_id="2026_01_NE_SEA"
    )
    assert p is not None
    assert 0.0 < p < 1.0


def test_the_two_events_get_different_fair_probabilities(tmp_path):
    """Scoping must actually select -- returning *a* number for both games would
    pass the test above while still being wrong.
    """
    store = _two_event_store(tmp_path / "snaps")
    snaps = store.read_as_of(NOW)
    a = latest_fair_prob(snaps, "pinnacle", Market.MONEYLINE, Side.HOME, NOW, "shin", event_id="2026_01_NE_SEA")
    b = latest_fair_prob(snaps, "pinnacle", Market.MONEYLINE, Side.HOME, NOW, "shin", event_id="2026_01_GB_MIN")
    assert a is not None and b is not None
    assert a != pytest.approx(b)


def test_event_id_is_required_not_optional():
    """A default would leave the trap armed: the failure mode is a silent None,
    so the next caller to forget it gets no error, just missing CLV.
    """
    with pytest.raises(TypeError):
        latest_fair_prob(
            pd.DataFrame(), "pinnacle", Market.MONEYLINE, Side.HOME, NOW, "shin"
        )


# --- shadow alerts -> CLV ----------------------------------------------------


def _log_a_moneyline_alert(path):
    spot = pd.DataFrame([{
        "event_id": "2026_01_NE_SEA", "side": "home", "book": "fanduel",
        "price_american": -105, "edge": 0.04, "capture_time": ENTRY_TIME,
    }])
    record_alert(spot, "moneyline_ev", lambda r: "k1", path=path)


def test_shadow_alert_becomes_a_notional_bet_priced_at_capture_time(tmp_path):
    """`placed_at` must be when the PRICE existed, not when the scanner noticed.
    Entry fair probability is read at `placed_at`, so using our own detection
    clock would score the bet against a market state it was never offered at.
    """
    path = tmp_path / "shadow.jsonl"
    _log_a_moneyline_alert(path)
    bets = shadow_alerts_as_bets(path)
    assert len(bets) == 1
    assert bets[0].placed_at == ENTRY_TIME
    assert bets[0].strategy == "moneyline_ev"
    assert bets[0].alert_key == "k1"


def test_clv_is_computed_once_the_game_has_kicked_off(tmp_path):
    path = tmp_path / "shadow.jsonl"
    _log_a_moneyline_alert(path)
    store = _two_event_store(tmp_path / "snaps")

    bets = shadow_clv(store, path=path, as_of=NOW)
    assert len(bets) == 1
    bet = bets[0]
    assert bet.entry_prob_fair is not None, "entry fair prob must resolve on a multi-event store"
    assert bet.close_prob_fair is not None, "kickoff has passed, so a close exists"
    assert bet.clv_probability is not None
    assert bet.clv_price is not None
    # Took the home side at -105 while Pinnacle drifted -110 -> -150 (home
    # shortened): the close is worse than entry, so CLV is positive.
    assert bet.clv_probability > 0


def test_no_close_before_kickoff_rather_than_a_fake_one(tmp_path):
    """A "close" read while the line is still moving would be a fabricated
    number, and `season_review` retires strategies on these.
    """
    path = tmp_path / "shadow.jsonl"
    _log_a_moneyline_alert(path)
    store = _two_event_store(tmp_path / "snaps")

    # Pin `as_of` before kickoff: the game has not started yet.
    bets = shadow_clv(store, path=path, as_of=KICKOFF - timedelta(minutes=5))
    assert bets[0].close_prob_fair is None
    assert bets[0].clv_probability is None


def test_frame_keeps_unmeasurable_rows_instead_of_shrinking(tmp_path):
    """Dropping them would quietly shrink the denominator, which is how a
    beat-rate starts looking better than it is.
    """
    path = tmp_path / "shadow.jsonl"
    _log_a_moneyline_alert(path)
    store = _two_event_store(tmp_path / "snaps")

    frame = shadow_clv_frame(store, path=path, as_of=KICKOFF - timedelta(minutes=5))
    assert len(frame) == 1
    assert frame["measurable"].tolist() == [False]


def test_empty_shadow_log_is_not_an_error(tmp_path):
    store = _two_event_store(tmp_path / "snaps")
    assert shadow_clv(store, path=tmp_path / "missing.jsonl") == []
    assert shadow_clv_frame(store, path=tmp_path / "missing.jsonl").empty


def test_shadow_clv_never_writes_to_the_real_bet_log(tmp_path):
    """These are hypotheticals. Mixing them into the record of real money would
    corrupt exactly what the bankroll discipline protects.
    """
    from src.store.bet_log import BET_LOG_PATH

    before = BET_LOG_PATH.exists()
    path = tmp_path / "shadow.jsonl"
    _log_a_moneyline_alert(path)
    shadow_clv(_two_event_store(tmp_path / "snaps"), path=path, as_of=NOW)
    assert BET_LOG_PATH.exists() == before


# --- revised kickoff times (2026-09-08) --------------------------------------


def test_kickoff_uses_the_latest_observed_time_not_the_largest_value(tmp_path):
    """A game moved EARLIER must not keep its stale later kickoff: the close
    window would extend past real kickoff and admit in-play quotes as the close.

    The store already holds a real revision (2026_01_NE_SEA, 00:15 -> 00:20 UTC),
    where the later value happened to be correct. This pins the opposite case.
    """
    from src.store.bet_log import _kickoff_for

    early = KICKOFF - timedelta(hours=3)
    snaps = pd.DataFrame([
        # Originally scheduled late, observed first...
        {"event_id": "E", "capture_time": NOW - timedelta(days=2), "event_start_time": KICKOFF},
        # ...then flexed EARLIER, observed most recently.
        {"event_id": "E", "capture_time": NOW - timedelta(hours=2), "event_start_time": early},
    ])
    assert _kickoff_for(snaps, "E") == early


def test_kickoff_handles_a_revision_to_a_later_time(tmp_path):
    from src.store.bet_log import _kickoff_for

    later = KICKOFF + timedelta(minutes=5)
    snaps = pd.DataFrame([
        {"event_id": "E", "capture_time": NOW - timedelta(days=2), "event_start_time": KICKOFF},
        {"event_id": "E", "capture_time": NOW - timedelta(hours=2), "event_start_time": later},
    ])
    assert _kickoff_for(snaps, "E") == later


def test_kickoff_is_none_for_an_unknown_event():
    from src.store.bet_log import _kickoff_for

    snaps = pd.DataFrame([
        {"event_id": "E", "capture_time": NOW, "event_start_time": KICKOFF},
    ])
    assert _kickoff_for(snaps, "OTHER") is None
