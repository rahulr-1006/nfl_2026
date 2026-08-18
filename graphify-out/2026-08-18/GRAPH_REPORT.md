# Graph Report - nfl_2026  (2026-08-18)

## Corpus Check
- 99 files · ~59,232 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 943 nodes · 2274 edges · 52 communities (41 shown, 11 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 291 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `47c19d33`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Side
- test_collect_scheduler.py
- test_live_scan.py
- scheduler.py
- test_evaluate.py
- PointInTimeStore
- 4. Methodology
- test_player_status.py
- test_devig.py
- test_features.py
- test_drift_monitor.py
- nfl-clv
- What You Must Do When Invoked
- graphify reference: extra exports and benchmark
- graphify reference: query, path, explain
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- CLAUDE.md
- .claude/CLAUDE.md
- extraction-spec.md
- test_prop_settlement.py
- datetime
- DataFrame
- 3. Data
- test_elo.py
- nfl-clv
- ndarray
- Pipeline
- test_collect_props_historical.py
- test_clv_metrics.py
- OddsApiClient
- Beating the Close, Not the Book: A CLV-First Case Study of NFL Betting Markets
- 5. Results
- 1. Introduction
- 6. Discussion
- 2. Background and Related Work
- Path

## God Nodes (most connected - your core abstractions)
1. `PointInTimeStore` - 73 edges
2. `Side` - 69 edges
3. `Market` - 60 edges
4. `OddsApiClient` - 34 edges
5. `OddsSnapshot` - 30 edges
6. `settle()` - 28 edges
7. `Outcome` - 25 edges
8. `tick()` - 25 edges
9. `OddsApiResponse` - 23 edges
10. `OddsApiError` - 21 edges

## Surprising Connections (you probably didn't know these)
- `test_event_odds_to_prop_snapshots_parses_over_under_pair()` --uses--> `Market`  [INFERRED]
  tests/test_collect_props.py → src/store/schema.py
- `test_event_to_snapshots_maps_markets_and_sides()` --uses--> `Market`  [INFERRED]
  tests/test_collect_transform.py → src/store/schema.py
- `_snapshot()` --uses--> `Market`  [INFERRED]
  tests/test_live_scan.py → src/store/schema.py
- `_snapshot()` --uses--> `Market`  [INFERRED]
  tests/test_monitor_run.py → src/store/schema.py
- `_snap()` --uses--> `Market`  [INFERRED]
  tests/test_pit_store.py → src/store/schema.py

## Import Cycles
- None detected.

## Communities (52 total, 11 thin omitted)

### Community 0 - "Side"
Cohesion: 0.08
Nodes (77): BacktestBet, BacktestEngine, BetOrder, DecisionPoint, _latest_fair_prob(), _latest_price(), _parse_kickoffs(), _payout() (+69 more)

### Community 1 - "test_collect_scheduler.py"
Cohesion: 0.06
Nodes (76): BlockingScheduler, date, Path, CollectorState, current_period_end(), decide_poll(), _game_interval_minutes(), load_state() (+68 more)

### Community 2 - "test_live_scan.py"
Cohesion: 0.05
Nodes (76): main(), End-to-end pipeline demo: pull -> store -> compare -> decide -> notify. `make…, _step(), main(), Live +EV monitor entrypoint: `python -m src.notify.monitor_run`. Meant to be…, One scan-and-alert cycle. Returns the number of alerts actually sent. Never…, run(), _escape_for_applescript() (+68 more)

### Community 3 - "scheduler.py"
Cohesion: 0.06
Nodes (80): OddsApiError, RuntimeError, RateLimitExceeded, Thin HTTP wrapper around The Odds API. Talks to The Odds API directly (not…, Network or unexpected-response failure talking to The Odds API., The API rejected the request for quota/auth reasons (401/402/429)., build_preseason_match(), main() (+72 more)

### Community 4 - "test_evaluate.py"
Cohesion: 0.05
Nodes (73): CalibratedClassifierCV, HistGradientBoostingClassifier, ndarray, Pipeline, Protocol, compare_to_baseline(), fit_calibrated_model(), predict_calibrated_proba() (+65 more)

### Community 5 - "PointInTimeStore"
Cohesion: 0.06
Nodes (59): BaseModel, model_validator, clv_movement_report(), DataFrame, datetime, Preseason CLV-movement report: a dry run of the measurement pipeline…, (home_price_american, away_price_american) from a moneyline slice. None if the…, One row per preseason event with at least two distinct capture times: price and… (+51 more)

### Community 6 - "4. Methodology"
Cohesion: 0.20
Nodes (10): 4.1 Odds conversion, 4.2 Devigging methods, 4.3 Closing Line Value, 4.4 Point-in-time backtesting framework, 4.5 Modeling approach, 4.6 Bet sizing, 4.7 Evaluation framework, 4.8 Non-stationarity and drift detection (+2 more)

### Community 7 - "test_player_status.py"
Cohesion: 0.14
Nodes (27): DataFrame, find_prop_ev_spots(), pinnacle_fair_probs(), Cross-book EV backtest for player props: does comparing an execution book's…, One row per (event_id, player_name, prop_stat) with both a Pinnacle Over and…, One row per (event, player, prop_stat, line, side, book) where `book`'s price…, current_injury_status(), current_team() (+19 more)

### Community 8 - "test_devig.py"
Cohesion: 0.10
Nodes (36): compare_methods(), compare_methods_table(), devig_additive(), devig_multiplicative(), devig_power(), devig_shin(), DevigResult, overround() (+28 more)

### Community 9 - "test_features.py"
Cohesion: 0.16
Nodes (27): Series, build_game_features(), _is_garbage_time(), DataFrame, Feature builder (blueprint Part E): team-strength proxies from play-by-play.…, One row per game_id: home/away pre-game rolling EPA features plus the schedule…, True where a play should be excluded. Missing `wp` (nflverse leaves ~0.6% of…, Collapse play-by-play to one row per (game_id, team): offensive and defensive… (+19 more)

### Community 10 - "test_drift_monitor.py"
Cohesion: 0.18
Nodes (18): cusum(), first_flag_index(), ndarray, Non-stationarity / drift monitor (blueprint Part E, "the genuinely hard part").…, Index of the first True in `flagged`, or None if it never fires., Trailing rolling mean CLV, one value per bet. Uses whatever history exists so…, Two-sided CUSUM change-point detector. `upper` accumulates evidence of a…, Rolling Brier score over the trailing `window` predictions, minus a… (+10 more)

### Community 24 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 25 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 26 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 27 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 28 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 29 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 35 - "test_prop_settlement.py"
Cohesion: 0.14
Nodes (26): Outcome, Side, build_player_stats_index(), normalize_player_name(), Settlement for player-prop (Over/Under) bets against nflverse's per-player game…, Batch-grade prop-shaped rows (event_id/game_id, player_name, prop_stat, side,…, Collapse punctuation/whitespace differences between an odds book's player name…, (game_id, player_display_name) -> {stat_column: value}, from nflreadpy's… (+18 more)

### Community 38 - "3. Data"
Cohesion: 0.18
Nodes (11): 3.10 Player-prop cross-book EV backtest (historical, not the live CLV headline), 3.1 Sources, 3.2 Live snapshot collection, 3.3 Known data limitations, 3.4 Bet execution venues, 3.5 Preseason dry run (infrastructure validation, not a result), 3.6 Player props (infrastructure prepped, not active), 3.7 Receiver-level Elo (player-prop pricing infrastructure) (+3 more)

### Community 39 - "test_elo.py"
Cohesion: 0.06
Nodes (69): canonical_team(), compute_team_elo_ratings(), elo_win_probability(), mov_multiplier(), DataFrame, Elo rating system: opponent-adjusted team strength, sequential and leakage-free…, One row per game: each team's Elo rating *entering* that game (pre-game,…, Map a historical/relocated abbreviation to the current one a franchise's rating… (+61 more)

### Community 40 - "nfl-clv"
Cohesion: 0.20
Nodes (9): Data chronology: nflverse (historical) vs. Pinnacle (live), Historical props for backtesting — checked, blocked on paid access, Live monitoring: 24/7 services + SMS alerts, nfl-clv, Player props (prepped, not active), Preseason dry run, Quickstart, Repo tree (+1 more)

### Community 43 - "test_collect_props_historical.py"
Cohesion: 0.18
Nodes (19): datetime, MatchResult, OddsApiClient, OddsSnapshot, PointInTimeStore, backfill_historical_props(), find_historical_event_id(), pull_historical_prop_snapshot() (+11 more)

### Community 44 - "test_clv_metrics.py"
Cohesion: 0.16
Nodes (20): beat_rate(), bootstrap_ci(), clv_price(), clv_probability(), Closing Line Value metrics (blueprint Part B.3). CLV is measured two ways --…, How far the fair market moved toward your side after you bet. Positive means…, Whether the decimal price you took beats the closing price for the same side.…, Fraction of bets with positive CLV. (+12 more)

### Community 45 - "OddsApiClient"
Cohesion: 0.12
Nodes (27): Response, Session, OddsApiClient, _parse_int_header(), _parse_iso(), datetime, Historical per-event odds, snapshotted at the nearest available timestamp <=…, Shared retry/error-handling for both endpoints. Returns the raw successful… (+19 more)

### Community 46 - "Beating the Close, Not the Book: A CLV-First Case Study of NFL Betting Markets"
Cohesion: 0.25
Nodes (7): 7. Conclusion, Abstract, Appendix A. Repo structure and reproducibility, Appendix B. Full devig derivations, Appendix C. Glossary, Beating the Close, Not the Book: A CLV-First Case Study of NFL Betting Markets, References

### Community 47 - "5. Results"
Cohesion: 0.29
Nodes (7): 5.1 Devig method comparison, 5.2 Model calibration, 5.3 CLV results (headline), 5.4 Bootstrap confidence intervals, 5.5 Power analysis: what this sample size can and cannot tell us, 5.6 Drift monitor output, 5. Results

### Community 48 - "1. Introduction"
Cohesion: 0.40
Nodes (5): 1.1 Motivation, 1.2 Thesis, 1.3 Contributions, 1.4 What success means here, 1. Introduction

### Community 49 - "6. Discussion"
Cohesion: 0.40
Nodes (5): 6.1 Honest interpretation of the CLV result, 6.2 Where the market was hardest to beat, 6.3 Where the drift monitor fired, if it did, 6.4 Limitations, 6. Discussion

### Community 50 - "2. Background and Related Work"
Cohesion: 0.50
Nodes (4): 2.1 Market efficiency in sports betting, 2.2 Closing Line Value as an edge proxy, 2.3 Prior work, 2. Background and Related Work

## Knowledge Gaps
- **93 isolated node(s):** `Status`, `Data chronology: nflverse (historical) vs. Pinnacle (live)`, `Live monitoring: 24/7 services + SMS alerts`, `Preseason dry run`, `Historical props for backtesting — checked, blocked on paid access` (+88 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PointInTimeStore` connect `PointInTimeStore` to `Side`, `test_collect_scheduler.py`, `test_live_scan.py`, `scheduler.py`, `test_collect_props_historical.py`?**
  _High betweenness centrality (0.141) - this node is a cross-community bridge._
- **Why does `market_baseline()` connect `test_devig.py` to `test_live_scan.py`, `test_evaluate.py`, `PointInTimeStore`, `test_player_status.py`?**
  _High betweenness centrality (0.124) - this node is a cross-community bridge._
- **Why does `build_training_frame()` connect `test_evaluate.py` to `test_devig.py`, `test_features.py`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Are the 46 inferred relationships involving `PointInTimeStore` (e.g. with `BacktestEngine` and `clv_movement_report()`) actually correct?**
  _`PointInTimeStore` has 46 INFERRED edges - model-reasoned connections that need verification._
- **Are the 51 inferred relationships involving `Side` (e.g. with `BacktestBet` and `BetOrder`) actually correct?**
  _`Side` has 51 INFERRED edges - model-reasoned connections that need verification._
- **Are the 42 inferred relationships involving `Market` (e.g. with `BacktestBet` and `BetOrder`) actually correct?**
  _`Market` has 42 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `OddsApiClient` (e.g. with `main()` and `poll_once()`) actually correct?**
  _`OddsApiClient` has 21 INFERRED edges - model-reasoned connections that need verification._