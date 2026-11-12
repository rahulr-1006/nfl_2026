# Pre-registration — H8, wind unders on the 2025 season

**Status: FINAL (committed 2026-11-11).** The scorer (`make prereg-score-2025`,
`src/clv/prereg_score_2025.py`) refuses to run until this line reads FINAL. It is
set to FINAL in the commit that freezes this document, and that commit's
timestamp is the evidence the rule came first.

**This uses up the 2025 holdout.** 2025 had been untouched since the 2026-08-21
data refresh. After this, the project has no unused completed season.

---

## 1. Source and mechanism

Borghesi (2008, *Applied Financial Economics*), 1984–2004: the NFL totals market
underweights adverse weather, and a weather-aware under strategy beat the 52.38%
break-even out of sample. A 2026 trade-press piece (startuphub.ai) points
specifically at 10–15 mph wind, with no numbers.

This repo's earlier weather result is not the same test. That one added wind as a
feature to an outcome model and scored Brier. H8 tests the market line directly,
at its real price.

## 2. Data

- **Selection:** nflverse `schedules_2015_2025.parquet`, regular season,
  `roof` in {outdoors, open}, `wind` ≥ W.
- **Development:** 2015–2024.
- **Holdout:** 2025. 49 games qualify at W = 10. That count was taken from wind
  and roof only, with no scores read.
- **Holdout prices:** Pinnacle's real closing total, bought for exactly those 49
  games by `scripts/pull_2025_wind_closes.py`. One snapshot at T−0.4h, totals, us+eu,
  about 1,029 credits. Bought after this commit.

## 3. Exploration already done (disclosed)

`make market-bias-dev` (`scripts/market_bias_dev.py`) reproduces these exactly.
Results are on nflverse closing lines, pushes excluded.

| Rule | n | ROI [95% CI] | Seasons + | Gate |
|---|---|---|---|---|
| H7: away when market home p ∈ [0.30, 0.70] | 1,727 | +0.17% [−4.80, +5.28] | 5/10 | **FAIL**, not scored on 2025 |
| H8: under, wind ≥ 10 | 587 | +13.54% [+5.71, +21.17] | 8/10 | pass |
| H8: under, wind ≥ 15 | 195 | +7.48% [−5.84, +21.24] | 6/10 | pass |

**W = 10 is frozen.** It came from the declared grid {10, 15}, chosen for the
larger sample and the stronger pooled result.

Checks run after seeing the H8 result, disclosed so they can be weighed:

- **All unders break even (+0.05%, n=2,596), and domes lose (−4.1%).** This is not
  a general under bias in the data.
- **By wind bucket (outdoor unders):**
  - [0,5) −2.2%, [5,8) −12.1%, [8,10) −2.2%;
  - [10,12) +14.3%, [12,15) +18.8%, [15,20) +11.0%;
  - 20+ −5.6% (n=41).
  - The effect is concentrated at moderate wind. Each bucket has an SE of roughly
    6–7 points, so the bucket-to-bucket shape is noisy.
- **Against real Pinnacle closes** (2023, 2024 and 2026 Weeks 1–9, the only seasons
  bought):
  - Windy unders: +5.4% on 116 games. 2023 +31.1% (n=49), 2024 −15.6% (n=55),
    2026 −3.3% (n=12).
  - nflverse's total line matches Pinnacle's on average (mean difference +0.01),
    but differs by ≥ 0.5 points in 48% of games.
  - **The real-price evidence is much weaker than the nflverse evidence and rests
    on one season.**

**Known look-ahead:** nflverse `wind` is the reading at kickoff, not the forecast
a bettor had. The close is also set at kickoff, so the gap is small. Some of the
effect could still be wind that wasn't forecast, which no bettor could have used.
That can't be separated with this data.

## 4. Hypothesis H8 · CONFIRMATORY

- **Bet:** the under at Pinnacle's closing total (its own line and price), in
  each 2025 game selected in §2.
- **Exclusions:** no two-sided Pinnacle total with matching lines, or a close more
  than 3h before kickoff. Both are counted.
- **Pushes:** refunded. Counted and dropped from ROI and the null.

**Pass bar (all required):**
1. n ≥ 30 graded bets.
2. ROI > 0.
3. 95% game-bootstrap CI lower bound > 0 (10,000 resamples, seed 0).
4. Beats the random-side null at p < 0.05: `evaluation.random_bet_benchmark`, with
   the over at its real Pinnacle price.
5. BH q = 0.05 across the family. The family is {H8}, because H7 failed
   development, so this reduces to p < 0.05.

**Power, stated in advance:** about 45 graded bets at roughly −105 give a ROI
standard error near 14.5 points. Only an observed ROI of about +28% or more can pass. The
development effect at real prices (+5%) would almost certainly FAIL. **A FAIL
here means "not confirmed", not "disproven."**

**Reported, not gated:**
- the best execution-book under at Pinnacle's line;
- ROI at nflverse's line (the development source);
- hit rate.

## 5. What this does not settle

- Whether a bettor using the *forecast* could capture any of this. That needs
  historical weather forecasts (e.g. archived forecast APIs from 2022 on), and
  goes in the backlog.
- Live 2026 use. Weeks 10–18 windy games are not part of this test.

## 6. Deviations log

| Date | Change | Reason | Changes bets? |
|---|---|---|---|
| 2026-11-11 | **Result of record: H8 FAIL.** 2025 closes bought after the FINAL commit (`4b16d0d`): 49/49 games, 1,029 credits. Scored once with `make prereg-score-2025`. At Pinnacle's close: n=48 (+1 push), ROI +4.44% [−23.70%, +31.94%], p=0.354, hit 54.2%. Random-side null −2.73%, p=0.327. Conditions 1–2 pass; 3–5 fail. Reported only: best execution book at Pinnacle's line +3.93% (n=37); nflverse line +1.22% (n=49). The point estimate matches the development estimate at real prices (+5.4%), and the test had the power stated in §4. That makes this "not confirmed", not "disproven". 2025 is now spent. | Recording the result. | No |
