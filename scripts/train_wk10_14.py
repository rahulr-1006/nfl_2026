"""Train-phase re-run for the Weeks 10-14 pre-registration.

Every live strategy, re-scored on all 2026 data played so far with the
pre-registration's yardstick (closing EV against Pinnacle's close, game-clustered
CI, random-side null, survival), so the Weeks 10-14 rules can be frozen on
current numbers instead of the 10-04 Train run.

The split this script sits in:

    fit / calibrate   2023-24 history -- calibration gates in
                      analysis/train_results_2026-10-04.md (not re-run here)
    train             2026 Weeks 1..last completed (this script)
    test              2026 Weeks 10-14, pre-registered before 2026-11-12
    untouched         2025 season

**Sealed:** player-prop legs in Weeks 5-9 are the H1/H1b holdout until
2026-11-10 (preregistration_wk5-9.md). `prop_ev`, `prop_arb` and every other
prop leg in those weeks are dropped *before pricing*, so no closing-EV number is
ever computed from them -- a filtered report would still mean the number existed
and was looked at. Mainline strategies (moneyline, spread, total) are not part of
that holdout and are scored on every week.

    .venv/bin/python -m scripts.train_wk10_14
"""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pandas as pd

from src.backtest.clv_portfolio import bets_to_frame
from src.backtest.correlated_props import bucket_favorite_strength
from src.backtest.team_total_props import (
    build_team_outcomes,
    build_team_total_lines,
    team_total_over_indicator,
)
from src.clv.decision_report import first_recheck_frame, structural_capture
from src.clv.metrics import clustered_bootstrap
from src.clv.prereg_score import (
    BAD_QUOTE_EV,
    HOLDOUT_WEEKS,
    SCORE_NOT_BEFORE,
    _fmt,
    score_strategy,
    week_of,
)
from src.clv.shadow_clv import shadow_alerts_as_bets
from src.features.load_static import STATIC_DIR
from src.model.baseline import market_baseline
from src.signal.live_scan import DEFAULT_EDGE_THRESHOLD, EXECUTION_BOOKS
from src.signal.shadow_log import SHADOW_LOG_PATH
from src.signal.team_total_scan import VALIDATED_TEAM_TOTAL_LIFT
from src.store.bet_log import settle_bets, to_backtest_bets
from src.store.pit_store import PointInTimeStore, kickoffs_from_store

FIRST_TRAIN_WEEKS = (1, 2, 3, 4)  # what the 10-04 run saw; everything later is new
# Pinnacle's 2023-24 moneyline close overrated short underdogs (fair .333-.5,
# decimal ~2.0-3.0) by ~6pp, so closing EV is not a valid yardstick there.
ML_BANDS = (("favourite (<2.0)", 0.0, 2.0), ("short dog (2.0-3.0, gate FAIL)", 2.0, 3.0),
            ("longshot (>3.0)", 3.0, float("inf")))
HISTORY_SEASONS = ("2023", "2024")  # 2025 is the untouched holdout; never read its odds here
KEY = ["event_id", "decision_time", "strategy", "market", "side", "line", "book", "player_name", "prop_stat"]


def sealed(event_id: str, market: str, now: datetime) -> bool:
    return market == "player_prop" and week_of(event_id) in HOLDOUT_WEEKS and now < SCORE_NOT_BEFORE


