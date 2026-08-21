# Graph Report - nfl_2026  (2026-08-20)

## Corpus Check
- 110 files · ~73,472 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1136 nodes · 2842 edges · 55 communities (46 shown, 9 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 368 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `fd1da23a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Side
- scheduler.py
- test_evaluate.py
- transform.py
- test_margin_total.py
- PointInTimeStore
- 4. Methodology
- Parking lot
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
- test_sizing.py
- DataFrame
- Series
- 3. Data
- test_elo.py
- NFL CLV Case Study: Blueprint
- props.py
- market_baseline
- test_correlated_props.py
- OddsApiClient
- Beating the Close, Not the Book: A CLV-First Case Study of NFL Betting Markets
- 5. Results
- 1. Introduction
- 6. Discussion
- 2. Background and Related Work
- test_props_scheduler.py
- test_game_level_features.py
- preseason.py
- OddsApiResponse
- client.py

## God Nodes (most connected - your core abstractions)
1. `Side` - 85 edges
2. `PointInTimeStore` - 83 edges
3. `Market` - 62 edges
4. `OddsApiClient` - 43 edges
5. `OddsSnapshot` - 35 edges
6. `Outcome` - 32 edges
7. `OddsApiResponse` - 31 edges
8. `settle()` - 28 edges
9. `OddsApiError` - 27 edges
10. `MatchResult` - 26 edges

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

## Communities (55 total, 9 thin omitted)

### Community 0 - "Side"
Cohesion: 0.05
Nodes (109): BacktestBet, BacktestEngine, BetOrder, DecisionPoint, _latest_fair_prob(), _latest_price(), _parse_kickoffs(), _payout() (+101 more)

### Community 1 - "scheduler.py"
Cohesion: 0.06
Nodes (78): date, CollectorState, current_period_end(), decide_poll(), _game_interval_minutes(), load_state(), _minutes_since(), _nearest_upcoming_hours() (+70 more)

### Community 2 - "test_evaluate.py"
Cohesion: 0.12
Nodes (27): brier_score(), log_loss(), power_analysis(), DataFrame, ndarray, Model evaluation (blueprint Part B.5). "This section is where you prove you are…, mean((p - y)^2). Lower is better., -mean(y*log(p) + (1-y)*log(1-p)). p is clipped away from exactly 0/1 so a… (+19 more)

### Community 3 - "transform.py"
Cohesion: 0.17
Nodes (28): build_team_name_map(), DataFrame, full team name -> abbreviation, restricted to abbrs used in `schedule`., build_schedule_index(), event_to_snapshots(), match_event(), MatchResult, DataFrame (+20 more)

### Community 4 - "test_margin_total.py"
Cohesion: 0.06
Nodes (74): CalibratedClassifierCV, HistGradientBoostingClassifier, Protocol, compare_to_baseline(), fit_calibrated_model(), fit_residual_std(), predict_calibrated_proba(), predict_over_proba() (+66 more)

### Community 5 - "PointInTimeStore"
Cohesion: 0.06
Nodes (78): BaseModel, main(), make_synthetic_snapshots(), datetime, End-to-end pipeline demo: pull -> store -> compare -> decide -> notify. `make…, _step(), main(), Live +EV monitor entrypoint: `python -m src.notify.monitor_run`. Meant to be… (+70 more)

### Community 6 - "4. Methodology"
Cohesion: 0.20
Nodes (10): 4.1 Odds conversion, 4.2 Devigging methods, 4.3 Closing Line Value, 4.4 Point-in-time backtesting framework, 4.5 Modeling approach, 4.6 Bet sizing, 4.7 Evaluation framework, 4.8 Non-stationarity and drift detection (+2 more)

### Community 8 - "test_devig.py"
Cohesion: 0.12
Nodes (30): compare_methods(), compare_methods_table(), devig_additive(), devig_multiplicative(), devig_power(), devig_shin(), DevigResult, overround() (+22 more)

### Community 9 - "test_features.py"
Cohesion: 0.12
Nodes (37): add_weather_features(), build_game_features(), _is_garbage_time(), DataFrame, Series, Feature builder (blueprint Part E): team-strength proxies from play-by-play.…, One row per game_id: home/away pre-game rolling EPA features plus the schedule…, Cleans and derives model-usable weather features from `roof`/… (+29 more)

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

### Community 35 - "test_sizing.py"
Cohesion: 0.14
Nodes (27): apply_bankroll_caps(), expected_value(), fractional_kelly(), kelly_fraction(), Expected value and Kelly bet sizing (blueprint Part B.4). Full Kelly is too…, EV of a unit bet at fair win probability p and decimal odds d., Full Kelly fraction of bankroll. Can be negative when the price is bad at this…, k * full Kelly. k in [0.25, 0.5] per the blueprint; default 0.375 is the… (+19 more)

### Community 38 - "3. Data"
Cohesion: 0.18
Nodes (11): 3.10 Player-prop cross-book strategies (historical, not the live CLV headline), 3.1 Sources, 3.2 Live snapshot collection, 3.3 Known data limitations, 3.4 Bet execution venues, 3.5 Preseason dry run (infrastructure validation, not a result), 3.6 Player props (infrastructure prepped, not active), 3.7 Receiver-level Elo (player-prop pricing infrastructure) (+3 more)

### Community 39 - "test_elo.py"
Cohesion: 0.06
Nodes (71): canonical_team(), compute_team_elo_ratings(), elo_win_probability(), mov_multiplier(), DataFrame, Elo rating system: opponent-adjusted team strength, sequential and leakage-free…, One row per game: each team's Elo rating *entering* that game (pre-game,…, Map a historical/relocated abbreviation to the current one a franchise's rating… (+63 more)

### Community 40 - "NFL CLV Case Study: Blueprint"
Cohesion: 0.06
Nodes (34): A simple, honest first model, B.1 Odds to implied probability, B.2 The vig, and why devigging is the real work, B.3 Closing Line Value, B.4 Bet sizing, B.5 Evaluation and, above all, sample size, Free static data, for backtester and baselines (cost: 0), Live intraday data, self-collected (the thing you cannot buy cheap) (+26 more)

### Community 42 - "props.py"
Cohesion: 0.16
Nodes (24): event_odds_to_prop_snapshots(), main(), poll_all_props(), poll_event_props(), datetime, ScheduleIndex, Player-prop odds collection. **Prepped, not active.** Live-checked 2026-08-17…, One event's worth of prop snapshots. Raises OddsApiError/RateLimitExceeded to… (+16 more)

### Community 43 - "market_baseline"
Cohesion: 0.05
Nodes (69): model_validator, find_arbitrage_spots(), find_prop_ev_spots(), pinnacle_fair_probs(), DataFrame, Cross-book player-prop strategies that don't rely on market timing: (1) a…, One row per (event_id, player_name, prop_stat) with both a Pinnacle Over and…, One row per (event, player, prop_stat, line, side, book) where `book`'s price… (+61 more)

### Community 44 - "test_correlated_props.py"
Cohesion: 0.10
Nodes (40): DataFrame, Series, bucket_favorite_strength(), build_team_game_outcomes(), correlated_edge(), estimate_game_specific_joint_prob(), measure_leg_correlation(), measure_leg_correlation_by_bucket() (+32 more)

### Community 45 - "OddsApiClient"
Cohesion: 0.24
Nodes (18): Session, OddsApiClient, parametrize, _response(), test_get_event_odds_hits_the_per_event_url(), test_get_event_odds_raises_rate_limit_exceeded_like_get_odds(), test_get_event_odds_wraps_the_single_event_object_in_a_list(), test_get_historical_event_odds_hits_the_historical_per_event_url() (+10 more)

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

### Community 51 - "test_props_scheduler.py"
Cohesion: 0.11
Nodes (42): decide_props_poll(), EventPollState, load_state(), PropsCollectorState, PropsPollDecision, datetime, Path, Budget-aware polling cadence for player props -- a different scheduling problem… (+34 more)

### Community 55 - "test_game_level_features.py"
Cohesion: 0.11
Nodes (38): current_injury_status(), current_team(), player_status_snapshot(), DataFrame, Current player status: which team a player is on, and their injury/game status,…, One row per player: their most recent roster team/status at or before…, One row per player with an injury-report history: their most recent…, One row per rostered player: current team (trade-aware) + current injury/game… (+30 more)

### Community 60 - "preseason.py"
Cohesion: 0.18
Nodes (20): build_preseason_match(), main(), poll_once(), Preseason dry-run collector: same collection mechanics as the real season…, One poll: fetch, match, transform, write. Returns counts for logging/testing --…, Build a MatchResult straight from the Odds API event, no nflverse schedule…, load_team_name_map(), Path (+12 more)

### Community 61 - "OddsApiResponse"
Cohesion: 0.17
Nodes (22): OddsApiError, OddsApiResponse, RuntimeError, RateLimitExceeded, Network or unexpected-response failure talking to The Odds API., The API rejected the request for quota/auth reasons (401/402/429)., backfill_historical_props(), find_historical_event_id() (+14 more)

### Community 64 - "client.py"
Cohesion: 0.15
Nodes (11): Response, _parse_int_header(), _parse_iso(), datetime, Thin HTTP wrapper around The Odds API. Talks to The Odds API directly (not…, Historical per-event odds, snapshotted at the nearest available timestamp <=…, Shared retry/error-handling for both endpoints. Returns the raw successful…, Bulk endpoint: one call returns every event in the sport's current slate. This… (+3 more)

## Knowledge Gaps
- **113 isolated node(s):** `Abstract`, `1.1 Motivation`, `1.2 Thesis`, `1.3 Contributions`, `1.4 What success means here` (+108 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PointInTimeStore` connect `PointInTimeStore` to `Side`, `scheduler.py`, `props.py`, `market_baseline`, `test_props_scheduler.py`, `preseason.py`, `OddsApiResponse`?**
  _High betweenness centrality (0.188) - this node is a cross-community bridge._
- **Why does `market_baseline()` connect `market_baseline` to `test_margin_total.py`, `PointInTimeStore`?**
  _High betweenness centrality (0.116) - this node is a cross-community bridge._
- **Why does `Side` connect `Side` to `market_baseline`, `props.py`, `transform.py`, `PointInTimeStore`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._
- **Are the 64 inferred relationships involving `Side` (e.g. with `BacktestBet` and `BetOrder`) actually correct?**
  _`Side` has 64 INFERRED edges - model-reasoned connections that need verification._
- **Are the 54 inferred relationships involving `PointInTimeStore` (e.g. with `BacktestEngine` and `clv_movement_report()`) actually correct?**
  _`PointInTimeStore` has 54 INFERRED edges - model-reasoned connections that need verification._
- **Are the 43 inferred relationships involving `Market` (e.g. with `BacktestBet` and `BetOrder`) actually correct?**
  _`Market` has 43 INFERRED edges - model-reasoned connections that need verification._
- **Are the 26 inferred relationships involving `OddsApiClient` (e.g. with `main()` and `poll_once()`) actually correct?**
  _`OddsApiClient` has 26 INFERRED edges - model-reasoned connections that need verification._