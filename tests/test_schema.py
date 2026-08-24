from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.store.schema import Market, OddsSnapshot, Side, american_to_decimal


def _snap(**overrides):
    defaults = {
        "capture_time": datetime(2026, 9, 4, 12, 0, tzinfo=UTC),
        "event_id": "2026_01_KC_LAC",
        "season": 2026,
        "week": 1,
        "home_team": "LAC",
        "away_team": "KC",
        "event_start_time": datetime(2026, 9, 5, 0, 20, tzinfo=UTC),
        "book": "pinnacle",
        "market": Market.SPREAD,
        "side": Side.HOME,
        "price_american": -110,
    }
    defaults.update(overrides)
    return OddsSnapshot.from_american(**defaults, line=-2.5)


def test_from_american_derives_decimal_and_prob():
    snap = _snap()
    assert snap.price_decimal == pytest.approx(1 + 100 / 110)
    assert snap.implied_prob_raw == pytest.approx(1 / snap.price_decimal)


def test_favorite_and_underdog_decimal_conversion():
    assert american_to_decimal(-110) == pytest.approx(1.9090909, rel=1e-6)
    assert american_to_decimal(150) == pytest.approx(2.5)


def test_frozen_snapshot_cannot_be_mutated():
    snap = _snap()
    with pytest.raises(ValidationError):
        snap.price_american = -120


def test_naive_capture_time_rejected():
    with pytest.raises(ValidationError):
        OddsSnapshot.from_american(
            capture_time=datetime(2026, 9, 4, 12, 0),  # noqa: DTZ001 -- naive on purpose
            event_id="2026_01_KC_LAC",
            season=2026,
            week=1,
            home_team="LAC",
            away_team="KC",
            event_start_time=datetime(2026, 9, 5, 0, 20, tzinfo=UTC),
            book="pinnacle",
            market=Market.SPREAD,
            side=Side.HOME,
            price_american=-110,
            line=-2.5,
        )


def test_moneyline_rejects_line():
    with pytest.raises(ValidationError):
        _snap(market=Market.MONEYLINE, side=Side.HOME, price_american=-150)


def test_non_moneyline_requires_line():
    with pytest.raises(ValidationError):
        OddsSnapshot.from_american(
            capture_time=datetime(2026, 9, 4, 12, 0, tzinfo=UTC),
            event_id="2026_01_KC_LAC",
            season=2026,
            week=1,
            home_team="LAC",
            away_team="KC",
            event_start_time=datetime(2026, 9, 5, 0, 20, tzinfo=UTC),
            book="pinnacle",
            market=Market.SPREAD,
            side=Side.HOME,
            price_american=-110,
            line=None,
        )
