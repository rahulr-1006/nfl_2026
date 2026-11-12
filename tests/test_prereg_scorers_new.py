from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest

from src.clv import prereg_score_2025, prereg_score_opener
from src.clv.prereg_score import BlindedError


def test_opener_scorer_is_blinded_before_2027_01_12():
    with pytest.raises(BlindedError):
        prereg_score_opener.check_blind(datetime(2027, 1, 11, 12, tzinfo=UTC))
    prereg_score_opener.check_blind(datetime(2027, 1, 12, 6, tzinfo=UTC))


def test_2025_scorer_requires_final_status(tmp_path):
    doc = tmp_path / "prereg.md"
    doc.write_text("# x\n\n**Status: DRAFT (written 2026-11-11).** ...\n")
    with pytest.raises(BlindedError):
        prereg_score_2025.check_blind(doc)
    doc.write_text("# x\n\n**Status: FINAL (committed 2026-11-12).** ...\n")
    prereg_score_2025.check_blind(doc)


def test_2025_scorer_missing_doc_is_blinded(tmp_path):
    with pytest.raises(BlindedError):
        prereg_score_2025.check_blind(tmp_path / "nope.md")


def test_opener_verdict_passes_only_with_clear_positive_slope():
    rng = np.random.default_rng(0)
    d = rng.normal(0, 0.07, 120)
    strong = pd.DataFrame({"d": d, "m": 0.5 * d + rng.normal(0, 0.01, 120), "event_id": range(120)})
    noise = pd.DataFrame({"d": d, "m": rng.normal(0, 0.03, 120), "event_id": range(120)})
    small = strong.head(20)
    for f in (strong, noise, small):
        for col in ("p_early", "p_close", "best_home_price", "best_away_price", "home_score", "away_score"):
            f[col] = 0.5 if col.startswith("p_") else np.nan
    assert prereg_score_opener.verdict(strong)["verdict"] == "PASS"
    assert prereg_score_opener.verdict(noise)["verdict"] == "FAIL"
    assert not prereg_score_opener.verdict(small)["conditions"]["1_n_games"]
