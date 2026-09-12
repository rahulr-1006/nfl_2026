import math
from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from src.backtest.middling import (
    MiddleOpportunity,
    best_middle_for_game,
    find_middle_opportunities,
    line_threshold,
    middle_ev,
    middle_window,
    pinnacle_reference_line,
    win_interval,
)
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, OddsSnapshot, Side
from src.store.settlement import GameResult as SettlementGameResult
from src.store.settlement import settle as settlement_settle

CAPTURE_TIME = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
EVENT_START = datetime(2026, 9, 13, 17, 0, tzinfo=UTC)


def _snapshot(
    book, market, side, price_american, line=None, capture_time=CAPTURE_TIME, event_id="2026_01_NE_SEA"
) -> OddsSnapshot:
    return OddsSnapshot.from_american(
        capture_time=capture_time,
        event_id=event_id,
        season=2026,
        week=1,
        home_team="SEA",
        away_team="NE",
        event_start_time=EVENT_START,
        book=book,
        market=market,
        side=side,
        price_american=price_american,
        line=line,
    )


# --- win_interval: the sign-convention anchor, cross-checked against settle() ---


@pytest.mark.parametrize(
    "line,home_score,away_score,expected_home_outcome",
    [
        (-3.0, 24, 20, "win"),  # home won by 4, more than the 3-point line -> covers
        (-3.0, 23, 21, "loss"),  # home won by only 2, less than 3 -> doesn't cover
        (-3.0, 20, 24, "loss"),  # home lost outright -> doesn't cover
        (3.5, 22, 24, "win"),  # home a 3.5-point dog, lost by only 2 -> covers
        (3.5, 17, 24, "loss"),  # home lost by 7, more than 3.5 -> doesn't cover
    ],
)
def test_win_interval_home_matches_settle_on_real_scores(line, home_score, away_score, expected_home_outcome):
    result = SettlementGameResult(event_id="x", home_score=home_score, away_score=away_score)
    actual = settlement_settle(Market.SPREAD, Side.HOME, line, result)
    assert actual.value != "push"  # none of the fixtures above land on a push
    assert actual.value == expected_home_outcome

    lo, hi = win_interval(Market.SPREAD, Side.HOME, line)
    home_margin = home_score - away_score
    in_interval = lo < home_margin < hi
    assert in_interval == (expected_home_outcome == "win")


@pytest.mark.parametrize("home_margin", range(-10, 11))
def test_win_interval_spread_matches_settle_across_a_full_margin_grid(home_margin):
    # Exhaustive cross-check, not just hand-picked examples: for a real
    # mirrored home/away quote (-3.0 / +3.0), walk every integer
    # home_margin from -10 to 10 and confirm win_interval's membership
    # test agrees with settle()'s own grading for BOTH sides, skipping
    # exact-line pushes (win_interval has no push concept, it's an open
    # interval). Each side is graded against its OWN real line -- away's
    # line is the mirror of home's, not the same raw number, exactly as a
    # real book would quote it.
    line_home, line_away = -3.0, 3.0
    away_score, home_score = 0, home_margin  # away_score=0 makes home_margin == home_score - away_score directly
    result = SettlementGameResult(event_id="x", home_score=home_score, away_score=away_score)

    home_outcome = settlement_settle(Market.SPREAD, Side.HOME, line_home, result)
    lo, hi = win_interval(Market.SPREAD, Side.HOME, line_home)
    if home_outcome.value != "push":
        assert (lo < home_margin < hi) == (home_outcome.value == "win")

    away_outcome = settlement_settle(Market.SPREAD, Side.AWAY, line_away, result)
    lo, hi = win_interval(Market.SPREAD, Side.AWAY, line_away)
    # win_interval's coordinate space is home_margin throughout (see its
    # docstring) -- AWAY's own interval is expressed in that same space,
    # NOT a separately negated "away_margin", so the value under test here
    # is still home_margin.
    if away_outcome.value != "push":
        assert (lo < home_margin < hi) == (away_outcome.value == "win")


