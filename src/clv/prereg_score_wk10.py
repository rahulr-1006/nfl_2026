"""Score H5 (moneyline longshots) against preregistration_wk10-14.md.

**A separate module on purpose.** `prereg_score.py` is the scorer the Weeks 5-9
pre-registration names; changing it after that commit would be a scoring-code
deviation. This one reuses its pass-bar arithmetic (`score_strategy`, conditions
1-5) unchanged and adds only what a moneyline needs: the opposite side's real
same-book quote for the random-side null, and the > 3.0 price region where
Pinnacle's moneyline close passed calibration.

**Blinded by date**, like the Weeks 5-9 scorer: holdout weeks (10-14) raise
before 2026-12-15 ET, with no override flag.

Condition 6 (BH) runs over H5 plus whichever of H1/H1b pass on 11-10; their
Weeks 10-14 p-values are passed in as `family_p` once they exist.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from src.backtest.clv_portfolio import bets_to_frame
from src.backtest.validation import benjamini_hochberg
from src.clv.decision_report import first_recheck_frame
from src.clv.prereg_score import ALPHA, BlindedError, _fmt, score_strategy, week_of
from src.clv.shadow_clv import shadow_alerts_as_bets
from src.features.load_static import STATIC_DIR
from src.signal.shadow_log import SHADOW_LOG_PATH
from src.store.bet_log import settle_bets, to_backtest_bets
from src.store.pit_store import PointInTimeStore, kickoffs_from_store

TRAIN_WEEKS = tuple(range(1, 10))
HOLDOUT_WEEKS = (10, 11, 12, 13, 14)
SCORE_NOT_BEFORE = datetime(2026, 12, 15, 0, 0, tzinfo=ZoneInfo("America/New_York"))

H5 = "moneyline_ev"
LONGSHOT_MIN_PRICE = 3.0  # strict: the gate passed for fair decimal > 3.0
KEY = ["event_id", "decision_time", "market", "side", "book"]


def check_blind(weeks: Sequence[int], now: datetime | None = None) -> None:
    holdout = sorted(set(weeks) & set(HOLDOUT_WEEKS))
    if holdout and (now or datetime.now(UTC)) < SCORE_NOT_BEFORE:
        raise BlindedError(
            f"weeks {holdout} are the Weeks 10-14 holdout; scoring opens "
            f"{SCORE_NOT_BEFORE.isoformat()} (preregistration_wk10-14.md §2)"
        )


def moneyline_opposite_prices(frame: pd.DataFrame, snapshots: pd.DataFrame) -> pd.Series:
    """The other side's decimal price at the same book and capture. NaN where the
    book had no quote then; the null then falls back to the no-vig fair price."""
    ml = snapshots[snapshots["market"] == "moneyline"][["event_id", "book", "side", "capture_time", "price_decimal"]]
    flip = {"home": "away", "away": "home"}
    want = frame.reset_index()[["index", "event_id", "book", "side", "decision_time"]]
    want = want.assign(side=want["side"].map(flip), capture_time=pd.to_datetime(want["decision_time"], utc=True))
    m = want.merge(ml, on=["event_id", "book", "side", "capture_time"], how="left")
    m = m.drop_duplicates("index", keep="last").set_index("index")
    return m["price_decimal"].reindex(frame.index)


def prepare_h5(store: PointInTimeStore, weeks: Sequence[int], as_of: datetime | None = None,
               path: Path = SHADOW_LOG_PATH, static_dir: Path = STATIC_DIR) -> pd.DataFrame:
    """H5's legs in `weeks`: earliest alert per (game, side), priced, settled,
    restricted to the > 3.0 region. Bad quotes are left in for `score_strategy`
    to exclude and count."""
    logged = [b for b in shadow_alerts_as_bets(path) if b.strategy == H5 and week_of(b.event_id) in set(weeks)]
    if not logged:
        return pd.DataFrame()
    priced = to_backtest_bets(logged, store, as_of=as_of)
    keys = bets_to_frame(priced).assign(alert_key=[b.alert_key for b in logged])[KEY + ["alert_key"]]

    schedule = pd.read_parquet(static_dir / "schedules_2026_2026.parquet")
    frame = bets_to_frame(settle_bets(priced, schedule, kickoffs_from_store(store, as_of)))
    frame = frame.merge(keys.drop_duplicates(KEY), on=KEY, how="left", validate="many_to_one")
    frame = frame[frame["price_decimal"] > LONGSHOT_MIN_PRICE].reset_index(drop=True)

    frame["close_ev"] = frame["close_prob_fair"] * frame["price_decimal"] - 1
    frame["entry_ev"] = frame["entry_prob_fair"] * frame["price_decimal"] - 1
    frame["opposite_price_decimal"] = moneyline_opposite_prices(frame, store.read_as_of(as_of or datetime.now(UTC)))
    return frame


def score(store: PointInTimeStore, weeks: Sequence[int], family_p: Sequence[float] = (),
          as_of: datetime | None = None, now: datetime | None = None,
          path: Path = SHADOW_LOG_PATH, static_dir: Path = STATIC_DIR) -> dict:
    check_blind(weeks, now)
    frame = prepare_h5(store, weeks, as_of, path, static_dir)
    if frame.empty:
        return {"strategy": H5, "n": 0, "conditions": {}, "verdict": "FAIL"}
    legs = first_recheck_frame(path)
    legs = legs[legs["alert_key"].isin(set(frame["alert_key"].dropna()))]

    r = score_strategy(frame, H5, legs)
    p = [r["p_one_sided"] if r["p_one_sided"] is not None else 1.0, *family_p]
    r["conditions"]["6_bh_family"] = bool(benjamini_hochberg(p, q=ALPHA)[0])
    r["family_size"] = len(p)
    r["verdict"] = "PASS" if all(r["conditions"].values()) else "FAIL"
    return r


def format_result(r: dict, weeks: Sequence[int]) -> str:
    title = (f"PRE-REGISTERED SCORING  H5 moneyline longshots (>{LONGSHOT_MIN_PRICE})  weeks {list(weeks)}  "
             "(preregistration_wk10-14.md)")
    lines = [title, "", f"H5: {r['verdict']}"]
    if not r.get("n"):
        return "\n".join([*lines, "  no measurable legs"])
    lines += [
        f"  legs {r['legs_logged']}, measurable {r['measurable']}, bad quotes excluded {r['excluded_bad_quote']}",
        (f"  n={r['n']} over {r['games']} games  close EV {_fmt(r['mean_close_ev'], True)} "
         f"[{_fmt(r['ci_lo'], True)}, {_fmt(r['ci_hi'], True)}]  p={_fmt(r['p_one_sided'])}"),
        (f"  realized ROI {_fmt(r['realized_roi'], True)} on {r['n_settled']} settled vs null "
         f"{_fmt(r['null_mean_roi'], True)} (opposite price: {r['null_opposite_price']}), p={_fmt(r['null_p'])}"),
        (f"  survival {_fmt(r['survival'], True)} (n={r['survival_n']})   clv_probability "
         f"{_fmt(r['mean_clv_probability'])} (reported only)   BH family size {r['family_size']}"),
    ]
    lines += [f"    [{'x' if ok else ' '}] {name}" for name, ok in r["conditions"].items()]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--weeks", choices=("train", "holdout"), required=True)
    parser.add_argument("--family-p", type=float, nargs="*", default=(),
                        help="Weeks 10-14 one-sided p-values of the H1/H1b replications in the family")
    args = parser.parse_args(argv)
    weeks = TRAIN_WEEKS if args.weeks == "train" else HOLDOUT_WEEKS
    try:
        result = score(PointInTimeStore(), weeks, family_p=args.family_p)
    except BlindedError as exc:
        raise SystemExit(f"BLINDED: {exc}") from None
    print(format_result(result, weeks))


if __name__ == "__main__":
    main()
