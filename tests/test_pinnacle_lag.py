from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from src.backtest.pinnacle_lag import (
    detect_moves,
    pinnacle_fair_path,
    score,
    stale_quotes,
    survives_next_capture,
)
from src.devig.convert import american_to_decimal

KICKOFF = datetime(2026, 9, 20, 17, 0, tzinfo=UTC)
T0 = KICKOFF - timedelta(hours=3)


def _row(t, book, side, price, line=4.5):
    return {
        "event_id": "2026_02_KC_BUF", "player_name": "Star WR", "prop_stat": "receptions", "line": line,
        "capture_time": t, "event_start_time": KICKOFF, "book": book, "side": side,
        "price_american": price, "price_decimal": american_to_decimal(price),
    }


def _props(rows):
    return pd.DataFrame(rows)


def _pin(t, over, under, line=4.5):
    return [_row(t, "pinnacle", "over", over, line), _row(t, "pinnacle", "under", under, line)]


def test_fair_path_devigs_both_sided_captures_and_drops_one_sided_ones():
    rows = _pin(T0, -110, -110) + [_row(T0 + timedelta(minutes=15), "pinnacle", "over", -150)]
    path = pinnacle_fair_path(_props(rows))
    assert len(path) == 1
    assert path["fair_over"].iloc[0] == pytest.approx(0.5)


def test_fair_path_refuses_post_kickoff_rows():
    with pytest.raises(ValueError):
        pinnacle_fair_path(_props(_pin(KICKOFF + timedelta(minutes=1), -110, -110)))


def test_detect_moves_needs_size_and_adjacency():
    t1, t2 = T0 + timedelta(minutes=15), T0 + timedelta(minutes=60)
    rows = _pin(T0, -110, -110) + _pin(t1, -140, +120) + _pin(t2, -145, +125)
    moves = detect_moves(pinnacle_fair_path(_props(rows)), min_move=0.03)
    assert len(moves) == 1  # the 45-min gap to t2 is too wide, and that step is tiny anyway
    assert moves["side"].iloc[0] == "over"
    assert moves["capture_time"].iloc[0] == t1


def test_stale_quote_is_the_best_lagging_price_on_the_moved_side_only():
    t1 = T0 + timedelta(minutes=15)
    rows = (
        _pin(T0, -110, -110) + _pin(t1, -140, +120)
        + [_row(t1, "draftkings", "over", -110), _row(t1, "fanduel", "over", -105),
           _row(t1, "betmgm", "under", +200)]  # wrong side: never a bet
    )
    props = _props(rows)
    moves = detect_moves(pinnacle_fair_path(props), min_move=0.03)
    bets = stale_quotes(moves, props, min_ev=0.02)
    assert len(bets) == 1
    assert bets["book"].iloc[0] == "fanduel" and bets["side"].iloc[0] == "over"
    assert bets["entry_ev"].iloc[0] > 0.02


def test_stale_quotes_only_use_prices_from_the_trigger_capture():
    """A soft price seen BEFORE Pinnacle moved is not a bet on the move."""
    t1 = T0 + timedelta(minutes=15)
    rows = _pin(T0, -110, -110) + _pin(t1, -140, +120) + [_row(T0, "fanduel", "over", -105)]
    props = _props(rows)
    bets = stale_quotes(detect_moves(pinnacle_fair_path(props), min_move=0.03), props, min_ev=0.02)
    assert bets.empty


def test_one_bet_per_contract_side_even_if_pinnacle_keeps_moving():
    t1, t2 = T0 + timedelta(minutes=15), T0 + timedelta(minutes=30)
    rows = (_pin(T0, -110, -110) + _pin(t1, -140, +120) + _pin(t2, -175, +150)
            + [_row(t1, "fanduel", "over", -105), _row(t2, "fanduel", "over", -105)])
    props = _props(rows)
    bets = stale_quotes(detect_moves(pinnacle_fair_path(props), min_move=0.03), props, min_ev=0.02)
    assert len(bets) == 1 and bets["capture_time"].iloc[0] == t1


def test_score_values_the_price_paid_at_the_close_and_flags_reversals():
    t1, t2 = T0 + timedelta(minutes=15), T0 + timedelta(minutes=30)
    held = (_pin(T0, -110, -110) + _pin(t1, -140, +120) + _pin(t2, -140, +120)
            + [_row(t1, "fanduel", "over", -105)])
    props = _props(held)
    path = pinnacle_fair_path(props)
    scored = score(stale_quotes(detect_moves(path, 0.03), props, 0.02), path)
    r = scored.iloc[0]
    assert r["close_ev"] == pytest.approx(r["close_side"] * r["price_decimal"] - 1)
    assert r["clv_probability"] == pytest.approx(0.0, abs=1e-9)  # Pinnacle held: no further drift
    assert not r["reverted"]

    reverted = [x for x in held if x["capture_time"] != t2] + _pin(KICKOFF - timedelta(minutes=5), -110, -110)
    props = _props(reverted)
    path = pinnacle_fair_path(props)
    assert score(stale_quotes(detect_moves(path, 0.03), props, 0.02), path)["reverted"].iloc[0]


def test_survival_checks_the_same_book_at_its_next_capture():
    t1, t2 = T0 + timedelta(minutes=15), T0 + timedelta(minutes=30)
    rows = (_pin(T0, -110, -110) + _pin(t1, -140, +120)
            + [_row(t1, "fanduel", "over", -105), _row(t2, "fanduel", "over", -130)])
    props = _props(rows)
    bets = stale_quotes(detect_moves(pinnacle_fair_path(props), 0.03), props, 0.02)
    assert survives_next_capture(bets, props).iloc[0] == 0.0


def test_moves_outside_the_final_12h_never_trigger():
    early = KICKOFF - timedelta(hours=13)
    rows = _pin(early, -110, -110) + _pin(early + timedelta(minutes=15), -140, +120)
    assert detect_moves(pinnacle_fair_path(_props(rows)), min_move=0.03).empty
