from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from src.store.bet_log import (
    LoggedBet,
    active_bets,
    load_bet_log,
    log_bet,
    settle_bets,
    to_backtest_bets,
)
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, OddsSnapshot, Side
from src.store.settlement import Outcome

KICKOFF = datetime(2026, 9, 20, 17, 0, tzinfo=UTC)
ENTRY = KICKOFF - timedelta(hours=24)
EVENT = "2026_03_KC_LAC"


def _bet(path=None, **kw):
    base = {
        "placed_at": ENTRY, "event_id": EVENT, "market": Market.MONEYLINE, "side": Side.HOME,
        "book": "draftkings", "price_american": -110, "stake": 2.0, "strategy": "moneyline_ev",
    }
    return LoggedBet(**{**base, **kw})


def _ml(book, home, away, capture, event_id=EVENT):
    return [
        OddsSnapshot.from_american(
            capture_time=capture, event_id=event_id, season=2026, week=3, home_team="LAC",
            away_team="KC", event_start_time=KICKOFF, book=book, market=Market.MONEYLINE,
            side=side, price_american=price,
        )
        for side, price in ((Side.HOME, home), (Side.AWAY, away))
    ]


# --- the record itself ------------------------------------------------------


def test_missing_log_is_empty_not_an_error(tmp_path):
    """Read by unattended reporting -- it must not become its own failure mode."""
    assert load_bet_log(tmp_path / "nope.jsonl") == []
    assert active_bets(tmp_path / "nope.jsonl") == []


def test_log_is_append_only(tmp_path):
    p = tmp_path / "bets.jsonl"
    log_bet(_bet(), path=p)
    log_bet(_bet(placed_at=ENTRY + timedelta(hours=1), strategy="prop_arb"), path=p)
    loaded = load_bet_log(p)
    assert len(loaded) == 2
    assert [b.strategy for b in loaded] == ["moneyline_ev", "prop_arb"]


def test_corrections_are_appended_and_supersede_not_overwrite(tmp_path):
    """A log editable after the close is one editable BECAUSE of the close --
    the exact bias CLV exists to detect. The wrong row stays visible.
    """
    p = tmp_path / "bets.jsonl"
    log_bet(_bet(stake=2.0), path=p)
    log_bet(_bet(placed_at=ENTRY + timedelta(minutes=5), stake=5.0,
                 corrects=ENTRY.isoformat()), path=p)

    assert len(load_bet_log(p)) == 2          # raw log keeps both
    live = active_bets(p)
    assert len(live) == 1 and live[0].stake == 5.0


def test_unknown_strategy_is_rejected():
    """A free-text strategy field fragments a segment and lets a dying
    strategy hide across three tiny groups.
    """
    with pytest.raises(ValueError, match="unknown strategy"):
        _bet(strategy="arb")


def test_naive_timestamp_is_rejected():
    """A naive placed_at compares wrong against the store's UTC capture_time
    and would corrupt every CLV number downstream.
    """
    with pytest.raises(ValueError, match="timezone-aware"):
        _bet(placed_at=datetime(2026, 9, 20, 12, 0))  # noqa: DTZ001 -- naive on purpose


def test_price_decimal_is_derived_not_typed():
    assert _bet(price_american=-110).price_decimal == pytest.approx(1.909, abs=1e-3)
    assert _bet(price_american=150).price_decimal == pytest.approx(2.5, abs=1e-9)


# --- the bridge to BacktestBet ---------------------------------------------


def test_clv_is_computed_from_the_store_not_typed(tmp_path):
    """The whole point: entry price is recorded, everything else is derived.
    Pinnacle moves toward the bet's side between entry and close, so CLV is
    positive and measurable.
    """
    store = PointInTimeStore(root=tmp_path)
    store.write(
        _ml("pinnacle", -110, -110, ENTRY)          # entry: fair ~0.50
        + _ml("pinnacle", -200, 170, KICKOFF - timedelta(minutes=5))   # close: home shorter
        + _ml("draftkings", -110, -110, KICKOFF - timedelta(minutes=5))
    )
    out = to_backtest_bets([_bet()], store, as_of=KICKOFF)
    assert len(out) == 1
    b = out[0]
    assert b.entry_prob_fair == pytest.approx(0.5, abs=0.01)
    assert b.close_prob_fair > b.entry_prob_fair       # line moved our way
    assert b.clv_probability is not None and b.clv_probability > 0
    assert b.close_price_decimal is not None


