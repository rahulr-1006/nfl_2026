from datetime import UTC, datetime

import pandas as pd
import pytest

from src.backtest.clv_portfolio import (
    bankroll_path,
    bets_to_frame,
    clv_by_segment,
    clv_summary,
)
from src.backtest.engine import BacktestBet
from src.store.schema import Market, Side
from src.store.settlement import Outcome

NOW = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)


def _bet(market, clv_prob, player_name=None, prop_stat=None, event_id="G1", payout=1.0, bankroll_after=101.0):
    return BacktestBet(
        event_id=event_id, decision_time=NOW, market=market, side=Side.OVER if prop_stat else Side.HOME,
        line=45.5 if prop_stat else None, book="pinnacle", stake=2.0, price_american=-110, price_decimal=1.909,
        entry_prob_fair=0.5, close_price_decimal=1.8, close_prob_fair=0.5 + (clv_prob or 0.0),
        clv_price=0.05, clv_probability=clv_prob, outcome=Outcome.WIN, payout=payout,
        player_name=player_name, prop_stat=prop_stat, bankroll_before=100.0, bankroll_after=bankroll_after,
    )


def _prop(clv_prob, **kw):
    return _bet(Market.PLAYER_PROP, clv_prob, player_name="A", prop_stat="receiving_yards", **kw)


def test_bets_to_frame_flattens_every_field_including_prop_columns():
    frame = bets_to_frame([_prop(0.01), _bet(Market.MONEYLINE, 0.02)])
    assert len(frame) == 2
    assert {"market", "player_name", "prop_stat", "clv_probability", "bankroll_after"} <= set(frame.columns)
    assert frame.iloc[0]["prop_stat"] == "receiving_yards"
    # pandas coerces None -> NaN in a mixed column; `isna` is the correct check
    assert pd.isna(frame.iloc[1]["player_name"])


def test_clv_summary_computes_mean_beat_rate_and_interval():
    summary = clv_summary([_prop(0.01), _prop(0.02), _prop(-0.01), _prop(0.03)])
    assert summary["n_total"] == 4
    assert summary["n_with_clv"] == 4
    assert summary["mean_clv"] == pytest.approx(0.0125)
    assert summary["beat_rate"] == pytest.approx(0.75)  # 3 of 4 positive
    assert summary["ci_lo"] is not None and summary["ci_hi"] is not None


def test_clv_summary_on_no_bets_returns_nulls_not_a_crash():
    summary = clv_summary([])
    assert summary["n_total"] == 0
    assert summary["mean_clv"] is None
    assert summary["beat_rate"] is None


def test_bets_without_clv_are_counted_but_excluded_from_stats():
    """A missing closing quote must show as a coverage gap, not silently
    shrink the sample it's averaged over.
    """
    summary = clv_summary([_prop(0.02), _prop(None), _prop(0.04)])
    assert summary["n_total"] == 3
    assert summary["n_with_clv"] == 2
    assert summary["mean_clv"] == pytest.approx(0.03)


def test_single_bet_reports_point_estimate_without_an_interval():
    summary = clv_summary([_prop(0.02)])
    assert summary["n_with_clv"] == 1
    assert summary["mean_clv"] == pytest.approx(0.02)
    assert summary["ci_lo"] is None and summary["ci_hi"] is None  # bootstrap needs >= 2


def test_clv_by_segment_never_pools_props_with_mainline():
    """The real reporting requirement: this project's validated edges are
    prop-adjacent, so a pooled number would answer the wrong question.
    """
    bets = [_prop(0.05), _prop(0.05), _bet(Market.MONEYLINE, -0.02), _bet(Market.MONEYLINE, -0.02)]
    by_market = clv_by_segment(bets, segment_column="market")

    assert set(by_market["market"]) == {"player_prop", "moneyline"}
    props_row = by_market[by_market["market"] == "player_prop"].iloc[0]
    main_row = by_market[by_market["market"] == "moneyline"].iloc[0]
    assert props_row["mean_clv"] == pytest.approx(0.05)
    assert main_row["mean_clv"] == pytest.approx(-0.02)
    assert props_row["beat_rate"] == 1.0
    assert main_row["beat_rate"] == 0.0


def test_clv_by_segment_supports_other_columns():
    bets = [_prop(0.05, event_id="G1"), _prop(0.01, event_id="G2")]
    by_event = clv_by_segment(bets, segment_column="event_id")
    assert set(by_event["event_id"]) == {"G1", "G2"}


def test_clv_by_segment_on_no_bets_returns_empty_frame_with_columns():
    out = clv_by_segment([])
    assert out.empty
    assert "mean_clv" in out.columns


def test_bankroll_path_preserves_settlement_order_and_does_not_resort():
    """`BacktestEngine.run` returns bets in kickoff order -- the order the
    bankroll actually accumulated in. Re-sorting by `decision_time` (the
    pre-2026-08-23 behavior) produced a non-monotone path, because a strategy
    can decide 5 days out on a late game and 1 hour out on an early one.
    """
    from datetime import timedelta

    # Settled first (kickoff earlier) but DECIDED later -- the two orders differ.
    settled_first = BacktestBet(**{**_prop(0.01).__dict__, "decision_time": NOW + timedelta(hours=5), "bankroll_after": 98.0})
    settled_second = BacktestBet(**{**_prop(0.01).__dict__, "decision_time": NOW, "bankroll_after": 96.0})

    path = bankroll_path([settled_first, settled_second])
    assert list(path["bankroll_after"]) == [98.0, 96.0]  # input (settlement) order, monotone


def test_bankroll_path_on_no_bets_returns_empty_frame_with_columns():
    """Regression: `sort_values("decision_time")` ran before the empty guard,
    so this raised KeyError on a strategy that placed no bets.
    """
    path = bankroll_path([])
    assert path.empty
    assert "bankroll_after" in path.columns


def test_clv_by_segment_counts_bets_in_a_nan_segment():
    """Regression: `frame[col] == segment` is False for every row when the
    segment key is NaN, so mainline bets (prop_stat=None) were silently
    reported as n_total=0 under the very segmentation the docstring
    advertises.
    """
    bets = [_bet(Market.MONEYLINE, 0.01), _bet(Market.MONEYLINE, 0.02), _prop(0.03)]
    by_stat = clv_by_segment(bets, segment_column="prop_stat")

    nan_row = by_stat[by_stat["prop_stat"].isna()].iloc[0]
    assert nan_row["n_total"] == 2
    assert nan_row["mean_clv"] == pytest.approx(0.015)
