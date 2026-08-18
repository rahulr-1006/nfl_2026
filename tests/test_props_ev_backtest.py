import pandas as pd
import pytest

from src.backtest.props_ev_backtest import find_prop_ev_spots, pinnacle_fair_probs
from src.devig.convert import american_to_decimal


def _row(event_id, player, stat, line, side, book, price_american):
    return {
        "event_id": event_id,
        "player_name": player,
        "prop_stat": stat,
        "line": line,
        "side": side,
        "book": book,
        "price_american": price_american,
        "price_decimal": american_to_decimal(price_american),
    }


def test_pinnacle_fair_probs_devigs_a_matched_over_under_pair():
    props = pd.DataFrame(
        [
            _row("G1", "P1", "receiving_yards", 65.5, "over", "pinnacle", -110),
            _row("G1", "P1", "receiving_yards", 65.5, "under", "pinnacle", -110),
        ]
    )
    fair = pinnacle_fair_probs(props)
    row = fair.iloc[0]
    assert row["over_fair"] == pytest.approx(0.5, abs=1e-6)
    assert row["under_fair"] == pytest.approx(0.5, abs=1e-6)
    assert row["over_fair"] + row["under_fair"] == pytest.approx(1.0)


def test_pinnacle_fair_probs_drops_mismatched_lines():
    # Over quoted at 60.5, Under at 65.5 -- not a real two-sided market, can't devig.
    props = pd.DataFrame(
        [
            _row("G1", "P1", "receiving_yards", 60.5, "over", "pinnacle", -110),
            _row("G1", "P1", "receiving_yards", 65.5, "under", "pinnacle", -110),
        ]
    )
    fair = pinnacle_fair_probs(props)
    assert fair.empty


def test_find_prop_ev_spots_flags_a_clearly_mispriced_book_price():
    props = pd.DataFrame(
        [
            _row("G1", "P1", "receiving_yards", 65.5, "over", "pinnacle", -110),
            _row("G1", "P1", "receiving_yards", 65.5, "under", "pinnacle", -110),
            # fair prob ~0.5; +150 on the Over is a huge overlay
            _row("G1", "P1", "receiving_yards", 65.5, "over", "draftkings", 150),
        ]
    )
    spots = find_prop_ev_spots(props, threshold=0.02, books=("draftkings",))
    assert len(spots) == 1
    assert spots.iloc[0]["book"] == "draftkings"
    assert spots.iloc[0]["edge"] > 0.2


def test_find_prop_ev_spots_does_not_flag_a_fairly_priced_book():
    props = pd.DataFrame(
        [
            _row("G1", "P1", "receiving_yards", 65.5, "over", "pinnacle", -110),
            _row("G1", "P1", "receiving_yards", 65.5, "under", "pinnacle", -110),
            # same -110 as Pinnacle -- no edge at a ~0.5 fair prob
            _row("G1", "P1", "receiving_yards", 65.5, "over", "draftkings", -110),
        ]
    )
    spots = find_prop_ev_spots(props, threshold=0.02, books=("draftkings",))
    assert spots.empty


def test_find_prop_ev_spots_requires_exact_line_match():
    props = pd.DataFrame(
        [
            _row("G1", "P1", "receiving_yards", 65.5, "over", "pinnacle", -110),
            _row("G1", "P1", "receiving_yards", 65.5, "under", "pinnacle", -110),
            # different line -- not a comparable bet, even though the price looks great
            _row("G1", "P1", "receiving_yards", 70.5, "over", "draftkings", 150),
        ]
    )
    spots = find_prop_ev_spots(props, threshold=0.02, books=("draftkings",))
    assert spots.empty
