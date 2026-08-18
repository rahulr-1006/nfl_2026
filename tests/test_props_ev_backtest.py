import pandas as pd
import pytest

from src.backtest.props_ev_backtest import (
    find_arbitrage_spots,
    find_prop_ev_spots,
    pinnacle_fair_probs,
)
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


def test_find_arbitrage_spots_flags_a_real_cross_book_disagreement():
    # DraftKings Over +120 (implied 45.5%) + FanDuel Under +110 (implied 47.6%)
    # sums to 93.1% -- a real, hand-verified 6.9% risk-free margin.
    props = pd.DataFrame(
        [
            _row("G1", "P1", "receiving_yards", 65.5, "over", "draftkings", 120),
            _row("G1", "P1", "receiving_yards", 65.5, "under", "fanduel", 110),
        ]
    )
    spots = find_arbitrage_spots(props, books=("draftkings", "fanduel"))
    assert len(spots) == 1
    row = spots.iloc[0]
    assert row["book_over"] == "draftkings"
    assert row["book_under"] == "fanduel"
    assert row["arb_margin"] == pytest.approx(0.06926, abs=1e-4)


def test_find_arbitrage_spots_ignores_a_normal_two_sided_market():
    # Both sides at standard -110 -- implied sum > 100%, no arbitrage, as expected
    # for any competently-priced two-sided market (that's the vig).
    props = pd.DataFrame(
        [
            _row("G1", "P1", "receiving_yards", 65.5, "over", "draftkings", -110),
            _row("G1", "P1", "receiving_yards", 65.5, "under", "fanduel", -110),
        ]
    )
    spots = find_arbitrage_spots(props, books=("draftkings", "fanduel"))
    assert spots.empty


def test_find_arbitrage_spots_only_considers_the_named_execution_books():
    # A juicy Pinnacle-side price shouldn't count -- Pinnacle isn't a
    # placeable execution book, an arb needs both legs to be real bets.
    props = pd.DataFrame(
        [
            _row("G1", "P1", "receiving_yards", 65.5, "over", "pinnacle", 500),
            _row("G1", "P1", "receiving_yards", 65.5, "under", "fanduel", 110),
        ]
    )
    spots = find_arbitrage_spots(props, books=("draftkings", "fanduel"))
    assert spots.empty


def test_find_arbitrage_spots_picks_the_best_price_when_multiple_books_quote():
    props = pd.DataFrame(
        [
            _row("G1", "P1", "receiving_yards", 65.5, "over", "draftkings", 100),  # worse
            _row("G1", "P1", "receiving_yards", 65.5, "over", "betmgm", 120),  # better -- should win
            _row("G1", "P1", "receiving_yards", 65.5, "under", "fanduel", 110),
        ]
    )
    spots = find_arbitrage_spots(props, books=("draftkings", "betmgm", "fanduel"))
    assert len(spots) == 1
    assert spots.iloc[0]["book_over"] == "betmgm"
    assert spots.iloc[0]["price_american_over"] == 120
