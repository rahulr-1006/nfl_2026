"""Score H8 (wind unders) on the 2025 season against
preregistration_2025_market_bias.md.

**Blinded by the document, not a date.** 2025 is already played, so a date lock
would protect nothing. Instead this refuses to run until the pre-registration's
status line reads FINAL, which is only set in the commit that freezes it. That
commit's timestamp is the evidence the rule came first.

**Primary price is Pinnacle's real close**, bought by
`scripts/pull_2025_wind_closes.py`: the under at Pinnacle's own closing line
and price. nflverse's line (the development source) is reported alongside but
does not gate. H7 failed the development stability gate and is not scored here.
"""

from __future__ import annotations

import argparse
import re
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd

from src.backtest.evaluation import random_bet_benchmark
from src.backtest.market_bias import HOLDOUT_SEASON, OUTDOOR_ROOFS, _settle, h8_bets
from src.clv.metrics import clustered_bootstrap
from src.clv.prereg_score import ALPHA, BlindedError
from src.devig.methods import devig_shin
from src.features.load_static import STATIC_DIR, kickoffs_utc
from src.signal.live_scan import EXECUTION_BOOKS
from src.store.pit_store import PointInTimeStore

PREREG = Path("docs/preregistration_2025_market_bias.md")
H8_WIND = 10.0  # frozen on 2015-2024 development, see the pre-registration §3
MIN_N = 30
MAX_CLOSE_STALENESS = pd.Timedelta(hours=3)


def check_blind(prereg: Path = PREREG) -> None:
    text = prereg.read_text() if prereg.exists() else ""
    if not re.search(r"^\*\*Status: FINAL", text, flags=re.MULTILINE):
        raise BlindedError(f"{prereg} is not FINAL; 2025 stays sealed until the pre-registration is committed")


def pinnacle_close_bets(schedule: pd.DataFrame, store: PointInTimeStore) -> tuple[pd.DataFrame, dict]:
    """H8's games priced at Pinnacle's closing total (its own line and price),
    plus the best execution-book under quoting that same line. Exclusions counted."""
    s = schedule[(schedule["season"] == HOLDOUT_SEASON) & (schedule["game_type"] == "REG")
                 & schedule["roof"].isin(OUTDOOR_ROOFS) & (schedule["wind"] >= H8_WIND)].copy()
    s["kickoff"] = kickoffs_utc(s)
    excluded = {"no_pinnacle_close": 0, "stale_close": 0}
    rows = []
    for g in s.itertuples():
        snaps = store.read_as_of(g.kickoff.to_pydatetime(), event_id=g.game_id)
        tot = snaps[snaps["market"] == "total"] if not snaps.empty else snaps
        pin = tot[tot["book"] == "pinnacle"] if not tot.empty else tot
        if pin.empty:
            excluded["no_pinnacle_close"] += 1
            continue
        last = pin[pin["capture_time"] == pin["capture_time"].max()]
        if g.kickoff - last["capture_time"].max() > MAX_CLOSE_STALENESS:
            excluded["stale_close"] += 1
            continue
        sides = last.set_index("side")
        if not {"over", "under"} <= set(sides.index) or sides.loc["over", "line"] != sides.loc["under", "line"]:
            excluded["no_pinnacle_close"] += 1
            continue
        line = float(sides.loc["under", "line"])
        d_under, d_over = float(sides.loc["under", "price_decimal"]), float(sides.loc["over", "price_decimal"])
        fair_under = devig_shin((1 / d_under, 1 / d_over)).probabilities[0]

        soft = tot[tot["book"].isin(EXECUTION_BOOKS) & (tot["side"] == "under") & (tot["line"] == line)]
        soft = soft.loc[soft.groupby("book")["capture_time"].idxmax()] if not soft.empty else soft
        rows.append({
            "game_id": g.game_id, "season": g.season, "side": "under", "line": line,
            "price_decimal": d_under, "opposite_price_decimal": d_over, "fair_prob": fair_under,
            "soft_price": float(soft["price_decimal"].max()) if not soft.empty else np.nan,
            "margin": line - (g.home_score + g.away_score),
        })
    return _settle(pd.DataFrame(rows)) if rows else pd.DataFrame(), excluded


