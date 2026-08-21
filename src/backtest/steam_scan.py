"""Steam-scan entrypoint: `python -m src.backtest.steam_scan`.

Manual, run-by-hand, not a launchd service -- same reasoning as
`src/backtest/middle_scan.py`: real synchronized multi-book movement takes
time to accumulate, and this strategy has zero live track record yet, so
print/log output reviewed by hand comes before any unattended alert channel.

Fits the margin/total regression models once per run purely for their
residual std (`sigma_margin`/`sigma_total`), the exact same reuse
`middle_scan.py` makes and for the same reason (`mu` comes from Pinnacle's
own post-steam line, not the model's prediction -- see
`src/backtest/steam.py`/`src/backtest/middling.py`'s module docstrings).
"""

from __future__ import annotations

import logging

import pandas as pd

from src.backtest.middle_scan import fit_residual_stds
from src.backtest.steam import find_steam_opportunities
from src.store.pit_store import PointInTimeStore

log = logging.getLogger(__name__)


def run(store_root: str = "data/snapshots", min_ev: float = 0.0) -> pd.DataFrame:
    """One scan. Returns the report DataFrame (also logged); never sends
    any notification -- print/log output only, reviewed by hand.
    """
    sigma_margin, sigma_total = fit_residual_stds()
    log.info("fitted residual stds: sigma_margin=%.2f sigma_total=%.2f", sigma_margin, sigma_total)

    store = PointInTimeStore(root=store_root)
    report = find_steam_opportunities(store, sigma_margin=sigma_margin, sigma_total=sigma_total)

    if report.empty:
        log.info("scan ok: no real steam moves in the current store")
        return report

    report = report[report["edge"] >= min_ev]
    if report.empty:
        log.info("scan ok: steam moves exist but none clear ev >= %.4f", min_ev)
        return report

    for row in report.itertuples():
        log.info(
            "%s %s %s: STALE %s @ %.1f -- %d books moved (%s) toward %+.0f, "
            "mu=%.2f sigma=%.2f p_win=%.3f ev=$%.3f stake=$%.2f",
            row.event_id,
            row.market,
            row.side,
            row.stale_book,
            row.stale_line,
            row.n_books_moved,
            row.books_moved,
            row.steam_direction,
            row.mu,
            row.sigma,
            row.p_win,
            row.edge,
            row.suggested_stake,
        )
    return report


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    run()


if __name__ == "__main__":
    main()
