"""H6 development run: Elo vs Pinnacle's T-120h moneyline, on the two samples
that have early prices -- 2024 (bought series) and 2026 Weeks 1-9 (live store).

Week 10 is excluded on purpose: its T-120h prices were recorded before the H6
pre-registration could be committed, so it can be neither development data (it
would leak into the freeze) nor holdout (its early price predates the commit).

    .venv/bin/python -m scripts.opener_dev
"""

from __future__ import annotations

import pandas as pd

from src.backtest.opener_movement import (
    TAU_GRID,
    build_frame,
    fit_elo_calibration,
    reliability_table,
    summarize,
)
from src.features.load_static import STATIC_DIR, kickoffs_utc
from src.model.elo import compute_team_elo_ratings
from src.store.pit_store import PointInTimeStore

DEV_2026_WEEKS = tuple(range(1, 10))


def load_schedule() -> pd.DataFrame:
    hist = pd.read_parquet(STATIC_DIR / "schedules_2015_2025.parquet")
    cur = pd.read_parquet(STATIC_DIR / "schedules_2026_2026.parquet")
    return pd.concat([hist, cur[~cur["game_id"].isin(hist["game_id"])]], ignore_index=True)


def samples(schedule: pd.DataFrame) -> dict[str, list[str]]:
    s24 = schedule[schedule["season"] == 2024]["game_id"].tolist()
    s26 = schedule[(schedule["season"] == 2026) & schedule["week"].isin(DEV_2026_WEEKS)]["game_id"].tolist()
    return {"2024": s24, "2026 wk1-9": s26}


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x:+.2%}"


def report(name: str, frame: pd.DataFrame, excluded: dict) -> None:
    print(f"\n=== {name}: {len(frame)} games  excluded {excluded}")
    if frame.empty:
        return
    print(f"  mean |d| {frame['d'].abs().mean():.3f}   mean |m| {frame['m'].abs().mean():.3f}   "
          f"corr(d, m) {frame['d'].corr(frame['m']):+.3f}")
    s = summarize(frame)
    sl = s["slope"]
    print(f"  slope m~d  beta {sl['beta']:+.3f} [{sl['ci_lo']:+.3f}, {sl['ci_hi']:+.3f}]")
    mo = s["momentum"]
    if mo.get("slope") is not None:
        print(f"  momentum (exploratory) slope {mo['slope']:+.3f} [{mo['ci_lo']:+.3f}, {mo['ci_hi']:+.3f}] n={mo['n']}")
    for tau, r in s["by_tau"].items():
        if r["n"] < 2:
            print(f"  tau {tau:.2f}: n={r['n']}")
            continue
        print(f"  tau {tau:.2f}: n={r['n']:3d}  clv_move {_pct(r['clv_move'])} [{_pct(r['ci_lo'])}, {_pct(r['ci_hi'])}] "
              f"p={r['p']:.3f}   soft close EV {_pct(r['soft_close_ev'])} (n={r['soft_n']})   "
              f"realized {_pct(r['realized_roi'])} (n={r['realized_n']})")


def main() -> None:
    schedule = load_schedule()
    kickoffs = pd.Series(kickoffs_utc(schedule).to_numpy(), index=schedule["game_id"])
    ratings = compute_team_elo_ratings(schedule)
    calibration = fit_elo_calibration(schedule, ratings)
    print(f"Platt calibration (fit 2015-2022): coef {calibration.coef_[0][0]:.3f}  "
          f"intercept {calibration.intercept_[0]:+.3f}")
    print("Reliability on 2023 (out of calibration):")
    print(reliability_table(schedule, ratings, calibration, 2023).round(3).to_string())

    store = PointInTimeStore()
    for name, ids in samples(schedule).items():
        frame, excluded = build_frame(store, schedule, kickoffs, ids, calibration, ratings)
        report(name, frame, excluded)
    print(f"\ntau grid {TAU_GRID}; CIs are game-level bootstrap, 10,000 resamples, seed 0")


if __name__ == "__main__":
    main()