@pytest.mark.parametrize("total_score", range(30, 55))
def test_win_interval_total_matches_settle_across_a_full_total_grid(total_score):
    line = 42.0
    home_score, away_score = total_score, 0
    result = SettlementGameResult(event_id="x", home_score=home_score, away_score=away_score)

    for side in (Side.OVER, Side.UNDER):
        outcome = settlement_settle(Market.TOTAL, side, line, result)
        lo, hi = win_interval(Market.TOTAL, side, line)
        if outcome.value == "push":
            continue
        assert (lo < total_score < hi) == (outcome.value == "win")


def test_win_interval_rejects_unsupported_markets():
    with pytest.raises(ValueError):
        win_interval(Market.MONEYLINE, Side.HOME, None)
    with pytest.raises(ValueError):
        win_interval(Market.PLAYER_PROP, Side.OVER, 10.5)


def test_win_interval_rejects_mismatched_side_for_market():
    with pytest.raises(ValueError):
        win_interval(Market.SPREAD, Side.OVER, -3.0)
    with pytest.raises(ValueError):
        win_interval(Market.TOTAL, Side.HOME, 42.0)


@pytest.mark.parametrize(
    "market,side,worse_line,better_line,bound_index",
    [
        # bound_index: which side of (lo, hi) is the FINITE, line-dependent
        # one for this side -- HOME/OVER have a finite lo (index 0) and an
        # infinite hi; AWAY/UNDER have a finite hi (index 1) and an
        # infinite lo. HOME/OVER are "better" with a SMALLER finite bound;
        # AWAY/UNDER are "better" with a LARGER one -- both intervals are
        # half-infinite, so "width" isn't a usable comparison (always inf);
        # the finite bound's own direction is what best_middle_for_game's
        # _best_line actually relies on.
        (Market.SPREAD, Side.HOME, -7.0, -3.0, 0),  # a smaller favorite is a better number for the bettor
        (Market.SPREAD, Side.AWAY, -3.0, 3.0, 1),  # more points is better for the underdog bettor
        (Market.TOTAL, Side.OVER, 47.0, 42.0, 0),  # a lower total needed is easier to clear
        (Market.TOTAL, Side.UNDER, 42.0, 47.0, 1),  # a higher total allowed is easier to stay under
    ],
)
def test_win_interval_is_monotonic_in_line(market, side, worse_line, better_line, bound_index):
    worse = win_interval(market, side, worse_line)
    better = win_interval(market, side, better_line)
    assert math.isinf(worse[1 - bound_index]) and math.isinf(better[1 - bound_index])

    if bound_index == 0:  # HOME/OVER: a smaller finite lower bound is more favorable
        assert better[0] < worse[0]
    else:  # AWAY/UNDER: a larger finite upper bound is more favorable
        assert better[1] > worse[1]


# --- line_threshold ---


def test_line_threshold_agrees_across_mirrored_spread_sides():
    assert line_threshold(Market.SPREAD, Side.HOME, -3.0) == pytest.approx(3.0)
    assert line_threshold(Market.SPREAD, Side.AWAY, 3.0) == pytest.approx(3.0)


def test_line_threshold_agrees_across_mirrored_total_sides():
    assert line_threshold(Market.TOTAL, Side.OVER, 47.0) == pytest.approx(47.0)
    assert line_threshold(Market.TOTAL, Side.UNDER, 47.0) == pytest.approx(47.0)


# --- middle_window ---


def test_middle_window_from_real_line_movement():
    # Home moved from -3 (early) to -7 (late) -- classic middle: bet HOME
    # at -3, bet AWAY at +7 (the mirror of -7). Window should be (3, 7).
    window = middle_window(Market.SPREAD, Side.HOME, -3.0, Side.AWAY, 7.0)
    assert window == (3.0, 7.0)


def test_middle_window_none_for_unchanged_mirrored_line():
    # No real movement -- home -3 / away +3 at the same implied number
    # gives a zero-width, non-existent window. Betting both sides of an
    # unchanged line is just a guaranteed vig loss, not a middle.
    assert middle_window(Market.SPREAD, Side.HOME, -3.0, Side.AWAY, 3.0) is None


