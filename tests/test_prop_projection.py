import numpy as np
import pandas as pd
import pytest

from src.model.prop_projection import (
    build_prop_training_frame,
    fit_prop_model,
    predict_over_probability,
    prior_form,
    to_bet_frame,
)


def _player_games(name="Player A", values=(10, 20, 30, 40, 50), season=2024):
    return pd.DataFrame({
        "game_id": [f"{season}_{w:02d}_G" for w in range(1, len(values) + 1)],
        "player_display_name": [name] * len(values),
        "season": [season] * len(values),
        "week": list(range(1, len(values) + 1)),
        "receiving_yards": list(values),
    })


# --- leakage discipline: the single most important property here ------------


def test_prior_form_never_includes_the_current_game():
    """`.shift(1)` after the expanding aggregate is what makes this safe. Without
    it a player's own current game leaks into the feature predicting it, which
    would produce a spectacular and entirely fake result.
    """
    form = prior_form(_player_games(values=(10, 20, 30, 40, 50)), "receiving_yards", min_games=1)
    # Week 4's prior mean must be mean(10,20,30) = 20, NOT mean(10,20,30,40) = 25.
    wk4 = form[form["week"] == 4].iloc[0]
    assert wk4["prior_mean"] == pytest.approx(20.0)
    assert wk4["prior_games"] == 3


def test_first_games_are_dropped_not_imputed():
    form = prior_form(_player_games(values=(10, 20, 30, 40, 50)), "receiving_yards", min_games=3)
    assert form["week"].min() == 4  # weeks 1-3 lack 3 prior games
    assert form["prior_mean"].notna().all()


def test_players_are_kept_independent():
    a = _player_games("Player A", (100, 100, 100, 100))
    b = _player_games("Player B", (1, 1, 1, 1))
    b["game_id"] = a["game_id"].values  # same games, different players
    form = prior_form(pd.concat([a, b], ignore_index=True), "receiving_yards", min_games=3)

    assert form[form["player_display_name"] == "Player A"]["prior_mean"].iloc[0] == pytest.approx(100.0)
    assert form[form["player_display_name"] == "Player B"]["prior_mean"].iloc[0] == pytest.approx(1.0)


def test_prior_form_respects_chronological_order_regardless_of_input_order():
    shuffled = _player_games(values=(10, 20, 30, 40, 50)).sample(frac=1, random_state=0)
    form = prior_form(shuffled, "receiving_yards", min_games=1)
    assert form[form["week"] == 4].iloc[0]["prior_mean"] == pytest.approx(20.0)


# --- frame assembly ---------------------------------------------------------


def _contracts(lines):
    return pd.DataFrame({
        "game_id": [f"2024_{w:02d}_G" for w in range(1, len(lines) + 1)],
        "player_display_name": ["Player A"] * len(lines),
        "line": list(lines),
    })


def test_went_over_label_matches_the_realized_stat():
    games = _player_games(values=(10, 20, 30, 40, 50))
    frame = build_prop_training_frame(_contracts([5, 5, 5, 35, 100]), games, "receiving_yards", min_games=3)
    # Only weeks 4-5 survive min_games; week 4 actual=40 vs line 35 -> over,
    # week 5 actual=50 vs line 100 -> under.
    assert list(frame.sort_values("week")["went_over"]) == [True, False]


def test_line_vs_prior_mean_is_the_books_disagreement_with_recent_form():
    games = _player_games(values=(10, 10, 10, 10, 10))
    frame = build_prop_training_frame(_contracts([0, 0, 0, 25, 25]), games, "receiving_yards", min_games=3)
    # prior mean is 10; a line of 25 means the book expects far more than form.
    assert frame["line_vs_prior_mean"].iloc[0] == pytest.approx(15.0)


def test_contracts_without_enough_history_are_dropped():
    games = _player_games(values=(10, 20, 30, 40, 50))
    frame = build_prop_training_frame(_contracts([5] * 5), games, "receiving_yards", min_games=4)
    assert len(frame) == 1  # only week 5 has 4 prior games


# --- model ------------------------------------------------------------------


def _synthetic_frame(n=400, seed=0, signal=True):
    """Contracts where going over IS (or is not) predictable from how the line
    compares to prior form.
    """
    rng = np.random.default_rng(seed)
    prior_mean = rng.uniform(20, 80, n)
    line = prior_mean + rng.normal(0, 15, n)
    p_over = 1 / (1 + np.exp((line - prior_mean) / 8)) if signal else np.full(n, 0.5)
    return pd.DataFrame({
        "prior_mean": prior_mean,
        "prior_std": rng.uniform(5, 20, n),
        "prior_games": rng.integers(3, 16, n),
        "line": line,
        "line_vs_prior_mean": line - prior_mean,
        "went_over": rng.random(n) < p_over,
    })


def test_model_learns_a_real_relationship_when_one_exists():
    frame = _synthetic_frame(600, signal=True)
    train, test = frame.iloc[:400], frame.iloc[400:]
    probs = predict_over_probability(fit_prop_model(train), test)

    # A line far above prior form should imply a low P(over).
    assert np.corrcoef(test["line_vs_prior_mean"], probs)[0, 1] < -0.5
    assert ((probs > 0) & (probs < 1)).all()


def test_model_finds_nothing_when_the_label_is_noise():
    """Negative control -- a model that 'works' on pure noise measures nothing."""
    frame = _synthetic_frame(600, seed=3, signal=False)
    train, test = frame.iloc[:400], frame.iloc[400:]
    probs = predict_over_probability(fit_prop_model(train), test)
    accuracy = ((probs >= 0.5) == test["went_over"]).mean()
    assert 0.40 < accuracy < 0.60  # indistinguishable from a coin flip


# --- bet frame --------------------------------------------------------------


def test_bet_frame_takes_the_side_the_model_prefers_with_that_sides_price():
    df = pd.DataFrame({
        "went_over": [True, False],
        "over_price_decimal": [2.0, 2.0],
        "under_price_decimal": [1.8, 1.8],
    })
    out = to_bet_frame(df, np.array([0.7, 0.3]))

    assert list(out["side"]) == ["over", "under"]
    assert out["fair_prob"].tolist() == [pytest.approx(0.7), pytest.approx(0.7)]  # prob OF the side taken
    assert out["price_decimal"].tolist() == [2.0, 1.8]
    assert list(out["won"]) == [True, True]  # over won; under won when it didn't go over


def test_bet_frame_output_is_accepted_by_the_evaluation_harness():
    """The whole point of this shape -- projections must flow straight into the
    Phase 2 bettability check without reshaping.
    """
    from src.backtest.evaluation import evaluate_at_threshold

    df = pd.DataFrame({
        "went_over": [True, False, True, False] * 10,
        "over_price_decimal": [1.91] * 40,
        "under_price_decimal": [1.91] * 40,
    })
    bets = to_bet_frame(df, np.linspace(0.3, 0.7, 40))
    result = evaluate_at_threshold(bets, threshold=0.0)
    assert result["n_bets"] > 0
