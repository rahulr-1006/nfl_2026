"""Props CLV path through BacktestEngine -- the capability this project's
actual (prop-adjacent) edges depend on, added 2026-08-23.
"""

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from src.backtest.engine import BacktestEngine, BetOrder, DecisionPoint
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, OddsSnapshot, Side
from src.store.settlement import Outcome

KICKOFF = datetime(2026, 9, 7, 17, 0, tzinfo=UTC)
ENTRY_TIME = KICKOFF - timedelta(hours=24)
CLOSE_TIME = KICKOFF - timedelta(hours=1)


def _prop_snap(capture_time, book, side, price_american, player_name, line=45.5, prop_stat="receiving_yards"):
    return OddsSnapshot.from_american(
        capture_time=capture_time,
        event_id="2026_01_KC_LAC",
        season=2026,
        week=1,
        home_team="LAC",
        away_team="KC",
        event_start_time=KICKOFF,
        book=book,
        market=Market.PLAYER_PROP,
        side=side,
        price_american=price_american,
        line=line,
        player_name=player_name,
        prop_stat=prop_stat,
    )


def _schedule():
    return pd.DataFrame(
        [{
            "game_id": "2026_01_KC_LAC", "season": 2026, "week": 1,
            "gameday": "2026-09-07", "gametime": "17:00",
            "home_team": "LAC", "away_team": "KC", "home_score": 27.0, "away_score": 20.0,
        }]
    )


def _player_stats(receiving_yards=60.0, player="Star Receiver"):
    return pd.DataFrame(
        [{"game_id": "2026_01_KC_LAC", "player_display_name": player, "receiving_yards": receiving_yards}]
    )


def _seed_two_players(store):
    """Two players in the SAME game at very different prices -- the exact
    structure that makes contract-level selection necessary.

    **Backup Guy is written FIRST deliberately.** The pre-2026-08-23 code
    selected with `idxmax()` on capture_time, which returns the FIRST row
    holding the max -- so with Star Receiver written first, the old broken
    code would have picked the right price by pure ordering luck and these
    tests would have passed against it, proving nothing. Verified
    empirically during this build: with this ordering the old selector
    returns Backup Guy's +400 for a Star Receiver bet, so the tests below
    genuinely discriminate.
    """
    store.write([
        # Backup Guy first -- see docstring. Same game/stat/line, wildly different price.
        _prop_snap(ENTRY_TIME, "pinnacle", Side.OVER, 400, "Backup Guy"),
        _prop_snap(ENTRY_TIME, "pinnacle", Side.UNDER, -600, "Backup Guy"),
        _prop_snap(CLOSE_TIME, "pinnacle", Side.OVER, 450, "Backup Guy"),
        _prop_snap(CLOSE_TIME, "pinnacle", Side.UNDER, -700, "Backup Guy"),
        # Star Receiver: -110 both sides at entry, -130/+110 at close
        _prop_snap(ENTRY_TIME, "pinnacle", Side.OVER, -110, "Star Receiver"),
        _prop_snap(ENTRY_TIME, "pinnacle", Side.UNDER, -110, "Star Receiver"),
        _prop_snap(CLOSE_TIME, "pinnacle", Side.OVER, -130, "Star Receiver"),
        _prop_snap(CLOSE_TIME, "pinnacle", Side.UNDER, 110, "Star Receiver"),
    ])


def _bet_star_over(dp: DecisionPoint):
    return BetOrder(
        market=Market.PLAYER_PROP, side=Side.OVER, line=45.5, book="pinnacle", stake=2.0,
        player_name="Star Receiver", prop_stat="receiving_yards",
    )


def test_prop_bet_selects_the_right_players_price_not_another(tmp_path):
    """The real correctness fix: with two players quoted in one game,
    filtering on (book, market, side) alone -- what this engine did before
    2026-08-23 -- could return Backup Guy's +400 for a Star Receiver bet.
    """
    store = PointInTimeStore(root=tmp_path)
    _seed_two_players(store)
    engine = BacktestEngine(store, _schedule(), player_stats=_player_stats())

    bets = engine.run(_bet_star_over)

    assert len(bets) == 1
    assert bets[0].price_american == -110  # Star Receiver's price, NOT Backup Guy's +400
    assert bets[0].player_name == "Star Receiver"
    assert bets[0].prop_stat == "receiving_yards"


