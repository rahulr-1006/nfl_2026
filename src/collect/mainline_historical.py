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

**UN-PARKED 2026-08-23 to buy real line movement.** It was parked as a completed
one-shot closing-line pull (the Pinnacle-vs-nflverse gap turned out real but
inconsequential: 0.000138 Brier, corr 0.9976). It is now the time-series pull.

**This overturns a claim repeated across this repo.** Ten places state that
historical CLV is "structurally impossible ... at any sample size". That was a
*cost* statement misfiled as an impossibility: `get_historical_event_odds` takes
an **arbitrary `date`** and returns the nearest 5-minute snapshot, so the series
was always purchasable -- nobody priced it. What is actually true is narrower:
*the data previously bought* is one snapshot per game, because each historical
call costs 10x the live rate and only the close was purchased.

**The economy that makes this affordable:** 570 games already have a near-kickoff
snapshot. We buy only the EARLIER points and pair them against a close already
paid for. At `10 x markets x regions`, `h2h,totals` over `us,eu` is 40 credits per
snapshot, so five offsets across ~105 games is ~21K -- fits the grant remainder
that expires unused at the 9/1 reset.

Still manual and still credit-spending: invoke deliberately, never on a schedule.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime, timedelta

from src.collect.client import OddsApiClient, OddsApiError, RateLimitExceeded
from src.collect.props_historical import find_historical_event_id
from src.collect.teams import load_team_name_map
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


# Hours before kickoff to buy. Spans the 5-day -> close window and lines up with
# the live schedule's tier boundaries (`props_budget.POLL_TARGETS`) so a historical
# series and a live one are directly comparable. The close itself is NOT here:
# 570 games already carry a ~15-minute-out snapshot, and re-buying it would be
# paying twice for a price we own.
DEFAULT_TIMESERIES_OFFSETS_HOURS = (120.0, 72.0, 48.0, 24.0, 6.0)

# 10x the live per-event rate, billed per (market x region) RETURNED.
HISTORICAL_COST_MULTIPLIER = 10


def estimate_pull_cost(n_games: int, markets: str, regions: str, offsets: Sequence[float]) -> int:
    """Credits a pull will cost, before spending any. One event-id lookup per
    game (1 credit, reused across every offset) plus one snapshot per offset.
    """
    per_snapshot = HISTORICAL_COST_MULTIPLIER * len(markets.split(",")) * len(regions.split(","))
    return n_games * (1 + per_snapshot * len(offsets))


def backfill_historical_mainline(
    client: OddsApiClient,
    games: Iterable[tuple[MatchResult, str, str, datetime]],
    store: PointInTimeStore,
    markets: str = DEFAULT_MAINLINE_MARKETS,
    regions: str = DEFAULT_REGIONS,
    offsets_hours: Sequence[float] = DEFAULT_TIMESERIES_OFFSETS_HOURS,
    max_credits: int | None = None,
) -> dict[str, int]:
    """`games`: iterable of (match, home_name, away_name, kickoff) -- same
    shape as `props_historical.py::backfill_historical_props`.

    Pulls one snapshot per offset in `offsets_hours`, giving a real
    **time series** per game rather than a lone close. The event-id lookup runs
    once per game and is reused across every offset -- it is 1 credit, but it is
    also the only call that does not scale with offsets.

    `max_credits` is a hard stop checked against the API's own reported
    `remaining_credits` as the run proceeds. Spending here is irreversible and a
    runaway loop would eat a grant that does not renew, so the cap is enforced
    mid-run, not just estimated up front.
    """
    found = missing = failed = malformed = 0
    all_snapshots: list[OddsSnapshot] = []
    # Sum each call's OWN reported cost rather than differencing `remaining`
    # against a baseline: the first response is already billed by the time it
    # arrives, so a baseline taken from it silently omits that charge (the probe
    # reported 160 against a true 201). The cap guards irreversible spending, so
    # it must not undercount.
    spent = 0

    for match, home_name, away_name, kickoff in games:
        # Look the event up once, at the earliest offset -- the id is stable, and
        # the earliest date is the one most likely to predate the book listing it,
        # so a miss here is a real "not listed yet" rather than a silent partial.
        lookup_date = _iso_z(kickoff - timedelta(hours=max(offsets_hours)))
        event_id = find_historical_event_id(client, lookup_date, home_name, away_name)
        spent += 1  # the events-list lookup is billed at 1 credit
        if event_id is None:
            log.warning("historical mainline: no event found for %s @ %s on %s", away_name, home_name, lookup_date)
            missing += 1
            continue

        game_snapshots: list[OddsSnapshot] = []
        for offset in offsets_hours:
            snapshot_date = _iso_z(kickoff - timedelta(hours=offset))
            try:
                response_snaps, cost = _pull_with_credits(
                    client, event_id, snapshot_date, match, markets, regions
                )
            except (OddsApiError, RateLimitExceeded) as exc:
                log.error("historical mainline: failed %s @ T-%sh (%s): %s", event_id, offset, match.event_id, exc)
                failed += 1
                continue
            except TransformError as exc:
                log.error("historical mainline: malformed %s @ T-%sh (%s): %s", event_id, offset, match.event_id, exc)
                malformed += 1
                continue

            game_snapshots.extend(response_snaps)
            spent += cost

        if max_credits is not None and spent >= max_credits:
            log.error("historical mainline: STOPPING -- spent %d credits, cap is %d", spent, max_credits)
            all_snapshots.extend(game_snapshots)
            break

        found += 1
        all_snapshots.extend(game_snapshots)

    if all_snapshots:
        store.write(all_snapshots)

    log.info(
        "historical mainline backfill: wrote %d snapshots across %d offset(s), "
        "found=%d missing=%d failed=%d malformed=%d spent=%d credits",
        len(all_snapshots), len(offsets_hours), found, missing, failed, malformed, spent,
    )
    return {"found": found, "missing": missing, "failed": failed, "malformed": malformed,
            "written": len(all_snapshots), "credits_spent": spent}


