# Methodology backlog

Candidate strategies and modeling ideas still worth trying, distinct from
`parking_lot.md` (ideas explicitly ruled *out of scope* for now). This list is
active — things queued to build, not deferred. Update status as work moves.

---

## Standing reference: the numbers any prop proposal must clear

Measured 2026-08-23 across the **complete** 2023+2024 historical pull (462K prop
snapshots, 16,953 two-sided contracts). Check a proposal against these before
building it — they are cheap to consult and have already explained every prop
failure to date.

| Quantity | Measured |
|---|---|
| Pinnacle prop vig (mean overround) | **6.29%** |
| Cross-book price dispersion, best−worst (median) | 0.101 decimal |
| Line-shopping gain, best−median book (median) | 0.045 decimal ≈ **1.26 pts** |
| Best-of-5-books EV vs Pinnacle fair (median) | **−4.74%** |
| Fraction of contract-sides with positive EV at best price | **14.0%** |

**Line shopping is real and NOT patched** — dispersion persists across 44,391
contract-sides with ≥3 books quoting. But it recovers only ~1.3 of the ~3.1
points of per-side vig, leaving a **~4.7% structural deficit** at the best
available price.

### Collection cost: measured 10 credits/poll, not the 14 every projection assumed

Measured 2026-09-02 from real `x-requests-remaining` deltas across **16
consecutive live per-event prop polls** (all of Week 1, early tier, all 7 markets
requested): every single poll billed exactly **10 credits**, not the theoretical
14. The Odds API bills per *(market x region)* **that actually returns data**, and
not all 7 prop markets quote on every game this far out.

`DEFAULT_COST_PER_POLL = 14` is therefore a ~29% overestimate, and **every credit
projection in this repo inherits that error** — they are upper bounds, not
forecasts:

| Basis | Peak month | % of the 100K monthly cap |
|---|---|---|
| Theoretical, 14/poll | 36,288 | 36.3% |
| **Measured, 10/poll** | **27,408** | **27.4%** |

Two caveats that stop this from being over-claimed:

- **One observation, one tier, one week.** All 16 polls were early-tier at
  180-300h out, while books are still ramping (Pinnacle quoted only 2 of 16
  games). As breadth grows the blended cost should drift back toward 14. Treat
  10 as *today's floor*, not a season constant, and re-measure once every book
  is quoting every market.
- **`DEFAULT_COST_PER_POLL` was deliberately NOT lowered.** It gates
  `decide_props_poll`'s affordability check, where understating cost risks
  overspending. A conservative upper bound is the correct value for a budget
  gate; this measurement belongs in the projections, not in the guard.

### The design rule this implies

Every strategy tried here falls into one of two shapes, and the shape predicts
the outcome:

| Shape | Requires | Track record |
|---|---|---|
| **Probability estimation** | beating Pinnacle's own probability | props EV (null, 6,812 bets), prop projection (worse than base rate), moneyline model (**0 for 7**) |
| **Structural exploitation** | no probability estimate at all | props arb (65 real spots), correlated/team-total props (validated buckets), middling & steam (live-validated) |

Probability-estimation strategies must overcome 6.29% vig; nothing this project
has built supplies more than ~0 of it. Structural strategies exploit two books
disagreeing, a book pricing correlated legs as independent, or a line moving —
none of which require out-predicting Pinnacle.

**Before proposing a prop strategy, state which shape it is.** If it is
probability estimation, state where the >4.7% is coming from.

### Vig is measured, never assumed (2026-08-23)

`MEASURED_PROP_VIG = 0.0629` is now **reproducible**: `measure_prop_vig` in
`src/backtest/correlated_props.py` re-derives it from raw snapshots and returns
n=16,953, mean=0.0629 against Pinnacle — matching the documented sample exactly.
Previously the number could be quoted but not audited, and it had already been
wrong once (0.0575).

**It is deliberately NOT a default on any pricing function.** Vig varies by book —
per-book median overround runs 6.47% (betonlineag) to 7.80% (williamhill_us) —
and `bucket_edge` divides by `(1 + vig) ** 2`, so **vig enters squared**. Pricing a
williamhill_us bet at the pooled 6.29% understates vig ~1.5pp, which is roughly a
3pp edge error in the self-flattering direction. `bucket_edge`,
`naive_parlay_price`, `correlated_edge` and `price_bucket_bet` now all require an
explicit vig; `team_total_scan.measured_vig_by_event` measures it per event from
the same quotes being priced, and **skips any event whose vig cannot be measured**
rather than assuming one.

Live devigging never used the constant and never did: all four methods in
`src/devig/methods.py` derive vig from the two-sided quote handed to them
(`overround()` is `sum(q_i) - 1` on that quote), per contract per capture. The
live EV path devigs Pinnacle only and compares against the execution book's **raw**
price — the book's vig is paid, not modelled away.

### What to expect once Pinnacle starts quoting props (measured 2026-08-23)

Live props posted on 2026-08-23 for the 9/9 opener — 17 days out, far earlier
than the ~9/2 this project assumed. FanDuel and BetRivers are quoting;
**Pinnacle is not yet**. Three answers recorded here so a future session
recognises predicted behaviour instead of re-deriving it:

**1. The posting window needs no retuning when Pinnacle appears.** Simulated the
real `decide_props_poll` walk against the actual opener kickoff with Pinnacle
withheld until 4 days out: **34 of 34 slots used**, 27 captures after Pinnacle
appears, **23 inside the CLV-critical final 48h**. The poll targets are absolute
*hours-before-kickoff*, not intervals, so a lagging `poll_count` catches up and
then waits — early capture cannot steal slots from the pre-kickoff window.
Retuning `POSTING_WINDOW_DAYS` to Pinnacle's posting time would add risk and buy
nothing.

**2. Seasonal drift in their posting time is already absorbed** by that same
property, plus empty probes costing 0 credits and `poll_count` advancing only on
capture. Pinnacle posting at 14 days or 2 days, September or January, needs no
config change.

**3. Anchored EV will fire ~14 alerts/week, and they should not be expected to
convert.** Measured over 32,226 real historical contract-sides (57/game):

| Threshold | Sides firing | Rate | Per 16-game slate |
|---|---|---|---|
| ≥2% | 2,179 | 6.76% | ~61/wk |
| **≥5% (production default)** | **479** | **1.49%** | **~14/wk** |
| ≥10% | 24 | 0.07% | ~1/wk |

Those same spots tested **null** on 6,812 settled bets, and the vig table above
explains why. The signal stays `[EXPERIMENTAL]`-labeled and gated at 5%. A
stream of prop-EV texts starting the week Pinnacle appears is **the predicted
behaviour, not a finding**. It is worth watching rather than deleting only
because the live setting may differ from a single historical snapshot.

`health_check.prop_book_coverage` + the `monitor_run` one-time announcement exist
so Pinnacle's first appearance is surfaced explicitly — until then the anchored
paths return empty, which is indistinguishable from "no spots today".

