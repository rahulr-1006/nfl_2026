"""Team-total rushing/passing yards vs. moneyline correlation
(methodology_backlog.md #9).

**The question:** does a team's real *market-implied* total rushing/passing
output correlate with its real *market-implied* win probability beyond what
independent pricing predicts? If the books aren't jointly calibrating these,
that's a real mispricing mechanism -- the same underlying hypothesis
`correlated_props.py` already tests for fixed-threshold legs (100+ rush
yards, 2+ pass TDs), extended to real market-implied legs now that real
per-player Pinnacle prop lines exist for the full 2023-2024 test set
(`src/collect/mainline_historical.py`, `src/collect/props_historical.py`).

**Why this isn't a fixed-threshold leg like the rest of `correlated_props.py`:**
"team total rushing/passing yards" isn't a market Odds API posts directly --
there's no single quoted line to devig. And real per-player lines almost
never sit exactly at correlated_props.py's fixed 100/75-yard thresholds,
since props post for every roster player, not just the leading one. Design
decisions locked 2026-08-22 (methodology_backlog.md #9, via direct
back-and-forth, not assumed):

1. **Legs are redefined around the real book line, not a fixed threshold.**
   Each team's leg is "cleared its own real market-implied total," not
   "cleared 100 yards." A new leg definition, not directly comparable to
   `correlated_props.py`'s already-validated underdog/narrow buckets.
2. **Team total = sum of each eligible player's own real posted O/U line**
   (`build_team_total_lines` below), not a synthesized number invented from
   scratch -- uses the book's own set points directly.
3. **Team-total pricing uncertainty is measured, not assumed from summed
   per-player variances.** The original design sketch considered assuming
   each player's yardage is Normal around their own line and summing
   variances under an independence assumption -- rejected during the build
   because it requires guessing at unknown per-player sigmas AND an
   independence assumption known to be wrong (running backs share touches).
   Instead, `fit_team_total_residual_std` calibrates ONE real team-level
   parameter directly from `(actual_team_total - implied_team_total_line)`
   on real historical games -- this implicitly captures whatever real
   correlation exists between teammates, rather than assuming it away.
   Same leg definition, same sum-of-lines threshold, same pricing/EV goal
   as the original design -- just a more defensible way to get the
   variance, consistent with this project's "measured, not guessed"
   discipline (`calibration.py::fit_residual_std`, `middle_scan.py::fit_residual_stds`).

**Reuses `correlated_props.py`'s machinery unchanged**, not a parallel
implementation: `measure_leg_correlation`, `measure_leg_correlation_by_bucket`,
`bucket_favorite_strength`, `naive_parlay_price`, `correlated_edge`,
`MEASURED_PROP_VIG` all apply directly once team-total legs are reduced to
the same boolean-indicator + market-probability shape those functions
already expect.

**Passing vs. rushing, a real asymmetry stated up front:** most teams have
exactly one real passing-yards prop per game (the starting QB), so the
"team total" IS effectively that one player's line -- a clean, low-noise
construction. Rushing totals sum 2-4 players with real shared-touch
correlation the residual-std calibration above absorbs implicitly but
doesn't explain -- expect the passing-yards version of this analysis to be
more trustworthy out of the gate.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from src.model.elo import canonical_team
from src.store.prop_settlement import normalize_player_name

REAL_PROP_STATS = ("rushing_yards", "passing_yards")


def build_team_total_lines(props: pd.DataFrame, player_stats: pd.DataFrame, prop_stat: str) -> pd.DataFrame:
    """One row per (event_id, team) with real Pinnacle data for `prop_stat`:
    `implied_team_total_line` (sum of every player with a real Pinnacle
    Over/Under line for that team/game/stat -- the team-total THRESHOLD,
    design decision #2 in the module docstring) and `actual_team_total`
    (real observed sum from `player_stats`, for calibration/outcome).

    Matches players to teams via `player_stats` (props snapshots carry no
    team field of their own) using the same `normalize_player_name()`
    reconciliation `src/store/prop_settlement.py` already built and
    validated against real book-vs-nflverse name mismatches -- reused
    here, not duplicated.
    """
    # A frame with no columns at all (an empty store read, or an empty default
    # DataFrame from a caller) raised KeyError here rather than returning the
    # empty result the next line already intends. Reporting paths call this
    # unattended, so a missing column is an empty answer, not an exception.
    required = {"book", "market", "prop_stat", "side", "capture_time", "event_id", "player_name", "line"}
    if props.empty or not required.issubset(props.columns):
        return pd.DataFrame(columns=["event_id", "team", "implied_team_total_line", "actual_team_total"])

    pin = props[
        (props["book"] == "pinnacle") & (props["market"] == "player_prop") & (props["prop_stat"] == prop_stat)
    ].copy()
    if pin.empty:
        return pd.DataFrame(columns=["event_id", "team", "implied_team_total_line", "actual_team_total"])

    # One line per player: books quote the SAME line on both Over and Under,
    # so the Over side alone (latest capture per player/game) already has it.
    pin_over = pin[pin["side"] == "over"].sort_values("capture_time")
    pin_over = pin_over.drop_duplicates(subset=["event_id", "player_name"], keep="last")

    name_to_team = {
        (row.game_id, normalize_player_name(row.player_display_name)): row.team
        for row in player_stats.itertuples(index=False)
        if pd.notna(row.player_display_name) and pd.notna(row.team)
    }
    pin_over = pin_over.copy()
    pin_over["team"] = [
        name_to_team.get((event_id, normalize_player_name(name)))
        for event_id, name in zip(pin_over["event_id"], pin_over["player_name"], strict=True)
    ]
    pin_over = pin_over.dropna(subset=["team"])
    pin_over["team"] = pin_over["team"].map(canonical_team)

    implied = pin_over.groupby(["event_id", "team"], as_index=False)["line"].sum().rename(
        columns={"line": "implied_team_total_line"}
    )

    stats = player_stats.copy()
    stats["team"] = stats["team"].map(canonical_team)
    actual = stats.groupby(["game_id", "team"], as_index=False)[prop_stat].sum().rename(
        columns={"game_id": "event_id", prop_stat: "actual_team_total"}
    )

    return implied.merge(actual, on=["event_id", "team"], how="inner")


def fit_team_total_residual_std(team_totals: pd.DataFrame) -> tuple[float, float]:
    """(mean_residual, residual_std) of `actual_team_total -
    implied_team_total_line` on real historical games -- see module
    docstring point 3 for why this replaces a summed-per-player-variance
    approach. `mean_residual` bias-corrects the implied mean (real lines
    aren't guaranteed to be exactly unbiased); `residual_std` is the real
    pricing uncertainty. Always pass a train/calib split here, never the
    same games being priced -- same discipline as every other residual-std
    fit in this project.
    """
    residuals = team_totals["actual_team_total"] - team_totals["implied_team_total_line"]
    return float(residuals.mean()), float(residuals.std(ddof=1))


def team_total_over_indicator(team_totals: pd.DataFrame) -> pd.Series:
    """Boolean: did the team's real total clear its own real implied line --
    the leg indicator `measure_leg_correlation`/`correlated_props.py`'s
    machinery expects, for THIS module's real-market-implied leg definition
    (design decision #1) instead of a fixed threshold.
    """
    return team_totals["actual_team_total"] > team_totals["implied_team_total_line"]


def build_team_outcomes(moneyline: pd.DataFrame, schedule: pd.DataFrame, book: str = "pinnacle") -> pd.DataFrame:
    """Per (event_id, team): `team_market_prob` (devigged moneyline win prob),
    `team_won`, and `season` -- the three columns
    `fit_team_total_lift_by_bucket` needs to stratify by favourite strength.

    Uses the LATEST quote per (event, side), i.e. the close, matching how the
    lift was originally measured.
    """
    from src.model.baseline import market_baseline

    ml = moneyline[(moneyline["market"] == "moneyline") & (moneyline["book"] == book)]
    if ml.empty:
        return pd.DataFrame(columns=["event_id", "team", "team_market_prob", "team_won", "season"])
    ml = ml.sort_values("capture_time").drop_duplicates(["event_id", "side"], keep="last")
    wide = ml.pivot_table(index="event_id", columns="side", values="price_american", aggfunc="last").dropna()
    if not {"home", "away"}.issubset(wide.columns):
        return pd.DataFrame(columns=["event_id", "team", "team_market_prob", "team_won", "season"])

    played = schedule.dropna(subset=["home_score", "away_score"])
    results = {
        r.game_id: (canonical_team(r.home_team), canonical_team(r.away_team),
                    int(r.home_score > r.away_score), int(r.season))
        for r in played.itertuples()
    }

    rows = []
    for event_id, r in wide.iterrows():
        if event_id not in results:
            continue
        home, away, home_won, season = results[event_id]
        prices = [int(r["home"]), int(r["away"])]
        rows.append({"event_id": event_id, "team": home, "season": season,
                     "team_market_prob": market_baseline(prices, side_index=0), "team_won": home_won})
        rows.append({"event_id": event_id, "team": away, "season": season,
                     "team_market_prob": market_baseline(prices, side_index=1), "team_won": 1 - home_won})
    return pd.DataFrame(rows)


def fit_team_total_lift_by_bucket(
    props: pd.DataFrame,
    player_stats: pd.DataFrame,
    team_outcomes: pd.DataFrame,
    prop_stat: str,
    seasons: Sequence[int] | None = None,
) -> pd.DataFrame:
    """Lift of (team wins AND team clears its own implied total), by
    favourite-strength bucket. Restrict to `seasons` for a train/test split.

    **Why this function exists (added 2026-09-04).** The lift numbers this
    project prices live bets with -- `signal/team_total_scan.py`'s
    `VALIDATED_TEAM_TOTAL_LIFT` -- existed for months as bare float literals
    with **no code anywhere that produced them**. They appeared only in that
    dict, in `methodology_backlog.md`, in the paper, and in a test that
    asserted the constant against itself. An unreproducible number priced with
    real money is indistinguishable from a typo, and the scanner's test could
    not have caught one.

    Verified on the real 2023+2024 pull the day it was written: this
    reproduces all six documented values exactly -- rushing underdog
    1.226 (train 2023) / 1.167 (test 2024) / 1.192 (pooled), passing underdog
    1.311 / 1.216 / 1.276.
    """
    totals = build_team_total_lines(props, player_stats, prop_stat)
    if totals.empty:
        return pd.DataFrame(columns=["bucket", "lift", "n"])
    totals = totals.copy()
    totals["over"] = team_total_over_indicator(totals).to_numpy()

    merged = totals.merge(team_outcomes, on=["event_id", "team"], how="inner")
    if seasons is not None:
        merged = merged[merged["season"].isin(list(seasons))]
    if merged.empty:
        return pd.DataFrame(columns=["bucket", "lift", "n"])

    from src.backtest.correlated_props import measure_leg_correlation_by_bucket

    return measure_leg_correlation_by_bucket(
        merged["team_won"], merged["over"], merged["team_market_prob"]
    )