def test_unquoted_anchor_yields_none_clv_not_a_guess(tmp_path):
    """Pinnacle does not quote props until close to kickoff. An unmeasurable
    bet must report None, which `_clv_series` drops -- never a fabricated number.
    """
    store = PointInTimeStore(root=tmp_path)
    store.write(_ml("draftkings", -110, -110, ENTRY))  # no pinnacle at all
    b = to_backtest_bets([_bet()], store, as_of=KICKOFF)[0]
    assert b.entry_prob_fair is None
    assert b.clv_probability is None


def test_empty_log_produces_no_bets(tmp_path):
    assert to_backtest_bets([], PointInTimeStore(root=tmp_path)) == []


def test_bridge_preserves_strategy_relevant_identity(tmp_path):
    """season_review segments on strategy, and props need player/stat/line to
    identify the contract at all -- losing them would price another player.
    """
    store = PointInTimeStore(root=tmp_path)
    store.write(_ml("pinnacle", -110, -110, ENTRY))
    prop = _bet(market=Market.PLAYER_PROP, side=Side.OVER, strategy="prop_arb",
                player_name="A. Player", prop_stat="receiving_yards", line=45.5)
    out = to_backtest_bets([prop], store, as_of=KICKOFF)[0]
    assert out.player_name == "A. Player"
    assert out.prop_stat == "receiving_yards"
    assert out.line == 45.5
    assert out.stake == 2.0


# --- settlement -------------------------------------------------------------
#
# Settlement reuses settlement.settle / prop_settlement.settle_prop /
# engine.payout_for unchanged. A second copy of that math would let live P&L
# and backtest P&L disagree silently, which is the whole reason payout_for was
# made public rather than duplicated.


def _schedule(home_score, away_score, game_id=EVENT):
    return pd.DataFrame([{"game_id": game_id, "home_score": home_score, "away_score": away_score}])


def _settled(bets, schedule, kickoffs=None, player_stats=None, bankroll=100.0):
    return settle_bets(bets, schedule, kickoffs or {EVENT: KICKOFF}, player_stats, bankroll)


def _as_backtest(logged, store):
    return to_backtest_bets(logged, store, as_of=KICKOFF)


def _store(tmp_path):
    s = PointInTimeStore(root=tmp_path)
    s.write(_ml("pinnacle", -110, -110, ENTRY))
    return s


def test_moneyline_win_pays_profit_not_total_return(tmp_path):
    bets = _as_backtest([_bet(price_american=100, stake=2.0)], _store(tmp_path))
    out = _settled(bets, _schedule(home_score=24, away_score=17))   # home wins
    assert out[0].outcome == Outcome.WIN
    assert out[0].payout == pytest.approx(2.0)          # profit, not 4.0
    assert out[0].bankroll_after == pytest.approx(102.0)


def test_loss_debits_the_stake(tmp_path):
    bets = _as_backtest([_bet(stake=2.0)], _store(tmp_path))
    out = _settled(bets, _schedule(home_score=10, away_score=31))
    assert out[0].outcome == Outcome.LOSS
    assert out[0].payout == pytest.approx(-2.0)
    assert out[0].bankroll_after == pytest.approx(98.0)


def test_tie_is_a_push_not_a_loss(tmp_path):
    """NFL ties are real -- ~1 a season. Folding one into a loss understates
    the bankroll.
    """
    bets = _as_backtest([_bet(stake=2.0)], _store(tmp_path))
    out = _settled(bets, _schedule(home_score=20, away_score=20))
    assert out[0].outcome == Outcome.PUSH
    assert out[0].payout == pytest.approx(0.0)
    assert out[0].bankroll_after == pytest.approx(100.0)


def test_ungraded_bet_is_not_counted_as_a_loss(tmp_path):
    """An unplayed game must leave the bankroll untouched. Grading it as a loss
    would silently understate a $100 bankroll that has no top-ups.
    """
    bets = _as_backtest([_bet(stake=2.0)], _store(tmp_path))
    out = _settled(bets, _schedule(home_score=None, away_score=None))
    assert out[0].outcome is None
    assert out[0].payout is None
    assert out[0].bankroll_after == pytest.approx(100.0)


