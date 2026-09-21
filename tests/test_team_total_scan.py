from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from src.signal.team_total_scan import (
    DEFAULT_EDGE_THRESHOLD,
    VALIDATED_TEAM_TOTAL_LIFT,
    find_team_total_spots,
    format_team_total_alert,
    measured_vig_by_event,
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
        "edge": 0.055, "suggested_stake": 1.5, "n_event_player_lines": 4,
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


# --- vig must be MEASURED per event, never a pooled constant ----------------
#
# `bucket_edge` divides by `(1 + vig) ** 2`, so vig enters squared. A pooled
# Pinnacle mean (6.29%) applied to a book quoting 7.80% understates the vig by
# ~1.5pp and overstates the edge by ~3pp -- in the self-flattering direction,
# which is exactly how the superseded 5.75% constant went unnoticed.


def _one_sided_prop(player, line, capture=NOW, event_id="2026_03_KC_LAC", stat="rushing_yards"):
    """Over only -- no complement, so no measurable overround."""
    return [
        OddsSnapshot.from_american(
            capture_time=capture, event_id=event_id, season=2026, week=3, home_team="LAC",
            away_team="KC", event_start_time=KICKOFF, book="pinnacle", market=Market.PLAYER_PROP,
            side=Side.OVER, price_american=-110, line=line, player_name=player, prop_stat=stat,
        )
    ]


def test_measured_vig_by_event_reads_the_real_quote(tmp_path):
    """-110/-110 is 4.76% overround by construction -- not the 6.29% constant."""
    store = PointInTimeStore(root=tmp_path)
    store.write(_ml(-110, -110) + _prop("RB1", 60.5))
    vigs = measured_vig_by_event(store, "rushing_yards", as_of=NOW)
    assert vigs["2026_03_KC_LAC"] == pytest.approx(0.047619, abs=1e-5)


def test_priced_spot_carries_the_vig_actually_measured(tmp_path):
    """-200/+170 puts the away side in the `underdog` bucket. It used to be an
    even -110/-110 line (the `narrow` bucket), which stopped producing a spot on
    2026-09-04 when the lifts were corrected from the 2023-train fit to the
    realized 2024 out-of-sample values: narrow rushing went 1.149 -> 1.045, whose
    edge at this 4.76% vig is NEGATIVE. That is the corrected constants working,
    not a regression -- so this test moved to a bucket that still prices, rather
    than loosening the threshold to keep an unprofitable bucket firing.
    """
    from src.backtest.correlated_props import MEASURED_PROP_VIG

    store = PointInTimeStore(root=tmp_path)
    store.write(_ml(-200, 170) + _prop("RB1", 60.5))
    spots = find_team_total_spots(store, "rushing_yards", as_of=NOW, threshold=0.0)
    assert not spots.empty
    assert spots.iloc[0]["vig"] == pytest.approx(0.047619, abs=1e-5)
    # The whole point: it is NOT silently the pooled constant.
    assert spots.iloc[0]["vig"] != pytest.approx(MEASURED_PROP_VIG, abs=1e-4)


def test_event_with_no_measurable_vig_is_skipped_not_assumed(tmp_path):
    """One-sided quotes carry no overround. Refuse rather than invent one --
    the same discipline as UnvalidatedBucketError.
    """
    store = PointInTimeStore(root=tmp_path)
    store.write(_ml(-110, -110) + _one_sided_prop("RB1", 60.5))
    assert measured_vig_by_event(store, "rushing_yards", as_of=NOW) == {}
    assert find_team_total_spots(store, "rushing_yards", as_of=NOW, threshold=0.0).empty


# --- the constants must stay the OUT-OF-SAMPLE fit, not the train fit --------


def test_lift_constants_are_the_realized_out_of_sample_values_not_the_train_fit():
    """Guards the 2026-09-04 correction from being silently reverted.

    The scanner priced live bets with the 2023-TRAIN lifts (rushing 1.226,
    passing 1.311) on a leakage-avoidance rationale that is right for validating
    a finding and wrong for pricing a bet: the train fit is optimistically biased,
    and this project's own out-of-sample check measured the decay. Train was also
    the highest of the three available estimates (train > pooled > realized),
    i.e. rounding toward self-flattery.

    Every value here is reproducible from raw data via
    `team_total_props.fit_team_total_lift_by_bucket(..., seasons=[2024])`.
    """
    assert VALIDATED_TEAM_TOTAL_LIFT == {
        "rushing_yards": {"underdog": 1.167, "narrow": 1.045},
        "passing_yards": {"underdog": 1.216, "narrow": 0.943},
    }
    train_fit = {"rushing_yards": 1.226, "passing_yards": 1.311}
    for stat, train in train_fit.items():
        assert VALIDATED_TEAM_TOTAL_LIFT[stat]["underdog"] < train


def test_only_passing_underdog_clears_the_threshold_at_realistic_vig():
    """The practical consequence, pinned so it is visible rather than inferred:
    at the vig actually measured live (6.54%), the corrected lifts leave exactly
    ONE firing bucket. Under the train fit both stats fired, which is what made
    the scanner project ~36 spots/week once Pinnacle broadens.
    """
    from src.backtest.correlated_props import bucket_edge

    vig = 0.0654
    firing = {
        (stat, bucket)
        for stat, buckets in VALIDATED_TEAM_TOTAL_LIFT.items()
        for bucket, lift in buckets.items()
        if bucket_edge(lift, vig) >= DEFAULT_EDGE_THRESHOLD
    }
    assert firing == {("passing_yards", "underdog")}
