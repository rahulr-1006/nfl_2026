from datetime import UTC, datetime, timedelta

from src.notify.health_check import (
    check_all,
    check_collector_health,
    check_props_write_freshness,
    market_write_freshness,
    pinnacle_arrival_message,
    prop_book_coverage,
    unhealthy_messages,
)
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, OddsSnapshot, Side

NOW = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)


def _snap(capture, kickoff, market=Market.MONEYLINE, side=Side.HOME, price=-110):
    return OddsSnapshot.from_american(
        capture_time=capture, event_id="2026_01_KC_LAC", season=2026, week=1,
        home_team="LAC", away_team="KC", event_start_time=kickoff,
        book="pinnacle", market=market, side=side, price_american=price,
        line=45.5 if market == Market.PLAYER_PROP else None,
        player_name="A" if market == Market.PLAYER_PROP else None,
        prop_stat="receiving_yards" if market == Market.PLAYER_PROP else None,
    )


def _store(tmp_path, snaps):
    s = PointInTimeStore(root=tmp_path)
    s.write(snaps)
    return s


# --- empty store ------------------------------------------------------------


def test_empty_store_is_unhealthy_and_reported_not_raised():
    """This runs unattended -- it must not become its own failure mode."""
    r = check_collector_health(PointInTimeStore(root="/tmp/definitely-not-a-store-xyz"), now=NOW)
    assert not r["healthy"]
    assert "empty" in r["message"]


# --- proximity-aware thresholds: the core design point ----------------------


def test_fresh_write_near_kickoff_is_healthy(tmp_path):
    kickoff = NOW + timedelta(hours=3)  # well inside the dense window
    r = check_collector_health(_store(tmp_path, [_snap(NOW - timedelta(hours=1), kickoff)]), now=NOW)
    assert r["healthy"] and r["near_kickoff"]


def test_stale_write_near_kickoff_alerts(tmp_path):
    """A 10h silence with a kickoff 3h away is a real outage -- entry prices
    lost here can never be recovered, since CLV needs an entry price.
    """
    kickoff = NOW + timedelta(hours=3)
    r = check_collector_health(_store(tmp_path, [_snap(NOW - timedelta(hours=10), kickoff)]), now=NOW)
    assert not r["healthy"]
    assert r["near_kickoff"]
    assert "ALERT" in r["message"]


def test_same_silence_is_tolerated_when_no_kickoff_is_near(tmp_path):
    """The whole reason the threshold is proximity-aware: 10h of silence during
    a quiet week is ordinary budget throttling, not an outage. A single fixed
    threshold cannot serve both cases.
    """
    kickoff = NOW + timedelta(days=20)  # far outside the dense window
    r = check_collector_health(_store(tmp_path, [_snap(NOW - timedelta(hours=10), kickoff)]), now=NOW)
    assert r["healthy"]
    assert not r["near_kickoff"]


def test_the_real_58_hour_gap_would_have_alerted(tmp_path):
    """Regression against reality: live collection actually went 58.2h without a
    write and nothing noticed. That must alert even in the quiet-week regime.
    """
    kickoff = NOW + timedelta(days=20)
    r = check_collector_health(_store(tmp_path, [_snap(NOW - timedelta(hours=58.2), kickoff)]), now=NOW)
    assert not r["healthy"]


def test_thresholds_are_overridable(tmp_path):
    kickoff = NOW + timedelta(days=20)
    store = _store(tmp_path, [_snap(NOW - timedelta(hours=10), kickoff)])
    assert not check_collector_health(store, now=NOW, max_silence_otherwise=timedelta(hours=2))["healthy"]


def test_past_only_games_do_not_count_as_near_kickoff(tmp_path):
    """With no upcoming games there is nothing to be near, so the loose
    threshold applies -- otherwise the offseason would page constantly.
    """
    kickoff = NOW - timedelta(days=1)
    r = check_collector_health(_store(tmp_path, [_snap(NOW - timedelta(hours=10), kickoff)]), now=NOW)
    assert not r["near_kickoff"]
    assert r["healthy"]


# --- aggregation ------------------------------------------------------------


def test_unhealthy_messages_filters_to_problems_only(tmp_path):
    kickoff = NOW + timedelta(hours=3)
    healthy = check_all(_store(tmp_path, [_snap(NOW - timedelta(minutes=10), kickoff)]), now=NOW)
    assert unhealthy_messages(healthy) == []

    stale = check_all(_store(tmp_path / "b", [_snap(NOW - timedelta(hours=20), kickoff)]), now=NOW)
    assert len(unhealthy_messages(stale)) == 1


