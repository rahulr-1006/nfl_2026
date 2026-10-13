# Pre-registration — 2026 Weeks 5–9 holdout

**Status: COMMITTED LATE (2026-10-13, deadline was 2026-10-07 23:59 ET).** Week 5
had already been played when it was committed. See §6 for what that changes:
the H1/H1b freeze stands on weaker evidence, and H2/H3 are out of this family.
(Original instruction: commit before Wed 2026-10-07 23:59 ET, one day before the
first Week 5 kickoff, Thu 10-08 20:15 ET.)

Items marked **[DECIDE]** are yours to settle before committing. Everything
else is a proposal you can edit freely until then, and not at all afterwards
(see §6, Deviations).

---

## 1. Why this exists

The 9/29 decision report scored strategies against a bar fixed in advance, and
that discipline is the only reason its verdicts mean anything. This document
extends it to new strategies. Rules, parameters and pass bars are written down
**before** the data that tests them exists, so a pass can't be the product of
choices made after looking.

Two lessons from this repo shape it:

- **Strategy shape predicts outcome** (`methodology_backlog.md`, design rule).
  Probability-estimation strategies are 0 for 7 here. Every hypothesis below
  states its shape.
- **Props from one game move together.** One game can produce many correlated
  bets, so a CI computed per bet overstates confidence. Every CI here is
  bootstrapped by game.

## 2. Data split

| Set | Weeks | Kickoffs (ET) | Use |
|---|---|---|---|
| **Train** | 1–4 | Thu 09-10 → Mon 10-05 | Build, explore, tune **only** within the grids in §4 |
| **Holdout** | 5–9 | Thu 10-08 → Mon 11-09 (~75 games) | Scored **once**, on or after Tue 11-10 |

- **Freeze:** each hypothesis's parameters are chosen on Train from its declared
  grid and written into §4 **before the freeze date**. The holdout tests only
  the frozen configuration.
- **No peeking:** until 11-10, no holdout CLV, ROI, beat-rate or hit-rate is
  computed for H1–H4. Operational checks (collection uptime, credits, whether
  the scanner fires, and survival/placeability) are allowed, since none of them
  reveals the outcome.
- **Train data caveats:** Week 1 props had 24 polls in the final 12h, not 48
  (the 15-min tier started 9/14). Yardage props only have 15-min data from
  2026-10-04 15:28 ET. Thursday and Monday games before 10-04 lost dense mainline
  polling in their last ~4h (timezone bug, fixed 10-04).

### Exploration already done (disclosed, because it shaped the hypotheses)

- **H1 probe (2026-10-04, Weeks 2–3 only):** 54 Pinnacle prop moves of 3+ pp
  between polls, across 24 games; 47 soft-book quotes on the moved side at
  >2% EV vs Pinnacle's new fair (median +4.6%); 64% still available about 15 min
  later. Receptions/pass TDs only, and it included books outside
  `EXECUTION_BOOKS` (Bovada 13, BetOnline 2), which H1 excludes.
- **H2:** validated on 2023 train / 2024 test (`team_total_props.py`).
  Out-of-sample edge: passing +7.1%, rushing +2.8% at 6.54% vig.
- **Decision report 2026-10-04:** `steam` NO (n=33, CLV −0.0097), `prop_ev`
  NO (n=109, CLV −0.0100). These are H1's priors, and they are unfavourable.

## 3. Common evaluation protocol (applies to every hypothesis)

**Primary metric: closing EV**, `close_ev = p_close_fair(side) × d_paid − 1`.
`p_close_fair` is Pinnacle's last quote before the store-observed kickoff,
devigged with `shin`, from the same code path as `shadow_clv` /
`bet_log.to_backtest_bets`. `d_paid` is the decimal price actually taken.