def test_bankroll_is_accumulated_in_KICKOFF_order_not_decision_order(tmp_path):
    """`clv_portfolio.bankroll_path` reads bankroll_after positionally, and
    sorting by decision time produced a non-monotone path once already: a bet
    can be decided 5 days out on a late game and 1 hour out on an early one.
    """
    early_ko, late_ko = KICKOFF, KICKOFF + timedelta(days=2)
    store = PointInTimeStore(root=tmp_path)
    store.write(_ml("pinnacle", -110, -110, ENTRY)
                + _ml("pinnacle", -110, -110, ENTRY, event_id="LATE"))

    # decided FIRST but kicks off LAST
    late = _bet(placed_at=ENTRY - timedelta(days=5), event_id="LATE", price_american=100)
    early = _bet(placed_at=ENTRY, price_american=100)

    bets = to_backtest_bets([late, early], store, as_of=KICKOFF)
    sched = pd.concat([_schedule(24, 17), _schedule(24, 17, game_id="LATE")], ignore_index=True)
    out = settle_bets(bets, sched, {EVENT: early_ko, "LATE": late_ko}, None, 100.0)

    assert [b.event_id for b in out] == [EVENT, "LATE"]           # kickoff order
    assert [b.bankroll_after for b in out] == pytest.approx([102.0, 104.0])


