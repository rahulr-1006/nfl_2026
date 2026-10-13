# Train-phase results — 2026-10-04

Unattended run against `preregistration_wk5-9.md`. Every number here was
produced by code that ran in this session: scratchpad `run/s1–s4`,
`run/audit_rerun.py`, `run/audit2.py`. Anything not computed says so.
Reusable code: `src/backtest/pinnacle_lag.py` (+8 tests) and
`clv.metrics.clustered_bootstrap` (+4 tests); 993 tests pass, ruff clean.

**Hard checks (asserted in code, not eyeballed):**
- **2026 Train:** Weeks 1–4, quotes captured before kickoff, and only games that
  had kicked off when the run started (62 games; Week 4 SNF/MNF excluded).
- **Historical props:** every row pre-kickoff (median 20.3 min before).
- **Live shadow legs:** `week <= 4`.
- **Week 5+:** no data read.
- **Side effects:** zero API credits, no service changes, nothing committed.

**Conventions:**
- 95% CIs, bootstrapped by game unless stated.
- **UNDERPOWERED** = fewer than 30 bets or fewer than 15 games; never read as a trend.
- **Settlement match rates** are reported; unmatched rows are counted, then excluded.

---

## Bottom line

| Item | Result | Status |
|---|---|---|
| Gate: Pinnacle **prop** close calibrated | Pooled PASS; **rushing_yards FAIL** | Closing EV usable for props **except rushing yards** |
| Gate: Pinnacle **moneyline** close calibrated | Overall slope PASS; **short underdogs (fair 33–50%) FAIL** | Moneyline closing EV usable **only where the gate passed** |
| H1 stale line after Pinnacle move | Kill check PASS (8.3% reversal); close EV **+3.0% [+1.3, +4.5]**, 44 bets / 24 games | Recommend freeze M=2pp, E=1% |
| H1b soft ≥1% vs Pinnacle, first per contract | close EV **+1.55% [+1.12, +1.98]**, 211 bets / 47 games | Recommend registering |
| H3 prop middles | Calibration gate **FAIL** | Pre-reg rule says drop (your call) |
| moneyline_ev | Gate-passing region (price >3.0): 20 bets | **UNDERPOWERED**; no recommendation |
| H2 team-total | Fires every week (105 spots / 53 games); proxy leg scoreable on only 16 spots: −5.6%, **UNDERPOWERED** | Contract undecided; Train can't support it |
| H4 wind | **Not computed**: no archived-forecast source wired | — |

---

## 1. Gate: is Pinnacle's prop close calibrated?

2023–24: 16,953 Pinnacle contracts with both sides; **settlement match rate
93.4%**; 15,837 graded after pushes. Devigged with shin; over-rate by decile;
slope = logistic fit of outcome on logit(p).

| Set | n | Predicted over | Realized | Slope [game CI] | Bins outside CI |
|---|---|---|---|---|---|
| Pooled | 15,837 | .495 | .492 | 1.08 [0.94, 1.23] | 0/10 |
| receptions | 5,353 | .493 | .492 | 1.06 [0.86, 1.23] | 0/10 |
| passing_tds | 1,079 | .479 | .483 | 1.15 [0.88, 1.46] | 0/10 |
| receiving_yards | 5,776 | .499 | .503 | 0.76 [0.21, 1.32] | 1/10 |
| passing_yards | 975 | .494 | .517 | 0.99 [−0.48, 2.44] | 0/10 |
| **rushing_yards** | 2,654 | **.494** | **.463** | 1.38 [0.88, 1.93] | **2/10 → FAIL** |

**2026 Weeks 1–4:** 3,336 contracts; **match rate 74.1%**. Unmatched by week:
70 / 45 / 44 / **706**. Week 4 is mostly unmatched because nflverse doesn't have
today's stats yet. Graded: 2,471 contracts over 49 games. Predicted .497,
realized .497, slope 0.70 [0.34, 1.07], 0 of 8 bins out.

**Gate outcome:** closing EV is usable for receptions, passing TDs and the
yardage markets that passed. **Rushing yards fails, so every closing-EV number
below excludes rushing legs.** Rushing overs came in 3.1pp under Pinnacle's
price. That isn't tested as a strategy here.

## 2. Gate: is Pinnacle's moneyline close calibrated?

2023–24, 570 games with a Pinnacle ML close, all settled (no ties). Home side
by quintile: 0/5 bins out; slope 1.16 [0.89, 1.44] (bootstrap by game).
**Underdog side:**

| Dog fair prob (≈ fair decimal) | n | Predicted | Realized [binomial CI] | |
|---|---|---|---|---|
| ≤ .25 (> 4.0) | 102 | .193 | .225 [.149, .319] | ok |
| .25–.333 (3.0–4.0) | 130 | .292 | .262 [.188, .346] | ok |
| **.333–.5 (2.0–3.0)** | **338** | **.413** | **.349 [.298, .403]** | **OUT** |

