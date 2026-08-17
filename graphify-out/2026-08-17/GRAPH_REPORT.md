# Graph Report - nfl_2026  (2026-08-17)

## Corpus Check
- 91 files · ~52,408 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 870 nodes · 2113 edges · 51 communities (39 shown, 12 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 289 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `41a09b37`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Side
- test_collect_scheduler.py
- test_live_scan.py
- props.py
- test_train.py
- market_baseline
- test_evaluate.py
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
- test_prop_settlement.py
- datetime
- DataFrame
- Beating the Close, Not the Book: A CLV-First Case Study of NFL Betting Markets
- test_elo.py
- nfl-clv
- ndarray
- Pipeline
- scheduler.py
- test_collect_preseason.py
- OddsApiClient
- match_event
- test_collect_transform.py
- preseason.py
- pit_store.py
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
10. `TransformError` - 21 edges

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

## Communities (51 total, 12 thin omitted)

### Community 0 - "Side"
Cohesion: 0.08
Nodes (78): BacktestBet, BacktestEngine, BetOrder, DecisionPoint, _latest_fair_prob(), _latest_price(), _parse_kickoffs(), _payout() (+70 more)

### Community 1 - "test_collect_scheduler.py"
Cohesion: 0.09
Nodes (50): date, CollectorState, current_period_end(), decide_poll(), _game_interval_minutes(), load_state(), _minutes_since(), _nearest_upcoming_hours() (+42 more)

### Community 2 - "test_live_scan.py"
Cohesion: 0.05
Nodes (79): datetime, OddsSnapshot, main(), make_synthetic_snapshots(), End-to-end pipeline demo: pull -> store -> compare -> decide -> notify. `make…, _step(), main(), Live +EV monitor entrypoint: `python -m src.notify.monitor_run`. Meant to be… (+71 more)

### Community 3 - "props.py"
Cohesion: 0.19
Nodes (21): event_odds_to_prop_snapshots(), poll_all_props(), poll_event_props(), datetime, ScheduleIndex, Player-prop odds collection. **Prepped, not active.** Live-checked 2026-08-17…, One event's worth of prop snapshots. Raises OddsApiError/RateLimitExceeded to…, `events`: iterable of (odds_api_event_id, home_team_name, away_team_name) --… (+13 more)

### Community 4 - "test_train.py"
Cohesion: 0.09
Nodes (46): CalibratedClassifierCV, HistGradientBoostingClassifier, ndarray, Pipeline, Protocol, compare_to_baseline(), fit_calibrated_model(), predict_calibrated_proba() (+38 more)

### Community 5 - "market_baseline"
Cohesion: 0.07
Nodes (50): model_validator, beat_rate(), bootstrap_ci(), clv_price(), clv_probability(), Closing Line Value metrics (blueprint Part B.3). CLV is measured two ways --…, How far the fair market moved toward your side after you bet. Positive means…, Whether the decimal price you took beats the closing price for the same side.… (+42 more)

### Community 6 - "test_evaluate.py"
Cohesion: 0.12
Nodes (27): brier_score(), log_loss(), power_analysis(), DataFrame, ndarray, Model evaluation (blueprint Part B.5). "This section is where you prove you are…, mean((p - y)^2). Lower is better., -mean(y*log(p) + (1-y)*log(1-p)). p is clipped away from exactly 0/1 so a… (+19 more)

### Community 7 - "PointInTimeStore"
Cohesion: 0.10
Nodes (34): BaseModel, LeakageError, PointInTimeStore, DataFrame, datetime, Path, RuntimeError, The only read path. Returns rows visible at `decision_time`, and nothing later. (+26 more)

### Community 8 - "test_devig.py"
Cohesion: 0.12
Nodes (30): compare_methods(), compare_methods_table(), devig_additive(), devig_multiplicative(), devig_power(), devig_shin(), DevigResult, overround() (+22 more)

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
Cohesion: 0.13
Nodes (27): DataFrame, Outcome, Side, build_player_stats_index(), normalize_player_name(), Settlement for player-prop (Over/Under) bets against nflverse's per-player game…, Batch-grade prop-shaped rows (event_id/game_id, player_name, prop_stat, side,…, Collapse punctuation/whitespace differences between an odds book's player name… (+19 more)

### Community 38 - "Beating the Close, Not the Book: A CLV-First Case Study of NFL Betting Markets"
Cohesion: 0.04
Nodes (45): 1.1 Motivation, 1.2 Thesis, 1.3 Contributions, 1.4 What success means here, 1. Introduction, 2.1 Market efficiency in sports betting, 2.2 Closing Line Value as an edge proxy, 2.3 Prior work (+37 more)

### Community 39 - "test_elo.py"
Cohesion: 0.10
Nodes (40): canonical_team(), compute_team_elo_ratings(), elo_win_probability(), mov_multiplier(), DataFrame, Elo rating system: opponent-adjusted team strength, sequential and leakage-free…, One row per game: each team's Elo rating *entering* that game (pre-game,…, Map a historical/relocated abbreviation to the current one a franchise's rating… (+32 more)

### Community 40 - "nfl-clv"
Cohesion: 0.20
Nodes (9): Data chronology: nflverse (historical) vs. Pinnacle (live), Historical props for backtesting — checked, blocked on paid access, Live monitoring: 24/7 services + SMS alerts, nfl-clv, Player props (prepped, not active), Preseason dry run, Quickstart, Repo tree (+1 more)

### Community 43 - "scheduler.py"
Cohesion: 0.15
Nodes (19): BlockingScheduler, Path, Config, load_config(), Path, Collector configuration. Everything The Odds API's free-tier budget forces us…, Build a Config from environment variables (or an injected mapping for tests).…, build_context() (+11 more)

### Community 44 - "test_collect_preseason.py"
Cohesion: 0.24
Nodes (16): build_preseason_match(), poll_once(), One poll: fetch, match, transform, write. Returns counts for logging/testing --…, Build a MatchResult straight from the Odds API event, no nflverse schedule…, RuntimeError, Raised when an Odds API event can't be joined to a schedule row., UnmatchedEventError, _preseason_event() (+8 more)

### Community 45 - "OddsApiClient"
Cohesion: 0.08
Nodes (50): MatchResult, OddsApiClient, PointInTimeStore, Response, Session, OddsApiClient, OddsApiError, OddsApiResponse (+42 more)

### Community 46 - "match_event"
Cohesion: 0.23
Nodes (15): build_team_name_map(), DataFrame, full team name -> abbreviation, restricted to abbrs used in `schedule`., build_schedule_index(), match_event(), DataFrame, ScheduleIndex, (season, home_abbr, away_abbr) -> MatchResult, built once at startup. (+7 more)

### Community 47 - "test_collect_transform.py"
Cohesion: 0.33
Nodes (13): event_to_snapshots(), MatchResult, datetime, Raw Odds API JSON -> OddsSnapshot list, and event -> schedule matching.…, All bookmakers in the event, not just Pinnacle — extra bookmakers cost nothing…, _resolve_side_and_line(), _event(), _pinnacle_block() (+5 more)

### Community 48 - "preseason.py"
Cohesion: 0.28
Nodes (7): main(), Preseason dry-run collector: same collection mechanics as the real season…, main(), Manual entrypoint: `python -m src.collect.props`. See module docstring -- not…, load_team_name_map(), Path, Team full-name -> abbreviation resolution. nflreadpy.load_teams() carries…

## Knowledge Gaps
- **89 isolated node(s):** `Status`, `Data chronology: nflverse (historical) vs. Pinnacle (live)`, `Live monitoring: 24/7 services + SMS alerts`, `Preseason dry run`, `Historical props for backtesting — checked, blocked on paid access` (+84 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PointInTimeStore` connect `PointInTimeStore` to `Side`, `test_collect_scheduler.py`, `test_live_scan.py`, `props.py`, `market_baseline`, `scheduler.py`, `test_collect_preseason.py`, `OddsApiClient`, `preseason.py`, `pit_store.py`?**
  _High betweenness centrality (0.141) - this node is a cross-community bridge._
- **Why does `market_baseline()` connect `market_baseline` to `test_live_scan.py`, `test_train.py`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Why does `build_training_frame()` connect `test_train.py` to `test_features.py`, `market_baseline`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Are the 46 inferred relationships involving `PointInTimeStore` (e.g. with `BacktestEngine` and `clv_movement_report()`) actually correct?**
  _`PointInTimeStore` has 46 INFERRED edges - model-reasoned connections that need verification._
- **Are the 51 inferred relationships involving `Side` (e.g. with `BacktestBet` and `BetOrder`) actually correct?**
  _`Side` has 51 INFERRED edges - model-reasoned connections that need verification._
- **Are the 42 inferred relationships involving `Market` (e.g. with `BacktestBet` and `BetOrder`) actually correct?**
  _`Market` has 42 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `OddsApiClient` (e.g. with `main()` and `poll_once()`) actually correct?**
  _`OddsApiClient` has 21 INFERRED edges - model-reasoned connections that need verification._