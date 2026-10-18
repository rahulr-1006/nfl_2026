from datetime import UTC, datetime

import pandas as pd
import pytest

from src.clv.prereg_score import BlindedError
from src.clv.prereg_score import check_blind as check_blind_wk5
from src.clv.prereg_score_wk10 import (
    HOLDOUT_WEEKS,
    SCORE_NOT_BEFORE,
    TRAIN_WEEKS,
    check_blind,
    moneyline_opposite_prices,
)


def test_weeks_10_to_14_are_locked_until_dec_15():
    with pytest.raises(BlindedError):
        check_blind(HOLDOUT_WEEKS, now=datetime(2026, 12, 14, 23, tzinfo=UTC))
    with pytest.raises(BlindedError):
        check_blind((9, 10), now=datetime(2026, 11, 20, tzinfo=UTC))
    check_blind(HOLDOUT_WEEKS, now=SCORE_NOT_BEFORE)


def test_train_overlaps_the_wk5_9_holdout_but_only_mainlines_are_scored_here():
    # Weeks 5-9 are H5 Train: this scorer reads moneyline only, which the
    # Weeks 5-9 seal never covered, so its own lock must not refuse them...
    check_blind(TRAIN_WEEKS, now=datetime(2026, 10, 17, tzinfo=UTC))
    # ...while the Weeks 5-9 prop scorer still does.
    with pytest.raises(BlindedError):
        check_blind_wk5(TRAIN_WEEKS, now=datetime(2026, 10, 17, tzinfo=UTC))


def test_opposite_price_is_the_other_side_at_the_same_book_and_capture():
    t = pd.Timestamp("2026-10-11 16:00", tz="UTC")
    bets = pd.DataFrame([{"event_id": "E", "book": "draftkings", "side": "away", "decision_time": t}])
    snaps = pd.DataFrame([
        {"market": "moneyline", "event_id": "E", "book": "draftkings", "side": "home", "capture_time": t,
         "price_decimal": 1.30},
        {"market": "moneyline", "event_id": "E", "book": "draftkings", "side": "home",
         "capture_time": t + pd.Timedelta(minutes=10), "price_decimal": 1.25},
        {"market": "moneyline", "event_id": "E", "book": "fanduel", "side": "home", "capture_time": t,
         "price_decimal": 1.33},
        {"market": "spread", "event_id": "E", "book": "draftkings", "side": "home", "capture_time": t,
         "price_decimal": 1.91},
    ])
    assert moneyline_opposite_prices(bets, snaps).tolist() == [1.30]
