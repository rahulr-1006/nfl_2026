"""Shadow execution log: did the alerted price survive the detection latency?

**The one question live betting cannot answer by observation.** This project can
measure that an arb *existed* (65 real spots, 2023-24) and that books disagree
structurally rather than randomly. What it has never measured is whether a spot
is still on the board by the time a human can act on it.

That gap is not incidental, it is architectural. The alert path is:

    price appears
      -> up to 30 min   (ARB_POLL_INTERVAL_HOURS 0.5h, floored by
                         props_scheduler.DEFAULT_TICK_MINUTES = 30.0)
      -> up to  5 min   (com.nflclv.monitor StartInterval 300s)
      = ~35 min worst case before the text is sent

Every historical prop row in this repo is a single ~20-minutes-to-kickoff
snapshot, so price persistence has never been observable in the data at all. It
can only be measured live, forward, once -- the same reason props rolling CLV had
to wait for the season.

## What this measures, and what it does NOT

**Measures:** whether the same contract, at the same book, still carries a price
at least as good as the alerted one at the next observation.

**Does NOT measure whether *you* could have taken it.** A price persisting in the
Odds API feed is an UPPER BOUND on capturability. A real attempt can still fail on
stake limits, a restricted account, or the book pulling the line for one customer
while the screen price stands. Read a survival rate here as "the market did not
move away", never as "this bet was available".

**Resolution is bounded by the poll cadence.** Re-checks read the store, never the
API, so they cost 0 credits -- but the store only advances when the collector
polls. Inside the arb window that is every 30 minutes, so "survived" means
"survived to the next observation", not "survived continuously". Sub-poll
round-trips are invisible here and always will be at this cadence.

## Why append-only observations rather than mutable alert rows

Each row is one (leg, moment) pair and is never rewritten -- the same discipline
as `src/store/bet_log.py`, for the same reason: a mutable "current price" field
would silently overwrite the evidence being collected. Survival is derived by
grouping on `alert_key`, not by updating a row in place.

**One row per LEG, not per alert.** An arb is two legs at two books, and it is
only real if both are placed -- so a two-leg alert whose over leg survives and
whose under leg vanishes did NOT survive. Recording legs separately makes that
the natural reading; an alert-level price column could not express it.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, field_validator

from src.signal.live_scan import upcoming_only
from src.store.bet_log import STRATEGIES
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, Side

log = logging.getLogger(__name__)

SHADOW_LOG_PATH = Path("data/shadow_log.jsonl")

# How long to keep re-checking an alert. Past this it is no longer telling us
# anything about detection latency -- a spot that survived 6h was never
# latency-sensitive in the first place, which is itself the finding.
DEFAULT_RECHECK_HORIZON = timedelta(hours=6)

# Contract identity, shared by props and mainline. `line`/`player_name`/
# `prop_stat` are None for moneyline, which is why they cannot be dropped from
# the key: two prop contracts on the same player differ only by stat and line
# (this exact omission once made a passing_tds and a rushing_yards contract at
# the same line look like one contract with two prices).
_CONTRACT_COLS = ("event_id", "book", "side", "player_name", "prop_stat", "line")


class ShadowObservation(BaseModel):
    """One leg of one alerted spot, as seen at one moment. Never rewritten."""

    alert_key: str
    strategy: str
    leg: str  # "over"/"under" for a two-leg arb, "single" otherwise
    alerted_at: datetime
    observed_at: datetime
    is_alert: bool

    event_id: str
    market: Market
    side: Side
    book: str
    price_american: int | None  # None = contract no longer quoted at this book
    line: float | None = None
    player_name: str | None = None
    prop_stat: str | None = None

    edge: float | None = None
    # The market's own clock, not ours. `observed_at` is when this process
    # looked; `capture_time` is when the price was actually sampled. Latency
    # must be measured against the latter -- using `observed_at` would credit
    # the scan schedule with freshness the data does not have.
    capture_time: datetime | None = None

    @field_validator("strategy")
    @classmethod
    def _known_strategy(cls, v: str) -> str:
        if v not in STRATEGIES:
            raise ValueError(f"unknown strategy {v!r}; expected one of {sorted(STRATEGIES)}")
        return v

    @field_validator("alerted_at", "observed_at")
    @classmethod
    def _tz_aware(cls, v: datetime) -> datetime:
        # Naive timestamps compare wrong against the store's UTC capture_time,
        # which would corrupt every elapsed-time number derived from them.
        if v.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware (use UTC)")
        return v


def legs_from_spot(row: pd.Series, strategy: str, alert_key: str) -> list[dict[str, Any]]:
    """Split one scanner row into its leg(s).

    Arb rows carry `book_over`/`book_under` and a price per side; every other
    scanner emits a single `side`/`book`/`price_american`. Detecting on the
    presence of `book_over` mirrors `props_scan.prop_alert_key`, so the two
    cannot disagree about what shape a row is.
    """
    is_prop = "player_name" in row.index and pd.notna(row.get("player_name"))
    market = Market.PLAYER_PROP if is_prop else Market.MONEYLINE
    common = {
        "alert_key": alert_key,
        "strategy": strategy,
        "event_id": str(row["event_id"]),
        "market": market,
        "line": float(row["line"]) if "line" in row.index and pd.notna(row.get("line")) else None,
        "player_name": str(row["player_name"]) if is_prop else None,
        "prop_stat": str(row["prop_stat"]) if is_prop and pd.notna(row.get("prop_stat")) else None,
    }

    if "book_over" in row.index:  # two-leg arb
        return [
            {**common, "leg": "over", "side": Side.OVER, "book": str(row["book_over"]),
             "price_american": int(row["price_american_over"]),
             "edge": float(row["arb_margin"]) if pd.notna(row.get("arb_margin")) else None},
            {**common, "leg": "under", "side": Side.UNDER, "book": str(row["book_under"]),
             "price_american": int(row["price_american_under"]),
             "edge": float(row["arb_margin"]) if pd.notna(row.get("arb_margin")) else None},
        ]

    return [{
        **common, "leg": "single", "side": Side(str(row["side"])), "book": str(row["book"]),
        "price_american": int(row["price_american"]),
        "edge": float(row["edge"]) if "edge" in row.index and pd.notna(row.get("edge")) else None,
    }]


def append(observations: list[ShadowObservation], path: Path = SHADOW_LOG_PATH) -> int:
    """Append observations. Creates the file on first use."""
    if not observations:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for obs in observations:
            fh.write(obs.model_dump_json() + "\n")
    return len(observations)


def load(path: Path = SHADOW_LOG_PATH) -> list[ShadowObservation]:
    """Every observation, oldest first. A missing file is an empty log, not an
    error -- this is read by unattended reporting.
    """
    if not path.exists():
        return []
    obs = [
        ShadowObservation.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return sorted(obs, key=lambda o: o.observed_at)


def record_alert(
    spots: pd.DataFrame,
    strategy: str,
    key_fn,
    now: datetime | None = None,
    path: Path = SHADOW_LOG_PATH,
    capture_times: pd.Series | None = None,
) -> int:
    """Record the originating observation for each alerted spot.

    `key_fn` is the scanner's own dedup key function (e.g.
    `props_scan.prop_alert_key`), reused rather than reimplemented so a shadow
    row and its alert can never key differently.
    """
    if spots.empty:
        return 0
    now = now or datetime.now(UTC)
    rows: list[ShadowObservation] = []
    for idx, row in spots.iterrows():
        key = key_fn(row)
        ct = row.get("capture_time") if "capture_time" in row.index else None
        if capture_times is not None and idx in capture_times.index:
            ct = capture_times.loc[idx]
        for leg in legs_from_spot(row, strategy, key):
            rows.append(ShadowObservation(
                **leg, alerted_at=now, observed_at=now, is_alert=True,
                capture_time=pd.Timestamp(ct).to_pydatetime() if ct is not None and pd.notna(ct) else None,
            ))
    n = append(rows, path)
    log.info("shadow log: recorded %d leg(s) for %d %s alert(s)", n, len(spots), strategy)
    return n


def _latest_price(props: pd.DataFrame, leg: ShadowObservation) -> tuple[int | None, datetime | None]:
    """Newest price for this exact contract at this exact book, or (None, None)
    if it is no longer quoted -- which is itself the measurement, not a failure.
    """
    m = (props["event_id"] == leg.event_id) & (props["book"] == leg.book) & (props["side"] == leg.side.value)
    if leg.player_name is not None:
        m &= props["player_name"] == leg.player_name
        m &= props["prop_stat"] == leg.prop_stat
    if leg.line is not None:
        m &= props["line"] == leg.line
    hit = props[m]
    if hit.empty:
        return None, None
    newest = hit.loc[hit["capture_time"].idxmax()]
    return int(newest["price_american"]), pd.Timestamp(newest["capture_time"]).to_pydatetime()


def recheck(
    store: PointInTimeStore,
    as_of: datetime | None = None,
    path: Path = SHADOW_LOG_PATH,
    horizon: timedelta = DEFAULT_RECHECK_HORIZON,
) -> int:
    """Re-observe every still-open alerted leg and append what the market shows.

    Reads the store only -- no API call, no credits.

    **Only upcoming events.** A spot on a game already kicked off cannot be acted
    on, and re-checking one would fabricate survival data from settled markets.
    This project has already shipped that exact bug once: before `upcoming_only`
    existed, 874 of 879 alerts fired on games that had finished.
    """
    as_of = as_of or datetime.now(UTC)
    existing = load(path)
    if not existing:
        return 0

    df = store.read_as_of(as_of)
    if df.empty:
        return 0
    live = upcoming_only(df, as_of)
    if live.empty:
        return 0

    # An alert is "open" while it is inside the re-check horizon. The newest
    # observation per leg decides whether we have already looked recently.
    latest_seen: dict[tuple[str, str], ShadowObservation] = {}
    alert_rows: dict[tuple[str, str], ShadowObservation] = {}
    for o in existing:
        k = (o.alert_key, o.leg)
        if o.is_alert:
            alert_rows[k] = o
        if k not in latest_seen or o.observed_at > latest_seen[k].observed_at:
            latest_seen[k] = o

    rows: list[ShadowObservation] = []
    for k, alert in alert_rows.items():
        if as_of - alert.alerted_at > horizon:
            continue
        if latest_seen[k].observed_at >= as_of:
            continue
        price, ct = _latest_price(live, alert)
        # Nothing new sampled since the last look: appending would manufacture a
        # duplicate observation that survival stats would double-count.
        if ct is not None and latest_seen[k].capture_time is not None and ct <= latest_seen[k].capture_time:
            continue
        rows.append(alert.model_copy(update={
            "observed_at": as_of, "is_alert": False,
            "price_american": price, "capture_time": ct,
        }))

    n = append(rows, path)
    log.info("shadow log: re-checked %d open leg(s)", n)
    return n


def survival_report(path: Path = SHADOW_LOG_PATH) -> pd.DataFrame:
    """Per-alert survival: did every leg still carry at least the alerted price?

    An arb survives only if BOTH legs do -- `all()` over legs, not `any()`.
    Alerts with no re-check yet are reported with `survived=None` rather than
    dropped, so a report cannot quietly shrink its own denominator.
    """
    obs = load(path)
    if not obs:
        return pd.DataFrame()

    by_leg: dict[tuple[str, str], list[ShadowObservation]] = {}
    for o in obs:
        by_leg.setdefault((o.alert_key, o.leg), []).append(o)

    rows = []
    for (alert_key, leg), series in by_leg.items():
        series.sort(key=lambda o: o.observed_at)
        alert = next((o for o in series if o.is_alert), None)
        rechecks = [o for o in series if not o.is_alert]
        if alert is None:
            continue
        last = rechecks[-1] if rechecks else None
        survived = None
        if last is not None:
            # "At least as good" in AMERICAN odds is not a numeric >=: -105 is
            # better than -120 but worse than +100. Compare decimal payouts.
            survived = (
                last.price_american is not None
                and _decimal(last.price_american) >= _decimal(alert.price_american)
            )
        rows.append({
            "alert_key": alert_key, "leg": leg, "strategy": alert.strategy,
            "event_id": alert.event_id, "book": alert.book,
            "player_name": alert.player_name, "prop_stat": alert.prop_stat,
            "alerted_at": alert.alerted_at, "alert_price": alert.price_american,
            "edge": alert.edge, "n_rechecks": len(rechecks),
            "last_price": last.price_american if last else None,
            "elapsed_minutes": (
                (last.capture_time - alert.capture_time).total_seconds() / 60
                if last is not None and last.capture_time is not None and alert.capture_time is not None
                else None
            ),
            "leg_survived": survived,
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    # Roll legs up to the alert: an arb needs every leg to hold.
    agg = df.groupby("alert_key")["leg_survived"].apply(
        lambda s: None if s.isna().any() else bool(s.all())
    ).rename("survived")
    return df.merge(agg, on="alert_key", how="left")


def _decimal(american: int) -> float:
    return 1 + (american / 100 if american > 0 else 100 / abs(american))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    store = PointInTimeStore(root="data/snapshots")
    n = recheck(store)
    rep = survival_report()
    print(f"re-checked {n} leg(s)")
    if rep.empty:
        print("no shadow observations yet -- alerts populate this as they fire")
        return
    done = rep.dropna(subset=["survived"])
    print(f"\nalerts tracked: {rep['alert_key'].nunique()}  (with a re-check: {done['alert_key'].nunique()})")
    if not done.empty:
        by_alert = done.drop_duplicates("alert_key")
        print(f"survival rate: {by_alert['survived'].mean():.1%}  (n={len(by_alert)})")
        print(f"median elapsed to re-check: {done['elapsed_minutes'].median():.0f} min")
        print("\nby strategy:")
        print(by_alert.groupby("strategy")["survived"].agg(["mean", "size"]).to_string())


if __name__ == "__main__":
    main()
