"""Correlated same-game outcome mispricing: do event pairs from the same
game co-occur more (or less) often than independence would predict?

**Why this matters as a strategy, stated plainly.** A well-documented
industry mispricing mechanism is a book building a same-game-parlay (SGP)
price by multiplying single-leg probabilities together, as if the legs
were independent -- when in reality legs from the same game are often
correlated (a team winning big and its QB having a big passing game tend
to happen together, not independently). If two legs are positively
correlated but priced as independent, the true joint probability is
higher than the quoted price implies -- a real edge, if it exists.

**Scope, stated just as plainly: this tests whether the correlation
itself is real, not whether any specific book actually misprices it.**
No real posted SGP odds exist in this project's data -- The Odds API
doesn't expose same-game-parlay pricing the way it exposes single-market
odds (a book's SGP engine typically prices dynamically at bet-slip time).
Confirming a real, statistically significant correlation is evidence the
underlying mechanism a bettor would need is real; it is not proof any
specific book prices any specific pair assuming independence. Treat a
result here as "worth checking against a real SGP price if one becomes
available," not a confirmed live exploit -- the same honest distinction
`props_arbitrage.py`'s caveats draw between a verified number and an
executable strategy.
"""

from __future__ import annotations

import pandas as pd
from scipy.stats import chi2_contingency

from src.model.elo import canonical_team
from src.signal.sizing import apply_bankroll_caps, expected_value, fractional_kelly

# Pinnacle's own measured player-prop vig: mean overround across **all 16,953
# two-sided Over/Under contracts** in the complete 2023+2024 historical pull.
# See this module's price functions below for how it becomes the "naive SGP
# price" tested against. (Mainline vig measured ~2.97% -- props consistently
# carry more, which is why this, not that number, is the default here.)
#
# **Corrected 2026-08-23: was 0.0575, measured from batch 1 only (5,005 pairs,
# 178 games).** The full two-season sample measures 0.0629. This matters
# directionally, not just numerically: `bucket_edge = lift/(1+vig)^2 - 1`, so an
# understated vig **overstates every edge this module reports** -- the
# self-flattering direction. The team-total findings move from +6.6%/+14.1% to
# +5.5%/+12.9% (still positive, but ~1.1pt weaker than previously published).
# If re-measured again, record the sample size it came from so the next reader
# knows what is being replaced.
MEASURED_PROP_VIG = 0.0629

# **Deliberately NOT a default on any pricing function below (2026-08-23).** It is
# a single pooled mean over Pinnacle only, and vig varies materially by book:
# measured across 228,146 real two-sided contracts, per-book median overround runs
# 6.47% (betonlineag) to 7.80% (williamhill_us) against this 6.29%. That spread
# matters more than it looks because `bucket_edge` divides by `(1 + vig) ** 2` --
# **vig enters SQUARED**, since these are two-leg bets. Pricing a williamhill_us
# parlay at 6.29% understates its vig by ~1.5pp, which through the squared term is
# roughly a 3pp edge error, against reported edges of +5.5%/+12.9%. And it errs in
# the self-flattering direction -- exactly how the superseded 0.0575 went unnoticed.
#
# So callers must pass a vig MEASURED from the book and line actually being priced
# (`measure_prop_vig` below). This constant remains for reference and for research
# code that genuinely wants the pooled Pinnacle number, stated explicitly.


