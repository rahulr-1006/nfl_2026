# Architecture & Status Audit

**Generated 2026-08-23** from the real import graph (`ast`-parsed), `launchctl list`,
the Makefile/launchd plists, and per-file inspection -- not from recollection. Phase 1
of the consolidation plan.

**Purpose:** this repo accumulated ~56 modules and 4 notebooks across many
exploratory strategies. This file answers, for every piece: *what is it, does
anything actually call it, and is it live?* It is the reference for deciding what to
consolidate, wire up, or delete -- so future work replaces things instead of
accreting alongside them.

---

## 1. What is actually running right now

Verified via `launchctl list`:

| Service | Runs | Status |
|---|---|---|
| `com.nflclv.collector` | `src.collect.run` | **RUNNING** (PID 6121) |
| `com.nflclv.monitor` | `src.notify.monitor_run` | **LOADED** (interval job, idle between ticks). Since 2026-10-04 it also runs the pre-registered H1/H1b **log-only** to `data/shadow_log_prereg.jsonl` (never texted). |
| `com.nflclv.props` | `src.collect.props_run` | **RUNNING** (loaded 2026-08-23) |

> ~~**Blocker for the season:** the props scheduler plist exists and the code is tested,
> but the service has never been loaded.~~ **CLEARED 2026-08-23** — the service was
> loaded early, and props turned out to post on 2026-08-23 — 17 days before the opener,
> not the ~9/2 assumed here. All three services verified running 2026-09-16. This paragraph and cleanup
> #1 in §9 stayed stale for three weeks while claiming to be the live status map;
> if you change what runs, change this table in the same commit.

Everything else in this repo is invoked by hand, by a notebook, or by nothing.

---

## 2. Layer map

```
COLLECT ──────► STORE ──────► SIGNAL ──────► NOTIFY
(Odds API)   (PointInTime)   (scanners)      (SMS)
                   │
                   ├──────► BACKTEST (engine, strategies, validation)
                   │
FEATURES ──► MODEL ┘
(nflverse)   (Elo, EPA, calibration)
```

**The structural gap this audit confirms:** `src/model/` never reads the odds store.
The paid Pinnacle data (~64,000 credits) is consumed only by `backtest/` and
`signal/` as a *scoring baseline*; no model parameter has ever been fit against it.
This is Phase 3 of the consolidation plan.

Re-verify with:
```
grep -rn "data/snapshots\|read_as_of" src/model/
```
The only hit is prose in `features.py`'s docstring (an analogy to `pit_store`'s
leakage guard), not a call — verified 2026-08-23.

---

## 3. Module status

Legend — **LIVE**: runs in a deployed service. **ENTRY**: manual entrypoint.
**LIB**: imported by live/entry code. **RESEARCH**: used only by notebooks/tests.
**The `Reach` column is GENERATED — do not hand-edit it.** `make sync-arch`
rewrites it from `make audit`. It used to be a hand-maintained `Status` column
that mixed two different axes — *role* (LIB, ENTRY, RESEARCH) and *reachability*
(LIVE, ORPHAN) — so rows compared on the wrong axis disagreed with reality by
construction, and eight did. Role is deliberately not duplicated here; the Notes
column carries it in prose, where it cannot silently contradict a fact.

Values, all from the audit: **LIVE** (reachable from a launchd service),
**MANUAL** (reachable from a make target — often deliberate, e.g. `middle_scan`
and `steam_scan` have no live track record yet and are not trusted to an
unattended alert channel), **RESEARCH** (reached from a notebook), **PARKED**
(unreachable by decision, with the reason and a reopen condition in the module's
own docstring), **UNDECIDED** (built and tested, wired to nothing, no verdict
yet), **UNREF** (nothing reaches it at all).

Reachability is never decided by reading imports alone — that misses make
targets, and it produced two wrong ORPHAN verdicts here (`preseason_report.py`,
since retired, and `demo_pipeline.py`).

### store/ — foundation (all LIVE)
| Module | Imported by | Reach | Notes |
|---|---|---|---|
| `pit_store.py` | 18 | **LIVE** | Most-depended-on module in the repo. The leakage guard. |
| `schema.py` | 12 | **LIVE** | `OddsSnapshot`/`Market`/`Side`. |
| `settlement.py` | 2 | **LIVE** | Game-score grading. |
| `prop_settlement.py` | 2 | **LIVE** | Player-stat grading + name reconciliation. |

