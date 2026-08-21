from pathlib import Path

import pandas as pd

from src.features.load_static import PBP_COLUMNS, home_spread_line
from src.store.schema import Market, Side
from src.store.settlement import build_results_index, settle

SCHEDULE_PATH = Path("data/static/schedules_2015_2025.parquet")
PBP_PATH = Path("data/static/pbp_2015_2025.parquet")


def test_home_spread_line_negates():
    assert home_spread_line(7.5) == -7.5
    assert home_spread_line(-3.0) == 3.0


def test_home_spread_line_sign_convention_matches_an_efficient_market():
    """Regression guard for the sign-convention bug: feeding nflverse's raw
    spread_line into settle() without negating it produced a 58.9% home-ATS
    "win rate" against 2015-2024 closing lines -- impossible in a real
    spread market. Using home_spread_line() must land close to 50%.
    """
    schedule = pd.read_parquet(SCHEDULE_PATH)
    results = build_results_index(schedule)
    sub = schedule.dropna(subset=["home_score", "away_score", "spread_line"])

    wins = losses = pushes = 0
    for row in sub.itertuples():
        outcome = settle(Market.SPREAD, Side.HOME, home_spread_line(row.spread_line), results[row.game_id])
        if outcome.value == "win":
            wins += 1
        elif outcome.value == "loss":
            losses += 1
        else:
            pushes += 1

    total = wins + losses + pushes
    assert total > 2000  # sanity: the fixture actually loaded real games
    win_rate = wins / (wins + losses)
    assert 0.45 < win_rate < 0.55, f"home ATS win rate {win_rate:.4f} is not efficient-market-plausible"
    assert 0 < pushes / total < 0.05  # spreads land on 3/7 often enough to push a few percent of the time


def test_cached_pbp_matches_trimmed_schema_and_covers_the_cached_seasons():
    """Regression guard for the trimmed-schema cache: src/model/features.py
    depends on exactly PBP_COLUMNS existing, so a schema drift here would
    silently break the feature builder rather than fail loudly.
    """
    pbp = pd.read_parquet(PBP_PATH)
    assert list(pbp.columns) == PBP_COLUMNS
    assert set(pbp["season"].unique()) == set(range(2015, 2026))
    assert len(pbp) > 400_000  # sanity: ten seasons of real plays, not an empty/partial pull
