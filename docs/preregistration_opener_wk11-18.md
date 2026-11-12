# Pre-registration — H6, Elo vs Pinnacle's early moneyline (2026 Weeks 11–18)

**Status: FINAL (committed 2026-11-11).** Deadline was **Sat 2026-11-14 20:15 ET**,
which is 120 hours before Week 11's first kickoff (`2026_11_IND_HOU`). A holdout
game's early price is defined at kickoff − 120h, so every holdout early price is
recorded after this commit.

**This is a research hypothesis, not a betting strategy.** Development already
shows the bettable version is negative-EV (§3). A pass would mean a public Elo
model carries information that Pinnacle's line 5 days out doesn't yet have, and
nothing more.

---

## 1. Question and mechanism

Pinnacle opens at low limits and lets sharp money move the line, so the close
is the early line plus whatever information arrived during the week. Costa
(2025, Claremont thesis) reports that NFL moneyline movement in the week before
kickoff is predictable. H6 asks a narrower question: when our Elo model disagrees
with Pinnacle at T−120h, does the close move toward the model?

Phase 3 (2026-08-23) couldn't ask this because the historical store had no early
prices. Two development samples have them now.

## 2. Data split

| Set | Games | Use |
|---|---|---|
| Elo calibration | 2015–2022 outcomes | Platt scaling of raw Elo probability |
| Development | 2024 (87 games with a T−120h quote), 2026 Weeks 1–9 (126) | design, disclosed in §3 |
| Excluded | 2026 Week 10 | its T−120h prices predate this commit |
| **Holdout** | **2026 Weeks 11–18** (122 scheduled) | scored **once**, on or after **Tue 2027-01-12** |

Scorer: `make prereg-score-opener`. It is `src/clv/prereg_score_opener.py`,
date-locked with no override flag.

**No peeking:** no β, `clv_move`, closing EV or realized ROI is computed on Weeks
11–18 before 2027-01-12. Operational checks (collector uptime, whether Pinnacle
quotes exist at T−120h) are allowed.

## 3. Development results (disclosed)

`make opener-dev` (`scripts/opener_dev.py`) reproduces these exactly.

| Sample | Games | β (m on d) [95% CI] | p (β ≤ 0) |
|---|---|---|---|
| 2024 | 87 | +0.014 [−0.074, +0.088] | 0.375 |
| 2026 Wk 1–9 | 126 | +0.050 [−0.006, +0.104] | 0.039 |
| Pooled | 213 | +0.036 [−0.010, +0.080] | 0.061 |

- **`clv_move` by τ:**
  - 2024: −0.79%, −0.47% and +0.61% at τ = 0.02, 0.03 and 0.05. None is significant.
  - 2026: +1.33%, +1.68% (p=0.022) and +1.38%.
- **The two samples agree in sign at only one τ (0.05).** Gating on that τ would
  mean picking the one setting where the data happens to agree. **That's why the
  gate is β, which has no τ.**
- **Bettable version:** the best execution-book price at T−120h, valued at
  Pinnacle's fair close, is **negative at every τ in both samples** (−0.5% to
  −2.9%). Even a real movement edge of about 1.5% doesn't cover soft-book vig 5
  days out.
- **Elo calibration:** Platt fit on 2015–2022 gives coefficient 0.954 and
  intercept −0.057. The 2023 reliability check is monotone with no gross
  miscalibration.

**Power, stated in advance.** If the pooled β of 0.036 is true, about 110
holdout games give a standard error near 0.028. A pass then needs β̂ above about
0.046, which has roughly a one-in-three chance. A FAIL is therefore weak evidence against H6. A PASS would be
notable.

## 4. Hypothesis H6 · CONFIRMATORY

**Definitions** (`src/backtest/opener_movement.py`, as of this commit):

- `t_early` = kickoff − 120h.
- `p_early` = Pinnacle's Shin-devigged home probability from its latest two-sided
  moneyline quote at or before `t_early`. The quote must be at most 24h older
  than `t_early`.
- `p_close` = the same at kickoff. The quote must be within 3h of kickoff.
- Games failing either rule are excluded and counted.
- `p_model` = team Elo with module defaults (K=20, home edge 48,
  reversion 1/3), computed **as of `t_early`**:
  - only games that finished by then count (game end = kickoff + 4h);
  - the result is Platt-calibrated as above.
- `d = p_model − p_early` and `m = p_close − p_early`.

**Statistic:** β = Σdm / Σd² (OLS of m on d, no intercept), with a 95% bootstrap
CI that resamples games (10,000 resamples, seed 0).

**Pass bar (all required):**
1. At least 30 holdout games after exclusions.
2. β > 0.
3. CI lower bound > 0 and one-sided bootstrap p < 0.05.

**Family:** {H6} alone, separate from H5's Weeks 10–14 family. Different data,
different question.

**Reported, not gated:**
- `clv_move` at τ = 0.03 with a game-level CI.
- Soft-book closing EV.
- Realized ROI.
- The momentum diagnostic (Moskowitz 2021): does m predict the outcome beyond the close?

## 5. What isn't tested

- Spreads and totals.
- Any feature beyond base Elo. EPA and QB Elo don't survive multiple-comparison
  correction in this repo.
- Any early anchor other than T−120h.

## 6. Deviations log

| Date | Change | Reason | Changes bets? |
|---|---|---|---|