### collect/ — data acquisition
| Module | Imported by | Reach | Notes |
|---|---|---|---|
| `client.py` | 8 | **LIVE** | Odds API wrapper. |
| `transform.py` | 8 | **LIVE** | JSON → snapshots, event matching. |
| `teams.py` / `config.py` | 4 / 3 | **LIVE** | |
| `run.py` | — | **LIVE** | Collector entrypoint (running). |
| `scheduler.py` / `budget.py` | 1 / 1 | **LIVE** | Mainline cadence. |
| `props_run.py` | — | **LIVE** | Loaded as `com.nflclv.props` (2026-08-23); the 9/2 blocker cleared early when props posted 17 days out. |
| `props_scheduler.py` / `props_budget.py` | 1 / 1 | **LIVE** | 3-tier cadence, 84.4% of credit grant. |
| `props.py` | 4 | **LIVE** | Prop parsing + market definitions. |
| `props_historical.py` | 1 | **MANUAL** | Executed: 2023+2024 props pulled. |
| `mainline_historical.py` | 0 | **MANUAL** | Completed one-shot pull (570 games); gap confirmed real but inconsequential (0.000138 Brier). Park verdict 2026-08-23, reason in its docstring. |

### model/ — feature/rating layer (trains ONLY on free nflverse data)
| Module | Imported by | Reach | Notes |
|---|---|---|---|
| `elo.py` | 8 | **LIVE** | Base team Elo — the one comparison that survives BH correction. |
| `features.py` / `train.py` | 1 / 2 | **LIVE** | Feature builder, splits, fitting. |
| `baseline.py` | 4 | **LIVE** | Devigged market baseline. |
| `qb_elo.py` | 1 | **LIVE** | In `COMBINED_QB_FEATURE_COLUMNS`. |
| `stadiums.py` | 1 | **LIVE** | Rest/travel (feature tested negative). |
| `calibration.py` / `evaluate.py` | 1 / 1 | **LIVE** | |
| `receiver_elo.py` | 0 | **RESEARCH** | Notebook + tests only. Never fed a live decision. |
| `pass_rush_elo.py` | 0 | **RESEARCH** | Same. |
| `game_level_features.py` | 0 | **RESEARCH** | Rolls the above to game level; tested negative. |
| `closing_line.py` | 0 | **PARKED** | Phase 3. Predicts Pinnacle's closing fair prob from pre-game features. Valid for MAINLINE; **not** for props (target is ~0.5 by construction, measured). |
| `prop_projection.py` | 0 | **PARKED** | Phase 3. Projects a player's stat vs the posted line -- the first model here to consume `data/snapshots`. Tested negative: recent form adds nothing beyond the line. |
| `individual_pass_rush_elo.py` | 0 | **PARKED** | Wiring it = comparison #10 against an 0-for-6 feature-engineering record; would spend a BH slot and the 2025 holdout. Reopen only for a structural use. |

### backtest/ — strategies & evaluation
| Module | Imported by | Reach | Notes |
|---|---|---|---|
| `engine.py` | 1 | **LIVE** | Point-in-time backtester. Look-ahead bug fixed 2026-08-23. |
| `middling.py` / `steam.py` | 2 / 1 | **LIVE** | |
| `middle_scan.py` / `steam_scan.py` | — | **LIVE / MANUAL** | Manual `make` targets. No service, no track record. |
| `props_ev_backtest.py` | 1 | **LIVE** | Now also powers live props scanning. |
| `correlated_props.py` | 0 | **MANUAL** | 11 public fns, 2 notebooks. `price_bucket_bet` is the gated entrypoint **no live scanner calls**. |
| `team_total_props.py` | 0 | **UNDECIDED** | Validated edge, **not wired to anything**. Edge figures here previously read +6.6%/+14.1%; those came from the TRAIN fit and were corrected 2026-09-04 to the realized out-of-sample values (**rushing +2.8%, passing +7.1%** at 6.54% vig — only passing/underdog clears the 3% threshold). |
| `validation.py` | 0 | **RESEARCH** | Leakage/FDR toolkit, used by 3 notebooks. Should be a hard dependency of any future claim. |
| `evaluation.py` | 0 | **MANUAL** | Phase 2 (2026-08-23). Bettability metrics: threshold sweep, `proportion_bet`, bootstrap CIs, random-side null. Reproduced the props-EV null on 6,812 real bets. Any future edge claim should pass `evaluate_strategy`. |
| `pinnacle_lag.py` | 1 | **LIVE** | 2026-10-04. Pre-registered H1/H1b: soft-book prop prices vs Pinnacle's devigged fair, scored on **closing EV** (`clv_probability` can't see the price paid). Frozen params live in `signal/prereg_scan.py`. ⚠️ `evaluation.random_bet_benchmark` pays the listed side's price to the opposite side (null mean ≈ price/2 − 1) — not a valid null for plus-money bets until fixed. |
| `synthetic_market.py` | 0 | **RESEARCH** | Simulator for CLV validation. |
| `clv_portfolio.py` | 0 | **MANUAL** | Built 2026-08-23; reporting layer, no live caller yet. |
| `season_review.py` | 0 | **MANUAL** | Phase 4. Weekly in-season health check: CLV + drift CUSUM + bettability -> continue/monitor/retire. Consumes `drift/monitor.py` and `clv_portfolio.py`, both previously orphaned. |
| `parlay.py` | 0 | **PARKED** | Contract requires REAL leg prices; team-total's second leg is a constructed aggregate, so that wire would launder a modelled number. Reopen when a same-game prop parlay scanner exists. |

