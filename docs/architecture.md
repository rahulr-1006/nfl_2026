# Architecture

A map of every module: what it is, what calls it, and whether it runs live.
Reachability comes from the real import graph (`ast`-parsed), the Makefile and the
launchd plists, not from recollection — `make audit` prints it, and `make sync-arch`
writes it into the `Reach` column below.

---

## 1. What runs live

Three macOS launchd services, installed from `ops/`:

| Service | Runs | Status |
|---|---|---|
| `com.nflclv.collector` | `src.collect.run` | Always on |
| `com.nflclv.monitor` | `src.notify.monitor_run` | Interval job. Moneyline EV, props arb/EV, middling and steam scanners; since 2026-10-04 it also runs the pre-registered H1/H1b **log-only** to `data/shadow_log_prereg.jsonl` (never texted). |
| `com.nflclv.props` | `src.collect.props_run` | Always on |

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

The live models in `src/model/` train only on free nflverse data. The paid Pinnacle
odds are used by `backtest/` and `signal/` as the scoring baseline. The two models
that *do* fit against the odds store (`closing_line.py`, `prop_projection.py`) were
built, tested negative, and parked — see their rows below.

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
| `pit_store.py` | 18 | **LIVE** | Most-depended-on module in the repo. The leakage guard. Since 2026-10-13 each instance caches the deduped full read, keyed on the file listing, so a monitor tick reads disk once instead of once per scanner (verified identical to an uncached read on the real store). |
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
| `props_run.py` | — | **LIVE** | Loaded as `com.nflclv.props` (2026-08-23). |
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
| `closing_line.py` | 0 | **PARKED** | Predicts Pinnacle's closing fair prob from pre-game features. Valid for MAINLINE; **not** for props (target is ~0.5 by construction, measured). |
| `prop_projection.py` | 0 | **PARKED** | Projects a player's stat vs the posted line -- the first model here to consume `data/snapshots`. Tested negative: recent form adds nothing beyond the line. |
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
| `validation.py` | 0 | **MANUAL** | Leakage/FDR toolkit, used by 3 notebooks. Should be a hard dependency of any future claim. |
| `evaluation.py` | 0 | **MANUAL** | Bettability metrics: threshold sweep, `proportion_bet`, bootstrap CIs, random-side null. Reproduced the props-EV null on 6,812 real bets. Any future edge claim should pass `evaluate_strategy`. |
| `pinnacle_lag.py` | 1 | **LIVE** | 2026-10-04. Pre-registered H1/H1b: soft-book prop prices vs Pinnacle's devigged fair, scored on **closing EV** (`clv_probability` can't see the price paid). Frozen params live in `signal/prereg_scan.py`. `evaluation.random_bet_benchmark`'s opposite-side pricing bug (null mean ≈ price/2 − 1) was fixed 2026-10-13; pass `opposite_price_decimal` for a real-price null. |
| `synthetic_market.py` | 0 | **RESEARCH** | Simulator for CLV validation. |
| `clv_portfolio.py` | 0 | **MANUAL** | Built 2026-08-23; reporting layer, no live caller yet. |
| `season_review.py` | 0 | **MANUAL** | Weekly in-season health check: CLV + drift CUSUM + bettability -> continue/monitor/retire. Consumes `drift/monitor.py` and `clv_portfolio.py`, both previously orphaned. |
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
| `clv/prereg_score.py` | 0 | **MANUAL** | 2026-10-13. `make prereg-score [WEEKS=holdout]`: H1/H1b against the pre-registration's §3 pass bar. Refuses holdout weeks before 2026-11-10. Rushing yards stay out of the verdict (§3 gate); a rushing-inclusive number prints as an exploratory line only. `scripts/h1_train_grid.py` reproduces the frozen Train numbers. |
| `clv/prereg_score_wk10.py` | 0 | **MANUAL** | 2026-10-17. `make prereg-score-wk10 [WEEKS=holdout]`: H5 (moneyline longshots >3.0) against `preregistration_wk10-14.md`. Refuses Weeks 10–14 before 2026-12-15. Kept separate so the Weeks 5–9 scorer is never edited after its commit. |
| `clv/seals.py` | 2 | **MANUAL** | Withholds pre-registered holdout legs from every CLV number (`shadow_alerts_as_bets`, so decision-report, clv-report and the notebooks): Weeks 5–9 player props until 2026-11-10 (H1/H1b; added 2026-11-03) and Weeks 10–14 `moneyline_ev` until 2026-12-15 (H5). Survival is not sealed. |
| `devig/convert.py` / `methods.py` | 4 / 2 | **LIVE** | |
| `features/load_static.py` | 1 | **LIVE** | nflverse pulls. |
| `features/player_status.py` | 1 | **RESEARCH** | Trade/injury lookup, no live consumer. |
| `drift/monitor.py` | 1 | **MANUAL** | CUSUM drift detection. **Wired 2026-08-23** by `season_review.py` -- no longer an orphan. |
| `demo_pipeline.py` | 0 | **MANUAL** | `make demo`. Was mis-filed ORPHAN by import-only reasoning. Documentation-by-example smoke test. |

---

## 4. Notebooks

| Notebook | Cells | Status |
|---|---|---|
| `model_backtest_results.ipynb` | 134 | **Primary results.** Comparison registry, BH correction family, most reported model results. |
| `clv_tracker_validation.ipynb` | 14 | Current — synthetic CLV validation (mainline + props). |
| `alert_clv_analysis.ipynb` | 23 | Current — every SMS alert as a bet at its texted stake: closing EV scorecard, P&L vs. what the close expected, calibration of the close, power. Seal-aware. |
| `training_frame_exploration.ipynb` | 14 | Current — feature-correlation EDA. |

---

## 5. Strategy verdicts (pre-season research)

| # | Strategy | Verdict | Wired live? |
|---|---|---|---|
| 1 | Rest/travel differential | Negative | n/a |
| 2 | Joint margin/total | Premise doesn't hold | n/a |
| 3 | Steam detection | Built | Yes (monitor, since 2026-09-21) |
| 4 | Player-prop middling | Blocked on live props | No |
| 5 | Referee tendencies | No signal | n/a |
| 6 | Individual pass-rush rating | Built | No — parked |
| 7 | Training-window size | Real effect (3yr worse; 5yr ≈ 7yr) | n/a |
| 8 | Mainline historical pull | Executed; gap real but inconsequential | n/a |
| 9 | Team-total props | **Validated edge** | Manual scanner |
| — | Props cross-book arb | **Validated (65 spots)** | Yes |
| — | Props EV vs Pinnacle | **NULL result** | Yes, labeled EXPERIMENTAL |

**Pattern:** 7 consecutive feature-engineering attempts on the moneyline model
failed, while the two validated edges (team-total props, props arb) are both
structural — see §7. These are pre-season verdicts on historical data; the live 2026
record is scored separately against the pre-registrations in `docs/`.

---

## 6. Data inventory

**`data/static/` (free nflverse)** — schedules, play-by-play, player stats, rosters,
injuries, snap counts, 2015–2025 plus the in-progress 2026 season. Not tracked in git;
`make data` rebuilds it.

**`data/snapshots/` (PointInTimeStore)** — mixes three eras: live 2026 collection,
2023-2024 mainline backfill, 2023-2024 props backfill.

> ⚠️ **This mixing already caused one live incident** (874/879 alerts fired on
> finished games; fixed via `upcoming_only`). Any new consumer of this store must
> filter on `event_start_time` — `capture_time` cannot express "is this game still
> playable."

---

## 7. Design rule: which strategies work here, and why

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
probability estimation, state where the >4.7% comes from.
