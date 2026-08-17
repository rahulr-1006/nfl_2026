"""Preseason CLV-movement report: a dry run of the measurement pipeline
(src/collect/preseason.py -> src/store/pit_store.py -> here) against real
preseason odds, so the CLV machinery gets exercised end-to-end on live
data before the real season's headline numbers are at stake. No bets, no
settlement, no bankroll -- just entry-vs-latest price/probability movement
for whatever preseason games have been polled more than once so far.

Not Pinnacle, not the paper's CLV result: preseason odds carry only
FanDuel, MyBookie, and 1xBet (verified live -- no region returns Pinnacle
for americanfootball_nfl_preseason, src/collect/preseason.py). FanDuel is
used here as the reference book purely because it's the most liquid one
present, not because it plays Pinnacle's role in the real methodology
(blueprint Part B.2 -- Pinnacle is the sharp anchor specifically because
of who trades it). These numbers validate the pipeline, not the thesis.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from src.clv.metrics import clv_price, clv_probability
from src.devig.convert import american_to_decimal
from src.model.baseline import market_baseline
from src.store.pit_store import PointInTimeStore

REFERENCE_BOOK = "fanduel"


def _side_prices(df: pd.DataFrame) -> tuple[int, int] | None:
    """(home_price_american, away_price_american) from a moneyline slice.
    None if the slice doesn't have both sides -- e.g. a partial poll where
    only one side's price came back.
    """
    home = df.loc[df["side"] == "home", "price_american"]
    away = df.loc[df["side"] == "away", "price_american"]
    if home.empty or away.empty:
        return None
    return int(home.iloc[0]), int(away.iloc[0])


def clv_movement_report(
    store: PointInTimeStore, book: str = REFERENCE_BOOK, as_of: datetime | None = None
) -> pd.DataFrame:
    """One row per preseason event with at least two distinct capture
    times: price and probability CLV for both sides, entry (earliest
    snapshot) vs. "close" (latest snapshot captured so far -- informal
    "close," since a game that hasn't kicked off yet has no real close).
    """
    as_of = as_of or datetime.now(UTC)
    df = store.read_as_of(as_of)
    if df.empty:
        return pd.DataFrame()

    df = df[(df["book"] == book) & (df["market"] == "moneyline")]
    if df.empty:
        return pd.DataFrame()

    rows = []
    for event_id, g in df.groupby("event_id"):
        capture_times = sorted(g["capture_time"].unique())
        if len(capture_times) < 2:
            continue  # only one poll so far -- nothing to measure movement against yet

        entry_slice = g[g["capture_time"] == capture_times[0]]
        close_slice = g[g["capture_time"] == capture_times[-1]]
        entry_prices = _side_prices(entry_slice)
        close_prices = _side_prices(close_slice)
        if entry_prices is None or close_prices is None:
            continue

        home_entry, away_entry = entry_prices
        home_close, away_close = close_prices

        p_home_entry = market_baseline([home_entry, away_entry], side_index=0)
        p_home_close = market_baseline([home_close, away_close], side_index=0)
        p_away_entry = market_baseline([home_entry, away_entry], side_index=1)
        p_away_close = market_baseline([home_close, away_close], side_index=1)

        rows.append(
            {
                "event_id": event_id,
                "home_team": entry_slice["home_team"].iloc[0],
                "away_team": entry_slice["away_team"].iloc[0],
                "n_snapshots": len(capture_times),
                "entry_time": capture_times[0],
                "close_time": capture_times[-1],
                "home_price_clv": clv_price(american_to_decimal(home_entry), american_to_decimal(home_close)),
                "away_price_clv": clv_price(american_to_decimal(away_entry), american_to_decimal(away_close)),
                "home_prob_clv": clv_probability(p_home_entry, p_home_close),
                "away_prob_clv": clv_probability(p_away_entry, p_away_close),
            }
        )

    return pd.DataFrame(rows)


if __name__ == "__main__":
    from src.collect.preseason import DEFAULT_STORE_ROOT

    store = PointInTimeStore(root=DEFAULT_STORE_ROOT)
    report = clv_movement_report(store)
    if report.empty:
        print("no preseason events with >=2 snapshots yet -- poll again later")
    else:
        print(report.to_string(index=False))