**Why not `clv_probability` (changed 2026-10-04, before commit).**
`clv_probability` is Pinnacle's close fair minus Pinnacle's entry fair. It
never sees the price paid. For a price-based bet (soft book vs Pinnacle) it
measures only whether Pinnacle *kept moving*, so it scores a +EV stale-line bet
at about zero by construction. Measured on the live shadow log 2026-10-04:
`prop_ev` has `clv_probability −0.0091` and closing EV `+0.0331` (game-clustered
CI [+0.021, +0.045]). The two metrics answer different questions.
`clv_probability` is still **reported** for every hypothesis as the
adverse-selection measure: how much Pinnacle moved against the side after entry.

**Closing EV is only meaningful if Pinnacle's prop close is calibrated.** This
is a **gate on every props hypothesis**, run on 2023–2024 history before the
holdout. Bin Pinnacle's no-vig close probability by decile; realized over-rates
must sit inside each bin's 95% CI, and the slope of realized vs predicted must
have a 95% CI containing 1. If it fails, closing EV against Pinnacle props is
not a valid yardstick, and props hypotheses are scored on realized ROI only
(which five weeks cannot power; see Power).

**Bad-quote exclusion (declared before the holdout):** legs with entry EV
> 15% against Pinnacle's entry fair are presumed stale or mislabelled quotes.
Example found 2026-10-04: BetMGM 2.35 on a side Pinnacle had at 60%. They are
excluded from the primary metric and reported separately. A real edge can't
live mainly in quotes that big.

**Known counter-evidence to keep in view:** the historical props-EV backtest
(6,812 bets) returned +3.1% ROI at a 2% EV threshold and −6.3% at 4%. That is
non-monotonic: the higher-EV bets did worse, which is the signature of errors
rather than edge. Any price-based hypothesis that passes on closing EV must
also report realized ROI by EV bucket, and must not show that inversion.

**Pass bar.** Every condition must hold:

1. `n >= 30` bets from `>= 15` distinct games.
2. Mean closing EV `> 0` (bad quotes excluded).
3. **Game-clustered bootstrap 95% CI lower bound `> 0`**: resample games with
   replacement, 10,000 reps, percentile interval, seed 0. This is stricter than
   the 9/29 bar on purpose; it is what "decent confidence interval" means here.
4. Beats the random-side null (`evaluation.random_bet_benchmark`: same games,
   same prices, random sides) at one-sided p < 0.05.
5. Survival at first re-check >= 50%: the price is still available at the next
   capture, so the edge can be placed by hand.
6. **Benjamini–Hochberg q < 0.05 across the confirmatory family {H1, H1b}**,
   plus H2 and H3 unless dropped before the freeze (**[DECIDE]**: H3 failed its
   calibration gate; H2's contract is unsettled; see
   `analysis/train_results_2026-10-04.md` §6–7).
   The p-value is the one-sided clustered-bootstrap p for mean closing EV > 0.

**Outcome:** pass → eligible to bet under the entry policy (GO, plus a price
equal to or better than the alert at placement), with a $100 bankroll + 2
reloads and a $2 max bet. Fail → not bet this season. No re-tuning on holdout
data. A failed hypothesis may be re-registered once, against a **fresh**
holdout (Weeks 10–14), with a written reason.

**Power, to set expectations:** today's report implies a per-bet CLV SD of
about 0.021 (moneyline) to 0.034 (props). For the CI to exclude zero:
roughly 20–45 independent bets at a true 1% edge, and 80–180 at 0.5%. Game
clustering raises both. A hypothesis that fires a handful of times a week
cannot pass in five weeks, whatever its true edge.

**Bets are logged, never texted.** H1, H1b and H2–H4 run as shadow-only strategies.

