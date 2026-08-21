# Graph Report - nfl_2026  (2026-08-21)

## Corpus Check
- 120 files · ~91,621 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1353 nodes · 3466 edges · 61 communities (54 shown, 7 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 486 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ac0e7498`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Market
- test_collect_scheduler.py
- test_evaluate.py
- pit_store.py
- test_margin_total.py
- props.py
- 4. Methodology
- Parking lot
- test_devig.py
- add_rest_travel_features
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
- Side
- test_middling.py
- market_baseline
- 3. Data
- test_elo.py
- NFL CLV Case Study: Blueprint
- OddsApiResponse
- MatchResult
- Methodology backlog
- test_correlated_props.py
- OddsApiClient
- Beating the Close, Not the Book: A CLV-First Case Study of NFL Betting Markets
- 5. Results
- 1. Introduction
- 6. Discussion
- 2. Background and Related Work
- test_props_scheduler.py
- client.py
- PointInTimeStore
- schema.py
- test_game_level_features.py
- test_validation.py
- best_middle_for_game
- ValueError
- test_live_scan.py
- engine.py

## God Nodes (most connected - your core abstractions)
1. `Side` - 118 edges
2. `Market` - 101 edges
3. `PointInTimeStore` - 98 edges
4. `OddsApiClient` - 43 edges
5. `OddsSnapshot` - 39 edges
6. `Outcome` - 32 edges
7. `OddsApiResponse` - 31 edges
8. `settle()` - 30 edges
9. `OddsApiError` - 27 edges
10. `MatchResult` - 26 edges

## Surprising Connections (you probably didn't know these)
- `test_get_odds_raises_odds_api_error_on_other_bad_status()` --uses--> `OddsApiError`  [INFERRED]
  tests/test_collect_client.py → src/collect/client.py
- `test_get_odds_retries_network_errors_then_raises()` --uses--> `OddsApiError`  [INFERRED]
  tests/test_collect_client.py → src/collect/client.py
- `test_poll_once_never_raises_on_api_error()` --uses--> `OddsApiError`  [INFERRED]
  tests/test_collect_preseason.py → src/collect/client.py
- `test_poll_all_props_records_failed_calls_without_raising()` --uses--> `OddsApiError`  [INFERRED]
  tests/test_collect_props.py → src/collect/client.py
- `test_tick_raises_collector_halted_after_too_many_failures()` --uses--> `OddsApiError`  [INFERRED]
  tests/test_collect_scheduler.py → src/collect/client.py

## Import Cycles
- None detected.

## Communities (61 total, 7 thin omitted)

### Community 0 - "Market"
Cohesion: 0.26
Nodes (22): Market, Outcome, str, Grade a single (market, side, line) bet against a final score., settle(), _snapshot_row(), test_moneyline_away_loss(), test_moneyline_home_win() (+14 more)

### Community 1 - "test_collect_scheduler.py"
Cohesion: 0.05
Nodes (77): CollectorState, current_period_end(), decide_poll(), _game_interval_minutes(), load_state(), _minutes_since(), _nearest_upcoming_hours(), parse_quota_headers() (+69 more)

### Community 2 - "test_evaluate.py"
Cohesion: 0.12
Nodes (27): brier_score(), log_loss(), power_analysis(), DataFrame, ndarray, Model evaluation (blueprint Part B.5). "This section is where you prove you are…, mean((p - y)^2). Lower is better., -mean(y*log(p) + (1-y)*log(1-p)). p is clipped away from exactly 0/1 so a… (+19 more)

### Community 3 - "pit_store.py"
Cohesion: 0.14
Nodes (27): build_preseason_match(), poll_once(), Preseason dry-run collector: same collection mechanics as the real season…, One poll: fetch, match, transform, write. Returns counts for logging/testing --…, Build a MatchResult straight from the Odds API event, no nflverse schedule…, Scheduler wiring: one `tick()` per poll opportunity, run on an interval.…, event_to_snapshots(), datetime (+19 more)

### Community 4 - "test_margin_total.py"
Cohesion: 0.05
Nodes (87): CalibratedClassifierCV, HistGradientBoostingClassifier, Protocol, _fit_residual_stds(), main(), DataFrame, Middle-scan entrypoint: `python -m src.backtest.middle_scan`. A manual, run-by-…, (sigma_margin, sigma_total), reusing the exact fitting pipeline already… (+79 more)

### Community 5 - "props.py"
Cohesion: 0.14
Nodes (24): main(), event_odds_to_prop_snapshots(), main(), poll_all_props(), poll_event_props(), datetime, ScheduleIndex, Player-prop odds collection. **Prepped, not active.** Live-checked 2026-08-17… (+16 more)

### Community 6 - "4. Methodology"
Cohesion: 0.18
Nodes (11): 4.10 Middling: exploiting real line movement over time (2026-08-20), 4.1 Odds conversion, 4.2 Devigging methods, 4.3 Closing Line Value, 4.4 Point-in-time backtesting framework, 4.5 Modeling approach, 4.6 Bet sizing, 4.7 Evaluation framework (+3 more)

### Community 8 - "test_devig.py"
Cohesion: 0.12
Nodes (30): compare_methods(), compare_methods_table(), devig_additive(), devig_multiplicative(), devig_power(), devig_shin(), DevigResult, overround() (+22 more)

### Community 9 - "add_rest_travel_features"
Cohesion: 0.06
Nodes (75): add_rest_travel_features(), add_weather_features(), build_game_features(), _is_garbage_time(), DataFrame, Series, Feature builder (blueprint Part E): team-strength proxies from play-by-play.…, One row per game_id: home/away pre-game rolling EPA features plus the schedule… (+67 more)

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

### Community 35 - "Side"
Cohesion: 0.17
Nodes (27): build_player_stats_index(), normalize_player_name(), DataFrame, Settlement for player-prop (Over/Under) bets against nflverse's per-player game…, Batch-grade prop-shaped rows (event_id/game_id, player_name, prop_stat, side,…, Collapse punctuation/whitespace differences between an odds book's player name…, (game_id, player_display_name) -> {stat_column: value}, from nflreadpy's…, Grade a single Over/Under prop bet. Pushes are real for integer-valued stats… (+19 more)

### Community 36 - "test_middling.py"
Cohesion: 0.09
Nodes (43): find_middle_opportunities(), _interval_prob(), line_threshold(), middle_ev(), middle_window(), MiddleOpportunity, datetime, Middling: betting opposite sides of the SAME game's spread/total at two… (+35 more)

### Community 37 - "market_baseline"
Cohesion: 0.05
Nodes (76): model_validator, find_arbitrage_spots(), find_prop_ev_spots(), pinnacle_fair_probs(), DataFrame, Timedelta, Cross-book player-prop strategies that don't rely on market timing: (1) a…, One row per (event, player, prop_stat, line, side, book) where `book`'s price… (+68 more)

### Community 38 - "3. Data"
Cohesion: 0.18
Nodes (11): 3.10 Player-prop cross-book strategies (historical, not the live CLV headline), 3.1 Sources, 3.2 Live snapshot collection, 3.3 Known data limitations, 3.4 Bet execution venues, 3.5 Preseason dry run (infrastructure validation, not a result), 3.6 Player props (infrastructure prepped, not active), 3.7 Receiver-level Elo (player-prop pricing infrastructure) (+3 more)

### Community 39 - "test_elo.py"
Cohesion: 0.06
Nodes (71): canonical_team(), compute_team_elo_ratings(), elo_win_probability(), mov_multiplier(), DataFrame, Elo rating system: opponent-adjusted team strength, sequential and leakage-free…, One row per game: each team's Elo rating *entering* that game (pre-game,…, Map a historical/relocated abbreviation to the current one a franchise's rating… (+63 more)

### Community 40 - "NFL CLV Case Study: Blueprint"
Cohesion: 0.06
Nodes (34): A simple, honest first model, B.1 Odds to implied probability, B.2 The vig, and why devigging is the real work, B.3 Closing Line Value, B.4 Bet sizing, B.5 Evaluation and, above all, sample size, Free static data, for backtester and baselines (cost: 0), Live intraday data, self-collected (the thing you cannot buy cheap) (+26 more)

### Community 41 - "OddsApiResponse"
Cohesion: 0.19
Nodes (21): OddsApiError, OddsApiResponse, RuntimeError, RateLimitExceeded, Network or unexpected-response failure talking to The Odds API., The API rejected the request for quota/auth reasons (401/402/429)., backfill_historical_props(), find_historical_event_id() (+13 more)

### Community 42 - "MatchResult"
Cohesion: 0.19
Nodes (23): build_team_name_map(), DataFrame, Team full-name -> abbreviation resolution. nflreadpy.load_teams() carries…, full team name -> abbreviation, restricted to abbrs used in `schedule`., build_schedule_index(), match_event(), MatchResult, DataFrame (+15 more)

### Community 43 - "Methodology backlog"
Cohesion: 0.29
Nodes (6): 1. Rest/travel differential — **tested, negative result**, 2. Joint margin/total correlated distribution — idea, 3. Reverse line movement / steam detection — idea, 4. Player-prop middling — idea, blocked on live props posting, Blocked on data, not on ideas, Methodology backlog

### Community 44 - "test_correlated_props.py"
Cohesion: 0.07
Nodes (58): bucket_edge(), bucket_favorite_strength(), build_team_game_outcomes(), correlated_edge(), estimate_game_specific_joint_prob(), is_bucket_validated(), measure_leg_correlation(), measure_leg_correlation_by_bucket() (+50 more)

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
Nodes (43): decide_props_poll(), EventPollState, load_state(), PropsCollectorState, PropsPollDecision, datetime, Path, Budget-aware polling cadence for player props -- a different scheduling problem… (+35 more)

### Community 52 - "client.py"
Cohesion: 0.15
Nodes (11): Response, _parse_int_header(), _parse_iso(), datetime, Thin HTTP wrapper around The Odds API. Talks to The Odds API directly (not…, Historical per-event odds, snapshotted at the nearest available timestamp <=…, Shared retry/error-handling for both endpoints. Returns the raw successful…, Bulk endpoint: one call returns every event in the sport's current slate. This… (+3 more)

### Community 53 - "PointInTimeStore"
Cohesion: 0.09
Nodes (51): BaseModel, BacktestEngine, BetOrder, DecisionPoint, What a strategy sees when it's given a chance to act. `visible_snapshots` is…, A strategy's decision to bet, returned from a Strategy callable. None means "no…, LeakageError, PointInTimeStore (+43 more)

### Community 54 - "schema.py"
Cohesion: 0.19
Nodes (11): home_spread_line(), Convert nflverse's spread_line into the sportsbook side-line convention that…, datetime, Enum, Point-in-time odds snapshot schema. One row = one price, for one side, at one…, utcnow(), Regression guard for the sign-convention bug: feeding nflverse's raw…, Regression guard for the trimmed-schema cache: src/model/features.py depends on… (+3 more)

### Community 55 - "test_game_level_features.py"
Cohesion: 0.11
Nodes (38): current_injury_status(), current_team(), player_status_snapshot(), DataFrame, Current player status: which team a player is on, and their injury/game status,…, One row per player: their most recent roster team/status at or before…, One row per player with an injury-report history: their most recent…, One row per rostered player: current team (trade-aware) + current injury/game… (+30 more)

### Community 56 - "test_validation.py"
Cohesion: 0.07
Nodes (51): benjamini_hochberg(), expanding_season_folds(), _lift(), paired_permutation_test_mean_diff(), permutation_test_lift(), DataFrame, ndarray, Series (+43 more)

### Community 57 - "best_middle_for_game"
Cohesion: 0.14
Nodes (20): _best_line(), best_middle_for_game(), pinnacle_reference_line(), DataFrame, Series, The single most favorable real line observed for this side, exploiting…, The single WIDEST middle window achievable from real quotes for one game, one…, A market-consensus estimate of the true outcome (home_margin for SPREAD,… (+12 more)

### Community 58 - "ValueError"
Cohesion: 0.24
Nodes (14): build_results_index(), GameResult, _outcome_from_margin(), DataFrame, Enum, Settlement: grade win/loss/push outcomes against nflverse final scores.…, Batch-grade snapshot-shaped rows (event_id, market, side, line columns) against…, game_id -> GameResult, restricted to completed games (both scores present). (+6 more)

### Community 59 - "test_live_scan.py"
Cohesion: 0.05
Nodes (82): main(), make_synthetic_snapshots(), datetime, End-to-end pipeline demo: pull -> store -> compare -> decide -> notify. `make…, _step(), main(), Live +EV monitor entrypoint: `python -m src.notify.monitor_run`. Meant to be…, One scan-and-alert cycle. Returns the number of alerts actually sent. Never… (+74 more)

### Community 63 - "engine.py"
Cohesion: 0.23
Nodes (12): BacktestBet, _latest_fair_prob(), _latest_price(), _parse_kickoffs(), _payout(), DataFrame, datetime, Series (+4 more)

## Knowledge Gaps
- **119 isolated node(s):** `nfl-clv`, `graphify`, `Usage`, `What graphify is for`, `Step 0 - GitHub repos and multi-path merge (only if a URL or several paths)` (+114 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PointInTimeStore` connect `PointInTimeStore` to `test_collect_scheduler.py`, `pit_store.py`, `test_margin_total.py`, `market_baseline`, `test_middling.py`, `props.py`, `OddsApiResponse`, `test_props_scheduler.py`, `test_live_scan.py`, `engine.py`?**
  _High betweenness centrality (0.189) - this node is a cross-community bridge._
- **Why does `Side` connect `Side` to `Market`, `pit_store.py`, `test_middling.py`, `props.py`, `test_margin_total.py`, `market_baseline`, `MatchResult`, `PointInTimeStore`, `schema.py`, `best_middle_for_game`, `ValueError`, `test_live_scan.py`, `engine.py`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Why does `market_baseline()` connect `market_baseline` to `test_live_scan.py`, `test_margin_total.py`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 94 inferred relationships involving `Side` (e.g. with `BacktestBet` and `BetOrder`) actually correct?**
  _`Side` has 94 INFERRED edges - model-reasoned connections that need verification._
- **Are the 79 inferred relationships involving `Market` (e.g. with `BacktestBet` and `BetOrder`) actually correct?**
  _`Market` has 79 INFERRED edges - model-reasoned connections that need verification._
- **Are the 65 inferred relationships involving `PointInTimeStore` (e.g. with `BacktestEngine` and `run()`) actually correct?**
  _`PointInTimeStore` has 65 INFERRED edges - model-reasoned connections that need verification._
- **Are the 26 inferred relationships involving `OddsApiClient` (e.g. with `main()` and `poll_once()`) actually correct?**
  _`OddsApiClient` has 26 INFERRED edges - model-reasoned connections that need verification._