def test_middle_window_none_for_wrong_direction_movement():
    # Home moved the "wrong" way for this pairing (-3 -> more favorable -7
    # picked on the wrong sides) -- pairing HOME's *worse* early line with
    # AWAY's *worse* late line should not produce a window.
    assert middle_window(Market.SPREAD, Side.HOME, -7.0, Side.AWAY, 3.0) is None


def test_middle_window_none_for_same_side_pair():
    assert middle_window(Market.SPREAD, Side.HOME, -3.0, Side.HOME, -7.0) is None


def test_middle_window_total_from_real_line_movement():
    # Total moved up from 47 to 51 -- bet OVER 47 early, UNDER 51 late.
    window = middle_window(Market.TOTAL, Side.OVER, 47.0, Side.UNDER, 51.0)
    assert window == (47.0, 51.0)


def test_middle_window_rejects_cross_market_side_mismatch():
    with pytest.raises(ValueError):
        middle_window(Market.TOTAL, Side.HOME, -3.0, Side.AWAY, 3.0)


# --- MiddleOpportunity ---


def test_middle_opportunity_rejects_an_invalid_window():
    with pytest.raises(ValueError):
        MiddleOpportunity(
            event_id="x",
            market=Market.SPREAD,
            side_a=Side.HOME,
            line_a=-3.0,
            price_decimal_a=1.91,
            book_a="fanduel",
            capture_time_a=CAPTURE_TIME,
            side_b=Side.AWAY,
            line_b=3.0,
            price_decimal_b=1.91,
            book_b="draftkings",
            capture_time_b=CAPTURE_TIME,
            window_lo=5.0,
            window_hi=5.0,  # not lo < hi
        )


def test_middle_opportunity_window_width():
    opp = MiddleOpportunity(
        event_id="x",
        market=Market.SPREAD,
        side_a=Side.HOME,
        line_a=-3.0,
        price_decimal_a=1.91,
        book_a="fanduel",
        capture_time_a=CAPTURE_TIME,
        side_b=Side.AWAY,
        line_b=7.0,
        price_decimal_b=1.87,
        book_b="draftkings",
        capture_time_b=CAPTURE_TIME + timedelta(days=3),
        window_lo=3.0,
        window_hi=7.0,
    )
    assert opp.window_width == pytest.approx(4.0)


# --- best_middle_for_game ---


def _spread_df(rows: list[dict]) -> pd.DataFrame:
    """rows: dicts with book/side/line/price_decimal/capture_time -- builds
    a minimal frame shaped like a real PointInTimeStore read, restricted to
    the columns best_middle_for_game actually touches."""
    base = {"event_id": "2026_01_NE_SEA"}
    return pd.DataFrame([{**base, **r} for r in rows])


def test_best_middle_for_game_picks_the_best_vs_best_pairing_not_first_row():
    df = _spread_df(
        [
            {"book": "fanduel", "side": "home", "line": -3.0, "price_decimal": 1.91, "capture_time": CAPTURE_TIME},
            {"book": "draftkings", "side": "home", "line": -7.0, "price_decimal": 1.95, "capture_time": CAPTURE_TIME + timedelta(days=2)},
            # best home line is -3.0 (the least negative) even though it's not the last row
            {"book": "fanduel", "side": "away", "line": 3.0, "price_decimal": 1.91, "capture_time": CAPTURE_TIME},
            {"book": "betmgm", "side": "away", "line": 7.0, "price_decimal": 1.87, "capture_time": CAPTURE_TIME + timedelta(days=3)},
            # best away line is +7.0
        ]
    )
    opp = best_middle_for_game(df, Market.SPREAD)
    assert opp is not None
    assert opp.line_a == pytest.approx(-3.0)
    assert opp.book_a == "fanduel"
    assert opp.line_b == pytest.approx(7.0)
    assert opp.book_b == "betmgm"
    assert (opp.window_lo, opp.window_hi) == (3.0, 7.0)


