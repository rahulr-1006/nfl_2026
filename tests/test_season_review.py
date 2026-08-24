from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from src.backtest.season_review import (
    CONTINUE,
    INSUFFICIENT,
    MONITOR,
    RETIRE,
    format_review_summary,
    review_all,
    review_strategy,
)

NOW = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)


def _frame(clv_values, market="player_prop", start=NOW, include_bet_cols=False):
    """Bets in decision order with a controlled CLV series -- lets a test dial
    in a healthy, decaying, or dead strategy.
    """
    n = len(clv_values)
    data = {
        "decision_time": [start + timedelta(hours=i) for i in range(n)],
        "market": [market] * n,
        "clv_probability": list(clv_values),
        "event_id": [f"G{i}" for i in range(n)],
    }
    if include_bet_cols:
        rng = np.random.default_rng(0)
        data |= {"fair_prob": [0.5] * n, "price_decimal": [2.0] * n, "won": rng.random(n) < 0.5}
    return pd.DataFrame(data)


# --- sample-size gating -----------------------------------------------------


def test_below_min_bets_returns_insufficient_rather_than_guessing():
    """A handful of bets cannot separate a dead edge from variance, and the cost
    of retiring a good strategy on noise is symmetric with keeping a dead one.
    """
    r = review_strategy(_frame([-0.05] * 10), min_bets=50)
    assert r.recommendation == INSUFFICIENT
    assert "10 bets" in r.reason


def test_empty_input_is_handled_not_crashed():
    r = review_strategy(pd.DataFrame())
    assert r.recommendation == INSUFFICIENT
    assert r.n_bets == 0


# --- the three real verdicts ------------------------------------------------


def test_healthy_strategy_continues():
    r = review_strategy(_frame([0.01] * 80), min_bets=50)
    assert r.recommendation == CONTINUE
    assert r.mean_clv == pytest.approx(0.01)
    assert r.clv_beat_rate == pytest.approx(1.0)
    assert not r.drift_flagged


def test_sustained_decay_with_negative_recent_clv_is_retired():
    """The case this module exists for: an edge that worked, then died."""
    r = review_strategy(_frame([0.02] * 60 + [-0.03] * 60), min_bets=50, window=25)
    assert r.drift_flagged
    assert r.recent_mean_clv < 0
    assert r.recommendation == RETIRE


def test_improving_strategy_is_not_flagged_as_drifting():
    """**The bug this module's tests caught.** With a fixed CUSUM target of 0.0,
    any consistently profitable strategy accumulates upward and trips the
    detector -- flagging the edge WORKING as if it were dying. Drift is measured
    against the strategy's own baseline, and only the downward arm counts.
    """
    r = review_strategy(_frame([0.001] * 60 + [0.05] * 60), min_bets=50, window=25)
    assert not r.drift_flagged  # improving, not decaying
    assert r.recommendation == CONTINUE


def test_partial_decay_not_yet_negative_warrants_monitoring():
    """Dropped well below baseline but the recent window is still positive --
    worth watching, not yet a retirement.
    """
    r = review_strategy(_frame([0.06] * 60 + [0.002] * 60), min_bets=50, window=25)
    assert r.drift_flagged
    assert r.recent_mean_clv > 0
    assert r.recommendation == MONITOR


def test_cold_streak_without_sustained_drift_only_warrants_monitoring():
    """A short negative run is not a dead edge; requiring BOTH signals is what
    stops variance from retiring a working strategy.
    """
    r = review_strategy(_frame([0.02] * 100 + [-0.01] * 5), min_bets=50, window=5,
                        cusum_threshold=10.0)  # threshold high enough that CUSUM cannot fire
    assert not r.drift_flagged
    assert r.recent_mean_clv < 0
    assert r.recommendation == MONITOR


# --- ordering matters for a sequential detector ------------------------------


def test_clv_series_is_ordered_by_decision_time_before_cusum():
    """CUSUM is sequential -- an unsorted series scrambles the exact pattern it
    detects, so a shuffled input must produce the same verdict as a sorted one.
    """
    frame = _frame([0.02] * 60 + [-0.03] * 60)
    shuffled = frame.sample(frac=1, random_state=3)
    assert review_strategy(shuffled, min_bets=50).recommendation == \
           review_strategy(frame, min_bets=50).recommendation


# --- segmentation -----------------------------------------------------------


def test_segments_are_reviewed_separately_so_one_cannot_mask_another():
    healthy = _frame([0.02] * 80, market="player_prop")
    dying = _frame([0.02] * 60 + [-0.04] * 60, market="moneyline")
    out = review_all(pd.concat([healthy, dying], ignore_index=True), min_bets=50)

    assert set(out["strategy"]) == {"player_prop", "moneyline"}
    assert out.set_index("strategy").loc["player_prop", "recommendation"] == CONTINUE
    assert out.set_index("strategy").loc["moneyline", "recommendation"] == RETIRE


