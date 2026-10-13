"""H1 (preregistration_wk5-9.md): stale soft-book prop lines after a Pinnacle move.

**The mechanism.** Pinnacle re-prices a prop; the execution books have not caught
up yet. Pinnacle's own move is the information -- there is no probability model
here -- and the bet is the slow book's price on the side Pinnacle moved toward.

**How this differs from `steam.py` (a NO on 2026-10-04).** Steam is mainline, needs
several books moving together inside an hour, and prices off line moves through a
normal-margin model. This is props, triggered by Pinnacle alone, and priced
directly against Pinnacle's new devigged probability.

**Scored on closing EV, not `clv_probability`.** `clv_probability` compares
Pinnacle's close with Pinnacle's entry fair and never sees the price paid. These
bets are placed *after* Pinnacle moved, so it would only measure whether Pinnacle
kept moving and score a +EV stale price at ~0 by construction. `close_ev` values
the price actually taken at Pinnacle's close; `clv_probability` is kept as the
adverse-selection measure. Pinnacle's prop close passed a calibration check on
15,837 historical contracts (2026-10-04) -- that is what licenses the yardstick.

**No look-ahead.** A bet only uses quotes captured at the trigger's own
capture_time, and its close is the last Pinnacle pair before kickoff. Callers pass
pre-kickoff rows only; `pinnacle_fair_path` refuses anything else.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from src.backtest.props_ev_backtest import EXECUTION_BOOKS
from src.devig.convert import american_to_implied_prob
from src.devig.methods import DEVIG_METHODS

CONTRACT = ["event_id", "player_name", "prop_stat", "line"]
DEFAULT_MAX_GAP = pd.Timedelta(minutes=20)  # two consecutive 15-min polls plus jitter
DEFAULT_REVERSAL_TOLERANCE = 0.01
# Frozen in preregistration_wk5-9.md: triggers only in the final 12h. On Train this
# held by polling cadence alone (<=20-min-apart Pinnacle pairs only exist in the
# 15-min tier), so it changed nothing measured -- enforcing it here keeps the rule
# true if the polling schedule ever changes.
DEFAULT_WINDOW_HOURS = 12.0


def pinnacle_fair_path(props: pd.DataFrame, devig_method: str = "shin") -> pd.DataFrame:
    """Pinnacle's devigged over-probability for every contract at every capture
    where BOTH sides were quoted. One row per (contract, capture_time)."""
    if (props["capture_time"] >= props["event_start_time"]).any():
        raise ValueError("pinnacle_fair_path takes pre-kickoff rows only")
    pin = props[props["book"] == "pinnacle"]
    if pin.empty:
        return pd.DataFrame(columns=[*CONTRACT, "capture_time", "event_start_time", "fair_over"])
    wide = (
        pin.pivot_table(index=[*CONTRACT, "capture_time", "event_start_time"], columns="side",
                        values="price_american", aggfunc="last")
        .reset_index()
    )
    if not {"over", "under"}.issubset(wide.columns):
        return pd.DataFrame(columns=[*CONTRACT, "capture_time", "event_start_time", "fair_over"])
    wide = wide.dropna(subset=["over", "under"])
    devig = DEVIG_METHODS[devig_method]
    raw = np.column_stack([
        wide["over"].map(american_to_implied_prob).to_numpy(),
        wide["under"].map(american_to_implied_prob).to_numpy(),
    ])
    wide["fair_over"] = [devig(list(r)).probabilities[0] for r in raw]
    return wide[[*CONTRACT, "capture_time", "event_start_time", "fair_over"]].sort_values([*CONTRACT, "capture_time"])


def detect_moves(
    path: pd.DataFrame,
    min_move: float,
    max_gap: pd.Timedelta = DEFAULT_MAX_GAP,
    window_hours: float = DEFAULT_WINDOW_HOURS,
) -> pd.DataFrame:
    """Consecutive Pinnacle captures of one contract, at most `max_gap` apart,
    whose fair over-probability changed by at least `min_move`, with the trigger
    capture inside the final `window_hours` before kickoff. `side` is the side
    Pinnacle moved toward."""
    p = path.sort_values([*CONTRACT, "capture_time"]).copy()
    grp = p.groupby(CONTRACT, sort=False)
    p["prev_fair"] = grp["fair_over"].shift()
    p["prev_time"] = grp["capture_time"].shift()
    p["move"] = p["fair_over"] - p["prev_fair"]
    in_window = (p["event_start_time"] - p["capture_time"]) <= pd.Timedelta(hours=window_hours)
    keep = (p["prev_fair"].notna() & ((p["capture_time"] - p["prev_time"]) <= max_gap)
            & (p["move"].abs() >= min_move) & in_window)
    moves = p[keep].copy()
    moves["side"] = np.where(moves["move"] > 0, "over", "under")
    return moves.reset_index(drop=True)


def stale_quotes(
    moves: pd.DataFrame,
    props: pd.DataFrame,
    min_ev: float,
    books: Sequence[str] = EXECUTION_BOOKS,
) -> pd.DataFrame:
    """For each move, the best execution-book price on the moved-toward side at
    the SAME capture and SAME line, kept if its EV against Pinnacle's new fair is
    at least `min_ev`. At most one bet per (contract, side): the first trigger."""
    soft = props[props["book"].isin(books)][[*CONTRACT, "capture_time", "book", "side", "price_american", "price_decimal"]]
    m = moves.merge(soft, on=[*CONTRACT, "capture_time", "side"], how="inner")
    if m.empty:
        return m.assign(fair_side=[], entry_ev=[])
    m["fair_side"] = np.where(m["side"] == "over", m["fair_over"], 1 - m["fair_over"])
    m["entry_ev"] = m["fair_side"] * m["price_decimal"] - 1
    m = m[m["entry_ev"] >= min_ev]
    best = m.sort_values("price_decimal", ascending=False).drop_duplicates([*CONTRACT, "capture_time", "side"])
    first = best.sort_values("capture_time").drop_duplicates([*CONTRACT, "side"])
    return first.reset_index(drop=True)


def score(bets: pd.DataFrame, path: pd.DataFrame, tolerance: float = DEFAULT_REVERSAL_TOLERANCE) -> pd.DataFrame:
    """Attach Pinnacle's close and the H1 metrics to each bet.

    close_ev        price taken, valued at Pinnacle's close (primary metric)
    clv_probability Pinnacle close minus Pinnacle entry fair, for the bet's side
                    (adverse selection: did Pinnacle keep going or come back?)
    reverted        the close kept less than `tolerance` of the move's direction
    """
    close = path.sort_values("capture_time").groupby(CONTRACT, as_index=False).last()[[*CONTRACT, "fair_over"]]
    out = bets.merge(close.rename(columns={"fair_over": "close_over"}), on=CONTRACT, how="left")
    over = out["side"] == "over"
    out["close_side"] = np.where(over, out["close_over"], 1 - out["close_over"])
    out["close_ev"] = out["close_side"] * out["price_decimal"] - 1
    out["clv_probability"] = out["close_side"] - out["fair_side"]
    direction = np.sign(out["move"])
    out["reverted"] = (out["close_over"] - out["prev_fair"]) * direction <= tolerance
    return out


def survives_next_capture(bets: pd.DataFrame, props: pd.DataFrame, max_gap: pd.Timedelta = DEFAULT_MAX_GAP) -> pd.Series:
    """Was the same book still offering at least the bet's price at its next
    capture of that contract (within `max_gap`)? NaN if there was no next capture
    -- the placeability question, separate from whether the price was good."""
    later = props[[*CONTRACT, "book", "side", "capture_time", "price_decimal"]].rename(
        columns={"capture_time": "t_next", "price_decimal": "p_next"})
    j = bets.reset_index().merge(later, on=[*CONTRACT, "book", "side"], how="left")
    j = j[(j["t_next"] > j["capture_time"]) & (j["t_next"] <= j["capture_time"] + max_gap)]
    first = j.sort_values("t_next").drop_duplicates("index").set_index("index")
    result = pd.Series(np.nan, index=bets.index)
    result.loc[first.index] = (first["p_next"] >= first["price_decimal"]).astype(float)
    return result
