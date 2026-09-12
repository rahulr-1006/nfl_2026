"""CLV when the anchor's line is not the line you bet.

Written 2026-09-10/11 after the season's first real close (2026_01_NE_SEA)
exposed three distinct bugs in one run, none of which any existing test could
reach because all three need a game to have ACTUALLY kicked off:

  1. `bets_to_frame` never emitted `close_price_decimal`, which
     `shadow_clv.format_summary` reads -- `make clv-report` crashed with a
     KeyError. Unreachable until then: the line sits after an early return that
     fires while every row is still unmeasurable.
  2. `_market_rows` filtered on `line` for PLAYER_PROP only, so a steam leg on
     Under 44.5 was scored against Pinnacle's Under 44.0 close -- two different
     contracts, reported as +0.0171 CLV.
  3. Fixing (2) with an exact-line match replaced a wrong number with a vacuous
     one: Pinnacle had left 44.5 8h48m before kickoff, so "the last quote at
     44.5" predated the steam move that fired the alert and CLV came out an
     exact, meaningless 0.0000.
"""

import math
from datetime import UTC, datetime, timedelta

import pytest

from src.backtest.clv_portfolio import bets_to_frame
from src.clv.line_adjust import implied_mean, translate_fair_prob
from src.clv.shadow_clv import format_summary
from src.store.bet_log import LoggedBet, to_backtest_bets
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, OddsSnapshot, Side

SIGMA_TOTAL = 13.457631834745575
SIGMA_MARGIN = 12.910331342813834

NOW = datetime.now(UTC)
KICKOFF = NOW - timedelta(hours=3)
ENTRY_TIME = KICKOFF - timedelta(hours=30)
CLOSE_TIME = KICKOFF - timedelta(minutes=18)


# --- the translation itself --------------------------------------------------


def test_even_price_implies_the_line_itself():
    """A 50% fair probability means the market's mean IS the line -- the one
    anchor point the whole inversion has to reproduce exactly."""
    assert implied_mean(Market.TOTAL, Side.UNDER, 44.0, 0.5, SIGMA_TOTAL) == pytest.approx(44.0)
    assert implied_mean(Market.TOTAL, Side.OVER, 44.0, 0.5, SIGMA_TOTAL) == pytest.approx(44.0)


def test_mirrored_spread_sides_imply_the_same_mean():
    """home -3.5 at 55% and away +3.5 at 45% are the same market view stated
    twice. If the sign handling were wrong these would disagree, and spread CLV
    would depend on which side you happened to bet."""
    home = implied_mean(Market.SPREAD, Side.HOME, -3.5, 0.55, SIGMA_MARGIN)
    away = implied_mean(Market.SPREAD, Side.AWAY, 3.5, 0.45, SIGMA_MARGIN)
    assert home == pytest.approx(away)


def test_translation_is_identity_on_a_matching_line():
    """Calling this unconditionally must not introduce model error where there
    was no gap -- otherwise every exact-match CLV would drift for no reason."""
    p = 0.5123
    assert translate_fair_prob(Market.TOTAL, Side.UNDER, 44.5, 44.5, p, SIGMA_TOTAL) == p


def test_translation_round_trips():
    p = 0.42
    there = translate_fair_prob(Market.TOTAL, Side.OVER, 44.0, 47.5, p, SIGMA_TOTAL)
    back = translate_fair_prob(Market.TOTAL, Side.OVER, 47.5, 44.0, there, SIGMA_TOTAL)
    assert back == pytest.approx(p)


def test_translation_moves_probability_the_right_way():
    """Under a HIGHER total is easier to win; over a higher total is harder.
    A sign error here would silently invert every translated CLV."""
    under = translate_fair_prob(Market.TOTAL, Side.UNDER, 44.0, 44.5, 0.5, SIGMA_TOTAL)
    over = translate_fair_prob(Market.TOTAL, Side.OVER, 44.0, 44.5, 0.5, SIGMA_TOTAL)
    assert under > 0.5
    assert over < 0.5
    assert under + over == pytest.approx(1.0)


