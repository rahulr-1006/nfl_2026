# Graph Report - nfl_2026  (2026-08-18)

## Corpus Check
- 97 files · ~57,828 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 929 nodes · 2240 edges · 49 communities (38 shown, 11 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 291 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d0883fae`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Side
- scheduler.py
- test_live_scan.py
- test_collect_transform.py
- test_evaluate.py
- PointInTimeStore
- props.py
- test_pass_rush_elo.py
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
- OddsApiResponse
- test_clv_metrics.py
- OddsApiClient
- test_collect_preseason.py
- preseason.py
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
- `_snapshot()` --uses--> `Market`  [INFERRED]
  tests/test_live_scan.py → src/store/schema.py
- `_snapshot()` --uses--> `Market`  [INFERRED]
  tests/test_monitor_run.py → src/store/schema.py
- `_snap()` --uses--> `Market`  [INFERRED]
  tests/test_pit_store.py → src/store/schema.py
- `test_event_id_filter()` --uses--> `Market`  [INFERRED]
  tests/test_pit_store.py → src/store/schema.py

## Import Cycles
- None detected.

## Communities (49 total, 11 thin omitted)

### Community 0 - "Side"
Cohesion: 0.08
Nodes (75): BacktestBet, BacktestEngine, BetOrder, DecisionPoint, _latest_fair_prob(), _latest_price(), _parse_kickoffs(), _payout() (+67 more)

### Community 1 - "scheduler.py"
Cohesion: 0.06
Nodes (76): BlockingScheduler, date, Path, CollectorState, current_period_end(), decide_poll(), _game_interval_minutes(), load_state() (+68 more)

### Community 2 - "test_live_scan.py"
Cohesion: 0.06
Nodes (73): main(), Live +EV monitor entrypoint: `python -m src.notify.monitor_run`. Meant to be…, One scan-and-alert cycle. Returns the number of alerts actually sent. Never…, run(), _escape_for_applescript(), RuntimeError, SMS/iMessage alerts via macOS Messages.app. No third-party account, no API key:…, AppleScript/Messages.app failed to send. (+65 more)

### Community 3 - "test_collect_transform.py"
Cohesion: 0.17
Nodes (27): build_team_name_map(), DataFrame, full team name -> abbreviation, restricted to abbrs used in `schedule`., build_schedule_index(), event_to_snapshots(), match_event(), MatchResult, DataFrame (+19 more)

### Community 4 - "test_evaluate.py"
Cohesion: 0.05
Nodes (73): CalibratedClassifierCV, HistGradientBoostingClassifier, ndarray, Pipeline, Protocol, compare_to_baseline(), fit_calibrated_model(), predict_calibrated_proba() (+65 more)

### Community 5 - "PointInTimeStore"
Cohesion: 0.06
Nodes (68): BaseModel, model_validator, clv_movement_report(), DataFrame, datetime, Preseason CLV-movement report: a dry run of the measurement pipeline…, (home_price_american, away_price_american) from a moneyline slice. None if the…, One row per preseason event with at least two distinct capture times: price and… (+60 more)

### Community 6 - "props.py"
Cohesion: 0.19
Nodes (21): event_odds_to_prop_snapshots(), poll_all_props(), poll_event_props(), datetime, ScheduleIndex, Player-prop odds collection. **Prepped, not active.** Live-checked 2026-08-17…, One event's worth of prop snapshots. Raises OddsApiError/RateLimitExceeded to…, `events`: iterable of (odds_api_event_id, home_team_name, away_team_name) --… (+13 more)

### Community 7 - "test_pass_rush_elo.py"
Cohesion: 0.12
Nodes (32): DataFrame, current_injury_status(), current_team(), player_status_snapshot(), Current player status: which team a player is on, and their injury/game status,…, One row per player: their most recent roster team/status at or before…, One row per player with an injury-report history: their most recent…, One row per rostered player: current team (trade-aware) + current injury/game… (+24 more)

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
Cohesion: 0.14
Nodes (26): Outcome, Side, build_player_stats_index(), normalize_player_name(), Settlement for player-prop (Over/Under) bets against nflverse's per-player game…, Batch-grade prop-shaped rows (event_id/game_id, player_name, prop_stat, side,…, Collapse punctuation/whitespace differences between an odds book's player name…, (game_id, player_display_name) -> {stat_column: value}, from nflreadpy's… (+18 more)

### Community 38 - "Beating the Close, Not the Book: A CLV-First Case Study of NFL Betting Markets"
Cohesion: 0.04
Nodes (48): 1.1 Motivation, 1.2 Thesis, 1.3 Contributions, 1.4 What success means here, 1. Introduction, 2.1 Market efficiency in sports betting, 2.2 Closing Line Value as an edge proxy, 2.3 Prior work (+40 more)

### Community 39 - "test_elo.py"
Cohesion: 0.07
Nodes (53): canonical_team(), compute_team_elo_ratings(), elo_win_probability(), mov_multiplier(), DataFrame, Elo rating system: opponent-adjusted team strength, sequential and leakage-free…, One row per game: each team's Elo rating *entering* that game (pre-game,…, Map a historical/relocated abbreviation to the current one a franchise's rating… (+45 more)

### Community 40 - "nfl-clv"
Cohesion: 0.20
Nodes (9): Data chronology: nflverse (historical) vs. Pinnacle (live), Historical props for backtesting — checked, blocked on paid access, Live monitoring: 24/7 services + SMS alerts, nfl-clv, Player props (prepped, not active), Preseason dry run, Quickstart, Repo tree (+1 more)

### Community 43 - "OddsApiResponse"
Cohesion: 0.15
Nodes (24): datetime, MatchResult, OddsApiClient, OddsSnapshot, PointInTimeStore, OddsApiResponse, backfill_historical_props(), find_historical_event_id() (+16 more)

### Community 44 - "test_clv_metrics.py"
Cohesion: 0.16
Nodes (20): beat_rate(), bootstrap_ci(), clv_price(), clv_probability(), Closing Line Value metrics (blueprint Part B.3). CLV is measured two ways --…, How far the fair market moved toward your side after you bet. Positive means…, Whether the decimal price you took beats the closing price for the same side.…, Fraction of bets with positive CLV. (+12 more)

### Community 45 - "OddsApiClient"
Cohesion: 0.11
Nodes (33): Response, Session, OddsApiClient, OddsApiError, _parse_int_header(), _parse_iso(), datetime, RuntimeError (+25 more)

### Community 47 - "test_collect_preseason.py"
Cohesion: 0.24
Nodes (16): build_preseason_match(), poll_once(), One poll: fetch, match, transform, write. Returns counts for logging/testing --…, Build a MatchResult straight from the Odds API event, no nflverse schedule…, RuntimeError, Raised when an Odds API event can't be joined to a schedule row., UnmatchedEventError, _preseason_event() (+8 more)

### Community 48 - "preseason.py"
Cohesion: 0.28
Nodes (7): main(), Preseason dry-run collector: same collection mechanics as the real season…, main(), Manual entrypoint: `python -m src.collect.props`. See module docstring -- not…, load_team_name_map(), Path, Team full-name -> abbreviation resolution. nflreadpy.load_teams() carries…

## Knowledge Gaps
- **92 isolated node(s):** `Status`, `Data chronology: nflverse (historical) vs. Pinnacle (live)`, `Live monitoring: 24/7 services + SMS alerts`, `Preseason dry run`, `Historical props for backtesting — checked, blocked on paid access` (+87 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PointInTimeStore` connect `PointInTimeStore` to `Side`, `scheduler.py`, `test_live_scan.py`, `props.py`, `OddsApiResponse`, `test_collect_preseason.py`, `preseason.py`?**
  _High betweenness centrality (0.129) - this node is a cross-community bridge._
- **Why does `settle_prop_snapshots()` connect `test_prop_settlement.py` to `test_pass_rush_elo.py`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Why does `build_player_stats_index()` connect `test_prop_settlement.py` to `test_pass_rush_elo.py`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Are the 46 inferred relationships involving `PointInTimeStore` (e.g. with `BacktestEngine` and `clv_movement_report()`) actually correct?**
  _`PointInTimeStore` has 46 INFERRED edges - model-reasoned connections that need verification._
- **Are the 51 inferred relationships involving `Side` (e.g. with `BacktestBet` and `BetOrder`) actually correct?**
  _`Side` has 51 INFERRED edges - model-reasoned connections that need verification._
- **Are the 42 inferred relationships involving `Market` (e.g. with `BacktestBet` and `BetOrder`) actually correct?**
  _`Market` has 42 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `OddsApiClient` (e.g. with `main()` and `poll_once()`) actually correct?**
  _`OddsApiClient` has 21 INFERRED edges - model-reasoned connections that need verification._