2026 Weeks 1–4: 62 games, 50 settled; slope 0.70 [−0.18, 1.75]. That's
**UNDERPOWERED**; nothing to read.

**Gate outcome:** in 2023–24, Pinnacle's close overrated short underdogs by
about 6pp. In that region, closing EV against Pinnacle overstates a dog bet's
value, so it is **not usable there**. The longshot region (fair decimal >3.0)
passes.

## 3. Does "price beats Pinnacle" turn into money? (historical, realized)

2023–24 execution-book prices vs Pinnacle fair, ~20 min before kickoff. 7,169
spots at EV ≥0; **match rate 95.0%** (357 unmatched, excluded).

| Entry EV | n | Games | Mean EV | Realized ROI [game CI] |
|---|---|---|---|---|
| 0–2% | 3,919 | 557 | +0.9% | −0.7% [−4.5, +3.0] |
| 2–4% | 1,838 | 505 | +2.8% | +2.4% [−2.9, +7.7] |
| 4–6% | 755 | 349 | +4.8% | +1.5% [−7.0, +10.0] |
| 6–10% | 276 | 181 | +7.3% | +2.8% [−11.9, +17.6] |
| 10–15% | 23 | 20 | +11.2% | UNDERPOWERED |
| **≥2%, ≤15%** | **2,892** | — | +3.9% | **+2.5% [−2.4, +7.3]**, p(≤0)=0.15 |

These rows include rushing yards (computed before the gate was applied; not
re-split). Realized ROI is a direct outcome measure and doesn't depend on the
closing-EV gate. The old "+3.1% at 2%, −6.3% at 4%" **inversion does not
reappear** with game clustering: every bucket is positive, and none is
distinguishable from zero. The CI is compatible both with the predicted +3.9%
and with 0, so **realized ROI at this sample size can't decide it.**

**Tooling flaw:** `evaluation.random_bet_benchmark` pays the listed side's price
to the *opposite* side too, so its null mean is about `price/2 − 1` (+2.45% at
an average price of 2.05). It placed a +2.5% ROI at the 54th percentile. Don't
use it as a pass condition until it uses the opposite side's real price.

## 4. Live 2026 alerts on closing EV (shadow log, Weeks 1–4)

346 legs, 326 measurable. Excluded: entry EV >15% (bad quotes) and rushing
yards (gate fail).

| Strategy | n | Games | Excluded (bad / rushing) | Closing EV [game CI] |
|---|---|---|---|---|
| prop_ev | 129 | 48 | 2 / 4 | **+3.08% [+1.86, +4.29]** |
| prop_arb (per leg) | 57 | 23 | 1 / 2 | +1.18% [+0.79, +1.60] |
| steam | 40 | 21 | 2 / 0 | **−2.84% [−5.07, −0.22]** |
| moneyline_ev | 80 | 35 | 3 / 0 | see below |
| middle | 4 | 2 | 2 / 0 | UNDERPOWERED |

**moneyline_ev** (first alert per game-side, n=36 / 35 games): +4.47%
[+1.81, +7.10] overall, but part of it falls where the ML gate failed. Split:
- **price >3.0 (gate region passes):** 20 bets, +6.95% [+3.62, +10.17]. **UNDERPOWERED**.
- **price ≤3.0 (includes the gate-fail short-dog region):** 16 bets. **UNDERPOWERED**, and partly **unusable**.

**Reading:** the decision report's `prop_ev` NO came from `clv_probability`,
which never sees the price paid. On closing EV, a yardstick that passed its
gate, prop_ev's alerts were +3.1% with a CI above zero. The pre-registered
verdict stands as recorded; this is a different measurement, not a re-score.
Steam is negative on both metrics.

## 5. H1 — stale soft line after a Pinnacle move

`pinnacle_lag.py`. Props, 0–12h before kickoff. Trigger: a Pinnacle devigged
move of ≥M between captures ≤20 min apart. Bet: the best `EXECUTION_BOOKS` price
on the side Pinnacle moved toward, at the same capture and line, with EV ≥E.
First trigger per (contract, side). Bad quotes excluded. H1 has no rushing legs
(40 receptions, 4 passing TDs).

**Kill check — PASS.** 145 Pinnacle moves of ≥2pp; **8.3% reverted** by the
close (8.8% at ≥3pp over 68 moves; 3.3% at ≥4pp over 30).

**Grid, closing EV [game CI]:**

| M \ E | 1% | 2% | 3% |
|---|---|---|---|
| **2pp** | **44 bets / 24 g: +2.98% [+1.31, +4.51]**, p=.0004 | 30 / 20 g: +3.91% [+1.60, +5.97] | 23 / 17 g: UNDERPOWERED |
| 3pp | 22 / 16 g: UNDERPOWERED | 19 / 14 g: UNDERPOWERED | 15 / 12 g: UNDERPOWERED |
| 4pp | 10 / 9 g: UNDERPOWERED | 8 / 8 g: UNDERPOWERED | 6 / 6 g: UNDERPOWERED |