def test_the_real_ne_sea_numbers():
    """The actual case: Pinnacle closed Under 44.0 at -106/-106 (devig 0.5) and
    the alert was Under 44.5. Pins the number the report now prints."""
    assert translate_fair_prob(
        Market.TOTAL, Side.UNDER, 44.0, 44.5, 0.5, SIGMA_TOTAL
    ) == pytest.approx(0.5148187, abs=1e-6)


def test_degenerate_probabilities_do_not_produce_nan():
    """norm.ppf(0) is -inf, which would put mu at infinity and poison every
    downstream CLV number with NaN rather than failing loudly."""
    for p in (0.0, 1.0):
        out = translate_fair_prob(Market.TOTAL, Side.OVER, 44.0, 45.0, p, SIGMA_TOTAL)
        assert math.isfinite(out)


def test_non_positive_sigma_is_rejected():
    with pytest.raises(ValueError):
        implied_mean(Market.TOTAL, Side.OVER, 44.0, 0.6, 0.0)


# --- end to end through the CLV path ----------------------------------------


def _snap(book, market, side, price, capture_time, line):
    return OddsSnapshot.from_american(
        capture_time=capture_time, event_id="2026_01_NE_SEA", season=2026, week=1,
        home_team="SEA", away_team="NE", event_start_time=KICKOFF,
        book=book, market=market, side=side, price_american=price, line=line,
    )


def _moving_line_store(root):
    """Pinnacle sits on 44.5, then moves to 44.0 and CLOSES there. FanDuel holds
    44.5 throughout -- the real 2026_01_NE_SEA shape."""
    store = PointInTimeStore(root=root)
    rows = []
    for t, pinn_line in ((ENTRY_TIME, 44.5), (CLOSE_TIME, 44.0)):
        rows += [
            _snap("pinnacle", Market.TOTAL, Side.OVER, -106, t, pinn_line),
            _snap("pinnacle", Market.TOTAL, Side.UNDER, -106, t, pinn_line),
            _snap("fanduel", Market.TOTAL, Side.OVER, -110, t, 44.5),
            _snap("fanduel", Market.TOTAL, Side.UNDER, -108, t, 44.5),
        ]
    store.write(rows)
    return store


def _under_445_bet():
    return LoggedBet(
        placed_at=ENTRY_TIME, event_id="2026_01_NE_SEA", market=Market.TOTAL,
        side=Side.UNDER, book="fanduel", price_american=-108, stake=1.0,
        strategy="steam", line=44.5,
    )


def test_close_is_translated_onto_the_bet_line(tmp_path):
    """The anchor closed at 44.0 but the bet was 44.5, so the close must be the
    TRANSLATED probability -- not the anchor's raw 44.0 number, and not a stale
    44.5 quote from before the move."""
    store = _moving_line_store(tmp_path / "snaps")
    bets = to_backtest_bets(
        [_under_445_bet()], store, residual_stds=lambda: (SIGMA_MARGIN, SIGMA_TOTAL)
    )
    (bet,) = bets
    assert bet.close_prob_fair == pytest.approx(0.5148187, abs=1e-6)
    assert bet.clv_probability is not None


def test_clv_is_not_vacuously_zero_when_the_anchor_moves_off_the_line(tmp_path):
    """The exact-match regression: entry and close both resolving to the same
    stale 44.5 snapshot made CLV exactly 0.0, which reads as 'no edge' rather
    than 'not measured'."""
    store = _moving_line_store(tmp_path / "snaps")
    (bet,) = to_backtest_bets(
        [_under_445_bet()], store, residual_stds=lambda: (SIGMA_MARGIN, SIGMA_TOTAL)
    )
    assert bet.clv_probability != 0.0
    assert bet.entry_prob_fair != bet.close_prob_fair


def test_sigma_is_not_fetched_for_bets_that_cannot_need_it(tmp_path):
    """A prop- or moneyline-only run must never trigger the play-by-play fit."""
    store = _moving_line_store(tmp_path / "snaps")

    def _explode():
        raise AssertionError("residual sigma must not be fetched for a moneyline bet")

    ml = LoggedBet(
        placed_at=ENTRY_TIME, event_id="2026_01_NE_SEA", market=Market.MONEYLINE,
        side=Side.HOME, book="fanduel", price_american=-110, stake=1.0, strategy="moneyline_ev",
    )
    to_backtest_bets([ml], store, residual_stds=_explode)  # must not raise


