# Methodology backlog

Candidate strategies and modeling ideas still worth trying, distinct from
`parking_lot.md` (ideas explicitly ruled *out of scope* for now). This list is
active — things queued to build, not deferred. Update status as work moves.

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

## Blocked on data, not on ideas

- **Public betting-percentage fade / reverse line movement via bet %.** Real,
  well-known angle, but needs a paid bet-percentage feed (Action Network,
  VSiN, or similar) this project doesn't have. Revisit if/when such a source
  gets added.
