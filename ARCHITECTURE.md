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
| `com.nflclv.monitor` | `src.notify.monitor_run` | **LOADED** (interval job, idle between ticks) |
| `com.nflclv.props` | `src.collect.props_run` | **NOT LOADED** |

> **Blocker for the season:** the props scheduler plist exists and the code is tested,
> but the service has never been loaded. Props start posting ~9/2. Everything the
> props CLV/arb work depends on is downstream of this one deployment step.

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
**ORPHAN**: nothing imports it anywhere.

### store/ — foundation (all LIVE)
| Module | Imported by | Status | Notes |
|---|---|---|---|
| `pit_store.py` | 18 | **LIVE** | Most-depended-on module in the repo. The leakage guard. |
| `schema.py` | 12 | **LIVE** | `OddsSnapshot`/`Market`/`Side`. |
| `settlement.py` | 2 | **LIVE** | Game-score grading. |
| `prop_settlement.py` | 2 | **LIVE** | Player-stat grading + name reconciliation. |

### collect/ — data acquisition
| Module | Imported by | Status | Notes |
|---|---|---|---|
| `client.py` | 8 | **LIVE** | Odds API wrapper. |
| `transform.py` | 8 | **LIVE** | JSON → snapshots, event matching. |
| `teams.py` / `config.py` | 4 / 3 | **LIVE** | |
| `run.py` | — | **LIVE** | Collector entrypoint (running). |
| `scheduler.py` / `budget.py` | 1 / 1 | **LIVE** | Mainline cadence. |
| `props_run.py` | — | **ENTRY** | **Not loaded as a service — the 9/2 blocker.** |
| `props_scheduler.py` / `props_budget.py` | 1 / 1 | **LIB** | 3-tier cadence, 84.4% of credit grant. |
| `props.py` | 4 | **LIB** | Prop parsing + market definitions. |
| `props_historical.py` | 1 | **ENTRY** | Executed: 2023+2024 props pulled. |
| `mainline_historical.py` | 0 | **ORPHAN** | Executed once (570 games) via a scratchpad driver; no test, no caller. **Wire or document as one-shot.** |
| `preseason.py` | 1 | **ENTRY** | Superseded by the real season — retire after 9/9. |

### model/ — feature/rating layer (trains ONLY on free nflverse data)
| Module | Imported by | Status | Notes |
|---|---|---|---|
| `elo.py` | 8 | **LIB** | Base team Elo — the one comparison that survives BH correction. |
| `features.py` / `train.py` | 1 / 2 | **LIB** | Feature builder, splits, fitting. |
| `baseline.py` | 4 | **LIB** | Devigged market baseline. |
| `qb_elo.py` | 1 | **LIB** | In `COMBINED_QB_FEATURE_COLUMNS`. |
| `stadiums.py` | 1 | **LIB** | Rest/travel (feature tested negative). |
| `calibration.py` / `evaluate.py` | 1 / 1 | **LIB** | |
| `receiver_elo.py` | 0 | **RESEARCH** | Notebook + tests only. Never fed a live decision. |
| `pass_rush_elo.py` | 0 | **RESEARCH** | Same. |
| `game_level_features.py` | 0 | **RESEARCH** | Rolls the above to game level; tested negative. |
| `closing_line.py` | 0 | **RESEARCH** | Phase 3. Predicts Pinnacle's closing fair prob from pre-game features. Valid for MAINLINE; **not** for props (target is ~0.5 by construction, measured). |
| `prop_projection.py` | 0 | **RESEARCH** | Phase 3. Projects a player's stat vs the posted line -- the first model here to consume `data/snapshots`. Tested negative: recent form adds nothing beyond the line. |
| `individual_pass_rush_elo.py` | 0 | **ORPHAN** | **12 tests, 0 notebooks, 0 callers.** Built, sanity-checked, then never used for anything. |