def build_frame(store: PointInTimeStore, now: datetime) -> tuple[pd.DataFrame, int]:
    logged = shadow_alerts_as_bets(SHADOW_LOG_PATH)
    kept = [b for b in logged if not sealed(b.event_id, b.market.value, now)]
    n_sealed = len(logged) - len(kept)

    priced = to_backtest_bets(kept, store, as_of=now)
    keys = bets_to_frame(priced).assign(alert_key=[b.alert_key for b in kept])[KEY + ["alert_key"]]
    schedule = pd.read_parquet(STATIC_DIR / "schedules_2026_2026.parquet")
    stats = pd.read_parquet(STATIC_DIR / "player_stats_2026_2026.parquet")
    frame = bets_to_frame(settle_bets(priced, schedule, kickoffs_from_store(store, now), player_stats=stats))
    frame = frame.merge(keys.drop_duplicates(KEY), on=KEY, how="left", validate="many_to_one")

    frame["week"] = frame["event_id"].map(week_of)
    frame["close_ev"] = frame["close_prob_fair"] * frame["price_decimal"] - 1
    frame["entry_ev"] = frame["entry_prob_fair"] * frame["price_decimal"] - 1
    # No same-book opposite quote is looked up for mainlines: the null falls back
    # to the no-vig fair price on the other side, which is the harder null.
    frame["opposite_price_decimal"] = float("nan")
    assert not frame.apply(lambda r: sealed(r["event_id"], r["market"], now), axis=1).any()
    return frame, n_sealed


def line(label: str, r: dict) -> str:
    if not r.get("n"):
        return f"  {label:<34} n=0"
    c = r["conditions"]
    marks = "".join("x" if c[k] else "." for k in sorted(c))
    return (f"  {label:<34} n={r['n']:<4} games={r['games']:<3} close EV {_fmt(r['mean_close_ev'], True):>7} "
            f"[{_fmt(r['ci_lo'], True)}, {_fmt(r['ci_hi'], True)}]  realized {_fmt(r['realized_roi'], True):>8} "
            f"on {r['n_settled']:<4} null p={_fmt(r['null_p'])}  surv {_fmt(r['survival'], True)}  [{marks}]")


def by_period(frame: pd.DataFrame, legs: pd.DataFrame, strategy: str, label: str, mask=None) -> list[str]:
    f = frame if mask is None else frame[mask]
    out = []
    for name, weeks in (("all weeks", None), ("Weeks 1-4", FIRST_TRAIN_WEEKS), ("Weeks 5+ (new)", "new")):
        if weeks is None:
            sub, lg = f, legs
        else:
            pick = f["week"].isin(FIRST_TRAIN_WEEKS) if weeks != "new" else ~f["week"].isin(FIRST_TRAIN_WEEKS)
            sub = f[pick]
            lg = legs[legs["week"].isin(FIRST_TRAIN_WEEKS) == (weeks != "new")]
        if sub.empty:
            continue
        out.append(line(f"{label} | {name}", score_strategy(sub, strategy, lg)))
    return out


def middle_pairs(frame: pd.DataFrame) -> str:
    """A middle is a two-leg position: score the pair, not each leg."""
    m = frame[(frame["strategy"] == "middle") & frame["won"].notna() & frame["alert_key"].notna()]
    pnl = m.assign(ret=lambda d: d["won"].astype(bool) * (d["price_decimal"]) - 1).groupby("alert_key")
    pairs = pnl.agg(legs=("ret", "size"), ret=("ret", "sum"), wins=("won", "sum"))
    pairs = pairs[pairs["legs"] == 2]
    if pairs.empty:
        return "  middle pairs: none settled"
    return (f"  middle pairs settled: {len(pairs)}  both legs won (middle hit): {(pairs['wins'] == 2).mean():.1%}  "
            f"one leg won: {(pairs['wins'] == 1).mean():.1%}  mean pair P&L per 2 units: {pairs['ret'].mean():+.3f}")