def test_nan_segment_key_still_produces_a_row_with_its_bets():
    """`== NaN` is False for every row -- the bug already fixed in
    clv_portfolio. Segmenting on a column that is None for some bets must not
    silently empty that group.
    """
    frame = _frame([0.01] * 60)
    frame["prop_stat"] = None
    out = review_all(frame, segment_column="prop_stat", min_bets=50)
    assert len(out) == 1
    assert out.iloc[0]["n_bets"] == 60
    assert out.iloc[0]["strategy"] == "unknown"


def test_review_all_on_empty_input_returns_empty_frame_with_columns():
    out = review_all(pd.DataFrame())
    assert out.empty
    assert "recommendation" in out.columns


# --- bettability integration ------------------------------------------------


def test_bettability_is_evaluated_when_bet_columns_are_present():
    r = review_strategy(_frame([0.01] * 80, include_bet_cols=True), min_bets=50)
    assert r.roi is not None
    assert isinstance(r.bettable, bool)


def test_bettability_is_skipped_when_bet_columns_are_absent():
    """CLV-only review is still valid -- not every recorded bet carries a
    settled price/outcome yet.
    """
    r = review_strategy(_frame([0.01] * 80), min_bets=50)
    assert r.roi is None and r.bettable is False
    assert r.recommendation == CONTINUE  # still produces a real verdict


# --- reporting --------------------------------------------------------------


def test_summary_puts_actionable_rows_first():
    """Meant to be read weekly -- burying a RETIRE beneath healthy rows would
    defeat the purpose.
    """
    out = review_all(
        pd.concat([
            _frame([0.02] * 80, market="healthy"),
            _frame([0.02] * 60 + [-0.04] * 60, market="dying"),
        ], ignore_index=True),
        min_bets=50,
    )
    lines = format_review_summary(out).splitlines()
    assert "RETIRE" in lines[0]
    assert "CONTINUE" in lines[-1]


def test_summary_handles_no_bets():
    assert "No live bets" in format_review_summary(pd.DataFrame())


def test_decay_is_measured_against_the_strategys_own_baseline_not_zero():
    """Regression: two strategies with IDENTICAL shapes but different levels
    must get the same verdict. A fixed zero target made the verdict depend on
    the absolute CLV level rather than on whether anything changed.
    """
    shape = [0.02] * 60 + [0.019] * 60          # flat-ish, low level
    shifted = [x + 0.05 for x in shape]          # same shape, much higher level

    assert review_strategy(_frame(shape), min_bets=50).drift_flagged is \
           review_strategy(_frame(shifted), min_bets=50).drift_flagged


def test_no_decay_reported_before_a_baseline_can_be_established():
    """With fewer bets than the baseline window there is nothing to compare
    against; reporting decay would be inventing a comparison.
    """
    r = review_strategy(_frame([-0.05] * 20), min_bets=10, baseline_bets=30)
    assert not r.drift_flagged


def test_pending_bets_do_not_crash_the_review():
    """**Found by a paper run, 2026-08-23.** A pending bet has fair_prob=None (no
    Pinnacle anchor yet) and won=None (game not played). Once `bets_to_frame`
    started emitting those columns, `review_strategy`'s presence-check passed and
    `expected_value` raised TypeError on the None. `make season-review` would have
    crashed the first week a real pending bet sat in the log.
    """
    import pandas as pd

    from src.backtest.season_review import review_strategy

    frame = pd.DataFrame([{
        "strategy": "prop_arb", "event_id": "2026_01_SF_LA",
        "decision_time": pd.Timestamp("2026-08-23", tz="UTC"),
        "clv_probability": None, "fair_prob": None, "won": None,
        "price_decimal": 1.909, "stake": 2.0,
    }])
    r = review_strategy(frame, strategy="prop_arb")
    assert r.n_bets == 1
    assert r.roi is None and r.bettable is False
    assert r.recommendation == "insufficient_data"


def test_unmeasurable_segment_renders_na_not_nan():
    """`review_strategy` returns None for an unmeasurable strategy, but
    `review_all` builds a DataFrame and pandas coerces that None to NaN once any
    other segment has real floats. NaN passes `is not None`, so the weekly digest
    printed "+nan". Found by a paper run 2026-08-23.
    """
    import pandas as pd

    from src.backtest.season_review import format_review_summary

    reviews = pd.DataFrame([
        {"strategy": "prop_arb", "n_bets": 1, "mean_clv": float("nan"), "clv_beat_rate": None,
         "recent_mean_clv": float("nan"), "drift_flagged": False, "first_flag_index": None,
         "roi": None, "bettable": False, "recommendation": "insufficient_data",
         "reason": "1 bets < 50 needed for a verdict"},
    ])
    out = format_review_summary(reviews)
    assert "nan" not in out.lower()
    assert "n/a" in out
