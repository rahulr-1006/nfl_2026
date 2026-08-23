# Graph Report - nfl_2026  (2026-08-23)

## Corpus Check
- 156 files · ~142,685 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2164 nodes · 5740 edges · 97 communities (89 shown, 8 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 809 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7e20747b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ValueError
- bet_log.py
- test_evaluate.py
- preseason.py
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
- Side
- test_middling.py
- market_baseline
- 3. Data
- test_elo.py
- NFL CLV Case Study: Blueprint
- evaluation.py
- MatchResult
- Methodology backlog
- test_correlated_props.py
- OddsApiError
- Beating the Close, Not the Book: A CLV-First Case Study of NFL Betting Markets
- 5. Results
- 1. Introduction
- 6. Discussion
- 2. Background and Related Work
- test_prop_projection.py
- Open items, in the order they should be picked up
- scheduler.py
- test_individual_pass_rush_elo.py
- test_game_level_features.py
- test_validation.py
- OddsApiResponse
- test_steam.py
- test_pass_rush_elo.py
- test_drift_monitor.py
- OddsApiClient
- test_bet_log.py
- test_backtest_engine.py
- expected_value
- test_team_total_props.py
- Market
- season_review.py
- compute_receiver_elo_ratings
- Architecture & Status Audit
- test_health_check.py
- engine.py
- test_engine_props.py
- test_margin_total.py
- test_clv_metrics.py
- prop_alert_key
- review_strategy
- test_synthetic_market.py
- test_props_budget.py
- SmsError
- test_evaluation.py
- test_collect_budget.py
- find_live_prop_arb_spots
- load_static.py
- PointInTimeStore
- test_live_scan.py
- compare_to_book
- test_collect_scheduler.py
- run
- elo_win_probability
- CollectorState
- monitor_run.py
- budget.py
- test_monotonicity_check_ignores_thin_tail_rows
- _coinflip_bets
- compute_qb_elo_ratings
- audit_integration.py

## God Nodes (most connected - your core abstractions)
1. `PointInTimeStore` - 198 edges
2. `Side` - 198 edges
3. `Market` - 174 edges
4. `OddsSnapshot` - 70 edges
5. `Outcome` - 48 edges
6. `OddsApiClient` - 46 edges
7. `OddsApiResponse` - 34 edges
8. `settle()` - 32 edges
9. `BacktestEngine` - 31 edges
10. `OddsApiError` - 29 edges

## Surprising Connections (you probably didn't know these)
- `test_favorite_and_underdog_decimal_conversion()` --calls--> `american_to_decimal()`  [INFERRED]
  tests/test_schema.py → src/devig/convert.py
- `_bet_star_over()` --uses--> `DecisionPoint`  [INFERRED]
  tests/test_engine_props.py → src/backtest/engine.py
- `_bet_star_over()` --uses--> `BetOrder`  [INFERRED]
  tests/test_engine_props.py → src/backtest/engine.py
- `_both_over()` --uses--> `BetOrder`  [INFERRED]
  tests/test_engine_props.py → src/backtest/engine.py
- `test_mainline_order_rejects_player_fields()` --uses--> `BetOrder`  [INFERRED]
  tests/test_engine_props.py → src/backtest/engine.py

## Import Cycles
- None detected.

## Communities (97 total, 8 thin omitted)

### Community 0 - "ValueError"
Cohesion: 0.10
Nodes (42): Dispatch to the right settlement path for this market -- game score for…, _grade(), One bet's outcome, or None if it cannot be graded yet. None is returned rather…, build_results_index(), GameResult, Outcome, _outcome_from_margin(), DataFrame (+34 more)

### Community 1 - "bet_log.py"
Cohesion: 0.13
Nodes (23): field_validator, main(), Weekly in-season health check over the LIVE bet log. Segments on `strategy`…, run(), _close_price_decimal(), _fair_at(), _kickoff_for(), kickoffs_from_store() (+15 more)

### Community 2 - "test_evaluate.py"
Cohesion: 0.12
Nodes (27): brier_score(), log_loss(), power_analysis(), DataFrame, ndarray, Model evaluation (blueprint Part B.5). "This section is where you prove you are…, mean((p - y)^2). Lower is better., -mean(y*log(p) + (1-y)*log(1-p)). p is clipped away from exactly 0/1 so a… (+19 more)

### Community 3 - "preseason.py"
Cohesion: 0.23
Nodes (17): build_preseason_match(), main(), poll_once(), Preseason dry-run collector: same collection mechanics as the real season…, One poll: fetch, match, transform, write. Returns counts for logging/testing --…, Build a MatchResult straight from the Odds API event, no nflverse schedule…, Raised when an Odds API event can't be joined to a schedule row., UnmatchedEventError (+9 more)

### Community 4 - "test_closing_line.py"
Cohesion: 0.12
Nodes (36): build_closing_line_frame(), closing_fair_probabilities(), evaluate_closing_line_model(), fit_closing_line_model(), predict_closing_prob(), DataFrame, ndarray, Pipeline (+28 more)

### Community 5 - "props.py"
Cohesion: 0.13
Nodes (28): event_odds_to_prop_snapshots(), main(), poll_all_props(), poll_event_props(), datetime, ScheduleIndex, Player-prop odds collection. **Prepped, not active.** Live-checked 2026-08-17…, One event's worth of prop snapshots. Raises OddsApiError/RateLimitExceeded to… (+20 more)

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
Cohesion: 0.12
Nodes (25): _apply_exposure_cap(), Keep alerts in priority order until their suggested stakes exhaust `remaining`,…, _prop(), parametrize, Arb spots carry no `suggested_stake` (legs are sized separately), but they are…, The cap is a per-CYCLE ceiling, not per-batch: spending it on the first signal…, A contract pulled from the board keeps its last-ever quote, which…, The filter must remove only the past, not suppress live spots that happen to… (+17 more)

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
Cohesion: 0.18
Nodes (24): build_player_stats_index(), DataFrame, Settlement for player-prop (Over/Under) bets against nflverse's per-player game…, Batch-grade prop-shaped rows (event_id/game_id, player_name, prop_stat, side,…, (game_id, player_display_name) -> {stat_column: value}, from nflreadpy's…, Grade a single Over/Under prop bet. Pushes are real for integer-valued stats…, settle_prop(), settle_prop_snapshots() (+16 more)

### Community 36 - "test_middling.py"
Cohesion: 0.07
Nodes (59): _best_line(), best_middle_for_game(), find_middle_opportunities(), _interval_prob(), line_threshold(), middle_ev(), middle_window(), MiddleOpportunity (+51 more)

### Community 37 - "market_baseline"
Cohesion: 0.06
Nodes (65): model_validator, find_arbitrage_spots(), find_prop_ev_spots(), pinnacle_fair_probs(), DataFrame, Timedelta, Cross-book player-prop strategies that don't rely on market timing: (1) a…, One row per (event, player, prop_stat, line, side, book) where `book`'s price… (+57 more)

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
Nodes (19): evaluate_strategy(), evaluate_threshold_sweep(), DataFrame, ndarray, random_bet_benchmark(), Betting-evaluation harness: is an edge *bettable*, not merely calibrated? **Why…, The whole curve, one row per threshold -- never just the best cell. Read…, Does `metric` hold up as the threshold tightens? A real edge should not… (+11 more)

### Community 42 - "MatchResult"
Cohesion: 0.11
Nodes (38): backfill_historical_mainline(), pull_historical_mainline_snapshot(), datetime, Historical mainline (h2h/spreads/totals) odds backfill. **The rigor fix from…, One historical mainline snapshot (nearest available <= `date`) for one event --…, `games`: iterable of (match, home_name, away_name, kickoff) -- same shape as…, build_team_name_map(), DataFrame (+30 more)

### Community 43 - "Methodology backlog"
Cohesion: 0.09
Nodes (21): 10. High-vig markets — **checked, hypothesis reframed, anytime-TD confirmed unpriceable**, 1. Rest/travel differential — **tested, negative result**, 2. Joint margin/total correlated distribution — **checked, premise doesn't hold**, 3. Steam detection — **built and live-validated**, 4. Player-prop middling — idea, blocked on live props posting, 5. Referee tendencies — **checked, no signal found (correcting an earlier wrong "blocked" claim)**, 6. Individual pass-rush rating — **built, corrects an earlier wrong "not buildable" claim**, 7. Training-window size — **checked, real effect, first non-Elo comparison to survive BH correction (in the negative direction)** (+13 more)

### Community 44 - "test_correlated_props.py"
Cohesion: 0.06
Nodes (74): bucket_edge(), bucket_favorite_strength(), build_team_game_outcomes(), correlated_edge(), estimate_game_specific_joint_prob(), is_bucket_validated(), measure_leg_correlation(), measure_leg_correlation_by_bucket() (+66 more)

### Community 45 - "OddsApiError"
Cohesion: 0.19
Nodes (18): OddsApiError, RuntimeError, Network or unexpected-response failure talking to The Odds API., backfill_historical_props(), find_historical_event_id(), pull_historical_prop_snapshot(), datetime, Historical player-prop odds backfill for backtesting. **Blocked on paid… (+10 more)

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
Nodes (14): 1. ~~Orphaned modules~~ RESOLVED 2026-08-23, 2. Stale data files — VERIFIED unreferenced, awaiting your call, 3. ~~`market_write_freshness` -> alert~~ DONE 2026-08-23, 4. ~~Full concurrent dry run~~ DONE 2026-08-23, 5. ~~Settle logged bets~~ DONE 2026-08-23, 6. Retire the preseason modules after 9/9, 7. Cosmetic / housekeeping, Open items, in the order they should be picked up (+6 more)

### Community 53 - "scheduler.py"
Cohesion: 0.16
Nodes (19): Config, load_config(), Path, Collector configuration. Everything The Odds API's free-tier budget forces us…, Build a Config from environment variables (or an injected mapping for tests).…, build_context(), main(), Entrypoint: `python -m src.collect.run [--once]`. `--once` does a single… (+11 more)

### Community 54 - "test_individual_pass_rush_elo.py"
Cohesion: 0.21
Nodes (20): build_individual_pass_rush_frame(), compute_individual_pass_rush_ratings(), DataFrame, Individual pass-rush rating: a real, previously-blocked capability. **Corrects…, One row per player-game at a real pass-rush position with at least one…, One row per player-game: this player's individual pass-rush rating *entering*…, _pfr_row(), _player_game() (+12 more)

### Community 55 - "test_game_level_features.py"
Cohesion: 0.11
Nodes (38): current_injury_status(), current_team(), player_status_snapshot(), DataFrame, Current player status: which team a player is on, and their injury/game status,…, One row per player: their most recent roster team/status at or before…, One row per player with an injury-report history: their most recent…, One row per rostered player: current team (trade-aware) + current injury/game… (+30 more)

### Community 56 - "test_validation.py"
Cohesion: 0.07
Nodes (50): benjamini_hochberg(), expanding_season_folds(), _lift(), paired_permutation_test_mean_diff(), permutation_test_lift(), DataFrame, ndarray, Series (+42 more)

### Community 57 - "OddsApiResponse"
Cohesion: 0.13
Nodes (35): OddsApiResponse, load_state(), PropsCollectorState, Path, Persisted to disk between process restarts (default:…, save_state(), build_context(), main() (+27 more)

### Community 58 - "test_steam.py"
Cohesion: 0.10
Nodes (38): book_moves(), BookMove, detect_steam_move(), find_steam_opportunities(), _interval_prob(), _largest_time_cluster(), price_stale_book_opportunity(), DataFrame (+30 more)

### Community 59 - "test_pass_rush_elo.py"
Cohesion: 0.22
Nodes (17): compute_pass_rush_elo_ratings(), credited_pressure_counts(), DataFrame, Pass-rush Elo: a play-level, team-level rating of pass-rush vs. pass-protection…, Raw per-player counts of sacks (full credit), half-sacks (0.5 credit), and QB…, One row per dropback: `posteam`'s pass-protection Elo and `defteam`'s pass-rush…, _pbp(), test_clean_pocket_lowers_rush_elo_and_raises_protection_elo() (+9 more)

### Community 60 - "test_drift_monitor.py"
Cohesion: 0.16
Nodes (20): _detect_decay(), Has CLV shifted *downward* from this strategy's OWN established baseline? Two…, cusum(), first_flag_index(), ndarray, Non-stationarity / drift monitor (blueprint Part E, "the genuinely hard part").…, Index of the first True in `flagged`, or None if it never fires., Trailing rolling mean CLV, one value per bet. Uses whatever history exists so… (+12 more)

### Community 61 - "OddsApiClient"
Cohesion: 0.11
Nodes (31): Response, Session, OddsApiClient, _parse_int_header(), _parse_iso(), datetime, RateLimitExceeded, Thin HTTP wrapper around The Odds API. Talks to The Odds API directly (not… (+23 more)

### Community 62 - "test_bet_log.py"
Cohesion: 0.12
Nodes (39): active_bets(), load_bet_log(), log_bet(), main(), Path, Append one bet. Creates the file on first use., Every logged bet, oldest first. Missing file is an empty log, not an error --…, Logged bets with superseded rows removed. Corrections are appended, never… (+31 more)

### Community 63 - "test_backtest_engine.py"
Cohesion: 0.35
Nodes (16): BetOrder, DecisionPoint, What a strategy sees when it's given a chance to act. `visible_snapshots` is…, A strategy's decision to bet, returned from a Strategy callable. None means "no…, _always_bet_home_spread(), _never_bet(), _schedule(), _seed_game1() (+8 more)

### Community 64 - "expected_value"
Cohesion: 0.07
Nodes (55): parlay_ev(), parlay_independent_probability(), parlay_price_decimal(), parlay_true_probability(), ParlayLeg, Parlay pricing and EV -- multi-leg bets, priced against REAL leg prices. **Why…, Correlation-adjusted joint win probability: the independent product scaled by…, Full EV/sizing for one parlay, reusing `src/signal/sizing.py`'s… (+47 more)

### Community 65 - "test_team_total_props.py"
Cohesion: 0.16
Nodes (24): build_team_total_lines(), fit_team_total_residual_std(), DataFrame, Series, Team-total rushing/passing yards vs. moneyline correlation…, (mean_residual, residual_std) of `actual_team_total - implied_team_total_line`…, Boolean: did the team's real total clear its own real implied line -- the leg…, One row per (event_id, team) with real Pinnacle data for `prop_stat`:… (+16 more)

### Community 66 - "Market"
Cohesion: 0.08
Nodes (44): fixture, datetime, Synthetic market simulator -- validates this project's OWN CLV-measurement code…, _to_snapshot(), make_synthetic_snapshots(), datetime, End-to-end pipeline demo: pull -> store -> compare -> decide -> notify. `make…, Append-only, point-in-time odds store. This is the leakage guard for the whole… (+36 more)

### Community 67 - "season_review.py"
Cohesion: 0.12
Nodes (33): bankroll_path(), bets_to_frame(), clv_by_segment(), clv_summary(), DataFrame, Portfolio-level CLV reporting: combine every bet the engine produced --…, `clv_summary` computed per segment -- one row per distinct value of…, Running bankroll after each settled bet -- the realized path, not a per-bet… (+25 more)

### Community 68 - "compute_receiver_elo_ratings"
Cohesion: 0.29
Nodes (13): compute_receiver_elo_ratings(), DataFrame, Receiver-level Elo: a play-level rating for pass-catchers, run against a…, One row per target (pass play with a recorded receiver): the receiver's and the…, _pbp(), test_different_receivers_and_defenses_tracked_independently(), test_failed_target_lowers_receiver_and_raises_defense(), test_first_target_begins_at_initial_rating() (+5 more)

### Community 69 - "Architecture & Status Audit"
Cohesion: 0.12
Nodes (15): 1. What is actually running right now, 2. Layer map, 3. Module status, 4. Orphan list — delete or wire, 5. Notebooks, 6. Strategy verdicts (`methodology_backlog.md`), 7. Data inventory, 8. Design rule: which strategies work here, and why (+7 more)

### Community 70 - "test_health_check.py"
Cohesion: 0.09
Nodes (57): check_all(), check_collector_health(), check_props_write_freshness(), market_write_freshness(), _now(), pinnacle_arrival_message(), prop_book_coverage(), DataFrame (+49 more)

### Community 71 - "engine.py"
Cohesion: 0.18
Nodes (15): latest_fair_prob(), _latest_price(), _market_rows(), _parse_kickoffs(), payout_for(), DataFrame, datetime, Series (+7 more)

### Community 72 - "test_engine_props.py"
Cohesion: 0.18
Nodes (29): BacktestEngine, Replays a strategy against the real point-in-time store. **Bankroll is a hard,…, _bet_star_over(), _both_over(), _player_stats(), _prop_snap(), Props CLV path through BacktestEngine -- the capability this project's actual…, Reuses prop_settlement.py's real name reconciliation -- book "AJ Brown" vs… (+21 more)

### Community 73 - "test_margin_total.py"
Cohesion: 0.05
Nodes (87): CalibratedClassifierCV, HistGradientBoostingClassifier, Protocol, fit_residual_stds(), main(), DataFrame, Middle-scan entrypoint: `python -m src.backtest.middle_scan`. A manual, run-by-…, (sigma_margin, sigma_total) for LIVE pricing -- not the research evaluation… (+79 more)

### Community 74 - "test_clv_metrics.py"
Cohesion: 0.16
Nodes (17): bootstrap_ci(), clv_price(), clv_probability(), How far the fair market moved toward your side after you bet. Positive means…, Whether the decimal price you took beats the closing price for the same side.…, Percentile bootstrap CI on mean CLV. Resamples clv_series with replacement…, test_beat_rate_all_positive_and_all_negative(), test_beat_rate_hand_computed() (+9 more)

### Community 75 - "prop_alert_key"
Cohesion: 0.17
Nodes (13): _fmt_american(), format_arb_alert_message(), format_prop_ev_alert_message(), prop_alert_key(), Series, Arb alerts name BOTH legs and both books -- an arb is only real if both are…, Dedup key for a prop alert. **Must include player/stat/line** --…, The props-EV signal tested null; the alert must say so rather than read like… (+5 more)

### Community 76 - "review_strategy"
Cohesion: 0.09
Nodes (41): _clv_series(), format_review_summary(), DataFrame, ndarray, Full health check on one strategy's live bets. The recommendation is…, One review row per strategy segment. Segments rather than pools for the same…, Human-readable digest, ordered so anything needing action is first -- this is…, CLV in decision order, dropping unmeasurable bets. Order matters: CUSUM is a… (+33 more)

### Community 77 - "test_synthetic_market.py"
Cohesion: 0.13
Nodes (27): _logit(), ndarray, timedelta, Ground truth for one simulated player-prop contract. `over_hit` is the realized…, Ground truth for one simulated game -- what `simulate_market` actually…, `n_games` synthetic games, each with its own independently-drawn latent price…, One simulated game's latent fair-probability path, length `n_steps + 1` (index…, _sigmoid() (+19 more)

### Community 78 - "test_props_budget.py"
Cohesion: 0.08
Nodes (50): arb_poll_targets_hours(), build_poll_targets(), decide_props_poll(), dense_poll_targets_hours(), early_poll_targets_hours(), EventPollState, PollTarget, PropsPollDecision (+42 more)

### Community 79 - "SmsError"
Cohesion: 0.23
Nodes (13): main(), _step(), _escape_for_applescript(), RuntimeError, SMS/iMessage alerts via macOS Messages.app. No third-party account, no API key:…, AppleScript/Messages.app failed to send., AppleScript string literals only need backslash and double-quote escaped --…, Send `text` to `phone_number` via Messages.app. Raises SmsError on any failure… (+5 more)

### Community 80 - "test_evaluation.py"
Cohesion: 0.19
Nodes (20): evaluate_at_threshold(), Metrics for the subset of `bets` whose edge clears `threshold`. `bets` needs…, _bets(), **Acceptance test.** `props_ev_backtest` found no detectable edge on real 2024…, Four bets at a huge price that all happened to win: positive ROI, but nothing…, Monotonicity is a disqualifier when measurable -- a strong-looking result that…, A vig'd 'probability' pair sums > 1 and individual legs can exceed 1; accepting…, The metric that exposes 'profitable on 4 of 900 games' as noise. (+12 more)

### Community 81 - "test_collect_budget.py"
Cohesion: 0.16
Nodes (20): current_period_end(), parse_quota_headers(), date, QuotaState, Rolls `anchor` forward by `period_days` until the result is after `now`.…, _decide(), test_both_tiers_unaffordable_is_budget_exhausted(), test_credits_at_or_below_safety_reserve_exhausts_budget() (+12 more)

### Community 82 - "find_live_prop_arb_spots"
Cohesion: 0.27
Nodes (14): find_live_prop_arb_spots(), find_live_prop_ev_spots(), _fresh_only(), _live_props(), DataFrame, datetime, Timedelta, Live player-prop scanning: cross-book arbitrage and Pinnacle-anchored EV, wired… (+6 more)

### Community 83 - "load_static.py"
Cohesion: 0.13
Nodes (19): home_spread_line(), load_injuries(), load_pbp(), load_pfr_pass_rush_advstats(), load_player_stats(), load_players(), load_snap_counts(), load_weekly_rosters() (+11 more)

### Community 84 - "PointInTimeStore"
Cohesion: 0.05
Nodes (81): main(), DataFrame, Steam-scan entrypoint: `python -m src.backtest.steam_scan`. Manual, run-by-…, One scan. Returns the report DataFrame (also logged); never sends any…, run(), available_stats(), find_team_total_spots(), format_team_total_alert() (+73 more)

### Community 85 - "test_live_scan.py"
Cohesion: 0.32
Nodes (12): find_positive_ev_spots(), Timedelta, One row per (event, side, book) where `book`'s latest moneyline price beats…, _snapshot(), test_find_positive_ev_spots_allows_a_small_natural_capture_gap(), test_find_positive_ev_spots_empty_store_returns_empty_frame(), test_find_positive_ev_spots_flags_a_book_beating_pinnacle_fair(), test_find_positive_ev_spots_ignores_a_spot_with_a_stale_pinnacle_price() (+4 more)

### Community 86 - "compare_to_book"
Cohesion: 0.40
Nodes (5): compare_to_book(), Forecast-quality comparison: model vs. book on the same events. Necessary but…, These are different questions and the API keeps them apart -- a model can win…, test_beating_the_book_on_brier_is_reported_separately_from_bettability(), test_compare_to_book_reports_both_sides_and_who_wins()

### Community 87 - "test_collect_scheduler.py"
Cohesion: 0.45
Nodes (13): Wraps _tick(ctx) so one unexpected bug in a single poll never kills a long-…, tick(), _config(), _ctx(), _pinnacle_event(), test_tick_does_not_poll_when_too_soon(), test_tick_never_propagates_unexpected_bug(), test_tick_persists_state_after_successful_poll() (+5 more)

### Community 88 - "run"
Cohesion: 0.38
Nodes (9): main(), One scan-and-alert cycle across all three signals. Returns the number of alerts…, run(), _seed_store(), _snapshot(), test_run_does_not_record_a_spot_whose_send_failed(), test_run_does_not_send_or_record_when_phone_not_configured(), test_run_returns_zero_when_no_spots_found() (+1 more)

### Community 89 - "elo_win_probability"
Cohesion: 0.29
Nodes (7): elo_win_probability(), Standard Elo logistic transform: P(a beats b), with `a` treated as the side…, test_400_point_gap_is_the_classic_10_to_1_elo_property(), test_equal_ratings_no_hfa_is_a_coin_flip(), test_home_field_advantage_shifts_probability_toward_home(), test_base_pressure_offset_recenters_expectation_to_the_measured_base_rate(), test_base_pressure_offset_recenters_expectation_to_the_measured_base_rate()

### Community 90 - "CollectorState"
Cohesion: 0.33
Nodes (7): CollectorState, load_state(), Path, Persisted to disk between process restarts (default: data/collect_state.json)., save_state(), test_load_state_missing_file_returns_none(), test_state_roundtrip()

### Community 91 - "monitor_run.py"
Cohesion: 0.15
Nodes (25): _alert_batch(), DataFrame, Series, Live +EV monitor entrypoint: `python -m src.notify.monitor_run`. Meant to be…, Dedup -> format -> send one class of alert. Shared by all three signals so they…, _alert_key(), AlertRecord, format_alert_message() (+17 more)

### Community 92 - "budget.py"
Cohesion: 0.54
Nodes (7): decide_poll(), _game_interval_minutes(), _minutes_since(), _nearest_upcoming_hours(), PollDecision, datetime, Budget-aware polling cadence. The Odds API bills `regions x markets` credits…

### Community 94 - "_coinflip_bets"
Cohesion: 0.29
Nodes (7): _coinflip_bets(), A strategy with no real selection skill should not stand out against randomly…, The negative control for the acceptance test above: a harness that always says…, n bets on true 50/50 events at a fixed price, with a controlled realized win…, test_detects_a_real_edge_when_one_actually_exists(), test_random_benchmark_flags_a_genuinely_strong_result(), test_random_benchmark_places_a_fair_coinflip_strategy_mid_distribution()

### Community 95 - "compute_qb_elo_ratings"
Cohesion: 0.33
Nodes (10): compute_qb_elo_ratings(), DataFrame, QB-level Elo: a residual rating crediting individual quarterback performance…, One row per game: each starting QB's Elo rating *entering* that game (pre-game,…, _schedule(), test_backup_qb_starts_are_tracked_as_a_distinct_rating_from_the_starter(), test_first_start_for_every_qb_begins_at_initial_rating(), test_qb_rating_carries_across_games_not_reset() (+2 more)

### Community 100 - "audit_integration.py"
Cohesion: 0.29
Nodes (12): check_architecture_md(), classify(), main(), _make_entrypoints(), _module_graph(), _notebook_entrypoints(), Path, Which src/ modules are actually reachable, and from what? **Why this exists.**… (+4 more)

## Knowledge Gaps
- **157 isolated node(s):** `nfl-clv`, `graphify`, `Usage`, `What graphify is for`, `Step 0 - GitHub repos and multi-path merge (only if a URL or several paths)` (+152 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PointInTimeStore` connect `PointInTimeStore` to `bet_log.py`, `preseason.py`, `test_closing_line.py`, `props.py`, `test_props_scan.py`, `test_middling.py`, `market_baseline`, `MatchResult`, `OddsApiError`, `scheduler.py`, `OddsApiResponse`, `test_steam.py`, `test_bet_log.py`, `test_backtest_engine.py`, `Market`, `season_review.py`, `test_health_check.py`, `engine.py`, `test_engine_props.py`, `test_margin_total.py`, `SmsError`, `find_live_prop_arb_spots`, `test_live_scan.py`, `test_collect_scheduler.py`, `run`, `monitor_run.py`?**
  _High betweenness centrality (0.251) - this node is a cross-community bridge._
- **Why does `Side` connect `Side` to `ValueError`, `bet_log.py`, `test_closing_line.py`, `props.py`, `test_props_scan.py`, `test_middling.py`, `market_baseline`, `MatchResult`, `test_steam.py`, `test_bet_log.py`, `test_backtest_engine.py`, `Market`, `season_review.py`, `test_health_check.py`, `engine.py`, `test_engine_props.py`, `test_margin_total.py`, `test_synthetic_market.py`, `find_live_prop_arb_spots`, `PointInTimeStore`, `test_live_scan.py`, `run`?**
  _High betweenness centrality (0.092) - this node is a cross-community bridge._
- **Why does `Market` connect `Market` to `ValueError`, `bet_log.py`, `test_closing_line.py`, `props.py`, `test_props_scan.py`, `Side`, `test_middling.py`, `market_baseline`, `MatchResult`, `test_steam.py`, `test_bet_log.py`, `test_backtest_engine.py`, `season_review.py`, `test_health_check.py`, `engine.py`, `test_engine_props.py`, `test_margin_total.py`, `test_synthetic_market.py`, `PointInTimeStore`, `test_live_scan.py`, `run`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Are the 147 inferred relationships involving `PointInTimeStore` (e.g. with `BacktestEngine` and `run()`) actually correct?**
  _`PointInTimeStore` has 147 INFERRED edges - model-reasoned connections that need verification._
- **Are the 159 inferred relationships involving `Side` (e.g. with `BacktestBet` and `BetOrder`) actually correct?**
  _`Side` has 159 INFERRED edges - model-reasoned connections that need verification._
- **Are the 137 inferred relationships involving `Market` (e.g. with `BacktestBet` and `BacktestEngine`) actually correct?**
  _`Market` has 137 INFERRED edges - model-reasoned connections that need verification._
- **Are the 40 inferred relationships involving `OddsSnapshot` (e.g. with `simulate_market()` and `_to_snapshot()`) actually correct?**
  _`OddsSnapshot` has 40 INFERRED edges - model-reasoned connections that need verification._