### signal/ notify/ clv/ devig/ features/ drift/
| Module | Imported by | Reach | Notes |
|---|---|---|---|
| `signal/live_scan.py` | 5 | **LIVE** | Moneyline scanner + shared alert state. |
| `signal/props_scan.py` | 1 | **LIVE** | Props arb + EV (wired 2026-08-23). |
| `signal/prereg_scan.py` | 1 | **LIVE** | 2026-10-04. H1/H1b **log-only** to `data/shadow_log_prereg.jsonl`, a separate file so `decision-report`/`shadow-report`/`clv-report` can't show holdout results before 2026-11-10 (`preregistration_wk5-9.md`). |
| `signal/sizing.py` | 5 | **LIVE** | Kelly + bankroll caps. |
| `notify/monitor_run.py` | — | **LIVE** | Alert entrypoint. |
| `notify/sms.py` | 2 | **LIVE** | |
| `clv/metrics.py` | 3 | **LIVE** | The project's headline metric. |
| `devig/convert.py` / `methods.py` | 4 / 2 | **LIVE** | |
| `features/load_static.py` | 1 | **LIVE** | nflverse pulls. |
| `features/player_status.py` | 1 | **RESEARCH** | Trade/injury lookup, no live consumer. |
| `drift/monitor.py` | 1 | **MANUAL** | CUSUM drift detection. **Wired 2026-08-23** by `season_review.py` -- no longer an orphan. |
| `demo_pipeline.py` | 0 | **MANUAL** | `make demo`. Was mis-filed ORPHAN by import-only reasoning. Documentation-by-example smoke test. |

---

## 4. Orphan list — delete or wire

| Module | Recommendation |
|---|---|
> **All rows below were decided 2026-08-23** (`make audit`: 0 undecided, 0 unreferenced).
> The "Wire."/"Decide." wording survived the decision and is kept only to show what was
> recommended at audit time — the verdict that binds is in `methodology_backlog.md`.

| `parlay.py` | ~~Wire~~ **PARKED 2026-08-23** (blocked). Parlay EV has no live path. |
| `drift/monitor.py` | ~~Wire~~ **DONE 2026-08-23** -- consumed by `season_review.py`. |
| `team_total_props.py` | ~~Wire~~ **DECIDED 2026-08-23**: scanner wired as `make team-total-scan-once` (manual). Deliberately NOT in `monitor_run`, so it has **no exposure cap** — see methodology_backlog.md. |
| `correlated_props.price_bucket_bet` | ~~Wire~~ **DONE 2026-08-23** — the underdog/narrow-only gate is enforced in code. |
| `clv_portfolio.py` | ~~Wire~~ **DONE 2026-08-23** -- consumed by `season_review.py`. |
| `individual_pass_rush_elo.py` | ~~Decide~~ **PARKED 2026-08-23** — would spend a BH slot and the 2025 holdout for no live consumer. |
| `mainline_historical.py` | ~~Document~~ **DONE** — `make mainline-timeseries` exists; manual and deliberate, never scheduled. |
| `clv/preseason_report.py`, `collect/preseason.py` | ~~Retire after 9/9~~ **DONE 2026-09-03** — deleted with their tests, `make` targets and notebook. |
| `demo_pipeline.py` | Keep only if it runs in CI; otherwise delete. |

---

## 5. Notebooks

| Notebook | Cells | Status |
|---|---|---|
| `model_backtest_results.ipynb` | 134 | **Primary results.** ⚠️ Reads **stale 2015-2024 data in 6 places** while `src/` moved to 2015-2025. |
| `clv_tracker_validation.ipynb` | 14 | Current — synthetic CLV validation (mainline + props). |
| `training_frame_exploration.ipynb` | 14 | Current — feature-correlation EDA. |

