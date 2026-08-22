# Graph Report - nfl_2026  (2026-08-22)

## Corpus Check
- 131 files · ~104,819 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1519 nodes · 4027 edges · 82 communities (75 shown, 7 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 638 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7a5cc9b6`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ValueError
- scheduler.py
- test_evaluate.py
- TransformError
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
- test_prop_settlement.py
- Side
- PointInTimeStore
- 3. Data
- test_elo.py
- NFL CLV Case Study: Blueprint
- OddsApiResponse
- MatchResult
- Methodology backlog
- correlated_props.py
- OddsApiClient
- Beating the Close, Not the Book: A CLV-First Case Study of NFL Betting Markets
- 5. Results
- 1. Introduction
- 6. Discussion
- 2. Background and Related Work
- timedelta
- Market
- test_props_ev_backtest.py
- test_individual_pass_rush_elo.py
- test_game_level_features.py
- test_validation.py
- engine.py
- test_steam.py
- test_pass_rush_elo.py
- test_sizing.py
- test_synthetic_market.py
- test_train.py
- calibration.py
- compute_qb_elo_ratings
- test_team_total_props.py
- middle_scan.py
- test_clv_metrics.py
- compute_receiver_elo_ratings
- test_correlated_props.py
- test_steam_scan.py
- measure_leg_correlation
- correlated_edge
- elo_win_probability
- test_convert.py
- bucket_favorite_strength
- american_to_decimal
- OddsSnapshot
- preseason.py
- build_margin_total_frame
- market_baseline
- _best_line

## God Nodes (most connected - your core abstractions)
1. `Side` - 146 edges
2. `Market` - 128 edges
3. `PointInTimeStore` - 110 edges
4. `OddsSnapshot` - 49 edges
5. `OddsApiClient` - 46 edges
6. `Outcome` - 32 edges
7. `OddsApiResponse` - 31 edges
8. `settle()` - 30 edges
9. `OddsApiError` - 29 edges
10. `MatchResult` - 29 edges

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

## Communities (82 total, 7 thin omitted)

### Community 0 - "ValueError"
Cohesion: 0.11
Nodes (42): home_spread_line(), Convert nflverse's spread_line into the sportsbook side-line convention that…, build_results_index(), GameResult, Outcome, _outcome_from_margin(), DataFrame, Enum (+34 more)

### Community 1 - "scheduler.py"
Cohesion: 0.05
Nodes (82): CollectorState, current_period_end(), decide_poll(), _game_interval_minutes(), load_state(), _minutes_since(), _nearest_upcoming_hours(), parse_quota_headers() (+74 more)

### Community 2 - "test_evaluate.py"
Cohesion: 0.12
Nodes (27): brier_score(), log_loss(), power_analysis(), DataFrame, ndarray, Model evaluation (blueprint Part B.5). "This section is where you prove you are…, mean((p - y)^2). Lower is better., -mean(y*log(p) + (1-y)*log(1-p)). p is clipped away from exactly 0/1 so a… (+19 more)

### Community 3 - "TransformError"
Cohesion: 0.23
Nodes (18): build_preseason_match(), poll_once(), One poll: fetch, match, transform, write. Returns counts for logging/testing --…, Build a MatchResult straight from the Odds API event, no nflverse schedule…, RuntimeError, Raised when an Odds API event can't be joined to a schedule row., Raised when a single event's payload has an unexpected shape., TransformError (+10 more)

### Community 4 - "test_margin_total.py"
Cohesion: 0.20
Nodes (18): fit_residual_std(), predict_over_proba(), predict_over_proba_empirical(), DataFrame, ndarray, Std of (actual - predicted) on `calib_df` -- a regression analogue of…, P(actual > line) under Normal(predicted_mean, residual_std) -- a v1…, Same question as `predict_over_proba` -- P(actual > line) -- but without… (+10 more)

### Community 5 - "props.py"
Cohesion: 0.17
Nodes (21): event_odds_to_prop_snapshots(), main(), poll_all_props(), poll_event_props(), datetime, ScheduleIndex, Player-prop odds collection. **Prepped, not active.** Live-checked 2026-08-17…, One event's worth of prop snapshots. Raises OddsApiError/RateLimitExceeded to… (+13 more)

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

### Community 35 - "test_prop_settlement.py"
Cohesion: 0.15
Nodes (25): build_player_stats_index(), normalize_player_name(), DataFrame, Settlement for player-prop (Over/Under) bets against nflverse's per-player game…, Batch-grade prop-shaped rows (event_id/game_id, player_name, prop_stat, side,…, Collapse punctuation/whitespace differences between an odds book's player name…, (game_id, player_display_name) -> {stat_column: value}, from nflreadpy's…, Grade a single Over/Under prop bet. Pushes are real for integer-valued stats… (+17 more)

### Community 36 - "Side"
Cohesion: 0.09
Nodes (49): find_middle_opportunities(), _interval_prob(), line_threshold(), middle_ev(), middle_window(), MiddleOpportunity, pinnacle_reference_line(), DataFrame (+41 more)

### Community 37 - "PointInTimeStore"
Cohesion: 0.06
Nodes (77): main(), make_synthetic_snapshots(), datetime, End-to-end pipeline demo: pull -> store -> compare -> decide -> notify. `make…, _step(), main(), Live +EV monitor entrypoint: `python -m src.notify.monitor_run`. Meant to be…, One scan-and-alert cycle. Returns the number of alerts actually sent. Never… (+69 more)

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
Cohesion: 0.20
Nodes (19): OddsApiError, OddsApiResponse, RuntimeError, Network or unexpected-response failure talking to The Odds API., backfill_historical_props(), find_historical_event_id(), pull_historical_prop_snapshot(), datetime (+11 more)

### Community 42 - "MatchResult"
Cohesion: 0.17
Nodes (27): build_team_name_map(), DataFrame, full team name -> abbreviation, restricted to abbrs used in `schedule`., build_schedule_index(), event_to_snapshots(), match_event(), MatchResult, DataFrame (+19 more)

### Community 43 - "Methodology backlog"
Cohesion: 0.17
Nodes (11): 1. Rest/travel differential — **tested, negative result**, 2. Joint margin/total correlated distribution — **checked, premise doesn't hold**, 3. Steam detection — **built and live-validated**, 4. Player-prop middling — idea, blocked on live props posting, 5. Referee tendencies — **checked, no signal found (correcting an earlier wrong "blocked" claim)**, 6. Individual pass-rush rating — **built, corrects an earlier wrong "not buildable" claim**, 7. Training-window size — **checked, real effect, first non-Elo comparison to survive BH correction (in the negative direction)**, 8. Mainline historical odds pull — **executed, gap confirmed real but numerically inconsequential** (+3 more)

### Community 44 - "correlated_props.py"
Cohesion: 0.16
Nodes (17): estimate_game_specific_joint_prob(), is_bucket_validated(), price_bucket_bet(), Correlated same-game outcome mispricing: do event pairs from the same game co-…, Game-specific estimate of P(A and B), for pricing one particular upcoming game…, Whether `bucket` (one of `FAVORITE_BUCKETS`' labels) has survived an honest…, Raised by `price_bucket_bet` when asked to price a favorite/ heavy_favorite…, The one real pricing entrypoint any future live correlated-props scanner should… (+9 more)

### Community 45 - "OddsApiClient"
Cohesion: 0.11
Nodes (31): Response, Session, OddsApiClient, _parse_int_header(), _parse_iso(), datetime, RateLimitExceeded, Thin HTTP wrapper around The Odds API. Talks to The Odds API directly (not… (+23 more)

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

### Community 51 - "timedelta"
Cohesion: 0.11
Nodes (46): timedelta, decide_props_poll(), dense_poll_targets_hours(), EventPollState, load_state(), PropsCollectorState, PropsPollDecision, datetime (+38 more)

### Community 52 - "Market"
Cohesion: 0.12
Nodes (28): best_middle_for_game(), The single WIDEST middle window achievable from real quotes for one game, one…, Market, datetime, Enum, Point-in-time odds snapshot schema. One row = one price, for one side, at one…, Build a snapshot from an American price, deriving decimal + implied prob., utcnow() (+20 more)

### Community 53 - "test_props_ev_backtest.py"
Cohesion: 0.19
Nodes (24): find_arbitrage_spots(), find_prop_ev_spots(), pinnacle_fair_probs(), DataFrame, Timedelta, One row per (event, player, prop_stat, line, side, book) where `book`'s price…, One row per (event, player, prop_stat, line, capture_time) where the best…, One row per (event_id, player_name, prop_stat, line) with both a Pinnacle Over… (+16 more)

### Community 54 - "test_individual_pass_rush_elo.py"
Cohesion: 0.21
Nodes (20): build_individual_pass_rush_frame(), compute_individual_pass_rush_ratings(), DataFrame, Individual pass-rush rating: a real, previously-blocked capability. **Corrects…, One row per player-game at a real pass-rush position with at least one…, One row per player-game: this player's individual pass-rush rating *entering*…, _pfr_row(), _player_game() (+12 more)

### Community 55 - "test_game_level_features.py"
Cohesion: 0.11
Nodes (38): current_injury_status(), current_team(), player_status_snapshot(), DataFrame, Current player status: which team a player is on, and their injury/game status,…, One row per player: their most recent roster team/status at or before…, One row per player with an injury-report history: their most recent…, One row per rostered player: current team (trade-aware) + current injury/game… (+30 more)

### Community 56 - "test_validation.py"
Cohesion: 0.07
Nodes (50): benjamini_hochberg(), expanding_season_folds(), _lift(), paired_permutation_test_mean_diff(), permutation_test_lift(), DataFrame, ndarray, Series (+42 more)

### Community 57 - "engine.py"
Cohesion: 0.16
Nodes (29): BacktestBet, BacktestEngine, BetOrder, DecisionPoint, latest_fair_prob(), _latest_price(), _parse_kickoffs(), _payout() (+21 more)

### Community 58 - "test_steam.py"
Cohesion: 0.10
Nodes (41): book_moves(), BookMove, detect_steam_move(), find_steam_opportunities(), _interval_prob(), _largest_time_cluster(), price_stale_book_opportunity(), DataFrame (+33 more)

### Community 59 - "test_pass_rush_elo.py"
Cohesion: 0.22
Nodes (17): compute_pass_rush_elo_ratings(), credited_pressure_counts(), DataFrame, Pass-rush Elo: a play-level, team-level rating of pass-rush vs. pass-protection…, Raw per-player counts of sacks (full credit), half-sacks (0.5 credit), and QB…, One row per dropback: `posteam`'s pass-protection Elo and `defteam`'s pass-rush…, _pbp(), test_clean_pocket_lowers_rush_elo_and_raises_protection_elo() (+9 more)

### Community 60 - "test_sizing.py"
Cohesion: 0.14
Nodes (27): apply_bankroll_caps(), expected_value(), fractional_kelly(), kelly_fraction(), Expected value and Kelly bet sizing (blueprint Part B.4). Full Kelly is too…, EV of a unit bet at fair win probability p and decimal odds d., Full Kelly fraction of bankroll. Can be negative when the price is bad at this…, k * full Kelly. k in [0.25, 0.5] per the blueprint; default 0.375 is the… (+19 more)

### Community 61 - "test_synthetic_market.py"
Cohesion: 0.16
Nodes (25): _logit(), datetime, ndarray, Synthetic market simulator -- validates this project's OWN CLV-measurement code…, Ground truth for one simulated game -- what `simulate_market` actually…, `n_games` synthetic games, each with its own independently-drawn latent price…, One simulated game's latent fair-probability path, length `n_steps + 1` (index…, _sigmoid() (+17 more)

### Community 62 - "test_train.py"
Cohesion: 0.16
Nodes (27): HistGradientBoostingClassifier, Protocol, build_training_frame(), fit_gbm_model(), predict_home_win_proba(), _ProbaClassifier, DataFrame, ndarray (+19 more)

### Community 63 - "calibration.py"
Cohesion: 0.18
Nodes (17): CalibratedClassifierCV, compare_to_baseline(), fit_calibrated_model(), predict_calibrated_proba(), Pipeline, Series, Calibration layer (blueprint Part E): Platt scaling / isotonic regression on…, `method`: "isotonic" (non-parametric, flexible, can overfit a small calibration… (+9 more)

### Community 64 - "compute_qb_elo_ratings"
Cohesion: 0.33
Nodes (10): compute_qb_elo_ratings(), DataFrame, QB-level Elo: a residual rating crediting individual quarterback performance…, One row per game: each starting QB's Elo rating *entering* that game (pre-game,…, _schedule(), test_backup_qb_starts_are_tracked_as_a_distinct_rating_from_the_starter(), test_first_start_for_every_qb_begins_at_initial_rating(), test_qb_rating_carries_across_games_not_reset() (+2 more)

### Community 65 - "test_team_total_props.py"
Cohesion: 0.20
Nodes (20): build_team_total_lines(), fit_team_total_residual_std(), DataFrame, Series, Team-total rushing/passing yards vs. moneyline correlation…, (mean_residual, residual_std) of `actual_team_total - implied_team_total_line`…, Boolean: did the team's real total clear its own real implied line -- the leg…, One row per (event_id, team) with real Pinnacle data for `prop_stat`:… (+12 more)

### Community 66 - "middle_scan.py"
Cohesion: 0.24
Nodes (13): fit_residual_stds(), main(), DataFrame, Middle-scan entrypoint: `python -m src.backtest.middle_scan`. A manual, run-by-…, (sigma_margin, sigma_total) for LIVE pricing -- not the research evaluation…, One scan. Returns the report DataFrame (also logged); never sends any…, run(), _seed_store_with_real_movement() (+5 more)

### Community 67 - "test_clv_metrics.py"
Cohesion: 0.16
Nodes (20): beat_rate(), bootstrap_ci(), clv_price(), clv_probability(), Closing Line Value metrics (blueprint Part B.3). CLV is measured two ways --…, How far the fair market moved toward your side after you bet. Positive means…, Whether the decimal price you took beats the closing price for the same side.…, Fraction of bets with positive CLV. (+12 more)

### Community 68 - "compute_receiver_elo_ratings"
Cohesion: 0.29
Nodes (13): compute_receiver_elo_ratings(), DataFrame, Receiver-level Elo: a play-level rating for pass-catchers, run against a…, One row per target (pass play with a recorded receiver): the receiver's and the…, _pbp(), test_different_receivers_and_defenses_tracked_independently(), test_failed_target_lowers_receiver_and_raises_defense(), test_first_target_begins_at_initial_rating() (+5 more)

### Community 69 - "test_correlated_props.py"
Cohesion: 0.29
Nodes (16): build_team_game_outcomes(), naive_parlay_price(), Decimal price a same-game parlay would carry if a book priced it by multiplying…, One row per team per game, home and away pooled (2x the game count, each team's…, _player_stats_fixture(), _schedule_fixture(), test_game_over_is_shared_across_both_perspectives(), test_leading_receiver_and_rusher_thresholds() (+8 more)

### Community 70 - "test_steam_scan.py"
Cohesion: 0.28
Nodes (11): main(), DataFrame, Steam-scan entrypoint: `python -m src.backtest.steam_scan`. Manual, run-by-…, One scan. Returns the report DataFrame (also logged); never sends any…, run(), _seed_store_with_real_steam(), _snapshot(), test_run_filters_out_spots_below_min_ev() (+3 more)

### Community 71 - "measure_leg_correlation"
Cohesion: 0.18
Nodes (12): measure_leg_correlation(), measure_leg_correlation_by_bucket(), DataFrame, Series, `measure_leg_correlation`, stratified by favorite strength -- see…, `indicator_a`/`indicator_b`: aligned boolean/0-1 Series, one row per game (or…, test_independent_legs_give_a_lift_near_one(), test_measure_leg_correlation_by_bucket_splits_by_market_prob() (+4 more)

### Community 72 - "correlated_edge"
Cohesion: 0.22
Nodes (10): bucket_edge(), correlated_edge(), Closed-form edge for one `FAVORITE_BUCKETS` bucket, under this module's…, The bettor-relevant number this module exists to produce: if a book prices a…, test_bucket_edge_is_independent_of_market_probability(), test_bucket_edge_matches_correlated_edge_when_unclipped(), test_bucket_edge_uses_measured_prop_vig_by_default(), test_correlated_edge_gives_no_stake_when_legs_are_actually_independent() (+2 more)

### Community 73 - "elo_win_probability"
Cohesion: 0.29
Nodes (7): elo_win_probability(), Standard Elo logistic transform: P(a beats b), with `a` treated as the side…, test_400_point_gap_is_the_classic_10_to_1_elo_property(), test_equal_ratings_no_hfa_is_a_coin_flip(), test_home_field_advantage_shifts_probability_toward_home(), test_base_pressure_offset_recenters_expectation_to_the_measured_base_rate(), test_base_pressure_offset_recenters_expectation_to_the_measured_base_rate()

### Community 74 - "test_convert.py"
Cohesion: 0.20
Nodes (19): american_to_implied_prob(), decimal_to_american(), decimal_to_implied_prob(), implied_prob_to_american(), implied_prob_to_decimal(), Odds conversion: American <-> decimal <-> implied probability. Single source of…, Inverse of `american_to_decimal` -- added 2026-08-22 for…, parametrize (+11 more)

### Community 75 - "bucket_favorite_strength"
Cohesion: 0.50
Nodes (4): bucket_favorite_strength(), Which `FAVORITE_BUCKETS` bucket a team's real market-implied win probability…, test_bucket_favorite_strength_classifies_correctly(), test_bucket_favorite_strength_rejects_out_of_range()

### Community 76 - "american_to_decimal"
Cohesion: 0.20
Nodes (15): model_validator, clv_movement_report(), DataFrame, datetime, Preseason CLV-movement report: a dry run of the measurement pipeline…, (home_price_american, away_price_american) from a moneyline slice. None if the…, One row per preseason event with at least two distinct capture times: price and…, _side_prices() (+7 more)

### Community 77 - "OddsSnapshot"
Cohesion: 0.20
Nodes (12): BaseModel, backfill_historical_mainline(), pull_historical_mainline_snapshot(), datetime, Historical mainline (h2h/spreads/totals) odds backfill. **The rigor fix from…, One historical mainline snapshot (nearest available <= `date`) for one event --…, `games`: iterable of (match, home_name, away_name, kickoff) -- same shape as…, Append-only, point-in-time odds store. This is the leakage guard for the whole… (+4 more)

### Community 78 - "preseason.py"
Cohesion: 0.23
Nodes (10): main(), Preseason dry-run collector: same collection mechanics as the real season…, build_context(), main(), Entrypoint: `python -m src.collect.props_run [--once]`. Live player-prop…, build_scheduler(), BlockingScheduler, load_team_name_map() (+2 more)

### Community 79 - "build_margin_total_frame"
Cohesion: 0.35
Nodes (12): build_margin_total_frame(), `build_training_frame()`'s output plus spread/total regression targets and…, _pbp_fixture(), _plays(), DataFrame, _schedule_fixture(), test_build_margin_total_frame_computes_margin_and_total(), test_home_covers_flips_when_home_is_a_big_enough_underdog() (+4 more)

### Community 80 - "market_baseline"
Cohesion: 0.31
Nodes (7): Cross-book player-prop strategies that don't rely on market timing: (1) a…, market_baseline(), Market baseline (blueprint Part E). "Your baseline is the devigged Pinnacle…, Fair probability for the side at `side_index`, from Pinnacle's raw American…, test_default_method_is_shin(), test_side_index_selects_the_right_side(), test_symmetric_market_gives_half_regardless_of_method()

### Community 81 - "_best_line"
Cohesion: 0.67
Nodes (3): _best_line(), Series, The single most favorable real line observed for this side, exploiting…

## Knowledge Gaps
- **125 isolated node(s):** `nfl-clv`, `graphify`, `Usage`, `What graphify is for`, `Step 0 - GitHub repos and multi-path merge (only if a URL or several paths)` (+120 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PointInTimeStore` connect `PointInTimeStore` to `scheduler.py`, `middle_scan.py`, `TransformError`, `Side`, `props.py`, `test_steam_scan.py`, `OddsApiResponse`, `american_to_decimal`, `OddsSnapshot`, `preseason.py`, `timedelta`, `engine.py`, `test_steam.py`?**
  _High betweenness centrality (0.157) - this node is a cross-community bridge._
- **Why does `Side` connect `Side` to `ValueError`, `middle_scan.py`, `test_prop_settlement.py`, `props.py`, `PointInTimeStore`, `test_steam_scan.py`, `MatchResult`, `american_to_decimal`, `_best_line`, `Market`, `engine.py`, `test_steam.py`, `test_synthetic_market.py`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Why does `canonical_team()` connect `test_elo.py` to `compute_qb_elo_ratings`, `test_team_total_props.py`, `compute_receiver_elo_ratings`, `test_correlated_props.py`, `correlated_props.py`, `test_game_level_features.py`, `test_pass_rush_elo.py`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Are the 117 inferred relationships involving `Side` (e.g. with `BacktestBet` and `BetOrder`) actually correct?**
  _`Side` has 117 INFERRED edges - model-reasoned connections that need verification._
- **Are the 101 inferred relationships involving `Market` (e.g. with `BacktestBet` and `BetOrder`) actually correct?**
  _`Market` has 101 INFERRED edges - model-reasoned connections that need verification._
- **Are the 72 inferred relationships involving `PointInTimeStore` (e.g. with `BacktestEngine` and `run()`) actually correct?**
  _`PointInTimeStore` has 72 INFERRED edges - model-reasoned connections that need verification._
- **Are the 80 inferred relationships involving `timedelta` (e.g. with `current_period_end()` and `backfill_historical_mainline()`) actually correct?**
  _`timedelta` has 80 INFERRED edges - model-reasoned connections that need verification._