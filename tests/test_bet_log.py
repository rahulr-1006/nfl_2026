from datetime import UTC, datetime, timedelta

import pytest

from src.store.bet_log import (
    LoggedBet,
    active_bets,
    load_bet_log,
    log_bet,
    to_backtest_bets,
)
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, OddsSnapshot, Side

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