def verdict(b: pd.DataFrame, n_resamples: int = 10000, n_null: int = 10000) -> dict:
    graded = b[~b["push"]] if not b.empty else b
    out: dict = {"n": len(graded), "pushes": int(b["push"].sum()) if not b.empty else 0}
    if len(graded) < 2:
        out.update(conditions={"1_n": False}, verdict="FAIL")
        return out
    boot = clustered_bootstrap(graded["ret"], graded["game_id"], n_resamples=n_resamples)
    null = random_bet_benchmark(graded, n_simulations=n_null)
    out.update(roi=boot["mean"], ci_lo=boot["ci_lo"], ci_hi=boot["ci_hi"], p_roi=boot["p_one_sided"],
               null_mean=null["null_mean_roi"], null_p=null["p_one_sided"], hit=float(graded["won"].mean()))
    out["conditions"] = {
        "1_n": len(graded) >= MIN_N,
        "2_roi_positive": boot["mean"] > 0,
        "3_ci_excludes_zero": boot["ci_lo"] > 0,
        "4_beats_random_null": null["p_one_sided"] < ALPHA,
        # Family of one ({H8}): BH at q=0.05 reduces to p < 0.05.
        "5_bh_family": boot["p_one_sided"] < ALPHA,
    }
    out["verdict"] = "PASS" if all(out["conditions"].values()) else "FAIL"
    soft = graded.dropna(subset=["soft_price"])
    if len(soft):
        out["soft_n"] = len(soft)
        out["soft_roi"] = float(np.where(soft["won"], soft["soft_price"] - 1, -1.0).mean())
    return out


def score(store: PointInTimeStore, static_dir: Path = STATIC_DIR, prereg: Path = PREREG) -> dict:
    check_blind(prereg)
    schedule = pd.read_parquet(static_dir / "schedules_2015_2025.parquet")
    b, excluded = pinnacle_close_bets(schedule, store)
    r = verdict(b)
    r["excluded"] = excluded
    nfl = h8_bets(schedule[schedule["season"] == HOLDOUT_SEASON], H8_WIND)
    nfl = nfl[~nfl["push"]]
    r["nflverse_n"], r["nflverse_roi"] = len(nfl), (float(nfl["ret"].mean()) if len(nfl) else None)
    return r


def format_result(r: dict) -> str:
    title = (f"PRE-REGISTERED SCORING  H8 wind >= {H8_WIND:g} mph unders  season {HOLDOUT_SEASON}  "
             "(preregistration_2025_market_bias.md)")
    lines = [title, "", f"H8: {r['verdict']}   excluded {r.get('excluded')}"]
    if "roi" in r:
        pin = (f"  Pinnacle close: n={r['n']} (+{r['pushes']} pushes)  ROI {r['roi']:+.2%} "
               f"[{r['ci_lo']:+.2%}, {r['ci_hi']:+.2%}] p={r['p_roi']:.4f}  hit {r['hit']:.3f}")
        lines += [pin, f"  random-side null {r['null_mean']:+.2%}  p={r['null_p']:.4f}"]
    lines += [f"    [{'x' if ok else ' '}] {name}" for name, ok in r["conditions"].items()]
    if "soft_roi" in r:
        lines.append(f"  reported only: best execution book at Pinnacle's line  ROI {r['soft_roi']:+.2%} (n={r['soft_n']})")
    if r.get("nflverse_roi") is not None:
        lines.append(f"  reported only: nflverse line  ROI {r['nflverse_roi']:+.2%} (n={r['nflverse_n']})")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> None:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    try:
        r = score(PointInTimeStore())
    except BlindedError as exc:
        raise SystemExit(f"BLINDED: {exc}") from None
    print(format_result(r))


if __name__ == "__main__":
    main()