---

## 1. Rest/travel differential — **tested, negative result**

Days-of-rest re-encoding (differential, short-week/bye-week binary flags) plus
genuinely new travel-distance and timezone-crossing features, computed from the
existing 2015-2024 schedule (no new data pull needed).

**Important framing, don't lose this:** `home_rest`/`away_rest` are already
inside the model's base `FEATURE_COLUMNS` (`src/model/train.py`) — every model
this project has ever evaluated, including all 5 prior negative results (GBM,
weather, garbage-time, expanded receiver/pass-rush, margin/total expansion),
already had raw rest-days as an input. So the rest-reencoding half of this is
a narrower bet than "new data" — it tests whether a nonlinear/threshold
encoding captures something the raw linear term doesn't. Travel
distance/timezone-crossing IS genuinely new information (nothing in this repo
had stadium coordinates before this).

**Built:** `src/model/stadiums.py` (44-stadium coordinate/timezone table,
haversine distance, `team_home_stadium_by_season` — derives each team's home
venue empirically from real schedule data rather than hand-tracking
relocations), `add_rest_travel_features` in `src/model/features.py`,
`REST_TRAVEL_FEATURE_COLUMNS`/`REST_TRAVEL_EXPANDED_FEATURE_COLUMNS` in
`src/model/train.py`. Smoke-tested against real 2015-2024 data — sane
distributions, zero nulls.

**Result (2026-08-21):** negative. Evaluated correctly from the start as
comparison #9 in the paired-permutation + Benjamini-Hochberg registry
(`notebooks/model_backtest_results.ipynb`) — ΔBrier=-0.0014 (candidate model
slightly worse than reference), p=0.84 uncorrected, nowhere close to
significant. The 6th consecutive feature-engineering attempt to fail in the
same direction (after GBM, garbage-time, expanded receiver/pass-rush,
weather, margin/total expansion). Full writeup: paper §6.4. Don't re-propose
rest/travel features for the moneyline model without new evidence.

## 2. Joint margin/total correlated distribution — **checked, premise doesn't hold**

`margin_model`/`total_model` price with *independent* Normal distributions.
The idea was to replace this with a joint bivariate model, on the assumption
margin and total correlate in real NFL games (blowouts skew totals).

**Checked before building anything (2026-08-21) — the correlation isn't
there.** Signed margin residual vs. total residual: r=-0.02 (calib split),
r=0.05 (test split), neither significant. `|margin|` vs. total (the more
plausible "blowouts suppress total via garbage time" mechanism, since signed
margin cancels home/away blowouts symmetrically): r=0.05-0.10 depending on
split, "significant" on the full 2,595-game sample (p=0.01) but R²≈0.002-0.01
— under 1% shared variance, and inconsistent across splits. Too small and too
unstable to justify a joint-distribution pricing model; the independent-Normal
assumption already in place isn't a real gap. **Don't re-propose without new
evidence.**

## 3. Steam detection — **built and live-validated**