def measure_prop_vig(props: pd.DataFrame, book: str | None = "pinnacle") -> dict:
    """Re-derive `MEASURED_PROP_VIG` from raw prop snapshots. **This exists
    because the constant above had no measurement code anywhere in the repo**
    -- it could be quoted but not reproduced or audited, and it has already
    been wrong once (0.0575, measured from batch 1 only, overstating every
    edge this module reports because `bucket_edge` divides by `(1+vig)^2`).

    Pass `book=None` to pool all books. Returns mean AND median: the constant
    is a *mean* overround, and the two differ materially here (a 2026-08-23
    re-measurement over the same 16,953 Pinnacle contracts read mean 6.29% vs
    median 6.88%, consistent with left skew from contracts priced at a flat
    -110/-110). Reporting only one hides that.

    Vig convention is `sum(q_i) - 1` (overround), matching
    `src/devig/methods.py::overround` and the `(1 + vig)` inversion used by
    `naive_parlay_price` below -- NOT "hold", which would be
    `overround / (1 + overround)` and reads ~0.5pp lower.
    """
    df = props[props["market"] == "player_prop"]
    if book is not None:
        df = df[df["book"] == book]

    key = ["event_id", "book", "player_name", "prop_stat", "line"]
    latest = df.sort_values("capture_time").groupby(key + ["side"], as_index=False).last()
    wide = latest.pivot_table(index=key, columns="side", values="implied_prob_raw", aggfunc="last")

    # Two-sided only: a one-sided quote has no complement to sum against, so it
    # carries no measurable overround at all (see src/collect/props.py on why
    # anytime-TD is out of scope entirely for exactly this reason).
    if "over" not in wide.columns or "under" not in wide.columns:
        return {"n_contracts": 0, "mean_overround": None, "median_overround": None, "book": book}
    wide = wide.dropna(subset=["over", "under"])
    ovr = wide["over"] + wide["under"] - 1.0

    return {
        "n_contracts": len(ovr),
        "mean_overround": float(ovr.mean()) if len(ovr) else None,
        "median_overround": float(ovr.median()) if len(ovr) else None,
        "p99_overround": float(ovr.quantile(0.99)) if len(ovr) else None,
        "book": book,
    }


def measure_leg_correlation(indicator_a: pd.Series, indicator_b: pd.Series) -> dict:
    """`indicator_a`/`indicator_b`: aligned boolean/0-1 Series, one row per
    game (or team-game). `lift` = P(A and B) / (P(A) x P(B)) -- 1.0 means
    independent, >1 means the legs co-occur more than chance (a real
    positive-correlation candidate), <1 means less. The chi-square test on
    the 2x2 contingency table is the significance check: a lift that looks
    real but isn't (p >= 0.05) shouldn't be reported as a finding, the same
    "does it survive a robustness check" discipline as every other result
    this session.
    """
    a = indicator_a.astype(bool).reset_index(drop=True)
    b = indicator_b.astype(bool).reset_index(drop=True)
    n = len(a)
    p_a = float(a.mean())
    p_b = float(b.mean())
    p_ab = float((a & b).mean())
    independent_p_ab = p_a * p_b
    lift = p_ab / independent_p_ab if independent_p_ab > 0 else float("nan")

    table = pd.crosstab(a, b)
    chi2, p_value, _dof, _expected = chi2_contingency(table)

    return {
        "n": n,
        "p_a": p_a,
        "p_b": p_b,
        "p_a_and_b": p_ab,
        "independent_p_a_and_b": independent_p_ab,
        "lift": lift,
        "chi2": float(chi2),
        "p_value": float(p_value),
    }


# Fixed, round bucket edges on the market's own devigged win probability for
# the team on the "A" side of a leg pair -- NOT data-derived quantiles, a
# deliberate choice for robustness/explainability over a marginal precision
# gain. Checked before using: pooled ("constant lift") was the original
# design, and it's wrong -- lift for team_won x leading_rusher_100plus runs
# 1.92 (biggest underdogs) down to 1.17 (heaviest favorites), monotonically
# decreasing across all four buckets, same direction for game_over x
# qb_2plus_tds. An underdog's win is disproportionately likely to come via
# grinding out a big rushing performance; a heavy favorite's win is more
# "routine" and doesn't need the same correlated performance to happen.
FAVORITE_BUCKETS = [
    (0.0, 0.45, "underdog"),
    (0.45, 0.55, "narrow"),
    (0.55, 0.70, "favorite"),
    (0.70, 1.000001, "heavy_favorite"),  # +epsilon so p=1.0 falls in-bucket, not out-of-range
]


def bucket_favorite_strength(team_market_prob: float, buckets: list[tuple[float, float, str]] = FAVORITE_BUCKETS) -> str:
    """Which `FAVORITE_BUCKETS` bucket a team's real market-implied win
    probability (for THIS specific game -- e.g. `market_prob_home` from
    `build_training_frame`, flipped for the away team) falls into.
    """
    for lo, hi, label in buckets:
        if lo <= team_market_prob < hi:
            return label
    raise ValueError(f"team_market_prob {team_market_prob} not in [0, 1]")