def test_prop_settles_against_player_stats(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    store.write(_ml("pinnacle", -110, -110, ENTRY))
    prop = _bet(market=Market.PLAYER_PROP, side=Side.OVER, strategy="prop_arb",
                player_name="A.J. Brown", prop_stat="receiving_yards", line=45.5,
                price_american=100, stake=2.0)
    stats = pd.DataFrame([{"game_id": EVENT, "player_display_name": "AJ Brown",
                           "receiving_yards": 78.0}])
    out = _settled(_as_backtest([prop], store), _schedule(24, 17), player_stats=stats)
    # name normalisation resolves "A.J. Brown" (book) to "AJ Brown" (nflverse)
    assert out[0].outcome == Outcome.WIN
    assert out[0].bankroll_after == pytest.approx(102.0)


# --- code-review regressions (2026-08-23) -----------------------------------


def test_corrects_matches_a_value_copied_out_of_the_file(tmp_path):
    """**The correction workflow must work with the value the file actually
    contains.** Pydantic serialises `placed_at` as `...Z`; `.isoformat()`
    produces `...+00:00`. Comparing those as strings never matches, so the
    superseded row survives and `settle_bets` counts its stake AND P&L twice --
    a real error on a fixed $100 bankroll with no top-ups.

    The earlier test passed only because it built `corrects` in Python instead
    of reading it back from disk: it validated the implementation, not the
    workflow. This one round-trips through the file, which is the only way a
    human can obtain that value.
    """
    import json

    p = tmp_path / "bets.jsonl"
    log_bet(_bet(stake=2.0), path=p)
    on_disk = json.loads(p.read_text().splitlines()[0])["placed_at"]

    log_bet(_bet(placed_at=ENTRY + timedelta(minutes=5), stake=5.0, corrects=on_disk), path=p)

    assert len(load_bet_log(p)) == 2          # raw record keeps both
    live = active_bets(p)
    assert len(live) == 1 and live[0].stake == 5.0


def test_no_clv_for_a_game_that_has_not_kicked_off(tmp_path):
    """"Close" is defined as the last quote at or before kickoff -- a filter every
    row trivially satisfies while kickoff is still in the future, which turns the
    *current* quote into a fake close. `season_review` feeds these into the CUSUM
    drift detector, so a strategy could be retired on CLV from lines still moving.
    """
    future_kickoff = ENTRY + timedelta(days=10)
    store = PointInTimeStore(root=tmp_path)
    store.write([
        OddsSnapshot.from_american(
            capture_time=cap, event_id=EVENT, season=2026, week=3, home_team="LAC",
            away_team="KC", event_start_time=future_kickoff, book="pinnacle",
            market=Market.MONEYLINE, side=side, price_american=price,
        )
        for cap, h, a in ((ENTRY, -110, -110), (ENTRY + timedelta(hours=2), -200, 170))
        for side, price in ((Side.HOME, h), (Side.AWAY, a))
    ])
    b = to_backtest_bets([_bet()], store, as_of=ENTRY + timedelta(hours=3))[0]
    assert b.entry_prob_fair is not None      # entry is knowable
    assert b.close_prob_fair is None          # the close is NOT
    assert b.clv_probability is None
    assert b.close_price_decimal is None


def test_impossible_market_side_combination_is_rejected_at_entry():
    """`--market player_prop --side home` used to be accepted by the CLI and
    only blow up later inside settlement, where the person who could have fixed
    it is no longer looking.
    """
    with pytest.raises(ValueError, match="requires side in"):
        _bet(market=Market.PLAYER_PROP, side=Side.HOME, strategy="prop_arb",
             player_name="A", prop_stat="receptions", line=2.5)
    with pytest.raises(ValueError, match="requires side in"):
        _bet(market=Market.MONEYLINE, side=Side.OVER)


def test_prop_without_contract_identity_is_rejected():
    """player/stat/line identify the CONTRACT. A prop missing them can never be
    graded and would sit in the log forever reporting outcome=None.
    """
    with pytest.raises(ValueError, match="identify the contract"):
        _bet(market=Market.PLAYER_PROP, side=Side.OVER, strategy="prop_arb")


def test_one_ungradeable_bet_does_not_abort_the_whole_settlement(tmp_path):
    """A single bad row must not hide every other bet's real P&L. `outcome=None`
    is already a supported state, so an ungradeable bet degrades to unsettled.
    """
    store = _store(tmp_path)
    good = _as_backtest([_bet(price_american=100, stake=2.0)], store)[0]
    # force an ungradeable row past the entry validator, as a corrupted file could
    broken = replace(good, side=Side.OVER, market=Market.PLAYER_PROP,
                     player_name="X", prop_stat="receptions", line=None)
    out = _settled([good, broken], _schedule(home_score=24, away_score=17))
    outcomes = {b.event_id + str(b.market.value): b.outcome for b in out}
    assert any(o is not None for o in outcomes.values())    # the good bet still graded
    assert any(o is None for o in outcomes.values())        # the bad one degraded
    assert out[-1].bankroll_after == pytest.approx(102.0)   # only the good bet moved it


# --- dry-run regressions (2026-09-27) ---------------------------------------


def test_a_correction_reusing_the_same_placed_at_does_not_delete_the_bet(tmp_path):
    """**A correction may share its target's `placed_at`, and must not erase it.**

    `placed_at` is documented as the moment the bet was STRUCK, not the moment
    it was typed, so correcting a mistyped stake on that same bet reuses that
    instant -- which is what a user following the docstring does. Matching
    superseded rows by timestamp value alone then dropped the correction too:
    the bet disappeared from `active_bets`, so it was never settled, never
    counted in the bankroll, and never reviewed. Silently losing a placed bet
    is worse than the double-count the filter exists to prevent.

    Found by the first end-to-end dry run of `make log-bet` (2026-09-27); the
    existing round-trip test missed it by giving the correction a later
    `placed_at`.
    """
    import json

    p = tmp_path / "bets.jsonl"
    log_bet(_bet(stake=3.0), path=p)
    on_disk = json.loads(p.read_text().splitlines()[0])["placed_at"]

    log_bet(_bet(placed_at=ENTRY, stake=8.0, corrects=on_disk), path=p)

    assert len(load_bet_log(p)) == 2           # raw record keeps both
    live = active_bets(p)
    assert len(live) == 1 and live[0].stake == 8.0


def test_a_chain_of_corrections_keeps_only_the_last(tmp_path):
    """Corrections are append-only, so a second correction supersedes the first.
    Only the newest row is live; every earlier one is history.
    """
    p = tmp_path / "bets.jsonl"
    log_bet(_bet(stake=1.0), path=p)
    log_bet(_bet(placed_at=ENTRY + timedelta(minutes=5), stake=2.0,
                 corrects=ENTRY.isoformat()), path=p)
    log_bet(_bet(placed_at=ENTRY + timedelta(minutes=9), stake=3.0,
                 corrects=(ENTRY + timedelta(minutes=5)).isoformat()), path=p)

    assert len(load_bet_log(p)) == 3
    live = active_bets(p)
    assert len(live) == 1 and live[0].stake == 3.0