Distinct signal from both existing live tools: not one book's price drifting
alone (`src/backtest/middling.py`'s target) and not one book vs. Pinnacle
(`src/signal/live_scan.py`'s target), but *synchronized* rapid movement
across multiple books at once — a classic sharp-money tell.

**Built (2026-08-21):** `src/backtest/steam.py` (detection + pricing, reuses
`middling.py`'s `win_interval`/`pinnacle_reference_line` and `sizing.py`'s
EV/Kelly math directly rather than reinventing it), `src/backtest/steam_scan.py`
+ `make steam-scan-once` (manual scan, same reasoning as middling for staying
manual — no live track record yet). 24 new tests.

**First live smoke test found 5 real opportunities immediately** — small
(EV $0.009-$0.010, stakes $0.34-$0.42) but real, on real execution-book
prices, confirming the full pipeline works end-to-end. Same honest ceiling
as middling: real and correctly priced, not yet a claim about long-run edge.
Full writeup: paper §4.11.

## 4. Player-prop middling — idea, blocked on live props posting

`src/backtest/middling.py` is explicitly scoped to SPREAD/TOTAL only today
(`win_interval` raises on `PLAYER_PROP`). Extending it would reuse almost all
existing code (OVER/UNDER is already structurally supported), but needs real
live multi-poll prop odds — the props scheduler is built
(`src/collect/props_scheduler.py`) but props don't start posting until
~9/2 for the 9/9-10 Week 1 opener. Natural next step once that data exists,
not buildable meaningfully before then.

## 5. Referee tendencies — **checked, no signal found (correcting an earlier wrong "blocked" claim)**

This was previously listed under "blocked on data" below with the claim that
nflverse doesn't carry usable referee data. **That was wrong, never actually
checked.** `data/static/schedules_2015_2024.parquet` has a real `referee`
column: 2,742/2,743 games populated, 32 distinct referees, 95-167 games each
across all 10 seasons — a genuinely usable sample, already cached, zero new
data needed.

**Checked directly (2026-08-21), three ways, all null:**
- Game-level margin/total residuals (from the existing fitted models) by
  referee, 852 holdout games, 18 refs with ≥15 games each: ANOVA F=0.72,
  p=0.79 (total); F=1.15, p=0.30 (margin).
- The props-relevant version of the hypothesis (ref tendencies -> game flow
  -> props, not just final score): total passing yards and total receptions
  per game by referee, 2,658 games, 26 refs with ≥40 games each: F=0.81,
  p=0.73 (passing yards); F=0.79, p=0.76 (receptions).
- Penalty-call rate (the most mechanistically direct link) isn't checkable
  with this project's cached play-by-play — a trimmed 29-column version with
  no penalty fields. Would need a fresh (free) nflverse pull to test
  properly, but given the aggregate outcome checks above are already flat,
  not prioritized — if penalty tendencies mattered, *some* signal should
  have shown up in aggregate passing yards, and none did.

**Don't re-propose without new evidence** — same standing rule as the other
negative results. If ever revisited, the penalty-rate pull is the one
untried angle, not a retry of the outcome-level checks already done here.

---

## 6. Individual pass-rush rating — **built, corrects an earlier wrong "not buildable" claim**

`src/model/pass_rush_elo.py`'s docstring claimed individual-level pass-rush Elo wasn't
buildable on free data at all (no participation/exposure data). That was true using
only nflverse's own trimmed play-by-play, and never checked against nflverse's full
table menu. It's wrong: `load_pfr_advstats(stat_type="def")` (real per-player pressure
counts) joined against `load_snap_counts`'s `defense_snaps` (100% ID match rate) gives
a real denominator for true pass-rush positions (DE/DT/NT/EDGE/OLB), 2018+ coverage.

Built as `src/model/individual_pass_rush_elo.py` (2026-08-21) — rate-based per-game
Elo vs. a fixed 1500 baseline, base rate 3.84%/snap measured fresh from the cache.
Sanity-checked: mean rating 1501.1, leaderboard top (Hendrickson, Hutchinson, Garrett,
Bosa, Jones) and bottom (Payne, Hankins, Nnadi, Stewart — run-stuffing DTs) both match
real football knowledge. 12 tests passing. See `individual_pass_rush_elo` memory.

Not itself a betting strategy yet — a rating, same status as team-level pass-rush Elo
and receiver Elo (standalone infrastructure, not wired into pricing). Next step if
pursued further: sack-prop / QB-pressure-prop pricing using this as a feature.

---

## 7. Training-window size — **checked, real effect, first non-Elo comparison to survive BH correction (in the negative direction)**

Directly answers "are we using the full potential of the free data" — never actually
tested before (only feature *content* was tested in #1-#6/the 6 failed feature
attempts, never window *size*). Uses only already-cached `schedules_2015_2024.parquet`
/`pbp_2015_2024.parquet` — zero new pull, nothing contingent on the Aug 22 Odds API
credit reset (that's a separate data source, historical prop lines).

3 window configs, same fixed holdout (`calib=[2022]`, `test=[2023,2024]`,
`COMBINED_QB_FEATURE_COLUMNS`) as every other comparison; Elo/QB Elo recomputed from
scratch per window (ratings restart at 1500 from the window's own start season, a
faithful "what if we'd only ever had N years" simulation, not a row-count truncation):

| Window | Train seasons | Games | Test Brier | Δ vs 7yr full | p-value | BH q=0.05 |
|---|---|---|---|---|---|---|
| 3yr_recent | 2019-2021 | 788 | 0.2265 | +0.0095 worse | **0.998** | survives (as a real degradation) |
| 5yr_mid | 2017-2021 | 1285 | 0.2173 | +0.0003 worse | 0.63 | no (noise) |
| 7yr_full (baseline) | 2015-2021 | 1743 | 0.2170 | — | — | — |

Test set (570 games) verified byte-identical across all 3 configs via an in-notebook
assertion. Final Elo rating mean landed at 1502.5 in all three (well-calibrated, no
drift).

**Result: cutting training to 3 recent seasons is a real, robust degradation — not
noise (p=0.998, essentially the extreme tail of the permutation null). 5 seasons is
statistically indistinguishable from 7 (p=0.63) — no measurable penalty from dropping
2015-2016.** More history does matter, but with clear diminishing returns past ~5
years within the currently-cached range. This does NOT test whether pre-2015 data
(the R packages' 1999+ range) would help further — that's a separate, larger pull,
still out of scope today; this experiment could only test cutting the existing window
down, not extending it further back.

---

## 8. Mainline historical odds pull — **executed, gap confirmed real but numerically inconsequential**

Every one of the 11 comparisons above (#1-#7, plus base Elo/GBM/garbage-time/QB Elo)
scores "model vs. market" against **nflverse's own `home_moneyline`/`spread_line`
columns** — `src/model/train.py`'s own docstring already flags this as "NOT confirmed
to be Pinnacle." Every historical Odds API pull this project has done or planned
(`props_historical.py`) has been player-props only — there has never been a
game-level (h2h/spreads/totals) historical odds pull, so the "market baseline" every
comparison above is benchmarked against has never been swapped for a confirmed-sharp
price. Caught 2026-08-21 by the user directly questioning the rigor of the testing
mechanic.

Raised and rejected once before (2026-08-17) on the grounds that the Odds API's
historical archive only starts 2020-06-06, so most of the 2015-2021 training window
can't be Pinnacle-confirmed at any price. Still true — but that rejection
under-weighted that **the current test set (2023-2024) is 100% inside the reachable
2020+ range**, and #7 above just showed a 5-year training window performs identically
to the full 7-year one, making a recent-years-leaning setup newly attractive rather
than hypothetical.

**Cost:** mainline markets (1-3 markets) are far cheaper than props (7 markets) — ~30
credits/game vs. ~101/game. Pulling closing-line Pinnacle odds for the 570 test-set
games (2023-2024) would cost ~17,100 credits.

**Executed 2026-08-22.** Built `src/collect/mainline_historical.py` (reuses
`transform.py::event_to_snapshots`, the live mainline parser). A 3-game test caught a
real mistake before the full spend: `regions="us"` returns **zero Pinnacle** (only
`eu` has it) — fixed, cost came in at ~61 credits/game (2x the original 30/game
estimate). Full run: **570/570 games, 0 failures, 570/570 with real Pinnacle
coverage**, 34,772 credits.

**Result: the gap was real but numerically inconsequential.** Re-scored the
market-baseline reference in `model_backtest_results.ipynb` against real Pinnacle
instead of nflverse's column. `market_baseline_real_pinnacle` Brier = 0.209724 vs.
`market_baseline_nflverse` = 0.209862 — a difference of 0.000138, dwarfed by the
0.007-0.022 gap between either market baseline and every model tested (best model,
`epa_elo_qb`: 0.216964). Correlation between the two baseline sources across all 570
games: 0.9976 (mean abs diff 1.0%, max 5.2%, only 1 game >5%). **Every conclusion
this project has drawn from "the market beats the model" holds regardless of which
market source is used** — the unconfirmed-source concern was legitimate to raise and
worth checking, but didn't change any finding once actually measured.

---

## 9. Team-total rushing/passing O/U vs moneyline — **built, validated, real underdog-bucket edge found**

The natural extension of `correlated_props.py` once real per-player Pinnacle prop
lines exist for enough games: does a team's real *market-implied* total rushing/
passing output correlate with its real *market-implied* win probability beyond what
independent pricing predicts? If the books aren't jointly calibrating these, that's
a genuine, real mispricing mechanism -- the user's own framing for why this is worth
building, not just another leg-pair variant of the existing pooled sweep.

**Why this needed its own design pass, not a quick add-on to `correlated_props.py`:**
the existing methodology's legs are fixed-threshold booleans (leading rusher clears
100 yards, QB throws 2+ TDs) checked against *population base rates* or a single
real market probability (`team_market_prob`, moneyline only). "Team total rushing/
passing yards" isn't a market Odds API posts directly -- there's no single quoted
line to devig. And real per-player lines almost never sit exactly at the fixed
100/75-yard thresholds already validated, since props post for every roster player,
not just the leading one.

**Design decisions made (2026-08-22, via direct back-and-forth, not assumed):**
1. **Legs are redefined around the real book line, not the fixed threshold.** Instead
   of "cleared 100 yards," each leg is "cleared its own real market-implied
   threshold" -- more market-native, avoids interpolation, but is a genuinely new
   leg definition, not directly comparable to the already-validated underdog/narrow
   buckets (which used the fixed thresholds).
2. **Team total = sum of each eligible player's own real posted O/U line**, not a
   synthesized single number invented from scratch -- uses the book's own set points
   directly.
3. **v1 includes real pricing/EV, not just a correlation/lift check.** Requires
   synthesizing a team-total *distribution* (assume each player's yardage is
   Normal around their own line, sum across players **assuming independence
   between teammates** -- a real, stated v1 simplification, not hidden: running
   backs likely have some negative correlation via shared touches, unmodeled here),
   then assigning the resulting team-total leg a vig via the same `MEASURED_PROP_VIG`
   constant (5.75%) the rest of this module already uses, rather than inventing a
   separate vig model.
4. **Data: pull the matching 2023 props batch first** — **executed 2026-08-22, same
   day as scoping.** 285/285 games, 0 missing/failed/malformed, ~28,808 credits (a
   2-game test confirmed Pinnacle first). This analysis now has the full 570-game
   2023-2024 overlap the mainline historical pull already covers, matching it
   exactly.

**Real risks to watch when building, stated up front:**
- The independence-across-teammates assumption is the single biggest simplification
  -- if it's wrong in a specific, correctable direction (e.g., a bell-cow back who
  vultures nearly all carries makes teammate correlation near-irrelevant, but a
  committee backfield doesn't), the synthesized team-total price could be
  systematically miscalibrated in a way this v1 won't detect on its own. Worth a
  sanity check (does the synthesized team-total's realized hit-rate land near 50%,
  the same "check the mean before trusting" discipline every Elo/pricing build in
  this project already follows) before trusting any edge number it produces.
- Passing yards has a much more natural "team total" reading (usually one real
  starting QB per team per game) than rushing (often 2-3 backs with real shared
  touches) -- the passing-yards version of this leg is likely more trustworthy than
  the rushing-yards version out of the gate.

**Built and run 2026-08-22 — same day as scoping.** `src/backtest/team_total_props.py`
(3 functions: `build_team_total_lines`, `fit_team_total_residual_std`,
`team_total_over_indicator`), 9 tests, reuses `correlated_props.py`'s
`measure_leg_correlation`/`measure_leg_correlation_by_bucket`/`bucket_edge` unchanged.
One real design refinement made during the build, not in the original scope: instead
of summing assumed per-player variances under an independence assumption (needs
unknown per-player sigma, and the assumption is known-wrong), `fit_team_total_residual_std`
calibrates ONE real team-level residual std directly from
`actual_team_total - implied_team_total_line` on real historical games — same leg
definition, same sum-of-lines threshold, same pricing goal, just measured instead of
guessed. Found a real, large systematic bias worth knowing about: summed player
lines under-count real team totals by **+38.3 yards (rushing)** and **+10.1 yards
(passing)** on average — expected, since only players with a posted prop line get
summed, missing backup-RB/scramble/jet-sweep yardage; correctly bias-corrected
before pricing, not ignored.

**Result: real, and it replicates the exact same pattern the fixed-threshold legs
found, using an independently-constructed leg definition.**

| Stat | Bucket | n | Lift | p-value | Priced edge | 2023→2024 OOS |
|---|---|---|---|---|---|---|
| rushing | underdog | 473 | 1.192 | 2.8e-5 | **+5.5%** | 1.226→1.167 (holds) |
| rushing | favorite | 303 | 1.091 | 2.6e-4 | -3.4% | 1.129→1.051 (shrinks, same leak as before) |
| passing | underdog | 410 | 1.276 | 6.0e-5 | **+12.9%** | 1.311→1.216 (holds) |

Permutation test (assumption-free, 10K shuffles): rushing pooled p=0.0001, passing
pooled p=0.029 — both confirm the chi-square result independent of its asymptotic
assumption. Folded into the existing 57-p-value BH-correction family (now 67) rather
than a fresh one — 58/67 survive, all 3 significant team-total tests included.

**Verdict: underdog-bucket team-total-clearing-its-own-line is a real, validated
finding for both rushing and passing — same status as `correlated_props.py`'s own
underdog/narrow buckets** (chi-square + permutation + honest out-of-sample, all
three). The favorite-bucket rushing result repeats the EXACT failure mode
`portfolio_validation` already found for the fixed-threshold legs: significant
pooled, doesn't clear vig, shrinks out-of-sample — not tradeable, don't treat it as
one. **Same honest ceiling as the original correlated-props edge numbers:** no real
posted price exists for "sum of individual player lines," so this confirms the
correlation mechanism is real, not a confirmed live exploit. Full write-up: paper
§4.5 (new subsection), `notebooks/model_backtest_results.ipynb` (new section, 6
cells).

---

## 10. High-vig markets — **checked, hypothesis reframed, anytime-TD confirmed unpriceable**

**The hypothesis (worth stating fairly, because it is a good one):** published
figures put player-prop vig near 12%, well above the 6.29% here. A book quoting
wide is a book that is less sure of itself, so wide markets should hold more
mispricing and therefore more edge.

**First finding: the 12% is not comparable to our number.** Measured across all
**228,146** real two-sided contracts in the store: median overround **6.93%**,
p99 **8.17%**, and **zero contracts at or above 10%**. One-sided dropout is
0.05%, so nothing wide is being filtered out. Live props run 6.54–7.38%. The
published 12–20% figures describe *multi-way* markets, a different construct
with a different denominator — see the anytime-TD result below.

**Second finding, and the reusable one: vig does not predict structural
opportunity here — line standardization does.** Correlation between per-book vig
and cross-book arb rate across our 5 stats is **−0.954**; the *lowest*-vig
markets carry the most opportunity.

| prop_stat | per-book vig | best-of-books | shopping gain | arb rate | distinct lines |
|---|---|---|---|---|---|
| receptions | 6.71% | 4.45% | 2.26pp | 3.00% | 11 |
| passing_tds | 6.72% | 3.18% | 3.54pp | 4.40% | 4 |
| receiving_yards | 6.93% | 6.51% | 0.42pp | 0.41% | 121 |
| rushing_yards | 6.93% | 6.28% | 0.64pp | 0.60% | 135 |
| passing_yards | 6.98% | 6.54% | 0.43pp | 0.24% | 161 |

The mechanism is **not** books disagreeing more. It is that few distinct lines
force every book onto the *same* contract, so prices are directly comparable.
Yards markets spray across 121–161 lines, matched pairs are rare, and there is
little to arb even when prices differ. `ARB_MARKETS` was already set to exactly
the two standardized markets — this explains *why* that worked.

**Honest limit:** our vig range is 6.71%–6.98%, a 0.27pp window, and n=5 stats.
That correlation cannot be extrapolated to a 12% market. The properties also come
apart at anytime-TD, which is high-vig *and* perfectly standardized. So the
question was settled by measurement, not inference.

**Third finding — anytime-TD is structurally unpriceable, on real evidence.**
A 2-credit live probe (2026-08-23, NE @ SEA) returned 3 books and 63 outcomes,
**all "Yes", zero "No" at any book**. This upholds an earlier call made
2026-08-17, but that one rested on a single preseason observation when only
DraftKings had posted anything; it is now evidenced.

The deeper reason the earlier note missed: **anytime-TD is not a partition.**
Multiple players score, so summed Yes probabilities came to **4.83–5.29 per
book** — the expected *number* of TD scorers, not 1.0. So `sum(q) − 1` is not an
overround either. **With no complementary price and no partition, this market's
vig cannot be measured from prices at all.** Any "TD props run 12–20%" figure is
model-derived, not observed.

Books do disagree substantially — up to **10.0pp** of implied probability on the
same player (DK +115 / FD +130 / WH −115). But one-sided quotes cannot be arbed
or middled, so capturing that requires estimating the true probability: the
strategy shape with a 0-for-7 record here, against a vig you cannot even measure.
**Verdict: park.** Reopen only if a book starts posting "No" prices.

**Free byproduct — the API bills on markets RETURNED, not requested.** A probe
requesting only `player_rush_tds,player_reception_tds` (which have never returned
a row in 462,331 snapshots) cost **0 credits**. Those two dead markets in
`PROP_MARKET_TO_STAT` are not wasting any budget; leaving them in place is free.

---

## Middling and steam vs real 2024 movement — mostly NEGATIVE (2026-08-23)

First evaluation of both structural strategies against real line movement rather
than synthetic data. Run through `find_middle_opportunities` /
`find_steam_opportunities` (execution books only, EV-priced) in a **single** call.

| season | series? | middles | median EV | positive-EV |
|---|---|---|---|---|
| 2023 | no (single snapshot) | 372 | **−0.1252** | **1%** |
| 2024 | **yes, 105 games** | 399 | **−0.1228** | **10%** |
| 2026 | yes, live | 16 | −0.0858 | 12% |

**The overwhelming majority of detectable middles are negative EV.** Even with a
real time series, only ~10% of 2024 windows price positive. Direct outcome test
on the 105 purchased games: hit rate **6.7%** (7/105), mean P&L **+3.4%** per
$1/$1 pair, **95% CI (−4.2%, +12.2%)** — not significant.

**What the series did buy:** 2024's positive-EV share is **10% vs 2023's 1%**, so
line movement genuinely surfaces ~10x more real middles than single-instant
cross-book disagreement. Real, but small, and not enough to validate the strategy.

**Steam: 6 detections across 105 games — and the sampling is wrong for it.**
Steam needs ≥3 books moving within a **1-hour** window; our purchased snapshots
are **~24 hours apart**, so books only ever appear to move "simultaneously"
because we observe them at the same 5 timestamps. Steam is a minutes-scale
phenomenon and is **not measurable at this density** at any sample size. Only the
live 30-minute arb tier can evaluate it.

### Two analysis errors made and corrected on the way here

1. **Scanning in a loop double-counted massively.** `find_middle_opportunities`
   scans the WHOLE store per call; calling it once per game and concatenating
   reported **54,268 middles across 451 games** when only 105 games have a series
   and no spreads were even purchased. The tells were 451 > 105 and the presence
   of `spread` rows. One call gives 787.
2. **A raw `best_middle_for_game` sweep said "105/105 games, median 2.5pt".**
   That used every book including ones with no account, and ignored EV entirely.
   The realistic figure is the EV-priced execution-book table above.

## Real historical line movement bought (2026-08-23) — an old claim was wrong

**Ten places in this repo said historical CLV was "structurally impossible ... at
any sample size". That was a COST statement misfiled as an impossibility.**
`get_historical_event_odds` accepts an **arbitrary `date`** and returns the
nearest 5-minute snapshot, so a time series was always purchasable. Only the
close had ever been bought, because each historical call bills 10x. Nobody
priced the alternative.

**What was bought:** 104 games (+1 probe) of 2024, five offsets — T-120h, 72h,
48h, 24h, 6h — on `h2h,totals` over `us,eu`, paired against the ~15-minute close
those games already owned. **43,236 snapshots, 0 missing / 0 failed / 0
malformed, 20,904 credits — exactly the estimate.** Result: 105 games with a
clean 6-point Pinnacle series across ~23 books, on both moneyline and totals.

Funded from grant remainder that expires at the 9/1 reset with no rollover, so
it cost the season nothing. Balance after: 3,959.

### What it shows

**Lines move, substantially.** Median |Δ fair probability| from T-120h to close is
**2.29 points**; 72% of games move >1pt and 39% move >3pt. Movement shrinks
monotonically toward kickoff (2.74% → 1.18% mean), which is the convergence the
whole CLV thesis assumes. The raw material for rolling-CLV strategies is real.

**The premise is directionally supported but UNDERPOWERED — not proven.** The
close forecasts the result better than the earlier line at all five horizons
(Brier improvement +0.001 to +0.0028), **but every 95% CI includes zero.** Best is
T-48h: +0.00275, CI (−0.00143, +0.00726). Five-for-five positive signs look
suggestive, but the windows are nested on the same 105 games, so that is not an
independent test and must not be reported as one. More power needs more games,
which needs credits we no longer have.

**This measures the MARKET, not a strategy.** It shows the line drifts. Capturing
that drift still requires predicting *which way* — which is the probability-
estimation problem this project has failed at 7 times.

### Two analysis bugs caught before believing the output

1. Including both sides made `beat_rate` exactly 0.5000 at every offset — devig
   forces `p_home + p_away = 1`, so the sides are exact mirrors. A metric that
   cannot come out otherwise is not evidence. Now home-side only, measured
   directionally against the actual result.
2. The T-6h entry window `(0, 12)` swallowed the close itself at 0.66h, making
   entry == close and CLV identically 0. Entry windows now exclude `CLOSE_MAX`.

### Still not possible

**Props.** At 7 markets a prop series is ~700 credits/game, so the remaining
budget buys ~5 games. Props rolling CLV stays a live-forward measurement.

---

## CLV power: the paper's n≈3140 rests on an ASSUMED sigma, and the real one is 3-7x smaller

**Corrects a load-bearing claim in this project's own honesty framing.**
`paper/nfl_clv_case_study.md` §4.7 states that a 0.5% mean-CLV edge needs
**n≈3140** bets, "well beyond what one NFL season of a few hundred bets can
confirm." That number is reproducible from the paper's stated inputs -- 
`power_analysis(0.005, 0.10**2)` returns exactly 3,140 -- which shows the **10%
bet-to-bet noise was assumed, never measured.**

Measured 2026-09-03 off the purchased 2024 Pinnacle mainline series (the 5-offset
pull, 105 games), sigma is the sd of `close_fair - entry_fair` across games:

| Entry | n games | sd(CLV) | n for 0.5% | n for 1.0% |
|---|---|---|---|---|
| T-120h | 97 | 0.0351 | 388 | 97 |
| T-72h | 105 | 0.0334 | 350 | 88 |
| T-48h | 103 | 0.0248 | 194 | 49 |
| T-24h | 105 | 0.0206 | 133 | 34 |
| T-6h | 105 | 0.0143 | 65 | 17 |

The paper's assumed 0.10 is **2.8x to 7.0x** the measured value, and since
`n` scales with sigma-squared, its sample requirement is overstated **8x (at a
T-120h entry) to 48x (at T-6h)**.

### What this changes, and what it does not

**Changes:** "one season can never confirm a CLV edge" is not supported by this
project's own data. At a realistic ~6 qualifying alerts/week over an 18-week season
(~108 bets), a **1% edge is detectable from any entry horizon** (n=17-97), and a
0.5% edge is detectable if entry is inside ~T-48h (n=65-194 vs 108 available -- so
T-24h and T-6h clear it, T-48h does not).

**Does not change:** nothing here says an edge EXISTS. This is only the sample size
needed to find out, and detecting CLV is not the same as profit.

### The horizon tradeoff this exposes -- the part worth actually thinking about

sigma **falls monotonically** as entry approaches kickoff (0.0351 -> 0.0143), so
late entry needs far fewer bets for the same power. But late entry also leaves less
line movement left to capture, which is the very thing CLV measures. **Entering
early maximises the available edge and the noise simultaneously.** This is a real
design tension in the betting policy and it has never been stated anywhere in the
repo. It is not resolved here.

### An error caught in-flight, recorded so the table above is not misread

The first pass at this reported sigma=0.0143 labelled as a **T-48h** entry and
concluded n=65. Wrong label: the entry window was `(2.0, 51)` hours and the helper
takes `.iloc[-1]` -- the LATEST capture in the window, i.e. the one nearest kickoff.
That is a T-6h entry, not T-48h. The real T-48h figure is sigma=0.0248, **n=194**,
three times larger. Any future reuse of a single sigma must state the entry horizon
it was measured at; a bare "CLV sigma" is meaningless.

---

## Prop price persistence at the alert latency — MEASURED 2026-09-03, first live movement data

**The first pre-kickoff prop movement this project has ever held.** Every
historical prop row is a single ~20-minutes-to-kickoff snapshot, so price
persistence was structurally unobservable until the live 2026 series accumulated
multiple captures per contract. 18,427 consecutive-capture pairs across 3,480
contract-sides.

**Conditioned on the gap between observations** — the confound that has to be
removed first, because a 3-day gap moving more than a 30-minute gap is a gap-length
effect, not a horizon effect:

| Gap | Pairs | Price changed | Line moved | Median move |
|---|---|---|---|---|
| **~30 min** | **13,519** | **1.9%** | **0.6%** | 5 pts |
| 2-8h | 1,514 | 13.7% | 5.6% | 4.5 pts |
| 8-26h | 2,355 | 29.0% | 15.4% | 4 pts |
| 1-4d | 979 | 35.3% | 28.6% | 5 pts |

**At the ~35-minute detection latency, 98.1% of prop prices and 99.4% of lines are
unchanged.** The execution books are the *most* stable of all: DraftKings 0.25%,
BetRivers 0.31%, FanDuel 0.94% price-change rate over 30 minutes.

### What this does and does not license

**Does:** it removes latency as the presumed blocker on acting on alerts in the
early window. The earlier framing — that ~35 minutes "decides whether any of this
works" — is not supported at this horizon.

**Does NOT:** every pair here sits **177-422 hours before kickoff (7.4-17.6 days)**,
because that is all the live series covers so far. The arb tier polls every 30
minutes inside 12h precisely because movement is expected to concentrate there, and
**that window remains entirely unmeasured.** Do not read 98.1% as an arb-window
survival rate. Re-run this against the final-12h captures after Week 1; that is the
number that actually governs whether arb is capturable.

### Two book-level oddities worth remembering

- **Fanatics reprices 10-100x faster than anyone else**: 21.3% at 30 minutes vs
  0.25-1.7% elsewhere. It is *not* in `live_scan.EXECUTION_BOOKS`, so it does not
  reach the arb/EV scanners — but it is being stored, and any future analysis
  pooling books without splitting it will inherit its volatility.
- **Bovada changed 0 times in 740 pairs.** Exactly zero is more consistent with a
  stale or slowly-refreshed feed than with a real market. Treat its quotes as
  suspect until something confirms they are live.

### An analysis artifact caught in-flight, recorded so it is not repeated

The first cut reported **0.0% line movement at every gap including >4 days**, which
is obviously wrong. Cause: `line` was in the grouping key, so a line change created
a *different* group and could never register as movement within one. Line movement
must be grouped on `event/player/stat/side/book` **without** `line`. The corrected
figures are the ones tabled above. The same shape of mistake — a metric that cannot
come out any other way — has now bitten this project three times (`beat_rate` fixed
at 0.5000 by devig symmetry; the T-6h entry window swallowing its own close).

---

## Props rolling CLV: the schedule cannot currently produce a CLOSE for 5 of 7 markets

Found 2026-09-02 while checking whether the live props series can feed a props
version of `scripts/rolling_clv_2024.py`. **The entry windows all work; the close
does not exist.**

`rolling_clv_2024.py` needs a capture within `CLOSE_MAX = 2.0h` of kickoff. Our
prop schedule's dense (all-7-market) tier bottoms out at **4.0h**, and everything
below that is the **arb tier, which requests only `player_receptions` and
`player_pass_tds`**:

```
lowest FULL-market capture : 4.0h before kickoff
lowest ARB-market  capture : 0.5h before kickoff
CLOSE (<= 2.0h): full markets -> NONE.  arb markets -> 2.0, 1.5, 1.0, 0.5
```

Entry offsets are fine — T-120/72/48/24h land exactly on sparse/dense targets,
and T-6h is covered by the 8.0h and 4.0h dense captures.

**Consequence: props CLV — this project's headline metric — is computable for
`receptions` and `passing_tds` only.** The other five (`pass_yds`, `rush_yds`,
`rush_tds`, `reception_yds`, `reception_tds`) would have an entry series and no
close, which yields nothing. This is not a bug in the CLV code; it is the arb
tier's market-narrowing (a deliberate cost optimisation for a *different*
signal) silently deciding what CLV can measure.

**It is also time-critical and irreversible.** Week 1 kicks off 2026-09-10. A
close not captured is not re-buyable at any price — the historical endpoint sells
5-minute snapshots, but at ~700 credits/game for a full prop series, which is why
props rolling CLV was deferred to live-forward measurement in the first place.

**Proposed fix (not yet applied):** promote the existing 1.5h arb target to a
full-market capture, so every prop market gets one quote inside `CLOSE_MAX`.
Measured cost:

| | Peak month | % cap |
|---|---|---|
| Current | 27,408 | 27.4% |
| + full-market close @1.5h | 27,780 | 27.8% |

**+0.4pp**, and poll count stays 55 because it replaces the arb-only target at
that offset rather than adding one. The arb tier keeps its 0.5h/1.0h/2.0h
captures, so nothing the arb signal depends on is lost.

## Code review, 2026-08-23 — 13 findings, all fixed

A `/code-review` pass over this session's work found **9 findings, 3 HIGH**, with
**zero overlap** against the 4 an inline self-review had found. Every HIGH was a
bug introduced that same session. All were verified by execution before fixing.
Worth recording honestly: two of them were in code written *specifically to
improve correctness*.

**HIGH — could cost money or corrupt a verdict**

1. **`corrects` never matched, so the bankroll double-counted.** Pydantic writes
   `placed_at` as `...Z`; `active_bets` compared against `.isoformat()`
   (`...+00:00`). A value copied out of `bet_log.jsonl` — the only place a human
   can get it — never matched, so the superseded row survived and `settle_bets`
   counted its stake and P&L twice. The original test passed only because it
   built `corrects` in Python instead of reading it back from the file: it
   validated the implementation, not the workflow. Now compared as parsed
   instants, with a round-trip test.
2. **CLV was computed for games that had not kicked off.** "Last quote at or
   before kickoff" is satisfied by every row while kickoff is in the future, so
   the current quote became a fake close — a bet 3 days out reported
   `clv_probability = +0.143`. `season_review` feeds these to the CUSUM detector,
   so a strategy could be retired on lines still moving. Now gated on
   `kickoff <= as_of`.
3. **Making `vig` required broke three notebook call sites** (cells 93/100/105)
   — fixed in `src/` and `tests/` but not the notebook, *while editing that same
   notebook*. Cell 95's already-queued re-run would have died at cell 93.

**MEDIUM**

4. **`measure_prop_vig` paired over/under from different moments** — `.last()`
   per side independently pairs a fresh over with a stale under. Measured: **22%
   overround reported where the truth was 4%.** It feeds `bucket_edge`, where vig
   is **squared**. Now pairs on a single `capture_time`, the rule
   `live_scan._latest_two_sided_pinnacle` already documents. (The constant still
   reproduces exactly — n=16,953, mean 0.062891 — because the historical pull has
   one capture_time per game; the fix matters for the live store.)
5. `LoggedBet` accepted impossible market/side combinations, and props with no
   player/stat/line that could never settle. Now rejected at entry.
6. `settle_bets` had no per-bet error isolation — one bad row hid every other
   bet's P&L. Now degrades to `outcome=None`, matching `monitor_run._safe`.
7. `season_review` never computed roi/bettable: `review_strategy` gates on
   `{fair_prob, price_decimal, won}` and `bets_to_frame` emitted none of them, so
   `roi` was always None while `make season-review` advertised bettability.
   Verified fixed: roi=0.321 at n=120.
8. `make log-bet` had no `--placed-at` (so the entry anchor was the *logging*
   time, biasing CLV) and no `--corrects` (making the correction workflow
   unreachable). Both added.
9. Props freshness had no sub-6h tier: a 12h allowance spanned the whole 48h
   window while the collector polls every 30 min inside 6h, so a props death
   under 12h before kickoff was never flagged at all. Added an arb tier (3h).
10. `sync_architecture`'s row regex (`\w+`) could not match the multi-value
    status the script itself emits (`**LIVE / MANUAL**`), so such a row would be
    skipped and never re-synced — the exact drift it exists to prevent.

**LOW:** `n_player_lines` counted both teams while the alert presented it as
evidence for one side (renamed `n_event_player_lines`); an ARCHITECTURE Notes
cell contradicted its generated Reach; `kickoffs_from_store` was moved from
`bet_log` to `pit_store` so the live alerting service no longer imports the
backtest engine.

## Alert state is now pruned (2026-08-23)

`data/alert_state.json` was **never cleaned by anything** and had grown to 874
entries / 124KB — **866 of them for already-played 2023-24 games**, residue from
the pre-`upcoming_only` alert bug. Verified the bug itself is genuinely fixed:
`find_live_prop_ev_spots` and `find_live_prop_arb_spots` both return 0 against
the live store, and the 874 sends were logged at 04:26 today, before the fixed
code was picked up on service restart.

**Pruning keys on KICKOFF, not alert age — and this distinction is the whole
point.** Age was the obvious first cut and it silently did nothing: that bug
fired *today* on games from 2023, so every stale entry carries a recent
`alerted_at` and an age filter keeps all 866. A live run proved it (874 -> 874,
nothing removed) before the approach was corrected. What makes an entry dead is
that its event has started.

- `event_id_from_alert_key` handles all three key shapes in use:
  `event|side|book`, `ev|event|...`, `arb|event|...`.
- Sentinels (`__`-prefixed, e.g. `__pinnacle_props_arrival__`) are **never**
  dropped — they are one-shot latches, and ageing one out would re-fire an
  announcement that must happen exactly once.
- Unresolvable keys fall back to a 30-day age cap, so an unknown key shape still
  cannot accumulate forever. 30 days deliberately exceeds the 21-day props
  posting window, which bounds how far ahead of kickoff an alert can fire.
- `monitor_run` persists on **prune OR send**. Saving only on send would leave
  the prune in memory and redo it every cycle forever, so the file would never
  actually shrink.

Result on the live file: 874 -> 8 entries, 124,686 -> 907 bytes, every survivor a
real upcoming Week 1 alert.

## Pre-kickoff only: enforced in both props paths (2026-08-23)

**No live prop is ever polled after kickoff.** Every strategy here is priced
entry-vs-close, and in-play prop books re-price on every snap, so an in-play
quote is expensive (a full per-event call) *and* methodologically useless.

Audit of every caller of the per-event odds endpoint:

| Caller | Guard |
|---|---|
| `collect/props_scheduler.py` | `decide_props_poll` -> `event_started` (`props_budget.py:385`). Fires **before** the budget check, so no API call is made. Was **untested**; now covered, including a test that the ordering holds — a well-funded key must not buy in-play polls. |
| `collect/props.py` (manual `make props-poll`) | **Was unguarded.** Its filter tested only `commence_time <= cutoff`, which a game that kicked off an hour ago still satisfies. Now `select_pollable_events` requires `now < kickoff <= now + days_ahead`. |
| `collect/props_historical.py` | Historical endpoint — past games are the point. PARKED. |

**Empirically clean:** 0 of 456,480 prop rows (and 0 mainline rows) have
`capture_time > event_start_time`. The manual-path gap was latent, never fired.

**Second defect found in the same function:** `props.py` built its client from
`config.api_key`, which is `ODDS_API_KEY` — the **free** tier the mainline
collector runs on (~500/month, 341 left). One manual props sweep at ~14 credits x
16 games would have wiped it and silently stopped mainline collection. It now
requires `ODDS_API_KEY_PAID` and hard-fails without it, matching `props_run.py`.
This was a direct violation of the standing "do not mix the keys" constraint,
sitting in a `make` target.

## Housekeeping backlog (low priority, not methodology)

- **~~2,752 conflicting historical prices~~ CORRECTED: the real count was 1, and
  it is now fixed.** The original reading was an analysis error of mine, not a
  data defect: the duplicate key omitted `prop_stat`, and one player can carry
  `passing_tds` and `rushing_yards` at the *same line value* (2.5), same book,
  same instant. That made two unrelated contracts look like one contract with two
  prices. With `prop_stat` in the key: 6,301 duplicate groups, of which **6,300
  are byte-identical re-writes** and exactly **1** is a genuine price conflict
  (Khalil Herbert receptions 1.5, betonlineag, 2023-09-24: -119 vs -125).

  **Fixed** in `PointInTimeStore.read_as_of`, which now deduplicates on
  `CONTRACT_KEY` (capture_time + event + book + market + side + player +
  **prop_stat** + line). This matters for determinism, not accuracy:
  `engine.latest_fair_prob` selects via `idxmax` on `capture_time`, which is
  ambiguous across tied rows, so identical code could return different prices
  between runs. Tie-break is last-in-sorted-file-order — stable, and deliberately
  **neutral**: picking the better price would flatter every EV and CLV number,
  the one direction a betting system must never round toward. Nothing is mutated;
  `dedupe=False` returns the raw record. Removes 6,589 redundant rows of 619,983.

- **`src/collect/mainline_historical.py` is the one truly unreferenced module**
  (no import, no make target, no notebook). It is a completed one-shot pull.
  Park or delete; do not "wire" it.

- **Pre-existing lint debt: 17 ruff errors across 7 files** (`src/clv/metrics.py`,
  `src/collect/run.py`, `src/devig/methods.py`, `src/store/pit_store.py`,
  `tests/test_pit_store.py`, `tests/test_props_budget.py`, `tests/test_schema.py`).
  All UP035/UP017/I001, all auto-fixable with `ruff check --fix`. Note the
  handoff recorded "lint clean" -- that was true under an older ruff.

### Orphan verdicts (2026-08-23) — 9 tested-only modules resolved

| Module | Verdict |
|---|---|
| `signal/team_total_scan.py` | **WIRED** — `make team-total-scan-once`, manual like `middle_scan`/`steam_scan` (validated edge, no live track record) |
| `collect/props_historical.py` | PARKED — completed one-shot pull, 285/285 games |
| `collect/mainline_historical.py` | PARKED — completed one-shot pull, was the only fully unreferenced module |
| `model/individual_pass_rush_elo.py` | PARKED — wiring = comparison #10 against an 0-for-6 record; would burn a BH slot and the 2025 holdout |
| `model/prop_projection.py` | PARKED — measured worse than base rate |
| `model/closing_line.py` | PARKED — honest negative (recent form adds nothing beyond the line) |
| `backtest/evaluation.py` | **BLOCKED** — see below |
| `backtest/parlay.py` | **BLOCKED** — see below |
| `backtest/season_review.py` | **BLOCKED** — see below |
| `drift/monitor.py` | **BLOCKED** — see below |

Park verdicts live in each module's own docstring (`PARKED`), and `make audit`
reads them, so a decided module stops resurfacing as an open question.

### The real blocker: there is no live bet log

**Nothing in this repo records a bet that was actually placed.** `BacktestBet` is
constructed in exactly one place -- `BacktestEngine.run()` -- which is a backtest.
`data/alert_state.json` records which alerts were *sent*, not what was staked, at
what price, or at which book. Bets are placed manually across 5 books and nothing
comes back.

That single gap is why the last four modules cannot be wired: `season_review`
reviews live bets, `clv_portfolio`/`evaluation` score them, `drift/monitor`
watches their CLV decay, and `parlay` prices real legs against a tracked bankroll.
All four are downstream of an input that does not exist. Wiring `season_review`
today would print "No live bets to review yet." forever.

It also means **CLV -- the project's headline thesis -- cannot currently be
computed for any real bet**, because CLV needs an entry price and no entry price
is ever stored. Note `paper/nfl_clv_case_study.md:322` already refers to "the bet
log" as though one exists. ARCHITECTURE.md's "wired 2026-08-23" notes on
`drift/monitor` and `clv_portfolio` describe them being wired **to each other**
via `season_review`, not into the pipeline.

**BUILT 2026-08-23: `src/store/bet_log.py`.** Append-only JSONL at
`data/bet_log.jsonl`, entered via `make log-bet ARGS="..."`, read by
`make season-review`.

Two rules make the record trustworthy:

1. **Only what a human can know at bet time is typed.** Entry fair probability,
   closing price, CLV and settlement are all derived later from the
   point-in-time store by `to_backtest_bets`, which reuses
   `engine.latest_fair_prob` so a live bet and a backtested bet are scored by
   *identical* code. Nothing derived can be mistyped, and everything can be
   recomputed if the methodology changes.
2. **Append-only.** A log editable after the close is one editable *because* of
   the close — the exact bias CLV exists to detect. Corrections are appended as
   new rows with `corrects`, and `active_bets()` resolves them while
   `load_bet_log()` keeps the original visible.

`strategy` is a required closed-set field, not inferred from `market`, because
prop arb and experimental prop EV are both `player_prop` with opposite track
records — pooling them lets the null one hide behind the validated one.
`BacktestBet` and `clv_portfolio.bets_to_frame` carry it through, so
`season_review` segments on the scanner that actually produced the bet.

A bet whose anchor never quoted two-sided gets `None` CLV, never a guess.

### Integration drift is now checkable, not rediscoverable

`make audit` (`scripts/audit_integration.py`) classifies every `src/` module by
what actually reaches it. **Run it before claiming anything is or isn't wired.**
Baseline 2026-08-23, 61 modules:

| Category | n | Meaning |
|---|---|---|
| LIVE (launchd service) | 24 | reachable from the 3 running services |
| MANUAL (make target) | 15 | hand-invoked, often deliberately |
| RESEARCH (notebook) | 12 | offline model/analysis code |
| TESTED ONLY (wired to nothing) | 9 | built and validated, connected to nothing |
| UNREFERENCED | 1 | `collect/mainline_historical.py` |

**Manual is not the same as neglected.** `middle_scan` and `steam_scan` are
make-target-only *on purpose* -- documented in the Makefile as having no live
track record yet and therefore not trusted to an unattended alert channel.

The 9 tested-only modules are the real standing question: `evaluation`,
`parlay`, `season_review`, `props_historical`, `drift.monitor`, `closing_line`,
`individual_pass_rush_elo`, `prop_projection`, `team_total_scan`. Note
`season_review` imports `evaluation` and `clv_portfolio`, so "properly wired"
claims about those describe wiring *to each other*, not to the pipeline.

---

## Blocked on data, not on ideas

- **Public betting-percentage fade / reverse line movement via bet %.** Real,
  well-known angle, but needs a paid bet-percentage feed (Action Network,
  VSiN, or similar) this project doesn't have. Revisit if/when such a source
  gets added.