def test_best_middle_for_game_breaks_line_ties_on_best_price():
    df = _spread_df(
        [
            {"book": "fanduel", "side": "home", "line": -3.0, "price_decimal": 1.85, "capture_time": CAPTURE_TIME},
            # same home line, better price -- must win the tie-break
            {"book": "draftkings", "side": "home", "line": -3.0, "price_decimal": 1.95, "capture_time": CAPTURE_TIME},
            {"book": "fanduel", "side": "away", "line": 7.0, "price_decimal": 1.87, "capture_time": CAPTURE_TIME + timedelta(days=3)},
        ]
    )
    opp = best_middle_for_game(df, Market.SPREAD)
    assert opp is not None
    assert opp.book_a == "draftkings"
    assert opp.price_decimal_a == pytest.approx(1.95)


def test_best_middle_for_game_none_when_one_side_missing():
    df = _spread_df([{"book": "fanduel", "side": "home", "line": -3.0, "price_decimal": 1.91, "capture_time": CAPTURE_TIME}])
    assert best_middle_for_game(df, Market.SPREAD) is None


def test_best_middle_for_game_none_when_no_real_movement():
    df = _spread_df(
        [
            {"book": "fanduel", "side": "home", "line": -3.0, "price_decimal": 1.91, "capture_time": CAPTURE_TIME},
            {"book": "draftkings", "side": "away", "line": 3.0, "price_decimal": 1.91, "capture_time": CAPTURE_TIME},
        ]
    )
    assert best_middle_for_game(df, Market.SPREAD) is None


def test_best_middle_for_game_total_market():
    df = _spread_df(
        [
            {"book": "fanduel", "side": "over", "line": 47.0, "price_decimal": 1.91, "capture_time": CAPTURE_TIME},
            {"book": "betmgm", "side": "over", "line": 49.0, "price_decimal": 1.91, "capture_time": CAPTURE_TIME + timedelta(days=1)},
            {"book": "draftkings", "side": "under", "line": 51.0, "price_decimal": 1.87, "capture_time": CAPTURE_TIME + timedelta(days=3)},
        ]
    )
    opp = best_middle_for_game(df, Market.TOTAL)
    assert opp is not None
    assert opp.line_a == pytest.approx(47.0)  # best (lowest) over line
    assert opp.line_b == pytest.approx(51.0)
    assert (opp.window_lo, opp.window_hi) == (47.0, 51.0)


def test_best_middle_for_game_ignores_rows_with_no_line():
    df = _spread_df(
        [
            {"book": "fanduel", "side": "home", "line": None, "price_decimal": 1.91, "capture_time": CAPTURE_TIME},
            {"book": "draftkings", "side": "home", "line": -3.0, "price_decimal": 1.91, "capture_time": CAPTURE_TIME},
            {"book": "fanduel", "side": "away", "line": 7.0, "price_decimal": 1.87, "capture_time": CAPTURE_TIME + timedelta(days=3)},
        ]
    )
    opp = best_middle_for_game(df, Market.SPREAD)
    assert opp is not None
    assert opp.book_a == "draftkings"


# --- pinnacle_reference_line ---


def test_pinnacle_reference_line_averages_both_sides():
    df = _spread_df(
        [
            {"book": "pinnacle", "side": "home", "line": -3.5, "price_decimal": 1.91, "capture_time": CAPTURE_TIME, "market": "spread"},
            {"book": "pinnacle", "side": "away", "line": 3.0, "price_decimal": 1.95, "capture_time": CAPTURE_TIME, "market": "spread"},
        ]
    )
    mu = pinnacle_reference_line(df, Market.SPREAD)
    # thresholds: home -3.5 -> 3.5, away 3.0 -> 3.0, average = 3.25
    assert mu == pytest.approx(3.25)


def test_pinnacle_reference_line_uses_only_the_latest_snapshot():
    df = _spread_df(
        [
            {"book": "pinnacle", "side": "home", "line": -10.0, "price_decimal": 1.91, "capture_time": CAPTURE_TIME, "market": "spread"},
            {"book": "pinnacle", "side": "away", "line": 10.0, "price_decimal": 1.91, "capture_time": CAPTURE_TIME, "market": "spread"},
            # a later, real move -- the stale -10 row above must not be averaged in
            {"book": "pinnacle", "side": "home", "line": -3.0, "price_decimal": 1.91, "capture_time": CAPTURE_TIME + timedelta(days=2), "market": "spread"},
            {"book": "pinnacle", "side": "away", "line": 3.0, "price_decimal": 1.91, "capture_time": CAPTURE_TIME + timedelta(days=2), "market": "spread"},
        ]
    )
    mu = pinnacle_reference_line(df, Market.SPREAD)
    assert mu == pytest.approx(3.0)