# --- per-market diagnostic --------------------------------------------------


def test_market_freshness_exposes_one_dead_market_behind_a_healthy_aggregate(tmp_path):
    """The mainline and props collectors are separate services writing to the
    same store -- props can die while moneyline keeps the aggregate timestamp
    fresh, which the top-level check cannot see.
    """
    kickoff = NOW + timedelta(hours=5)
    store = _store(tmp_path, [
        _snap(NOW - timedelta(minutes=5), kickoff, Market.MONEYLINE),
        _snap(NOW - timedelta(minutes=5), kickoff, Market.MONEYLINE, Side.AWAY, 120),
        _snap(NOW - timedelta(hours=40), kickoff, Market.PLAYER_PROP, Side.OVER),
    ])
    out = market_write_freshness(store, now=NOW)

    assert check_collector_health(store, now=NOW)["healthy"]  # aggregate looks fine...
    stale = out.set_index("market").loc["player_prop", "hours_ago"]
    assert stale > 39  # ...while props is 40h dead
    assert next(iter(out["market"])) == "moneyline"  # freshest first


def test_market_freshness_on_empty_store_returns_empty_frame():
    out = market_write_freshness(PointInTimeStore(root="/tmp/definitely-not-a-store-xyz"))
    assert out.empty
    assert "hours_ago" in out.columns


# --- Pinnacle arrival: the state change that switches three capabilities on ---


def _prop(book, capture, kickoff, side=Side.OVER, price=-110):
    return OddsSnapshot.from_american(
        capture_time=capture, event_id="2026_01_KC_LAC", season=2026, week=1,
        home_team="LAC", away_team="KC", event_start_time=kickoff, book=book,
        market=Market.PLAYER_PROP, side=side, price_american=price, line=45.5,
        player_name="Star Receiver", prop_stat="receiving_yards",
    )


def test_coverage_reports_pinnacle_absent_with_the_books_that_are_quoting(tmp_path):
    """The real state on 2026-08-23: FanDuel/BetRivers quoting the opener 17
    days out, Pinnacle not yet.
    """
    kickoff = NOW + timedelta(days=17)
    store = _store(tmp_path, [_prop("fanduel", NOW, kickoff), _prop("betrivers", NOW, kickoff)])
    cov = prop_book_coverage(store, now=NOW)

    assert cov["pinnacle_present"] is False
    assert cov["books"] == ["betrivers", "fanduel"]
    assert cov["n_prop_rows"] == 2 and cov["n_games"] == 1
    assert pinnacle_arrival_message(cov) is None  # nothing to announce yet


def test_coverage_detects_pinnacle_and_produces_the_announcement(tmp_path):
    kickoff = NOW + timedelta(days=17)
    store = _store(tmp_path, [_prop("fanduel", NOW, kickoff), _prop("pinnacle", NOW, kickoff)])
    cov = prop_book_coverage(store, now=NOW)

    assert cov["pinnacle_present"] is True
    msg = pinnacle_arrival_message(cov)
    assert "PINNACLE NOW QUOTING" in msg
    assert "anchored EV" in msg  # says WHAT switched on, not just that something did


def test_coverage_ignores_props_on_games_already_played(tmp_path):
    """The historical backfill lives in the same store; a 2023 Pinnacle prop
    must not read as "Pinnacle is quoting now".
    """
    past_kick = NOW - timedelta(days=2)
    store = _store(tmp_path, [_prop("pinnacle", past_kick - timedelta(hours=2), past_kick)])
    assert prop_book_coverage(store, now=NOW)["pinnacle_present"] is False


def test_coverage_on_a_store_with_no_props_is_empty_not_a_crash(tmp_path):
    kickoff = NOW + timedelta(hours=5)
    store = _store(tmp_path, [_snap(NOW, kickoff, Market.MONEYLINE)])
    cov = prop_book_coverage(store, now=NOW)
    assert cov["pinnacle_present"] is False and cov["books"] == []


# --- props write freshness: the gap the aggregate check cannot see -----------
#
# Props and mainline are separate launchd services writing to one store, so a
# dead props service leaves the store-wide timestamp fresh and the aggregate
# check reporting OK. These tests pin that the props check sees what the
# aggregate one structurally cannot.


