# Graph Report - nfl_2026  (2026-08-17)

## Corpus Check
- 86 files · ~46,041 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 728 nodes · 1917 edges · 35 communities (29 shown, 6 thin omitted)
- Extraction: 83% EXTRACTED · 17% INFERRED · 0% AMBIGUOUS · INFERRED: 323 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `81236401`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Side
- scheduler.py
- test_live_scan.py
- test_collect_transform.py
- test_evaluate.py
- market_baseline
- OddsApiClient
- PointInTimeStore
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

## God Nodes (most connected - your core abstractions)
1. `Side` - 81 edges
2. `PointInTimeStore` - 75 edges
3. `Market` - 60 edges
4. `OddsApiClient` - 38 edges
5. `OddsSnapshot` - 33 edges
6. `Outcome` - 32 edges
7. `settle()` - 28 edges
8. `tick()` - 25 edges
9. `OddsApiError` - 24 edges
10. `MatchResult` - 24 edges

## Surprising Connections (you probably didn't know these)
- `test_favorite_and_underdog_decimal_conversion()` --calls--> `american_to_decimal()`  [INFERRED]
  tests/test_schema.py → src/devig/convert.py
- `test_event_odds_to_prop_snapshots_parses_over_under_pair()` --uses--> `Market`  [INFERRED]
  tests/test_collect_props.py → src/store/schema.py
- `test_event_to_snapshots_maps_markets_and_sides()` --uses--> `Market`  [INFERRED]
  tests/test_collect_transform.py → src/store/schema.py
- `_snapshot()` --uses--> `Market`  [INFERRED]
  tests/test_live_scan.py → src/store/schema.py
- `_snapshot()` --uses--> `Market`  [INFERRED]
  tests/test_monitor_run.py → src/store/schema.py

## Import Cycles
- None detected.

## Communities (35 total, 6 thin omitted)

### Community 0 - "Side"
Cohesion: 0.06
Nodes (95): BacktestBet, BacktestEngine, BetOrder, DecisionPoint, _latest_fair_prob(), _latest_price(), _parse_kickoffs(), _payout() (+87 more)

### Community 1 - "scheduler.py"
Cohesion: 0.06
Nodes (75): BlockingScheduler, date, CollectorState, current_period_end(), decide_poll(), _game_interval_minutes(), load_state(), _minutes_since() (+67 more)

### Community 2 - "test_live_scan.py"
Cohesion: 0.06
Nodes (73): main(), Live +EV monitor entrypoint: `python -m src.notify.monitor_run`. Meant to be…, One scan-and-alert cycle. Returns the number of alerts actually sent. Never…, run(), _escape_for_applescript(), RuntimeError, SMS/iMessage alerts via macOS Messages.app. No third-party account, no API key:…, AppleScript/Messages.app failed to send. (+65 more)

### Community 3 - "test_collect_transform.py"
Cohesion: 0.17
Nodes (28): build_team_name_map(), DataFrame, full team name -> abbreviation, restricted to abbrs used in `schedule`., build_schedule_index(), event_to_snapshots(), match_event(), MatchResult, DataFrame (+20 more)

### Community 4 - "test_evaluate.py"
Cohesion: 0.06
Nodes (63): CalibratedClassifierCV, compare_to_baseline(), fit_calibrated_model(), predict_calibrated_proba(), DataFrame, Pipeline, Series, Calibration layer (blueprint Part E): Platt scaling / isotonic regression on… (+55 more)

### Community 5 - "market_baseline"
Cohesion: 0.07
Nodes (50): model_validator, beat_rate(), bootstrap_ci(), clv_price(), clv_probability(), Closing Line Value metrics (blueprint Part B.3). CLV is measured two ways --…, How far the fair market moved toward your side after you bet. Positive means…, Whether the decimal price you took beats the closing price for the same side.… (+42 more)

### Community 6 - "OddsApiClient"
Cohesion: 0.05
Nodes (89): Response, Session, OddsApiClient, OddsApiError, OddsApiResponse, _parse_int_header(), _parse_iso(), datetime (+81 more)

### Community 7 - "PointInTimeStore"
Cohesion: 0.10
Nodes (34): BaseModel, LeakageError, PointInTimeStore, DataFrame, datetime, Path, RuntimeError, The only read path. Returns rows visible at `decision_time`, and nothing later. (+26 more)

### Community 8 - "test_devig.py"
Cohesion: 0.12
Nodes (30): compare_methods(), compare_methods_table(), devig_additive(), devig_multiplicative(), devig_power(), devig_shin(), DevigResult, overround() (+22 more)

### Community 9 - "test_features.py"
Cohesion: 0.21
Nodes (19): build_game_features(), DataFrame, Feature builder (blueprint Part E): team-strength proxies from play-by-play.…, Collapse play-by-play to one row per (game_id, team): offensive and defensive…, Pre-game rolling team-strength features, one row per (game_id, team). `window`…, One row per game_id: home/away pre-game rolling EPA features plus the schedule…, rolling_team_strength(), team_game_epa() (+11 more)

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

## Knowledge Gaps
- **44 isolated node(s):** `graphify`, `Usage`, `What graphify is for`, `Step 0 - GitHub repos and multi-path merge (only if a URL or several paths)`, `Step 1 - Ensure graphify is installed` (+39 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PointInTimeStore` connect `PointInTimeStore` to `Side`, `scheduler.py`, `test_live_scan.py`, `market_baseline`, `OddsApiClient`?**
  _High betweenness centrality (0.196) - this node is a cross-community bridge._
- **Why does `market_baseline()` connect `market_baseline` to `test_live_scan.py`, `test_evaluate.py`?**
  _High betweenness centrality (0.129) - this node is a cross-community bridge._
- **Why does `Side` connect `Side` to `test_live_scan.py`, `test_collect_transform.py`, `market_baseline`, `OddsApiClient`, `PointInTimeStore`?**
  _High betweenness centrality (0.111) - this node is a cross-community bridge._
- **Are the 61 inferred relationships involving `Side` (e.g. with `BacktestBet` and `BetOrder`) actually correct?**
  _`Side` has 61 INFERRED edges - model-reasoned connections that need verification._
- **Are the 50 inferred relationships involving `PointInTimeStore` (e.g. with `BacktestEngine` and `clv_movement_report()`) actually correct?**
  _`PointInTimeStore` has 50 INFERRED edges - model-reasoned connections that need verification._
- **Are the 42 inferred relationships involving `Market` (e.g. with `BacktestBet` and `BetOrder`) actually correct?**
  _`Market` has 42 INFERRED edges - model-reasoned connections that need verification._
- **Are the 24 inferred relationships involving `OddsApiClient` (e.g. with `main()` and `poll_once()`) actually correct?**
  _`OddsApiClient` has 24 INFERRED edges - model-reasoned connections that need verification._