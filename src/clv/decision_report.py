"""The go/no-go table: what do I bet at the end of September, and on what evidence?

**Why this module exists.** As of 2026-09-14 the alert side had produced 820 shadow
legs -- 625 of them in two days -- and nothing downstream turned them into a number
anyone could decide on. `make clv-report` gives CLV, `make shadow-report` gives
survival, and neither says *go or no-go*. Answering that meant running ad-hoc queries
by hand, which is exactly the state in which a bet gets placed on a vibe.

This composes the two existing measurements into one pre-registered verdict. It
computes **no new statistics** -- CLV comes from `shadow_clv` (which routes through
`bet_log.to_backtest_bets`, the single canonical CLV definition), CIs come from
`clv.metrics.bootstrap_ci`, and survival comes from the shadow log. Re-deriving any of
them here would create a second definition that could silently drift from the one every
other consumer uses, which is a failure this project has already found in its own
history more than once.

## The bar, fixed before the data arrived

A DIRECTIONAL strategy goes live only when, over `MIN_N` measurable legs:

    beat_rate > 50%  AND  mean_clv > 0

Set on 2026-09-14, deliberately ahead of the Week 2 and Week 3 data, so it cannot be
tuned to whatever the season happens to produce. End of September is a review
checkpoint, not a start gun: if nothing clears, nothing gets bet.

## Why `prop_arb` is scored differently, and why that is not special pleading

**An arbitrage is market-neutral by construction.** Both sides are held, so line
movement cancels and expected CLV is ~0 no matter how good the arb is. The measured
`mean_clv = -0.0000` on 2026-09-14 is the *predicted* value, not a failure signal.
Scoring it against `mean_clv > 0` would permanently retire the project's strongest
structural edge for a reason that is mathematically guaranteed in advance -- the exact
shape of error `methodology_backlog.md` records three times already ("a metric that
cannot come out any other way").

Structural strategies are therefore scored on whether the lock is *capturable*:

    expected_capture = both_legs_placeable_rate * mean_margin  > 0

`both_legs_placeable_rate` is the real unknown. A margin you cannot place both sides of
is not an edge, and `one_leg_only_rate` is worse than a miss -- it is naked exposure on
a side you never wanted, which is why this module reports it as its own column rather
than folding it into the failures.

## The horizon trap this module exists to avoid

`shadow_log.survival_report` answers "did the price survive to the LAST re-check",
which lands 4-6 hours out. That is a real question but it is not the actionable one,
and reading it as a latency number is what made prop arb look like 0% survival on
2026-09-14. **Survival here is measured at the FIRST re-check**, and only for legs whose
first re-check actually landed inside `DEFAULT_HORIZON_MINUTES`.

That distinction has teeth because prop re-observation cadence *is* the props polling
cadence: median time to first re-check measured 2026-09-14 was ~31-35 min for
`moneyline_ev`/`steam` but **~238 min for props** outside the final 12h. Props are only
sampled densely inside the arb tier. So an out-of-window prop renders `n/a`, never a
4-hour number wearing a 20-minute label.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from src.clv.metrics import bootstrap_ci
from src.clv.seals import WK10_14_OPENS, withheld
from src.clv.shadow_clv import shadow_clv_frame
from src.signal.shadow_log import SHADOW_LOG_PATH, ShadowObservation, load
from src.store.pit_store import PointInTimeStore

log = logging.getLogger(__name__)

# Fixed 2026-09-14, before the Week 2/3 data existed. Do not tune to results.
MIN_N = 30
MIN_BEAT_RATE = 0.50
MIN_MEAN_CLV = 0.0

# Strategies whose edge is structural (both sides held) rather than directional.
# These are scored on capturability, not CLV -- see the module docstring.
STRUCTURAL_STRATEGIES = frozenset({"prop_arb"})

# A re-check later than this is not measuring detection latency, whatever it is
# measuring. Wider than the ~20 min worst-case alert path (0.25h poll spacing +
# 300s monitor interval) so a single missed poll does not void an otherwise good
# observation, tight enough that a 4-hour props gap can never qualify.
DEFAULT_HORIZON_MINUTES = 40.0
# Below this, a survival rate is noise dressed as a measurement.
MIN_SURVIVAL_N = 5

VERDICT_GO = "GO"
VERDICT_NO = "NO"


def _decimal(american: float) -> float:
    """American -> decimal. Survival must compare payouts, not raw American odds:
    -105 is better than -120 but worse than +100, so a numeric `>=` is wrong.
    """
    a = float(american)
    return 1 + (a / 100 if a > 0 else 100 / abs(a))


def first_recheck_frame(path: Path = SHADOW_LOG_PATH) -> pd.DataFrame:
    """One row per alerted leg, scored at its FIRST re-observation.

    This is the piece `survival_report` does not provide: it reports the last
    re-check, which is a 4-6 hour horizon. `minutes_to_first` is carried on every
    row so a caller can see *when* the observation happened rather than trusting
    that it happened soon.

    Legs never re-checked are returned with `held=None` rather than dropped -- a
    report that silently drops unobserved legs shrinks its own denominator, which
    is how a survival rate starts looking better than it is.
    """
    obs = load(path)
    if not obs:
        return pd.DataFrame()

    by_leg: dict[tuple[str, str], list[ShadowObservation]] = {}
    for o in obs:
        by_leg.setdefault((o.alert_key, o.leg), []).append(o)

    rows = []
    for (alert_key, leg), series in by_leg.items():
        series.sort(key=lambda o: o.observed_at)
        alert = next((o for o in series if o.is_alert), None)
        if alert is None:
            continue
        rechecks = [o for o in series if not o.is_alert]
        first = rechecks[0] if rechecks else None

        held: bool | None = None
        minutes: float | None = None
        if first is not None:
            held = (
                first.price_american is not None
                and alert.price_american is not None
                and _decimal(first.price_american) >= _decimal(alert.price_american)
            )
            minutes = (first.observed_at - alert.alerted_at).total_seconds() / 60.0

        rows.append({
            "alert_key": alert_key,
            "leg": leg,
            "strategy": alert.strategy,
            "alerted_at": alert.alerted_at,
            "edge": alert.edge,
            "minutes_to_first": minutes,
            "held": held,
        })
    return pd.DataFrame(rows)


def survival_at_horizon(
    legs: pd.DataFrame,
    strategy: str,
    horizon_minutes: float = DEFAULT_HORIZON_MINUTES,
    min_n: int = MIN_SURVIVAL_N,
) -> tuple[float | None, int, float | None]:
    """(survival_rate, n_in_horizon, median_minutes_to_first) for one strategy.

    Returns `None` for the rate when too few legs were re-observed inside the
    horizon. `median_minutes_to_first` is computed over ALL re-checked legs, not
    just the qualifying ones, because its whole job is to explain a `None`: a
    median of 238 minutes is why props outside the final 12h have no latency
    number, and hiding that would make the gap look like missing data.
    """
    if legs.empty:
        return None, 0, None
    s = legs[(legs["strategy"] == strategy) & legs["minutes_to_first"].notna()]
    if s.empty:
        return None, 0, None
    median_minutes = float(s["minutes_to_first"].median())

    inside = s[(s["minutes_to_first"] <= horizon_minutes) & s["held"].notna()]
    if len(inside) < min_n:
        return None, len(inside), median_minutes
    return float(inside["held"].mean()), len(inside), median_minutes


def structural_capture(
    legs: pd.DataFrame,
    strategy: str,
    horizon_minutes: float = DEFAULT_HORIZON_MINUTES,
) -> dict:
    """Capturability of a structural (both-sides-held) strategy.

    An arb is only real if EVERY leg is still placeable, so legs are rolled up to
    the alert with `all()`, never `any()`. Three outcomes are distinguished because
    they have different consequences:

      - all legs held        -> the lock was capturable
      - SOME legs held       -> `one_leg_only_rate`, the dangerous case. You get
                                naked exposure on a side you never wanted, which
                                is strictly worse than the alert never firing.
      - no legs held         -> a clean miss, costs nothing

    `expected_capture` is deliberately optimistic: it credits the full margin on
    captured alerts and charges nothing for the one-leg case. A negative number
    here would therefore be damning; a positive one is an upper bound.
    """
    s = legs[(legs["strategy"] == strategy) & legs["minutes_to_first"].notna()]
    s = s[s["minutes_to_first"] <= horizon_minutes]
    empty = {"n_alerts": 0, "both_legs_rate": None, "one_leg_only_rate": None,
             "mean_margin": None, "expected_capture": None}
    if s.empty:
        return empty

    per_alert = s.groupby("alert_key").agg(
        n_legs=("held", "size"),
        n_held=("held", lambda x: int(x.fillna(False).sum())),
        margin=("edge", "first"),
    )
    per_alert = per_alert[per_alert["n_legs"] >= 2]  # a one-legged "arb" is not one
    # Below MIN_SURVIVAL_N these rates are noise wearing a percent sign. Reporting
    # "one_leg_only=100%" off two alerts would read as a finding about naked
    # exposure when it is two coin flips; `n_alerts` is still returned so the
    # caller can say how short the sample is.
    if len(per_alert) < MIN_SURVIVAL_N:
        return {**empty, "n_alerts": len(per_alert)}

    both = per_alert["n_held"] == per_alert["n_legs"]
    partial = (per_alert["n_held"] > 0) & ~both
    both_rate = float(both.mean())
    margins = per_alert.loc[both, "margin"].dropna()
    mean_margin = float(margins.mean()) if not margins.empty else None

    return {
        "n_alerts": len(per_alert),
        "both_legs_rate": both_rate,
        "one_leg_only_rate": float(partial.mean()),
        "mean_margin": mean_margin,
        "expected_capture": (both_rate * mean_margin) if mean_margin is not None else None,
    }


def _ci(values: np.ndarray) -> tuple[float | None, float | None]:
    if values.size < 2:
        return None, None
    lo, hi = bootstrap_ci(values, random_state=0)
    return float(lo), float(hi)


def ci_includes_zero(lo: float | None, hi: float | None) -> bool:
    """Does the CLV confidence interval straddle zero?

    **This is deliberately NOT part of the bar.** The bar was pre-registered on
    2026-09-14 as `beat_rate > 50% AND mean_clv > 0`, and adding a
    CI-excludes-zero clause after seeing the data would be tuning the test to the
    result -- the exact thing pre-registration prevents.

    It is surfaced next to the verdict instead, because on 2026-09-21
    `moneyline_ev` cleared the bar with mean_clv +0.0053 and a CI of
    [-0.0006, +0.0112]. That is a GO resting on a point estimate the same data
    cannot distinguish from zero, on the one market this project's own backtests
    say it reliably loses to. A reader must see that without the verdict quietly
    changing underneath them.
    """
    return not _missing(lo) and not _missing(hi) and float(lo) <= 0.0 <= float(hi)


def _directional_verdict(n: int, beat: float | None, mean_clv: float | None) -> str:
    if n < MIN_N or beat is None or mean_clv is None:
        return f"HOLD (n={n}, need {MIN_N})"
    if beat > MIN_BEAT_RATE and mean_clv > MIN_MEAN_CLV:
        return VERDICT_GO
    return VERDICT_NO


def _structural_verdict(cap: dict) -> str:
    n = cap["n_alerts"]
    if n < MIN_N or cap["expected_capture"] is None:
        return f"HOLD (n={n}, need {MIN_N})"
    return VERDICT_GO if cap["expected_capture"] > 0 else VERDICT_NO


def decision_table(
    store: PointInTimeStore,
    path: Path = SHADOW_LOG_PATH,
    as_of: datetime | None = None,
    horizon_minutes: float = DEFAULT_HORIZON_MINUTES,
) -> pd.DataFrame:
    """One row per strategy: the evidence, and the verdict it implies.

    Strategies are taken from the union of what the CLV frame and the shadow log
    know about, so a strategy that has alerted but has no measurable CLV yet still
    appears as a HOLD rather than vanishing from the table.
    """
    clv = shadow_clv_frame(store, path=path, as_of=as_of)
    legs = first_recheck_frame(path)

    names: set[str] = set()
    if not clv.empty:
        names |= {str(s) for s in clv["strategy"].dropna().unique()}
    if not legs.empty:
        names |= {str(s) for s in legs["strategy"].dropna().unique()}
    if not names:
        return pd.DataFrame()

    measurable = clv[clv["measurable"]] if not clv.empty else pd.DataFrame()

    rows = []
    for name in sorted(names):
        structural = name in STRUCTURAL_STRATEGIES

        vals = np.array([])
        if not measurable.empty:
            vals = measurable.loc[measurable["strategy"] == name, "clv_probability"].dropna().to_numpy()
        n = int(vals.size)
        beat = float((vals > 0).mean()) if n else None
        mean_clv = float(vals.mean()) if n else None
        lo, hi = _ci(vals)

        rate, n_surv, median_min = survival_at_horizon(legs, name, horizon_minutes)
        cap = structural_capture(legs, name, horizon_minutes) if structural else {}

        rows.append({
            "strategy": name,
            "scored_as": "structural" if structural else "directional",
            "n": cap["n_alerts"] if structural else n,
            "beat_rate": beat,
            "mean_clv": mean_clv,
            "clv_ci_lo": lo,
            "clv_ci_hi": hi,
            "survival": rate,
            "n_survival": n_surv,
            "median_min_to_first": median_min,
            "both_legs_rate": cap.get("both_legs_rate"),
            "one_leg_only_rate": cap.get("one_leg_only_rate"),
            "expected_capture": cap.get("expected_capture"),
            "verdict": _structural_verdict(cap) if structural else _directional_verdict(n, beat, mean_clv),
        })
    return pd.DataFrame(rows)


def _missing(v) -> bool:
    """None and NaN both mean "not measured" here. They must render identically:
    a bare `is None` check lets a NaN through as "nan%", which reads like a
    computed value rather than an absent one.
    """
    return v is None or (isinstance(v, float) and pd.isna(v)) or v is pd.NA


def _pct(v: float | None) -> str:
    return "  n/a " if _missing(v) else f"{float(v):6.1%}"


def _sig(v: float | None) -> str:
    return "    n/a" if _missing(v) else f"{float(v):+7.4f}"


def format_table(table: pd.DataFrame, horizon_minutes: float = DEFAULT_HORIZON_MINUTES) -> str:
    """The table as text, carrying its own caveats.

    Every `n/a` is explained inline. A reader who does not know that props are
    sampled every 4 hours outside the final 12h would otherwise read a missing
    survival number as a bug.
    """
    if table.empty:
        return "decision report: no alerts recorded yet"

    header = (
        f"DECISION REPORT  (bar: n>={MIN_N}, beat_rate>{MIN_BEAT_RATE:.0%}, mean_clv>{MIN_MEAN_CLV:g};"
        f" survival at first re-check <= {horizon_minutes:.0f} min)"
    )
    columns = (
        f"{'strategy':14} {'n':>4} {'beat':>7} {'mean_clv':>8} {'95% CI':>18} "
        f"{'surv':>7} {'verdict':>18}"
    )
    lines = [header, "", columns, "-" * 82]
    for _, r in table.iterrows():
        ci = (
            f"[{r['clv_ci_lo']:+.4f},{r['clv_ci_hi']:+.4f}]"
            if not _missing(r["clv_ci_lo"])
            else "               n/a"
        )
        # `*` marks a structural row, whose `n` counts ALERTS scored for
        # capturability -- not the CLV legs the directional rows count. Without
        # the marker the two n's read as the same quantity.
        name = f"{r['strategy']}*" if r["scored_as"] == "structural" else str(r["strategy"])
        lines.append(
            f"{name:14} {int(r['n']):4d} {_pct(r['beat_rate'])} {_sig(r['mean_clv'])} "
            f"{ci:>18} {_pct(r['survival'])} {r['verdict']:>18}"
        )

    notes: list[str] = []
    for _, r in table.iterrows():
        if r["verdict"] == VERDICT_GO and r["scored_as"] == "directional" and ci_includes_zero(r["clv_ci_lo"], r["clv_ci_hi"]):
            notes.append(
                f"{r['strategy']}: GO rests on a 95% CI that INCLUDES ZERO "
                f"([{r['clv_ci_lo']:+.4f}, {r['clv_ci_hi']:+.4f}]) -- the bar is a point estimate and this "
                f"data cannot distinguish its mean CLV from zero. The bar was fixed before the data and is "
                f"NOT being changed here; treat this as clearing a low bar, not as a measured edge."
            )
    if (table["scored_as"] == "structural").any():
        notes.append(
            "* = scored on CAPTURABILITY, not CLV, and its `n` counts alerts rather than CLV legs. "
            "An arb is market-neutral by construction, so mean_clv ~ 0 is the predicted value, "
            "not a failure -- its beat_rate/mean_clv columns are shown for information and are "
            "NOT what the verdict uses."
        )
    for _, r in table.iterrows():
        if r["scored_as"] == "structural":
            if _missing(r["both_legs_rate"]):
                notes.append(
                    f"{r['strategy']}: capturability unmeasured -- only {int(r['n'])} alert(s) had both legs "
                    f"re-observed inside the horizon, below the {MIN_SURVIVAL_N} needed. This is the number "
                    f"that decides whether the lock is real, and it is the main thing Weeks 2-3 must produce."
                )
            else:
                notes.append(
                    f"{r['strategy']}: both_legs={_pct(r['both_legs_rate'])} "
                    f"one_leg_only={_pct(r['one_leg_only_rate'])} "
                    f"expected_capture={_sig(r['expected_capture'])}"
                )
                if not _missing(r["one_leg_only_rate"]) and r["one_leg_only_rate"] > 0:
                    notes.append(
                        f"{r['strategy']}: one_leg_only is NAKED EXPOSURE, strictly worse than a miss -- "
                        f"not counted as a cost in expected_capture, so that figure is an upper bound."
                    )
        if r["survival"] is None or pd.isna(r["survival"]):
            med = r["median_min_to_first"]
            if med is None or pd.isna(med):
                notes.append(f"{r['strategy']}: no re-check yet, so survival is unmeasured.")
            elif med > horizon_minutes:
                notes.append(
                    f"{r['strategy']}: survival n/a -- median first re-check is {med:.0f} min, past the "
                    f"{horizon_minutes:.0f} min horizon. Props outside the final 12h are sampled at the "
                    f"props polling cadence, so this is a sampling limit, not a missing measurement."
                )
            else:
                notes.append(
                    f"{r['strategy']}: survival n/a -- only {int(r['n_survival'])} leg(s) inside the horizon, "
                    f"below the {MIN_SURVIVAL_N} needed to report a rate."
                )
    if notes:
        lines += ["", "notes:"] + [f"  - {n}" for n in notes]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    store = PointInTimeStore(root="data/snapshots")
    print(format_table(decision_table(store)))
    sealed = sum(o.is_alert and withheld(o.strategy, o.event_id) for o in load(SHADOW_LOG_PATH))
    if sealed:
        print(f"  - {sealed} moneyline_ev alert(s) in Weeks 10-14 are withheld until "
              f"{WK10_14_OPENS:%Y-%m-%d} (H5 holdout, preregistration_wk10-14.md); survival still counts them.")


if __name__ == "__main__":
    main()
