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

import json
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


def fit_residual_stds() -> tuple[float, float]:
    """(sigma_margin, sigma_total) for LIVE pricing -- not the research
    evaluation split used in `notebooks/model_backtest_results.ipynb`
    (train 2015-2021/calib 2022/test 2023-2024). This is a deployed tool
    pricing real 2026 games, not a research comparison, so it has no
    reason to hold back real historical data the way an evaluation split
    does: trains on 2015-2024 and calibrates (fits residual std) on the
    freshest complete season, 2025 -- closer to current NFL conditions
    than the notebook's 2022 calib season, and the exact season this
    project is now deliberately keeping OUT of every research comparison
    so it stays a genuine, never-touched holdout (2026-08-21 finding: this
    project had never pulled 2025 data at all until asked to check whether
    the cached data was current). `test_seasons=[]` -- this function never
    reports test metrics, only extracts sigma from the calibration split.
    """
    schedule = pd.read_parquet(_DATA_ROOT / "schedules_2015_2025.parquet")
    pbp = pd.read_parquet(_DATA_ROOT / "pbp_2015_2025.parquet")

    elo_ratings = compute_team_elo_ratings(schedule)
    qb_elo_ratings = compute_qb_elo_ratings(schedule, elo_ratings)
    training_df = build_margin_total_frame(pbp, schedule, elo_ratings=elo_ratings, qb_elo_ratings=qb_elo_ratings)
    train_df, calib_df, _test_df = time_based_split(
        training_df, train_seasons=range(2015, 2025), calib_seasons=[2025], test_seasons=[]
    )

    margin_model = fit_margin_model(train_df, feature_columns=COMBINED_QB_FEATURE_COLUMNS)
    total_model = fit_total_model(train_df, feature_columns=COMBINED_QB_FEATURE_COLUMNS)
    sigma_margin = fit_residual_std(margin_model, calib_df, COMBINED_QB_FEATURE_COLUMNS, "margin")
    sigma_total = fit_residual_std(total_model, calib_df, COMBINED_QB_FEATURE_COLUMNS, "total_points")
    return sigma_margin, sigma_total


_SIGMA_CACHE_PATH = Path("data/residual_sigma_cache.json")
_SIGMA_MEMO: dict[str, tuple[float, float]] = {}


def _training_data_fingerprint() -> str:
    """Identifies the exact training inputs a cached sigma was fitted on, so the
    cache invalidates itself when the cached parquet files are refreshed (as
    they were for the 2025 season) rather than silently pricing live bets off
    a stale model.
    """
    parts = []
    for name in ("schedules_2015_2025.parquet", "pbp_2015_2025.parquet"):
        stat = (_DATA_ROOT / name).stat()
        parts.append(f"{name}:{stat.st_mtime_ns}:{stat.st_size}")
    return "|".join(parts)


def cached_residual_stds(cache_path: Path = _SIGMA_CACHE_PATH) -> tuple[float, float]:
    """`fit_residual_stds()` memoized in-process and on disk.

    The uncached fit reads the full 2015-2025 play-by-play parquet and fits Elo,
    QB Elo and two regressions -- ~10s. That is fine for a hand-run scan, but
    `src/notify/monitor_run.py` runs every ~5 minutes and would otherwise redo
    the identical fit ~288 times a day to recover two numbers that only change
    when the cached training data does.
    """
    fingerprint = _training_data_fingerprint()
    if fingerprint in _SIGMA_MEMO:
        return _SIGMA_MEMO[fingerprint]

    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text())
            if cached.get("fingerprint") == fingerprint:
                sigmas = (float(cached["sigma_margin"]), float(cached["sigma_total"]))
                _SIGMA_MEMO[fingerprint] = sigmas
                return sigmas
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            log.warning("residual-sigma cache at %s is unreadable, refitting", cache_path)

    sigma_margin, sigma_total = fit_residual_stds()
    _SIGMA_MEMO[fingerprint] = (sigma_margin, sigma_total)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps({
        "fingerprint": fingerprint,
        "sigma_margin": sigma_margin,
        "sigma_total": sigma_total,
    }))
    return sigma_margin, sigma_total


def run(store_root: str = "data/snapshots", min_ev: float = 0.0) -> pd.DataFrame:
    """One scan. Returns the report DataFrame (also logged); never sends
    any notification -- print/log output only, reviewed by hand.
    """
    sigma_margin, sigma_total = fit_residual_stds()
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
