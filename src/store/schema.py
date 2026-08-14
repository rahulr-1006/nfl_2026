"""Point-in-time odds snapshot schema.

One row = one price, for one side, at one book, as observed at one instant.
Rows are frozen (immutable) so the append-only contract is enforced at the
object level, not just by convention in the store layer. See src/store/pit_store.py
for the write/read rules that make this leakage-free.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, model_validator

from src.devig.convert import american_to_decimal, decimal_to_implied_prob


class Market(str, Enum):
    SPREAD = "spread"
    TOTAL = "total"
    MONEYLINE = "moneyline"


class Side(str, Enum):
    HOME = "home"
    AWAY = "away"
    OVER = "over"
    UNDER = "under"


class OddsSnapshot(BaseModel):
    """A single immutable price observation.

    `capture_time` is when we observed the price, not the game time.
    `event_id` should match the nflverse `game_id` convention
    (e.g. "2026_01_KC_LAC") so snapshots join cleanly to schedules/results.
    """

    model_config = ConfigDict(frozen=True)

    capture_time: datetime
    event_id: str
    season: int
    week: int
    home_team: str
    away_team: str
    event_start_time: datetime

    book: str
    market: Market
    side: Side
    line: float | None = None  # spread/total number; None for moneyline

    price_american: int
    price_decimal: float
    implied_prob_raw: float

    @model_validator(mode="after")
    def _check_consistency(self) -> OddsSnapshot:
        if self.capture_time.tzinfo is None:
            raise ValueError("capture_time must be tz-aware (use UTC)")
        if self.event_start_time.tzinfo is None:
            raise ValueError("event_start_time must be tz-aware (use UTC)")
        if self.market == Market.MONEYLINE and self.line is not None:
            raise ValueError("moneyline snapshots must not carry a line")
        if self.market != Market.MONEYLINE and self.line is None:
            raise ValueError(f"{self.market} snapshots require a line")

        expected_decimal = american_to_decimal(self.price_american)
        if abs(expected_decimal - self.price_decimal) > 1e-6:
            raise ValueError(
                f"price_decimal {self.price_decimal} inconsistent with "
                f"price_american {self.price_american} -> {expected_decimal}"
            )
        expected_prob = decimal_to_implied_prob(self.price_decimal)
        if abs(expected_prob - self.implied_prob_raw) > 1e-6:
            raise ValueError(
                f"implied_prob_raw {self.implied_prob_raw} inconsistent with "
                f"price_decimal {self.price_decimal} -> {expected_prob}"
            )
        return self

    @classmethod
    def from_american(
        cls,
        *,
        capture_time: datetime,
        event_id: str,
        season: int,
        week: int,
        home_team: str,
        away_team: str,
        event_start_time: datetime,
        book: str,
        market: Market,
        side: Side,
        price_american: int,
        line: float | None = None,
    ) -> OddsSnapshot:
        """Build a snapshot from an American price, deriving decimal + implied prob."""
        decimal = american_to_decimal(price_american)
        return cls(
            capture_time=capture_time,
            event_id=event_id,
            season=season,
            week=week,
            home_team=home_team,
            away_team=away_team,
            event_start_time=event_start_time,
            book=book,
            market=market,
            side=side,
            line=line,
            price_american=price_american,
            price_decimal=decimal,
            implied_prob_raw=decimal_to_implied_prob(decimal),
        )


def utcnow() -> datetime:
    return datetime.now(UTC)
