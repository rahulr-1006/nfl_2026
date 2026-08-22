# Graph Report - nfl_2026  (2026-08-21)

## Corpus Check
- 126 files · ~98,516 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1441 nodes · 3733 edges · 75 communities (68 shown, 7 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 533 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e2fbe52f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Side
- scheduler.py
- test_evaluate.py
- preseason.py
- market_baseline
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
- Outcome
- test_middling.py
- test_props_ev_backtest.py
- 3. Data
- test_elo.py
- NFL CLV Case Study: Blueprint
- OddsApiResponse
- transform.py
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
- engine.py
- test_individual_pass_rush_elo.py
- test_game_level_features.py
- test_validation.py
- load_static.py
- test_steam.py
- test_pass_rush_elo.py
- test_live_scan.py
- test_middle_scan.py
- OddsSnapshot
- american_to_decimal
- middle_scan.py
- schema.py
- PointInTimeStore
- ValueError
- compute_receiver_elo_ratings
- test_preseason_report.py
- test_steam_scan.py
- pit_store.py
- win_interval
- elo_win_probability
- .read_as_of

## God Nodes (most connected - your core abstractions)
1. `Side` - 140 edges
2. `Market` - 122 edges
3. `PointInTimeStore` - 108 edges
4. `OddsApiClient` - 43 edges
5. `OddsSnapshot` - 43 edges
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
- `test_backfill_historical_props_records_api_failures_without_raising()` --uses--> `OddsApiError`  [INFERRED]
  tests/test_collect_props_historical.py → src/collect/client.py

## Import Cycles
- None detected.

## Communities (75 total, 7 thin omitted)

### Community 0 - "Side"
Cohesion: 0.18
Nodes (33): middle_window(), The overlap of two opposite-side legs' win regions, or None if no real (finite,…, _resolve_side_and_line(), Market, str, Side, Batch-grade snapshot-shaped rows (event_id, market, side, line columns) against…, Grade a single (market, side, line) bet against a final score. (+25 more)

### Community 1 - "scheduler.py"
Cohesion: 0.07
Nodes (66): CollectorState, current_period_end(), decide_poll(), _game_interval_minutes(), load_state(), _minutes_since(), _nearest_upcoming_hours(), parse_quota_headers() (+58 more)

### Community 2 - "test_evaluate.py"
Cohesion: 0.12
Nodes (27): brier_score(), log_loss(), power_analysis(), DataFrame, ndarray, Model evaluation (blueprint Part B.5). "This section is where you prove you are…, mean((p - y)^2). Lower is better., -mean(y*log(p) + (1-y)*log(1-p)). p is clipped away from exactly 0/1 so a… (+19 more)

### Community 3 - "preseason.py"
Cohesion: 0.21
Nodes (17): build_preseason_match(), main(), poll_once(), Preseason dry-run collector: same collection mechanics as the real season…, One poll: fetch, match, transform, write. Returns counts for logging/testing --…, Build a MatchResult straight from the Odds API event, no nflverse schedule…, load_team_name_map(), Path (+9 more)

### Community 4 - "market_baseline"
Cohesion: 0.06
Nodes (80): CalibratedClassifierCV, HistGradientBoostingClassifier, Protocol, market_baseline(), Market baseline (blueprint Part E). "Your baseline is the devigged Pinnacle…, Fair probability for the side at `side_index`, from Pinnacle's raw American…, compare_to_baseline(), fit_calibrated_model() (+72 more)

### Community 5 - "props.py"
Cohesion: 0.14
Nodes (27): OddsApiError, RuntimeError, Network or unexpected-response failure talking to The Odds API., event_odds_to_prop_snapshots(), main(), poll_all_props(), poll_event_props(), datetime (+19 more)

### Community 6 - "4. Methodology"
Cohesion: 0.17
Nodes (12): 4.10 Middling: exploiting real line movement over time (2026-08-20), 4.11 Steam detection: synchronized cross-book movement (2026-08-21), 4.1 Odds conversion, 4.2 Devigging methods, 4.3 Closing Line Value, 4.4 Point-in-time backtesting framework, 4.5 Modeling approach, 4.6 Bet sizing (+4 more)

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

### Community 35 - "Outcome"
Cohesion: 0.15
Nodes (27): build_player_stats_index(), normalize_player_name(), DataFrame, Settlement for player-prop (Over/Under) bets against nflverse's per-player game…, Batch-grade prop-shaped rows (event_id/game_id, player_name, prop_stat, side,…, Collapse punctuation/whitespace differences between an odds book's player name…, (game_id, player_display_name) -> {stat_column: value}, from nflreadpy's…, Grade a single Over/Under prop bet. Pushes are real for integer-valued stats… (+19 more)

### Community 36 - "test_middling.py"
Cohesion: 0.09
Nodes (43): best_middle_for_game(), find_middle_opportunities(), _interval_prob(), line_threshold(), middle_ev(), MiddleOpportunity, pinnacle_reference_line(), DataFrame (+35 more)

### Community 37 - "test_props_ev_backtest.py"
Cohesion: 0.08
Nodes (52): find_arbitrage_spots(), find_prop_ev_spots(), pinnacle_fair_probs(), DataFrame, Timedelta, Cross-book player-prop strategies that don't rely on market timing: (1) a…, One row per (event, player, prop_stat, line, side, book) where `book`'s price…, One row per (event, player, prop_stat, line, capture_time) where the best… (+44 more)

### Community 38 - "3. Data"
Cohesion: 0.18
Nodes (11): 3.10 Player-prop cross-book strategies (historical, not the live CLV headline), 3.1 Sources, 3.2 Live snapshot collection, 3.3 Known data limitations, 3.4 Bet execution venues, 3.5 Preseason dry run (infrastructure validation, not a result), 3.6 Player props (infrastructure prepped, not active), 3.7 Receiver-level Elo (player-prop pricing infrastructure) (+3 more)

### Community 39 - "test_elo.py"
Cohesion: 0.15
Nodes (25): canonical_team(), compute_team_elo_ratings(), mov_multiplier(), DataFrame, Elo rating system: opponent-adjusted team strength, sequential and leakage-free…, One row per game: each team's Elo rating *entering* that game (pre-game,…, Map a historical/relocated abbreviation to the current one a franchise's rating…, FiveThirtyEight's margin-of-victory multiplier: ln(|margin| + 1) * (2.2 /… (+17 more)

### Community 40 - "NFL CLV Case Study: Blueprint"
Cohesion: 0.06
Nodes (34): A simple, honest first model, B.1 Odds to implied probability, B.2 The vig, and why devigging is the real work, B.3 Closing Line Value, B.4 Bet sizing, B.5 Evaluation and, above all, sample size, Free static data, for backtester and baselines (cost: 0), Live intraday data, self-collected (the thing you cannot buy cheap) (+26 more)

### Community 41 - "OddsApiResponse"
Cohesion: 0.24
Nodes (16): OddsApiResponse, backfill_historical_props(), find_historical_event_id(), pull_historical_prop_snapshot(), datetime, Historical player-prop odds backfill for backtesting. **Blocked on paid…, 1 credit. Looks up the historical events list as of `date` and returns the Odds…, One historical snapshot (nearest available <= `date`) for one or more markets… (+8 more)

### Community 42 - "transform.py"
Cohesion: 0.15
Nodes (30): build_team_name_map(), DataFrame, Team full-name -> abbreviation resolution. nflreadpy.load_teams() carries…, full team name -> abbreviation, restricted to abbrs used in `schedule`., build_schedule_index(), event_to_snapshots(), match_event(), MatchResult (+22 more)

### Community 43 - "Methodology backlog"
Cohesion: 0.20
Nodes (9): 1. Rest/travel differential — **tested, negative result**, 2. Joint margin/total correlated distribution — **checked, premise doesn't hold**, 3. Steam detection — **built and live-validated**, 4. Player-prop middling — idea, blocked on live props posting, 5. Referee tendencies — **checked, no signal found (correcting an earlier wrong "blocked" claim)**, 6. Individual pass-rush rating — **built, corrects an earlier wrong "not buildable" claim**, 7. Training-window size — **checked, real effect, first non-Elo comparison to survive BH correction (in the negative direction)**, Blocked on data, not on ideas (+1 more)

### Community 44 - "test_correlated_props.py"
Cohesion: 0.07
Nodes (58): bucket_edge(), bucket_favorite_strength(), build_team_game_outcomes(), correlated_edge(), estimate_game_specific_joint_prob(), is_bucket_validated(), measure_leg_correlation(), measure_leg_correlation_by_bucket() (+50 more)

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

### Community 51 - "test_props_scheduler.py"
Cohesion: 0.13
Nodes (36): decide_props_poll(), EventPollState, load_state(), PropsCollectorState, PropsPollDecision, datetime, Path, Budget-aware polling cadence for player props -- a different scheduling problem… (+28 more)

### Community 52 - "client.py"
Cohesion: 0.15
Nodes (11): Response, _parse_int_header(), _parse_iso(), datetime, Thin HTTP wrapper around The Odds API. Talks to The Odds API directly (not…, Historical per-event odds, snapshotted at the nearest available timestamp <=…, Shared retry/error-handling for both endpoints. Returns the raw successful…, Bulk endpoint: one call returns every event in the sport's current slate. This… (+3 more)

### Community 53 - "engine.py"
Cohesion: 0.09
Nodes (49): BacktestBet, BacktestEngine, BetOrder, DecisionPoint, _latest_fair_prob(), _latest_price(), _parse_kickoffs(), _payout() (+41 more)

### Community 54 - "test_individual_pass_rush_elo.py"
Cohesion: 0.21
Nodes (20): build_individual_pass_rush_frame(), compute_individual_pass_rush_ratings(), DataFrame, Individual pass-rush rating: a real, previously-blocked capability. **Corrects…, One row per player-game at a real pass-rush position with at least one…, One row per player-game: this player's individual pass-rush rating *entering*…, _pfr_row(), _player_game() (+12 more)

### Community 55 - "test_game_level_features.py"
Cohesion: 0.11
Nodes (38): current_injury_status(), current_team(), player_status_snapshot(), DataFrame, Current player status: which team a player is on, and their injury/game status,…, One row per player: their most recent roster team/status at or before…, One row per player with an injury-report history: their most recent…, One row per rostered player: current team (trade-aware) + current injury/game… (+30 more)

### Community 56 - "test_validation.py"
Cohesion: 0.07
Nodes (51): benjamini_hochberg(), expanding_season_folds(), _lift(), paired_permutation_test_mean_diff(), permutation_test_lift(), DataFrame, ndarray, Series (+43 more)

### Community 57 - "load_static.py"
Cohesion: 0.11
Nodes (23): home_spread_line(), load_injuries(), load_pbp(), load_pfr_pass_rush_advstats(), load_player_stats(), load_players(), load_snap_counts(), load_weekly_rosters() (+15 more)

### Community 58 - "test_steam.py"
Cohesion: 0.10
Nodes (41): book_moves(), BookMove, detect_steam_move(), find_steam_opportunities(), _interval_prob(), _largest_time_cluster(), price_stale_book_opportunity(), DataFrame (+33 more)

### Community 59 - "test_pass_rush_elo.py"
Cohesion: 0.22
Nodes (17): compute_pass_rush_elo_ratings(), credited_pressure_counts(), DataFrame, Pass-rush Elo: a play-level, team-level rating of pass-rush vs. pass-protection…, Raw per-player counts of sacks (full credit), half-sacks (0.5 credit), and QB…, One row per dropback: `posteam`'s pass-protection Elo and `defteam`'s pass-rush…, _pbp(), test_clean_pocket_lowers_rush_elo_and_raises_protection_elo() (+9 more)

### Community 60 - "test_live_scan.py"
Cohesion: 0.08
Nodes (55): main(), make_synthetic_snapshots(), datetime, End-to-end pipeline demo: pull -> store -> compare -> decide -> notify. `make…, _step(), main(), Live +EV monitor entrypoint: `python -m src.notify.monitor_run`. Meant to be…, One scan-and-alert cycle. Returns the number of alerts actually sent. Never… (+47 more)

### Community 61 - "test_middle_scan.py"
Cohesion: 0.33
Nodes (10): main(), DataFrame, One scan. Returns the report DataFrame (also logged); never sends any…, run(), _seed_store_with_real_movement(), _snapshot(), test_run_filters_out_windows_below_min_ev(), test_run_finds_and_logs_a_real_middle() (+2 more)

### Community 62 - "OddsSnapshot"
Cohesion: 0.18
Nodes (14): BaseModel, Path, Append one immutable batch. Never overwrites an existing file., _to_dataframe(), OddsSnapshot, Build a snapshot from an American price, deriving decimal + implied prob., A single immutable price observation. `capture_time` is when we observed the…, _snap() (+6 more)

### Community 63 - "american_to_decimal"
Cohesion: 0.27
Nodes (12): model_validator, american_to_decimal(), american_to_implied_prob(), decimal_to_implied_prob(), Odds conversion: American <-> decimal <-> implied probability. Single source of…, parametrize, test_american_to_implied_prob_matches_decimal_round_trip(), test_decimal_to_implied_prob_round_trips_to_one_over_d() (+4 more)

### Community 64 - "middle_scan.py"
Cohesion: 0.23
Nodes (13): fit_residual_stds(), Middle-scan entrypoint: `python -m src.backtest.middle_scan`. A manual, run-by-…, (sigma_margin, sigma_total) for LIVE pricing -- not the research evaluation…, compute_qb_elo_ratings(), DataFrame, QB-level Elo: a residual rating crediting individual quarterback performance…, One row per game: each starting QB's Elo rating *entering* that game (pre-game,…, _schedule() (+5 more)

### Community 65 - "schema.py"
Cohesion: 0.50
Nodes (4): datetime, Enum, Point-in-time odds snapshot schema. One row = one price, for one side, at one…, utcnow()

### Community 66 - "PointInTimeStore"
Cohesion: 0.23
Nodes (18): LeakageError, PointInTimeStore, RuntimeError, Raised if a query would return (or returned) data from after decision_time., Regression guard: if `_filter` is ever changed to stop filtering, read_as_of…, Regression guard: a schema addition (player_name/prop_stat, added for player…, _snap(), test_decision_time_must_be_tz_aware() (+10 more)

### Community 67 - "ValueError"
Cohesion: 0.20
Nodes (15): _best_line(), Series, The single most favorable real line observed for this side, exploiting…, build_results_index(), GameResult, _outcome_from_margin(), DataFrame, Enum (+7 more)

### Community 68 - "compute_receiver_elo_ratings"
Cohesion: 0.29
Nodes (13): compute_receiver_elo_ratings(), DataFrame, Receiver-level Elo: a play-level rating for pass-catchers, run against a…, One row per target (pass play with a recorded receiver): the receiver's and the…, _pbp(), test_different_receivers_and_defenses_tracked_independently(), test_failed_target_lowers_receiver_and_raises_defense(), test_first_target_begins_at_initial_rating() (+5 more)

### Community 69 - "test_preseason_report.py"
Cohesion: 0.26
Nodes (12): clv_movement_report(), DataFrame, datetime, Preseason CLV-movement report: a dry run of the measurement pipeline…, (home_price_american, away_price_american) from a moneyline slice. None if the…, One row per preseason event with at least two distinct capture times: price and…, _side_prices(), _moneyline_snapshot() (+4 more)

### Community 70 - "test_steam_scan.py"
Cohesion: 0.28
Nodes (11): main(), DataFrame, Steam-scan entrypoint: `python -m src.backtest.steam_scan`. Manual, run-by-…, One scan. Returns the report DataFrame (also logged); never sends any…, run(), _seed_store_with_real_steam(), _snapshot(), test_run_filters_out_spots_below_min_ev() (+3 more)

### Community 71 - "pit_store.py"
Cohesion: 0.31
Nodes (8): build_context(), main(), Entrypoint: `python -m src.collect.props_run [--once]`. Live player-prop…, build_scheduler(), PropsCollectorContext, BlockingScheduler, Scheduler wiring for player-prop polling -- one `tick()` per opportunity,…, Append-only, point-in-time odds store. This is the leakage guard for the whole…

### Community 72 - "win_interval"
Cohesion: 0.31
Nodes (9): (lo, hi) bounds, in "true outcome" space (home_margin for SPREAD, total_score…, win_interval(), parametrize, test_win_interval_home_matches_settle_on_real_scores(), test_win_interval_is_monotonic_in_line(), test_win_interval_rejects_mismatched_side_for_market(), test_win_interval_rejects_unsupported_markets(), test_win_interval_spread_matches_settle_across_a_full_margin_grid() (+1 more)

### Community 73 - "elo_win_probability"
Cohesion: 0.29
Nodes (7): elo_win_probability(), Standard Elo logistic transform: P(a beats b), with `a` treated as the side…, test_400_point_gap_is_the_classic_10_to_1_elo_property(), test_equal_ratings_no_hfa_is_a_coin_flip(), test_home_field_advantage_shifts_probability_toward_home(), test_base_pressure_offset_recenters_expectation_to_the_measured_base_rate(), test_base_pressure_offset_recenters_expectation_to_the_measured_base_rate()

### Community 74 - ".read_as_of"
Cohesion: 0.53
Nodes (3): DataFrame, datetime, The only read path. Returns rows visible at `decision_time`, and nothing later.

## Knowledge Gaps
- **123 isolated node(s):** `nfl-clv`, `graphify`, `Usage`, `What graphify is for`, `Step 0 - GitHub repos and multi-path merge (only if a URL or several paths)` (+118 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PointInTimeStore` connect `PointInTimeStore` to `middle_scan.py`, `scheduler.py`, `preseason.py`, `test_middling.py`, `test_preseason_report.py`, `test_steam_scan.py`, `props.py`, `pit_store.py`, `OddsApiResponse`, `.read_as_of`, `test_props_scheduler.py`, `engine.py`, `test_steam.py`, `test_live_scan.py`, `test_middle_scan.py`, `OddsSnapshot`?**
  _High betweenness centrality (0.162) - this node is a cross-community bridge._
- **Why does `Side` connect `Side` to `schema.py`, `PointInTimeStore`, `ValueError`, `test_middling.py`, `props.py`, `Outcome`, `test_preseason_report.py`, `win_interval`, `test_steam_scan.py`, `transform.py`, `engine.py`, `load_static.py`, `test_steam.py`, `test_live_scan.py`, `test_middle_scan.py`, `OddsSnapshot`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Why does `market_baseline()` connect `market_baseline` to `test_preseason_report.py`, `test_props_ev_backtest.py`, `test_live_scan.py`, `american_to_decimal`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Are the 113 inferred relationships involving `Side` (e.g. with `BacktestBet` and `BetOrder`) actually correct?**
  _`Side` has 113 INFERRED edges - model-reasoned connections that need verification._
- **Are the 97 inferred relationships involving `Market` (e.g. with `BacktestBet` and `BetOrder`) actually correct?**
  _`Market` has 97 INFERRED edges - model-reasoned connections that need verification._
- **Are the 71 inferred relationships involving `PointInTimeStore` (e.g. with `BacktestEngine` and `run()`) actually correct?**
  _`PointInTimeStore` has 71 INFERRED edges - model-reasoned connections that need verification._
- **Are the 26 inferred relationships involving `OddsApiClient` (e.g. with `main()` and `poll_once()`) actually correct?**
  _`OddsApiClient` has 26 INFERRED edges - model-reasoned connections that need verification._