"""Entrypoint: `python -m src.collect.run [--once]`.

`--once` does a single immediate poll and exits (used by `make
collect-once` for manual verification). Without it, does one immediate
poll for fast feedback, then hands off to the apscheduler loop.
"""

from __future__ import annotations

import logging
import sys

import pandas as pd
from dotenv import load_dotenv

from src.collect.client import OddsApiClient
from src.collect.config import Config, load_config
from src.collect.scheduler import CollectorContext, CollectorHalted, build_scheduler, tick
from src.collect.teams import load_team_name_map
from src.collect.transform import build_schedule_index
from src.features.load_static import load_schedules
from src.store.pit_store import PointInTimeStore

log = logging.getLogger(__name__)


def build_context(config: Config) -> CollectorContext:
    if not config.resolved_schedule_path.exists():
        load_schedules([config.season], out_dir=config.resolved_schedule_path.parent)

    schedule = pd.read_parquet(config.resolved_schedule_path)
    schedule = schedule[schedule["season"] == config.season]

    schedule_index = build_schedule_index(schedule)
    name_to_abbr = dict(load_team_name_map(config.season, config.resolved_schedule_path))
    upcoming_kickoffs = pd.to_datetime(schedule["gameday"].astype(str) + " " + schedule["gametime"].astype(str), utc=True).tolist()

    return CollectorContext(
        config=config,
        client=OddsApiClient(config.api_key, config.sport_key, config.request_timeout_seconds),
        store=PointInTimeStore(root=config.store_root),
        schedule_index=schedule_index,
        name_to_abbr=name_to_abbr,
        upcoming_kickoffs=upcoming_kickoffs,
    )


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    load_dotenv()
    config = load_config()
    ctx = build_context(config)

    tick(ctx)

    args = argv if argv is not None else sys.argv[1:]
    if "--once" in args:
        return

    try:
        build_scheduler(ctx).start()
    except CollectorHalted:
        log.critical("collector halted after too many consecutive failures", exc_info=True)
        raise


if __name__ == "__main__":
    main()
