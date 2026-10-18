# Pre-registration — 2026 Weeks 10–14 holdout

**Status: DRAFT (started 2026-10-17).** Commit the final version before
**Thu 2026-11-12 20:15 ET** (first Week 10 kickoff, `2026_10_WAS_NYG`). The target
is **before Tue 11-10**, when the Weeks 5–9 result is scored, so that result
can't shape anything here except the two H1/H1b branches written out in advance
in §4. Commit drafts as they change: an earlier git timestamp is stronger
evidence, and the Weeks 5–9 doc lost its timestamp by sitting staged.

Items marked **[DECIDE]** are yours. Everything else is a proposal you can edit
until the commit, and not afterwards (see §6).

---

## 1. What carries over from the Weeks 5–9 pre-registration

Unchanged and incorporated by reference (`preregistration_wk5-9.md`):

- **§3 primary metric:** closing EV = p_close_fair(side) × d_paid − 1 against
  Pinnacle's Shin-devigged close, computed through `bet_log.to_backtest_bets`.
- **§3 pass bar:** conditions 1–6 (n ≥ 30 from ≥ 15 games; mean > 0;
  game-clustered 95% CI lower bound > 0 at 10,000 reps, seed 0; random-side null
  p < 0.05 with the opposite side at its real quote; survival at first re-check
  ≥ 50%; BH q < 0.05 across this document's family).
- **Exclusions:** bad quotes (entry EV > 15%); any market or price region that
  failed its calibration gate (rushing yards; moneyline short underdogs, Pinnacle
  fair .333–.5).

## 2. Data split

| Set | Data | Use |
|---|---|---|
| Fit / calibrate | 2023–24 history | calibration gates (`analysis/train_results_2026-10-04.md` §1–2) |
| **Train** | 2026 Weeks 1–9 (mainlines); Weeks 1–4 for props, plus 5–9 only after the 11-10 unseal | evidence for the freeze (`analysis/train_results_2026-10-17.md`) |
| **Holdout** | Weeks 10–14: Thu 11-12 → Mon 12-14 | scored **once**, on or after **Tue 2026-12-15** |
| Untouched | 2025 season | not used |

**No peeking:** no closing EV, realized ROI, beat rate or hit rate is computed on
holdout weeks for any hypothesis below before 12-15. Operational checks (uptime,
credits, whether the scanner fires, survival) are allowed.

**Known partial leak, disclosed now:** `make decision-report` will keep showing
`moneyline_ev`'s `clv_probability` and beat rate across all weeks, including
Weeks 10–14. That isn't the registered metric, but it's correlated with it.
**[DECIDE]**: either filter Weeks 10–14 out of `decision-report` until 12-15
(recommended; a small code change), or accept the leak and record it here.

## 3. Exploration already done (disclosed)

From `analysis/train_results_2026-10-17.md`:

- moneyline_ev, price > 3.0: closing EV **+5.20% [+2.67, +7.63]**, 68 bets / 25
  games (Weeks 1–5). Weeks 1–4: +5.76%; Week 5 alone: +2.82% on 4 games.
- **The same rule on 2023–24, scored on realized results: −21.6% [−59.5, +20.8],
  81 bets.** They won 16.0% against a 21.7% fair probability. That doesn't refute
  the closing-EV result (the CI is ±40pp), but it is the strongest evidence
  against H5 and is written here before the holdout.
- Team-total underdog passing lift 1.337 [1.034, 1.724], a third replication.
- steam, middle and prop_arb are dead on Train. They are not registered.

## 4. Hypotheses

### H5 — Moneyline longshot price vs Pinnacle · CONFIRMATORY

**Shape:** price comparison (soft book vs sharp fair), not probability
estimation.

**Rule:**
- **Spot:** `live_scan.find_positive_ev_spots` exactly as in code on the commit
  date: `EXECUTION_BOOKS`, EV ≥ `DEFAULT_EDGE_THRESHOLD` (2%) vs Pinnacle's
  latest Shin fair, Pinnacle captured within 30 min of the book's price.
- **Region:** price_decimal **> 3.0** only, where the moneyline gate passed.
- **One bet per (game, side):** the earliest alert (`shadow_alerts_as_bets`).
- **Excluded:** entry EV > 15%.
- **Logged** by the running monitor to `data/shadow_log.jsonl` as
  `moneyline_ev`. No new code is in the bet path.

**Train:** see §3. **Expected volume:** ~13 bets/week over ~5 games, so ~65 bets
over ~25 games in five weeks. That clears condition 1 if the Week 1–4 rate holds,
but Week 5 alone came in at 4 games.

**Also reported, not gated:** realized ROI with game-clustered CI, next to the
2023–24 history result, and `clv_probability`.

### H1 / H1b — carried forward only if they pass on 11-10

Both branches are written now, so the 11-10 result picks one mechanically:

- **H1 or H1b PASSES Weeks 5–9:** it re-runs unchanged (M=2pp, E=1%, same code,
  `data/shadow_log_prereg.jsonl`) on Weeks 10–14 as a **replication**, in this
  family.
- **FAILS:** dropped. No re-tuning and no new grid on Weeks 5–9.

### H2 — Team-total correlation · [DECIDE]

The H2 edge is priced as a **same-game parlay**: underdog ML + team over, against
a book that multiplies the vigged legs (`correlated_props.bucket_edge =
lift/(1+vig)^2 − 1`). The lift is a property of the *joint* outcome. Neither leg
alone is mispriced.

- **(a) QB-over proxy, as recommended on 10-04: withdrawn.** An over-only bet
  carries none of the joint lift, so by construction its expected closing EV is
  about −vig. The 10-04 Train result (−5.6% on 16 spots, "roughly the soft books'
  vig") is that prediction coming true, not a sign of a weak edge.
- **(b) Book team-yards market: doesn't exist.** The Odds API's NFL
  `team_totals` / `alternate_team_totals` are points only (checked 2026-10-17).
- **(c) Drop from the confirmatory family (recommended).** The mechanism is
  replicated three times but can't be scored with data this pipeline collects:
  SGP prices aren't in the Odds API, and books' SGP engines price correlation
  themselves.
- **Optional exploratory study (not in the family):** for the H2 underdog spots
  in Weeks 10–14, record by hand DraftKings' SGP price for (dog ML + QB pass
  yards over) next to the two single-leg prices. If the SGP price is above
  `naive_parlay_price`, books aren't pricing the correlation and a bettable H2
  exists. If it's below, they are, and H2 is closed.

### Not registered

steam, middle, prop_arb (dead on Train); H3 (calibration gate failed); H4 (no
archived-forecast source).

## 5. Family and correction

BH at q = 0.05 across **{H5} ∪ {whichever of H1, H1b pass on 11-10}**. The
family size is fixed once the 11-10 result is in and is recorded in §6 that day.

## 6. Deviations log

| Date | Change | Reason | Changes bets? |
|---|---|---|---|

## 7. Build order (before the commit)

1. ~~Scorer~~ DONE 2026-10-17: `src/clv/prereg_score_wk10.py`, run as `make
   prereg-score-wk10 [WEEKS=holdout]`. It's a separate module so the Weeks 5–9
   scorer stays untouched. It reuses `score_strategy` (conditions 1–5), prices
   the null's opposite side at the real same-book moneyline quote, and refuses
   Weeks 10–14 before 12-15. Train (Weeks 1–5 played): 67 bets / 25 games,
   +5.34% [+2.82, +7.74], all six conditions pass. That is **in-sample**: it's
   the data that selected H5.
2. **[DECIDE]** the `decision-report` leak (§2).
3. **[DECIDE]** H2: (c) plus the optional manual SGP study, or something else.
4. After 11-10: record the H1/H1b branch and the family size in §6.
5. Commit before 11-12 20:15 ET, earlier if possible.
