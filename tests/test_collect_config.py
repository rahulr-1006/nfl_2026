"""`load_config` key selection and budget-period defaults.

Untested before 2026-09-08, which is part of why the mainline collector sat on
the free key's 500/month pool -- starved to a 3.4h poll cadence 34 hours before
Week 1 -- while ~97,800 credits went unused on the paid key's recurring
100K/month pool.
"""

from src.collect.config import load_config

_MIN_ENV = {"ODDS_API_KEY": "free-key", "ODDS_API_KEY_PAID": "paid-key"}


def test_defaults_to_the_free_key_and_rolling_period():
    cfg = load_config(_MIN_ENV)
    assert cfg.api_key == "free-key"
    assert cfg.monthly_budget == 500
    assert cfg.budget_period_mode == "rolling"


def test_paid_key_opt_in_switches_key_budget_and_period_mode():
    cfg = load_config({**_MIN_ENV, "COLLECT_USE_PAID_KEY": "true"})
    assert cfg.api_key == "paid-key"
    assert cfg.monthly_budget == 100_000
    # The paid key refills on the 1st, not on a rolling 30-day anchor.
    assert cfg.budget_period_mode == "calendar_month"


def test_paid_key_opt_in_accepts_common_truthy_spellings():
    for value in ("1", "TRUE", " yes "):
        assert load_config({**_MIN_ENV, "COLLECT_USE_PAID_KEY": value}).api_key == "paid-key"


def test_non_truthy_values_stay_on_the_free_key():
    for value in ("", "0", "false", "no"):
        assert load_config({**_MIN_ENV, "COLLECT_USE_PAID_KEY": value}).api_key == "free-key"


def test_missing_paid_key_names_the_paid_variable_in_the_error():
    """The error must say which key is missing -- pointing at ODDS_API_KEY when
    the paid one is the one absent would send you editing the wrong line.
    """
    try:
        load_config({"ODDS_API_KEY": "free-key", "COLLECT_USE_PAID_KEY": "true"})
    except ValueError as exc:
        assert "ODDS_API_KEY_PAID" in str(exc)
    else:
        raise AssertionError("expected ValueError for a missing paid key")


def test_explicit_env_overrides_beat_the_paid_key_defaults():
    cfg = load_config({
        **_MIN_ENV,
        "COLLECT_USE_PAID_KEY": "true",
        "ODDS_API_MONTHLY_BUDGET": "5000",
        "COLLECT_BUDGET_PERIOD_MODE": "rolling",
        "COLLECT_DENSE_INTERVAL_MINUTES": "15",
    })
    assert cfg.monthly_budget == 5000
    assert cfg.budget_period_mode == "rolling"
    assert cfg.dense_interval_minutes == 15.0