def measure_leg_correlation_by_bucket(
    indicator_a: pd.Series,
    indicator_b: pd.Series,
    team_market_prob: pd.Series,
    buckets: list[tuple[float, float, str]] = FAVORITE_BUCKETS,
) -> pd.DataFrame:
    """`measure_leg_correlation`, stratified by favorite strength -- see
    `FAVORITE_BUCKETS`'s docstring for why pooled ("constant") lift is
    misleading and shouldn't be used for a specific game.
    """
    df = pd.DataFrame(
        {
            "a": indicator_a.reset_index(drop=True),
            "b": indicator_b.reset_index(drop=True),
            "p": team_market_prob.reset_index(drop=True),
        }
    )
    df["bucket"] = df["p"].apply(lambda p: bucket_favorite_strength(p, buckets))

    rows = []
    for _lo, _hi, label in buckets:
        sub = df[df["bucket"] == label]
        if sub.empty:
            continue
        r = measure_leg_correlation(sub["a"], sub["b"])
        rows.append({"bucket": label, "mean_market_prob": float(sub["p"].mean()), **r})
    return pd.DataFrame(rows)


def estimate_game_specific_joint_prob(team_market_prob: float, historical_p_b: float, bucket_lift: float) -> float:
    """Game-specific estimate of P(A and B), for pricing one particular
    upcoming game rather than reporting a pooled statistic. Uses THIS
    game's real market-implied P(A) (a bettor's actual best pre-game
    estimate of the leg-A probability -- not the pooled historical
    average, which is exactly 0.5 by construction when home/away are
    pooled and tells you nothing about this specific matchup), the pooled
    historical P(B) (no per-game model exists yet for the prop-threshold
    leg), and the bucket-specific lift for this game's favorite strength
    (`measure_leg_correlation_by_bucket` -- constant/pooled lift was
    tested and rejected, see `FAVORITE_BUCKETS`).

    Clipped to a valid joint-probability range: P(A and B) can never
    exceed either marginal, and a naive `lift * p_a * p_b` product isn't
    guaranteed to respect that on its own.

    **This function has no notion of which bucket is trustworthy** -- it
    will happily price a favorite/heavy_favorite bucket that failed an
    honest out-of-sample check just as readily as a validated one. A real
    live scan should call `price_bucket_bet` instead, which wraps this
    function with that check.
    """
    raw = bucket_lift * team_market_prob * historical_p_b
    return min(raw, team_market_prob, historical_p_b)


def bucket_edge(lift: float, vig: float) -> float:
    """Closed-form edge for one `FAVORITE_BUCKETS` bucket, under this
    module's multiplicative pricing model -- a real algebraic property, not
    an approximation. `naive_parlay_price` scales as `1/p_a`; the unclipped
    `estimate_game_specific_joint_prob` scales as `p_a` directly; they
    cancel exactly, so the edge depends only on which bucket's lift applies,
    not on any specific game's market probability. Derivation:
    `edge = p*d - 1 = (lift*p_a*p_b) * (1/(p_a*(1+vig)*p_b*(1+vig))) - 1
    = lift/(1+vig)^2 - 1`.

    Matches `correlated_edge(...)["edge"]` exactly whenever the joint estimate
    isn't hitting the clip (true for all but the most extreme favorite
    games -- see `estimate_game_specific_joint_prob`'s docstring). Lets a
    bucket sweep across many leg pairs be screened for "clears vig" without
    looping over every individual game.
    """
    return lift / (1 + vig) ** 2 - 1


def naive_parlay_price(p_a: float, p_b: float, vig: float) -> float:
    """Decimal price a same-game parlay would carry if a book priced it by
    multiplying each leg's own *vigged* single-leg price together -- the
    naive-independence SGP construction this whole module tests against.

    `vig` inflates each true leg probability the way
    `src/devig/methods.py::devig_multiplicative` removes it, in reverse:
    `q_i = p_i * (1 + vig)`, so a symmetric two-way market's raw implied
    probabilities sum to `(1 + vig)`, matching that method's own overround
    definition -- reusing this project's existing devig methodology rather
    than inventing a separate vig model for this one strategy.
    """
    q_a = p_a * (1 + vig)
    q_b = p_b * (1 + vig)
    if q_a >= 1 or q_b >= 1:
        raise ValueError(f"vig-inflated probability >= 1 (p_a={p_a}, p_b={p_b}, vig={vig}) -- too large for these leg probabilities")
    return 1.0 / (q_a * q_b)


