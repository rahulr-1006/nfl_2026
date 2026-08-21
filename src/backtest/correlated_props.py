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

# Pinnacle's own measured player-prop vig, from this project's real 178-game
# historical pull (batch 1) -- mean overround across 5,005 real Over/Under
# pairs, not a guess. See src/backtest/correlated_props.py's price functions
# below for how this becomes the "naive SGP price" this module tests against.
# (Mainline moneyline/spread/total vig measured earlier this project was
# ~2.97% -- props consistently carry more, which is why this, not that
# number, is the default here.)
MEASURED_PROP_VIG = 0.0575


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
    """
    raw = bucket_lift * team_market_prob * historical_p_b
    return min(raw, team_market_prob, historical_p_b)


def naive_parlay_price(p_a: float, p_b: float, vig: float = MEASURED_PROP_VIG) -> float:
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
    p_a: float, p_b: float, p_a_and_b: float, vig: float = MEASURED_PROP_VIG, bankroll: float = 100.0
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
