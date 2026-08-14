from pathlib import Path

import pandas as pd

from src.features.load_static import home_spread_line
from src.store.schema import Market, Side
from src.store.settlement import build_results_index, settle

SCHEDULE_PATH = Path("data/static/schedules_2015_2024.parquet")


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
