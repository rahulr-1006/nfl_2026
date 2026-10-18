"""Date locks for pre-registered holdouts that share `data/shadow_log.jsonl`.

H1/H1b log to their own file, so the Weeks 5-9 holdout never needed this. H5
(preregistration_wk10-14.md) is `moneyline_ev`, which logs to the shared shadow
log that `decision-report` and `clv-report` read, so without a seal those reports
would show its closing numbers week by week through the holdout. The seal is
applied in `shadow_clv.shadow_alerts_as_bets`, the one door every CLV number for
a shadow alert passes through. It lifts on its own on the scoring date.

Survival (`shadow-report`, `first_recheck_frame`) is not sealed: the
pre-registration allows operational checks that don't reveal the outcome.
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

WK10_14_WEEKS = (10, 11, 12, 13, 14)
WK10_14_OPENS = datetime(2026, 12, 15, 0, 0, tzinfo=ZoneInfo("America/New_York"))
WK10_14_STRATEGIES = frozenset({"moneyline_ev"})


def withheld(strategy: str | None, event_id: str, now: datetime | None = None) -> bool:
    """True while this alert's closing numbers belong to an unscored holdout."""
    if strategy not in WK10_14_STRATEGIES or not str(event_id).startswith("2026_"):
        return False
    week = int(str(event_id).split("_")[1])
    return week in WK10_14_WEEKS and (now or datetime.now(UTC)) < WK10_14_OPENS
