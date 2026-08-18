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
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from src.model.baseline import market_baseline
from src.signal.sizing import apply_bankroll_caps, expected_value, fractional_kelly
from src.store.pit_store import PointInTimeStore

EXECUTION_BOOKS = ("draftkings", "fanduel", "betmgm", "betrivers", "williamhill_us")  # williamhill_us = Caesars Sportsbook's Odds API key
DEFAULT_EDGE_THRESHOLD = 0.02  # 2% EV per dollar staked


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
) -> pd.DataFrame:
    """One row per (event, side, book) where `book`'s latest moneyline price
    beats Pinnacle's latest devigged fair probability by at least
    `threshold` in expected value (per $1 staked).
    """
    as_of = as_of or datetime.now(UTC)
    df = store.read_as_of(as_of)
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
                    "book_price_american": row.price_american,
                    "edge": edge,
                    "suggested_stake": stake,
                    "book_time": row.capture_time,
                    "pinnacle_time": row.pinnacle_time,
                }
            )

    if not rows:
        return pd.DataFrame()

    spots = pd.DataFrame(rows).merge(event_meta, on="event_id", how="left")
    return spots.sort_values("edge", ascending=False).reset_index(drop=True)


def format_alert_message(row: pd.Series) -> str:
    side_team = row["home_team"] if row["side"] == "home" else row["away_team"]
    price = row["book_price_american"]
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


def _alert_key(row: pd.Series) -> str:
    return f"{row['event_id']}|{row['side']}|{row['book']}"


def new_or_improved_spots(
    spots: pd.DataFrame, state: dict[str, AlertRecord], min_edge_increase: float = 0.01
) -> pd.DataFrame:
    """Keep only spots that are brand new, or whose edge has grown by at
    least `min_edge_increase` since the last alert for that (event, side,
    book) -- so a stable +EV spot doesn't re-text every scan cycle, but a
    meaningfully improving one still does.
    """
    if spots.empty:
        return spots

    def _is_new_or_improved(row: pd.Series) -> bool:
        prior = state.get(_alert_key(row))
        return prior is None or row["edge"] >= prior.edge + min_edge_increase

    mask = spots.apply(_is_new_or_improved, axis=1)
    return spots[mask]


def record_alerts(spots: pd.DataFrame, state: dict[str, AlertRecord], now: datetime | None = None) -> dict[str, AlertRecord]:
    now = now or datetime.now(UTC)
    updated = dict(state)
    for row in spots.itertuples():
        updated[f"{row.event_id}|{row.side}|{row.book}"] = AlertRecord(edge=row.edge, alerted_at=now)
    return updated
