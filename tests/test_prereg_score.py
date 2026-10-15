from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest

from src.clv.prereg_score import (
    HOLDOUT_WEEKS,
    SCORE_NOT_BEFORE,
    TRAIN_WEEKS,
    BlindedError,
    check_blind,
    opposite_prices,
    score_strategy,
    week_of,
)

BEFORE = datetime(2026, 10, 13, tzinfo=UTC)
AFTER = datetime(2026, 11, 10, 12, tzinfo=UTC)


def test_week_of_reads_the_nflverse_game_id():
    assert week_of("2026_05_MIN_NO") == 5
    assert week_of("2026_12_KC_LV") == 12


def test_holdout_is_locked_before_the_scoring_date():
    with pytest.raises(BlindedError):
        check_blind(HOLDOUT_WEEKS, now=BEFORE)
    # a single holdout week mixed into a train request is still refused
    with pytest.raises(BlindedError):
        check_blind((4, 5), now=BEFORE)


def test_train_is_always_scorable_and_holdout_opens_on_the_date():
    check_blind(TRAIN_WEEKS, now=BEFORE)
    check_blind(HOLDOUT_WEEKS, now=AFTER)
    check_blind(HOLDOUT_WEEKS, now=SCORE_NOT_BEFORE)


def _frame(n_games: int, per_game: int, close_ev: float, prop_stat: str = "receptions",
           entry_ev: float = 0.03, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = n_games * per_game
    price = 2.0
    close_prob = (1 + close_ev) / price
    return pd.DataFrame({
        "strategy": "h1b_stale_price",
        "event_id": [f"2026_05_G{i // per_game:02d}_X" for i in range(n)],
        "prop_stat": prop_stat,
        "price_decimal": price,
        "close_prob_fair": close_prob + rng.normal(0, 0.01, n),
        "entry_prob_fair": (1 + entry_ev) / price,
        "clv_probability": 0.0,
        "won": rng.random(n) < close_prob,
        "opposite_price_decimal": 1.8,
    }).assign(close_ev=lambda f: f["close_prob_fair"] * f["price_decimal"] - 1,
              entry_ev=lambda f: f["entry_prob_fair"] * f["price_decimal"] - 1)


def _legs(held: list[bool]) -> pd.DataFrame:
    return pd.DataFrame({"strategy": "h1b_stale_price", "minutes_to_first": 15.0, "held": held})


def test_a_clear_edge_meets_conditions_1_to_3_and_5():
    r = score_strategy(_frame(20, 3, close_ev=0.05), "h1b_stale_price", _legs([True] * 8 + [False] * 2))
    c = r["conditions"]
    assert c["1_n_and_games"] and c["2_mean_positive"] and c["3_ci_excludes_zero"] and c["5_survival"]
    assert r["n"] == 60 and r["games"] == 20


def test_condition_1_needs_15_games_not_just_30_bets():
    r = score_strategy(_frame(10, 5, close_ev=0.05), "h1b_stale_price", _legs([True] * 6))
    assert r["n"] == 50 and not r["conditions"]["1_n_and_games"]


def test_bad_quotes_and_gate_failed_stats_are_excluded_but_counted():
    good = _frame(20, 2, close_ev=0.02)
    bad = _frame(2, 1, close_ev=0.30, entry_ev=0.20, seed=1).assign(event_id=["2026_05_B1_X", "2026_05_B2_X"])
    rush = _frame(2, 1, close_ev=0.10, prop_stat="rushing_yards", seed=2).assign(event_id=["2026_05_R1_X", "2026_05_R2_X"])
    r = score_strategy(pd.concat([good, bad, rush], ignore_index=True), "h1b_stale_price", _legs([True] * 6))
    assert r["excluded_bad_quote"] == 2
    assert r["excluded_gate_failed_stat"] == 2
    assert r["n"] == 40  # neither excluded group reaches the primary metric
    assert r["mean_close_ev"] == pytest.approx(good["close_ev"].mean())


def test_survival_below_half_fails_condition_5():
    r = score_strategy(_frame(20, 2, close_ev=0.05), "h1b_stale_price", _legs([True] * 2 + [False] * 4))
    assert not r["conditions"]["5_survival"]


def test_opposite_prices_finds_the_other_side_at_the_same_book_line_and_capture():
    t = pd.Timestamp("2026-10-11 16:00", tz="UTC")
    bets = pd.DataFrame([{"event_id": "E", "player_name": "P", "prop_stat": "receptions", "line": 4.5,
                          "book": "draftkings", "side": "over", "decision_time": t}])
    snaps = pd.DataFrame([
        {"market": "player_prop", "event_id": "E", "player_name": "P", "prop_stat": "receptions", "line": 4.5,
         "book": "draftkings", "side": "under", "capture_time": t, "price_decimal": 1.83},
        # a later capture and another book must both be ignored
        {"market": "player_prop", "event_id": "E", "player_name": "P", "prop_stat": "receptions", "line": 4.5,
         "book": "draftkings", "side": "under", "capture_time": t + pd.Timedelta(minutes=15), "price_decimal": 1.70},
        {"market": "player_prop", "event_id": "E", "player_name": "P", "prop_stat": "receptions", "line": 4.5,
         "book": "fanduel", "side": "under", "capture_time": t, "price_decimal": 1.95},
    ])
    assert opposite_prices(bets, snaps).tolist() == [1.83]


def test_rushing_sensitivity_is_reported_but_never_changes_the_primary():
    good = _frame(20, 2, close_ev=0.02)
    rush = _frame(4, 1, close_ev=-0.20, prop_stat="rushing_yards", seed=2).assign(
        event_id=[f"2026_05_R{i}_X" for i in range(4)])
    legs = _legs([True] * 6)
    alone = score_strategy(good, "h1b_stale_price", legs)
    mixed = score_strategy(pd.concat([good, rush], ignore_index=True), "h1b_stale_price", legs)
    assert mixed["conditions"] == alone["conditions"]
    assert mixed["mean_close_ev"] == pytest.approx(alone["mean_close_ev"])
    g = mixed["with_gated"]
    assert g["n"] == 44 and g["games"] == 24
    assert g["mean_close_ev"] < alone["mean_close_ev"]  # the bad rushing legs show up here only
    assert g["gated_n_settled"] == 4
