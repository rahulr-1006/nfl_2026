# Graph Report - nfl_2026  (2026-08-20)

## Corpus Check
- 116 files · ~83,942 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1280 nodes · 3300 edges · 71 communities (64 shown, 7 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 481 edges (avg confidence: 0.53)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d2aea55c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Side
- scheduler.py
- test_evaluate.py
- transform.py
- test_train.py
- test_sizing.py
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
- test_middling.py
- middling.py
- test_prop_settlement.py
- 3. Data
- test_elo.py
- NFL CLV Case Study: Blueprint
- preseason.py
- props.py
- test_clv_metrics.py
- test_correlated_props.py
- OddsApiClient
- Beating the Close, Not the Book: A CLV-First Case Study of NFL Betting Markets
- 5. Results
- 1. Introduction
- 6. Discussion
- 2. Background and Related Work
- OddsApiResponse
- market_baseline
- test_load_static.py
- OddsSnapshot
- test_game_level_features.py
- test_validation.py
- PointInTimeStore
- calibration.py
- test_live_scan.py
- test_collect_preseason.py
- OddsApiError
- demo_pipeline.py
- middle_scan.py
- client.py
- test_backtest_engine.py
- engine.py
- test_margin_total.py
- american_to_decimal
- ValueError
- run

## God Nodes (most connected - your core abstractions)
1. `Side` - 115 edges
2. `Market` - 101 edges
3. `PointInTimeStore` - 94 edges
4. `OddsApiClient` - 43 edges
5. `OddsSnapshot` - 39 edges
6. `Outcome` - 32 edges
7. `OddsApiResponse` - 31 edges
8. `settle()` - 30 edges
9. `OddsApiError` - 27 edges
10. `MatchResult` - 26 edges

## Surprising Connections (you probably didn't know these)
- `test_favorite_and_underdog_decimal_conversion()` --calls--> `american_to_decimal()`  [INFERRED]
  tests/test_schema.py → src/devig/convert.py
- `test_get_odds_raises_odds_api_error_on_other_bad_status()` --uses--> `OddsApiError`  [INFERRED]
  tests/test_collect_client.py → src/collect/client.py
- `test_get_odds_retries_network_errors_then_raises()` --uses--> `OddsApiError`  [INFERRED]
  tests/test_collect_client.py → src/collect/client.py
- `test_poll_once_never_raises_on_api_error()` --uses--> `OddsApiError`  [INFERRED]
  tests/test_collect_preseason.py → src/collect/client.py
- `test_poll_all_props_records_failed_calls_without_raising()` --uses--> `OddsApiError`  [INFERRED]
  tests/test_collect_props.py → src/collect/client.py

## Import Cycles
- None detected.

## Communities (71 total, 7 thin omitted)

### Community 0 - "Side"
Cohesion: 0.25
Nodes (25): Market, Enum, str, Side, Batch-grade snapshot-shaped rows (event_id, market, side, line columns) against…, Grade a single (market, side, line) bet against a final score., settle(), settle_snapshots() (+17 more)

### Community 1 - "scheduler.py"
Cohesion: 0.07
Nodes (66): date, CollectorState, current_period_end(), decide_poll(), _game_interval_minutes(), load_state(), _minutes_since(), _nearest_upcoming_hours() (+58 more)

### Community 2 - "test_evaluate.py"
Cohesion: 0.12
Nodes (27): brier_score(), log_loss(), power_analysis(), DataFrame, ndarray, Model evaluation (blueprint Part B.5). "This section is where you prove you are…, mean((p - y)^2). Lower is better., -mean(y*log(p) + (1-y)*log(1-p)). p is clipped away from exactly 0/1 so a… (+19 more)

### Community 3 - "transform.py"
Cohesion: 0.17
Nodes (28): build_team_name_map(), DataFrame, full team name -> abbreviation, restricted to abbrs used in `schedule`., build_schedule_index(), event_to_snapshots(), match_event(), MatchResult, DataFrame (+20 more)

### Community 4 - "test_train.py"
Cohesion: 0.15
Nodes (29): HistGradientBoostingClassifier, Protocol, build_training_frame(), fit_gbm_model(), fit_win_probability_model(), predict_home_win_proba(), _ProbaClassifier, DataFrame (+21 more)

### Community 5 - "test_sizing.py"
Cohesion: 0.09
Nodes (45): find_arbitrage_spots(), find_prop_ev_spots(), pinnacle_fair_probs(), DataFrame, Cross-book player-prop strategies that don't rely on market timing: (1) a…, One row per (event_id, player_name, prop_stat) with both a Pinnacle Over and…, One row per (event, player, prop_stat, line, side, book) where `book`'s price…, One row per (event, player, prop_stat, line) where the best available Over… (+37 more)

### Community 6 - "4. Methodology"
Cohesion: 0.18
Nodes (11): 4.10 Middling: exploiting real line movement over time (2026-08-20), 4.1 Odds conversion, 4.2 Devigging methods, 4.3 Closing Line Value, 4.4 Point-in-time backtesting framework, 4.5 Modeling approach, 4.6 Bet sizing, 4.7 Evaluation framework (+3 more)

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

### Community 35 - "test_middling.py"
Cohesion: 0.13
Nodes (29): middle_ev(), middle_window(), MiddleOpportunity, The overlap of two opposite-side legs' win regions, or None if no real (finite,…, One real, concrete middle: two actual quotes (any book/time) on opposite sides…, Prices a `MiddleOpportunity`'s expected value under a Normal(mu, sigma) model…, (lo, hi) bounds, in "true outcome" space (home_margin for SPREAD, total_score…, win_interval() (+21 more)

### Community 36 - "middling.py"
Cohesion: 0.09
Nodes (34): _best_line(), best_middle_for_game(), find_middle_opportunities(), _interval_prob(), line_threshold(), pinnacle_reference_line(), DataFrame, datetime (+26 more)

### Community 37 - "test_prop_settlement.py"
Cohesion: 0.15
Nodes (25): build_player_stats_index(), normalize_player_name(), DataFrame, Settlement for player-prop (Over/Under) bets against nflverse's per-player game…, Batch-grade prop-shaped rows (event_id/game_id, player_name, prop_stat, side,…, Collapse punctuation/whitespace differences between an odds book's player name…, (game_id, player_display_name) -> {stat_column: value}, from nflreadpy's…, Grade a single Over/Under prop bet. Pushes are real for integer-valued stats… (+17 more)

### Community 38 - "3. Data"
Cohesion: 0.18
Nodes (11): 3.10 Player-prop cross-book strategies (historical, not the live CLV headline), 3.1 Sources, 3.2 Live snapshot collection, 3.3 Known data limitations, 3.4 Bet execution venues, 3.5 Preseason dry run (infrastructure validation, not a result), 3.6 Player props (infrastructure prepped, not active), 3.7 Receiver-level Elo (player-prop pricing infrastructure) (+3 more)

### Community 39 - "test_elo.py"
Cohesion: 0.06
Nodes (71): canonical_team(), compute_team_elo_ratings(), elo_win_probability(), mov_multiplier(), DataFrame, Elo rating system: opponent-adjusted team strength, sequential and leakage-free…, One row per game: each team's Elo rating *entering* that game (pre-game,…, Map a historical/relocated abbreviation to the current one a franchise's rating… (+63 more)

### Community 40 - "NFL CLV Case Study: Blueprint"
Cohesion: 0.06
Nodes (34): A simple, honest first model, B.1 Odds to implied probability, B.2 The vig, and why devigging is the real work, B.3 Closing Line Value, B.4 Bet sizing, B.5 Evaluation and, above all, sample size, Free static data, for backtester and baselines (cost: 0), Live intraday data, self-collected (the thing you cannot buy cheap) (+26 more)

### Community 41 - "preseason.py"
Cohesion: 0.29
Nodes (7): main(), Preseason dry-run collector: same collection mechanics as the real season…, build_context(), Entrypoint: `python -m src.collect.props_run [--once]`. Live player-prop…, load_team_name_map(), Path, Team full-name -> abbreviation resolution. nflreadpy.load_teams() carries…

### Community 42 - "props.py"
Cohesion: 0.16
Nodes (24): event_odds_to_prop_snapshots(), main(), poll_all_props(), poll_event_props(), datetime, ScheduleIndex, Player-prop odds collection. **Prepped, not active.** Live-checked 2026-08-17…, One event's worth of prop snapshots. Raises OddsApiError/RateLimitExceeded to… (+16 more)

### Community 43 - "test_clv_metrics.py"
Cohesion: 0.16
Nodes (20): beat_rate(), bootstrap_ci(), clv_price(), clv_probability(), Closing Line Value metrics (blueprint Part B.3). CLV is measured two ways --…, How far the fair market moved toward your side after you bet. Positive means…, Whether the decimal price you took beats the closing price for the same side.…, Fraction of bets with positive CLV. (+12 more)

### Community 44 - "test_correlated_props.py"
Cohesion: 0.07
Nodes (59): bucket_edge(), bucket_favorite_strength(), build_team_game_outcomes(), correlated_edge(), estimate_game_specific_joint_prob(), is_bucket_validated(), measure_leg_correlation(), measure_leg_correlation_by_bucket() (+51 more)

### Community 45 - "OddsApiClient"
Cohesion: 0.22
Nodes (20): Session, OddsApiClient, RateLimitExceeded, The API rejected the request for quota/auth reasons (401/402/429)., parametrize, _response(), test_get_event_odds_hits_the_per_event_url(), test_get_event_odds_raises_rate_limit_exceeded_like_get_odds() (+12 more)

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

### Community 51 - "OddsApiResponse"
Cohesion: 0.12
Nodes (42): OddsApiResponse, decide_props_poll(), EventPollState, load_state(), PropsCollectorState, PropsPollDecision, datetime, Path (+34 more)

### Community 52 - "market_baseline"
Cohesion: 0.18
Nodes (18): clv_movement_report(), DataFrame, datetime, Preseason CLV-movement report: a dry run of the measurement pipeline…, (home_price_american, away_price_american) from a moneyline slice. None if the…, One row per preseason event with at least two distinct capture times: price and…, _side_prices(), market_baseline() (+10 more)

### Community 53 - "test_load_static.py"
Cohesion: 0.13
Nodes (19): home_spread_line(), load_injuries(), load_pbp(), load_player_stats(), load_players(), load_weekly_rosters(), Path, Pull free static nflverse data (schedules + closing lines) into data/static/.… (+11 more)

### Community 54 - "OddsSnapshot"
Cohesion: 0.13
Nodes (19): BaseModel, Historical player-prop odds backfill for backtesting. **Blocked on paid…, Path, Append-only, point-in-time odds store. This is the leakage guard for the whole…, Append one immutable batch. Never overwrites an existing file., _to_dataframe(), OddsSnapshot, datetime (+11 more)

### Community 55 - "test_game_level_features.py"
Cohesion: 0.11
Nodes (38): current_injury_status(), current_team(), player_status_snapshot(), DataFrame, Current player status: which team a player is on, and their injury/game status,…, One row per player: their most recent roster team/status at or before…, One row per player with an injury-report history: their most recent…, One row per rostered player: current team (trade-aware) + current injury/game… (+30 more)

### Community 56 - "test_validation.py"
Cohesion: 0.08
Nodes (41): benjamini_hochberg(), expanding_season_folds(), _lift(), permutation_test_lift(), DataFrame, ndarray, Series, Portfolio validation: leakage-safe splitting, walk-forward folds, permutation… (+33 more)

### Community 57 - "PointInTimeStore"
Cohesion: 0.18
Nodes (20): LeakageError, PointInTimeStore, DataFrame, datetime, RuntimeError, The only read path. Returns rows visible at `decision_time`, and nothing later., Raised if a query would return (or returned) data from after decision_time., Regression guard: a schema addition (player_name/prop_stat, added for player… (+12 more)

### Community 58 - "calibration.py"
Cohesion: 0.13
Nodes (25): CalibratedClassifierCV, compare_to_baseline(), fit_calibrated_model(), fit_residual_std(), predict_calibrated_proba(), predict_over_proba(), predict_over_proba_empirical(), DataFrame (+17 more)

### Community 59 - "test_live_scan.py"
Cohesion: 0.18
Nodes (22): Live +EV monitor entrypoint: `python -m src.notify.monitor_run`. Meant to be…, AlertRecord, find_positive_ev_spots(), _latest_two_sided_pinnacle(), load_alert_state(), new_or_improved_spots(), DataFrame, datetime (+14 more)

### Community 60 - "test_collect_preseason.py"
Cohesion: 0.27
Nodes (15): build_preseason_match(), poll_once(), One poll: fetch, match, transform, write. Returns counts for logging/testing --…, Build a MatchResult straight from the Odds API event, no nflverse schedule…, Raised when an Odds API event can't be joined to a schedule row., UnmatchedEventError, _preseason_event(), The whole point of keying off Odds API's own event id: entry and close… (+7 more)

### Community 61 - "OddsApiError"
Cohesion: 0.19
Nodes (17): OddsApiError, RuntimeError, Network or unexpected-response failure talking to The Odds API., backfill_historical_props(), find_historical_event_id(), pull_historical_prop_snapshot(), datetime, 1 credit. Looks up the historical events list as of `date` and returns the Odds… (+9 more)

### Community 62 - "demo_pipeline.py"
Cohesion: 0.15
Nodes (20): main(), make_synthetic_snapshots(), datetime, End-to-end pipeline demo: pull -> store -> compare -> decide -> notify. `make…, _step(), _escape_for_applescript(), RuntimeError, SMS/iMessage alerts via macOS Messages.app. No third-party account, no API key:… (+12 more)

### Community 63 - "middle_scan.py"
Cohesion: 0.17
Nodes (18): _fit_residual_stds(), main(), DataFrame, Middle-scan entrypoint: `python -m src.backtest.middle_scan`. A manual, run-by-…, (sigma_margin, sigma_total), reusing the exact fitting pipeline already…, One scan. Returns the report DataFrame (also logged); never sends any…, run(), fit_margin_model() (+10 more)

### Community 64 - "client.py"
Cohesion: 0.15
Nodes (11): Response, _parse_int_header(), _parse_iso(), datetime, Thin HTTP wrapper around The Odds API. Talks to The Odds API directly (not…, Historical per-event odds, snapshotted at the nearest available timestamp <=…, Shared retry/error-handling for both endpoints. Returns the raw successful…, Bulk endpoint: one call returns every event in the sport's current slate. This… (+3 more)

### Community 65 - "test_backtest_engine.py"
Cohesion: 0.37
Nodes (17): BacktestEngine, BetOrder, DecisionPoint, What a strategy sees when it's given a chance to act. `visible_snapshots` is…, A strategy's decision to bet, returned from a Strategy callable. None means "no…, _always_bet_home_spread(), _never_bet(), _schedule() (+9 more)

### Community 66 - "engine.py"
Cohesion: 0.23
Nodes (12): BacktestBet, _latest_fair_prob(), _latest_price(), _parse_kickoffs(), _payout(), DataFrame, datetime, Series (+4 more)

### Community 67 - "test_margin_total.py"
Cohesion: 0.33
Nodes (15): build_margin_total_frame(), `build_training_frame()`'s output plus spread/total regression targets and…, _pbp_fixture(), _plays(), DataFrame, _schedule_fixture(), _synthetic_margin_total_frame(), test_build_margin_total_frame_computes_margin_and_total() (+7 more)

### Community 68 - "american_to_decimal"
Cohesion: 0.27
Nodes (12): model_validator, american_to_decimal(), american_to_implied_prob(), decimal_to_implied_prob(), Odds conversion: American <-> decimal <-> implied probability. Single source of…, parametrize, test_american_to_implied_prob_matches_decimal_round_trip(), test_decimal_to_implied_prob_round_trips_to_one_over_d() (+4 more)

### Community 69 - "ValueError"
Cohesion: 0.27
Nodes (14): build_results_index(), GameResult, Outcome, _outcome_from_margin(), DataFrame, Enum, str, Settlement: grade win/loss/push outcomes against nflverse final scores.… (+6 more)

### Community 70 - "run"
Cohesion: 0.38
Nodes (9): main(), One scan-and-alert cycle. Returns the number of alerts actually sent. Never…, run(), _seed_store(), _snapshot(), test_run_does_not_record_a_spot_whose_send_failed(), test_run_does_not_send_or_record_when_phone_not_configured(), test_run_returns_zero_when_no_spots_found() (+1 more)

## Knowledge Gaps
- **114 isolated node(s):** `nfl-clv`, `graphify`, `Usage`, `What graphify is for`, `Step 0 - GitHub repos and multi-path merge (only if a URL or several paths)` (+109 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PointInTimeStore` connect `PointInTimeStore` to `test_backtest_engine.py`, `engine.py`, `scheduler.py`, `middling.py`, `test_middling.py`, `run`, `preseason.py`, `props.py`, `OddsApiResponse`, `market_baseline`, `OddsSnapshot`, `test_live_scan.py`, `test_collect_preseason.py`, `OddsApiError`, `demo_pipeline.py`, `middle_scan.py`?**
  _High betweenness centrality (0.173) - this node is a cross-community bridge._
- **Why does `Side` connect `Side` to `test_backtest_engine.py`, `engine.py`, `test_middling.py`, `middling.py`, `transform.py`, `test_prop_settlement.py`, `ValueError`, `run`, `props.py`, `market_baseline`, `test_load_static.py`, `OddsSnapshot`, `PointInTimeStore`, `test_live_scan.py`, `demo_pipeline.py`, `middle_scan.py`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Why does `canonical_team()` connect `test_elo.py` to `test_correlated_props.py`, `test_game_level_features.py`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Are the 91 inferred relationships involving `Side` (e.g. with `BacktestBet` and `BetOrder`) actually correct?**
  _`Side` has 91 INFERRED edges - model-reasoned connections that need verification._
- **Are the 79 inferred relationships involving `Market` (e.g. with `BacktestBet` and `BetOrder`) actually correct?**
  _`Market` has 79 INFERRED edges - model-reasoned connections that need verification._
- **Are the 61 inferred relationships involving `PointInTimeStore` (e.g. with `BacktestEngine` and `run()`) actually correct?**
  _`PointInTimeStore` has 61 INFERRED edges - model-reasoned connections that need verification._
- **Are the 26 inferred relationships involving `OddsApiClient` (e.g. with `main()` and `poll_once()`) actually correct?**
  _`OddsApiClient` has 26 INFERRED edges - model-reasoned connections that need verification._