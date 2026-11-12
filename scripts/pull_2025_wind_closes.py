"""Buy real 2025 closing totals for H8's qualifying games only (spends credits).

`src/collect/mainline_historical.py` refuses 2025 on purpose: it was the
untouched holdout. H8 is the pre-registered use of it
(`docs/preregistration_2025_market_bias.md`), so this narrow pull exists instead
of loosening that guard. It buys exactly one near-kickoff snapshot of the totals
market, us+eu (eu is where Pinnacle lives), for 2025 regular-season outdoor /
open-roof games with wind >= the frozen threshold. Prices only: nothing here
reads a score.

    .venv/bin/python -m scripts.pull_2025_wind_closes            # estimate only
    .venv/bin/python -m scripts.pull_2025_wind_closes --spend    # real credits
"""

from __future__ import annotations

import argparse
import logging
import os

import pandas as pd
from dotenv import load_dotenv

from src.backtest.market_bias import HOLDOUT_SEASON, OUTDOOR_ROOFS
from src.clv.prereg_score_2025 import H8_WIND
from src.collect.client import OddsApiClient
from src.collect.mainline_historical import backfill_historical_mainline, estimate_pull_cost
from src.collect.teams import load_team_name_map
from src.collect.transform import MatchResult
from src.features.load_static import STATIC_DIR, kickoffs_utc
from src.store.pit_store import PointInTimeStore

SCHEDULE = STATIC_DIR / "schedules_2015_2025.parquet"
# 2024's purchased closes sit 0.24-0.66h before kickoff; 0.4h is the middle.
CLOSE_OFFSET_HOURS = (0.4,)
MARKETS = "totals"
REGIONS = "us,eu"
MAX_CREDITS = 1500

log = logging.getLogger(__name__)


def qualifying_games() -> pd.DataFrame:
    cols = ["game_id", "season", "week", "game_type", "gameday", "gametime", "home_team", "away_team", "roof", "wind"]
    s = pd.read_parquet(SCHEDULE, columns=cols)
    s = s[(s["season"] == HOLDOUT_SEASON) & (s["game_type"] == "REG") & s["roof"].isin(OUTDOOR_ROOFS)
          & (s["wind"] >= H8_WIND)].copy()
    s["kickoff"] = kickoffs_utc(s)
    return s


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--spend", action="store_true", help="actually buy the snapshots")
    a = ap.parse_args()

    games = qualifying_games()
    names = {abbr: name for name, abbr in load_team_name_map(HOLDOUT_SEASON, SCHEDULE).items()}
    plan = []
    for g in games.itertuples():
        home, away = names.get(g.home_team), names.get(g.away_team)
        if not home or not away:
            log.warning("no Odds API name for %s/%s -- skipping %s", g.home_team, g.away_team, g.game_id)
            continue
        match = MatchResult(event_id=g.game_id, season=HOLDOUT_SEASON, week=int(g.week),
                            home_abbr=g.home_team, away_abbr=g.away_team)
        plan.append((match, home, away, g.kickoff.to_pydatetime()))

    estimate = estimate_pull_cost(len(plan), MARKETS, REGIONS, CLOSE_OFFSET_HOURS)
    log.info("PLAN: %d games, %r over %r at T-%sh -> ~%d credits (cap %d)",
             len(plan), MARKETS, REGIONS, CLOSE_OFFSET_HOURS[0], estimate, MAX_CREDITS)
    if not a.spend:
        log.info("estimate only -- pass --spend to buy")
        return

    load_dotenv()
    key = os.environ.get("ODDS_API_KEY_PAID")
    if not key:
        raise ValueError("ODDS_API_KEY_PAID is not set")
    result = backfill_historical_mainline(OddsApiClient(key), plan, PointInTimeStore(), markets=MARKETS,
                                          regions=REGIONS, offsets_hours=CLOSE_OFFSET_HOURS, max_credits=MAX_CREDITS)
    log.info("RESULT: %s", result)


if __name__ == "__main__":
    main()
