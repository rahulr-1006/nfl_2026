from datetime import UTC, datetime

from src.clv.seals import WK5_9_OPENS, WK5_9_WEEKS, WK10_14_OPENS, seal_reason, withheld
from src.clv.shadow_clv import shadow_alerts_as_bets
from src.signal.shadow_log import append
from src.store.schema import Market, Side
from tests.test_decision_report import _obs

BEFORE = datetime(2026, 11, 20, tzinfo=UTC)


def test_only_h5_strategy_in_weeks_10_to_14_is_withheld_and_only_until_scoring():
    assert withheld("moneyline_ev", "2026_10_WAS_NYG", BEFORE)
    assert withheld("moneyline_ev", "2026_14_PIT_JAX", BEFORE)
    assert not withheld("moneyline_ev", "2026_09_KC_LV", BEFORE)   # Train week
    assert not withheld("moneyline_ev", "2026_15_KC_LV", BEFORE)   # after the holdout
    assert not withheld("steam", "2026_10_WAS_NYG", BEFORE)        # not registered
    assert not withheld("moneyline_ev", "2026_10_WAS_NYG", WK10_14_OPENS)


def test_sealed_alerts_never_reach_clv_but_lift_on_the_scoring_date(tmp_path):
    path = tmp_path / "shadow.jsonl"
    train = _obs("k1", "single", "moneyline_ev", 350, is_alert=True, minutes=0)
    holdout = _obs("k2", "single", "moneyline_ev", 400, is_alert=True, minutes=0).model_copy(
        update={"event_id": "2026_11_DAL_PHI"})
    other = _obs("k3", "single", "steam", 110, is_alert=True, minutes=0).model_copy(update={"event_id": "2026_11_DAL_PHI"})
    append([train, holdout, other], path)

    assert {b.alert_key for b in shadow_alerts_as_bets(path, now=BEFORE)} == {"k1", "k3"}
    assert {b.alert_key for b in shadow_alerts_as_bets(path, now=WK10_14_OPENS)} == {"k1", "k2", "k3"}


# --- Weeks 5-9 player props (H1/H1b) -----------------------------------------

BEFORE_WK5_9 = datetime(2026, 11, 3, tzinfo=UTC)


def test_weeks_5_to_9_player_props_are_withheld_by_market_not_strategy():
    for strategy in ("prop_ev", "prop_arb", "h1_pinnacle_lag"):
        assert withheld(strategy, "2026_05_TB_DAL", BEFORE_WK5_9, market=Market.PLAYER_PROP)
    assert withheld("prop_ev", "2026_09_KC_LV", BEFORE_WK5_9, market="player_prop")   # string form too
    assert not withheld("prop_ev", "2026_04_KC_LV", BEFORE_WK5_9, market=Market.PLAYER_PROP)   # Train
    assert not withheld("prop_ev", "2026_10_KC_LV", BEFORE_WK5_9, market=Market.PLAYER_PROP)   # after
    assert not withheld("steam", "2026_06_KC_LV", BEFORE_WK5_9, market=Market.SPREAD)          # mainline
    assert not withheld("prop_ev", "2026_05_TB_DAL", WK5_9_OPENS, market=Market.PLAYER_PROP)


def test_omitting_market_cannot_trip_the_props_seal():
    # The old two-argument call sites must keep their old meaning.
    assert not withheld("prop_ev", "2026_05_TB_DAL", BEFORE_WK5_9)


def test_seal_reasons_name_their_holdout():
    assert seal_reason("prop_ev", "2026_05_TB_DAL", Market.PLAYER_PROP, BEFORE_WK5_9).startswith("H1/H1b")
    assert seal_reason("moneyline_ev", "2026_10_WAS_NYG", Market.MONEYLINE, BEFORE).startswith("H5")
    assert seal_reason("moneyline_ev", "2026_05_TB_DAL", Market.MONEYLINE, BEFORE_WK5_9) is None


def test_props_seal_matches_the_frozen_scorer_exactly():
    # seals.py can't import these (circular), so drift is caught here instead.
    from src.clv import prereg_score

    assert WK5_9_WEEKS == prereg_score.HOLDOUT_WEEKS
    assert WK5_9_OPENS == prereg_score.SCORE_NOT_BEFORE


def test_sealed_prop_legs_never_reach_clv_but_lift_on_the_scoring_date(tmp_path):
    path = tmp_path / "shadow.jsonl"
    prop = {"market": Market.PLAYER_PROP, "side": Side.OVER, "line": 4.5,
            "player_name": "Some Receiver", "prop_stat": "receptions"}
    train = _obs("p1", "single", "prop_ev", 120, is_alert=True, minutes=0).model_copy(
        update={**prop, "event_id": "2026_04_DAL_PHI"})
    holdout = _obs("p2", "single", "prop_ev", 120, is_alert=True, minutes=0).model_copy(
        update={**prop, "event_id": "2026_07_DAL_PHI"})
    mainline = _obs("m1", "single", "steam", 110, is_alert=True, minutes=0).model_copy(
        update={"event_id": "2026_07_DAL_PHI"})
    append([train, holdout, mainline], path)

    assert {b.alert_key for b in shadow_alerts_as_bets(path, now=BEFORE_WK5_9)} == {"p1", "m1"}
    assert {b.alert_key for b in shadow_alerts_as_bets(path, now=WK5_9_OPENS)} == {"p1", "p2", "m1"}
