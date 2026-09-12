"""Live adapters for the two LINE-MOVEMENT strategies: middling and steam.

`src/backtest/middling.py` and `src/backtest/steam.py` already find real
opportunities, and `middle_scan.py`/`steam_scan.py` already run them by hand.
This module is the thin layer that makes them safe to run UNATTENDED from
`src/notify/monitor_run.py`, which is what they were missing:

  1. **`upcoming_only`.** Neither backtest scanner filters out finished games,
     because neither was ever pointed at an alert channel. The point-in-time
     store holds the 2023-2024 historical backfill next to live collection, so
     an unfiltered scan alerts on games played two years ago -- the exact bug a
     2026-08-23 dry run caught in the props path (874 of 879 spots were on
     finished games). Hand-run scans get away with it because a human reads the
     event_id; an SMS channel does not.
  2. **An EV threshold.** The hand-run scripts default to `min_ev=0.0`, which
     for an unattended texter means "text me about every rounding error".
  3. **Dedup keys and message formatters**, so `monitor_run._alert_batch` can
     treat these like every other signal.

Both strategies are EXPERIMENTAL and labelled as such in the alert text, the
same treatment `props_scan.format_prop_ev_alert_message` gives the prop-EV
signal: they are priced by a model with no live track record, so they sort
BELOW arbitrage and moneyline EV in `monitor_run`'s confidence order.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from src.backtest.middling import find_middle_opportunities
from src.backtest.steam import find_steam_opportunities
from src.signal.live_scan import upcoming_only

# Both are EV per dollar staked, so they sit on the same scale as
# `live_scan.DEFAULT_EDGE_THRESHOLD` (2%) and are directly comparable to it.
# Middling's own report expresses EV in dollars on `total_risked`, so
# `find_live_middle_spots` normalises it to a rate before thresholding --
# otherwise the number would silently mean something different from every
# other `edge` column the monitor handles.
DEFAULT_MIDDLE_EV_THRESHOLD = 0.02
# Steam sits at 1.5% rather than middling's 2.0% deliberately (2026-09-08): the
# only live spot the fixed scanner has produced so far priced at 1.79%, and a
# strategy with zero live track record is worth more as a running experiment
# than as a silent one. This is a bar for OBSERVATION, not a claim that 1.5% is
# where steam becomes profitable -- alerts are labelled EXPERIMENTAL and the
# shadow log is what will eventually answer that.
DEFAULT_STEAM_EDGE_THRESHOLD = 0.015


def find_live_middle_spots(
    store,
    sigma_margin: float,
    sigma_total: float,
    threshold: float = DEFAULT_MIDDLE_EV_THRESHOLD,
    as_of: datetime | None = None,
) -> pd.DataFrame:
    """Bettable middles on games that have NOT kicked off yet, clearing
    `threshold` EV per dollar risked.
    """
    as_of = as_of or datetime.now(UTC)
    report = find_middle_opportunities(
        store, sigma_margin=sigma_margin, sigma_total=sigma_total, as_of=as_of
    )
    if report.empty:
        return report

    report = upcoming_only(report, as_of)
    if report.empty:
        return report

    # EV per dollar risked, not EV in dollars: `_alert_batch` compares this
    # against the previously alerted value to decide "improved", and a dollar
    # figure would make that comparison stake-dependent.
    report = report.assign(ev_rate=report["ev"] / report["total_risked"])
    return report[report["ev_rate"] >= threshold].reset_index(drop=True)


def find_live_steam_spots(
    store,
    sigma_margin: float,
    sigma_total: float,
    threshold: float = DEFAULT_STEAM_EDGE_THRESHOLD,
    as_of: datetime | None = None,
) -> pd.DataFrame:
    """Stale execution-book prices left behind by a synchronized multi-book
    move, on games that have not kicked off yet.
    """
    as_of = as_of or datetime.now(UTC)
    report = find_steam_opportunities(
        store, sigma_margin=sigma_margin, sigma_total=sigma_total, as_of=as_of
    )
    if report.empty:
        return report

    report = upcoming_only(report, as_of)
    if report.empty:
        return report

    return report[report["edge"] >= threshold].reset_index(drop=True)


def middle_alert_key(row: pd.Series) -> str:
    """Both legs are part of the identity: the same game can offer a different
    middle later at different books or a different window, and that is a new
    opportunity, not a re-alert of the old one.
    """
    return (
        f"mid|{row['event_id']}|{row['market']}|"
        f"{row['book_a']}|{row['side_a']}|{row['line_a']}|"
        f"{row['book_b']}|{row['side_b']}|{row['line_b']}"
    )


def steam_alert_key(row: pd.Series) -> str:
    """Keyed on the stale book AND its stale line -- once that book moves, the
    opportunity is gone, and a later stale price at a different number is a
    genuinely new spot.
    """
    return f"steam|{row['event_id']}|{row['market']}|{row['side']}|{row['stale_book']}|{row['stale_line']}"


def format_middle_alert_message(row: pd.Series) -> str:
    return (
        f"[EXPERIMENTAL] MIDDLE {row['ev_rate'] * 100:.1f}%: {row['away_team']} @ {row['home_team']} "
        f"{row['market']} | {str(row['book_a']).title()} {row['side_a']} {row['line_a']:g} "
        f"@{row['price_decimal_a']:.2f} + {str(row['book_b']).title()} {row['side_b']} {row['line_b']:g} "
        f"@{row['price_decimal_b']:.2f} -- both win in ({row['window_lo']:g}, {row['window_hi']:g}), "
        f"p={row['p_both_win']:.3f}, ${row['total_risked']:.2f} risked ({row['event_id']})"
    )


def format_steam_alert_message(row: pd.Series) -> str:
    return (
        f"[EXPERIMENTAL] STEAM {row['edge'] * 100:.1f}%: {row['away_team']} @ {row['home_team']} "
        f"{row['market']} {row['side'].upper()} -- {str(row['stale_book']).title()} still at "
        f"{row['stale_line']:g} after {int(row['n_books_moved'])} books moved "
        f"{row['steam_direction']:+.0f} (Pinnacle {row['mu']:g}). "
        f"Suggested stake ${row['suggested_stake']:.2f} ({row['event_id']})"
    )
