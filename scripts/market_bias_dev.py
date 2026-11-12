"""H7 / H8 development run on 2015-2024. 2025 is never read here.

    .venv/bin/python -m scripts.market_bias_dev
"""

from __future__ import annotations

import pandas as pd

from src.backtest.market_bias import (
    DEV_SEASONS,
    H7_BAND,
    H8_WIND_GRID,
    evaluate,
    h7_bets,
    h8_bets,
    passes_stability,
    seasons,
)
from src.features.load_static import STATIC_DIR


def report(name: str, r: dict) -> None:
    if "roi" not in r:
        print(f"\n{name}: n={r['n']} (too few)")
        return
    print(f"\n{name}: n={r['n']} (+{r['pushes']} pushes)  ROI {r['roi']:+.2%} [{r['ci_lo']:+.2%}, {r['ci_hi']:+.2%}] "
          f"p={r['p_roi']:.3f}   null {r['null_mean']:+.2%} p={r['null_p']:.3f}   "
          f"hit {r['hit']:.3f} vs fair {r['mean_fair']:.3f}")
    print(f"  seasons positive {r['seasons_positive']}/{r['seasons']}   stability gate: "
          f"{'PASS' if passes_stability(r) else 'FAIL'}")
    print("  " + r["by_season"].assign(roi=lambda x: x["roi"].map("{:+.1%}".format)).T.to_string().replace("\n", "\n  "))


def main() -> None:
    schedule = pd.read_parquet(STATIC_DIR / "schedules_2015_2025.parquet")
    dev = seasons(schedule, DEV_SEASONS)
    assert dev["season"].max() < 2025
    report(f"H7 away in close games, home p in {H7_BAND}", evaluate(h7_bets(dev)))
    for w in H8_WIND_GRID:
        report(f"H8 unders, wind >= {w:g} mph (outdoor/open)", evaluate(h8_bets(dev, w)))


if __name__ == "__main__":
    main()