> **The 134-cell notebook is the single biggest coherence problem.** It holds the
> comparison registry, the BH correction family, and most reported results — on data
> a full season out of date relative to `src/`. Every number in it should be regarded
> as 2015-2024-based until it is re-run.

---

## 6. Strategy verdicts (`methodology_backlog.md`)

| # | Strategy | Verdict | Wired live? |
|---|---|---|---|
| 1 | Rest/travel differential | Negative | n/a |
| 2 | Joint margin/total | Premise doesn't hold | n/a |
| 3 | Steam detection | Built, live-validated | Manual only |
| 4 | Player-prop middling | Blocked on live props | No |
| 5 | Referee tendencies | No signal | n/a |
| 6 | Individual pass-rush rating | Built | **No — orphan** |
| 7 | Training-window size | Real effect (3yr worse; 5yr ≈ 7yr) | n/a |
| 8 | Mainline historical pull | Executed; gap real but inconsequential | n/a |
| 9 | Team-total props | **Validated edge** | **No** |
| — | Props cross-book arb | **Validated (65 spots)** | **Yes** (2026-08-23) |
| — | Props EV vs Pinnacle | **NULL result** | Yes, labeled EXPERIMENTAL |

**Pattern:** of two strategies with genuine out-of-sample-validated edges
(team-total props, props arb), only one can be acted on. Meanwhile 7 consecutive
feature-engineering attempts on the moneyline model all failed — which is why the
consolidation plan defers feature work behind evaluation rigor.

---

## 7. Data inventory

**`data/static/` (free nflverse)** — 2015-2025 current; **2015-2024 duplicates still
present and still referenced by notebooks.** Recommend deleting the `_2015_2024`
files *after* the notebooks are repointed, so the stale references fail loudly.

**`data/snapshots/` (PointInTimeStore)** — mixes three eras: live 2026 collection,
2023-2024 mainline backfill, 2023-2024 props backfill.

> ⚠️ **This mixing already caused one live incident** (874/879 alerts fired on
> finished games; fixed via `upcoming_only`). Any new consumer of this store must
> filter on `event_start_time` — `capture_time` cannot express "is this game still
> playable."

---

## 8. Design rule: which strategies work here, and why

Measured 2026-08-23 across the full 2023+2024 prop pull. **Pinnacle's prop vig is
6.29%.** Taking the best price across all five execution books, the median EV vs
Pinnacle's devigged fair is **−4.74%**, positive on only **14%** of contract-sides.
Line shopping is real (median best−median gain ≈ 1.26 implied-prob points, dispersion
across 44,391 contract-sides) but recovers barely a third of the per-side vig.

Every strategy in this repo falls into one of two shapes, and the shape has predicted
the outcome every time:

| Shape | Requires | Track record |
|---|---|---|
| **Probability estimation** | out-predicting Pinnacle | props EV (null on 6,812 bets), prop projection (worse than base rate), moneyline model (**0 for 7**) |
| **Structural exploitation** | no probability estimate at all | props arb (65 real spots), correlated/team-total props (validated buckets), middling & steam (live-validated) |

The first shape must find >4.7% of edge before breaking even; nothing built here has
supplied meaningfully more than zero. The second shape sidesteps the question — two
books disagreeing, a book pricing correlated legs as independent, or a line moving.

**Practical rule: before building, state which shape the strategy is.** If it is
probability estimation, state where the >4.7% comes from. Standing reference figures
live at the top of `methodology_backlog.md`.

---

## 9. Highest-leverage cleanups

1. ~~**Load `com.nflclv.props`**~~ **DONE 2026-08-23** — running since.
2. **Repoint `model_backtest_results.ipynb` to 2015-2025** and re-run, so the
   headline results match the code.
3. ~~**Wire or park the four validated-but-orphaned modules**~~ **DONE 2026-08-23** —
   all nine decided; `make audit` reports 0 undecided, 0 unreferenced. See the
   verdicts in `methodology_backlog.md`, not the stale table in §7 above.
4. **Delete stale `_2015_2024` parquets** once (2) is done.
5. ~~Retire preseason modules after 9/9~~ **DONE 2026-09-03.** `collect/preseason.py`,
   `clv/preseason_report.py`, both test files, `preseason_dry_run.ipynb`, and the
   `preseason-poll`/`preseason-report` make targets are deleted. Retired 6 days
   early: the NFL preseason itself ended in August, so the modules could no longer
   collect anything, and the live pipeline they existed to de-risk is proven
   (3 services running, health checks green, 21,907 prop rows). The collected
   preseason snapshots are KEPT at `data/snapshots_preseason/` — deleting the code
   that produced evidence is not the same as deleting the evidence.