def historical_moneyline(store: PointInTimeStore, threshold: float = DEFAULT_EDGE_THRESHOLD) -> list[str]:
    """`moneyline_ev`'s rule on 2023-24, scored on realized results.

    History has one pre-kickoff snapshot per game (~20 min out), so there is no
    entry-vs-close here: the snapshot is effectively the close, and the question
    is whether "execution book beats Pinnacle's fair by >= threshold" turns into
    money. One bet per game-side at the best qualifying book, as a person would
    place it.
    """
    df = store.read_as_of(datetime.now(UTC))
    ml = df[(df["market"] == "moneyline") & df["event_id"].str[:4].isin(HISTORY_SEASONS)]
    ml = ml[ml["capture_time"] < ml["event_start_time"]]
    pin = ml[ml["book"] == "pinnacle"].pivot_table(index="event_id", columns="side", values="price_american",
                                                   aggfunc="last").dropna()
    fair = pd.DataFrame({
        "home": [market_baseline([int(h), int(a)], 0) for h, a in zip(pin["home"], pin["away"], strict=True)],
        "away": [market_baseline([int(h), int(a)], 1) for h, a in zip(pin["home"], pin["away"], strict=True)],
    }, index=pin.index).stack().rename("fair").reset_index().rename(columns={"level_1": "side"})

    soft = ml[ml["book"].isin(EXECUTION_BOOKS)].sort_values("capture_time")
    soft = soft.groupby(["event_id", "side", "book"], as_index=False).last()
    bets = soft.merge(fair, on=["event_id", "side"]).assign(ev=lambda d: d["fair"] * d["price_decimal"] - 1)
    bets = bets[bets["ev"].between(threshold, BAD_QUOTE_EV)]
    bets = bets.sort_values("price_decimal").groupby(["event_id", "side"], as_index=False).last()

    sched = pd.read_parquet(STATIC_DIR / "schedules_2015_2025.parquet")
    sched = sched[sched["season"].astype(str).isin(HISTORY_SEASONS) & sched["home_score"].notna()]
    winner = pd.Series(
        ["home" if h > a else "away" if a > h else "tie" for h, a in zip(sched["home_score"], sched["away_score"], strict=True)],
        index=sched["game_id"])
    bets["result"] = bets["event_id"].map(winner)
    unmatched = int(bets["result"].isna().sum())
    bets = bets[bets["result"].isin(["home", "away"])]
    bets["ret"] = (bets["result"] == bets["side"]) * bets["price_decimal"] - 1

    out = [f"history 2023-24 ({len(fair) // 2} games with a Pinnacle quote; {unmatched} bets unmatched to a result)"]
    for band, lo, hi in ML_BANDS:
        b = bets[bets["price_decimal"].between(lo, hi, inclusive="left")]
        if len(b) < 2 or b["event_id"].nunique() < 2:
            out.append(f"  {band:<34} n={len(b)}")
            continue
        boot = clustered_bootstrap(b["ret"], b["event_id"], n_resamples=10_000, random_state=0)
        out.append(f"  {band:<34} n={len(b):<4} games={b['event_id'].nunique():<4} mean entry EV {b['ev'].mean():+.2%}  "
                   f"realized ROI {b['ret'].mean():+.2%} [{boot['ci_lo']:+.2%}, {boot['ci_hi']:+.2%}]  "
                   f"win {(b['ret'] > 0).mean():.1%} vs fair {b['fair'].mean():.1%}")
    return out


def _lift(won: np.ndarray, over: np.ndarray, idx: np.ndarray) -> float:
    pa, pb = won[idx].mean(), over[idx].mean()
    return (won[idx] & over[idx]).mean() / (pa * pb) if pa * pb > 0 else np.nan


def team_total_lift(store: PointInTimeStore, now: datetime, n_boot: int = 10_000) -> list[str]:
    """H2's mechanism on 2026: does an underdog that wins also clear its summed
    Pinnacle prop line more often than independence predicts? Built from prop
    lines, so it is limited to unsealed weeks (1-4) like every other prop number.
    Lift CI resamples games (one underdog per game, so team-games are independent)."""
    df = store.read_as_of(now)
    weeks_1_4 = df["event_id"].str.startswith("2026_") & df["event_id"].map(week_of).isin(FIRST_TRAIN_WEEKS)
    d = df[weeks_1_4 & (df["capture_time"] < df["event_start_time"])]
    schedule = pd.read_parquet(STATIC_DIR / "schedules_2026_2026.parquet")
    stats = pd.read_parquet(STATIC_DIR / "player_stats_2026_2026.parquet")
    outcomes = build_team_outcomes(d, schedule)
    rng = np.random.default_rng(0)
    out = ["team-total lift, 2026 Weeks 1-4 (H2 mechanism; 2024 value is what live pricing uses)"]
    for stat in ("passing_yards", "rushing_yards"):
        t = build_team_total_lines(d, stats, stat)
        t = t.assign(over=team_total_over_indicator(t).to_numpy()).merge(outcomes, on=["event_id", "team"])
        t["bucket"] = t["team_market_prob"].map(bucket_favorite_strength)
        dog = t[t["bucket"] == "underdog"].reset_index(drop=True)
        if len(dog) < 10:
            out.append(f"  {stat:<14} underdog n={len(dog)} (too few)")
            continue
        w, o = dog["team_won"].to_numpy().astype(bool), dog["over"].to_numpy().astype(bool)

        boots = np.array([_lift(w, o, rng.integers(0, len(dog), len(dog))) for _ in range(n_boot)])
        lo, hi = np.nanpercentile(boots, [2.5, 97.5])
        out.append(f"  {stat:<14} underdog n={len(dog):<3} won {w.mean():.1%}  cleared line {o.mean():.1%}  "
                   f"lift {_lift(w, o, np.arange(len(dog))):.3f} [{lo:.3f}, {hi:.3f}]  vs 2024 "
                   f"{VALIDATED_TEAM_TOTAL_LIFT[stat]['underdog']:.3f}")
    return out