def test_pinnacle_reference_line_none_when_pinnacle_absent():
    df = _spread_df(
        [{"book": "fanduel", "side": "home", "line": -3.0, "price_decimal": 1.91, "capture_time": CAPTURE_TIME, "market": "spread"}]
    )
    assert pinnacle_reference_line(df, Market.SPREAD) is None


# --- middle_ev ---


def _opp(window_lo=3.0, window_hi=7.0, price_a=1.91, price_b=1.87) -> MiddleOpportunity:
    return MiddleOpportunity(
        event_id="2026_01_NE_SEA",
        market=Market.SPREAD,
        side_a=Side.HOME,
        line_a=-3.0,
        price_decimal_a=price_a,
        book_a="fanduel",
        capture_time_a=CAPTURE_TIME,
        side_b=Side.AWAY,
        line_b=7.0,
        price_decimal_b=price_b,
        book_b="draftkings",
        capture_time_b=CAPTURE_TIME + timedelta(days=3),
        window_lo=window_lo,
        window_hi=window_hi,
    )


def test_middle_ev_probabilities_sum_to_one():
    opp = _opp()
    result = middle_ev(opp, mu=3.0, sigma=13.0, stake_a=2.0, stake_b=2.0)
    total = result["p_both_win"] + result["p_a_only"] + result["p_b_only"] + result["p_neither"]
    assert total == pytest.approx(1.0)


@pytest.mark.parametrize("mu,sigma", [(3.0, 13.0), (-10.0, 8.0), (20.0, 20.0), (5.0, 0.5)])
def test_middle_ev_never_loses_both_legs(mu, sigma):
    # The structural guarantee this whole strategy depends on: a real
    # middle (opposite sides, valid window) can never lose both legs at
    # once, for ANY true-outcome distribution. p_neither must be ~0
    # regardless of where mu/sigma put the probability mass.
    opp = _opp()
    result = middle_ev(opp, mu=mu, sigma=sigma, stake_a=2.0, stake_b=2.0)
    assert result["p_neither"] == pytest.approx(0.0, abs=1e-9)


def test_middle_ev_matches_hand_computation():
    opp = _opp(price_a=1.91, price_b=1.87)
    mu, sigma = 5.0, 2.0
    result = middle_ev(opp, mu=mu, sigma=sigma, stake_a=2.0, stake_b=2.0)

    from scipy.stats import norm

    p_win_a = 1 - norm.cdf(-3.0, loc=mu, scale=sigma)  # HOME wins if margin > -(-3)=... win_interval(HOME,-3)=(3,inf)
    p_win_a = 1 - norm.cdf(3.0, loc=mu, scale=sigma)
    p_win_b = norm.cdf(7.0, loc=mu, scale=sigma)  # AWAY wins if margin < 7
    p_both = norm.cdf(7.0, loc=mu, scale=sigma) - norm.cdf(3.0, loc=mu, scale=sigma)
    p_a_only = p_win_a - p_both
    p_b_only = p_win_b - p_both

    net_both = 2.0 * (1.91 - 1) + 2.0 * (1.87 - 1)
    net_a_only = 2.0 * (1.91 - 1) - 2.0
    net_b_only = 2.0 * (1.87 - 1) - 2.0
    expected_ev = p_both * net_both + p_a_only * net_a_only + p_b_only * net_b_only

    assert result["ev"] == pytest.approx(expected_ev, abs=1e-9)
    assert result["p_both_win"] == pytest.approx(p_both)


def test_middle_ev_approaches_double_win_as_mu_centers_in_the_window():
    # mu dead-center in a wide window with tiny sigma -> almost certainly
    # both legs hit -> ev should approach net_both_win.
    opp = _opp(window_lo=3.0, window_hi=7.0)
    result = middle_ev(opp, mu=5.0, sigma=0.1, stake_a=2.0, stake_b=2.0)
    assert result["p_both_win"] == pytest.approx(1.0, abs=1e-6)
    assert result["ev"] == pytest.approx(result["net_both_win"], abs=1e-6)


