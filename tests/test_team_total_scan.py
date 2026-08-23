from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from src.signal.team_total_scan import (
    VALIDATED_TEAM_TOTAL_LIFT,
    find_team_total_spots,
    format_team_total_alert,
    team_market_probabilities,
    team_total_alert_key,
    team_total_lines_from_store,
)
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, OddsSnapshot, Side

KICKOFF = datetime(2026, 9, 20, 17, 0, tzinfo=UTC)
NOW = KICKOFF - timedelta(hours=6)


def _ml(home_price, away_price, capture=NOW, event_id="2026_03_KC_LAC"):
    return [
        OddsSnapshot.from_american(
            capture_time=capture, event_id=event_id, season=2026, week=3, home_team="LAC",
            away_team="KC", event_start_time=KICKOFF, book="pinnacle", market=Market.MONEYLINE,
            side=side, price_american=price,
        )
        for side, price in ((Side.HOME, home_price), (Side.AWAY, away_price))
    ]


def _prop(player, line, capture=NOW, event_id="2026_03_KC_LAC", stat="rushing_yards"):
    return [
        OddsSnapshot.from_american(
            capture_time=capture, event_id=event_id, season=2026, week=3, home_team="LAC",
            away_team="KC", event_start_time=KICKOFF, book="pinnacle", market=Market.PLAYER_PROP,
            side=side, price_american=-110, line=line, player_name=player, prop_stat=stat,
        )
        for side in (Side.OVER, Side.UNDER)
    ]


# --- the gate: unvalidated buckets must be skipped, not priced --------------


def test_heavy_favorite_is_skipped_because_its_bucket_never_validated(tmp_path):
    """`price_bucket_bet` raises UnvalidatedBucketError for favorite buckets --
    one collapsed +19.2%->+3.8% out-of-sample, the other flipped sign. Catching
    that (rather than passing allow_unvalidated) is the gate working.
    """
    store = PointInTimeStore(root=tmp_path)
    store.write(_ml(-600, 450) + _prop("RB1", 60.5))  # home ~86% -> heavy_favorite
    spots = find_team_total_spots(store, "rushing_yards", as_of=NOW, threshold=0.0)
    assert "home" not in set(spots.get("side", []))


def test_underdog_is_priced_because_that_bucket_survived_validation(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    store.write(_ml(-600, 450) + _prop("RB1", 60.5))  # away ~14% -> underdog
    spots = find_team_total_spots(store, "rushing_yards", as_of=NOW, threshold=0.0)
    assert not spots.empty
    assert set(spots["side"]) == {"away"}
    assert spots.iloc[0]["bucket"] == "underdog"


def test_priced_edge_matches_the_validated_underdog_lift(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    store.write(_ml(-600, 450) + _prop("RB1", 60.5))
    spot = find_team_total_spots(store, "rushing_yards", as_of=NOW, threshold=0.0).iloc[0]
    assert spot["lift"] == pytest.approx(VALIDATED_TEAM_TOTAL_LIFT["rushing_yards"]["underdog"])
    assert spot["edge"] > 0


def test_threshold_filters_weak_spots(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    store.write(_ml(-600, 450) + _prop("RB1", 60.5))
    assert find_team_total_spots(store, "rushing_yards", as_of=NOW, threshold=0.99).empty


def test_unknown_stat_raises_rather_than_inventing_a_lift(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    store.write(_ml(-600, 450) + _prop("RB1", 60.5))
    with pytest.raises(ValueError, match="no validated lift"):
        find_team_total_spots(store, "receiving_yards", as_of=NOW)


# --- live-data hygiene ------------------------------------------------------


def test_finished_games_are_excluded(tmp_path):
    """Same guard that fixed the 874-phantom-alert incident."""
    store = PointInTimeStore(root=tmp_path)
    store.write(_ml(-600, 450) + _prop("RB1", 60.5))
    after_kickoff = KICKOFF + timedelta(hours=1)
    assert find_team_total_spots(store, "rushing_yards", as_of=after_kickoff, threshold=0.0).empty


def test_only_the_latest_line_per_player_is_summed(tmp_path):
    """A line that has since moved is not what you'd be betting into."""
    store = PointInTimeStore(root=tmp_path)
    store.write(_prop("RB1", 40.5, capture=NOW - timedelta(hours=3)) + _prop("RB1", 70.5, capture=NOW))
    lines = team_total_lines_from_store(store, "rushing_yards", as_of=NOW)
    assert len(lines) == 1
    assert lines.iloc[0]["line"] == 70.5


def test_team_market_probabilities_devigs_and_covers_both_sides(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    store.write(_ml(-110, -110))
    probs = team_market_probabilities(store, as_of=NOW)
    assert set(probs["side"]) == {"home", "away"}
    assert probs["team_market_prob"].sum() == pytest.approx(1.0, abs=1e-6)  # devigged
    assert probs["team_market_prob"].iloc[0] == pytest.approx(0.5, abs=1e-6)


def test_empty_or_propless_store_returns_empty_not_a_crash(tmp_path):
    empty = PointInTimeStore(root=tmp_path / "a")
    assert find_team_total_spots(empty, "rushing_yards", as_of=NOW).empty

    ml_only = PointInTimeStore(root=tmp_path / "b")
    ml_only.write(_ml(-110, -110))
    assert find_team_total_spots(ml_only, "rushing_yards", as_of=NOW).empty


# --- alerting shape ---------------------------------------------------------


def test_alert_message_is_actionable_without_opening_a_laptop():
    row = pd.Series({
        "event_id": "2026_03_KC_LAC", "side": "away", "prop_stat": "rushing_yards",
        "bucket": "underdog", "team_market_prob": 0.14, "lift": 1.226,
        "edge": 0.055, "suggested_stake": 1.5, "n_player_lines": 4,
    })
    msg = format_team_total_alert(row)
    assert "TEAM-TOTAL" in msg and "underdog" in msg and "5.5%" in msg
    assert "2026_03_KC_LAC" in msg and "rushing_yards" in msg


def test_alert_keys_distinguish_side_and_stat():
    base = {"event_id": "G1", "bucket": "underdog"}
    a = team_total_alert_key(pd.Series({**base, "side": "home", "prop_stat": "rushing_yards"}))
    b = team_total_alert_key(pd.Series({**base, "side": "away", "prop_stat": "rushing_yards"}))
    c = team_total_alert_key(pd.Series({**base, "side": "home", "prop_stat": "passing_yards"}))
    assert len({a, b, c}) == 3
    assert a.startswith("tt|")
