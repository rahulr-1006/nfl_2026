from datetime import UTC, datetime

from src.clv.seals import WK10_14_OPENS, withheld
from src.clv.shadow_clv import shadow_alerts_as_bets
from src.signal.shadow_log import append
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