def _prop_snap(capture, kickoff, event_id="2026_01_KC_LAC", book="fanduel", player="A"):
    return OddsSnapshot.from_american(
        capture_time=capture, event_id=event_id, season=2026, week=1,
        home_team="LAC", away_team="KC", event_start_time=kickoff,
        book=book, market=Market.PLAYER_PROP, side=Side.OVER, price_american=-110,
        line=45.5, player_name=player, prop_stat="receiving_yards",
    )


def test_no_upcoming_props_is_healthy_not_an_alert(tmp_path):
    """Books post props on their own schedule -- the 2026 opener posted 17 days
    out. Before that, no amount of healthy polling produces a prop row, so
    silence must not page.
    """
    kickoff = NOW + timedelta(hours=3)
    r = check_props_write_freshness(_store(tmp_path, [_snap(NOW - timedelta(hours=1), kickoff)]), now=NOW)
    assert r["healthy"]
    assert "not posted" in r["message"]


def test_historical_backfill_cannot_pass_as_live_collector_activity(tmp_path):
    """The 2023-24 prop backfill carries ~1.5-year-old capture_times in the same
    store. Reading it as a live write is the exact confusion that once fired
    874 of 879 alerts on already-played games.
    """
    old = datetime(2024, 11, 1, tzinfo=UTC)
    store = _store(tmp_path, [
        _prop_snap(old, old + timedelta(hours=3), event_id="2024_09_SF_SEA"),
        _snap(NOW - timedelta(hours=1), NOW + timedelta(hours=3)),
    ])
    r = check_props_write_freshness(store, now=NOW)
    # The backfill row is not upcoming, so it is invisible here -- and crucially
    # this reports "nothing to collect", never a fresh-looking last_write.
    assert r["healthy"]
    assert r["last_write"] is None


def test_dead_props_service_alerts_while_aggregate_check_says_ok(tmp_path):
    """The whole point. Mainline keeps writing; props stopped 20h ago with a
    kickoff 3h away. The aggregate check sees only the fresh mainline write.
    """
    kickoff = NOW + timedelta(hours=3)
    store = _store(tmp_path, [
        _prop_snap(NOW - timedelta(hours=20), kickoff),
        _snap(NOW - timedelta(minutes=20), kickoff),
    ])
    assert check_collector_health(store, now=NOW)["healthy"]
    r = check_props_write_freshness(store, now=NOW)
    assert not r["healthy"]
    assert r["tier"] == "dense"


def test_fresh_props_write_near_kickoff_is_healthy(tmp_path):
    kickoff = NOW + timedelta(hours=3)
    r = check_props_write_freshness(_store(tmp_path, [_prop_snap(NOW - timedelta(hours=2), kickoff)]), now=NOW)
    assert r["healthy"] and r["tier"] == "dense"


def test_thresholds_loosen_with_distance_from_kickoff(tmp_path):
    """A 20h silence is an outage inside 48h and entirely normal 10 days out,
    where the collector only probes every 72h. One constant cannot do both.
    """
    silence = timedelta(hours=20)
    dense = _store(tmp_path / "d", [_prop_snap(NOW - silence, NOW + timedelta(hours=3))])
    early = _store(tmp_path / "e", [_prop_snap(NOW - silence, NOW + timedelta(days=10))])
    assert not check_props_write_freshness(dense, now=NOW)["healthy"]
    assert check_props_write_freshness(early, now=NOW)["healthy"]
    assert check_props_write_freshness(early, now=NOW)["tier"] == "early"


def test_early_tier_still_alerts_on_a_genuinely_dead_collector(tmp_path):
    """Loose is not the same as off -- 6 days of silence 10 days out is real."""
    store = _store(tmp_path, [_prop_snap(NOW - timedelta(days=6), NOW + timedelta(days=10))])
    assert not check_props_write_freshness(store, now=NOW)["healthy"]


def test_check_all_runs_both_checks_and_surfaces_the_props_alert(tmp_path):
    """Wiring test: monitor_run texts whatever `unhealthy_messages(check_all())`
    returns, so a props alert only reaches the phone if check_all carries it.
    """
    kickoff = NOW + timedelta(hours=3)
    store = _store(tmp_path, [
        _prop_snap(NOW - timedelta(hours=20), kickoff),
        _snap(NOW - timedelta(minutes=20), kickoff),
    ])
    results = check_all(store, now=NOW)
    assert len(results) == 2
    msgs = unhealthy_messages(results)
    assert len(msgs) == 1 and "props collector" in msgs[0]
