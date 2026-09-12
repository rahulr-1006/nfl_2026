"""Portfolio-level CLV reporting: combine every bet the engine produced --
mainline and props, one strategy or several -- into one honest picture.

**Why a separate layer instead of more CLV trackers.** The temptation with
several bet types is several trackers, then reconciling their numbers later.
That's the wrong shape: `src/backtest/engine.py` already computes CLV
identically for every market (same Pinnacle anchor, same devig, same
`src/clv/metrics.py` functions), because a prop's CLV and a moneyline's CLV
are the same measurement applied to different contracts -- not different
metrics. So there is exactly ONE tracker, and this module is the reporting
layer that slices its output. Nothing here recomputes CLV; it aggregates
what the engine already measured.

**What this layer adds that per-bet CLV cannot express:**
  1. **Segmented beat rates with intervals.** A pooled beat rate across
     mainline and props hides the thing that matters -- this project's only
     out-of-sample-validated edges are prop-adjacent, so "did props beat the
     close" is a different question from "did anything beat the close," and
     answering the second when asked the first would be a real error.
  2. **Bootstrap CIs per segment, always.** Same discipline
     `src/clv/metrics.py` already enforces: a point-estimate beat rate with
     no interval is exactly the unearned confidence this project exists to
     avoid. A segment with 6 bets gets an interval wide enough to say so.
  3. **Realized bankroll path**, not just per-bet stakes -- with several
     bets per game the running exposure is a real constraint that per-bet
     sizing caps cannot see (see `BacktestEngine`'s own docstring).

**The limitation that shapes how any of this gets read:** CLV needs an entry
price and a close.

**Corrected 2026-08-23.** This docstring used to say no historical CLV backtest
was possible "for ANY market ... at any sample size". That was wrong -- it was a
COST statement misfiled as an impossibility. `get_historical_event_odds` accepts
an arbitrary `date`, so a time series was always purchasable; only the close had
ever been bought, because each historical call bills 10x. 105 games of 2024 now
carry a real 6-point Pinnacle series (T-120h..close, ~23 books), pulled by
`collect/mainline_historical.py`.

So: **mainline 2024 CLV can now be backtested.** Props cannot, still for cost --
a prop series is ~700 credits/game at 7 markets. Numbers here come from that
2024 mainline series, from synthetic data with known ground truth (pre-season
pipeline validation), or from live 2026 collection. Which one is always stated;
a future reader should never have to guess.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from src.backtest.engine import BacktestBet
from src.clv.metrics import beat_rate, bootstrap_ci
from src.store.settlement import Outcome

MIN_BETS_FOR_INTERVAL = 2  # bootstrap_ci's own floor -- below this, report the point estimate with no interval


def bets_to_frame(bets: Sequence[BacktestBet]) -> pd.DataFrame:
    """One row per bet, flat -- the shape every aggregation below works on
    and the natural thing to hand a notebook for ad hoc slicing.
    """
    return pd.DataFrame(
        [
            {
                "event_id": b.event_id,
                "decision_time": b.decision_time,
                "strategy": b.strategy,
                "market": b.market.value,
                "side": b.side.value,
                "line": b.line,
                "book": b.book,
                "player_name": b.player_name,
                "prop_stat": b.prop_stat,
                "stake": b.stake,
                "price_decimal": b.price_decimal,
                "entry_prob_fair": b.entry_prob_fair,
                # `fair_prob` and `won` exist so `season_review.review_strategy`
                # can actually compute ROI/bettability -- it gates on
                # {"fair_prob", "price_decimal", "won"} and this frame emitted
                # neither, so `roi` was always None and `bettable` always False
                # while `make season-review` advertised "CLV + drift + bettability".
                # Aliases, not new data: fair_prob IS the entry fair probability,
                # and `won` is None (not False) for an unsettled or pushed bet so
                # an ungraded bet is never counted as a loss.
                "fair_prob": b.entry_prob_fair,
                "won": None if b.outcome is None else (b.outcome == Outcome.WIN),
                "close_prob_fair": b.close_prob_fair,
                # `close_price_decimal` is the raw close `clv_price` is derived
                # from. Omitting it made `shadow_clv.format_summary` raise a
                # KeyError -- and only once a game had ACTUALLY closed, because
                # the line that reads it sits after an early return that fires
                # while every row is still unmeasurable. The first real close of
                # the season (2026_01_NE_SEA) was therefore also the first run
                # that could ever hit it.
                "close_price_decimal": b.close_price_decimal,
                "clv_price": b.clv_price,
                "clv_probability": b.clv_probability,
                "outcome": b.outcome.value if b.outcome is not None else None,
                "payout": b.payout,
                "bankroll_after": b.bankroll_after,
            }
            for b in bets
        ]
    )


def clv_summary(bets: Sequence[BacktestBet], clv_column: str = "clv_probability", random_state: int | None = 0) -> dict:
    """Pooled CLV summary across every bet given: n, mean CLV, beat rate,
    and a bootstrap CI on mean CLV.

    Bets with no CLV (the closing quote was missing for that contract) are
    excluded from the CLV stats but still counted in `n_total`, so a
    coverage gap is visible rather than silently shrinking the sample.
    """
    frame = bets_to_frame(bets)
    n_total = len(frame)
    if n_total == 0:
        return {"n_total": 0, "n_with_clv": 0, "mean_clv": None, "beat_rate": None, "ci_lo": None, "ci_hi": None}

    values = frame[clv_column].dropna()
    n_with_clv = len(values)
    if n_with_clv == 0:
        return {"n_total": n_total, "n_with_clv": 0, "mean_clv": None, "beat_rate": None, "ci_lo": None, "ci_hi": None}

    lo = hi = None
    if n_with_clv >= MIN_BETS_FOR_INTERVAL:
        lo, hi = bootstrap_ci(values.to_numpy(), random_state=random_state)

    return {
        "n_total": n_total,
        "n_with_clv": n_with_clv,
        "mean_clv": float(values.mean()),
        "beat_rate": beat_rate(values.to_numpy()),
        "ci_lo": lo,
        "ci_hi": hi,
    }


def clv_by_segment(
    bets: Sequence[BacktestBet],
    segment_column: str = "market",
    clv_column: str = "clv_probability",
    random_state: int | None = 0,
) -> pd.DataFrame:
    """`clv_summary` computed per segment -- one row per distinct value of
    `segment_column` (default: per market, so props and mainline are never
    pooled into a single misleading number). `segment_column` can be any
    column `bets_to_frame` produces (`book`, `prop_stat`, ...).
    """
    frame = bets_to_frame(bets)
    if frame.empty:
        return pd.DataFrame(columns=[segment_column, "n_total", "n_with_clv", "mean_clv", "beat_rate", "ci_lo", "ci_hi"])

    rows = []
    for segment, group in frame.groupby(segment_column, dropna=False):
        # Select by the group's own row positions, NOT `frame[col] == segment`.
        # With `dropna=False` the segment key can be NaN, and `== NaN` is False
        # for every row -- so the equality form silently produced an empty group
        # and reported n_total=0 for it (fixed 2026-08-23). That broke exactly
        # the `prop_stat` segmentation this function's docstring advertises,
        # since `prop_stat` is None on every mainline bet.
        group_bets = [bets[i] for i in frame.index.get_indexer(group.index)]
        rows.append({segment_column: segment, **clv_summary(group_bets, clv_column, random_state)})
    return pd.DataFrame(rows).sort_values("n_total", ascending=False).reset_index(drop=True)


_BANKROLL_PATH_COLUMNS = ["decision_time", "event_id", "market", "stake", "payout", "bankroll_after"]


def bankroll_path(bets: Sequence[BacktestBet]) -> pd.DataFrame:
    """Running bankroll after each settled bet -- the realized path, not a
    per-bet stake list. Makes drawdown and peak exposure visible, which
    per-bet sizing caps structurally cannot show.

    **Input order is preserved deliberately -- do not sort here.**
    `BacktestEngine.run` iterates `schedule.sort_values("kickoff")`, so the
    list it returns is already in the order `bankroll_after` was actually
    accumulated. Re-sorting by `decision_time` (as this did before
    2026-08-23) produced a non-monotone path, because a strategy can decide
    5 days out on a late game and 1 hour out on an early one -- settlement
    order and decision order are genuinely different, and only settlement
    order describes the bankroll.
    """
    if not bets:
        return pd.DataFrame(columns=_BANKROLL_PATH_COLUMNS)
    return bets_to_frame(bets)[_BANKROLL_PATH_COLUMNS]