**Implementation (2026-10-04):** H1/H1b are live in `com.nflclv.monitor` via
`src/signal/prereg_scan.py`, using `backtest.pinnacle_lag` with the frozen
parameters, so the live record and the Train numbers share one definition. Legs
go to **`data/shadow_log_prereg.jsonl`**, a separate file from
`data/shadow_log.jsonl`. `decision-report`, `shadow-report` and `clv-report`
read only the latter, so none of them can show H1/H1b holdout results before
11-10. Survival rechecks run on the separate file, which this document allows.
Everything the rule selects is logged, including quotes >15% EV and rushing
legs; those exclusions are applied at scoring, not to the record. Their
alerts go to `shadow_log.jsonl` and are not sent by SMS until they pass. That
keeps the live record complete and stops a promising early run from
influencing what gets bet.

## 4. Hypotheses

### H1 — Stale soft line after a Pinnacle move (props) · CONFIRMATORY

**Shape:** structural (latency). There is no probability model: Pinnacle's
own move is the information, and the bet is a book that hasn't moved yet.

**How it differs from `steam` (a NO):** steam is mainline only, triggers on
3+ books moving together within 1h, and is priced from line moves through a
normal-margin model. H1 is props only, triggers on Pinnacle alone, and is
priced directly against Pinnacle's new devigged probability.

**Rule:**
- **Universe:** player props, all 5 quoted markets, captures 0–12h before kickoff.
- **Trigger:** for one contract (event, player, prop_stat, line), Pinnacle's
  devigged over-probability changes by **≥ M pp** between two consecutive
  Pinnacle captures **≤ 20 min apart**.
- **Bet:** at that same capture, the side Pinnacle moved toward, at the best
  price among `EXECUTION_BOOKS` (DK, FD, MGM, BetRivers, Caesars) quoting the
  **same line**, if EV vs Pinnacle's new fair **≥ E**.
- **Dedupe:** at most one bet per (contract, side) per game, the first trigger.
  This matches the shadow-log dedupe fixed 9/21.

**Tuning grid (Train only):** M ∈ {2, 3, 4} pp × E ∈ {1, 2, 3}%: 9 cells.
The whole grid is reported in `analysis/train_results_2026-10-04.md` §5.

**FROZEN (2026-10-04, by the user): M = 2pp, E = 1%.** Train: 44 bets over 24
games, closing EV +2.98% [+1.31, +4.51] (game-clustered), p = 0.0004.

**Selection-rule change, recorded:** this draft's rule was "highest Train
closing EV among cells with n ≥ 30". Applied literally, that picks **E = 2%**
(+3.91%, n = 30 exactly). The user chose E = 1% instead, for the larger sample
(44 vs 30) and the margin above the n ≥ 30 floor that the holdout must also
clear. The rule is changed before the commit, so it binds nothing, but it is
written here so the choice doesn't look as if it came from the declared
procedure.

**Trigger window enforced in code:** `pinnacle_lag.detect_moves(window_hours=12)`.
On Train every H1 bet was 0.16–9.36h before kickoff, so this changed nothing
measured. It keeps the rule true if the polling schedule changes.

