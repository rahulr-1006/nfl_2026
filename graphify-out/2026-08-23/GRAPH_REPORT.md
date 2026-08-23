# Graph Report - nfl_2026  (2026-08-23)

## Corpus Check
- 147 files · ~125,115 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1905 nodes · 4892 edges · 101 communities (91 shown, 10 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 675 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2776ffff`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Market
- scheduler.py
- test_evaluate.py
- test_collect_preseason.py
- test_closing_line.py
- props.py
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
- Outcome
- test_middling.py
- demo_pipeline.py
- 3. Data
- test_elo.py
- NFL CLV Case Study: Blueprint
- test_evaluation.py
- OddsSnapshot
- Methodology backlog
- test_correlated_props.py
- OddsApiClient
- Beating the Close, Not the Book: A CLV-First Case Study of NFL Betting Markets
- 5. Results
- 1. Introduction
- 6. Discussion
- 2. Background and Related Work
- test_prop_projection.py
- Side
- test_synthetic_market.py
- test_individual_pass_rush_elo.py
- test_game_level_features.py
- test_validation.py
- test_clv_metrics.py
- test_steam.py
- test_pass_rush_elo.py
- test_sizing.py
- test_middle_scan.py
- market_baseline
- evaluation.py
- compute_qb_elo_ratings
- test_team_total_props.py
- OddsApiResponse
- test_clv_portfolio.py
- compute_receiver_elo_ratings
- Architecture & Status Audit
- test_collect_budget.py
- load_static.py
- test_engine_props.py
- elo_win_probability
- run
- test_props_ev_backtest.py
- review_strategy
- test_drift_monitor.py
- timedelta
- monitor_run.py
- client.py
- evaluate_closing_line_model
- pit_store.py
- prop_alert_key
- test_live_scan.py
- _coinflip_bets
- compare_to_book
- PointInTimeStore
- permutation_test_lift
- _apply_exposure_cap
- test_collect_scheduler.py
- test_steam_scan.py
- split_by_season
- CollectorState
- budget.py
- props_run.py
- expanding_season_folds
- ValueError
- _detect_decay
- BlockingScheduler
- parametrize

## God Nodes (most connected - your core abstractions)
1. `Side` - 135 edges
2. `PointInTimeStore` - 129 edges
3. `Market` - 117 edges
4. `OddsSnapshot` - 46 edges
5. `OddsApiClient` - 44 edges
6. `OddsApiResponse` - 31 edges
7. `Outcome` - 29 edges
8. `MatchResult` - 29 edges
9. `settle()` - 29 edges
10. `OddsApiError` - 28 edges

## Surprising Connections (you probably didn't know these)
- `test_mainline_order_rejects_player_fields()` --uses--> `BetOrder`  [INFERRED]
  tests/test_engine_props.py → src/backtest/engine.py
- `test_prop_order_requires_player_fields()` --uses--> `BetOrder`  [INFERRED]
  tests/test_engine_props.py → src/backtest/engine.py
- `test_leg_validates_probability_and_price()` --uses--> `ParlayLeg`  [INFERRED]
  tests/test_parlay.py → src/backtest/parlay.py
- `test_unchanged_spot_does_not_realert_but_improved_one_does()` --indirect_call--> `prop_alert_key()`  [INFERRED]
  tests/test_props_scan.py → src/signal/props_scan.py
- `test_win_interval_home_matches_settle_on_real_scores()` --uses--> `GameResult`  [INFERRED]
  tests/test_middling.py → src/store/settlement.py

## Import Cycles
- None detected.

## Communities (101 total, 10 thin omitted)

### Community 0 - "Market"
Cohesion: 0.13
Nodes (37): Market, build_results_index(), GameResult, _outcome_from_margin(), DataFrame, Enum, Settlement: grade win/loss/push outcomes against nflverse final scores.…, Batch-grade snapshot-shaped rows (event_id, market, side, line columns) against… (+29 more)

### Community 1 - "scheduler.py"
Cohesion: 0.16
Nodes (19): Config, load_config(), Path, Collector configuration. Everything The Odds API's free-tier budget forces us…, Build a Config from environment variables (or an injected mapping for tests).…, build_context(), main(), Entrypoint: `python -m src.collect.run [--once]`. `--once` does a single… (+11 more)

### Community 2 - "test_evaluate.py"
Cohesion: 0.12
Nodes (27): brier_score(), log_loss(), power_analysis(), DataFrame, ndarray, Model evaluation (blueprint Part B.5). "This section is where you prove you are…, mean((p - y)^2). Lower is better., -mean(y*log(p) + (1-y)*log(1-p)). p is clipped away from exactly 0/1 so a… (+19 more)

### Community 3 - "test_collect_preseason.py"
Cohesion: 0.24
Nodes (16): build_preseason_match(), poll_once(), One poll: fetch, match, transform, write. Returns counts for logging/testing --…, Build a MatchResult straight from the Odds API event, no nflverse schedule…, RuntimeError, Raised when an Odds API event can't be joined to a schedule row., UnmatchedEventError, _preseason_event() (+8 more)

### Community 4 - "test_closing_line.py"
Cohesion: 0.19
Nodes (18): build_closing_line_frame(), closing_fair_probabilities(), PointInTimeStore, Predict Pinnacle's CLOSING fair probability from pre-game features. **This is…, `event_id` -> `close_fair_prob`, the devigged closing home-win probability.…, `training_frame` (from `src/model/train.py::build_training_frame`) joined to…, _ml(), Negative control: if the close is unrelated to the features, R^2 must not come… (+10 more)

### Community 5 - "props.py"
Cohesion: 0.17
Nodes (22): OddsApiError, RuntimeError, Network or unexpected-response failure talking to The Odds API., event_odds_to_prop_snapshots(), poll_all_props(), poll_event_props(), datetime, ScheduleIndex (+14 more)

### Community 6 - "4. Methodology"
Cohesion: 0.17
Nodes (12): 4.10 Middling: exploiting real line movement over time (2026-08-20), 4.11 Steam detection: synchronized cross-book movement (2026-08-21), 4.1 Odds conversion, 4.2 Devigging methods, 4.3 Closing Line Value, 4.4 Point-in-time backtesting framework, 4.5 Modeling approach, 4.6 Bet sizing (+4 more)

### Community 8 - "test_devig.py"
Cohesion: 0.12
Nodes (30): compare_methods(), compare_methods_table(), devig_additive(), devig_multiplicative(), devig_power(), devig_shin(), DevigResult, overround() (+22 more)

### Community 9 - "add_rest_travel_features"
Cohesion: 0.06
Nodes (75): add_rest_travel_features(), add_weather_features(), build_game_features(), _is_garbage_time(), DataFrame, Series, Feature builder (blueprint Part E): team-strength proxies from play-by-play.…, One row per game_id: home/away pre-game rolling EPA features plus the schedule… (+67 more)

### Community 10 - "test_props_scan.py"
Cohesion: 0.13
Nodes (33): find_live_prop_arb_spots(), find_live_prop_ev_spots(), _fresh_only(), _live_props(), DataFrame, datetime, PointInTimeStore, Timedelta (+25 more)

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
Cohesion: 0.08
Nodes (55): _best_line(), best_middle_for_game(), find_middle_opportunities(), _interval_prob(), line_threshold(), middle_ev(), MiddleOpportunity, pinnacle_reference_line() (+47 more)

### Community 37 - "demo_pipeline.py"
Cohesion: 0.18
Nodes (18): main(), make_synthetic_snapshots(), datetime, End-to-end pipeline demo: pull -> store -> compare -> decide -> notify. `make…, _step(), _escape_for_applescript(), RuntimeError, SMS/iMessage alerts via macOS Messages.app. No third-party account, no API key:… (+10 more)

### Community 38 - "3. Data"
Cohesion: 0.18
Nodes (11): 3.10 Player-prop cross-book strategies (historical, not the live CLV headline), 3.1 Sources, 3.2 Live snapshot collection, 3.3 Known data limitations, 3.4 Bet execution venues, 3.5 Preseason dry run (infrastructure validation, not a result), 3.6 Player props (infrastructure prepped, not active), 3.7 Receiver-level Elo (player-prop pricing infrastructure) (+3 more)

### Community 39 - "test_elo.py"
Cohesion: 0.15
Nodes (25): canonical_team(), compute_team_elo_ratings(), mov_multiplier(), DataFrame, Elo rating system: opponent-adjusted team strength, sequential and leakage-free…, One row per game: each team's Elo rating *entering* that game (pre-game,…, Map a historical/relocated abbreviation to the current one a franchise's rating…, FiveThirtyEight's margin-of-victory multiplier: ln(|margin| + 1) * (2.2 /… (+17 more)

### Community 40 - "NFL CLV Case Study: Blueprint"
Cohesion: 0.06
Nodes (34): A simple, honest first model, B.1 Odds to implied probability, B.2 The vig, and why devigging is the real work, B.3 Closing Line Value, B.4 Bet sizing, B.5 Evaluation and, above all, sample size, Free static data, for backtester and baselines (cost: 0), Live intraday data, self-collected (the thing you cannot buy cheap) (+26 more)

### Community 41 - "test_evaluation.py"
Cohesion: 0.19
Nodes (20): evaluate_at_threshold(), Metrics for the subset of `bets` whose edge clears `threshold`. `bets` needs…, _bets(), **Acceptance test.** `props_ev_backtest` found no detectable edge on real 2024…, Four bets at a huge price that all happened to win: positive ROI, but nothing…, Monotonicity is a disqualifier when measurable -- a strong-looking result that…, A vig'd 'probability' pair sums > 1 and individual legs can exceed 1; accepting…, The metric that exposes 'profitable on 4 of 900 games' as noise. (+12 more)

### Community 42 - "OddsSnapshot"
Cohesion: 0.15
Nodes (26): BaseModel, backfill_historical_mainline(), pull_historical_mainline_snapshot(), datetime, Historical mainline (h2h/spreads/totals) odds backfill. **The rigor fix from…, One historical mainline snapshot (nearest available <= `date`) for one event --…, `games`: iterable of (match, home_name, away_name, kickoff) -- same shape as…, Preseason dry-run collector: same collection mechanics as the real season… (+18 more)

### Community 43 - "Methodology backlog"
Cohesion: 0.14
Nodes (13): 1. Rest/travel differential — **tested, negative result**, 2. Joint margin/total correlated distribution — **checked, premise doesn't hold**, 3. Steam detection — **built and live-validated**, 4. Player-prop middling — idea, blocked on live props posting, 5. Referee tendencies — **checked, no signal found (correcting an earlier wrong "blocked" claim)**, 6. Individual pass-rush rating — **built, corrects an earlier wrong "not buildable" claim**, 7. Training-window size — **checked, real effect, first non-Elo comparison to survive BH correction (in the negative direction)**, 8. Mainline historical odds pull — **executed, gap confirmed real but numerically inconsequential** (+5 more)

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

### Community 51 - "test_prop_projection.py"
Cohesion: 0.13
Nodes (31): build_prop_training_frame(), fit_prop_model(), predict_over_probability(), prior_form(), DataFrame, ndarray, Pipeline, Project a player's stat against the book's posted prop line. **The formulation… (+23 more)

### Community 52 - "Side"
Cohesion: 0.16
Nodes (21): middle_window(), The overlap of two opposite-side legs' win regions, or None if no real (finite,…, datetime, Enum, str, Point-in-time odds snapshot schema. One row = one price, for one side, at one…, Build a snapshot from an American price, deriving decimal + implied prob., Side (+13 more)

### Community 53 - "test_synthetic_market.py"
Cohesion: 0.12
Nodes (32): OddsSnapshot, _logit(), datetime, Market, ndarray, Side, Synthetic market simulator -- validates this project's OWN CLV-measurement code…, Ground truth for one simulated player-prop contract. `over_hit` is the realized… (+24 more)

### Community 54 - "test_individual_pass_rush_elo.py"
Cohesion: 0.21
Nodes (20): build_individual_pass_rush_frame(), compute_individual_pass_rush_ratings(), DataFrame, Individual pass-rush rating: a real, previously-blocked capability. **Corrects…, One row per player-game at a real pass-rush position with at least one…, One row per player-game: this player's individual pass-rush rating *entering*…, _pfr_row(), _player_game() (+12 more)

### Community 55 - "test_game_level_features.py"
Cohesion: 0.11
Nodes (38): current_injury_status(), current_team(), player_status_snapshot(), DataFrame, Current player status: which team a player is on, and their injury/game status,…, One row per player: their most recent roster team/status at or before…, One row per player with an injury-report history: their most recent…, One row per rostered player: current team (trade-aware) + current injury/game… (+30 more)

### Community 56 - "test_validation.py"
Cohesion: 0.17
Nodes (20): benjamini_hochberg(), paired_permutation_test_mean_diff(), One-sided significance test for whether the mean of paired per-game differences…, Benjamini-Hochberg false-discovery-rate correction. Returns a boolean array, in…, test_benjamini_hochberg_all_significant(), test_benjamini_hochberg_is_more_conservative_than_uncorrected_alpha(), test_benjamini_hochberg_matches_hand_computation_simple_case(), test_benjamini_hochberg_none_significant() (+12 more)

### Community 57 - "test_clv_metrics.py"
Cohesion: 0.16
Nodes (20): beat_rate(), bootstrap_ci(), clv_price(), clv_probability(), Closing Line Value metrics (blueprint Part B.3). CLV is measured two ways --…, How far the fair market moved toward your side after you bet. Positive means…, Whether the decimal price you took beats the closing price for the same side.…, Fraction of bets with positive CLV. (+12 more)

### Community 58 - "test_steam.py"
Cohesion: 0.10
Nodes (41): book_moves(), BookMove, detect_steam_move(), find_steam_opportunities(), _interval_prob(), _largest_time_cluster(), price_stale_book_opportunity(), DataFrame (+33 more)

### Community 59 - "test_pass_rush_elo.py"
Cohesion: 0.22
Nodes (17): compute_pass_rush_elo_ratings(), credited_pressure_counts(), DataFrame, Pass-rush Elo: a play-level, team-level rating of pass-rush vs. pass-protection…, Raw per-player counts of sacks (full credit), half-sacks (0.5 credit), and QB…, One row per dropback: `posteam`'s pass-protection Elo and `defteam`'s pass-rush…, _pbp(), test_clean_pocket_lowers_rush_elo_and_raises_protection_elo() (+9 more)

### Community 60 - "test_sizing.py"
Cohesion: 0.07
Nodes (55): parlay_ev(), parlay_independent_probability(), parlay_price_decimal(), parlay_true_probability(), ParlayLeg, Parlay pricing and EV -- multi-leg bets, priced against REAL leg prices. **Why…, Full EV/sizing for one parlay, reusing `src/signal/sizing.py`'s…, The one case this project has real measured correlation for: two same-game… (+47 more)

### Community 61 - "test_middle_scan.py"
Cohesion: 0.33
Nodes (10): main(), DataFrame, One scan. Returns the report DataFrame (also logged); never sends any…, run(), _seed_store_with_real_movement(), _snapshot(), test_run_filters_out_windows_below_min_ev(), test_run_finds_and_logs_a_real_middle() (+2 more)

### Community 62 - "market_baseline"
Cohesion: 0.06
Nodes (83): CalibratedClassifierCV, HistGradientBoostingClassifier, Protocol, fit_residual_stds(), Middle-scan entrypoint: `python -m src.backtest.middle_scan`. A manual, run-by-…, (sigma_margin, sigma_total) for LIVE pricing -- not the research evaluation…, market_baseline(), Market baseline (blueprint Part E). "Your baseline is the devigged Pinnacle… (+75 more)

### Community 63 - "evaluation.py"
Cohesion: 0.13
Nodes (21): evaluate_strategy(), evaluate_threshold_sweep(), DataFrame, ndarray, random_bet_benchmark(), Betting-evaluation harness: is an edge *bettable*, not merely calibrated? **Why…, The whole curve, one row per threshold -- never just the best cell. Read…, Does `metric` hold up as the threshold tightens? A real edge should not… (+13 more)

### Community 64 - "compute_qb_elo_ratings"
Cohesion: 0.33
Nodes (10): compute_qb_elo_ratings(), DataFrame, QB-level Elo: a residual rating crediting individual quarterback performance…, One row per game: each starting QB's Elo rating *entering* that game (pre-game,…, _schedule(), test_backup_qb_starts_are_tracked_as_a_distinct_rating_from_the_starter(), test_first_start_for_every_qb_begins_at_initial_rating(), test_qb_rating_carries_across_games_not_reset() (+2 more)

### Community 65 - "test_team_total_props.py"
Cohesion: 0.20
Nodes (20): build_team_total_lines(), fit_team_total_residual_std(), DataFrame, Series, Team-total rushing/passing yards vs. moneyline correlation…, (mean_residual, residual_std) of `actual_team_total - implied_team_total_line`…, Boolean: did the team's real total clear its own real implied line -- the leg…, One row per (event_id, team) with real Pinnacle data for `prop_stat`:… (+12 more)

### Community 66 - "OddsApiResponse"
Cohesion: 0.24
Nodes (16): OddsApiResponse, backfill_historical_props(), find_historical_event_id(), pull_historical_prop_snapshot(), datetime, Historical player-prop odds backfill for backtesting. **Blocked on paid…, 1 credit. Looks up the historical events list as of `date` and returns the Odds…, One historical snapshot (nearest available <= `date`) for one or more markets… (+8 more)

### Community 67 - "test_clv_portfolio.py"
Cohesion: 0.15
Nodes (29): bankroll_path(), bets_to_frame(), clv_by_segment(), clv_summary(), DataFrame, Portfolio-level CLV reporting: combine every bet the engine produced --…, `clv_summary` computed per segment -- one row per distinct value of…, Running bankroll after each settled bet -- the realized path, not a per-bet… (+21 more)

### Community 68 - "compute_receiver_elo_ratings"
Cohesion: 0.29
Nodes (13): compute_receiver_elo_ratings(), DataFrame, Receiver-level Elo: a play-level rating for pass-catchers, run against a…, One row per target (pass play with a recorded receiver): the receiver's and the…, _pbp(), test_different_receivers_and_defenses_tracked_independently(), test_failed_target_lowers_receiver_and_raises_defense(), test_first_target_begins_at_initial_rating() (+5 more)

### Community 69 - "Architecture & Status Audit"
Cohesion: 0.12
Nodes (15): 1. What is actually running right now, 2. Layer map, 3. Module status, 4. Orphan list — delete or wire, 5. Notebooks, 6. Strategy verdicts (`methodology_backlog.md`), 7. Data inventory, 8. Design rule: which strategies work here, and why (+7 more)

### Community 70 - "test_collect_budget.py"
Cohesion: 0.16
Nodes (20): current_period_end(), parse_quota_headers(), date, QuotaState, Rolls `anchor` forward by `period_days` until the result is after `now`.…, _decide(), test_both_tiers_unaffordable_is_budget_exhausted(), test_credits_at_or_below_safety_reserve_exhausts_budget() (+12 more)

### Community 71 - "load_static.py"
Cohesion: 0.13
Nodes (19): home_spread_line(), load_injuries(), load_pbp(), load_pfr_pass_rush_advstats(), load_player_stats(), load_players(), load_snap_counts(), load_weekly_rosters() (+11 more)

### Community 72 - "test_engine_props.py"
Cohesion: 0.08
Nodes (64): Outcome, BacktestEngine, BetOrder, DecisionPoint, latest_fair_prob(), _latest_price(), _market_rows(), _parse_kickoffs() (+56 more)

### Community 73 - "elo_win_probability"
Cohesion: 0.29
Nodes (7): elo_win_probability(), Standard Elo logistic transform: P(a beats b), with `a` treated as the side…, test_400_point_gap_is_the_classic_10_to_1_elo_property(), test_equal_ratings_no_hfa_is_a_coin_flip(), test_home_field_advantage_shifts_probability_toward_home(), test_base_pressure_offset_recenters_expectation_to_the_measured_base_rate(), test_base_pressure_offset_recenters_expectation_to_the_measured_base_rate()

### Community 74 - "run"
Cohesion: 0.38
Nodes (9): main(), One scan-and-alert cycle across all three signals. Returns the number of alerts…, run(), _seed_store(), _snapshot(), test_run_does_not_record_a_spot_whose_send_failed(), test_run_does_not_send_or_record_when_phone_not_configured(), test_run_returns_zero_when_no_spots_found() (+1 more)

### Community 75 - "test_props_ev_backtest.py"
Cohesion: 0.07
Nodes (61): model_validator, find_arbitrage_spots(), find_prop_ev_spots(), pinnacle_fair_probs(), DataFrame, Timedelta, Cross-book player-prop strategies that don't rely on market timing: (1) a…, One row per (event, player, prop_stat, line, side, book) where `book`'s price… (+53 more)

### Community 76 - "review_strategy"
Cohesion: 0.09
Nodes (41): _clv_series(), format_review_summary(), DataFrame, In-season strategy review: is each live strategy still working, and when should…, Full health check on one strategy's live bets. The recommendation is…, One review row per strategy segment. Segments rather than pools for the same…, Human-readable digest, ordered so anything needing action is first -- this is…, CLV in decision order, dropping unmeasurable bets. Order matters: CUSUM is a… (+33 more)

### Community 77 - "test_drift_monitor.py"
Cohesion: 0.18
Nodes (18): cusum(), first_flag_index(), ndarray, Non-stationarity / drift monitor (blueprint Part E, "the genuinely hard part").…, Index of the first True in `flagged`, or None if it never fires., Trailing rolling mean CLV, one value per bet. Uses whatever history exists so…, Two-sided CUSUM change-point detector. `upper` accumulates evidence of a…, Rolling Brier score over the trailing `window` predictions, minus a… (+10 more)

### Community 78 - "timedelta"
Cohesion: 0.08
Nodes (64): timedelta, arb_poll_targets_hours(), build_poll_targets(), decide_props_poll(), dense_poll_targets_hours(), EventPollState, load_state(), PollTarget (+56 more)

### Community 79 - "monitor_run.py"
Cohesion: 0.20
Nodes (18): _alert_batch(), DataFrame, Series, Live +EV monitor entrypoint: `python -m src.notify.monitor_run`. Meant to be…, Dedup -> format -> send one class of alert. Shared by all three signals so they…, _alert_key(), AlertRecord, load_alert_state() (+10 more)

### Community 80 - "client.py"
Cohesion: 0.15
Nodes (11): Response, _parse_int_header(), _parse_iso(), datetime, Thin HTTP wrapper around The Odds API. Talks to The Odds API directly (not…, Historical per-event odds, snapshotted at the nearest available timestamp <=…, Shared retry/error-handling for both endpoints. Returns the raw successful…, Bulk endpoint: one call returns every event in the sport's current slate. This… (+3 more)

### Community 81 - "evaluate_closing_line_model"
Cohesion: 0.18
Nodes (19): evaluate_closing_line_model(), fit_closing_line_model(), predict_closing_prob(), DataFrame, ndarray, Pipeline, Ridge regression onto `close_fair_prob`. Ridge rather than plain OLS because…, Predicted closing probability, clipped to a valid range -- an unclipped linear… (+11 more)

### Community 82 - "pit_store.py"
Cohesion: 0.17
Nodes (10): LeakageError, DataFrame, datetime, Path, RuntimeError, Append-only, point-in-time odds store. This is the leakage guard for the whole…, The only read path. Returns rows visible at `decision_time`, and nothing later., Raised if a query would return (or returned) data from after decision_time. (+2 more)

### Community 83 - "prop_alert_key"
Cohesion: 0.17
Nodes (13): _fmt_american(), format_arb_alert_message(), format_prop_ev_alert_message(), prop_alert_key(), Series, Arb alerts name BOTH legs and both books -- an arb is only real if both are…, Dedup key for a prop alert. **Must include player/stat/line** --…, The props-EV signal tested null; the alert must say so rather than read like… (+5 more)

### Community 84 - "test_live_scan.py"
Cohesion: 0.20
Nodes (18): find_positive_ev_spots(), _latest_two_sided_pinnacle(), DataFrame, datetime, PointInTimeStore, Timedelta, One row per (event, side, book) where `book`'s latest moneyline price beats…, Drop snapshots for games that have already kicked off -- only a future game is… (+10 more)

### Community 85 - "_coinflip_bets"
Cohesion: 0.29
Nodes (7): _coinflip_bets(), A strategy with no real selection skill should not stand out against randomly…, The negative control for the acceptance test above: a harness that always says…, n bets on true 50/50 events at a fixed price, with a controlled realized win…, test_detects_a_real_edge_when_one_actually_exists(), test_random_benchmark_flags_a_genuinely_strong_result(), test_random_benchmark_places_a_fair_coinflip_strategy_mid_distribution()

### Community 86 - "compare_to_book"
Cohesion: 0.40
Nodes (5): compare_to_book(), Forecast-quality comparison: model vs. book on the same events. Necessary but…, These are different questions and the API keeps them apart -- a model can win…, test_beating_the_book_on_brier_is_reported_separately_from_bettability(), test_compare_to_book_reports_both_sides_and_who_wins()

### Community 87 - "PointInTimeStore"
Cohesion: 0.30
Nodes (15): PointInTimeStore, Regression guard: if `_filter` is ever changed to stop filtering, read_as_of…, Regression guard: a schema addition (player_name/prop_stat, added for player…, _snap(), test_decision_time_must_be_tz_aware(), test_event_id_filter(), test_leakage_guard_fires_if_filter_is_ever_broken(), test_read_as_of_before_any_capture_returns_empty() (+7 more)

### Community 88 - "permutation_test_lift"
Cohesion: 0.14
Nodes (14): _lift(), permutation_test_lift(), ndarray, Series, Portfolio validation: leakage-safe splitting, walk-forward folds, permutation…, P(a and b) / (P(a) x P(b)) -- the exact formula…, An empirical, simulation-based alternative to `measure_leg_correlation`'s…, test_lift_matches_measure_leg_correlation() (+6 more)

### Community 89 - "_apply_exposure_cap"
Cohesion: 0.22
Nodes (9): parametrize, _apply_exposure_cap(), Keep alerts in priority order until their suggested stakes exhaust `remaining`,…, Arb spots carry no `suggested_stake` (legs are sized separately), but they are…, The cap is a per-CYCLE ceiling, not per-batch: spending it on the first signal…, test_exposure_budget_is_shared_across_successive_signals(), test_exposure_cap_charges_rows_without_a_stake_column(), test_exposure_cap_handles_extremes() (+1 more)

### Community 90 - "test_collect_scheduler.py"
Cohesion: 0.45
Nodes (13): Wraps _tick(ctx) so one unexpected bug in a single poll never kills a long-…, tick(), _config(), _ctx(), _pinnacle_event(), test_tick_does_not_poll_when_too_soon(), test_tick_never_propagates_unexpected_bug(), test_tick_persists_state_after_successful_poll() (+5 more)

### Community 91 - "test_steam_scan.py"
Cohesion: 0.28
Nodes (11): main(), DataFrame, Steam-scan entrypoint: `python -m src.backtest.steam_scan`. Manual, run-by-…, One scan. Returns the report DataFrame (also logged); never sends any…, run(), _seed_store_with_real_steam(), _snapshot(), test_run_filters_out_spots_below_min_ev() (+3 more)

### Community 92 - "split_by_season"
Cohesion: 0.22
Nodes (9): DataFrame, (train_df, test_df): rows with `season_col` in `test_seasons` go to test,…, split_by_season(), test_split_by_season_accepts_multiple_test_seasons(), test_split_by_season_custom_column_name(), test_split_by_season_empty_test_seasons_raises(), test_split_by_season_missing_column_raises(), test_split_by_season_resets_index() (+1 more)

### Community 93 - "CollectorState"
Cohesion: 0.33
Nodes (7): CollectorState, load_state(), Path, Persisted to disk between process restarts (default: data/collect_state.json)., save_state(), test_load_state_missing_file_returns_none(), test_state_roundtrip()

### Community 94 - "budget.py"
Cohesion: 0.54
Nodes (7): decide_poll(), _game_interval_minutes(), _minutes_since(), _nearest_upcoming_hours(), PollDecision, datetime, Budget-aware polling cadence. The Odds API bills `regions x markets` credits…

### Community 95 - "props_run.py"
Cohesion: 0.13
Nodes (25): BlockingScheduler, main(), main(), Manual entrypoint: `python -m src.collect.props`. See module docstring -- not…, build_context(), main(), Entrypoint: `python -m src.collect.props_run [--once]`. Live player-prop…, build_scheduler() (+17 more)

### Community 96 - "expanding_season_folds"
Cohesion: 0.29
Nodes (7): expanding_season_folds(), Expanding-window walk-forward folds: `(train_seasons, test_season)` pairs where…, test_expanding_season_folds_dedupes_and_sorts_input(), test_expanding_season_folds_never_trains_on_a_later_season_than_it_tests(), test_expanding_season_folds_produces_correct_boundaries(), test_expanding_season_folds_rejects_min_train_seasons_leaving_no_test_season(), test_expanding_season_folds_rejects_non_positive_min_train_seasons()

### Community 98 - "_detect_decay"
Cohesion: 0.67
Nodes (3): _detect_decay(), ndarray, Has CLV shifted *downward* from this strategy's OWN established baseline? Two…

## Knowledge Gaps
- **139 isolated node(s):** `1. What is actually running right now`, `2. Layer map`, `store/ — foundation (all LIVE)`, `collect/ — data acquisition`, `model/ — feature/rating layer (trains ONLY on free nflverse data)` (+134 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PointInTimeStore` connect `PointInTimeStore` to `scheduler.py`, `test_collect_preseason.py`, `test_closing_line.py`, `props.py`, `test_props_scan.py`, `test_middling.py`, `demo_pipeline.py`, `OddsSnapshot`, `test_steam.py`, `test_middle_scan.py`, `market_baseline`, `OddsApiResponse`, `test_engine_props.py`, `run`, `test_props_ev_backtest.py`, `timedelta`, `pit_store.py`, `test_live_scan.py`, `test_collect_scheduler.py`, `test_steam_scan.py`, `props_run.py`?**
  _High betweenness centrality (0.123) - this node is a cross-community bridge._
- **Why does `Side` connect `Side` to `Market`, `Outcome`, `test_middling.py`, `demo_pipeline.py`, `props.py`, `test_engine_props.py`, `OddsSnapshot`, `run`, `test_props_ev_backtest.py`, `test_live_scan.py`, `PointInTimeStore`, `test_steam.py`, `test_steam_scan.py`, `test_middle_scan.py`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Why does `expected_value()` connect `test_sizing.py` to `test_evaluation.py`, `test_props_ev_backtest.py`, `test_correlated_props.py`, `test_live_scan.py`, `test_steam.py`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Are the 109 inferred relationships involving `Side` (e.g. with `_best_line()` and `best_middle_for_game()`) actually correct?**
  _`Side` has 109 INFERRED edges - model-reasoned connections that need verification._
- **Are the 68 inferred relationships involving `PointInTimeStore` (e.g. with `run()` and `find_middle_opportunities()`) actually correct?**
  _`PointInTimeStore` has 68 INFERRED edges - model-reasoned connections that need verification._
- **Are the 93 inferred relationships involving `Market` (e.g. with `best_middle_for_game()` and `find_middle_opportunities()`) actually correct?**
  _`Market` has 93 INFERRED edges - model-reasoned connections that need verification._
- **Are the 87 inferred relationships involving `timedelta` (e.g. with `current_period_end()` and `backfill_historical_mainline()`) actually correct?**
  _`timedelta` has 87 INFERRED edges - model-reasoned connections that need verification._