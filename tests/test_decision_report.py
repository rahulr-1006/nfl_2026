"""The verdict logic is the part that decides where real money goes, so it is
pinned harder than the formatting.

Three properties matter most, and each corresponds to a mistake this project has
already made or nearly made:
  1. `prop_arb` is NOT scored on CLV -- doing so retires a market-neutral edge for
     a mathematically guaranteed reason.
  2. A survival number computed at a 4-hour horizon is never labelled as latency.
  3. `None` and `NaN` render identically, so an absent measurement cannot read as
     a computed one.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from src.clv.decision_report import (
    DEFAULT_HORIZON_MINUTES,
    MIN_N,
    MIN_SURVIVAL_N,
    STRUCTURAL_STRATEGIES,
    VERDICT_GO,
    VERDICT_NO,
    _directional_verdict,
    _missing,
    _pct,
    _structural_verdict,
    ci_includes_zero,
    first_recheck_frame,
    format_table,
    structural_capture,
    survival_at_horizon,
)
from src.signal.shadow_log import ShadowObservation, append
from src.store.schema import Market, Side

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


def _obs(alert_key, leg, strategy, price, *, is_alert, minutes, edge=0.01):
    return ShadowObservation(
        alert_key=alert_key,
        leg=leg,
        strategy=strategy,
        event_id="2026_02_DET_BUF",
        market=Market.MONEYLINE,
        side=Side.HOME,
        book="fanduel",
        price_american=price,
        edge=edge,
        alerted_at=NOW,
        observed_at=NOW + timedelta(minutes=minutes),
        capture_time=NOW + timedelta(minutes=minutes),
        is_alert=is_alert,
    )


# --- the bar itself -----------------------------------------------------------

def test_directional_needs_both_halves_of_the_bar():
    assert _directional_verdict(MIN_N, 0.6, 0.01) == VERDICT_GO
    assert _directional_verdict(MIN_N, 0.6, -0.01) == VERDICT_NO  # beat but negative CLV
    assert _directional_verdict(MIN_N, 0.4, 0.01) == VERDICT_NO  # positive CLV, loses more often
    assert _directional_verdict(MIN_N, 0.50, 0.01) == VERDICT_NO  # strictly greater than


def test_below_min_n_is_hold_not_no():
    """A small sample is not evidence of failure. Collapsing HOLD into NO would
    retire a strategy for having little data rather than for losing.
    """
    v = _directional_verdict(MIN_N - 1, 0.1, -0.05)
    assert v.startswith("HOLD")
    assert str(MIN_N) in v


def test_the_bar_constants_are_the_ones_agreed_before_the_data():
    """Pinned so a later session cannot quietly tune the bar to whatever the
    season produced -- the whole point of pre-registering it.
    """
    assert MIN_N == 30


# --- prop_arb must not be scored on CLV ---------------------------------------

def test_prop_arb_is_routed_to_the_structural_test():
    assert "prop_arb" in STRUCTURAL_STRATEGIES


def test_structural_verdict_ignores_clv_entirely():
    """The regression that matters: an arb with terrible CLV but a capturable
    lock must still pass. CLV is not an input here at all.
    """
    cap = {"n_alerts": MIN_N, "expected_capture": 0.004,
           "both_legs_rate": 0.4, "one_leg_only_rate": 0.1, "mean_margin": 0.01}
    assert _structural_verdict(cap) == VERDICT_GO
    assert _structural_verdict({**cap, "expected_capture": -0.001}) == VERDICT_NO


def test_structural_capture_needs_both_legs_not_either():
    """An arb with one leg gone is not a partial win, it is naked exposure."""
    rows = []
    for i in range(MIN_SURVIVAL_N + 1):
        rows += [
            _obs(f"arb{i}", "over", "prop_arb", 120, is_alert=True, minutes=0),
            _obs(f"arb{i}", "under", "prop_arb", -110, is_alert=True, minutes=0),
            # over holds, under does not -> exactly one leg
            _obs(f"arb{i}", "over", "prop_arb", 130, is_alert=False, minutes=10),
            _obs(f"arb{i}", "under", "prop_arb", -200, is_alert=False, minutes=10),
        ]
    legs = first_recheck_frame_from(rows)
    cap = structural_capture(legs, "prop_arb")
    assert cap["both_legs_rate"] == 0.0
    assert cap["one_leg_only_rate"] == 1.0


def test_structural_capture_is_unreported_below_min_survival_n():
    """Two alerts cannot support a rate. Reporting one would turn coin flips into
    a finding about naked exposure.
    """
    rows = []
    for i in range(2):
        rows += [
            _obs(f"arb{i}", "over", "prop_arb", 120, is_alert=True, minutes=0),
            _obs(f"arb{i}", "under", "prop_arb", -110, is_alert=True, minutes=0),
            _obs(f"arb{i}", "over", "prop_arb", 100, is_alert=False, minutes=10),
            _obs(f"arb{i}", "under", "prop_arb", -200, is_alert=False, minutes=10),
        ]
    cap = structural_capture(first_recheck_frame_from(rows), "prop_arb")
    assert cap["both_legs_rate"] is None
    assert cap["n_alerts"] == 2


# --- the horizon trap ---------------------------------------------------------

def test_a_four_hour_recheck_never_counts_as_survival():
    """The bug this module exists to prevent: props outside the final 12h are
    first re-observed ~240 min later, and that number must not be presented as a
    detection-latency survival rate.
    """
    rows = []
    for i in range(MIN_SURVIVAL_N + 5):
        rows += [
            _obs(f"ev{i}", "single", "prop_ev", 120, is_alert=True, minutes=0),
            _obs(f"ev{i}", "single", "prop_ev", 130, is_alert=False, minutes=240),
        ]
    legs = first_recheck_frame_from(rows)
    rate, n_in, median = survival_at_horizon(legs, "prop_ev")
    assert rate is None, "a 240-minute observation must not produce a survival rate"
    assert n_in == 0
    assert median == pytest.approx(240.0)


def test_survival_uses_the_first_recheck_not_the_last():
    """`survival_report` answers a 6-hour question. Reusing it here is what made
    prop arb look like 0% survival on 2026-09-14.
    """
    rows = []
    for i in range(MIN_SURVIVAL_N + 1):
        rows += [
            _obs(f"ml{i}", "single", "moneyline_ev", 100, is_alert=True, minutes=0),
            _obs(f"ml{i}", "single", "moneyline_ev", 120, is_alert=False, minutes=10),   # held
            _obs(f"ml{i}", "single", "moneyline_ev", -200, is_alert=False, minutes=300),  # gone later
        ]
    rate, _, _ = survival_at_horizon(first_recheck_frame_from(rows), "moneyline_ev")
    assert rate == 1.0


def test_survival_compares_payouts_not_american_odds():
    """-105 beats -120 but loses to +100; a numeric >= on American odds is wrong."""
    rows = []
    for i in range(MIN_SURVIVAL_N + 1):
        rows += [
            _obs(f"x{i}", "single", "steam", -120, is_alert=True, minutes=0),
            _obs(f"x{i}", "single", "steam", -105, is_alert=False, minutes=5),
        ]
    rate, _, _ = survival_at_horizon(first_recheck_frame_from(rows), "steam")
    assert rate == 1.0, "-105 is a better payout than -120, so the price held"


def test_horizon_default_covers_the_real_alert_path():
    """0.25h poll spacing + 300s monitor interval = ~20 min worst case; the
    default must leave room for one missed poll without voiding the observation.
    """
    assert DEFAULT_HORIZON_MINUTES >= 20.0


# --- rendering ----------------------------------------------------------------

def test_none_and_nan_render_identically():
    """A NaN leaking through as "nan%" reads like a computed value."""
    assert _pct(None).strip() == "n/a"
    assert _pct(float("nan")).strip() == "n/a"
    assert _missing(pd.NA) and _missing(None) and _missing(float("nan"))
    assert not _missing(0.0)


def test_empty_table_says_so_instead_of_crashing():
    assert "no alerts" in format_table(pd.DataFrame())


def test_structural_row_is_marked_and_explained():
    table = pd.DataFrame([{
        "strategy": "prop_arb", "scored_as": "structural", "n": 40,
        "beat_rate": 0.41, "mean_clv": -0.0000, "clv_ci_lo": -0.01, "clv_ci_hi": 0.01,
        "survival": None, "n_survival": 0, "median_min_to_first": 240.0,
        "both_legs_rate": 0.3, "one_leg_only_rate": 0.2, "expected_capture": 0.003,
        "verdict": VERDICT_GO,
    }])
    out = format_table(table)
    assert "prop_arb*" in out
    assert "CAPTURABILITY" in out
    assert "NAKED EXPOSURE" in out
    assert "sampling limit" in out, "an n/a survival must explain itself"


# --- helper -------------------------------------------------------------------

def first_recheck_frame_from(rows, tmp=None):
    """Round-trip through the real append/load path rather than constructing the
    frame directly -- a test that builds its own input validates the
    implementation instead of the workflow, which has burned this repo before
    (the `corrects` string-mismatch bug).
    """
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "shadow.jsonl"
        append(rows, p)
        return first_recheck_frame(p)


# --- the CI disclosure added 2026-09-21 ---------------------------------------

def test_ci_including_zero_is_disclosed_but_does_not_change_the_verdict():
    """`moneyline_ev` cleared the bar on 2026-09-21 with mean_clv +0.0053 and a CI
    of [-0.0006, +0.0112]. The verdict must stay GO -- silently tightening a
    pre-registered bar after seeing data is the failure pre-registration exists to
    prevent -- but the reader must be told.
    """
    table = pd.DataFrame([{
        "strategy": "moneyline_ev", "scored_as": "directional", "n": 47,
        "beat_rate": 0.66, "mean_clv": 0.0053, "clv_ci_lo": -0.0006, "clv_ci_hi": 0.0112,
        "survival": 0.762, "n_survival": 21, "median_min_to_first": 35.0,
        "both_legs_rate": None, "one_leg_only_rate": None, "expected_capture": None,
        "verdict": VERDICT_GO,
    }])
    out = format_table(table)
    assert "GO" in out
    assert "INCLUDES ZERO" in out
    assert "NOT being changed" in out


def test_ci_excluding_zero_gets_no_such_warning():
    table = pd.DataFrame([{
        "strategy": "moneyline_ev", "scored_as": "directional", "n": 47,
        "beat_rate": 0.66, "mean_clv": 0.02, "clv_ci_lo": 0.011, "clv_ci_hi": 0.030,
        "survival": 0.762, "n_survival": 21, "median_min_to_first": 35.0,
        "both_legs_rate": None, "one_leg_only_rate": None, "expected_capture": None,
        "verdict": VERDICT_GO,
    }])
    assert "INCLUDES ZERO" not in format_table(table)


def test_ci_includes_zero_handles_missing_bounds():
    assert not ci_includes_zero(None, None)
    assert not ci_includes_zero(float("nan"), 0.01)
    assert ci_includes_zero(-0.01, 0.01)
    assert not ci_includes_zero(0.001, 0.01)
