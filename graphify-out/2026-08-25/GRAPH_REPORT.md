# Graph Report - nfl_2026  (2026-08-23)

## Corpus Check
- 159 files · ~150,580 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2263 nodes · 5746 edges · 104 communities (93 shown, 11 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 712 edges (avg confidence: 0.53)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `90bff577`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Side
- test_bet_log.py
- test_evaluate.py
- test_collect_preseason.py
- test_closing_line.py
- OddsSnapshot
- 4. Methodology
- Parking lot
- test_devig.py
- add_rest_travel_features
- test_props_scan.py
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
- Market
- test_synthetic_market.py
- 3. Data
- test_elo.py
- NFL CLV Case Study: Blueprint
- evaluation.py
- test_collect_budget.py
- Methodology backlog
- test_correlated_props.py
- test_collect_scheduler.py
- Beating the Close, Not the Book: A CLV-First Case Study of NFL Betting Markets
- 5. Results
- 1. Introduction
- 6. Discussion
- 2. Background and Related Work
- test_prop_projection.py
- Open items, in the order they should be picked up
- test_drift_monitor.py
- test_individual_pass_rush_elo.py
- test_game_level_features.py
- test_validation.py
- season_review.py
- test_steam.py
- test_pass_rush_elo.py
- mainline_historical.py
- OddsApiClient
- .from_american
- test_clv_metrics.py
- expected_value
- test_team_total_props.py
- schema.py
- test_clv_portfolio.py
- compute_receiver_elo_ratings
- Architecture & Status Audit
- test_health_check.py
- calibration.py
- test_engine_props.py
- test_train.py
- middle_scan.py
- test_convert.py
- review_strategy
- transform.py
- test_props_budget.py
- fit_margin_model
- test_evaluation.py
- test_team_total_scan.py
- team_total_scan.py
- scheduler.py
- PointInTimeStore
- pit_store.py
- compare_to_book
- test_margin_total.py
- test_steam_scan.py
- elo_win_probability
- test_load_static.py
- test_live_scan.py
- .read_as_of
- market_baseline
- train.py
- compute_qb_elo_ratings
- test_schema.py
- rolling_clv_2024.py
- _best_line
- Pipeline
- audit_integration.py
- BaseModel
- model_validator
- RuntimeError

## God Nodes (most connected - your core abstractions)
1. `PointInTimeStore` - 209 edges
2. `Side` - 161 edges
3. `Market` - 137 edges
4. `OddsSnapshot` - 44 edges
5. `OddsApiClient` - 43 edges
6. `Outcome` - 36 edges
7. `OddsApiResponse` - 35 edges
8. `settle()` - 30 edges
9. `run()` - 29 edges
10. `BacktestEngine` - 28 edges

## Surprising Connections (you probably didn't know these)
- `main()` --uses--> `PointInTimeStore`  [INFERRED]
  scripts/rolling_clv_2024.py → src/store/pit_store.py
- `test_mainline_order_rejects_player_fields()` --uses--> `BetOrder`  [INFERRED]
  tests/test_engine_props.py → src/backtest/engine.py
- `test_prop_order_requires_player_fields()` --uses--> `BetOrder`  [INFERRED]
  tests/test_engine_props.py → src/backtest/engine.py
- `test_leakage_guard_fires_if_filter_is_ever_broken()` --uses--> `LeakageError`  [INFERRED]
  tests/test_pit_store.py → src/store/pit_store.py
- `test_future_snapshot_never_visible_to_strategy_or_used_as_close()` --uses--> `PointInTimeStore`  [INFERRED]
  tests/test_backtest_engine.py → src/store/pit_store.py

## Import Cycles
- None detected.

## Communities (104 total, 11 thin omitted)

### Community 0 - "Side"
Cohesion: 0.15
Nodes (38): Side, build_results_index(), GameResult, Outcome, _outcome_from_margin(), DataFrame, Enum, str (+30 more)

### Community 1 - "test_bet_log.py"
Cohesion: 0.06
Nodes (72): BaseModel, field_validator, model_validator, payout_for(), Outcome, Profit (not total return) for a graded bet. Public because live bets in…, active_bets(), _close_price_decimal() (+64 more)

### Community 2 - "test_evaluate.py"
Cohesion: 0.12
Nodes (27): brier_score(), log_loss(), power_analysis(), DataFrame, ndarray, Model evaluation (blueprint Part B.5). "This section is where you prove you are…, mean((p - y)^2). Lower is better., -mean(y*log(p) + (1-y)*log(1-p)). p is clipped away from exactly 0/1 so a… (+19 more)

### Community 3 - "test_collect_preseason.py"
Cohesion: 0.27
Nodes (15): build_preseason_match(), poll_once(), One poll: fetch, match, transform, write. Returns counts for logging/testing --…, Build a MatchResult straight from the Odds API event, no nflverse schedule…, Raised when an Odds API event can't be joined to a schedule row., UnmatchedEventError, _preseason_event(), The whole point of keying off Odds API's own event id: entry and close… (+7 more)

### Community 4 - "test_closing_line.py"
Cohesion: 0.12
Nodes (36): Pipeline, build_closing_line_frame(), closing_fair_probabilities(), evaluate_closing_line_model(), fit_closing_line_model(), predict_closing_prob(), DataFrame, ndarray (+28 more)

### Community 5 - "OddsSnapshot"
Cohesion: 0.12
Nodes (32): event_odds_to_prop_snapshots(), main(), poll_all_props(), poll_event_props(), datetime, ScheduleIndex, Player-prop odds collection. **Prepped, not active.** Live-checked 2026-08-17…, One event's worth of prop snapshots. Raises OddsApiError/RateLimitExceeded to… (+24 more)

### Community 6 - "4. Methodology"
Cohesion: 0.17
Nodes (12): 4.10 Middling: exploiting real line movement over time (2026-08-20), 4.11 Steam detection: synchronized cross-book movement (2026-08-21), 4.1 Odds conversion, 4.2 Devigging methods, 4.3 Closing Line Value, 4.4 Point-in-time backtesting framework, 4.5 Modeling approach, 4.6 Bet sizing (+4 more)

### Community 8 - "test_devig.py"
Cohesion: 0.09
Nodes (38): compare_methods(), compare_methods_table(), devig_additive(), devig_multiplicative(), devig_power(), devig_shin(), DevigResult, overround() (+30 more)

### Community 9 - "add_rest_travel_features"
Cohesion: 0.06
Nodes (75): add_rest_travel_features(), add_weather_features(), build_game_features(), _is_garbage_time(), DataFrame, Series, Feature builder (blueprint Part E): team-strength proxies from play-by-play.…, One row per game_id: home/away pre-game rolling EPA features plus the schedule… (+67 more)

### Community 10 - "test_props_scan.py"
Cohesion: 0.05
Nodes (80): find_arbitrage_spots(), find_prop_ev_spots(), pinnacle_fair_probs(), DataFrame, Timedelta, Cross-book player-prop strategies that don't rely on market timing: (1) a…, One row per (event, player, prop_stat, line, side, book) where `book`'s price…, One row per (event, player, prop_stat, line, capture_time) where the best… (+72 more)

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
Nodes (27): Dispatch to the right settlement path for this market -- game score for…, _grade(), Outcome, One bet's outcome, or None if it cannot be graded yet. None is returned rather…, build_player_stats_index(), normalize_player_name(), DataFrame, Settlement for player-prop (Over/Under) bets against nflverse's per-player game… (+19 more)

### Community 36 - "Market"
Cohesion: 0.08
Nodes (65): best_middle_for_game(), find_middle_opportunities(), _interval_prob(), line_threshold(), middle_ev(), middle_window(), MiddleOpportunity, pinnacle_reference_line() (+57 more)

### Community 37 - "test_synthetic_market.py"
Cohesion: 0.12
Nodes (32): _logit(), datetime, Market, ndarray, OddsSnapshot, Side, timedelta, Synthetic market simulator -- validates this project's OWN CLV-measurement code… (+24 more)

### Community 38 - "3. Data"
Cohesion: 0.18
Nodes (11): 3.10 Player-prop cross-book strategies (historical, not the live CLV headline), 3.1 Sources, 3.2 Live snapshot collection, 3.3 Known data limitations, 3.4 Bet execution venues, 3.5 Preseason dry run (infrastructure validation, not a result), 3.6 Player props (infrastructure prepped, not active), 3.7 Receiver-level Elo (player-prop pricing infrastructure) (+3 more)

### Community 39 - "test_elo.py"
Cohesion: 0.15
Nodes (25): canonical_team(), compute_team_elo_ratings(), mov_multiplier(), DataFrame, Elo rating system: opponent-adjusted team strength, sequential and leakage-free…, One row per game: each team's Elo rating *entering* that game (pre-game,…, Map a historical/relocated abbreviation to the current one a franchise's rating…, FiveThirtyEight's margin-of-victory multiplier: ln(|margin| + 1) * (2.2 /… (+17 more)

### Community 40 - "NFL CLV Case Study: Blueprint"
Cohesion: 0.06
Nodes (34): A simple, honest first model, B.1 Odds to implied probability, B.2 The vig, and why devigging is the real work, B.3 Closing Line Value, B.4 Bet sizing, B.5 Evaluation and, above all, sample size, Free static data, for backtester and baselines (cost: 0), Live intraday data, self-collected (the thing you cannot buy cheap) (+26 more)

### Community 41 - "evaluation.py"
Cohesion: 0.15
Nodes (16): DataFrame, ndarray, random_bet_benchmark(), Betting-evaluation harness: is an edge *bettable*, not merely calibrated? **Why…, Does `metric` hold up as the threshold tightens? A real edge should not…, The null model: bet the SAME events at the SAME prices, choosing sides at…, Per-unit-staked return: (d-1) on a win, -1 on a loss., _returns() (+8 more)

### Community 42 - "test_collect_budget.py"
Cohesion: 0.13
Nodes (28): current_period_end(), decide_poll(), _game_interval_minutes(), _minutes_since(), _nearest_upcoming_hours(), parse_quota_headers(), PollDecision, date (+20 more)

### Community 43 - "Methodology backlog"
Cohesion: 0.07
Nodes (29): 10. High-vig markets — **checked, hypothesis reframed, anytime-TD confirmed unpriceable**, 1. Rest/travel differential — **tested, negative result**, 2. Joint margin/total correlated distribution — **checked, premise doesn't hold**, 3. Steam detection — **built and live-validated**, 4. Player-prop middling — idea, blocked on live props posting, 5. Referee tendencies — **checked, no signal found (correcting an earlier wrong "blocked" claim)**, 6. Individual pass-rush rating — **built, corrects an earlier wrong "not buildable" claim**, 7. Training-window size — **checked, real effect, first non-Elo comparison to survive BH correction (in the negative direction)** (+21 more)

### Community 44 - "test_correlated_props.py"
Cohesion: 0.05
Nodes (78): bucket_edge(), bucket_favorite_strength(), build_team_game_outcomes(), correlated_edge(), estimate_game_specific_joint_prob(), is_bucket_validated(), measure_leg_correlation(), measure_leg_correlation_by_bucket() (+70 more)

### Community 45 - "test_collect_scheduler.py"
Cohesion: 0.27
Nodes (19): CollectorState, load_state(), Path, Persisted to disk between process restarts (default: data/collect_state.json)., save_state(), Wraps _tick(ctx) so one unexpected bug in a single poll never kills a long-…, tick(), test_state_roundtrip() (+11 more)

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

### Community 51 - "test_prop_projection.py"
Cohesion: 0.13
Nodes (31): build_prop_training_frame(), fit_prop_model(), predict_over_probability(), prior_form(), DataFrame, ndarray, Pipeline, Project a player's stat against the book's posted prop line. **The formulation… (+23 more)

### Community 52 - "Open items, in the order they should be picked up"
Cohesion: 0.13
Nodes (14): 1. ~~Orphaned modules~~ RESOLVED 2026-08-23, 2. ~~Stale data files~~ DELETED 2026-08-23, 3. ~~`market_write_freshness` -> alert~~ DONE 2026-08-23, 4. ~~Full concurrent dry run~~ DONE 2026-08-23, 5. ~~Settle logged bets~~ DONE 2026-08-23, 6. Retire the preseason modules after 9/9, 7. Cosmetic / housekeeping — mostly DONE 2026-08-23, 8. Code review — 13 findings, all fixed 2026-08-23 (+6 more)

### Community 53 - "test_drift_monitor.py"
Cohesion: 0.15
Nodes (21): _detect_decay(), ndarray, Has CLV shifted *downward* from this strategy's OWN established baseline? Two…, cusum(), first_flag_index(), ndarray, Non-stationarity / drift monitor (blueprint Part E, "the genuinely hard part").…, Index of the first True in `flagged`, or None if it never fires. (+13 more)

### Community 54 - "test_individual_pass_rush_elo.py"
Cohesion: 0.21
Nodes (20): build_individual_pass_rush_frame(), compute_individual_pass_rush_ratings(), DataFrame, Individual pass-rush rating: a real, previously-blocked capability. **Corrects…, One row per player-game at a real pass-rush position with at least one…, One row per player-game: this player's individual pass-rush rating *entering*…, _pfr_row(), _player_game() (+12 more)

### Community 55 - "test_game_level_features.py"
Cohesion: 0.11
Nodes (38): current_injury_status(), current_team(), player_status_snapshot(), DataFrame, Current player status: which team a player is on, and their injury/game status,…, One row per player: their most recent roster team/status at or before…, One row per player with an injury-report history: their most recent…, One row per rostered player: current team (trade-aware) + current injury/game… (+30 more)

### Community 56 - "test_validation.py"
Cohesion: 0.07
Nodes (50): benjamini_hochberg(), expanding_season_folds(), _lift(), paired_permutation_test_mean_diff(), permutation_test_lift(), DataFrame, ndarray, Series (+42 more)

### Community 57 - "season_review.py"
Cohesion: 0.14
Nodes (18): _clv_series(), format_review_summary(), main(), DataFrame, In-season strategy review: is each live strategy still working, and when should…, One review row per strategy segment. Segments rather than pools for the same…, Human-readable digest, ordered so anything needing action is first -- this is…, Weekly in-season health check over the LIVE bet log. Segments on `strategy`… (+10 more)

### Community 58 - "test_steam.py"
Cohesion: 0.10
Nodes (41): book_moves(), BookMove, detect_steam_move(), find_steam_opportunities(), _interval_prob(), _largest_time_cluster(), price_stale_book_opportunity(), DataFrame (+33 more)

### Community 59 - "test_pass_rush_elo.py"
Cohesion: 0.22
Nodes (17): compute_pass_rush_elo_ratings(), credited_pressure_counts(), DataFrame, Pass-rush Elo: a play-level, team-level rating of pass-rush vs. pass-protection…, Raw per-player counts of sacks (full credit), half-sacks (0.5 credit), and QB…, One row per dropback: `posteam`'s pass-protection Elo and `defteam`'s pass-rush…, _pbp(), test_clean_pocket_lowers_rush_elo_and_raises_protection_elo() (+9 more)

### Community 60 - "mainline_historical.py"
Cohesion: 0.10
Nodes (34): MatchResult, OddsApiClient, backfill_historical_mainline(), estimate_pull_cost(), _iso_z(), main(), pull_historical_mainline_snapshot(), _pull_with_credits() (+26 more)

### Community 61 - "OddsApiClient"
Cohesion: 0.08
Nodes (50): Response, Session, OddsApiClient, OddsApiError, OddsApiResponse, _parse_int_header(), _parse_iso(), datetime (+42 more)

### Community 62 - ".from_american"
Cohesion: 0.16
Nodes (17): clv_movement_report(), DataFrame, datetime, Preseason CLV-movement report: a dry run of the measurement pipeline…, (home_price_american, away_price_american) from a moneyline slice. None if the…, One row per preseason event with at least two distinct capture times: price and…, _side_prices(), american_to_decimal() (+9 more)

### Community 63 - "test_clv_metrics.py"
Cohesion: 0.16
Nodes (20): beat_rate(), bootstrap_ci(), clv_price(), clv_probability(), Closing Line Value metrics (blueprint Part B.3). CLV is measured two ways --…, How far the fair market moved toward your side after you bet. Positive means…, Whether the decimal price you took beats the closing price for the same side.…, Fraction of bets with positive CLV. (+12 more)

### Community 64 - "expected_value"
Cohesion: 0.07
Nodes (55): parlay_ev(), parlay_independent_probability(), parlay_price_decimal(), parlay_true_probability(), ParlayLeg, Parlay pricing and EV -- multi-leg bets, priced against REAL leg prices. **Why…, Correlation-adjusted joint win probability: the independent product scaled by…, Full EV/sizing for one parlay, reusing `src/signal/sizing.py`'s… (+47 more)

### Community 65 - "test_team_total_props.py"
Cohesion: 0.20
Nodes (20): build_team_total_lines(), fit_team_total_residual_std(), DataFrame, Series, Team-total rushing/passing yards vs. moneyline correlation…, (mean_residual, residual_std) of `actual_team_total - implied_team_total_line`…, Boolean: did the team's real total clear its own real implied line -- the leg…, One row per (event_id, team) with real Pinnacle data for `prop_stat`:… (+12 more)

### Community 66 - "schema.py"
Cohesion: 0.19
Nodes (11): fixture, datetime, Enum, Point-in-time odds snapshot schema. One row = one price, for one side, at one…, utcnow(), isolated_state(), _prop(), The Pinnacle-arrival announcement must fire exactly once, ever. (+3 more)

### Community 67 - "test_clv_portfolio.py"
Cohesion: 0.15
Nodes (29): bankroll_path(), bets_to_frame(), clv_by_segment(), clv_summary(), DataFrame, Portfolio-level CLV reporting: combine every bet the engine produced --…, Pooled CLV summary across every bet given: n, mean CLV, beat rate, and a…, `clv_summary` computed per segment -- one row per distinct value of… (+21 more)

### Community 68 - "compute_receiver_elo_ratings"
Cohesion: 0.29
Nodes (13): compute_receiver_elo_ratings(), DataFrame, Receiver-level Elo: a play-level rating for pass-catchers, run against a…, One row per target (pass play with a recorded receiver): the receiver's and the…, _pbp(), test_different_receivers_and_defenses_tracked_independently(), test_failed_target_lowers_receiver_and_raises_defense(), test_first_target_begins_at_initial_rating() (+5 more)

### Community 69 - "Architecture & Status Audit"
Cohesion: 0.12
Nodes (15): 1. What is actually running right now, 2. Layer map, 3. Module status, 4. Orphan list — delete or wire, 5. Notebooks, 6. Strategy verdicts (`methodology_backlog.md`), 7. Data inventory, 8. Design rule: which strategies work here, and why (+7 more)

### Community 70 - "test_health_check.py"
Cohesion: 0.08
Nodes (60): check_all(), check_collector_health(), check_props_write_freshness(), market_write_freshness(), _now(), pinnacle_arrival_message(), prop_book_coverage(), DataFrame (+52 more)

### Community 71 - "calibration.py"
Cohesion: 0.18
Nodes (17): CalibratedClassifierCV, compare_to_baseline(), fit_calibrated_model(), predict_calibrated_proba(), Pipeline, Series, Calibration layer (blueprint Part E): Platt scaling / isotonic regression on…, `method`: "isotonic" (non-parametric, flexible, can overfit a small calibration… (+9 more)

### Community 72 - "test_engine_props.py"
Cohesion: 0.09
Nodes (58): BacktestEngine, BetOrder, DecisionPoint, latest_fair_prob(), _latest_price(), _market_rows(), _parse_kickoffs(), DataFrame (+50 more)

### Community 73 - "test_train.py"
Cohesion: 0.21
Nodes (22): HistGradientBoostingClassifier, build_training_frame(), fit_gbm_model(), DataFrame, Three-way, out-of-time split: fit the model on `train_seasons`, fit the…, Gradient-boosted trees on `feature_columns` -- blueprint Part E's other…, One row per game: `build_game_features()` output plus the home-win label and…, time_based_split() (+14 more)

### Community 74 - "middle_scan.py"
Cohesion: 0.18
Nodes (17): fit_residual_stds(), main(), DataFrame, Middle-scan entrypoint: `python -m src.backtest.middle_scan`. A manual, run-by-…, (sigma_margin, sigma_total) for LIVE pricing -- not the research evaluation…, One scan. Returns the report DataFrame (also logged); never sends any…, run(), fit_total_model() (+9 more)

### Community 75 - "test_convert.py"
Cohesion: 0.19
Nodes (20): american_to_implied_prob(), decimal_to_american(), decimal_to_implied_prob(), implied_prob_to_american(), implied_prob_to_decimal(), Odds conversion: American <-> decimal <-> implied probability. Single source of…, Inverse of `american_to_decimal` -- added 2026-08-22 for…, parametrize (+12 more)

### Community 76 - "review_strategy"
Cohesion: 0.12
Nodes (30): Full health check on one strategy's live bets. The recommendation is…, review_strategy(), _frame(), CUSUM is sequential -- an unsorted series scrambles the exact pattern it…, `== NaN` is False for every row -- the bug already fixed in clv_portfolio.…, CLV-only review is still valid -- not every recorded bet carries a settled…, Regression: two strategies with IDENTICAL shapes but different levels must get…, With fewer bets than the baseline window there is nothing to compare against;… (+22 more)

### Community 77 - "transform.py"
Cohesion: 0.17
Nodes (28): build_team_name_map(), DataFrame, full team name -> abbreviation, restricted to abbrs used in `schedule`., build_schedule_index(), event_to_snapshots(), match_event(), MatchResult, DataFrame (+20 more)

### Community 78 - "test_props_budget.py"
Cohesion: 0.05
Nodes (77): arb_poll_targets_hours(), build_poll_targets(), decide_props_poll(), dense_poll_targets_hours(), early_poll_targets_hours(), EventPollState, load_state(), PollTarget (+69 more)

### Community 79 - "fit_margin_model"
Cohesion: 0.22
Nodes (14): fit_residual_std(), predict_over_proba(), predict_over_proba_empirical(), DataFrame, ndarray, Std of (actual - predicted) on `calib_df` -- a regression analogue of…, P(actual > line) under Normal(predicted_mean, residual_std) -- a v1…, Same question as `predict_over_proba` -- P(actual > line) -- but without… (+6 more)

### Community 80 - "test_evaluation.py"
Cohesion: 0.12
Nodes (32): evaluate_at_threshold(), evaluate_strategy(), evaluate_threshold_sweep(), Metrics for the subset of `bets` whose edge clears `threshold`. `bets` needs…, The whole curve, one row per threshold -- never just the best cell. Read…, Full report: sweep + monotonicity + random-bet null + a plain verdict.…, _bets(), _coinflip_bets() (+24 more)

### Community 81 - "test_team_total_scan.py"
Cohesion: 0.19
Nodes (23): find_team_total_spots(), Priceable team-total spots on upcoming games. Teams in unvalidated buckets are…, _ml(), _one_sided_prop(), _prop(), A line that has since moved is not what you'd be betting into., Over only -- no complement, so no measurable overround., -110/-110 is 4.76% overround by construction -- not the 6.29% constant. (+15 more)

### Community 82 - "team_total_scan.py"
Cohesion: 0.15
Nodes (20): Drop snapshots for games that have already kicked off -- only a future game is…, upcoming_only(), available_stats(), format_team_total_alert(), main(), measured_vig_by_event(), DataFrame, datetime (+12 more)

### Community 83 - "scheduler.py"
Cohesion: 0.08
Nodes (35): Config, load_config(), Path, Collector configuration. Everything The Odds API's free-tier budget forces us…, Build a Config from environment variables (or an injected mapping for tests).…, build_context(), main(), Entrypoint: `python -m src.collect.run [--once]`. `--once` does a single… (+27 more)

### Community 84 - "PointInTimeStore"
Cohesion: 0.17
Nodes (25): PointInTimeStore, _prop(), Regression guard: if `_filter` is ever changed to stop filtering, read_as_of…, Regression guard: a schema addition (player_name/prop_stat, added for player…, Nothing is mutated -- dedupe is a read-time view, not a deletion., Real case: Khalil Herbert receptions 1.5 at betonlineag carried -119 AND -125…, **Regression guard for a real analysis error (2026-08-23).** One player can…, Dedupe must never flatten a price HISTORY -- that is the whole store. (+17 more)

### Community 85 - "pit_store.py"
Cohesion: 0.19
Nodes (13): main(), Preseason dry-run collector: same collection mechanics as the real season…, build_context(), main(), Entrypoint: `python -m src.collect.props_run [--once]`. Live player-prop…, build_scheduler(), PropsCollectorContext, BlockingScheduler (+5 more)

### Community 86 - "compare_to_book"
Cohesion: 0.40
Nodes (5): compare_to_book(), Forecast-quality comparison: model vs. book on the same events. Necessary but…, These are different questions and the API keeps them apart -- a model can win…, test_beating_the_book_on_brier_is_reported_separately_from_bettability(), test_compare_to_book_reports_both_sides_and_who_wins()

### Community 87 - "test_margin_total.py"
Cohesion: 0.42
Nodes (12): build_margin_total_frame(), `build_training_frame()`'s output plus spread/total regression targets and…, _pbp_fixture(), _plays(), DataFrame, _schedule_fixture(), test_build_margin_total_frame_computes_margin_and_total(), test_home_covers_flips_when_home_is_a_big_enough_underdog() (+4 more)

### Community 88 - "test_steam_scan.py"
Cohesion: 0.28
Nodes (11): main(), DataFrame, Steam-scan entrypoint: `python -m src.backtest.steam_scan`. Manual, run-by-…, One scan. Returns the report DataFrame (also logged); never sends any…, run(), _seed_store_with_real_steam(), _snapshot(), test_run_filters_out_spots_below_min_ev() (+3 more)

### Community 89 - "elo_win_probability"
Cohesion: 0.29
Nodes (7): elo_win_probability(), Standard Elo logistic transform: P(a beats b), with `a` treated as the side…, test_400_point_gap_is_the_classic_10_to_1_elo_property(), test_equal_ratings_no_hfa_is_a_coin_flip(), test_home_field_advantage_shifts_probability_toward_home(), test_base_pressure_offset_recenters_expectation_to_the_measured_base_rate(), test_base_pressure_offset_recenters_expectation_to_the_measured_base_rate()

### Community 90 - "test_load_static.py"
Cohesion: 0.32
Nodes (7): home_spread_line(), Convert nflverse's spread_line into the sportsbook side-line convention that…, Regression guard for the sign-convention bug: feeding nflverse's raw…, Regression guard for the trimmed-schema cache: src/model/features.py depends on…, test_cached_pbp_matches_trimmed_schema_and_covers_the_cached_seasons(), test_home_spread_line_negates(), test_home_spread_line_sign_convention_matches_an_efficient_market()

### Community 91 - "test_live_scan.py"
Cohesion: 0.06
Nodes (75): main(), make_synthetic_snapshots(), datetime, End-to-end pipeline demo: pull -> store -> compare -> decide -> notify. `make…, _step(), _alert_batch(), main(), Series (+67 more)

### Community 92 - ".read_as_of"
Cohesion: 0.17
Nodes (10): RuntimeError, LeakageError, DataFrame, datetime, OddsSnapshot, Path, The only read path. Returns rows visible at `decision_time`, and nothing later.…, Raised if a query would return (or returned) data from after decision_time. (+2 more)

### Community 93 - "market_baseline"
Cohesion: 0.39
Nodes (6): market_baseline(), Market baseline (blueprint Part E). "Your baseline is the devigged Pinnacle…, Fair probability for the side at `side_index`, from Pinnacle's raw American…, test_default_method_is_shin(), test_side_index_selects_the_right_side(), test_symmetric_market_gives_half_regardless_of_method()

### Community 94 - "train.py"
Cohesion: 0.38
Nodes (5): Protocol, predict_home_win_proba(), _ProbaClassifier, ndarray, Model training (blueprint Part E): first outcome model + time-based split.…

### Community 95 - "compute_qb_elo_ratings"
Cohesion: 0.33
Nodes (10): compute_qb_elo_ratings(), DataFrame, QB-level Elo: a residual rating crediting individual quarterback performance…, One row per game: each starting QB's Elo rating *entering* that game (pre-game,…, _schedule(), test_backup_qb_starts_are_tracked_as_a_distinct_rating_from_the_starter(), test_first_start_for_every_qb_begins_at_initial_rating(), test_qb_rating_carries_across_games_not_reset() (+2 more)

### Community 96 - "test_schema.py"
Cohesion: 0.43
Nodes (4): _snap(), test_from_american_derives_decimal_and_prob(), test_frozen_snapshot_cannot_be_mutated(), test_moneyline_rejects_line()

### Community 97 - "rolling_clv_2024.py"
Cohesion: 0.50
Nodes (4): _home_fair(), main(), DataFrame, Does the line actually move toward truth? Real 2024 historical movement. **Two…

### Community 98 - "_best_line"
Cohesion: 0.67
Nodes (3): _best_line(), Series, The single most favorable real line observed for this side, exploiting…

### Community 100 - "audit_integration.py"
Cohesion: 0.20
Nodes (16): check_architecture_md(), classify(), main(), _make_entrypoints(), _module_graph(), _notebook_entrypoints(), Path, Which src/ modules are actually reachable, and from what? **Why this exists.**… (+8 more)

## Knowledge Gaps
- **163 isolated node(s):** `1. What is actually running right now`, `2. Layer map`, `store/ — foundation (all LIVE)`, `collect/ — data acquisition`, `model/ — feature/rating layer (trains ONLY on free nflverse data)` (+158 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PointInTimeStore` connect `PointInTimeStore` to `test_bet_log.py`, `test_collect_preseason.py`, `test_closing_line.py`, `OddsSnapshot`, `test_props_scan.py`, `Market`, `test_collect_scheduler.py`, `season_review.py`, `test_steam.py`, `mainline_historical.py`, `OddsApiClient`, `.from_american`, `schema.py`, `test_health_check.py`, `test_engine_props.py`, `middle_scan.py`, `test_props_budget.py`, `test_team_total_scan.py`, `team_total_scan.py`, `scheduler.py`, `pit_store.py`, `test_steam_scan.py`, `test_live_scan.py`, `.read_as_of`, `rolling_clv_2024.py`?**
  _High betweenness centrality (0.308) - this node is a cross-community bridge._
- **Why does `Side` connect `Side` to `test_bet_log.py`, `test_closing_line.py`, `OddsSnapshot`, `test_props_scan.py`, `test_prop_settlement.py`, `Market`, `test_synthetic_market.py`, `test_steam.py`, `.from_american`, `schema.py`, `test_clv_portfolio.py`, `test_engine_props.py`, `middle_scan.py`, `test_convert.py`, `transform.py`, `PointInTimeStore`, `test_steam_scan.py`, `test_load_static.py`, `test_live_scan.py`, `_best_line`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._
- **Why does `Market` connect `Market` to `Side`, `test_bet_log.py`, `schema.py`, `test_clv_portfolio.py`, `test_closing_line.py`, `OddsSnapshot`, `test_load_static.py`, `test_synthetic_market.py`, `test_engine_props.py`, `middle_scan.py`, `test_props_scan.py`, `transform.py`, `PointInTimeStore`, `test_steam_scan.py`, `test_steam.py`, `test_live_scan.py`, `.from_american`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Are the 155 inferred relationships involving `PointInTimeStore` (e.g. with `main()` and `BacktestEngine`) actually correct?**
  _`PointInTimeStore` has 155 INFERRED edges - model-reasoned connections that need verification._
- **Are the 130 inferred relationships involving `Side` (e.g. with `_best_line()` and `best_middle_for_game()`) actually correct?**
  _`Side` has 130 INFERRED edges - model-reasoned connections that need verification._
- **Are the 108 inferred relationships involving `Market` (e.g. with `best_middle_for_game()` and `find_middle_opportunities()`) actually correct?**
  _`Market` has 108 INFERRED edges - model-reasoned connections that need verification._
- **Are the 50 inferred relationships involving `ValueError` (e.g. with `._grade()` and `._settle_order()`) actually correct?**
  _`ValueError` has 50 INFERRED edges - model-reasoned connections that need verification._