For M=2pp, E=1%: survival at next capture 72.5%; Pinnacle's post-entry drift
−0.24pp; realized ROI on 37 settled bets is UNDERPOWERED.

**Recommendation (yours to freeze): M=2pp, E=1%.** It's the only cell with
n≥30 and a CI clear of zero, plus a margin above the floor.

**By week (computed on the corrected Train set):**

| Week | Games | Pinnacle moves ≥2pp | H1 bets | H1b bets |
|---|---|---|---|---|
| 1 | 16 | 3 | 0 | 4 |
| 2 | 16 | 60 | 29 | 91 |
| 3 | 16 | 54 | 11 | 70 |
| 4 | 14 | 28 | 4 | 47 |

Every weekly H1 count is under 30, so this is **UNDERPOWERED as a trend**.
Week 1 is low because of polling: the 15-min tier started 9/14. What can be
said: Train has 44 H1 bets over 3 effective weeks. If the holdout's rate
matches Train's, n≥30 is plausible; if it matches Week 4 alone, it isn't. That
can't be known in advance.

**Does the trigger matter? H1b control:** the same scoring on *every*
execution-book quote ≥1% EV in 0–12h, first per contract-side, no move required,
rushing excluded: **211 bets / 47 games, +1.55% [+1.12, +1.98]**, p<.0001.
H1 minus the control (excluding H1's own contracts): +1.8pp [−0.1, +3.7]. The
CI touches zero, so **it isn't established that the trigger adds value.**
Post-entry Pinnacle drift: −0.24pp for H1 vs −0.66pp for the control
(excluding H1).

**Distribution shift to flag:** Train has essentially no yardage bets, because
yardage only got 15-min polling today. The holdout will contain them under the
same rule.

## 6. H3 — prop middles: calibration gate FAIL

Main lines only: each book's line whose two sides are priced closest to even.
A first pass paired alternate lines and produced impossible 31% hit rates, and
was discarded. The hit model is the 2023 empirical distribution of
(actual − Pinnacle main line) by stat, checked on 2024.

| 2024 | Middles | Predicted hit | Realized [binomial CI] |
|---|---|---|---|
| gap ≥1 | 4,004 | 5.5% | 4.3% [3.7, 5.0] **out** |
| gap ≥2 | 2,266 | 4.7% | 2.8% [2.2, 3.6] **out** |
| gap ≥3 | 1,128 | 5.6% | 3.1% [2.2, 4.3] **out** |

Rushing is worst: predicted 4.4%, realized 2.0% (gap ≥1). **Gate failed, so
the chain stops:** H3 EV and 2026 results aren't reported. The settlement match
rate for the 2024 middles was **not computed** (unmatched rows were dropped
without counting). That doesn't change the verdict: the gate fails on the
matched rows.

## 7. H2 — team-total (exploratory; contract undecided)

`team_total_scan.find_team_total_spots` exactly as in code, run 3h before each
Weeks 1–4 kickoff slot (`run/s5_h2.py`; Week 4 slots that had kicked off).
**105 spots over 53 games**, all in the `underdog` bucket. By week, passing /
rushing: 12/11, 16/16, 11/11, 14/14. Mean modeled edge +7.35%. It fires for
roughly one underdog team per game per stat, so it is not selective.

**Proxy leg, option (a), passing only** (rushing excluded: gate fail):
the underdog's QB `passing_yards` over at the best execution-book price at T−3h,
scored on closing EV (`run/s5b_proxy.py`). Of 53 spots: 1 had no QB team match,
and **36 had no Pinnacle close on the same line** as the best soft over. Both
were excluded and counted. The remaining **16 bets / 16 games: −5.62%
[−6.75, −4.74], UNDERPOWERED.** Pinnacle's close P(over) on them averaged .499,
so on this subset the team-total lift does not show up in the QB's own line,
and the result is roughly the soft books' vig. With 69% of spots unscoreable,
this sample can't stand for H2.

## 8. Not computed

- **H4:** needs an archived-forecast source.
- **Week 4 SNF/MNF:** not yet played.

## 9. Decisions for you before the Wed 10-07 freeze

1. **H1:** freeze M=2pp, E=1%? (recommended)
2. **H1b:** register as confirmatory? (recommended; largest sample, tightest CI)
3. **Rushing yards:** exclude from all closing-EV scoring in the pre-reg (gate fail).
4. **Moneyline short underdogs:** exclude the gate-fail region (Pinnacle dog
   fair .333–.5) from any moneyline closing-EV scoring. Whether to register
   `moneyline_ev` at all: Train is underpowered in the usable region, so no
   recommendation.
5. **H3:** the pre-reg rule says drop; confirm.
6. **`random_bet_benchmark`:** fix (use the opposite side's real price) or
   remove it from the pass bar.
7. **H2:** volume is fine, but option (a) was scoreable on only 16 of 53
   spots on Train (−5.6%, underpowered). Option (b) needs a new Odds API market;
   (c) keeps it unbettable. No recommendation from this data.
