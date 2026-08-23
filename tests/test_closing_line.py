from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest

from src.model.closing_line import (
    build_closing_line_frame,
    closing_fair_probabilities,
    evaluate_closing_line_model,
    fit_closing_line_model,
    predict_closing_prob,
)
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, OddsSnapshot, Side

KICKOFF = datetime(2024, 9, 8, 17, 0, tzinfo=UTC)
FEATURES = ["home_pre_elo", "away_pre_elo"]


def _ml(event_id, side, price, capture=None, book="pinnacle"):
    return OddsSnapshot.from_american(
        capture_time=capture or (KICKOFF.replace(hour=16)),
        event_id=event_id, season=2024, week=1, home_team="LAC", away_team="KC",
        event_start_time=KICKOFF, book=book, market=Market.MONEYLINE, side=side, price_american=price,
    )


def _training_frame(n=40, seed=0):
    """Synthetic pre-game features with a known linear relationship to the close,
    so the model has something real to recover.
    """
    rng = np.random.default_rng(seed)
    home = rng.normal(1500, 60, n)
    away = rng.normal(1500, 60, n)
    return pd.DataFrame({
        "game_id": [f"2024_01_G{i:03d}" for i in range(n)],
        "home_pre_elo": home,
        "away_pre_elo": away,
        "market_prob_home": np.clip(0.5 + (home - away) / 800, 0.05, 0.95),
    })


# --- closing probability extraction ----------------------------------------


def test_extracts_devigged_closing_probability(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    store.write([_ml("G1", Side.HOME, -110), _ml("G1", Side.AWAY, -110)])

    out = closing_fair_probabilities(store, ["G1"])
    assert len(out) == 1
    assert out.iloc[0]["close_fair_prob"] == pytest.approx(0.5, abs=1e-6)  # symmetric market


def test_uses_the_latest_snapshot_as_the_close(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    early, late = KICKOFF.replace(hour=8), KICKOFF.replace(hour=16)
    store.write([
        _ml("G1", Side.HOME, -110, capture=early), _ml("G1", Side.AWAY, -110, capture=early),
        _ml("G1", Side.HOME, -300, capture=late), _ml("G1", Side.AWAY, 250, capture=late),
    ])
    # The late (closing) quote is lopsided; if the early one were used we'd get ~0.5.
    assert closing_fair_probabilities(store, ["G1"]).iloc[0]["close_fair_prob"] > 0.65


def test_duplicate_snapshots_do_not_silently_drop_a_game(tmp_path):
    """Smoke-test reruns wrote identical rows at the same capture_time, and
    `latest_fair_prob` refuses to guess between duplicates -- without the dedup
    those games vanish from training with no error.
    """
    store = PointInTimeStore(root=tmp_path)
    dupes = [_ml("G1", Side.HOME, -110), _ml("G1", Side.AWAY, -110)]
    store.write(dupes)
    store.write(dupes)  # exact duplicates, same capture_time

    assert len(closing_fair_probabilities(store, ["G1"])) == 1


def test_games_with_no_close_are_omitted_not_imputed(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    store.write([_ml("G1", Side.HOME, -110), _ml("G1", Side.AWAY, -110)])
    out = closing_fair_probabilities(store, ["G1", "MISSING"])
    assert list(out["game_id"]) == ["G1"]


def test_one_sided_quote_is_omitted_rather_than_devigged_wrongly(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    store.write([_ml("G1", Side.HOME, -110)])  # no away side -> can't devig
    assert closing_fair_probabilities(store, ["G1"]).empty


# --- frame assembly ---------------------------------------------------------


def test_build_frame_inner_joins_and_drops_games_without_a_close(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    store.write([_ml("2024_01_G000", Side.HOME, -110), _ml("2024_01_G000", Side.AWAY, -110)])

    frame = build_closing_line_frame(_training_frame(n=5), store)
    assert len(frame) == 1  # only the one game with a real close survives
    assert "close_fair_prob" in frame.columns


# --- model ------------------------------------------------------------------


def _labelled_frame(n=200, seed=1, noise=0.01):
    """Features plus a close that genuinely depends on them, so a working model
    must recover the relationship rather than the mean.
    """
    frame = _training_frame(n=n, seed=seed)
    rng = np.random.default_rng(seed + 100)
    true = 0.5 + (frame["home_pre_elo"] - frame["away_pre_elo"]) / 800
    frame["close_fair_prob"] = np.clip(true + rng.normal(0, noise, n), 0.02, 0.98)
    return frame


def test_model_recovers_a_real_relationship_and_beats_the_naive_mean():
    frame = _labelled_frame(n=300)
    train, test = frame.iloc[:200], frame.iloc[200:]
    model = fit_closing_line_model(train, FEATURES)

    result = evaluate_closing_line_model(model, test, FEATURES)
    assert result["model"]["rmse"] < result["naive"]["rmse"]
    assert result["model"]["r2"] > 0.8


def test_predictions_are_clipped_to_valid_probabilities():
    """An unclipped linear model will happily predict >1 on extreme inputs."""
    frame = _labelled_frame(n=100)
    model = fit_closing_line_model(frame, FEATURES)
    extreme = pd.DataFrame({"home_pre_elo": [3000.0, 0.0], "away_pre_elo": [0.0, 3000.0]})
    preds = predict_closing_prob(model, extreme, FEATURES)
    assert np.all((preds > 0) & (preds < 1))


def test_evaluation_reports_the_own_outcome_model_baseline_when_available():
    """The comparison that decides whether this has independent value: does
    modelling the close beat just reading the market's own number?
    """
    frame = _labelled_frame(n=200)
    train, test = frame.iloc[:150], frame.iloc[150:]
    result = evaluate_closing_line_model(fit_closing_line_model(train, FEATURES), test, FEATURES)
    assert "own_outcome_model" in result
    assert set(result["own_outcome_model"]) == {"rmse", "mae", "r2"}


def test_evaluation_omits_the_market_baseline_when_the_column_is_absent():
    frame = _labelled_frame(n=120).drop(columns=["market_prob_home"])
    train, test = frame.iloc[:80], frame.iloc[80:]
    result = evaluate_closing_line_model(fit_closing_line_model(train, FEATURES), test, FEATURES)
    assert "own_outcome_model" not in result


def test_residuals_are_returned_for_downstream_strategy_use():
    """The residual (predicted close minus actual close), not the prediction, is
    what a strategy would actually trade on.
    """
    frame = _labelled_frame(n=150)
    train, test = frame.iloc[:100], frame.iloc[100:]
    result = evaluate_closing_line_model(fit_closing_line_model(train, FEATURES), test, FEATURES)
    assert len(result["residuals"]) == len(test)
    assert result["residuals"].mean() == pytest.approx(0.0, abs=0.05)


def test_pure_noise_target_yields_no_predictive_power():
    """Negative control: if the close is unrelated to the features, R^2 must not
    come back high. A model that 'works' on noise is measuring nothing.
    """
    frame = _training_frame(n=300, seed=5)
    rng = np.random.default_rng(9)
    frame["close_fair_prob"] = rng.uniform(0.2, 0.8, len(frame))  # independent of features
    train, test = frame.iloc[:200], frame.iloc[200:]

    result = evaluate_closing_line_model(fit_closing_line_model(train, FEATURES), test, FEATURES)
    assert result["model"]["r2"] < 0.2