def correlated_edge(
    p_a: float, p_b: float, p_a_and_b: float, vig: float, bankroll: float = 100.0
) -> dict:
    """The bettor-relevant number this module exists to produce: if a book
    prices a same-game parlay of legs A and B naively (`naive_parlay_price`),
    and the TRUE joint probability is `p_a_and_b` (measured by
    `measure_leg_correlation` on real historical data, not assumed), what's
    the expected value of betting that parlay, and what would
    `src/signal/sizing.py`'s own Kelly sizing suggest staking? Reuses
    `expected_value`/`fractional_kelly`/`apply_bankroll_caps` unchanged --
    the same sizing math every other +EV spot in this project uses, not a
    bespoke calculation for this one strategy.
    """
    price = naive_parlay_price(p_a, p_b, vig)
    edge = expected_value(p_a_and_b, price)
    stake = apply_bankroll_caps(fractional_kelly(p_a_and_b, price) * bankroll, bankroll=bankroll)
    return {
        "vig": vig,
        "naive_parlay_price": price,
        "naive_implied_prob": 1.0 / price,
        "true_prob": p_a_and_b,
        "edge": edge,
        "suggested_stake": stake,
    }


# Buckets confirmed to survive an honest out-of-sample check
# (`src/backtest/validation.py`'s 2026-08-21 portfolio validation -- see paper
# §4.5's "Portfolio validation" subsection for the full evidence), not just the
# original in-sample pooled analysis that first reported bucket edges above.
# `favorite`/`heavy_favorite` cleared vig pooled for BOTH pairs checked this way
# (`team_won x leading_rusher_100plus`, `game_over x qb_2plus_tds`), but neither
# survived a proper train/test split or walk-forward validation -- one bucket's
# edge collapsed to near-zero, the other flipped sign entirely. The other 5 leg
# pairs' favorite/heavy_favorite buckets have never been checked this way at
# all -- there's no evidence they're fine, only less evidence they're broken.
# Treating them as unvalidated too, not just the two directly tested, is the
# conservative direction to be wrong in.
VALIDATED_RELIABLE_BUCKETS = {"underdog", "narrow"}


def is_bucket_validated(bucket: str) -> bool:
    """Whether `bucket` (one of `FAVORITE_BUCKETS`' labels) has survived an
    honest out-of-sample check. See `VALIDATED_RELIABLE_BUCKETS`'s comment
    for the evidence and its scope.
    """
    return bucket in VALIDATED_RELIABLE_BUCKETS


class UnvalidatedBucketError(ValueError):
    """Raised by `price_bucket_bet` when asked to price a favorite/
    heavy_favorite bucket without explicitly opting in via
    `allow_unvalidated=True`. See `VALIDATED_RELIABLE_BUCKETS`."""


def price_bucket_bet(
    team_market_prob: float,
    historical_p_b: float,
    bucket_lift: dict[str, float],
    vig: float,
    bankroll: float = 100.0,
    allow_unvalidated: bool = False,
) -> dict:
    """The one real pricing entrypoint any future live correlated-props
    scanner should call -- not `estimate_game_specific_joint_prob` /
    `correlated_edge` directly, which have no notion of which buckets are
    trustworthy and will happily price an unvalidated one.

    Classifies `team_market_prob` into its `FAVORITE_BUCKETS` bucket, REFUSES
    (raises `UnvalidatedBucketError`) to price it if that bucket isn't in
    `VALIDATED_RELIABLE_BUCKETS` -- unless the caller explicitly passes
    `allow_unvalidated=True` (e.g. for further research on the unvalidated
    buckets, never for a real live scan) -- and otherwise reuses
    `estimate_game_specific_joint_prob` + `correlated_edge` completely
    unchanged.

    `bucket_lift` must be keyed by bucket label (e.g. the output of
    `dict(zip(bt["bucket"], bt["lift"]))` on a `measure_leg_correlation_by_bucket`
    result) -- and should itself come from an honest split
    (`src/backtest/validation.py::split_by_season`/`expanding_season_folds`
    on TRAIN data only), not the full pool including whatever game is being
    priced. This function only guards which BUCKET is trustworthy; it
    can't detect whether the `bucket_lift` passed in was itself leaked --
    that discipline is still the caller's responsibility.
    """
    bucket = bucket_favorite_strength(team_market_prob)
    if not allow_unvalidated and not is_bucket_validated(bucket):
        raise UnvalidatedBucketError(
            f"bucket {bucket!r} (team_market_prob={team_market_prob}) has not survived an "
            f"honest out-of-sample check -- only {sorted(VALIDATED_RELIABLE_BUCKETS)} have "
            f"(src/backtest/validation.py, 2026-08-21). Pass allow_unvalidated=True to price "
            f"it anyway."
        )

    lift = bucket_lift[bucket]
    joint = estimate_game_specific_joint_prob(team_market_prob, historical_p_b, lift)
    result = correlated_edge(team_market_prob, historical_p_b, joint, vig=vig, bankroll=bankroll)
    result["bucket"] = bucket
    result["bucket_validated"] = is_bucket_validated(bucket)
    result["bucket_lift"] = lift
    return result


