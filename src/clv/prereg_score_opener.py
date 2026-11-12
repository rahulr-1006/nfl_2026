"""Score H6 (Elo vs Pinnacle's T-120h moneyline) against
preregistration_opener_wk11-18.md.

**Blinded by date**, like the other scorers: Weeks 11-18 raise before
2027-01-12 ET (the Tuesday after Week 18), with no override flag. Development
(2024 + 2026 Weeks 1-9) is always allowed and is what `scripts/opener_dev.py`
prints.

The gate is the movement slope beta (no tau to choose), so this scorer has no
tuning parameters of its own; everything it reads is fixed in
`backtest.opener_movement`.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from src.backtest.opener_movement import bets, build_frame, fit_elo_calibration
from src.clv.metrics import clustered_bootstrap
from src.clv.prereg_score import ALPHA, BlindedError
from src.features.load_static import STATIC_DIR, kickoffs_utc
from src.model.elo import compute_team_elo_ratings
from src.store.pit_store import PointInTimeStore

HOLDOUT_WEEKS = tuple(range(11, 19))
SCORE_NOT_BEFORE = datetime(2027, 1, 12, 0, 0, tzinfo=ZoneInfo("America/New_York"))
MIN_GAMES = 30
N_RESAMPLES = 10000
SEED = 0
REPORTED_TAU = 0.03  # secondary, reported only; fixed in the pre-registration


def check_blind(now: datetime | None = None) -> None:
    if (now or datetime.now(UTC)) < SCORE_NOT_BEFORE:
        raise BlindedError(f"Weeks 11-18 are the H6 holdout; scoring opens {SCORE_NOT_BEFORE.isoformat()} "
                           "(preregistration_opener_wk11-18.md §2)")


def slope_test(frame: pd.DataFrame, n_resamples: int = N_RESAMPLES, seed: int = SEED) -> dict:
    """beta of m on d (no intercept) with a game-level bootstrap. `p_one_sided`
    is the share of resampled betas <= 0."""
    d, m = frame["d"].to_numpy(), frame["m"].to_numpy()
    beta = float((d @ m) / (d @ d))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(n_resamples, len(d)))
    dd, mm = d[idx], m[idx]
    betas = (dd * mm).sum(axis=1) / (dd * dd).sum(axis=1)
    return {"beta": beta, "ci_lo": float(np.percentile(betas, 2.5)), "ci_hi": float(np.percentile(betas, 97.5)),
            "p_one_sided": float((betas <= 0).mean())}


def verdict(frame: pd.DataFrame) -> dict:
    """Conditions 1-3 of the pre-registration's pass bar, plus reported-only
    secondaries."""
    out: dict = {"games": len(frame)}
    if len(frame) < 3:
        out["conditions"] = {"1_n_games": False}
        out["verdict"] = "FAIL"
        return out
    s = slope_test(frame)
    out.update(s)
    out["conditions"] = {
        "1_n_games": len(frame) >= MIN_GAMES,
        "2_beta_positive": s["beta"] > 0,
        "3_ci_excludes_zero_and_p": s["ci_lo"] > 0 and s["p_one_sided"] < ALPHA,
    }
    out["verdict"] = "PASS" if all(out["conditions"].values()) else "FAIL"

    b = bets(frame, REPORTED_TAU)
    if len(b) >= 2:
        boot = clustered_bootstrap(b["clv_move"], b["event_id"], n_resamples=N_RESAMPLES)
        out["tau_n"], out["tau_clv_move"], out["tau_ci"] = len(b), boot["mean"], (boot["ci_lo"], boot["ci_hi"])
        ev = b["soft_close_ev"].dropna()
        out["soft_close_ev"], out["soft_n"] = (float(ev.mean()) if len(ev) else None), len(ev)
        real = b["realized"].dropna()
        out["realized_roi"], out["realized_n"] = (float(real.mean()) if len(real) else None), len(real)
    return out


def load_schedule(static_dir=STATIC_DIR) -> pd.DataFrame:
    hist = pd.read_parquet(static_dir / "schedules_2015_2025.parquet")
    cur = pd.read_parquet(static_dir / "schedules_2026_2026.parquet")
    return pd.concat([hist, cur[~cur["game_id"].isin(hist["game_id"])]], ignore_index=True)


def score(store: PointInTimeStore, now: datetime | None = None, static_dir=STATIC_DIR) -> tuple[dict, dict]:
    check_blind(now)
    schedule = load_schedule(static_dir)
    kickoffs = pd.Series(kickoffs_utc(schedule).to_numpy(), index=schedule["game_id"])
    ratings = compute_team_elo_ratings(schedule)
    ids = schedule[(schedule["season"] == 2026) & schedule["week"].isin(HOLDOUT_WEEKS)]["game_id"].tolist()
    frame, excluded = build_frame(store, schedule, kickoffs, ids, fit_elo_calibration(schedule, ratings), ratings,
                                  now=now)
    return verdict(frame), excluded


def format_result(r: dict, excluded: dict) -> str:
    title = ("PRE-REGISTERED SCORING  H6 Elo vs Pinnacle T-120h moneyline  Weeks 11-18 "
             "(preregistration_opener_wk11-18.md)")
    lines = [title, "", f"H6: {r['verdict']}   games {r['games']}   excluded {excluded}"]
    if "beta" in r:
        lines.append(f"  beta {r['beta']:+.3f} [{r['ci_lo']:+.3f}, {r['ci_hi']:+.3f}]  p={r['p_one_sided']:.4f}")
    lines += [f"    [{'x' if ok else ' '}] {name}" for name, ok in r["conditions"].items()]
    if "tau_n" in r:
        lo, hi = r["tau_ci"]
        lines.append(f"  reported only, tau={REPORTED_TAU}: n={r['tau_n']} clv_move {r['tau_clv_move']:+.2%} "
                     f"[{lo:+.2%}, {hi:+.2%}]   soft close EV "
                     f"{'n/a' if r['soft_close_ev'] is None else format(r['soft_close_ev'], '+.2%')} (n={r['soft_n']})   "
                     f"realized {'n/a' if r['realized_roi'] is None else format(r['realized_roi'], '+.2%')} "
                     f"(n={r['realized_n']})")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> None:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    try:
        result, excluded = score(PointInTimeStore())
    except BlindedError as exc:
        raise SystemExit(f"BLINDED: {exc}") from None
    print(format_result(result, excluded))


if __name__ == "__main__":
    main()
