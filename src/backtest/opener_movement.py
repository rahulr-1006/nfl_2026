"""H6: when our Elo model disagrees with Pinnacle's early moneyline, does the
close move toward the model?

**Why this exists.** Every model here loses to Pinnacle's *close*. That says
nothing about the *early* line: Pinnacle opens at low limits and lets sharp money
correct it, so the gap between early and close is where new information enters
the price (Costa 2025, Claremont thesis: NFL moneyline movement in the week
before kickoff is predictable). Phase 3 couldn't ask this because the historical
store had no early prices (`src/model/closing_line.py`). Two samples have them
now: 105 games of 2024 with a Pinnacle quote at T-120h, and the live 2026 store.

**The anchor is fixed, not "the opener".** `t_early` = kickoff - 120h for every
game. The 2024 series was bought at exactly T-120h and the 2026 collector first
sees lines ~6.7 days out, so 120h is the one point both samples share. A quote
older than `MAX_EARLY_STALENESS` at `t_early` doesn't count as an early price.

**What is measured.** `clv_move` prices both ends at Pinnacle's no-vig fair
probability: did the side the model liked get more likely by the close? It is
the research question, not a bettable return -- nobody in the US can bet
Pinnacle. `soft_close_ev` is the bettable version: the best execution-book price
on the model's side at `t_early`, valued at Pinnacle's fair close.

**Leakage discipline.**
- Every price comes from `PointInTimeStore.read_as_of(kickoff)` then
  `engine.latest_fair_prob(as_of=t)`, so no snapshot after `t` can be used.
- Elo is `elo.team_elo_as_of(t_early)`: results of games still in progress or
  unplayed at `t_early` are excluded (the Monday-night -> next week's lookahead
  line case).
- The Platt calibration is fit on 2015-2022 outcomes only; both samples are
  2024 or later. Elo's K / home edge / reversion are the module defaults, never
  tuned on these samples.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from src.backtest.engine import latest_fair_prob
from src.clv.metrics import clustered_bootstrap
from src.model.elo import (
    DEFAULT_HOME_FIELD_ADVANTAGE,
    canonical_team,
    compute_team_elo_ratings,
    elo_win_probability,
    team_elo_as_of,
)
from src.signal.live_scan import EXECUTION_BOOKS
from src.store.pit_store import PointInTimeStore
from src.store.schema import Market, Side

EARLY_LEAD = pd.Timedelta(hours=120)
# The early quote must be this fresh at t_early. A 2026 line first seen 7 days
# out and never re-polled would otherwise stand in for a 5-day price.
MAX_EARLY_STALENESS = pd.Timedelta(hours=24)
# The close must be this close to kickoff. 2024's historical closes are
# 0.24-0.66h out and the live collector polls every 30 min inside 48h.
MAX_CLOSE_STALENESS = pd.Timedelta(hours=3)
CALIBRATION_SEASONS = tuple(range(2015, 2023))
TAU_GRID = (0.02, 0.03, 0.05)
DEVIG = "shin"


def fit_elo_calibration(schedule: pd.DataFrame, ratings: pd.DataFrame,
                        seasons: Sequence[int] = CALIBRATION_SEASONS) -> LogisticRegression:
    """Platt scaling of raw Elo home-win probability on `seasons`' outcomes.

    Raw Elo probabilities are not guaranteed calibrated, and calibration is what
    a betting decision consumes (Walsh & Joshi 2024). Ties are dropped: they are
    neither a home win nor a loss.
    """
    frame = _historical_elo_frame(schedule, ratings)
    frame = frame[frame["season"].isin(seasons) & (frame["home_score"] != frame["away_score"])]
    x = _logit(frame["p_elo_raw"].to_numpy()).reshape(-1, 1)
    y = (frame["home_score"] > frame["away_score"]).astype(int).to_numpy()
    return LogisticRegression(C=1e6).fit(x, y)


def calibrated(model: LogisticRegression, p_raw: Iterable[float]) -> np.ndarray:
    x = _logit(np.asarray(list(p_raw), dtype=float)).reshape(-1, 1)
    return model.predict_proba(x)[:, 1]


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def _historical_elo_frame(schedule: pd.DataFrame, ratings: pd.DataFrame) -> pd.DataFrame:
    """Plain pre-game Elo probability for completed games (calibration and the
    reliability check only -- H6 itself uses the as-of rating)."""
    f = ratings.merge(schedule[["game_id", "home_score", "away_score"]], on="game_id", how="left")
    f["p_elo_raw"] = [
        elo_win_probability(h, a, DEFAULT_HOME_FIELD_ADVANTAGE)
        for h, a in zip(f["home_pre_elo"], f["away_pre_elo"], strict=True)
    ]
    return f


def reliability_table(schedule: pd.DataFrame, ratings: pd.DataFrame, model: LogisticRegression,
                      season: int, n_bins: int = 5) -> pd.DataFrame:
    """Calibrated Elo vs realized home-win rate on one out-of-calibration season."""
    f = _historical_elo_frame(schedule, ratings)
    f = f[(f["season"] == season) & (f["home_score"] != f["away_score"])].copy()
    f["p"] = calibrated(model, f["p_elo_raw"])
    f["won"] = (f["home_score"] > f["away_score"]).astype(float)
    f["bin"] = pd.qcut(f["p"], n_bins, duplicates="drop")
    return f.groupby("bin", observed=True).agg(n=("won", "size"), mean_p=("p", "mean"), hit=("won", "mean"))


def build_frame(store: PointInTimeStore, schedule: pd.DataFrame, kickoffs: pd.Series,
                event_ids: Sequence[str], calibration: LogisticRegression,
                ratings: pd.DataFrame | None = None, now: datetime | None = None) -> tuple[pd.DataFrame, dict]:
    """One row per game with an early and a closing Pinnacle price.

    `schedule` must contain every season from the Elo burn-in through the games
    scored; only completed rows feed the ratings. `kickoffs` maps game_id ->
    UTC kickoff for the whole schedule. Games whose kickoff is after `now` are
    skipped (no close yet). Returns the frame and a count of exclusions by reason,
    so a shrinking sample is visible rather than silent.
    """
    if ratings is None:
        ratings = compute_team_elo_ratings(schedule)
    now_ts = pd.Timestamp(now) if now is not None else pd.Timestamp.now(tz="UTC")
    sched = schedule.set_index("game_id")
    excluded = {"not_in_schedule": 0, "not_kicked_off": 0, "no_early_price": 0, "stale_early_price": 0,
                "no_close_price": 0, "stale_close_price": 0}
    rows = []
    for event_id in event_ids:
        if event_id not in sched.index:
            excluded["not_in_schedule"] += 1
            continue
        ko = kickoffs[event_id]
        if ko > now_ts:
            excluded["not_kicked_off"] += 1
            continue
        t_early = ko - EARLY_LEAD
        snaps = store.read_as_of(ko.to_pydatetime(), event_id=event_id)
        pin = _pinnacle_moneyline(snaps)

        early_time = _latest_two_sided_time(pin, t_early)
        if early_time is None:
            excluded["no_early_price"] += 1
            continue
        if t_early - early_time > MAX_EARLY_STALENESS:
            excluded["stale_early_price"] += 1
            continue
        close_time = _latest_two_sided_time(pin, ko)
        if close_time is None:
            excluded["no_close_price"] += 1
            continue
        if ko - close_time > MAX_CLOSE_STALENESS:
            excluded["stale_close_price"] += 1
            continue

        p_early = latest_fair_prob(snaps, "pinnacle", Market.MONEYLINE, Side.HOME, t_early.to_pydatetime(),
                                   DEVIG, event_id=event_id)
        p_close = latest_fair_prob(snaps, "pinnacle", Market.MONEYLINE, Side.HOME, ko.to_pydatetime(),
                                   DEVIG, event_id=event_id)
        if p_early is None or p_close is None:  # duplicate rows at the latest capture
            excluded["no_early_price" if p_early is None else "no_close_price"] += 1
            continue

        game = sched.loc[event_id]
        season = int(game["season"])
        home, away = canonical_team(game["home_team"]), canonical_team(game["away_team"])
        elo_home = team_elo_as_of(ratings, kickoffs, home, t_early, season, ko)
        elo_away = team_elo_as_of(ratings, kickoffs, away, t_early, season, ko)
        p_raw = elo_win_probability(elo_home, elo_away, DEFAULT_HOME_FIELD_ADVANTAGE)

        rows.append({
            "event_id": event_id, "season": season, "week": int(game["week"]), "kickoff": ko,
            "t_early": t_early, "early_capture": early_time, "close_capture": close_time,
            "p_early": p_early, "p_close": p_close, "p_elo_raw": p_raw,
            "home_score": game["home_score"], "away_score": game["away_score"],
            "best_home_price": _best_soft_price(snaps, Side.HOME, t_early),
            "best_away_price": _best_soft_price(snaps, Side.AWAY, t_early),
        })
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame["p_model"] = calibrated(calibration, frame["p_elo_raw"])
        frame["d"] = frame["p_model"] - frame["p_early"]
        frame["m"] = frame["p_close"] - frame["p_early"]
    return frame, excluded


def _pinnacle_moneyline(snaps: pd.DataFrame) -> pd.DataFrame:
    if snaps.empty:
        return snaps
    return snaps[(snaps["book"] == "pinnacle") & (snaps["market"] == Market.MONEYLINE.value)]


def _latest_two_sided_time(pin: pd.DataFrame, as_of: pd.Timestamp) -> pd.Timestamp | None:
    """Latest capture at or before `as_of` that quotes both sides."""
    if pin.empty:
        return None
    seen = pin[pin["capture_time"] <= as_of]
    sides = seen.groupby("capture_time")["side"].nunique()
    both = sides[sides == 2]
    return None if both.empty else both.index.max()


def _best_soft_price(snaps: pd.DataFrame, side: Side, as_of: pd.Timestamp) -> float:
    """Best decimal price on `side` across execution books, each book's latest
    quote within MAX_EARLY_STALENESS of `as_of`. NaN if none quoted."""
    if snaps.empty:
        return float("nan")
    s = snaps[(snaps["market"] == Market.MONEYLINE.value) & (snaps["side"] == side.value)
              & snaps["book"].isin(EXECUTION_BOOKS) & (snaps["capture_time"] <= as_of)
              & (snaps["capture_time"] >= as_of - MAX_EARLY_STALENESS)]
    if s.empty:
        return float("nan")
    latest = s.loc[s.groupby("book")["capture_time"].idxmax()]
    return float(latest["price_decimal"].max())


def bets(frame: pd.DataFrame, tau: float) -> pd.DataFrame:
    """One bet per game where |d| >= tau, on the side the model prefers.

    `clv_move`: Pinnacle fair probability of that side at the close over the
    early one, minus 1 -- positive when the market moved toward the model.
    `soft_close_ev`: best execution-book price at t_early times Pinnacle's fair
    close, minus 1 (NaN where no execution book quoted). `realized`: return of a
    1-unit bet at that soft price (0 on a tie, NaN without a price or a result).
    """
    b = frame[frame["d"].abs() >= tau].copy()
    if b.empty:
        return b
    home = b["d"] > 0
    b["side"] = np.where(home, "home", "away")
    b["p_early_side"] = np.where(home, b["p_early"], 1 - b["p_early"])
    b["p_close_side"] = np.where(home, b["p_close"], 1 - b["p_close"])
    b["clv_move"] = b["p_close_side"] / b["p_early_side"] - 1
    b["price"] = np.where(home, b["best_home_price"], b["best_away_price"])
    b["soft_close_ev"] = b["p_close_side"] * b["price"] - 1

    margin = b["home_score"] - b["away_score"]
    side_margin = np.where(home, margin, -margin)
    won = np.where(side_margin > 0, b["price"] - 1, np.where(side_margin < 0, -1.0, 0.0))
    b["realized"] = np.where(b["price"].notna() & margin.notna(), won, np.nan)
    return b


def summarize(frame: pd.DataFrame, taus: Sequence[float] = TAU_GRID, n_resamples: int = 10000) -> dict:
    """Per-tau bet statistics plus the movement slope and the momentum diagnostic."""
    out = {"games": len(frame), "slope": movement_slope(frame, n_resamples),
           "momentum": momentum_diagnostic(frame, n_resamples), "by_tau": {}}
    for tau in taus:
        b = bets(frame, tau)
        r = {"n": len(b)}
        if len(b) >= 2:
            boot = clustered_bootstrap(b["clv_move"], b["event_id"], n_resamples=n_resamples)
            r.update(clv_move=boot["mean"], ci_lo=boot["ci_lo"], ci_hi=boot["ci_hi"], p=boot["p_one_sided"])
            ev = b.dropna(subset=["soft_close_ev"])
            r["soft_n"] = len(ev)
            r["soft_close_ev"] = float(ev["soft_close_ev"].mean()) if len(ev) else None
            real = b["realized"].dropna()
            r["realized_n"] = len(real)
            r["realized_roi"] = float(real.mean()) if len(real) else None
        out["by_tau"][tau] = r
    return out


def movement_slope(frame: pd.DataFrame, n_resamples: int = 10000, seed: int = 0) -> dict:
    """OLS slope of m on d (no intercept): the share of the model's disagreement
    the market closes. Game-level bootstrap CI. Diagnostic, not the gate."""
    if len(frame) < 3:
        return {"beta": None}
    d, m = frame["d"].to_numpy(), frame["m"].to_numpy()
    beta = float((d @ m) / (d @ d))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(n_resamples, len(d)))
    dd, mm = d[idx], m[idx]
    betas = (dd * mm).sum(axis=1) / (dd * dd).sum(axis=1)
    return {"beta": beta, "ci_lo": float(np.percentile(betas, 2.5)), "ci_hi": float(np.percentile(betas, 97.5))}


def momentum_diagnostic(frame: pd.DataFrame, n_resamples: int = 10000, seed: int = 0) -> dict:
    """Moskowitz (2021): does early->close movement predict the outcome BEYOND
    the close? Slope of (home_win - p_close) on m. Zero if the close is efficient;
    positive = under-reaction (momentum), negative = over-reaction. Exploratory."""
    f = frame.dropna(subset=["home_score", "away_score"])
    f = f[f["home_score"] != f["away_score"]]
    if len(f) < 3:
        return {"slope": None}
    resid = (f["home_score"] > f["away_score"]).astype(float).to_numpy() - f["p_close"].to_numpy()
    m = f["m"].to_numpy() - f["m"].mean()
    slope = float((m @ resid) / (m @ m))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(m), size=(n_resamples, len(m)))
    mm, rr = m[idx], resid[idx]
    mm = mm - mm.mean(axis=1, keepdims=True)
    slopes = (mm * rr).sum(axis=1) / (mm * mm).sum(axis=1)
    return {"slope": slope, "ci_lo": float(np.percentile(slopes, 2.5)), "ci_hi": float(np.percentile(slopes, 97.5)),
            "n": len(f)}