def test_middle_ev_rejects_non_positive_sigma():
    opp = _opp()
    with pytest.raises(ValueError):
        middle_ev(opp, mu=5.0, sigma=0.0, stake_a=2.0, stake_b=2.0)
    with pytest.raises(ValueError):
        middle_ev(opp, mu=5.0, sigma=-1.0, stake_a=2.0, stake_b=2.0)


# --- find_middle_opportunities (integration, real PointInTimeStore) ---


def test_find_middle_opportunities_end_to_end(tmp_path):
    store = PointInTimeStore(root=tmp_path / "snapshots")
    store.write(
        [
            _snapshot("pinnacle", Market.SPREAD, Side.HOME, -150, line=-5.0, capture_time=CAPTURE_TIME + timedelta(days=3)),
            _snapshot("pinnacle", Market.SPREAD, Side.AWAY, 130, line=5.0, capture_time=CAPTURE_TIME + timedelta(days=3)),
            # A real, bettable middle: the two books disagree RIGHT NOW.
            # FanDuel has been sitting on home -3 since CAPTURE_TIME and is
            # still quoting it in the latest poll, while DraftKings offers away
            # +7. Both legs are re-captured in that latest poll -- which is what
            # real collection produces, since every book present in a poll gets
            # a fresh row even when its number has not changed.
            _snapshot("fanduel", Market.SPREAD, Side.HOME, -110, line=-3.0, capture_time=CAPTURE_TIME),
            _snapshot("fanduel", Market.SPREAD, Side.HOME, -110, line=-3.0, capture_time=CAPTURE_TIME + timedelta(days=3)),
            _snapshot("draftkings", Market.SPREAD, Side.AWAY, -105, line=7.0, capture_time=CAPTURE_TIME + timedelta(days=3)),
        ]
    )

    report = find_middle_opportunities(
        store, sigma_margin=13.0, sigma_total=10.0, as_of=CAPTURE_TIME + timedelta(days=4)
    )

    assert len(report) == 1
    row = report.iloc[0]
    assert row["event_id"] == "2026_01_NE_SEA"
    assert row["market"] == "spread"
    assert row["window_lo"] == pytest.approx(3.0)
    assert row["window_hi"] == pytest.approx(7.0)
    assert row["mu"] == pytest.approx(5.0)  # Pinnacle -5/+5, both thresholds average to 5.0
    assert row["p_neither"] == pytest.approx(0.0, abs=1e-9)


def test_find_middle_opportunities_excludes_offshore_books_from_the_bettable_legs(tmp_path):
    store = PointInTimeStore(root=tmp_path / "snapshots")
    store.write(
        [
            _snapshot("pinnacle", Market.SPREAD, Side.HOME, -150, line=-5.0, capture_time=CAPTURE_TIME + timedelta(days=3)),
            _snapshot("pinnacle", Market.SPREAD, Side.AWAY, 130, line=5.0, capture_time=CAPTURE_TIME + timedelta(days=3)),
            # A juicy "opportunity" only exists at a non-execution book -- must be ignored.
            _snapshot("onexbet", Market.SPREAD, Side.HOME, -110, line=-3.0, capture_time=CAPTURE_TIME + timedelta(days=3)),
            _snapshot("onexbet", Market.SPREAD, Side.AWAY, -105, line=7.0, capture_time=CAPTURE_TIME + timedelta(days=3)),
        ]
    )
    report = find_middle_opportunities(store, sigma_margin=13.0, sigma_total=10.0, as_of=CAPTURE_TIME + timedelta(days=4))
    assert report.empty


