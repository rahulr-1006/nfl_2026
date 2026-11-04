"""Date locks for pre-registered holdouts whose legs reach `data/shadow_log.jsonl`.

Two holdouts overlap the shared shadow log that `decision-report`, `clv-report`
and the notebooks read, so without a seal those reports would show their closing
numbers week by week before the scoring date:

- **Weeks 5-9 player props** (H1/H1b, preregistration_wk5-9.md). H1/H1b log to
  their own file, but `prop_ev` and `prop_arb` price the same contracts against the
  same Pinnacle close, so their Weeks 5-9 closing numbers are a preview of the H1
  result. The 2026-10-17 train run sealed every player-prop leg in those weeks for
  that reason (`scripts/train_wk10_14.py::sealed`). Until 2026-11-03 nothing else
  did: `clv-report` and `decision-report` showed them, and an ad hoc analysis that
  day printed them before anyone noticed. That is the gap this rule closes.
- **Weeks 10-14 `moneyline_ev`** (H5, preregistration_wk10-14.md).

The seal is applied in `shadow_clv.shadow_alerts_as_bets`, the one door every CLV
number for a shadow alert passes through. Each lifts on its own on its scoring date.

Survival (`shadow-report`, `first_recheck_frame`) is not sealed: the
pre-registrations allow operational checks that don't reveal the outcome.
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

# Mirrors `prereg_score.HOLDOUT_WEEKS` / `SCORE_NOT_BEFORE`. Not imported:
# prereg_score -> shadow_clv -> seals would be circular. tests/test_seals.py fails
# if the two ever disagree.
WK5_9_WEEKS = (5, 6, 7, 8, 9)
WK5_9_OPENS = datetime(2026, 11, 10, 0, 0, tzinfo=ZoneInfo("America/New_York"))
WK5_9_MARKET = "player_prop"

WK10_14_WEEKS = (10, 11, 12, 13, 14)
WK10_14_OPENS = datetime(2026, 12, 15, 0, 0, tzinfo=ZoneInfo("America/New_York"))
WK10_14_STRATEGIES = frozenset({"moneyline_ev"})


def _week(event_id: str) -> int | None:
    parts = str(event_id).split("_")
    if len(parts) < 2 or parts[0] != "2026":
        return None
    return int(parts[1])


def seal_reason(strategy: str | None, event_id: str, market: object = None,
                now: datetime | None = None) -> str | None:
    """Which holdout this alert's closing numbers belong to, or None if unsealed.

    `market` accepts a `Market` or its string value. Callers that omit it can
    only ever trip the strategy-based seal, never the market-based one.
    """
    week = _week(event_id)
    if week is None:
        return None
    now = now or datetime.now(UTC)
    if getattr(market, "value", market) == WK5_9_MARKET and week in WK5_9_WEEKS and now < WK5_9_OPENS:
        return "H1/H1b: Weeks 5-9 player props"
    if strategy in WK10_14_STRATEGIES and week in WK10_14_WEEKS and now < WK10_14_OPENS:
        return "H5: Weeks 10-14 moneyline_ev"
    return None


def withheld(strategy: str | None, event_id: str, now: datetime | None = None,
             market: object = None) -> bool:
    """True while this alert's closing numbers belong to an unscored holdout."""
    return seal_reason(strategy, event_id, market, now) is not None
