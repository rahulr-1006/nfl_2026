"""Middle-scan entrypoint: `python -m src.backtest.middle_scan`.

A manual, run-by-hand check, not a launchd service -- unlike
`src/notify/monitor_run.py`. Two reasons this stays manual for now, same
discipline already applied to the props scheduler ([[player_props_infra]]
in memory: don't install a service before there's real, live-confirmed
reason to expect it will find something):

1. Real line movement takes days to accumulate (see the module docstring
   in `src/backtest/middling.py`) -- a 5-minute polling cadence has
   nothing new to check most of the time this early in the pre-season
   window.
2. This strategy has zero live track record yet. Wiring it straight to an
   SMS alert (like `monitor_run.py` does) before a single real opportunity
   has ever been manually reviewed would be trusting an untested pricing
   model with an unattended notification channel -- reviewed print output
   first, alerts later if this proves out.

Reads the real cached 2015-2024 schedule + play-by-play to fit the
existing margin/total regression models ONE TIME per run, purely to
extract their residual std (`sigma_margin`/`sigma_total` via
`fit_residual_std`) -- the models' own point predictions are discarded
(see `src/backtest/middling.py`'s module docstring for why `mu` comes from
Pinnacle instead). This refit is cheap (sub-second on the cached parquet
files, no network calls) but not free, so this script is meant to be run
by hand a few times as the pre-season window progresses, not on every
collector tick.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.backtest.middling import find_middle_opportunities
from src.model.calibration import fit_residual_std
from src.model.elo import compute_team_elo_ratings
from src.model.qb_elo import compute_qb_elo_ratings
from src.model.train import (
    COMBINED_QB_FEATURE_COLUMNS,
    build_margin_total_frame,
    fit_margin_model,
    fit_total_model,
    time_based_split,
)
from src.store.pit_store import PointInTimeStore

log = logging.getLogger(__name__)

_DATA_ROOT = Path("data/static")


def _fit_residual_stds() -> tuple[float, float]:
    """(sigma_margin, sigma_total), reusing the exact fitting pipeline
    already validated in `notebooks/model_backtest_results.ipynb` (same
    train/calib/test split, same feature set) -- not a fresh model, a
    reuse of the one this project already trusts.
    """
    schedule = pd.read_parquet(_DATA_ROOT / "schedules_2015_2024.parquet")
    pbp = pd.read_parquet(_DATA_ROOT / "pbp_2015_2024.parquet")

    elo_ratings = compute_team_elo_ratings(schedule)
    qb_elo_ratings = compute_qb_elo_ratings(schedule, elo_ratings)
    training_df = build_margin_total_frame(pbp, schedule, elo_ratings=elo_ratings, qb_elo_ratings=qb_elo_ratings)
    train_df, calib_df, _test_df = time_based_split(
        training_df, train_seasons=range(2015, 2022), calib_seasons=[2022], test_seasons=[2023, 2024]
    )

    margin_model = fit_margin_model(train_df, feature_columns=COMBINED_QB_FEATURE_COLUMNS)
    total_model = fit_total_model(train_df, feature_columns=COMBINED_QB_FEATURE_COLUMNS)
    sigma_margin = fit_residual_std(margin_model, calib_df, COMBINED_QB_FEATURE_COLUMNS, "margin")
    sigma_total = fit_residual_std(total_model, calib_df, COMBINED_QB_FEATURE_COLUMNS, "total_points")
    return sigma_margin, sigma_total


def run(store_root: str = "data/snapshots", min_ev: float = 0.0) -> pd.DataFrame:
    """One scan. Returns the report DataFrame (also logged); never sends
    any notification -- print/log output only, reviewed by hand.
    """
    sigma_margin, sigma_total = _fit_residual_stds()
    log.info("fitted residual stds: sigma_margin=%.2f sigma_total=%.2f", sigma_margin, sigma_total)

    store = PointInTimeStore(root=store_root)
    report = find_middle_opportunities(store, sigma_margin=sigma_margin, sigma_total=sigma_total)

    if report.empty:
        log.info("scan ok: no real middle windows in the current store (expected early in the pre-season window)")
        return report

    report = report[report["ev"] >= min_ev]
    if report.empty:
        log.info("scan ok: real windows exist but none clear ev >= %.4f", min_ev)
        return report

    for row in report.itertuples():
        log.info(
            "%s %s: %s %s(%.1f)@%.2f vs %s %s(%.1f)@%.2f -- window (%.1f, %.1f) width=%.1f "
            "mu=%.2f sigma=%.2f p_both=%.3f ev=$%.3f on $%.2f risked",
            row.event_id,
            row.market,
            row.book_a,
            row.side_a,
            row.line_a,
            row.price_decimal_a,
            row.book_b,
            row.side_b,
            row.line_b,
            row.price_decimal_b,
            row.window_lo,
            row.window_hi,
            row.window_width,
            row.mu,
            row.sigma,
            row.p_both_win,
            row.ev,
            row.total_risked,
        )
    return report


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    run()


if __name__ == "__main__":
    main()