# --- the report crash --------------------------------------------------------


def test_frame_carries_close_price_decimal(tmp_path):
    store = _moving_line_store(tmp_path / "snaps")
    bets = to_backtest_bets(
        [_under_445_bet()], store, residual_stds=lambda: (SIGMA_MARGIN, SIGMA_TOTAL)
    )
    assert "close_price_decimal" in bets_to_frame(bets).columns


def test_format_summary_survives_a_closed_game(tmp_path):
    """The KeyError that broke `make clv-report`: reachable only once at least
    one row is measurable, i.e. only after a real kickoff."""
    store = _moving_line_store(tmp_path / "snaps")
    bets = to_backtest_bets(
        [_under_445_bet()], store, residual_stds=lambda: (SIGMA_MARGIN, SIGMA_TOTAL)
    )
    frame = bets_to_frame(bets)
    frame["measurable"] = frame["clv_probability"].notna()
    assert frame["measurable"].any(), "fixture must produce a measurable row"
    assert "beat_rate" in format_summary(frame)


# --- _market_rows line filtering --------------------------------------------


def test_total_line_filter_isolates_one_contract(tmp_path):
    """Alternate totals quoted at the SAME instant: without a line filter
    `latest_fair_prob` sees four rows where it needs two and returns None, and
    before the fix it had no line filter for TOTAL at all."""
    from src.backtest.engine import latest_fair_prob

    store = PointInTimeStore(root=tmp_path / "alt")
    store.write([
        _snap("pinnacle", Market.TOTAL, Side.OVER, -106, CLOSE_TIME, 44.0),
        _snap("pinnacle", Market.TOTAL, Side.UNDER, -106, CLOSE_TIME, 44.0),
        _snap("pinnacle", Market.TOTAL, Side.OVER, 120, CLOSE_TIME, 47.5),
        _snap("pinnacle", Market.TOTAL, Side.UNDER, -140, CLOSE_TIME, 47.5),
    ])
    snaps = store.read_as_of(NOW)

    p44 = latest_fair_prob(snaps, "pinnacle", Market.TOTAL, Side.OVER, NOW, "shin",
                           line=44.0, event_id="2026_01_NE_SEA")
    p475 = latest_fair_prob(snaps, "pinnacle", Market.TOTAL, Side.OVER, NOW, "shin",
                            line=47.5, event_id="2026_01_NE_SEA")
    assert p44 == pytest.approx(0.5, abs=0.01)
    assert p475 is not None and p475 < 0.5, "over a higher total must be less likely"


def test_spread_line_filter_keeps_the_mirrored_pair(tmp_path):
    """A spread's sides carry mirrored lines (home -3.5 / away +3.5). An exact
    match on either value would keep ONE side and make every spread CLV None,
    so the filter matches on absolute value."""
    from src.backtest.engine import latest_fair_prob

    store = PointInTimeStore(root=tmp_path / "spr")
    store.write([
        _snap("pinnacle", Market.SPREAD, Side.HOME, -110, CLOSE_TIME, -3.5),
        _snap("pinnacle", Market.SPREAD, Side.AWAY, -110, CLOSE_TIME, 3.5),
        _snap("pinnacle", Market.SPREAD, Side.HOME, 150, CLOSE_TIME, -9.5),
        _snap("pinnacle", Market.SPREAD, Side.AWAY, -175, CLOSE_TIME, 9.5),
    ])
    snaps = store.read_as_of(NOW)

    p = latest_fair_prob(snaps, "pinnacle", Market.SPREAD, Side.HOME, NOW, "shin",
                         line=-3.5, event_id="2026_01_NE_SEA")
    assert p == pytest.approx(0.5, abs=0.01), "mirrored pair must survive the filter"

    alt = latest_fair_prob(snaps, "pinnacle", Market.SPREAD, Side.HOME, NOW, "shin",
                           line=-9.5, event_id="2026_01_NE_SEA")
    assert alt is not None and alt < 0.4, "the alternate spread must be priced separately"
