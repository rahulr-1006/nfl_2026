"""Collector configuration.

Everything The Odds API's free-tier budget forces us to make a decision
about is env-configurable; the rest (sport key, cadence numbers taken
straight from the blueprint, file locations) is hardcoded. This is a
single-provider personal project, not a framework — no plugin config.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class Config:
    api_key: str
    sport_key: str = "americanfootball_nfl"
    # "eu" alone gets Pinnacle (the CLV anchor); "us" is DraftKings/FanDuel/BetMGM,
    # the actual bet-execution books (paper Sec 3.4) -- src/signal/live_scan.py
    # needs both regions to compare a live execution-book price against
    # Pinnacle's fair value. This doubles per-poll credit cost (regions x
    # markets); added 2026-08-17 once that comparison became load-bearing.
    regions: str = "eu,us"
    markets: str = "h2h,spreads,totals"
    reduced_markets: str = "spreads,totals"  # budget-tight fallback: drop moneyline first
    odds_format: str = "american"
    season: int = 2026
    monthly_budget: int = 500
    safety_reserve_credits: int = 20
    dense_window_hours: float = 48.0
    dense_interval_minutes: float = 30.0
    sparse_interval_minutes: float = 60.0
    min_interval_minutes: float = 15.0
    tick_minutes: float = 5.0
    budget_period_days: int = 30
    budget_period_anchor: date | None = None
    # "rolling" (roll the anchor forward by budget_period_days) or
    # "calendar_month" (refill at 00:00 UTC on the 1st). The paid key bills
    # on the calendar month; the free key's anchor is arbitrary. See
    # `src/collect/budget.py::current_period_end`.
    budget_period_mode: str = "rolling"
    max_consecutive_failures: int = 20
    request_timeout_seconds: float = 15.0
    store_root: Path = Path("data/snapshots")
    schedule_path: Path | None = None
    state_path: Path = Path("data/collect_state.json")

    @property
    def resolved_schedule_path(self) -> Path:
        if self.schedule_path is not None:
            return self.schedule_path
        return Path("data/static") / f"schedules_{self.season}_{self.season}.parquet"


def load_config(env: Mapping[str, str] | None = None) -> Config:
    """Build a Config from environment variables (or an injected mapping for tests).

    Does not call load_dotenv() itself, so it stays a pure function of its
    input — callers that want .env support (src/collect/run.py) load the
    .env file once before calling this.
    """
    src = env if env is not None else os.environ

    # COLLECT_USE_PAID_KEY moves the MAINLINE collector onto ODDS_API_KEY_PAID
    # (2026-09-08). The two keys are separate credit pools: the free key is
    # 500/month, the paid key 100,000/month RECURRING (it refills on the 1st;
    # see `budget.py::current_period_end`, which documents the log evidence).
    # The mainline collector was starving on the free key -- 206 credits left,
    # a 3.4h poll cadence 34 hours before Week 1 -- while ~97,800 paid credits
    # sat unused. At 6 credits/poll a true 30-minute cadence costs ~8.6K/month,
    # which the paid pool absorbs comfortably alongside props polling.
    use_paid_key = src.get("COLLECT_USE_PAID_KEY", "").strip().lower() in {"1", "true", "yes"}
    key_name = "ODDS_API_KEY_PAID" if use_paid_key else "ODDS_API_KEY"
    api_key = src.get(key_name)
    if not api_key:
        raise ValueError(f"{key_name} is not set (add it to .env or the environment)")

    anchor_str = src.get("COLLECT_BUDGET_PERIOD_ANCHOR")
    anchor = date.fromisoformat(anchor_str) if anchor_str else None

    default_budget = "100000" if use_paid_key else "500"
    default_mode = "calendar_month" if use_paid_key else "rolling"

    return Config(
        api_key=api_key,
        regions=src.get("ODDS_API_REGIONS", "eu,us"),
        markets=src.get("ODDS_API_MARKETS", "h2h,spreads,totals"),
        season=int(src.get("COLLECT_SEASON", "2026")),
        monthly_budget=int(src.get("ODDS_API_MONTHLY_BUDGET", default_budget)),
        safety_reserve_credits=int(src.get("COLLECT_SAFETY_RESERVE_CREDITS", "20")),
        dense_interval_minutes=float(src.get("COLLECT_DENSE_INTERVAL_MINUTES", "30")),
        tick_minutes=float(src.get("COLLECT_TICK_MINUTES", "5")),
        budget_period_anchor=anchor,
        budget_period_mode=src.get("COLLECT_BUDGET_PERIOD_MODE", default_mode),
    )