def test_find_middle_opportunities_returns_empty_when_nothing_moved(tmp_path):
    store = PointInTimeStore(root=tmp_path / "snapshots")
    store.write(
        [
            _snapshot("pinnacle", Market.SPREAD, Side.HOME, -150, line=-3.0, capture_time=CAPTURE_TIME),
            _snapshot("pinnacle", Market.SPREAD, Side.AWAY, 130, line=3.0, capture_time=CAPTURE_TIME),
            _snapshot("fanduel", Market.SPREAD, Side.HOME, -110, line=-3.0, capture_time=CAPTURE_TIME + timedelta(days=1)),
            _snapshot("draftkings", Market.SPREAD, Side.AWAY, -105, line=3.0, capture_time=CAPTURE_TIME + timedelta(days=2)),
        ]
    )
    report = find_middle_opportunities(store, sigma_margin=13.0, sigma_total=10.0, as_of=CAPTURE_TIME + timedelta(days=4))
    assert report.empty


# --- leg freshness (2026-09-08) ----------------------------------------------
#
# Both of these were live false positives before the fix. Wiring middling into
# the unattended monitor produced a GB@MIN alert whose BetRivers leg had been
# captured 13 days earlier: BetRivers' home line was +1.0 back then and is -1.0
# now, so the "middle" required placing a bet at a number no longer on the
# board. Real collection re-captures every book present in a poll, so a leg
# whose newest row is old is a leg that is no longer being offered.


def test_a_book_only_offers_its_latest_line_not_its_best_ever(tmp_path):
    """BetRivers at home +1.0 (13 days ago) then home -1.0 (now) must be treated
    as offering -1.0. Picking the historical +1.0 because it makes a wider
    window is picking a bet that cannot be placed.
    """
    store = PointInTimeStore(root=tmp_path / "snapshots")
    store.write(
        [
            _snapshot("pinnacle", Market.SPREAD, Side.HOME, -150, line=-5.0, capture_time=CAPTURE_TIME + timedelta(days=3)),
            _snapshot("pinnacle", Market.SPREAD, Side.AWAY, 130, line=5.0, capture_time=CAPTURE_TIME + timedelta(days=3)),
            # The wide line, long gone.
            _snapshot("betrivers", Market.SPREAD, Side.HOME, -110, line=-3.0, capture_time=CAPTURE_TIME),
            # What BetRivers actually offers now.
            _snapshot("betrivers", Market.SPREAD, Side.HOME, -110, line=-7.5, capture_time=CAPTURE_TIME + timedelta(days=3)),
            _snapshot("draftkings", Market.SPREAD, Side.AWAY, -105, line=7.0, capture_time=CAPTURE_TIME + timedelta(days=3)),
        ]
    )
    report = find_middle_opportunities(
        store, sigma_margin=13.0, sigma_total=10.0, as_of=CAPTURE_TIME + timedelta(days=4)
    )
    # -7.5 vs +7.0 is not a middle at all; the stale -3.0 would have made one.
    assert report.empty


def test_a_leg_that_stopped_being_quoted_is_dropped(tmp_path):
    """A book that vanishes from the feed must not keep offering its last known
    number forever -- bounded by DEFAULT_MAX_LEG_STALENESS.
    """
    store = PointInTimeStore(root=tmp_path / "snapshots")
    store.write(
        [
            _snapshot("pinnacle", Market.SPREAD, Side.HOME, -150, line=-5.0, capture_time=CAPTURE_TIME + timedelta(days=3)),
            _snapshot("pinnacle", Market.SPREAD, Side.AWAY, 130, line=5.0, capture_time=CAPTURE_TIME + timedelta(days=3)),
            # FanDuel's only quote is days older than the freshest in the event.
            _snapshot("fanduel", Market.SPREAD, Side.HOME, -110, line=-3.0, capture_time=CAPTURE_TIME),
            _snapshot("draftkings", Market.SPREAD, Side.AWAY, -105, line=7.0, capture_time=CAPTURE_TIME + timedelta(days=3)),
        ]
    )
    report = find_middle_opportunities(
        store, sigma_margin=13.0, sigma_total=10.0, as_of=CAPTURE_TIME + timedelta(days=4)
    )
    assert report.empty

    # Opting the bound out restores the old behaviour, so backtests that
    # deliberately span a long window can still ask for it explicitly.
    unbounded = find_middle_opportunities(
        store, sigma_margin=13.0, sigma_total=10.0,
        as_of=CAPTURE_TIME + timedelta(days=4), max_leg_staleness=None,
    )
    assert len(unbounded) == 1
