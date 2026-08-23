"""Live scanning for the team-total correlated-props edge.

**Why this exists: the edge had no way to be acted on.** `team_total_props.py`
produced this project's most rigorously validated finding -- underdog-bucket
team-total rushing (+5.5%) and passing (+12.9%), surviving chi-square, a
10K-shuffle permutation test, an honest 2023-train/2024-test split, and BH
correction inside a 69-p-value family. It was then wired to nothing, alongside
`correlated_props.price_bucket_bet`, the deliberately-gated pricing entrypoint
that no live code called. The 2026-08-23 architecture audit flagged both as
orphans. This closes that.

**The gate is the point, not an obstacle.** `price_bucket_bet` REFUSES to price
`favorite`/`heavy_favorite` buckets, because those failed an honest
out-of-sample check (one collapsed +19.2% -> +3.8%, the other flipped sign).
This scanner calls it without `allow_unvalidated`, so an unvalidated bucket
raises and is skipped rather than quietly alerted on. If a future check
validates those buckets, widen `VALIDATED_RELIABLE_BUCKETS` -- never pass the
override here.

**Blocked on live props until ~9/2**, same as `props_scan.py`: a team total is
built by summing real posted player lines, and those don't exist yet. Built and
tested ahead of the data for the same reason the props scheduler was -- so the
code path is exercised before it matters.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

import pandas as pd

from src.backtest.correlated_props import (
    UnvalidatedBucketError,
    bucket_favorite_strength,
    measure_prop_vig,
    price_bucket_bet,
)
from src.model.baseline import market_baseline
from src.signal.live_scan import upcoming_only
from src.store.pit_store import PointInTimeStore

# Lift by bucket, per stat, from the 2023-train fit in `team_total_props.py`'s
# validation -- TRAIN-ONLY values, deliberately not refit on everything, so a
# live bet is priced with a number that was never allowed to see its own
# outcome. Only validated buckets are listed; `price_bucket_bet` enforces that
# independently.
VALIDATED_TEAM_TOTAL_LIFT: Mapping[str, Mapping[str, float]] = {
    "rushing_yards": {"underdog": 1.226, "narrow": 1.149},
    "passing_yards": {"underdog": 1.311, "narrow": 0.950},
}
# Base rate of a team clearing its own summed prop line, measured on the real
# 2023-24 contracts (`team_total_props` build). Near 0.5 by construction, which
# is the expected result of summing balanced two-sided lines.
log = logging.getLogger(__name__)

PINNACLE_BOOK = "pinnacle"
DEFAULT_TEAM_TOTAL_BASE_RATE = 0.5
DEFAULT_EDGE_THRESHOLD = 0.03


def team_total_lines_from_store(
    store: PointInTimeStore, prop_stat: str, as_of: datetime | None = None
) -> pd.DataFrame:
    """Live implied team totals: per (event, team), the sum of every currently
    posted Pinnacle player line for `prop_stat`.

    Uses only the LATEST quote per player contract -- an earlier line that has
    since moved is not what you would be betting into. `upcoming_only` keeps
    finished games out, the same guard that fixed the 874-phantom-alert incident.
    """
    as_of = as_of or datetime.now(UTC)
    df = upcoming_only(store.read_as_of(as_of), as_of)
    if df.empty or "prop_stat" not in df.columns:
        return pd.DataFrame(columns=["event_id", "player_name", "line"])

    pin = df[(df["book"] == "pinnacle") & (df["market"] == "player_prop")
             & (df["prop_stat"] == prop_stat) & (df["side"] == "over")]
    if pin.empty:
        return pd.DataFrame(columns=["event_id", "player_name", "line"])

    latest = pin.loc[pin.groupby(["event_id", "player_name"])["capture_time"].idxmax()]
    return latest[["event_id", "player_name", "line", "capture_time"]]


def team_market_probabilities(store: PointInTimeStore, as_of: datetime | None = None) -> pd.DataFrame:
    """Per (event, side): Pinnacle's devigged moneyline win probability.

    This is the `team_market_prob` that decides which favorite-strength bucket a
    team falls in, and therefore whether it is priceable at all.
    """
    as_of = as_of or datetime.now(UTC)
    df = upcoming_only(store.read_as_of(as_of), as_of)
    if df.empty:
        return pd.DataFrame(columns=["event_id", "side", "team_market_prob"])

    ml = df[(df["book"] == "pinnacle") & (df["market"] == "moneyline")]
    if ml.empty:
        return pd.DataFrame(columns=["event_id", "side", "team_market_prob"])

    latest = ml.loc[ml.groupby(["event_id", "side"])["capture_time"].idxmax()]
    wide = latest.pivot_table(index="event_id", columns="side", values="price_american", aggfunc="first").dropna()
    if not {"home", "away"}.issubset(wide.columns):
        return pd.DataFrame(columns=["event_id", "side", "team_market_prob"])

    rows = []
    for event_id, r in wide.iterrows():
        prices = [int(r["home"]), int(r["away"])]
        for i, side in enumerate(("home", "away")):
            rows.append({"event_id": event_id, "side": side,
                         "team_market_prob": market_baseline(prices, side_index=i)})
    return pd.DataFrame(rows)


def measured_vig_by_event(
    store: PointInTimeStore, prop_stat: str, as_of: datetime | None = None, book: str = PINNACLE_BOOK
) -> dict[str, float]:
    """Vig measured per event from the SAME rows this scanner prices against,
    rather than a pooled constant.

    **Why this is not `MEASURED_PROP_VIG`.** That constant is one pooled mean
    over all of Pinnacle; real per-book median overround runs 6.47%-7.80%, and
    `bucket_edge` divides by `(1 + vig) ** 2`, so vig enters squared and a 1.5pp
    error becomes roughly a 3pp edge error -- in the self-flattering direction.
    An event whose vig cannot be measured returns no entry, and the caller skips
    it: the same "refuse rather than invent" discipline as `UnvalidatedBucketError`.
    """
    as_of = as_of or datetime.now(UTC)
    df = upcoming_only(store.read_as_of(as_of), as_of)
    if df.empty or "prop_stat" not in df.columns:
        return {}

    scoped = df[(df["market"] == "player_prop") & (df["prop_stat"] == prop_stat)]
    if scoped.empty:
        return {}

    out: dict[str, float] = {}
    for event_id, rows in scoped.groupby("event_id"):
        measured = measure_prop_vig(rows, book=book)
        if measured["n_contracts"] and measured["median_overround"] is not None:
            # Median, not mean: a single lopsided contract should not move the
            # vig applied to a whole game's pricing.
            out[str(event_id)] = float(measured["median_overround"])
    return out


def find_team_total_spots(
    store: PointInTimeStore,
    prop_stat: str = "rushing_yards",
    as_of: datetime | None = None,
    threshold: float = DEFAULT_EDGE_THRESHOLD,
    base_rate: float = DEFAULT_TEAM_TOTAL_BASE_RATE,
    lift_by_bucket: Mapping[str, Mapping[str, float]] = VALIDATED_TEAM_TOTAL_LIFT,
    bankroll: float = 100.0,
) -> pd.DataFrame:
    """Priceable team-total spots on upcoming games.

    Teams in unvalidated buckets are SKIPPED, not priced -- `price_bucket_bet`
    raises `UnvalidatedBucketError` and that exception is caught here rather
    than suppressed with `allow_unvalidated`. A skipped favorite is the gate
    working correctly, not a missed opportunity.
    """
    lifts = lift_by_bucket.get(prop_stat)
    if lifts is None:
        raise ValueError(f"no validated lift for prop_stat={prop_stat!r}; have {sorted(lift_by_bucket)}")

    lines = team_total_lines_from_store(store, prop_stat, as_of)
    probs = team_market_probabilities(store, as_of)
    if lines.empty or probs.empty:
        return pd.DataFrame()

    # Vig measured from the actual quotes being priced, per event -- never a
    # pooled constant. See `measured_vig_by_event` for why that distinction is
    # not cosmetic (vig enters `bucket_edge` squared).
    vig_by_event = measured_vig_by_event(store, prop_stat, as_of)

    rows = []
    for r in probs.itertuples():
        try:
            bucket = bucket_favorite_strength(r.team_market_prob)
        except ValueError:
            continue
        if bucket not in lifts:
            continue  # no TRAIN-fit lift for this bucket -- do not invent one
        vig = vig_by_event.get(str(r.event_id))
        if vig is None:
            continue  # no measurable vig for this game -- refuse rather than assume one
        try:
            priced = price_bucket_bet(
                r.team_market_prob, base_rate, dict(lifts), vig=vig, bankroll=bankroll
            )
        except UnvalidatedBucketError:
            continue  # the gate doing its job

        if priced["edge"] < threshold:
            continue
        rows.append({
            "event_id": r.event_id, "side": r.side, "prop_stat": prop_stat, "bucket": bucket,
            "team_market_prob": r.team_market_prob, "lift": priced["bucket_lift"],
            "edge": priced["edge"], "suggested_stake": priced["suggested_stake"], "vig": vig,
            "n_player_lines": int((lines["event_id"] == r.event_id).sum()),
        })

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("edge", ascending=False).reset_index(drop=True)


def format_team_total_alert(row: pd.Series) -> str:
    return (
        f"TEAM-TOTAL {row['edge'] * 100:.1f}% ({row['bucket']}): {row['event_id']} {row['side']} "
        f"{row['prop_stat']} | mkt_prob={row['team_market_prob']:.3f} lift={row['lift']:.3f} "
        f"| stake ${row['suggested_stake']:.2f} [{row['n_player_lines']} player lines]"
    )


def team_total_alert_key(row: pd.Series) -> str:
    return f"tt|{row['event_id']}|{row['side']}|{row['prop_stat']}|{row['bucket']}"


def available_stats(lift_by_bucket: Mapping[str, Mapping[str, float]] = VALIDATED_TEAM_TOTAL_LIFT) -> Sequence[str]:
    return sorted(lift_by_bucket)


def run(store_root: str = "data/snapshots", threshold: float = DEFAULT_EDGE_THRESHOLD) -> pd.DataFrame:
    """Scan every validated stat and print what is priceable right now.

    **Manual only, matching `middle_scan`/`steam_scan` and for the same stated
    reason:** this strategy has no live track record yet, so it is not trusted
    to an unattended alert channel. Reads local parquet only -- no Odds API
    cost, so it is free to run as often as you like.
    """
    store = PointInTimeStore(root=store_root)
    frames = []
    for stat in available_stats():
        spots = find_team_total_spots(store, prop_stat=stat, threshold=threshold)
        if not spots.empty:
            frames.append(spots)

    if not frames:
        log.info("team-total scan: no priceable spots (validated buckets only)")
        return pd.DataFrame()

    out = pd.concat(frames, ignore_index=True).sort_values("edge", ascending=False)
    for _, row in out.iterrows():
        log.info(format_team_total_alert(row))
    return out.reset_index(drop=True)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    run()


if __name__ == "__main__":
    main()
