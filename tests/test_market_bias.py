import pandas as pd
import pytest

from src.backtest.market_bias import evaluate, h7_bets, h8_bets, passes_stability


def _games(**overrides):
    base = {
        "game_id": ["g1", "g2", "g3", "g4"], "season": 2020, "game_type": "REG",
        "home_moneyline": [-150, -500, 120, -110], "away_moneyline": [130, 400, -140, -110],
        "home_score": [17, 30, 10, 20], "away_score": [20, 10, 24, 20],
        "roof": ["outdoors", "outdoors", "dome", "open"], "wind": [12.0, 5.0, 20.0, 15.0],
        "total_line": [44.5, 40.0, 50.0, 40.0], "under_odds": [-110, -110, -110, -105],
        "over_odds": [-110, -110, -110, -115],
    }
    base.update(overrides)
    return pd.DataFrame(base)


def test_h7_bets_away_only_inside_the_band():
    b = h7_bets(_games())
    # g2's home side is ~0.81, outside [0.30, 0.70].
    assert set(b["game_id"]) == {"g1", "g3", "g4"}
    assert (b["side"] == "away").all()
    g1 = b.set_index("game_id").loc["g1"]
    assert g1["price_decimal"] == pytest.approx(2.30)
    assert g1["won"] and g1["ret"] == pytest.approx(1.30)


def test_h7_tie_is_a_push():
    b = h7_bets(_games()).set_index("game_id")
    assert b.loc["g4", "push"] and b.loc["g4", "ret"] == 0.0


def test_h8_requires_outdoor_and_wind_threshold():
    b = h8_bets(_games(), 10.0)
    # g2 too calm, g3 is a dome; g1 and g4 qualify.
    assert set(b["game_id"]) == {"g1", "g4"}
    g1 = b.set_index("game_id").loc["g1"]
    assert g1["won"]  # 37 points < 44.5
    g4 = b.set_index("game_id").loc["g4"]
    assert g4["push"]  # 40 points == 40.0


def test_h8_higher_threshold_drops_games():
    assert set(h8_bets(_games(), 15.0)["game_id"]) == {"g4"}


def test_evaluate_excludes_pushes_and_gates_on_stability():
    rows = []
    for season in range(2015, 2025):
        for i in range(4):
            rows.append({"game_id": f"{season}_{i}", "season": season, "price_decimal": 1.91,
                         "opposite_price_decimal": 1.91, "fair_prob": 0.5, "margin": 1 if i < 3 else -1})
    rows.append({"game_id": "push", "season": 2015, "price_decimal": 1.91, "opposite_price_decimal": 1.91,
                 "fair_prob": 0.5, "margin": 0})
    from src.backtest.market_bias import _settle
    r = evaluate(_settle(pd.DataFrame(rows)), n_resamples=200, n_null=200)
    assert r["n"] == 40 and r["pushes"] == 1
    assert r["roi"] > 0 and r["seasons_positive"] == 10
    assert passes_stability(r)
    assert not passes_stability({**r, "seasons_positive": 5})
