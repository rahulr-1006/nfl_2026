"""Entrypoint: `python -m src.collect.props_run [--once]`.

Live player-prop polling, separate process from the mainline collector
(`src/collect/run.py`) and on a **separate key** -- `ODDS_API_KEY_PAID`,
not `ODDS_API_KEY`. See `src/collect/props_budget.py`'s module docstring
for why: the mainline collector's dense pre-kickoff polling is the actual
CLV thesis and runs on the free tier's 500 credits/month; props polling
at real per-event cost, twice per game across ~16 games/week, would burn
through that same budget and starve the mainline collector right when it
matters most. The paid key has the headroom this needs without touching
the free tier's budget at all.

`--once` does a single immediate tick and exits (manual verification,
mirrors `make collect-once`). Without it, does one immediate tick for
fast feedback, then hands off to the apscheduler loop.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from src.collect.client import OddsApiClient
from src.collect.props import DEFAULT_MARKETS, DEFAULT_REGIONS
from src.collect.props_scheduler import (
    DEFAULT_STATE_PATH,
    DEFAULT_TICK_MINUTES,
    PropsCollectorContext,
    build_scheduler,
    tick,
)
from src.collect.teams import load_team_name_map
from src.collect.transform import build_schedule_index
from src.store.pit_store import PointInTimeStore

log = logging.getLogger(__name__)

DEFAULT_SEASON = 2026
DEFAULT_STORE_ROOT = Path("data/snapshots")  # same store the mainline collector and historical props backfill both write into


def build_context(season: int = DEFAULT_SEASON) -> PropsCollectorContext:
    api_key = os.environ.get("ODDS_API_KEY_PAID")
    if not api_key:
        raise ValueError("ODDS_API_KEY_PAID is not set (add it to .env) -- props polling uses the paid key, not ODDS_API_KEY")

    schedule_path = Path("data/static") / f"schedules_{season}_{season}.parquet"
    schedule = pd.read_parquet(schedule_path)
    schedule = schedule[schedule["season"] == season]

    schedule_index = build_schedule_index(schedule)
    name_to_abbr = dict(load_team_name_map(season, schedule_path))

    return PropsCollectorContext(
        season=season,
        client=OddsApiClient(api_key),
        store=PointInTimeStore(root=DEFAULT_STORE_ROOT),
        schedule_index=schedule_index,
        name_to_abbr=name_to_abbr,
        state_path=DEFAULT_STATE_PATH,
        regions=DEFAULT_REGIONS,
        markets=DEFAULT_MARKETS,
        tick_minutes=DEFAULT_TICK_MINUTES,
    )


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    load_dotenv()
    ctx = build_context()

    tick(ctx)

    args = argv if argv is not None else sys.argv[1:]
    if "--once" in args:
        return

    build_scheduler(ctx).start()


if __name__ == "__main__":
    main()