def test_prop_clv_is_computed_from_the_same_players_close(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    _seed_two_players(store)
    engine = BacktestEngine(store, _schedule(), devig_method="multiplicative", player_stats=_player_stats())

    bet = engine.run(_bet_star_over)[0]

    entry_decimal = 1 + 100 / 110
    close_decimal = 1 + 100 / 130  # Star Receiver's -130 close, not Backup Guy's +450
    assert bet.close_price_decimal == pytest.approx(close_decimal)
    assert bet.clv_price == pytest.approx(entry_decimal / close_decimal - 1)
    assert bet.clv_price > 0  # took -110, closed -130: beat the close
    assert bet.entry_prob_fair == pytest.approx(0.5)  # symmetric -110/-110
    assert bet.clv_probability > 0


def test_prop_settles_against_the_players_real_stat_line(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    _seed_two_players(store)
    # 60 receiving yards vs a 45.5 line -> OVER wins
    engine = BacktestEngine(store, _schedule(), player_stats=_player_stats(receiving_yards=60.0))
    assert engine.run(_bet_star_over)[0].outcome == Outcome.WIN

    store2 = PointInTimeStore(root=tmp_path / "b")
    _seed_two_players(store2)
    engine2 = BacktestEngine(store2, _schedule(), player_stats=_player_stats(receiving_yards=30.0))
    assert engine2.run(_bet_star_over)[0].outcome == Outcome.LOSS


def test_prop_settlement_matches_names_despite_punctuation(tmp_path):
    """Reuses prop_settlement.py's real name reconciliation -- book "AJ Brown"
    vs nflverse "A.J. Brown", the exact mismatch that module was built for.
    """
    store = PointInTimeStore(root=tmp_path)
    store.write([
        _prop_snap(ENTRY_TIME, "pinnacle", Side.OVER, -110, "AJ Brown"),
        _prop_snap(ENTRY_TIME, "pinnacle", Side.UNDER, -110, "AJ Brown"),
    ])
    engine = BacktestEngine(store, _schedule(), player_stats=_player_stats(player="A.J. Brown"))

    def _bet(dp):
        return BetOrder(
            market=Market.PLAYER_PROP, side=Side.OVER, line=45.5, book="pinnacle", stake=2.0,
            player_name="AJ Brown", prop_stat="receiving_yards",
        )

    assert engine.run(_bet)[0].outcome == Outcome.WIN


def test_prop_bet_without_player_stats_raises_rather_than_guessing(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    _seed_two_players(store)
    engine = BacktestEngine(store, _schedule())  # no player_stats
    with pytest.raises(ValueError, match="player_stats"):
        engine.run(_bet_star_over)


def test_prop_order_requires_player_fields():
    with pytest.raises(ValueError, match="player_name and prop_stat"):
        BetOrder(market=Market.PLAYER_PROP, side=Side.OVER, line=45.5, book="pinnacle", stake=2.0)


def test_mainline_order_rejects_player_fields():
    with pytest.raises(ValueError, match="must not carry"):
        BetOrder(
            market=Market.MONEYLINE, side=Side.HOME, line=None, book="pinnacle", stake=2.0,
            player_name="Someone", prop_stat="receiving_yards",
        )


# --- multiple bets per game + bankroll ---


def test_multiple_prop_bets_in_one_game_all_recorded(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    _seed_two_players(store)
    stats = pd.DataFrame([
        {"game_id": "2026_01_KC_LAC", "player_display_name": "Star Receiver", "receiving_yards": 60.0},
        {"game_id": "2026_01_KC_LAC", "player_display_name": "Backup Guy", "receiving_yards": 10.0},
    ])
    engine = BacktestEngine(store, _schedule(), player_stats=stats)

    def _bet_both(dp):
        return [
            BetOrder(market=Market.PLAYER_PROP, side=Side.OVER, line=45.5, book="pinnacle", stake=2.0,
                     player_name="Star Receiver", prop_stat="receiving_yards"),
            BetOrder(market=Market.PLAYER_PROP, side=Side.UNDER, line=45.5, book="pinnacle", stake=2.0,
                     player_name="Backup Guy", prop_stat="receiving_yards"),
        ]

    bets = engine.run(_bet_both)
    assert len(bets) == 2
    assert {b.player_name for b in bets} == {"Star Receiver", "Backup Guy"}
    assert all(b.outcome == Outcome.WIN for b in bets)  # 60 > 45.5 over, 10 < 45.5 under


def _both_over(dp):
    return [
        BetOrder(market=Market.PLAYER_PROP, side=Side.OVER, line=45.5, book="pinnacle", stake=2.0,
                 player_name="Star Receiver", prop_stat="receiving_yards"),
        BetOrder(market=Market.PLAYER_PROP, side=Side.OVER, line=45.5, book="pinnacle", stake=2.0,
                 player_name="Backup Guy", prop_stat="receiving_yards"),
    ]


def _stats_both(star_yards, backup_yards):
    return pd.DataFrame([
        {"game_id": "2026_01_KC_LAC", "player_display_name": "Star Receiver", "receiving_yards": star_yards},
        {"game_id": "2026_01_KC_LAC", "player_display_name": "Backup Guy", "receiving_yards": backup_yards},
    ])


def test_bankroll_is_tracked_across_bets_and_never_goes_negative(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    _seed_two_players(store)
    # Tiny bankroll: only one $2 bet is affordable at decision time.
    engine = BacktestEngine(store, _schedule(), player_stats=_stats_both(10.0, 10.0), bankroll=2.5)

    bets = engine.run(_both_over)
    assert len(bets) == 1  # second unaffordable: only 0.5 uncommitted at decision time
    assert bets[0].bankroll_before == 2.5
    assert bets[0].bankroll_after == pytest.approx(0.5)  # lost 2.0
    assert engine.bankroll >= 0


def test_simultaneous_bets_cannot_be_funded_by_each_others_winnings(tmp_path):
    """**The look-ahead regression test.** Two $2 bets placed at the SAME
    decision point on a $2.50 bankroll, both of which WIN.

    The pre-2026-08-23 engine credited each payout before checking the next
    order's affordability, so a winning first bet bankrolled the second and
    BOTH were placed -- meaning the backtester placed more bets precisely in
    the branch where earlier bets had won. Only one is actually affordable at
    decision time, regardless of how they later resolve.
    """
    store = PointInTimeStore(root=tmp_path)
    _seed_two_players(store)
    # 60 yards vs a 45.5 line -> both OVERs win.
    engine = BacktestEngine(store, _schedule(), player_stats=_stats_both(60.0, 60.0), bankroll=2.5)

    bets = engine.run(_both_over)

    assert len(bets) == 1, "a winning bet must not retroactively fund a simultaneous one"
    assert bets[0].outcome == Outcome.WIN


def test_outcome_does_not_change_which_bets_get_placed(tmp_path):
    """Same orders, same bankroll, opposite results -- the SET of placed bets
    must be identical, because affordability is decided before any of them
    can resolve. Any divergence is look-ahead by definition.
    """
    def _placed(star_yards, backup_yards, bankroll):
        store = PointInTimeStore(root=tmp_path / f"s{star_yards}{backup_yards}{bankroll}")
        _seed_two_players(store)
        engine = BacktestEngine(
            store, _schedule(), player_stats=_stats_both(star_yards, backup_yards), bankroll=bankroll
        )
        return [(b.player_name, b.stake) for b in engine.run(_both_over)]

    assert _placed(60.0, 60.0, 2.5) == _placed(10.0, 10.0, 2.5)  # all win vs all lose
    assert _placed(60.0, 10.0, 2.5) == _placed(10.0, 60.0, 2.5)  # split, either direction


def test_all_bets_at_one_decision_point_share_a_bankroll_before(tmp_path):
    """They were all placed at the same instant, so none of them had settled
    when the others were decided -- a running `bankroll_before` would imply a
    sequencing that did not happen.
    """
    store = PointInTimeStore(root=tmp_path)
    _seed_two_players(store)
    engine = BacktestEngine(store, _schedule(), player_stats=_stats_both(60.0, 60.0), bankroll=100.0)

    bets = engine.run(_both_over)
    assert len(bets) == 2
    assert {b.bankroll_before for b in bets} == {100.0}


def test_run_resets_bankroll_so_repeated_runs_are_reproducible(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    _seed_two_players(store)
    engine = BacktestEngine(store, _schedule(), player_stats=_player_stats(receiving_yards=10.0), bankroll=100.0)

    first = engine.run(_bet_star_over)
    second = engine.run(_bet_star_over)

    assert first[0].bankroll_before == second[0].bankroll_before == 100.0
    assert first[0].bankroll_after == second[0].bankroll_after