**Reported, not gating:** the reversal rate (the share of triggers where
Pinnacle's close returns to within 1 pp of the pre-move fair), lag by book, and
CLV split by prop_stat.

**Kill signal worth knowing early:** if the Train reversal rate is above about
50%, Pinnacle's moves are mostly noise. Then H1 is steam again, and should be
dropped before the holdout rather than tested.

### H1b — Soft price beats Pinnacle, no move required (props) · CONFIRMATORY

**Registered 2026-10-04 by the user.** This was H1's control in the Train
analysis. It is the same pipeline with the move threshold removed, and it had
the largest Train sample.

**Shape:** structural (price vs a calibrated sharp close). No probability model.

**Rule:** exactly `pinnacle_lag` with **M = 0**, **E = 1%**:
- **Universe:** player props, captures 0–12h before kickoff.
- **Trigger:** any Pinnacle capture of a contract whose previous Pinnacle
  capture of that contract was **≤ 20 min earlier** (the `max_gap` that H1 uses;
  on Train this is the 15-min tier).
- **Bet:** at that capture, the best `EXECUTION_BOOKS` price on the same line,
  either side, with EV vs Pinnacle's devigged fair **≥ 1%**.
- **Dedupe:** first qualifying capture per (contract, side).
- **Excluded:** entry EV > 15% (bad quotes, §3).

**Train:** 211 bets over 47 games (rushing legs excluded per the §3 gate
pending the [DECIDE] in the results doc), closing EV **+1.55% [+1.12, +1.98]**,
p < 0.0001. Post-entry Pinnacle drift −0.52pp.

**Overlap with H1:** every H1 bet satisfies H1b's rule, so the two are
correlated and not independent tests. BH across correlated hypotheses is still
valid (positive dependence), but a pass on both is less than two separate
confirmations. On Train, H1 minus H1b-without-H1's-contracts was +1.8pp
[−0.1, +3.7]: not established.

**What it is, plainly:** a cleaned-up version of the live `prop_ev` alert
(first trigger per contract, final 12h, bad quotes out, scored on closing EV).
`prop_ev`'s decision-report NO used the price-blind `clv_probability`. H1b
tests the same idea on the metric that sees the price.

### H2 — Team-total correlation, live · CONFIRMATORY

**Shape:** probability estimation, but with a validated, out-of-sample lift
(the project's only one).

**Rule:** `team_total_scan.find_team_total_spots` exactly as in code on the
freeze date. Lifts are `VALIDATED_TEAM_TOTAL_LIFT` (the 2024 realized values),
`DEFAULT_EDGE_THRESHOLD` is 0.03, vig is measured per event, and only validated
buckets are used. **No re-fit on 2026 data.**

**[DECIDE] The executable contract.** The edge is on a *constructed* team
aggregate (a sum of player lines). Most books don't offer that as a single
bet, and the alert names no price, so CLV can't be scored as written. Options:

- **(a) Proxy leg:** bet the over on the team's starting QB `passing_yards` prop
  (passing) or lead RB `rushing_yards` prop (rushing), at the best
  `EXECUTION_BOOKS` price. This also tests whether the aggregate edge transfers
  to one player.
- **(b) Book team-total market:** only where a book offers team passing or
  rushing yards. This needs a new Odds API market and is probably sparse.
- **(c) Drop H2 from the confirmatory family** and keep it as a measured but
  unbettable finding.

Recommendation: **(a)**, written down as a transfer test. If H2 is (a), its
n is the number of alerts (~2–14 a week) and it may be underpowered (§3).

### H3 — Player-prop middles across books · CONFIRMATORY

**Shape:** structural (book disagreement), with a thin hit-probability model.

**Rule:**
- **Spot:** same player and prop_stat, two `EXECUTION_BOOKS` quoting different
  lines at the same capture. Over at the lower line (book A), under at the
  higher line (book B). The gap must be ≥ G.
- **Hit probability:** P(lower < actual < higher) from the **empirical**
  distribution of (actual − Pinnacle close line) by prop_stat, fit on
  2023 historical props + player stats. It is not a normal: receptions and
  TDs are discrete.
- **Bet if** the two-leg EV ≥ 2% of total stake, using both real prices.

**Train gate (before the holdout, on history, not 2026):** fit on 2023 and
check calibration on 2024. The predicted vs realized window hit rate must agree
within its 95% CI, by stat. If it fails, H3 is dropped before the holdout. This
is H3's main advantage: the hard part (the probability) is validated on
thousands of historical player-games, not on five weeks.

**Primary metric exception:** CLV doesn't fit a two-leg middle, because the legs
are on opposite sides and roughly cancel. For H3, conditions 2–3 of the pass bar
use **expected value per middle** (computed from the frozen model and the real
prices), plus a **calibration check on holdout**: realized hit rate ≥ predicted
minus its 95% CI half-width. Realized ROI is reported, but it can't gate: at
5–15% hit rates, five weeks of ROI is mostly noise.

**Tuning grid (Train only):** G ∈ {1.0, 2.0, 3.0} (in each stat's units; TDs
and receptions are only eligible at G ≥ 1.0). **Frozen value:** G = ___ .

### H4 — Wind and yardage-line drift · EXPLORATORY (cannot produce a GO)

**Shape:** probability estimation (do books under-react early to forecasts?).

**Rule:** outdoor or open-roof games with **forecast** wind ≥ 15 mph at entry
(T−12h). Bet under `passing_yards` and `receiving_yards` at the best
`EXECUTION_BOOKS` price at T−12h, and measure CLV to the close.

**Lookahead rule:** nflverse `wind`/`temp` are **observed at game time**. Using
them for a T−12h decision is look-ahead, and they are banned as the trigger.
Use an archived forecast as of the entry time (e.g. Open-Meteo's
historical-forecast API — **verify it exists and covers stadium coordinates
before relying on it**).

**Why exploratory:** about 1–3 qualifying games a week means about 5–15 holdout
games. That's far too few for a clustered CI to exclude zero. It is reported
only, outside the BH family, and it can at most justify registering it again
for Weeks 10–14.

## 5. Not registered (and why)

- **Neural nets / large feature sets:** the effective sample is dozens of
  games, not thousands of rows; 0 for 7 on feature engineering.
- **Static props EV vs Pinnacle:** already a NO (n=109).
- **More moneyline features:** 0 for 7; covered by the design rule.
- **Injury cascades** (teammates' lines lag when a player's props are pulled):
  promising and structural, but there is no news-timestamp source yet. Candidate
  for Weeks 10–14.
- **Mainline version of H1:** mainline polls every ~30 min, not 15, so lag
  detection is coarser. Candidate for Weeks 10–14 if H1 passes.

## 6. Deviations log

Any change after the commit is recorded here with its date and reason, and
flagged in the final report. Bug fixes that don't change a strategy's decisions
(e.g. a crash) are allowed. Anything that changes which bets are made is a
deviation.

| Date | Change | Reason | Changes bets? |
|---|---|---|---|
| 2026-10-13 | **Committed 6 days late** (commit `85094e3`, 2026-10-13), after all of Week 5 was played. The text was not edited between 2026-10-04 19:09 ET (file mtime) and the commit. Supporting, not tamper-proof, evidence that H1/H1b were frozen before the holdout: `data/shadow_log_prereg.jsonl`'s first row is `alerted_at` 2026-10-04T23:24Z, and `logs/monitor.err.log` shows the frozen scan running at 2026-10-04 19:25 ET. Nobody scored the prereg log before the commit; only row counts were read. | The deadline was missed. The evidence the git timestamp should have supplied is now weaker, and the final report must say so. | No. H1/H1b parameters are unchanged (M=2pp, E=1%). |
| 2026-10-13 | **H2 and H3 are dropped from the Weeks 5–9 confirmatory family.** The BH family is {H1, H1b}. H2's contract, H3's keep/drop and its `G` were still [DECIDE] when the holdout started, so settling them now would mean choosing after Week 5 had happened. Either can be registered against the Weeks 10–14 holdout. H4 stays exploratory. | Consequence of the late commit. | Yes for H2/H3 (no holdout bets are scored for them). None for H1/H1b. |

## 7. Build order (Train phase, 10-05 → 10-07)

1. ~~Game-clustered bootstrap + one-sided p~~ — DONE 2026-10-04 as `clv.metrics.clustered_bootstrap`.
2. Pinnacle prop-close calibration gate on 2023–2024 history (decides whether closing EV is valid for props).
3. H1 backtest on Weeks 1–4: reversal rate first (the kill signal), then the grid.
4. H3 historical calibration gate (2023 fit → 2024 check).
5. Shadow-only wiring for whatever survives Train, so live alerts accrue from Week 5.
6. Fill the frozen values, settle the [DECIDE] items, commit.
