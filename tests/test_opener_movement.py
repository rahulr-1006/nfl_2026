from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from src.backtest.opener_movement import bets, build_frame, movement_slope
from src.model.elo import DEFAULT_HOME_FIELD_ADVANTAGE, elo_win_probability
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, OddsSnapshot, Side

KO = datetime(2026, 10, 18, 17, 0, tzinfo=UTC)
T_EARLY = KO - timedelta(hours=120)
# With no rating history both teams sit at 1500, so the model is home edge only.
P_MODEL = elo_win_probability(1500, 1500, DEFAULT_HOME_FIELD_ADVANTAGE)  # ~0.568


class IdentityCalibration:
    """Platt map that returns the raw probability, so tests control p_model exactly."""

    def predict_proba(self, x):
        p = 1 / (1 + np.exp(-x[:, 0]))
        return np.column_stack([1 - p, p])


def _ml(event_id, side, price, capture, book="pinnacle"):
    return OddsSnapshot.from_american(
        capture_time=capture, event_id=event_id, season=2026, week=6, home_team="CLE", away_team="BAL",
        event_start_time=KO, book=book, market=Market.MONEYLINE, side=side, price_american=price,
    )


def _pair(event_id, home, away, capture, book="pinnacle"):
    return [_ml(event_id, Side.HOME, home, capture, book), _ml(event_id, Side.AWAY, away, capture, book)]


def _schedule(event_ids, home_score=24, away_score=17):
    return pd.DataFrame({"game_id": event_ids, "season": 2026, "week": 6, "home_team": "CLE", "away_team": "BAL",
                         "home_score": home_score, "away_score": away_score})


EMPTY_RATINGS = pd.DataFrame(columns=["game_id", "season", "home_team", "away_team", "home_pre_elo",
                                      "away_pre_elo", "home_post_elo", "away_post_elo"])


def _build(store, ids, **kw):
    kickoffs = pd.Series({e: pd.Timestamp(KO) for e in ids})
    return build_frame(store, _schedule(ids, **kw), kickoffs, ids, IdentityCalibration(), EMPTY_RATINGS,
                       now=KO + timedelta(days=1))


def test_early_price_ignores_snapshots_after_t_early(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    store.write(_pair("G1", 150, -170, T_EARLY - timedelta(hours=2)))      # the real early price
    store.write(_pair("G1", -300, 250, T_EARLY + timedelta(minutes=30)))   # after t_early: must not be used
    store.write(_pair("G1", 120, -140, KO - timedelta(minutes=20)))
    frame, _ = _build(store, ["G1"])
    assert frame.iloc[0]["early_capture"] == pd.Timestamp(T_EARLY - timedelta(hours=2))
    assert frame.iloc[0]["p_early"] < 0.45  # +150 home, not the -300 posted later


def test_stale_and_missing_early_prices_are_excluded_and_counted(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    store.write(_pair("STALE", 150, -170, T_EARLY - timedelta(hours=30)))
    store.write(_pair("STALE", 150, -170, KO - timedelta(minutes=20)))
    store.write(_pair("LATE", 150, -170, T_EARLY + timedelta(hours=1)))
    store.write(_pair("LATE", 150, -170, KO - timedelta(minutes=20)))
    frame, excluded = _build(store, ["STALE", "LATE"])
    assert frame.empty
    assert excluded["stale_early_price"] == 1 and excluded["no_early_price"] == 1


def _moving_store(tmp_path, close_home, close_away):
    """Home +150 early (p_early ~0.39 < p_model ~0.57), so the model takes home."""
    store = PointInTimeStore(root=tmp_path)
    store.write(_pair("G1", 150, -170, T_EARLY - timedelta(hours=1)))
    store.write(_pair("G1", 175, -205, T_EARLY - timedelta(hours=1), book="draftkings"))
    store.write(_pair("G1", close_home, close_away, KO - timedelta(minutes=20)))
    return store


def test_close_moving_toward_model_gives_positive_clv(tmp_path):
    frame, _ = _build(_moving_store(tmp_path, 110, -130), ["G1"])
    b = bets(frame, 0.02)
    assert b.iloc[0]["side"] == "home"
    assert b.iloc[0]["clv_move"] > 0
    assert b.iloc[0]["price"] == pytest.approx(2.75)  # best execution-book home price
    assert b.iloc[0]["realized"] == pytest.approx(1.75)  # home won 24-17


def test_close_moving_away_from_model_gives_negative_clv(tmp_path):
    frame, _ = _build(_moving_store(tmp_path, 220, -270), ["G1"])
    assert bets(frame, 0.02).iloc[0]["clv_move"] < 0


def test_tie_returns_zero(tmp_path):
    frame, _ = _build(_moving_store(tmp_path, 110, -130), ["G1"], home_score=20, away_score=20)
    assert bets(frame, 0.02).iloc[0]["realized"] == 0.0


def test_tau_filters_small_disagreements(tmp_path):
    frame, _ = _build(_moving_store(tmp_path, 110, -130), ["G1"])
    assert len(bets(frame, abs(frame.iloc[0]["d"]) + 0.01)) == 0


def test_movement_slope_sign():
    d = np.linspace(-0.1, 0.1, 50)
    toward = pd.DataFrame({"d": d, "m": 0.3 * d})
    away = pd.DataFrame({"d": d, "m": -0.3 * d})
    assert movement_slope(toward, n_resamples=200)["beta"] == pytest.approx(0.3)
    assert movement_slope(away, n_resamples=200)["beta"] == pytest.approx(-0.3)


def test_model_probability_is_home_edge_only_without_history(tmp_path):
    frame, _ = _build(_moving_store(tmp_path, 110, -130), ["G1"])
    assert frame.iloc[0]["p_model"] == pytest.approx(P_MODEL)
