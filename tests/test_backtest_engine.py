from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from src.backtest.engine import BacktestEngine, BetOrder, DecisionPoint
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, OddsSnapshot, Side
from src.store.settlement import Outcome

KICKOFF_G1 = datetime(2026, 9, 7, 17, 0, tzinfo=UTC)
KICKOFF_G2 = datetime(2026, 9, 7, 20, 0, tzinfo=UTC)
KICKOFF_G3 = datetime(2026, 9, 7, 20, 0, tzinfo=UTC)


def _snap(event_id, season, week, home, away, kickoff, capture_time, book, market, side, price_american, line=None):
    return OddsSnapshot.from_american(
        capture_time=capture_time,
        event_id=event_id,
        season=season,
        week=week,
        home_team=home,
        away_team=away,
        event_start_time=kickoff,
        book=book,
        market=market,
        side=side,
        price_american=price_american,
        line=line,
    )


def _schedule():
    return pd.DataFrame(
        [
            {
                "game_id": "2026_01_KC_LAC",
                "season": 2026,
                "week": 1,
                "gameday": "2026-09-07",
                "gametime": "13:00",
                "home_team": "LAC",
                "away_team": "KC",
                "home_score": 27.0,
                "away_score": 20.0,
            },
            {
                "game_id": "2026_01_BUF_NYJ",
                "season": 2026,
                "week": 1,
                "gameday": "2026-09-07",
                "gametime": "16:00",
                "home_team": "NYJ",
                "away_team": "BUF",
                "home_score": 17.0,
                "away_score": 24.0,
            },
            {
                "game_id": "2026_01_IND_HOU",
                "season": 2026,
                "week": 1,
                "gameday": "2026-09-07",
                "gametime": "16:00",
                "home_team": "HOU",
                "away_team": "IND",
                "home_score": 20.0,
                "away_score": 20.0,
            },
            {
                # No snapshots ever written for this one -- must be skipped, not crash.
                "game_id": "2026_01_DAL_PHI",
                "season": 2026,
                "week": 1,
                "gameday": "2026-09-07",
                "gametime": "13:00",
                "home_team": "PHI",
                "away_team": "DAL",
                "home_score": None,
                "away_score": None,
            },
        ]
    )


def _seed_game1(store):
    # Entry: symmetric -110/-110 -> fair 0.5/0.5 under any devig method.
    entry_time = KICKOFF_G1 - timedelta(hours=10)
    store.write(
        [
            _snap("2026_01_KC_LAC", 2026, 1, "LAC", "KC", KICKOFF_G1, entry_time, "pinnacle", Market.SPREAD, Side.HOME, -110, line=-4.5),
            _snap("2026_01_KC_LAC", 2026, 1, "LAC", "KC", KICKOFF_G1, entry_time, "pinnacle", Market.SPREAD, Side.AWAY, -110, line=4.5),
        ]
    )
    # Close: home -120 (q=0.545455), away +105 (q=0.487805) -> multiplicative fair_home = 0.527839
    close_time = KICKOFF_G1 - timedelta(hours=1)
    store.write(
        [
            _snap("2026_01_KC_LAC", 2026, 1, "LAC", "KC", KICKOFF_G1, close_time, "pinnacle", Market.SPREAD, Side.HOME, -120, line=-4.5),
            _snap("2026_01_KC_LAC", 2026, 1, "LAC", "KC", KICKOFF_G1, close_time, "pinnacle", Market.SPREAD, Side.AWAY, 105, line=4.5),
        ]
    )
    return entry_time, close_time


def _always_bet_home_spread(dp: DecisionPoint) -> BetOrder | None:
    return BetOrder(market=Market.SPREAD, side=Side.HOME, line=-4.5, book="pinnacle", stake=2.0)


def _never_bet(dp: DecisionPoint) -> BetOrder | None:
    return None


