"""Score H1 / H1b against the pass bar in preregistration_wk5-9.md §3.

**Written 2026-10-13, before any holdout scoring.** The pre-registration fixes
the rules and parameters; this module fixes the *arithmetic*, so the 11-10 run
is mechanical rather than a fresh analysis written with the answer in view.
Every condition below cites the section it implements.

**Blinded by date.** Asking for any holdout week (5-9) before
`SCORE_NOT_BEFORE` raises. There is no override flag: the only way past the
lock is to wait, or to pass `now=` from a test. Train weeks (1-4) are scorable
any time -- they are the data the parameters were frozen on.

Primary metric (§3): `close_ev = p_close_fair(side) x d_paid - 1`, with
`p_close_fair` from `bet_log.to_backtest_bets` -- the same code path as
`shadow_clv`, as §3 requires.

Exclusions from the primary metric, both declared before the holdout and both
reported separately rather than dropped:
- **Bad quotes** (§3): entry EV > 15% against Pinnacle's entry fair.
- **Rushing yards** (§3 calibration gate): Pinnacle's rushing-yards close
  failed the 2023-24 calibration gate (`analysis/train_results_2026-10-04.md`),
  and §3 says a stat that fails is not scored on closing EV. H1b's registered
  Train numbers already exclude rushing. A rushing-inclusive closing EV and
  the rushing legs' realized ROI are printed as an exploratory sensitivity
  line (confirmed 2026-10-15); they never feed a condition or the verdict.

Pass bar (§3, all required):
  1. n >= 30 bets from >= 15 distinct games
  2. mean closing EV > 0
  3. game-clustered bootstrap 95% CI lower bound > 0 (10,000 reps, seed 0)
  4. beats the random-side null at one-sided p < 0.05
     (`evaluation.random_bet_benchmark`, opposite side at its real quote)
  5. survival at first re-check >= 50%
  6. Benjamini-Hochberg q < 0.05 across the family {H1, H1b}
     (H2/H3 dropped, §6 2026-10-13)
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from src.backtest.clv_portfolio import bets_to_frame
from src.backtest.evaluation import random_bet_benchmark
from src.backtest.validation import benjamini_hochberg
from src.clv.decision_report import first_recheck_frame, survival_at_horizon
from src.clv.metrics import clustered_bootstrap
from src.clv.shadow_clv import shadow_clv
from src.features.load_static import STATIC_DIR
from src.signal.prereg_scan import FROZEN_STRATEGIES, PREREG_SHADOW_LOG_PATH
from src.store.bet_log import settle_bets
from src.store.pit_store import PointInTimeStore, kickoffs_from_store

TRAIN_WEEKS = (1, 2, 3, 4)
HOLDOUT_WEEKS = (5, 6, 7, 8, 9)
SCORE_NOT_BEFORE = datetime(2026, 11, 10, 0, 0, tzinfo=ZoneInfo("America/New_York"))

BAD_QUOTE_EV = 0.15
GATE_FAILED_STATS = frozenset({"rushing_yards"})
MIN_BETS = 30
MIN_GAMES = 15
MIN_SURVIVAL = 0.50
ALPHA = 0.05
N_BOOT = 10_000
SEED = 0
EV_BUCKETS = (0.01, 0.02, 0.04, 0.08, BAD_QUOTE_EV)


class BlindedError(RuntimeError):
    """Holdout weeks requested before the pre-registered scoring date."""


def week_of(event_id: str) -> int:
    """`2026_05_MIN_NO` -> 5. Every event_id in the store is an nflverse game_id."""
    return int(str(event_id).split("_")[1])


def check_blind(weeks: Sequence[int], now: datetime | None = None) -> None:
    holdout = sorted(set(weeks) & set(HOLDOUT_WEEKS))
    if holdout and (now or datetime.now(UTC)) < SCORE_NOT_BEFORE:
        raise BlindedError(
            f"weeks {holdout} are the pre-registered holdout; scoring opens "
            f"{SCORE_NOT_BEFORE.isoformat()} (preregistration_wk5-9.md §2)"
        )


def opposite_prices(frame: pd.DataFrame, snapshots: pd.DataFrame) -> pd.Series:
    """The decimal price on the OTHER side of each bet, at the same book, line
    and capture -- what the random-side null pays when it takes that side.
    NaN where the book did not quote it then; the null falls back to fair."""
    props = snapshots[snapshots["market"] == "player_prop"][
        ["event_id", "player_name", "prop_stat", "line", "book", "side", "capture_time", "price_decimal"]
    ]
    flip = {"over": "under", "under": "over"}
    want = frame.reset_index()[["index", "event_id", "player_name", "prop_stat", "line", "book", "side", "decision_time"]]
    want = want.assign(side=want["side"].map(flip), capture_time=pd.to_datetime(want["decision_time"], utc=True))
    m = want.merge(props, on=["event_id", "player_name", "prop_stat", "line", "book", "side", "capture_time"], how="left")
    m = m.drop_duplicates("index", keep="last").set_index("index")
    return m["price_decimal"].reindex(frame.index)


def prepare(store: PointInTimeStore, path: Path, weeks: Sequence[int],
            as_of: datetime | None = None, static_dir: Path = STATIC_DIR) -> pd.DataFrame:
    """Every prereg leg in `weeks`, with closing EV, settlement and the opposite
    quote attached. No exclusions applied -- `score_strategy` does that, so the
    excluded legs remain visible."""
    bets = shadow_clv(store, path=path, as_of=as_of)
    if not bets:
        return pd.DataFrame()
    bets = [b for b in bets if week_of(b.event_id) in set(weeks)]
    if not bets:
        return pd.DataFrame()

    schedule = pd.read_parquet(static_dir / "schedules_2026_2026.parquet")
    player_stats = pd.read_parquet(static_dir / "player_stats_2026_2026.parquet")
    settled = settle_bets(bets, schedule, kickoffs_from_store(store, as_of), player_stats=player_stats)
    frame = bets_to_frame(settled)

    frame["close_ev"] = frame["close_prob_fair"] * frame["price_decimal"] - 1
    frame["entry_ev"] = frame["entry_prob_fair"] * frame["price_decimal"] - 1
    frame["opposite_price_decimal"] = opposite_prices(frame, store.read_as_of(as_of or datetime.now(UTC)))
    return frame


def _ev_bucket_roi(s: pd.DataFrame) -> pd.DataFrame:
    """Realized ROI by entry-EV bucket -- §3 requires it reported, and requires
    that higher-EV buckets not do worse (the 6,812-bet inversion)."""
    settled = s[s["won"].notna()]
    if settled.empty:
        return pd.DataFrame(columns=["bucket", "n", "roi"])
    cut = pd.cut(settled["entry_ev"], bins=list(EV_BUCKETS), right=False)
    ret = np.where(settled["won"].astype(bool), settled["price_decimal"] - 1, -1.0)
    out = pd.DataFrame({"bucket": cut.astype(str), "ret": ret}).groupby("bucket", observed=True)["ret"]
    return out.agg(n="size", roi="mean").reset_index()


def _with_gated_sensitivity(with_gated: pd.DataFrame, gated: pd.DataFrame) -> dict:
    """Exploratory only -- never feeds a condition or the verdict.

    The primary metric drops gate-failed stats because §3 says their closing EV
    isn't a valid yardstick. This shows what the number would be with them back
    in, plus the gated legs' realized ROI, which doesn't depend on the gate.
    """
    n, games = len(with_gated), with_gated["event_id"].nunique()
    boot = clustered_bootstrap(with_gated["close_ev"], with_gated["event_id"], n_resamples=N_BOOT,
                               random_state=SEED) if games >= 2 else None
    settled = gated[gated["won"].notna()]
    ret = np.where(settled["won"].astype(bool), settled["price_decimal"] - 1, -1.0)
    return {
        "n": n, "games": games, "mean_close_ev": float(with_gated["close_ev"].mean()) if n else None,
        "ci_lo": boot and boot["ci_lo"], "ci_hi": boot and boot["ci_hi"],
        "gated_n_settled": len(settled), "gated_realized_roi": float(ret.mean()) if len(settled) else None,
    }


def score_strategy(frame: pd.DataFrame, strategy: str, survival_legs: pd.DataFrame) -> dict:
    s = frame[frame["strategy"] == strategy]
    measurable = s[s["close_ev"].notna()]
    bad = measurable["entry_ev"] > BAD_QUOTE_EV
    gated = measurable["prop_stat"].isin(GATE_FAILED_STATS)
    primary = measurable[~bad & ~gated]

    n, games = len(primary), primary["event_id"].nunique()
    out: dict = {
        "strategy": strategy, "legs_logged": len(s), "measurable": len(measurable),
        "excluded_bad_quote": int(bad.sum()), "excluded_gate_failed_stat": int((gated & ~bad).sum()),
        "n": n, "games": games, "mean_close_ev": float(primary["close_ev"].mean()) if n else None,
        "excluded_close_ev": float(measurable[bad | gated]["close_ev"].mean()) if (bad | gated).any() else None,
        "mean_clv_probability": float(primary["clv_probability"].mean()) if n else None,
    }

    boot = clustered_bootstrap(primary["close_ev"], primary["event_id"], n_resamples=N_BOOT,
                               random_state=SEED) if games >= 2 else None
    out.update(ci_lo=boot and boot["ci_lo"], ci_hi=boot and boot["ci_hi"], p_one_sided=boot and boot["p_one_sided"])

    settled = primary[primary["won"].notna()].copy()
    if len(settled):
        null_input = settled.assign(fair_prob=settled["close_prob_fair"], won=settled["won"].astype(bool))
        null = random_bet_benchmark(null_input[["fair_prob", "price_decimal", "won", "opposite_price_decimal"]],
                                    random_state=SEED)
        out.update(null_p=null["p_one_sided"], realized_roi=null["observed_roi"],
                   null_mean_roi=null["null_mean_roi"], null_opposite_price=null["opposite_price_source"],
                   n_settled=len(settled))
    else:
        out.update(null_p=None, realized_roi=None, null_mean_roi=None, null_opposite_price=None, n_settled=0)

    surv, surv_n, _ = survival_at_horizon(survival_legs, strategy)
    out.update(survival=surv, survival_n=surv_n)

    out["ev_buckets"] = _ev_bucket_roi(primary)
    out["with_gated"] = _with_gated_sensitivity(measurable[~bad], measurable[~bad & gated])
    out["conditions"] = {
        "1_n_and_games": n >= MIN_BETS and games >= MIN_GAMES,
        "2_mean_positive": bool(n) and out["mean_close_ev"] > 0,
        "3_ci_excludes_zero": out["ci_lo"] is not None and out["ci_lo"] > 0,
        "4_beats_random_null": out["null_p"] is not None and out["null_p"] < ALPHA,
        "5_survival": surv is not None and surv >= MIN_SURVIVAL,
    }
    return out


def score(store: PointInTimeStore, weeks: Sequence[int], path: Path = PREREG_SHADOW_LOG_PATH,
          as_of: datetime | None = None, now: datetime | None = None,
          static_dir: Path = STATIC_DIR) -> list[dict]:
    """Every frozen strategy, scored on `weeks`, with BH (condition 6) applied
    across the family. Raises `BlindedError` for holdout weeks before 11-10."""
    check_blind(weeks, now)
    frame = prepare(store, path, weeks, as_of, static_dir)
    legs = first_recheck_frame(path)
    if not legs.empty:
        legs = legs[legs["alert_key"].map(lambda k: week_of(k.split("|")[1]) in set(weeks))]

    results = [score_strategy(frame, s.name, legs) if not frame.empty else
               {"strategy": s.name, "n": 0, "p_one_sided": None, "conditions": {}} for s in FROZEN_STRATEGIES]

    p = [r["p_one_sided"] if r["p_one_sided"] is not None else 1.0 for r in results]
    rejected = benjamini_hochberg(p, q=ALPHA)
    for r, bh in zip(results, rejected, strict=True):
        r.setdefault("conditions", {})["6_bh_family"] = bool(bh)
        conds = r["conditions"]
        r["verdict"] = "PASS" if conds and len(conds) == 6 and all(conds.values()) else "FAIL"
    return results


def _fmt(v, pct: bool = False) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "n/a"
    return f"{v:+.2%}" if pct else f"{v:.4f}"


def format_results(results: list[dict], weeks: Sequence[int]) -> str:
    lines = [f"PRE-REGISTERED SCORING  weeks {list(weeks)}  (preregistration_wk5-9.md §3)", ""]
    for r in results:
        lines.append(f"{r['strategy']}: {r.get('verdict', 'FAIL')}")
        if not r.get("n"):
            lines.append("  no measurable legs")
            continue
        lines += [
            (
                f"  legs logged {r['legs_logged']}, measurable {r['measurable']}, excluded: "
                f"bad quote {r['excluded_bad_quote']}, gate-failed stat {r['excluded_gate_failed_stat']} "
                f"(their mean close EV {_fmt(r['excluded_close_ev'], True)})"
            ),
            (
                f"  n={r['n']} over {r['games']} games  close EV {_fmt(r['mean_close_ev'], True)} "
                f"[{_fmt(r['ci_lo'], True)}, {_fmt(r['ci_hi'], True)}]  p={_fmt(r['p_one_sided'])}"
            ),
            (
                f"  realized ROI {_fmt(r['realized_roi'], True)} on {r['n_settled']} settled vs null "
                f"{_fmt(r['null_mean_roi'], True)} (opposite price: {r['null_opposite_price']}), p={_fmt(r['null_p'])}"
            ),
            (
                f"  survival {_fmt(r['survival'], True)} (n={r['survival_n']})   "
                f"clv_probability {_fmt(r['mean_clv_probability'])} (adverse selection, reported only)"
            ),
        ]
        for name, ok in r["conditions"].items():
            lines.append(f"    [{'x' if ok else ' '}] {name}")
        g = r["with_gated"]
        lines += [
            (
                f"  EXPLORATORY, not in verdict -- with rushing yards: n={g['n']} over {g['games']} games  "
                f"close EV {_fmt(g['mean_close_ev'], True)} [{_fmt(g['ci_lo'], True)}, {_fmt(g['ci_hi'], True)}]"
            ),
            f"    rushing legs realized ROI {_fmt(g['gated_realized_roi'], True)} on {g['gated_n_settled']} settled",
        ]
        if not r["ev_buckets"].empty:
            lines.append("  realized ROI by entry-EV bucket (must not invert):")
            for b in r["ev_buckets"].itertuples():
                lines.append(f"    {b.bucket:<14} n={b.n:<4} roi {b.roi:+.2%}")
        lines.append("")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--weeks", choices=("train", "holdout"), required=True)
    args = parser.parse_args(argv)
    weeks = TRAIN_WEEKS if args.weeks == "train" else HOLDOUT_WEEKS
    try:
        results = score(PointInTimeStore(), weeks)
    except BlindedError as exc:
        raise SystemExit(f"BLINDED: {exc}") from None
    print(format_results(results, weeks))


if __name__ == "__main__":
    main()