def build_team_game_outcomes(schedule: pd.DataFrame, player_stats: pd.DataFrame) -> pd.DataFrame:
    """One row per team per game, home and away pooled (2x the game count,
    each team's own perspective) -- the analysis frame `measure_leg_correlation`
    runs against. Columns:

    - `team_won`: this team beat its opponent (ties excluded, same as every
      other win-label frame in this project).
    - `team_covers`: this team covered `spread_line` from its own perspective.
    - `game_over`: the game total went over `total_line`.
    - `qb_2plus_tds`: this team's starting QB (schedule's `home_qb_id`/
      `away_qb_id` -- the same authoritative starter field `qb_elo.py` uses,
      not "whoever threw the most passes that game") threw >=2 passing TDs.
    - `leading_receiver_75plus`: this team's leading receiver that game (by
      `receiving_yards` in `player_stats`, ties broken arbitrarily -- rare)
      gained >=75 receiving yards.
    - `leading_rusher_100plus`: same for `rushing_yards` >= 100.
    - `season`: from the schedule's own `season` column -- needed for an
      honest train/test split (`src/backtest/validation.py::split_by_season`)
      instead of parsing it out of `game_id` ad hoc, which the notebook did
      before this column existed.
    """
    games = schedule.dropna(subset=["home_score", "away_score", "spread_line", "total_line"]).copy()
    games["home_team"] = games["home_team"].map(canonical_team)
    games["away_team"] = games["away_team"].map(canonical_team)
    games = games[games["home_score"] != games["away_score"]]

    stats = player_stats.copy()
    stats["team"] = stats["team"].map(canonical_team)

    leading_receiver = stats.sort_values("receiving_yards", ascending=False).drop_duplicates(["game_id", "team"], keep="first")
    leading_rusher = stats.sort_values("rushing_yards", ascending=False).drop_duplicates(["game_id", "team"], keep="first")
    qb_tds = stats.set_index(["game_id", "player_id"])["passing_tds"]

    rows = []
    for row in games.itertuples():
        margin = row.home_score - row.away_score
        total_points = row.home_score + row.away_score
        game_over = total_points > row.total_line

        for team, opp_team, qb_id, team_margin, covers_line in (
            (row.home_team, row.away_team, row.home_qb_id, margin, row.spread_line),
            (row.away_team, row.home_team, row.away_qb_id, -margin, -row.spread_line),
        ):
            qb_pass_tds = qb_tds.get((row.game_id, qb_id))
            receiver_row = leading_receiver[(leading_receiver["game_id"] == row.game_id) & (leading_receiver["team"] == team)]
            rusher_row = leading_rusher[(leading_rusher["game_id"] == row.game_id) & (leading_rusher["team"] == team)]

            rows.append(
                {
                    "game_id": row.game_id,
                    "season": row.season,
                    "team": team,
                    "opponent": opp_team,
                    "team_won": team_margin > 0,
                    "team_covers": team_margin > covers_line if team_margin != covers_line else None,
                    "game_over": game_over,
                    "qb_2plus_tds": (qb_pass_tds is not None) and (qb_pass_tds >= 2),
                    "leading_receiver_75plus": bool(len(receiver_row)) and float(receiver_row["receiving_yards"].iloc[0]) >= 75,
                    "leading_rusher_100plus": bool(len(rusher_row)) and float(rusher_row["rushing_yards"].iloc[0]) >= 100,
                }
            )

    return pd.DataFrame(rows)