def test_hand_computed_clv_and_win_payout(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    entry_time, _close_time = _seed_game1(store)
    engine = BacktestEngine(store, _schedule(), devig_method="multiplicative")

    bets = engine.run(_always_bet_home_spread)

    g1 = next(b for b in bets if b.event_id == "2026_01_KC_LAC")

    # Independent hand computation, straight from the American-odds formulas
    # (not via engine.py's or devig/convert.py's helpers):
    entry_decimal = 1 + 100 / 110  # -110
    close_decimal = 1 + 100 / 120  # -120
    close_away_decimal = 1 + 105 / 100  # +105
    entry_fair = 0.5  # symmetric -110/-110 market
    q_home_close = 1 / close_decimal
    q_away_close = 1 / close_away_decimal
    close_fair = q_home_close / (q_home_close + q_away_close)  # multiplicative devig

    assert g1.decision_time == pd.Timestamp(entry_time)
    assert g1.price_american == -110
    assert g1.price_decimal == pytest.approx(entry_decimal)
    assert g1.entry_prob_fair == pytest.approx(entry_fair)
    assert g1.close_price_decimal == pytest.approx(close_decimal)
    assert g1.close_prob_fair == pytest.approx(close_fair)
    assert g1.clv_price == pytest.approx(entry_decimal / close_decimal - 1)
    assert g1.clv_probability == pytest.approx(close_fair - entry_fair)
    assert g1.clv_price > 0  # better price than the close
    assert g1.clv_probability > 0  # market moved toward our side after entry

    # LAC (home) won 27-20, covers -4.5 -> WIN
    assert g1.outcome == Outcome.WIN
    assert g1.payout == pytest.approx(2.0 * (entry_decimal - 1))


def test_loss_payout_is_negative_stake(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    t = KICKOFF_G2 - timedelta(hours=5)
    store.write(
        [
            _snap("2026_01_BUF_NYJ", 2026, 1, "NYJ", "BUF", KICKOFF_G2, t, "pinnacle", Market.MONEYLINE, Side.HOME, 150),
            _snap("2026_01_BUF_NYJ", 2026, 1, "NYJ", "BUF", KICKOFF_G2, t, "pinnacle", Market.MONEYLINE, Side.AWAY, -180),
        ]
    )

    def _bet_home_moneyline(dp: DecisionPoint) -> BetOrder | None:
        if dp.event_id != "2026_01_BUF_NYJ":
            return None
        return BetOrder(market=Market.MONEYLINE, side=Side.HOME, line=None, book="pinnacle", stake=2.0)

    engine = BacktestEngine(store, _schedule())
    bets = engine.run(_bet_home_moneyline)

    g2 = next(b for b in bets if b.event_id == "2026_01_BUF_NYJ")
    # NYJ (home) lost 17-24 -> LOSS
    assert g2.outcome == Outcome.LOSS
    assert g2.payout == pytest.approx(-2.0)


def test_push_payout_is_zero(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    t = KICKOFF_G3 - timedelta(hours=5)
    store.write(
        [
            _snap("2026_01_IND_HOU", 2026, 1, "HOU", "IND", KICKOFF_G3, t, "pinnacle", Market.MONEYLINE, Side.HOME, 100),
            _snap("2026_01_IND_HOU", 2026, 1, "HOU", "IND", KICKOFF_G3, t, "pinnacle", Market.MONEYLINE, Side.AWAY, -105),
        ]
    )

    def _bet_home_moneyline(dp: DecisionPoint) -> BetOrder | None:
        if dp.event_id != "2026_01_IND_HOU":
            return None
        return BetOrder(market=Market.MONEYLINE, side=Side.HOME, line=None, book="pinnacle", stake=2.0)

    engine = BacktestEngine(store, _schedule())
    bets = engine.run(_bet_home_moneyline)

    g3 = next(b for b in bets if b.event_id == "2026_01_IND_HOU")
    # HOU 20 - IND 20: tie -> PUSH
    assert g3.outcome == Outcome.PUSH
    assert g3.payout == 0.0


def test_game_with_no_snapshots_is_skipped_not_crashed(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    _seed_game1(store)  # only game1 has data; DAL_PHI never gets any snapshots
    engine = BacktestEngine(store, _schedule())

    bets = engine.run(_always_bet_home_spread)

    assert all(b.event_id != "2026_01_DAL_PHI" for b in bets)


def test_strategy_that_never_bets_produces_no_bets(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    _seed_game1(store)
    engine = BacktestEngine(store, _schedule())

    bets = engine.run(_never_bet)

    assert bets == []


def test_strategy_ordering_an_unavailable_book_raises(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    _seed_game1(store)
    engine = BacktestEngine(store, _schedule())

    def _bet_nonexistent_book(dp: DecisionPoint) -> BetOrder | None:
        return BetOrder(market=Market.SPREAD, side=Side.HOME, line=-4.5, book="draftkings", stake=2.0)

    with pytest.raises(ValueError, match="not visible"):
        engine.run(_bet_nonexistent_book)


# --- leakage guard (required, not optional) ---


def test_future_snapshot_never_visible_to_strategy_or_used_as_close(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    _seed_game1(store)

    # A snapshot captured AFTER kickoff, with an obviously-wrong price that
    # would be trivially detectable if it ever leaked into the backtest.
    leaked_time = KICKOFF_G1 + timedelta(minutes=30)
    store.write(
        [
            _snap("2026_01_KC_LAC", 2026, 1, "LAC", "KC", KICKOFF_G1, leaked_time, "pinnacle", Market.SPREAD, Side.HOME, -100000, line=-4.5),
            _snap("2026_01_KC_LAC", 2026, 1, "LAC", "KC", KICKOFF_G1, leaked_time, "pinnacle", Market.SPREAD, Side.AWAY, 100000, line=4.5),
        ]
    )

    seen_capture_times = []

    def _record_and_never_bet(dp: DecisionPoint) -> BetOrder | None:
        seen_capture_times.extend(dp.visible_snapshots["capture_time"].tolist())
        return None

    engine = BacktestEngine(store, _schedule(), devig_method="multiplicative")
    engine.run(_record_and_never_bet)

    assert all(t <= pd.Timestamp(KICKOFF_G1) for t in seen_capture_times)
    assert pd.Timestamp(leaked_time) not in seen_capture_times

    # And the same guarantee holds for the recorded bet's own close price/prob.
    bets = engine.run(_always_bet_home_spread)
    g1 = next(b for b in bets if b.event_id == "2026_01_KC_LAC")
    assert g1.close_price_decimal == pytest.approx(1 + 100 / 120)  # the real -120 close, not -100000
