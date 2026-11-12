"""H7 / H8: two structural market-bias rules from the literature, tested on
nflverse's bundled closing lines.

- **H7, home overvaluation in close games** (Costa 2025, Claremont thesis): bet
  the AWAY side when the market's home win probability is in [0.30, 0.70]. The
  thesis gated on a model forecast; this uses the market's own devigged
  probability, so the rule has no fitted parts.
- **H8, wind unders** (Borghesi 2008, *Applied Financial Economics*): in
  outdoor / open-roof games with wind >= W mph, bet the under against the closing
  total.

**Not the same as this repo's earlier weather test.** That one added wind as a
FEATURE to an outcome model and scored Brier against the market. These test the
market LINE directly at its real price: is the under at the listed odds a
positive-return bet when it's windy?

**Data caveats, stated up front.**
- nflverse's moneyline / total / odds columns are a closing consensus of
  unconfirmed source (`src/collect/mainline_historical.py`), not Pinnacle.
- `wind` is the observed game-day reading, not the forecast a bettor had. The
  close is set at kickoff, when the forecast is close to the reading, so the
  look-ahead is small but not zero.
- Pushes (ML tie, total landing on the line) are refunds: they are counted and
  dropped from ROI and from the null, which treats every bet as win/lose.

Regular season only: the playoffs' 13 games a year carry different limits and
public attention, and the 2025 holdout count was planned on the regular season.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from src.backtest.evaluation import random_bet_benchmark
from src.clv.metrics import clustered_bootstrap
from src.devig.convert import american_to_decimal
from src.devig.methods import devig_shin

H7_BAND = (0.30, 0.70)
H8_WIND_GRID = (10.0, 15.0)
OUTDOOR_ROOFS = ("outdoors", "open")
DEV_SEASONS = tuple(range(2015, 2025))
HOLDOUT_SEASON = 2025


def _two_sided(price_a: pd.Series, price_b: pd.Series) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Decimal prices of both sides and Shin-fair probability of side a."""
    da = price_a.map(lambda x: american_to_decimal(int(x))).to_numpy(dtype=float)
    db = price_b.map(lambda x: american_to_decimal(int(x))).to_numpy(dtype=float)
    fair_a = np.array([devig_shin((1 / a, 1 / b)).probabilities[0] for a, b in zip(da, db, strict=True)])
    return da, db, fair_a


def h7_bets(schedule: pd.DataFrame, band: tuple[float, float] = H7_BAND) -> pd.DataFrame:
    """Away-side bets in close games. One row per qualifying game."""
    s = schedule[(schedule["game_type"] == "REG")].dropna(
        subset=["home_moneyline", "away_moneyline", "home_score", "away_score"]).copy()
    d_away, d_home, fair_away = _two_sided(s["away_moneyline"], s["home_moneyline"])
    s["p_home"] = 1 - fair_away
    keep = (s["p_home"] >= band[0]) & (s["p_home"] <= band[1])
    out = pd.DataFrame({
        "game_id": s["game_id"], "season": s["season"], "side": "away",
        "price_decimal": d_away, "opposite_price_decimal": d_home, "fair_prob": fair_away,
        "margin": s["away_score"] - s["home_score"],
    })[keep.to_numpy()]
    return _settle(out)


def h8_bets(schedule: pd.DataFrame, min_wind: float) -> pd.DataFrame:
    """Under bets in windy outdoor games. One row per qualifying game."""
    s = schedule[(schedule["game_type"] == "REG") & schedule["roof"].isin(OUTDOOR_ROOFS)].dropna(
        subset=["wind", "total_line", "under_odds", "over_odds", "home_score", "away_score"]).copy()
    s = s[s["wind"] >= min_wind]
    d_under, d_over, fair_under = _two_sided(s["under_odds"], s["over_odds"])
    out = pd.DataFrame({
        "game_id": s["game_id"], "season": s["season"], "side": "under",
        "price_decimal": d_under, "opposite_price_decimal": d_over, "fair_prob": fair_under,
        "margin": s["total_line"] - (s["home_score"] + s["away_score"]),
    })
    return _settle(out)


def _settle(bets: pd.DataFrame) -> pd.DataFrame:
    """`margin` > 0 wins, < 0 loses, == 0 pushes (kept, flagged, return 0)."""
    b = bets.reset_index(drop=True)
    b["push"] = b["margin"] == 0
    b["won"] = b["margin"] > 0
    b["ret"] = np.where(b["push"], 0.0, np.where(b["won"], b["price_decimal"] - 1, -1.0))
    return b


def evaluate(bets: pd.DataFrame, n_resamples: int = 10000, n_null: int = 2000) -> dict:
    """Pooled ROI (game bootstrap), random-side null, and the per-season table
    the stability rule reads. Pushes excluded from ROI and null, and counted."""
    graded = bets[~bets["push"]]
    out = {"n": len(graded), "pushes": int(bets["push"].sum())}
    if len(graded) < 2:
        return out
    boot = clustered_bootstrap(graded["ret"], graded["game_id"], n_resamples=n_resamples)
    null = random_bet_benchmark(graded, n_simulations=n_null)
    out.update(roi=boot["mean"], ci_lo=boot["ci_lo"], ci_hi=boot["ci_hi"], p_roi=boot["p_one_sided"],
               null_mean=null["null_mean_roi"], null_p=null["p_one_sided"],
               hit=float(graded["won"].mean()), mean_fair=float(graded["fair_prob"].mean()))
    by = graded.groupby("season")["ret"].agg(["size", "mean"]).rename(columns={"size": "n", "mean": "roi"})
    out["by_season"] = by
    out["seasons_positive"] = int((by["roi"] > 0).sum())
    out["seasons"] = len(by)
    return out


def passes_stability(result: dict, min_positive: int = 6) -> bool:
    """Development gate before 2025 is spent: pooled ROI > 0 and at least
    `min_positive` of the development seasons positive (Winkelmann et al. 2024:
    single-season effects appear even in an efficient market)."""
    return bool(result.get("roi") is not None and result["roi"] > 0
                and result.get("seasons_positive", 0) >= min_positive)


def seasons(schedule: pd.DataFrame, which: Sequence[int]) -> pd.DataFrame:
    return schedule[schedule["season"].isin(which)]