def main() -> None:
    now = datetime.now(UTC)
    store = PointInTimeStore()
    frame, n_sealed = build_frame(store, now)
    legs = first_recheck_frame(SHADOW_LOG_PATH)
    # moneyline_ev keys start with the game_id; every other strategy prefixes a tag
    legs["event_id"] = legs["alert_key"].str.extract(r"(?:^|\|)(\d{4}_\d{2}_[A-Z]+_[A-Z]+)", expand=False)
    legs["week"] = legs["event_id"].map(week_of)
    legs["market"] = legs["strategy"].map(lambda s: "player_prop" if s.startswith("prop") else "mainline")
    legs = legs[~legs.apply(lambda r: sealed(r["event_id"], r["market"], now), axis=1)]

    done = frame[frame["close_ev"].notna()]
    print(f"TRAIN RE-RUN for Weeks 10-14  as of {now:%Y-%m-%d %H:%M} UTC")
    print(f"weeks with closed games: {sorted(int(w) for w in done['week'].unique())}   "
          f"sealed prop legs dropped before pricing: {n_sealed}")
    print(f"bad quotes (entry EV > {BAD_QUOTE_EV:.0%}) and rushing yards excluded from close EV, as in §3.")
    print("conditions [1 n/games, 2 mean>0, 3 CI>0, 4 null, 5 survival]\n")

    for strategy in ("moneyline_ev", "steam", "middle"):
        print(strategy)
        print("\n".join(by_period(frame, legs, strategy, "all")))
        if strategy == "moneyline_ev":
            for band, lo, hi in ML_BANDS:
                mask = frame["price_decimal"].between(lo, hi, inclusive="left")
                print("\n".join(by_period(frame, legs, strategy, band, mask)))
        if strategy in ("steam", "middle"):
            for mkt in ("spread", "total"):
                print("\n".join(by_period(frame, legs, strategy, mkt, frame["market"] == mkt)))
        if strategy == "middle":
            print(middle_pairs(frame))
        print()

    print("prop_ev  (Weeks 1-4 only; 5-9 sealed)")
    print("\n".join(by_period(frame, legs, "prop_ev", "all")))
    print("\nmoneyline_ev rule on history (realized ROI)")
    print("\n".join(historical_moneyline(store)))
    print()
    print("\n".join(team_total_lift(store, now)))
    print("\nprop_arb  (Weeks 1-4; capturability at first re-check <=40 min, not per-leg CLV)")
    cap = structural_capture(legs[legs["week"].isin(FIRST_TRAIN_WEEKS)], "prop_arb")
    print(f"  alerts={cap['n_alerts']}  both legs {_fmt(cap['both_legs_rate'], True)}  "
          f"one leg only {_fmt(cap['one_leg_only_rate'], True)}  expected capture "
          f"{_fmt(cap['expected_capture'], True)} (upper bound)")


if __name__ == "__main__":
    main()