def _iso_z(when: datetime) -> str:
    """The API wants a Z-suffixed UTC instant, not a +00:00 offset."""
    return when.isoformat().replace("+00:00", "Z")


def _pull_with_credits(
    client: OddsApiClient, event_id: str, date: str, match: MatchResult, markets: str, regions: str
) -> tuple[list[OddsSnapshot], int]:
    """One snapshot plus THIS call's own billed cost, so the caller can enforce a
    spend cap by summing real charges rather than inferring them from a balance.
    """
    response = client.get_historical_event_odds(event_id, date, regions, markets)
    snaps = event_to_snapshots(response.events[0], response.fetched_at, match)
    return snaps, response.last_cost or 0


def select_games_with_a_close(
    store: PointInTimeStore, season: int, n_games: int, schedule_path: str
) -> list[tuple[MatchResult, str, str, datetime]]:
    """The `n_games` 2024 events that already hold a closing snapshot, spread
    EVENLY across the season rather than taking the first N.

    Even spacing matters: line-movement behaviour is not week-invariant (week 1
    prices off an offseason, late weeks price off playoff leverage and resting
    starters), so a contiguous block would measure one regime and call it the
    season. Every event returned already owns its close, which is the whole
    reason this pull is affordable.
    """
    df = store.read_as_of(datetime.now(UTC))
    ml = df[(df["market"] == "moneyline") & (df["season"] == season)]
    if ml.empty:
        return []

    per_event = ml.groupby("event_id").agg(
        kickoff=("event_start_time", "max"), home=("home_team", "first"),
        away=("away_team", "first"), week=("week", "first"),
        n_captures=("capture_time", "nunique"),
    ).sort_values("kickoff")

    # Skip anything that ALREADY has a series. This makes the pull resumable: an
    # interrupted or repeated run continues where it stopped instead of re-buying
    # snapshots it holds, which at 201 credits/game against a non-renewing grant
    # is the difference between a retry and a loss.
    already_done = per_event[per_event["n_captures"] > 1]
    if len(already_done):
        log.info("skipping %d game(s) that already have a time series", len(already_done))
    per_event = per_event[per_event["n_captures"] <= 1]

    abbr_to_name = {abbr: name for name, abbr in load_team_name_map(season, schedule_path).items()}

    rows = list(per_event.itertuples())
    step = max(1, len(rows) // n_games)
    chosen = rows[::step][:n_games]

    out = []
    for r in chosen:
        home_name, away_name = abbr_to_name.get(r.home), abbr_to_name.get(r.away)
        if not home_name or not away_name:
            log.warning("no Odds API name for %s/%s -- skipping %s", r.home, r.away, r.Index)
            continue
        match = MatchResult(event_id=r.Index, season=season, week=int(r.week),
                            home_abbr=r.home, away_abbr=r.away)
        out.append((match, home_name, away_name, r.kickoff.to_pydatetime()))
    return out


def main() -> None:
    import argparse
    import os

    from dotenv import load_dotenv

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    load_dotenv()

    ap = argparse.ArgumentParser(description="Buy a historical mainline TIME SERIES (spends real credits).")
    ap.add_argument("--games", type=int, default=105)
    ap.add_argument("--season", type=int, default=2024, help="2025 is the untouched holdout -- do not pull it")
    ap.add_argument("--markets", default="h2h,totals")
    ap.add_argument("--regions", default=DEFAULT_REGIONS)
    ap.add_argument("--offsets", default=",".join(str(o) for o in DEFAULT_TIMESERIES_OFFSETS_HOURS),
                    help="hours before kickoff, comma separated")
    ap.add_argument("--max-credits", type=int, default=22_000)
    ap.add_argument("--store-root", default="data/snapshots")
    ap.add_argument("--schedule", default="data/static/schedules_2015_2025.parquet")
    ap.add_argument("--dry-run", action="store_true", help="estimate cost and exit, spending nothing")
    ap.add_argument("--probe", action="store_true", help="pull ONE game only, to verify cost and timestamps")
    a = ap.parse_args()

    if a.season >= 2025:
        ap.error(f"season {a.season} is the untouched research holdout -- refusing to pull it")

    offsets = tuple(float(x) for x in a.offsets.split(","))
    store = PointInTimeStore(root=a.store_root)
    games = select_games_with_a_close(store, a.season, a.games, a.schedule)
    if not games:
        ap.error(f"no {a.season} games with a closing snapshot found in {a.store_root}")

    if a.probe:
        games = games[:1]
    estimate = estimate_pull_cost(len(games), a.markets, a.regions, offsets)
    log.info("PLAN: %d game(s) x %d offset(s) of %r over %r -> ~%d credits (cap %d)",
             len(games), len(offsets), a.markets, a.regions, estimate, a.max_credits)

    if a.dry_run:
        log.info("dry run -- nothing spent")
        return
    if estimate > a.max_credits:
        ap.error(f"estimate {estimate} exceeds cap {a.max_credits} -- lower --games or --offsets")

    api_key = os.environ.get("ODDS_API_KEY_PAID")
    if not api_key:
        raise ValueError("ODDS_API_KEY_PAID is not set -- historical pulls use the paid key, "
                         "never ODDS_API_KEY, which the mainline collector needs")

    result = backfill_historical_mainline(
        OddsApiClient(api_key), games, store,
        markets=a.markets, regions=a.regions, offsets_hours=offsets, max_credits=a.max_credits,
    )
    log.info("RESULT: %s", result)


if __name__ == "__main__":
    main()
