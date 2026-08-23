"""Historical mainline (h2h/spreads/totals) odds backfill.

**The rigor fix from methodology_backlog.md #8.** Every model comparison in
this project has scored "model vs. market" against nflverse's own bundled
`home_moneyline`/`spread_line` columns -- `src/model/train.py`'s own
docstring flags this as "NOT confirmed to be Pinnacle." This module pulls
real, confirmed-Pinnacle closing-line mainline odds via the historical
endpoint, so those comparisons can be re-scored against a real sharp price
instead of an unconfirmed one.

**Reuses the LIVE mainline parser, not a new one.** `src/collect/transform.py
::event_to_snapshots` already maps h2h/spreads/totals bookmaker responses
into `Market.MONEYLINE`/`SPREAD`/`TOTAL` `OddsSnapshot`s -- the historical
endpoint's response shape for a single event is the same shape the live
`get_event_odds` returns, just wrapped in an envelope
(`OddsApiClient.get_historical_event_odds` already unwraps this). Same
"reuse the live-verified parser against a historical response" pattern
`props_historical.py` uses for player props.

**Cost:** 10x the live per-event rate (10 x markets x regions), same
multiplier as the props historical endpoint. h2h+spreads+totals x 2 regions
(us,eu -- Pinnacle only shows up in `eu`, confirmed by a real test pull
2026-08-22 that came back with 16 US recreational books and zero Pinnacle
on `regions="us"` alone) = 60 credits/game -- the original
`mainline_historical_odds_reconsidered` memory's ~17,100-credit/~30-per-game
estimate assumed a single region and undercounted by 2x; real estimate for
the 570 2023-2024 test-set games is ~34,200 credits.

**Unverified against a real response until the first real pull** -- same
caveat `props_historical.py` carries, for the same reason (no way to call
the historical endpoint without paid access to test against).

**PARKED 2026-08-23 (audit verdict).** A completed one-shot pull -- the real
Pinnacle mainline odds were fetched and re-scored, and the gap turned out real
but numerically inconsequential (0.000138 Brier difference, corr 0.9976). It was
the *only* module in the repo with no importer, no make target and no notebook
reference. Nothing should wire it; re-running spends real paid credits.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import datetime, timedelta

from src.collect.client import OddsApiClient, OddsApiError, RateLimitExceeded
from src.collect.props_historical import find_historical_event_id
from src.collect.transform import MatchResult, TransformError, event_to_snapshots
from src.store.pit_store import PointInTimeStore
from src.store.schema import OddsSnapshot

log = logging.getLogger(__name__)

DEFAULT_MAINLINE_MARKETS = "h2h,spreads,totals"
DEFAULT_REGIONS = "us,eu"  # eu is required for Pinnacle -- regions="us" alone returns zero Pinnacle rows (confirmed by a real test pull, see module docstring)


def pull_historical_mainline_snapshot(
    client: OddsApiClient,
    event_id: str,
    date: str,
    match: MatchResult,
    markets: str = DEFAULT_MAINLINE_MARKETS,
    regions: str = DEFAULT_REGIONS,
) -> list[OddsSnapshot]:
    """One historical mainline snapshot (nearest available <= `date`) for
    one event -- mirrors `props_historical.py::pull_historical_prop_snapshot`
    but parses via `event_to_snapshots` (mainline schema) instead of
    `event_odds_to_prop_snapshots`.
    """
    response = client.get_historical_event_odds(event_id, date, regions, markets)
    event_data = response.events[0]
    return event_to_snapshots(event_data, response.fetched_at, match)


def backfill_historical_mainline(
    client: OddsApiClient,
    games: Iterable[tuple[MatchResult, str, str, datetime]],
    store: PointInTimeStore,
    markets: str = DEFAULT_MAINLINE_MARKETS,
    regions: str = DEFAULT_REGIONS,
    minutes_before_kickoff: int = 15,
) -> dict[str, int]:
    """`games`: iterable of (match, home_name, away_name, kickoff) -- same
    shape as `props_historical.py::backfill_historical_props`. Pulls one
    closing-line snapshot per game, `minutes_before_kickoff` before kickoff.
    """
    found = missing = failed = malformed = 0
    all_snapshots: list[OddsSnapshot] = []

    for match, home_name, away_name, kickoff in games:
        snapshot_date = (kickoff - timedelta(minutes=minutes_before_kickoff)).isoformat().replace("+00:00", "Z")
        event_id = find_historical_event_id(client, snapshot_date, home_name, away_name)
        if event_id is None:
            log.warning("historical mainline: no event found for %s @ %s on %s", away_name, home_name, snapshot_date)
            missing += 1
            continue

        try:
            snapshots = pull_historical_mainline_snapshot(client, event_id, snapshot_date, match, markets, regions)
        except (OddsApiError, RateLimitExceeded) as exc:
            log.error("historical mainline: failed to pull %s (%s): %s", event_id, match.event_id, exc)
            failed += 1
            continue
        except TransformError as exc:
            log.error("historical mainline: malformed response for %s (%s): %s", event_id, match.event_id, exc)
            malformed += 1
            continue

        found += 1
        all_snapshots.extend(snapshots)

    if all_snapshots:
        store.write(all_snapshots)

    log.info(
        "historical mainline backfill: wrote %d snapshots, found=%d missing=%d failed=%d malformed=%d",
        len(all_snapshots), found, missing, failed, malformed,
    )
    return {"found": found, "missing": missing, "failed": failed, "malformed": malformed, "written": len(all_snapshots)}
