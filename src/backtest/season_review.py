"""In-season strategy review: is each live strategy still working, and when
should one be retired?

**The gap this closes.** Nothing in this project re-checked anything during a
season. Strategies were validated once on historical data and then run
indefinitely -- but books patch inefficiencies, and the whole premise of
`src/drift/monitor.py` (built long ago, wired to nothing until now) is that an
edge dies before the bankroll makes it obvious. Sharp bettors re-evaluate
continuously; this module is that loop.

**A decayed edge is a real finding, not a failure** -- provided the decay is
*recorded*. The failure mode this guards against is quietly continuing to bet a
strategy whose edge is gone, or quietly dropping one without noting that it
worked first.

## What it combines (all existing pieces, nothing reimplemented)

- `src/backtest/evaluation.py` -- is it still *bettable* (ROI, proportion bet,
  bootstrap CI, random-side null)?
- `src/clv/metrics.py` + `src/backtest/clv_portfolio.py` -- CLV level and beat
  rate, segmented so props and mainline are never pooled.
- `src/drift/monitor.py` -- CUSUM on the CLV series: has performance shifted in a
  *sustained* way rather than wobbled?

## Two constraints that shape this, stated plainly

1. **Live data only.** CLV needs an entry price and a close; every historical
   pull in this project is a single near-kickoff snapshot, so there is no
   historical CLV to review. This operates on live 2026 collection as it accrues
   and on synthetic series before then -- it cannot be backfilled.
2. **Early-season verdicts are weak by construction.** A handful of bets cannot
   distinguish a dead edge from variance. `MIN_BETS_FOR_VERDICT` gates the
   recommendation, and `review_strategy` reports `insufficient_data` rather than
   guessing -- deliberately, because the cost of retiring a good strategy on
   noise is symmetric with the cost of keeping a dead one.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.backtest.clv_portfolio import bets_to_frame
from src.backtest.engine import BacktestBet
from src.backtest.evaluation import evaluate_strategy
from src.clv.metrics import beat_rate
from src.drift.monitor import cusum, first_flag_index, rolling_mean_clv
from src.store.pit_store import PointInTimeStore

log = logging.getLogger(__name__)

# Below this, a verdict is noise. Not tuned on data -- chosen so a single bad
# week cannot retire a strategy, since with ~16 games/week a real props strategy
# accumulates this within a few weeks while a cold streak does not reach it.
MIN_BETS_FOR_VERDICT = 50
DEFAULT_CLV_WINDOW = 25
# Bets used to establish the strategy's own baseline CLV before drift detection
# starts. See `_detect_decay` for why a fixed target of 0.0 is wrong here.
DEFAULT_BASELINE_BETS = 30
# CUSUM allowance/threshold in CLV probability units. CLV moves in single-digit
# thousandths per bet, so `drift` absorbs ordinary wobble and `threshold` takes a
# sustained run to cross. See `src/drift/monitor.py::cusum` for the mechanics.
DEFAULT_CUSUM_DRIFT = 0.002
DEFAULT_CUSUM_THRESHOLD = 0.05

CONTINUE, MONITOR, RETIRE, INSUFFICIENT = "continue", "monitor", "retire", "insufficient_data"


@dataclass(frozen=True)
class StrategyReview:
    strategy: str
    n_bets: int
    mean_clv: float | None
    clv_beat_rate: float | None
    recent_mean_clv: float | None
    drift_flagged: bool
    drift_first_index: int | None
    roi: float | None
    bettable: bool
    recommendation: str
    reason: str

    def to_dict(self) -> dict:
        return {**self.__dict__}


def _clv_series(frame: pd.DataFrame, clv_column: str) -> np.ndarray:
    """CLV in decision order, dropping unmeasurable bets.

    Order matters: CUSUM is a *sequential* detector, so feeding it an unsorted
    series would scramble the very thing it looks for.
    """
    ordered = frame.sort_values("decision_time")
    return ordered[clv_column].dropna().to_numpy()


def _detect_decay(
    clv: np.ndarray, baseline_bets: int, drift: float, threshold: float
) -> tuple[bool, int | None, float | None]:
    """Has CLV shifted *downward* from this strategy's OWN established baseline?

    Two design points, both of which a naive implementation gets wrong (and this
    module did, until its tests caught it):

    1. **The CUSUM target is the strategy's own early-period mean CLV, not 0.0.**
       Against a fixed target of zero, a *consistently profitable* strategy
       accumulates upward and trips the detector -- flagging the edge working as
       if it were the edge dying. Drift means "different from how it was", so the
       baseline has to be what it was.
    2. **Only the LOWER arm counts.** `cusum` flags shifts in either direction;
       a sustained move *above* baseline is a strategy improving, which is not a
       retirement signal. Decay is specifically the lower arm crossing.

    Returns `(decayed, first_index_in_full_series, baseline)`. With fewer than
    `baseline_bets + 1` observations there is nothing to compare against yet, so
    it reports no decay rather than guessing.
    """
    if clv.size <= baseline_bets:
        return False, None, (float(clv.mean()) if clv.size else None)

    baseline = float(clv[:baseline_bets].mean())
    _upper, lower, _flagged = cusum(clv[baseline_bets:], target=baseline, threshold=threshold, drift=drift)
    decayed_arr = lower < -threshold
    idx = first_flag_index(decayed_arr)
    return bool(decayed_arr.any()), (idx + baseline_bets if idx is not None else None), baseline


def review_strategy(
    bets: Sequence[BacktestBet] | pd.DataFrame,
    strategy: str = "all",
    clv_column: str = "clv_probability",
    window: int = DEFAULT_CLV_WINDOW,
    min_bets: int = MIN_BETS_FOR_VERDICT,
    baseline_bets: int = DEFAULT_BASELINE_BETS,
    cusum_drift: float = DEFAULT_CUSUM_DRIFT,
    cusum_threshold: float = DEFAULT_CUSUM_THRESHOLD,
    random_state: int | None = 0,
) -> StrategyReview:
    """Full health check on one strategy's live bets.

    The recommendation is deliberately conservative in both directions:
    - `insufficient_data` below `min_bets` -- no verdict is better than a wrong one.
    - `retire` only when CUSUM flags a sustained shift AND recent CLV has actually
      gone negative. Either alone is not enough: a CUSUM flag can fire on an
      *upward* shift, and a negative window can be a cold streak.
    - `monitor` when exactly one of those two is true.
    """
    frame = bets if isinstance(bets, pd.DataFrame) else bets_to_frame(bets)

    if frame.empty:
        return StrategyReview(strategy, 0, None, None, None, False, None, None, False,
                              INSUFFICIENT, "no bets")

    clv = _clv_series(frame, clv_column)
    n = len(frame)

    mean_clv = float(clv.mean()) if clv.size else None
    clv_beat = beat_rate(clv) if clv.size else None
    rolling = rolling_mean_clv(clv, window) if clv.size else np.array([])
    recent = float(rolling[-1]) if rolling.size else None

    flagged, first_flag, _baseline = _detect_decay(clv, baseline_bets, cusum_drift, cusum_threshold)

    roi, bettable = None, False
    if {"fair_prob", "price_decimal", "won"}.issubset(frame.columns) and n:
        report = evaluate_strategy(frame, min_bets=min(min_bets, n), random_state=random_state)
        best = report["best_threshold"]
        roi = float(best["roi"]) if best else None
        bettable = report["verdict"] == "bettable edge"

    if n < min_bets:
        rec, reason = INSUFFICIENT, f"{n} bets < {min_bets} needed for a verdict"
    elif flagged and recent is not None and recent < 0:
        rec, reason = RETIRE, "sustained drift AND recent CLV negative"
    elif flagged:
        rec, reason = MONITOR, "drift flagged but recent CLV still positive"
    elif recent is not None and recent < 0:
        rec, reason = MONITOR, "recent CLV negative but no sustained drift yet"
    else:
        rec, reason = CONTINUE, "no drift, recent CLV holding"

    return StrategyReview(strategy, n, mean_clv, clv_beat, recent, flagged, first_flag, roi, bettable, rec, reason)


def review_all(
    bets: Sequence[BacktestBet] | pd.DataFrame,
    segment_column: str = "market",
    **kwargs,
) -> pd.DataFrame:
    """One review row per strategy segment.

    Segments rather than pools for the same reason `clv_portfolio.clv_by_segment`
    does: this project's validated edges are prop-adjacent, and a pooled verdict
    would let a healthy strategy mask a dying one.

    Selects group rows by position, not `== segment` -- a NaN segment key
    (mainline bets have `prop_stat=None`) never matches itself by equality, which
    silently emptied groups before this was fixed in `clv_portfolio`.
    """
    frame = bets if isinstance(bets, pd.DataFrame) else bets_to_frame(bets)
    if frame.empty:
        return pd.DataFrame(columns=[f.name for f in StrategyReview.__dataclass_fields__.values()])

    rows = []
    for segment, group in frame.groupby(segment_column, dropna=False):
        label = "unknown" if pd.isna(segment) else str(segment)
        rows.append(review_strategy(group, strategy=label, **kwargs).to_dict())
    return pd.DataFrame(rows).sort_values("n_bets", ascending=False).reset_index(drop=True)


def format_review_summary(reviews: pd.DataFrame) -> str:
    """Human-readable digest, ordered so anything needing action is first --
    this is meant to be read weekly, so burying a RETIRE under healthy rows
    would defeat the purpose.
    """
    if reviews.empty:
        return "No live bets to review yet."

    order = {RETIRE: 0, MONITOR: 1, INSUFFICIENT: 2, CONTINUE: 3}
    ordered = reviews.sort_values(by="recommendation", key=lambda s: s.map(order))

    lines = []
    for r in ordered.itertuples():
        clv = f"{r.mean_clv:+.4f}" if r.mean_clv is not None else "n/a"
        recent = f"{r.recent_mean_clv:+.4f}" if r.recent_mean_clv is not None else "n/a"
        lines.append(
            f"[{r.recommendation.upper():<17}] {r.strategy:<14} n={r.n_bets:<5} "
            f"mean_clv={clv} recent={recent} drift={'YES' if r.drift_flagged else 'no'} -- {r.reason}"
        )
    return "\n".join(lines)


def run(store_root: str = "data/snapshots", segment_column: str = "strategy") -> pd.DataFrame:
    """Weekly in-season health check over the LIVE bet log.

    Segments on `strategy` rather than `market` because that is what identifies
    the scanner: prop arb and experimental prop EV are both `player_prop` with
    opposite track records, and a pooled verdict would let the validated one
    mask the null one.

    Reads `data/bet_log.jsonl` + the local snapshot store only -- no Odds API
    cost, so it is free to run as often as you like. Meant to be read weekly;
    manual for now, since acting on a RETIRE verdict is a human decision.
    """
    from src.store.bet_log import active_bets, to_backtest_bets

    logged = active_bets()
    if not logged:
        log.info("season review: bet log is empty -- nothing placed yet")
        return pd.DataFrame()

    bets = to_backtest_bets(logged, PointInTimeStore(root=store_root))
    reviews = review_all(bets, segment_column=segment_column)
    print(format_review_summary(reviews))
    return reviews


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    run()


if __name__ == "__main__":
    main()
