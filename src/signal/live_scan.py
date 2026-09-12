"""Live +EV scanner: compare execution-book prices against Pinnacle's fair
value, right now, not just at settlement.

This is the "optimal spot" detector -- it doesn't wait for a game to close
and grade a backtest; it watches the point-in-time store as new snapshots
land and flags whenever a book you can actually bet at (EXECUTION_BOOKS,
matching the manual-bets-only scope in paper Sec 3.4 -- updated 2026-08-18
to five real accounts: DraftKings, FanDuel, BetMGM, BetRivers, Caesars/
William Hill US) offers a price that beats Pinnacle's current devigged
fair probability by a real margin.

Moneyline only for now: spread/total comparisons need matching line
numbers between books to be a clean apples-to-apples bet, which adds real
complexity (line shopping across non-identical spreads isn't the same bet)
-- deferred rather than built sloppily.

`expected_value(p, d)` (src/signal/sizing.py) is reused unchanged: p is
Pinnacle's devigged fair probability, d is the execution book's own
(vig-inflated) decimal price -- exactly the EV calculation that function
already exists for, just wired to live data instead of a backtest.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from src.model.baseline import market_baseline
from src.signal.sizing import apply_bankroll_caps, expected_value, fractional_kelly
from src.store.pit_store import PointInTimeStore

EXECUTION_BOOKS = ("draftkings", "fanduel", "betmgm", "betrivers", "williamhill_us")  # williamhill_us = Caesars Sportsbook's Odds API key
DEFAULT_EDGE_THRESHOLD = 0.02  # 2% EV per dollar staked
# Under normal operation the collector fetches Pinnacle + execution books in
# one combined poll, so capture_time and pinnacle_time land together (gap ~0).
# The gap only opens when Pinnacle is missing from a specific poll cycle (an
# event the API didn't return that call) and _latest_two_sided_pinnacle falls
# back to an OLDER Pinnacle price while the execution book's price stays
# fresh -- comparing a stale "fair" value against a live price. 30 minutes is
# comfortably wider than any single-poll write jitter but far tighter than
# the gap a real stale-fallback would produce (at least one full missed poll
# cycle). Found via a 2026-08-21 adversarial audit; this was previously
# unguarded -- capture_time/pinnacle_time were captured and returned but never
# actually checked against each other.
DEFAULT_MAX_CAPTURE_GAP = pd.Timedelta(minutes=30)


def upcoming_only(df: pd.DataFrame, as_of: datetime) -> pd.DataFrame:
    """Drop snapshots for games that have already kicked off -- only a
    future game is actually bettable.

    **Not a hypothetical guard: this was a real, live bug.** The
    point-in-time store holds historical backfill alongside live collection
    (the 2026-08-22/23 pulls put 570 games of 2023-2024 mainline odds and a
    full 2023-2024 season of props into the same store the live collector
    writes to). Every scanner reads `read_as_of(now)`, which correctly
    returns everything captured before now -- including those finished
    games. A dry run of the monitor found **874 of 879 flagged spots were on
    games played months ago**, which would have flooded the alert channel
    with unbettable noise on day one. Filtering on `event_start_time` is the
    fix; `capture_time` cannot express this, since a historical snapshot's
    capture_time is legitimately in the past too.
    """
    if df.empty or "event_start_time" not in df.columns:
        return df
    return df[df["event_start_time"] > as_of]


def _latest_two_sided_pinnacle(moneyline: pd.DataFrame) -> pd.DataFrame:
    """One row per event: Pinnacle's most recent home+away American prices,
    both from the same capture_time -- a single poll always writes both
    outcomes together, so pairing on the latest timestamp (not latest per
    side independently) guarantees they're devigged as one consistent
    market rather than mixing two different moments in time.
    """
    pin = moneyline[moneyline["book"] == "pinnacle"]
    if pin.empty:
        return pd.DataFrame(columns=["event_id", "capture_time", "home_price", "away_price"])

    latest_time = pin.groupby("event_id")["capture_time"].transform("max")
    pin = pin[pin["capture_time"] == latest_time]
    wide = pin.pivot_table(
        index=["event_id", "capture_time"], columns="side", values="price_american", aggfunc="first"
    ).reset_index()
    if not {"home", "away"}.issubset(wide.columns):
        return pd.DataFrame(columns=["event_id", "capture_time", "home_price", "away_price"])

    wide = wide.rename(columns={"home": "home_price", "away": "away_price"}).dropna(subset=["home_price", "away_price"])
    wide["home_fair"] = wide.apply(lambda r: market_baseline([int(r.home_price), int(r.away_price)], side_index=0), axis=1)
    wide["away_fair"] = wide.apply(lambda r: market_baseline([int(r.home_price), int(r.away_price)], side_index=1), axis=1)
    return wide[["event_id", "capture_time", "home_fair", "away_fair"]].rename(columns={"capture_time": "pinnacle_time"})


def find_positive_ev_spots(
    store: PointInTimeStore,
    threshold: float = DEFAULT_EDGE_THRESHOLD,
    books: Sequence[str] = EXECUTION_BOOKS,
    as_of: datetime | None = None,
    max_capture_gap: pd.Timedelta = DEFAULT_MAX_CAPTURE_GAP,
) -> pd.DataFrame:
    """One row per (event, side, book) where `book`'s latest moneyline price
    beats Pinnacle's latest devigged fair probability by at least
    `threshold` in expected value (per $1 staked) -- and Pinnacle's price
    was captured within `max_capture_gap` of the execution book's own price,
    so a spot is never flagged from comparing a stale Pinnacle read against
    a fresh execution-book one (see `DEFAULT_MAX_CAPTURE_GAP`'s comment).
    """
    as_of = as_of or datetime.now(UTC)
    df = upcoming_only(store.read_as_of(as_of), as_of)
    if df.empty:
        return pd.DataFrame()

    moneyline = df[df["market"] == "moneyline"]
    if moneyline.empty:
        return pd.DataFrame()

    pinnacle_fair = _latest_two_sided_pinnacle(moneyline)
    if pinnacle_fair.empty:
        return pd.DataFrame()

    event_meta = df[["event_id", "home_team", "away_team", "event_start_time"]].drop_duplicates("event_id")

    rows = []
    for book in books:
        book_df = moneyline[moneyline["book"] == book]
        if book_df.empty:
            continue
        latest_book = book_df.sort_values("capture_time").groupby(["event_id", "side"], as_index=False).last()
        merged = latest_book.merge(pinnacle_fair, on="event_id", how="inner")

        for row in merged.itertuples():
            if abs(row.capture_time - row.pinnacle_time) > max_capture_gap:
                continue
            fair = row.home_fair if row.side == "home" else row.away_fair
            edge = expected_value(fair, row.price_decimal)
            if edge < threshold:
                continue
            stake = apply_bankroll_caps(fractional_kelly(fair, row.price_decimal) * 100)
            rows.append(
                {
                    "event_id": row.event_id,
                    "side": row.side,
                    "book": book,
                    "pinnacle_fair_prob": fair,
                    "price_american": row.price_american,
                    "edge": edge,
                    "suggested_stake": stake,
                    "capture_time": row.capture_time,
                    "pinnacle_time": row.pinnacle_time,
                }
            )

    if not rows:
        return pd.DataFrame()

    spots = pd.DataFrame(rows).merge(event_meta, on="event_id", how="left")
    return spots.sort_values("edge", ascending=False).reset_index(drop=True)


def format_alert_message(row: pd.Series) -> str:
    side_team = row["home_team"] if row["side"] == "home" else row["away_team"]
    price = row["price_american"]
    price_str = f"+{price}" if price > 0 else str(price)
    return (
        f"{row['away_team']} @ {row['home_team']}: {row['book'].title()} {side_team} ML {price_str} "
        f"beats Pinnacle fair by {row['edge'] * 100:.1f}%. "
        f"Suggested stake ${row['suggested_stake']:.2f}."
    )


# --- alert dedup state: don't re-text the same unchanged spot every tick ---

_ALERT_STATE_PATH = Path("data/alert_state.json")


@dataclass(frozen=True)
class AlertRecord:
    edge: float
    alerted_at: datetime


def load_alert_state(path: Path = _ALERT_STATE_PATH) -> dict[str, AlertRecord]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text())
    return {k: AlertRecord(edge=v["edge"], alerted_at=datetime.fromisoformat(v["alerted_at"])) for k, v in raw.items()}


def save_alert_state(state: dict[str, AlertRecord], path: Path = _ALERT_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = {k: {"edge": v.edge, "alerted_at": v.alerted_at.isoformat()} for k, v in state.items()}
    path.write_text(json.dumps(raw))


# Alert dedup keys are only useful until their game is played -- a spot on a
# finished game can never recur. Nothing pruned this state, so it grew without
# bound: measured 2026-08-23 it held 874 entries, 866 of them for already-played
# 2023-24 games, residue from the pre-`upcoming_only` alert bug.
#
# **Pruning is by KICKOFF, not by alert age.** Age was the obvious first choice
# and is wrong here: that bug fired *today* on games from 2023, so the stale
# entries carry recent `alerted_at` values and an age filter keeps every one of
# them. What makes an entry dead is that its event has started, which is exactly
# what the store's `event_start_time` records.
#
# `max_age` remains as a fallback for keys whose event cannot be resolved (an
# unknown key shape, or an event missing from the store), so an unparseable key
# still cannot accumulate forever. 30 days is safely longer than the 21-day props
# posting window, which bounds how far ahead of kickoff any alert can fire.
DEFAULT_ALERT_STATE_MAX_AGE = timedelta(days=30)

# Keys namespaced with "__" are one-shot latches (e.g. monitor_run's
# PINNACLE_ARRIVAL_KEY), not per-spot dedup entries. Dropping one would re-fire
# an announcement that is supposed to happen exactly once, ever.
_SENTINEL_PREFIX = "__"


def event_id_from_alert_key(key: str) -> str | None:
    """The event a dedup key refers to, across all three key shapes in use:
    `event|side|book` (moneyline), and `ev|event|...` / `arb|event|...` (props).
    Returns None for sentinels and anything unrecognised.
    """
    if key.startswith(_SENTINEL_PREFIX):
        return None
    parts = key.split("|")
    if parts[0] in ("ev", "arb"):
        return parts[1] if len(parts) > 1 else None
    return parts[0] or None


def prune_alert_state(
    state: dict[str, AlertRecord],
    now: datetime | None = None,
    kickoffs: Mapping[str, datetime] | None = None,
    max_age: timedelta = DEFAULT_ALERT_STATE_MAX_AGE,
) -> dict[str, AlertRecord]:
    """Drop dedup entries whose event has already started. Sentinels are always
    kept; entries whose event cannot be resolved fall back to `max_age`.
    """
    now = now or datetime.now(UTC)
    kickoffs = kickoffs or {}

    kept = {}
    for k, v in state.items():
        if k.startswith(_SENTINEL_PREFIX):
            kept[k] = v
            continue
        event_id = event_id_from_alert_key(k)
        kickoff = kickoffs.get(event_id) if event_id else None
        if kickoff is not None:
            if kickoff > now:
                kept[k] = v
        elif (now - v.alerted_at) <= max_age:
            kept[k] = v
    return kept


def _alert_key(row: pd.Series) -> str:
    return f"{row['event_id']}|{row['side']}|{row['book']}"


def new_or_improved_spots(
    spots: pd.DataFrame,
    state: dict[str, AlertRecord],
    min_edge_increase: float = 0.01,
    key_fn: Callable[[pd.Series], str] = _alert_key,
    edge_column: str = "edge",
) -> pd.DataFrame:
    """Keep only spots that are brand new, or whose edge has grown by at
    least `min_edge_increase` since the last alert for that key -- so a
    stable +EV spot doesn't re-text every scan cycle, but a meaningfully
    improving one still does.

    `key_fn`/`edge_column` are parameterized (2026-08-23) so the props
    scanner can share this state machine instead of duplicating it: prop
    contracts need `player/stat/line` in the key (the moneyline default
    collides across every prop in a game), and arbitrage rows carry
    `arb_margin` rather than `edge`.
    """
    if spots.empty:
        return spots

    def _is_new_or_improved(row: pd.Series) -> bool:
        prior = state.get(key_fn(row))
        return prior is None or row[edge_column] >= prior.edge + min_edge_increase

    mask = spots.apply(_is_new_or_improved, axis=1)
    return spots[mask]


def record_alerts(
    spots: pd.DataFrame,
    state: dict[str, AlertRecord],
    now: datetime | None = None,
    key_fn: Callable[[pd.Series], str] = _alert_key,
    edge_column: str = "edge",
) -> dict[str, AlertRecord]:
    now = now or datetime.now(UTC)
    updated = dict(state)
    for _, row in spots.iterrows():
        updated[key_fn(row)] = AlertRecord(edge=float(row[edge_column]), alerted_at=now)
    return updated