### backtest/ — strategies & evaluation
| Module | Imported by | Status | Notes |
|---|---|---|---|
| `engine.py` | 1 | **LIB** | Point-in-time backtester. Look-ahead bug fixed 2026-08-23. |
| `middling.py` / `steam.py` | 2 / 1 | **LIB** | |
| `middle_scan.py` / `steam_scan.py` | — | **ENTRY** | Manual `make` targets. No service, no track record. |
| `props_ev_backtest.py` | 1 | **LIB** | Now also powers live props scanning. |
| `correlated_props.py` | 0 | **RESEARCH** | 11 public fns, 2 notebooks. `price_bucket_bet` is the gated entrypoint **no live scanner calls**. |
| `team_total_props.py` | 0 | **RESEARCH** | Validated edge (underdog +6.6%/+14.1%), **not wired to anything**. |
| `validation.py` | 0 | **RESEARCH** | Leakage/FDR toolkit, used by 3 notebooks. Should be a hard dependency of any future claim. |
| `evaluation.py` | 0 | **RESEARCH** | Phase 2 (2026-08-23). Bettability metrics: threshold sweep, `proportion_bet`, bootstrap CIs, random-side null. Reproduced the props-EV null on 6,812 real bets. Any future edge claim should pass `evaluate_strategy`. |
| `synthetic_market.py` | 0 | **RESEARCH** | Simulator for CLV validation. |
| `clv_portfolio.py` | 0 | **RESEARCH** | Built 2026-08-23; reporting layer, no live caller yet. |
| `season_review.py` | 0 | **RESEARCH** | Phase 4. Weekly in-season health check: CLV + drift CUSUM + bettability -> continue/monitor/retire. Consumes `drift/monitor.py` and `clv_portfolio.py`, both previously orphaned. |
| `parlay.py` | 0 | **ORPHAN** | Built 2026-08-23. Tested, documented, **wired to nothing**. |

### signal/ notify/ clv/ devig/ features/ drift/
| Module | Imported by | Status | Notes |
|---|---|---|---|
| `signal/live_scan.py` | 5 | **LIVE** | Moneyline scanner + shared alert state. |
| `signal/props_scan.py` | 1 | **LIVE** | Props arb + EV (wired 2026-08-23). |
| `signal/sizing.py` | 5 | **LIVE** | Kelly + bankroll caps. |
| `notify/monitor_run.py` | — | **LIVE** | Alert entrypoint. |
| `notify/sms.py` | 2 | **LIVE** | |
| `clv/metrics.py` | 3 | **LIVE** | The project's headline metric. |
| `clv/preseason_report.py` | 0 | **ORPHAN** | Preseason-only; retire after 9/9. |
| `devig/convert.py` / `methods.py` | 4 / 2 | **LIVE** | |
| `features/load_static.py` | 1 | **ENTRY** | nflverse pulls. |
| `features/player_status.py` | 1 | **RESEARCH** | Trade/injury lookup, no live consumer. |
| `drift/monitor.py` | 1 | **LIB** | CUSUM drift detection. **Wired 2026-08-23** by `season_review.py` -- no longer an orphan. |
| `demo_pipeline.py` | 0 | **ORPHAN** | Documentation-by-example. Keep as a smoke test or delete. |

---

## 4. Orphan list — delete or wire

| Module | Recommendation |
|---|---|
| `parlay.py` | **Wire.** Parlay EV has no live path; correlated-props edge is the natural consumer. |
| `drift/monitor.py` | ~~Wire~~ **DONE 2026-08-23** -- consumed by `season_review.py`. |
| `team_total_props.py` | **Wire.** Has a validated out-of-sample edge and no way to act on it. |
| `correlated_props.price_bucket_bet` | **Wire.** Deliberately-gated pricing entrypoint that nothing calls. |
| `clv_portfolio.py` | ~~Wire~~ **DONE 2026-08-23** -- consumed by `season_review.py`. |
| `individual_pass_rush_elo.py` | **Decide.** Built and tested but used nowhere — either feed it into prop pricing or mark it explicitly parked. |
| `mainline_historical.py` | **Document** as a one-shot backfill tool, or add a `make` target. |
| `clv/preseason_report.py`, `collect/preseason.py` | **Retire after 9/9** — the real season supersedes the dry run. |
| `demo_pipeline.py` | Keep only if it runs in CI; otherwise delete. |

---

## 5. Notebooks

| Notebook | Cells | Status |
|---|---|---|
| `model_backtest_results.ipynb` | 134 | **Primary results.** ⚠️ Reads **stale 2015-2024 data in 6 places** while `src/` moved to 2015-2025. |
| `clv_tracker_validation.ipynb` | 14 | Current — synthetic CLV validation (mainline + props). |
| `training_frame_exploration.ipynb` | 14 | Current — feature-correlation EDA. |
| `preseason_dry_run.ipynb` | 18 | Superseded after 9/9; also reads stale data (2 places). |

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

1. **Load `com.nflclv.props`** — hard blocker, everything props depends on it.
2. **Repoint `model_backtest_results.ipynb` to 2015-2025** and re-run, so the
   headline results match the code.
3. **Wire or park the four validated-but-orphaned modules** (`team_total_props`,
   `parlay`, `price_bucket_bet`, `drift/monitor`).
4. **Delete stale `_2015_2024` parquets** once (2) is done.
5. **Retire preseason modules** after 9/9.
