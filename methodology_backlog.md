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

---

## Blocked on data, not on ideas

- **Public betting-percentage fade / reverse line movement via bet %.** Real,
  well-known angle, but needs a paid bet-percentage feed (Action Network,
  VSiN, or similar) this project doesn't have. Revisit if/when such a source
  gets added.
- **Referee-crew tendencies.** Real, well-documented effect (penalty rates,
  game-flow impact on totals), but nflverse doesn't carry referee-crew-level
  data usable for this, and no other free source is wired into this project.
