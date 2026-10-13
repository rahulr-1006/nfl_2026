# Graph Report - nfl_2026  (2026-10-13)

## Corpus Check
- 177 files · ~186,539 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2791 nodes · 7071 edges · 146 communities (124 shown, 22 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 799 edges (avg confidence: 0.53)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8f4f6948`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Side
- test_bet_log.py
- test_evaluate.py
- OddsApiResponse
- test_closing_line.py
- props.py
- 4. Methodology
- Parking lot
- test_devig.py
- add_rest_travel_features
- Timedelta
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
- live_scan.py
- test_middling.py
- test_synthetic_market.py
- 3. Data
- test_elo.py
- NFL CLV Case Study: Blueprint
- test_movement_scan.py
- survival_at_horizon
- Methodology backlog
- CollectorState
- test_team_total_props.py
- Beating the Close, Not the Book: A CLV-First Case Study of NFL Betting Markets
- 5. Results
- 1. Introduction
- 6. Discussion
- 2. Background and Related Work
- test_prop_projection.py
- Session handoff — 2026-09-21 (updated 2026-10-04)
- test_clv_data_path.py
- test_individual_pass_rush_elo.py
- test_game_level_features.py
- test_validation.py
- correlated_props.py
- test_steam.py
- test_pass_rush_elo.py
- mainline_historical.py
- OddsApiError
- DataFrame
- test_clv_metrics.py
- test_parlay.py
- test_prop_settlement.py
- pinnacle_fair_path
- test_clv_portfolio.py
- compute_receiver_elo_ratings
- Architecture & Status Audit
- test_health_check.py
- demo_pipeline.py
- test_engine_props.py
- OddsApiClient
- load_static.py
- test_team_total_scan.py
- review_strategy
- MatchResult
- test_props_budget.py
- PointInTimeStore
- test_evaluation.py
- test_migrate_props_poll_state.py
- middle_scan.py
- load_config
- test_clv_line_adjust.py
- test_collect_budget.py
- test_props_scan.py
- OddsSnapshot
- budget.py
- run
- test_margin_total.py
- test_train.py
- evaluation.py
- prereg_score.py
- engine.py
- calibration.py
- elo_win_probability
- BacktestEngine
- test_drift_monitor.py
- Pre-registration — 2026 Weeks 5–9 holdout
- audit_integration.py
- test_live_scan.py
- test_prereg_scan.py
- test_decision_report.py
- PropsCollectorState
- test_shadow_log.py
- test_correlated_props.py
- Train-phase results — 2026-10-04
- shadow_clv.py
- measure_prop_vig
- test_collect_scheduler.py
- market_baseline
- decision_table
- season_review.py
- datetime
- DataFrame
- RuntimeError
- decision_report.py
- date
- compute_qb_elo_ratings
- BaseModel
- field_validator
- model_validator
- datetime
- parametrize
- _coinflip_bets
- Path
- compare_to_book
- pit_store.py
- RuntimeError
- team_total_scan.py
- props_budget.py
- build_team_game_outcomes
- price_bucket_bet
- test_steam_scan.py
- DataFrame
- ndarray
- measure_leg_correlation
- scheduler.py
- test_middle_scan.py
- bucket_edge
- build_training_frame
- realistic_season_credit_cost
- h1_train_grid.py
- bucket_favorite_strength
- test_outcome_does_not_change_which_bets_get_placed

## God Nodes (most connected - your core abstractions)
1. `PointInTimeStore` - 215 edges
2. `Side` - 189 edges
3. `Market` - 178 edges
4. `OddsSnapshot` - 66 edges
5. `OddsApiClient` - 47 edges
6. `run()` - 46 edges
7. `OddsApiResponse` - 32 edges
8. `MatchResult` - 30 edges
9. `to_backtest_bets()` - 30 edges
10. `settle()` - 29 edges

## Surprising Connections (you probably didn't know these)
- `test_append_returns_count_and_round_trips()` --uses--> `ShadowObservation`  [INFERRED]
  tests/test_shadow_log.py → src/signal/shadow_log.py
- `test_naive_timestamp_is_rejected_so_elapsed_times_cannot_be_wrong()` --uses--> `ShadowObservation`  [INFERRED]
  tests/test_shadow_log.py → src/signal/shadow_log.py
- `_ml()` --uses--> `Market`  [INFERRED]
  tests/test_closing_line.py → src/store/schema.py
- `test_event_id_is_required_not_optional()` --uses--> `Market`  [INFERRED]
  tests/test_clv_data_path.py → src/store/schema.py
- `test_latest_fair_prob_scopes_to_one_event()` --uses--> `Market`  [INFERRED]
  tests/test_clv_data_path.py → src/store/schema.py

## Import Cycles
- None detected.

## Communities (146 total, 22 thin omitted)

### Community 0 - "Side"
Cohesion: 0.12
Nodes (47): BaseModel, field_validator, One leg of one alerted spot, as seen at one moment. Never rewritten., ShadowObservation, Market, str, Side, build_results_index() (+39 more)

### Community 1 - "test_bet_log.py"
Cohesion: 0.05
Nodes (84): BaseModel, field_validator, model_validator, active_bets(), _anchor_fair_for_bet(), _anchor_line_at(), _close_price_decimal(), _fair_at() (+76 more)

### Community 2 - "test_evaluate.py"
Cohesion: 0.12
Nodes (27): brier_score(), log_loss(), power_analysis(), DataFrame, ndarray, Model evaluation (blueprint Part B.5). "This section is where you prove you are…, mean((p - y)^2). Lower is better., -mean(y*log(p) + (1-y)*log(1-p)). p is clipped away from exactly 0/1 so a… (+19 more)

### Community 3 - "OddsApiResponse"
Cohesion: 0.28
Nodes (20): OddsApiResponse, datetime, Wraps _tick(ctx) so one unexpected bug never kills a long-running process --…, tick(), _ctx(), _event(), _prop_event_odds(), **The fix that makes a 21-day posting window safe.** Probing a game whose props… (+12 more)

### Community 4 - "test_closing_line.py"
Cohesion: 0.12
Nodes (36): build_closing_line_frame(), closing_fair_probabilities(), evaluate_closing_line_model(), fit_closing_line_model(), predict_closing_prob(), DataFrame, ndarray, Pipeline (+28 more)

### Community 5 - "props.py"
Cohesion: 0.14
Nodes (26): event_odds_to_prop_snapshots(), main(), poll_all_props(), poll_event_props(), datetime, ScheduleIndex, Player-prop odds collection. **Prepped, not active.** Live-checked 2026-08-17…, One event's worth of prop snapshots. Raises OddsApiError/RateLimitExceeded to… (+18 more)

### Community 6 - "4. Methodology"
Cohesion: 0.17
Nodes (12): 4.10 Middling: exploiting real line movement over time (2026-08-20), 4.11 Steam detection: synchronized cross-book movement (2026-08-21), 4.1 Odds conversion, 4.2 Devigging methods, 4.3 Closing Line Value, 4.4 Point-in-time backtesting framework, 4.5 Modeling approach, 4.6 Bet sizing (+4 more)

### Community 8 - "test_devig.py"
Cohesion: 0.09
Nodes (38): compare_methods(), compare_methods_table(), devig_additive(), devig_multiplicative(), devig_power(), devig_shin(), DevigResult, overround() (+30 more)

### Community 9 - "add_rest_travel_features"
Cohesion: 0.06
Nodes (75): date, add_rest_travel_features(), add_weather_features(), build_game_features(), _is_garbage_time(), DataFrame, Series, Feature builder (blueprint Part E): team-strength proxies from play-by-play.… (+67 more)

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

### Community 35 - "live_scan.py"
Cohesion: 0.21
Nodes (16): _alert_key(), AlertRecord, _latest_two_sided_pinnacle(), load_alert_state(), new_or_improved_spots(), DataFrame, Path, Series (+8 more)

### Community 36 - "test_middling.py"
Cohesion: 0.06
Nodes (68): _best_line(), best_middle_for_game(), find_middle_opportunities(), _interval_prob(), line_threshold(), middle_ev(), middle_window(), MiddleOpportunity (+60 more)

### Community 37 - "test_synthetic_market.py"
Cohesion: 0.07
Nodes (52): _logit(), datetime, ndarray, timedelta, Synthetic market simulator -- validates this project's OWN CLV-measurement code…, Ground truth for one simulated player-prop contract. `over_hit` is the realized…, Ground truth for one simulated game -- what `simulate_market` actually…, `n_games` synthetic games, each with its own independently-drawn latent price… (+44 more)

### Community 38 - "3. Data"
Cohesion: 0.18
Nodes (11): 3.10 Player-prop cross-book strategies (historical, not the live CLV headline), 3.1 Sources, 3.2 Live snapshot collection, 3.3 Known data limitations, 3.4 Bet execution venues, 3.5 Preseason dry run (infrastructure validation, not a result), 3.6 Player props (infrastructure prepped, not active), 3.7 Receiver-level Elo (player-prop pricing infrastructure) (+3 more)

### Community 39 - "test_elo.py"
Cohesion: 0.15
Nodes (25): canonical_team(), compute_team_elo_ratings(), mov_multiplier(), DataFrame, Elo rating system: opponent-adjusted team strength, sequential and leakage-free…, One row per game: each team's Elo rating *entering* that game (pre-game,…, Map a historical/relocated abbreviation to the current one a franchise's rating…, FiveThirtyEight's margin-of-victory multiplier: ln(|margin| + 1) * (2.2 /… (+17 more)

### Community 40 - "NFL CLV Case Study: Blueprint"
Cohesion: 0.06
Nodes (34): A simple, honest first model, B.1 Odds to implied probability, B.2 The vig, and why devigging is the real work, B.3 Closing Line Value, B.4 Bet sizing, B.5 Evaluation and, above all, sample size, Free static data, for backtester and baselines (cost: 0), Live intraday data, self-collected (the thing you cannot buy cheap) (+26 more)

### Community 41 - "test_movement_scan.py"
Cohesion: 0.12
Nodes (31): find_live_middle_spots(), find_live_steam_spots(), format_middle_alert_message(), format_steam_alert_message(), middle_alert_key(), DataFrame, datetime, Series (+23 more)

### Community 42 - "survival_at_horizon"
Cohesion: 0.15
Nodes (17): DataFrame, (survival_rate, n_in_horizon, median_minutes_to_first) for one strategy.…, Capturability of a structural (both-sides-held) strategy. An arb is only real…, structural_capture(), survival_at_horizon(), first_recheck_frame_from(), An arb with one leg gone is not a partial win, it is naked exposure., Two alerts cannot support a rate. Reporting one would turn coin flips into a… (+9 more)

### Community 43 - "Methodology backlog"
Cohesion: 0.04
Nodes (48): 10. High-vig markets — **checked, hypothesis reframed, anytime-TD confirmed unpriceable**, 1. It priced with the TRAIN fit, the highest of three available estimates, 1. Rest/travel differential — **tested, negative result**, 2. Joint margin/total correlated distribution — **checked, premise doesn't hold**, 2. The constants had NO producing code anywhere in the repo, 3. Steam detection — **built and live-validated**, 3. The player lines never entered the price, 4. Player-prop middling — idea, blocked on live props posting (+40 more)

### Community 44 - "CollectorState"
Cohesion: 0.17
Nodes (18): CollectorState, key_fingerprint(), load_state(), Path, Short, non-reversible tag identifying WHICH key a cached credit balance belongs…, Persisted to disk between process restarts (default: data/collect_state.json)., `state` with its cached credit balance dropped if it was observed on a…, save_state() (+10 more)

### Community 45 - "test_team_total_props.py"
Cohesion: 0.13
Nodes (31): build_team_outcomes(), build_team_total_lines(), fit_team_total_lift_by_bucket(), fit_team_total_residual_std(), DataFrame, Series, Team-total rushing/passing yards vs. moneyline correlation…, (mean_residual, residual_std) of `actual_team_total - implied_team_total_line`… (+23 more)

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

### Community 52 - "Session handoff — 2026-09-21 (updated 2026-10-04)"
Cohesion: 0.11
Nodes (17): 1. Let the data accumulate — do NOT ship new strategies, 2026-10-04 update — read this first, 2. ~~Exercise `make log-bet` for real before betting on it~~ — DONE 2026-09-27, 3. ~~Resolve the bankroll contradiction~~ — DONE 2026-10-04, 4. ~~Write an entry-horizon policy~~ — DONE 2026-10-04, 5. Decide `team_total_scan`'s exposure cap, 6. Known-stale, non-blocking, Concurrency verified under live-time replication (2026-09-21) (+9 more)

### Community 53 - "test_clv_data_path.py"
Cohesion: 0.15
Nodes (20): _log_a_moneyline_alert(), The CLV data path, end to end: shadow alert -> notional bet -> close -> CLV.…, `placed_at` must be when the PRICE existed, not when the scanner noticed. Entry…, A "close" read while the line is still moving would be a fabricated number, and…, Dropping them would quietly shrink the denominator, which is how a beat-rate…, These are hypotheticals. Mixing them into the record of real money would…, Two games quoted by the same book at the same instants -- the shape that broke…, The bug: on a multi-event frame every mainline lookup returned None. (+12 more)

### Community 54 - "test_individual_pass_rush_elo.py"
Cohesion: 0.21
Nodes (20): build_individual_pass_rush_frame(), compute_individual_pass_rush_ratings(), DataFrame, Individual pass-rush rating: a real, previously-blocked capability. **Corrects…, One row per player-game at a real pass-rush position with at least one…, One row per player-game: this player's individual pass-rush rating *entering*…, _pfr_row(), _player_game() (+12 more)

### Community 55 - "test_game_level_features.py"
Cohesion: 0.11
Nodes (38): current_injury_status(), current_team(), player_status_snapshot(), DataFrame, Current player status: which team a player is on, and their injury/game status,…, One row per player: their most recent roster team/status at or before…, One row per player with an injury-report history: their most recent…, One row per rostered player: current team (trade-aware) + current injury/game… (+30 more)

### Community 56 - "test_validation.py"
Cohesion: 0.07
Nodes (50): benjamini_hochberg(), expanding_season_folds(), _lift(), paired_permutation_test_mean_diff(), permutation_test_lift(), DataFrame, ndarray, Series (+42 more)

### Community 57 - "correlated_props.py"
Cohesion: 0.13
Nodes (28): Correlated same-game outcome mispricing: do event pairs from the same game co-…, apply_bankroll_caps(), expected_value(), fractional_kelly(), kelly_fraction(), Expected value and Kelly bet sizing (blueprint Part B.4). Full Kelly is too…, EV of a unit bet at fair win probability p and decimal odds d., Full Kelly fraction of bankroll. Can be negative when the price is bad at this… (+20 more)

### Community 58 - "test_steam.py"
Cohesion: 0.10
Nodes (41): book_moves(), BookMove, detect_steam_move(), find_steam_opportunities(), _interval_prob(), _largest_time_cluster(), price_stale_book_opportunity(), DataFrame (+33 more)

### Community 59 - "test_pass_rush_elo.py"
Cohesion: 0.22
Nodes (17): compute_pass_rush_elo_ratings(), credited_pressure_counts(), DataFrame, Pass-rush Elo: a play-level, team-level rating of pass-rush vs. pass-protection…, Raw per-player counts of sacks (full credit), half-sacks (0.5 credit), and QB…, One row per dropback: `posteam`'s pass-protection Elo and `defteam`'s pass-rush…, _pbp(), test_clean_pocket_lowers_rush_elo_and_raises_protection_elo() (+9 more)

### Community 60 - "mainline_historical.py"
Cohesion: 0.11
Nodes (29): backfill_historical_mainline(), estimate_pull_cost(), _iso_z(), main(), _pull_with_credits(), datetime, Historical mainline (h2h/spreads/totals) odds backfill. **The rigor fix from…, Credits a pull will cost, before spending any. One event-id lookup per game (1… (+21 more)

### Community 61 - "OddsApiError"
Cohesion: 0.19
Nodes (19): OddsApiError, RateLimitExceeded, Network or unexpected-response failure talking to The Odds API., The API rejected the request for quota/auth reasons (401/402/429)., backfill_historical_props(), find_historical_event_id(), pull_historical_prop_snapshot(), datetime (+11 more)

### Community 63 - "test_clv_metrics.py"
Cohesion: 0.10
Nodes (31): _home_fair(), main(), DataFrame, Does the line actually move toward truth? Real 2024 historical movement. **Two…, beat_rate(), bootstrap_ci(), clustered_bootstrap(), clv_price() (+23 more)

### Community 64 - "test_parlay.py"
Cohesion: 0.14
Nodes (28): parlay_ev(), parlay_independent_probability(), parlay_price_decimal(), parlay_true_probability(), ParlayLeg, Parlay pricing and EV -- multi-leg bets, priced against REAL leg prices. **Why…, Correlation-adjusted joint win probability: the independent product scaled by…, Full EV/sizing for one parlay, reusing `src/signal/sizing.py`'s… (+20 more)

### Community 65 - "test_prop_settlement.py"
Cohesion: 0.11
Nodes (32): Outcome, Side, _grade(), Outcome, One bet's outcome, or None if it cannot be graded yet. None is returned rather…, build_player_stats_index(), normalize_player_name(), Settlement for player-prop (Over/Under) bets against nflverse's per-player game… (+24 more)

### Community 66 - "pinnacle_fair_path"
Cohesion: 0.21
Nodes (27): detect_moves(), pinnacle_fair_path(), DataFrame, Series, H1 (preregistration_wk5-9.md): stale soft-book prop lines after a Pinnacle…, For each move, the best execution-book price on the moved-toward side at the…, Attach Pinnacle's close and the H1 metrics to each bet. close_ev price taken,…, Was the same book still offering at least the bet's price at its next capture… (+19 more)

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

### Community 71 - "demo_pipeline.py"
Cohesion: 0.18
Nodes (18): main(), make_synthetic_snapshots(), datetime, End-to-end pipeline demo: pull -> store -> compare -> decide -> notify. `make…, _step(), _escape_for_applescript(), RuntimeError, SMS/iMessage alerts via macOS Messages.app. No third-party account, no API key:… (+10 more)

### Community 72 - "test_engine_props.py"
Cohesion: 0.22
Nodes (23): _bet_star_over(), _both_over(), _player_stats(), _prop_snap(), Props CLV path through BacktestEngine -- the capability this project's actual…, Reuses prop_settlement.py's real name reconciliation -- book "AJ Brown" vs…, **The look-ahead regression test.** Two $2 bets placed at the SAME decision…, They were all placed at the same instant, so none of them had settled when the… (+15 more)

### Community 73 - "OddsApiClient"
Cohesion: 0.10
Nodes (31): parametrize, Response, Session, OddsApiClient, _parse_int_header(), _parse_iso(), datetime, Thin HTTP wrapper around The Odds API. Talks to The Odds API directly (not… (+23 more)

### Community 74 - "load_static.py"
Cohesion: 0.08
Nodes (31): home_spread_line(), kickoffs_utc(), load_injuries(), load_pbp(), load_pfr_pass_rush_advstats(), load_player_stats(), load_players(), load_schedules() (+23 more)

### Community 75 - "test_team_total_scan.py"
Cohesion: 0.18
Nodes (24): find_team_total_spots(), Priceable team-total spots on upcoming games. Teams in unvalidated buckets are…, _ml(), _prop(), A line that has since moved is not what you'd be betting into., -110/-110 is 4.76% overround by construction -- not the 6.29% constant., -200/+170 puts the away side in the `underdog` bucket. It used to be an even…, One-sided quotes carry no overround. Refuse rather than invent one -- the same… (+16 more)

### Community 76 - "review_strategy"
Cohesion: 0.11
Nodes (35): Full health check on one strategy's live bets. The recommendation is…, One review row per strategy segment. Segments rather than pools for the same…, review_all(), review_strategy(), _frame(), CUSUM is sequential -- an unsorted series scrambles the exact pattern it…, `== NaN` is False for every row -- the bug already fixed in clv_portfolio.…, CLV-only review is still valid -- not every recorded bet carries a settled… (+27 more)

### Community 77 - "MatchResult"
Cohesion: 0.14
Nodes (35): pull_historical_mainline_snapshot(), One historical mainline snapshot (nearest available <= `date`) for one event --…, build_team_name_map(), DataFrame, full team name -> abbreviation, restricted to abbrs used in `schedule`., build_schedule_index(), event_to_snapshots(), match_event() (+27 more)

### Community 78 - "test_props_budget.py"
Cohesion: 0.15
Nodes (26): decide_props_poll(), EventPollState, Should this specific event be polled right now, and if so, for which markets?…, Not a scheduling bug: the dense tier keeps firing inside the arb window, so a…, The 15-min tier must capture yardage-line movement, while ARB_MARKETS itself…, Bare PollTargets at the given hours -- tests here exercise the scheduling walk,…, A cheap arb poll must stay affordable when an expensive full poll would not --…, Props for the 2026-09-09 opener posted 17 days ahead; the old 5-day window… (+18 more)

### Community 79 - "PointInTimeStore"
Cohesion: 0.14
Nodes (32): PointInTimeStore, _prop(), OddsSnapshot, Regression guard: if `_filter` is ever changed to stop filtering, read_as_of…, Regression guard: a schema addition (player_name/prop_stat, added for player…, Nothing is mutated -- dedupe is a read-time view, not a deletion., Real case: Khalil Herbert receptions 1.5 at betonlineag carried -119 AND -125…, **Regression guard for a real analysis error (2026-08-23).** One player can… (+24 more)

### Community 80 - "test_evaluation.py"
Cohesion: 0.15
Nodes (24): evaluate_at_threshold(), Metrics for the subset of `bets` whose edge clears `threshold`. `bets` needs…, _bets(), **Acceptance test.** `props_ev_backtest` found no detectable edge on real 2024…, Four bets at a huge price that all happened to win: positive ROI, but nothing…, Monotonicity is a disqualifier when measurable -- a strong-looking result that…, At +200 with a fair 1/3, the listed side is zero EV and the opposite side at…, A vig'd 'probability' pair sums > 1 and individual legs can exceed 1; accepting… (+16 more)

### Community 81 - "test_migrate_props_poll_state.py"
Cohesion: 0.18
Nodes (13): migrate_poll_count(), Map an index on `old_targets` to the index on `new_targets` pointing at the…, `poll_count` is an index into a grid, so changing the grid moves every in-…, The whole point: an event keeps its position in TIME, not its ordinal., Only the arb tier's spacing changed, so an event still in the early, sparse or…, Mapping a completed schedule back onto a real target would re-open it and re-…, DEN@KC on 2026-09-14: index 44 meant 5.5h before kickoff on the old grid and…, A migrated index must not point FURTHER from kickoff than the old one -- that… (+5 more)

### Community 82 - "middle_scan.py"
Cohesion: 0.20
Nodes (13): cached_residual_stds(), fit_residual_stds(), Path, Middle-scan entrypoint: `python -m src.backtest.middle_scan`. A manual, run-by-…, `fit_residual_stds()` memoized in-process and on disk. The uncached fit reads…, (sigma_margin, sigma_total) for LIVE pricing -- not the research evaluation…, Identifies the exact training inputs a cached sigma was fitted on, so the cache…, _training_data_fingerprint() (+5 more)

### Community 83 - "load_config"
Cohesion: 0.24
Nodes (11): load_config(), Collector configuration. Everything The Odds API's free-tier budget forces us…, Build a Config from environment variables (or an injected mapping for tests).…, `load_config` key selection and budget-period defaults. Untested before…, The error must say which key is missing -- pointing at ODDS_API_KEY when the…, test_defaults_to_the_free_key_and_rolling_period(), test_explicit_env_overrides_beat_the_paid_key_defaults(), test_missing_paid_key_names_the_paid_variable_in_the_error() (+3 more)

### Community 84 - "test_clv_line_adjust.py"
Cohesion: 0.08
Nodes (39): latest_fair_prob(), Fair probability for `side`, devigged from `book`'s most recent two-sided quote…, implied_mean(), Translating a fair probability from one spread/total line to another. **The gap…, The mean of the Normal the market implies, given `fair_prob` for this (market,…, `fair_prob`, quoted for (market, side, `from_line`), restated as the fair…, translate_fair_prob(), _moving_line_store() (+31 more)

### Community 85 - "test_collect_budget.py"
Cohesion: 0.11
Nodes (29): current_period_end(), parse_quota_headers(), date, QuotaState, When the current credit quota refills. Two modes, because this project's two…, _decide(), The old uniform pacer flattened dense and sparse to the SAME interval whenever…, The paid key refills at 00:00 UTC on the 1st -- confirmed from the 2026-08-31… (+21 more)

### Community 86 - "test_props_scan.py"
Cohesion: 0.05
Nodes (78): find_arbitrage_spots(), find_prop_ev_spots(), pinnacle_fair_probs(), DataFrame, Timedelta, Cross-book player-prop strategies that don't rely on market timing: (1) a…, One row per (event, player, prop_stat, line, side, book) where `book`'s price…, One row per (event, player, prop_stat, line, capture_time) where the best… (+70 more)

### Community 87 - "OddsSnapshot"
Cohesion: 0.10
Nodes (29): fixture, _to_snapshot(), OddsSnapshot, BaseModel, datetime, Enum, Point-in-time odds snapshot schema. One row = one price, for one side, at one…, Build a snapshot from an American price, deriving decimal + implied prob. (+21 more)

### Community 88 - "budget.py"
Cohesion: 0.19
Nodes (16): decide_poll(), _dense_minutes_remaining(), _game_interval_minutes(), _minutes_since(), _nearest_upcoming_hours(), PollDecision, datetime, Budget-aware polling cadence. The Odds API bills `regions x markets` credits… (+8 more)

### Community 89 - "run"
Cohesion: 0.14
Nodes (25): AlertRecord, _alert_batch(), main(), Path, Series, Live +EV monitor entrypoint: `python -m src.notify.monitor_run`. Meant to be…, Dedup -> format -> send one class of alert. Shared by all three signals so they…, One scan-and-alert cycle across all five signals. Returns the number of alerts… (+17 more)

### Community 90 - "test_margin_total.py"
Cohesion: 0.33
Nodes (15): build_margin_total_frame(), `build_training_frame()`'s output plus spread/total regression targets and…, _pbp_fixture(), _plays(), DataFrame, _schedule_fixture(), _synthetic_margin_total_frame(), test_build_margin_total_frame_computes_margin_and_total() (+7 more)

### Community 91 - "test_train.py"
Cohesion: 0.20
Nodes (19): HistGradientBoostingClassifier, Protocol, fit_gbm_model(), fit_win_probability_model(), predict_home_win_proba(), _ProbaClassifier, DataFrame, ndarray (+11 more)

### Community 92 - "evaluation.py"
Cohesion: 0.14
Nodes (20): DataFrame, ndarray, evaluate_strategy(), evaluate_threshold_sweep(), random_bet_benchmark(), Betting-evaluation harness: is an edge *bettable*, not merely calibrated? **Why…, The whole curve, one row per threshold -- never just the best cell. Read…, Does `metric` hold up as the threshold tightens? A real edge should not… (+12 more)

### Community 93 - "prereg_score.py"
Cohesion: 0.10
Nodes (36): Path, PointInTimeStore, Series, BlindedError, check_blind(), _ev_bucket_roi(), _fmt(), format_results() (+28 more)

### Community 94 - "engine.py"
Cohesion: 0.14
Nodes (17): _latest_price(), _market_rows(), _parse_kickoffs(), payout_for(), DataFrame, datetime, Market, Outcome (+9 more)

### Community 95 - "calibration.py"
Cohesion: 0.13
Nodes (25): CalibratedClassifierCV, compare_to_baseline(), fit_calibrated_model(), fit_residual_std(), predict_calibrated_proba(), predict_over_proba(), predict_over_proba_empirical(), DataFrame (+17 more)

### Community 96 - "elo_win_probability"
Cohesion: 0.29
Nodes (7): elo_win_probability(), Standard Elo logistic transform: P(a beats b), with `a` treated as the side…, test_400_point_gap_is_the_classic_10_to_1_elo_property(), test_equal_ratings_no_hfa_is_a_coin_flip(), test_home_field_advantage_shifts_probability_toward_home(), test_base_pressure_offset_recenters_expectation_to_the_measured_base_rate(), test_base_pressure_offset_recenters_expectation_to_the_measured_base_rate()

### Community 97 - "BacktestEngine"
Cohesion: 0.26
Nodes (20): BacktestEngine, BetOrder, DecisionPoint, Replays a strategy against the real point-in-time store. **Bankroll is a hard,…, What a strategy sees when it's given a chance to act. `visible_snapshots` is…, A strategy's decision to bet, returned from a Strategy callable. None means "no…, _always_bet_home_spread(), _never_bet() (+12 more)

### Community 98 - "test_drift_monitor.py"
Cohesion: 0.16
Nodes (20): _detect_decay(), Has CLV shifted *downward* from this strategy's OWN established baseline? Two…, cusum(), first_flag_index(), ndarray, Non-stationarity / drift monitor (blueprint Part E, "the genuinely hard part").…, Index of the first True in `flagged`, or None if it never fires., Trailing rolling mean CLV, one value per bet. Uses whatever history exists so… (+12 more)

### Community 99 - "Pre-registration — 2026 Weeks 5–9 holdout"
Cohesion: 0.13
Nodes (14): 1. Why this exists, 2. Data split, 3. Common evaluation protocol (applies to every hypothesis), 4. Hypotheses, 5. Not registered (and why), 6. Deviations log, 7. Build order (Train phase, 10-05 → 10-07), Exploration already done (disclosed, because it shaped the hypotheses) (+6 more)

### Community 100 - "audit_integration.py"
Cohesion: 0.21
Nodes (16): check_architecture_md(), classify(), main(), _make_entrypoints(), _module_graph(), _notebook_entrypoints(), Path, Which src/ modules are actually reachable, and from what? **Why this exists.**… (+8 more)

### Community 101 - "test_live_scan.py"
Cohesion: 0.14
Nodes (25): event_id_from_alert_key(), find_positive_ev_spots(), prune_alert_state(), datetime, Timedelta, One row per (event, side, book) where `book`'s latest moneyline price beats…, The event a dedup key refers to, across all three key shapes in use:…, Drop dedup entries whose event has already started. Sentinels are always kept;… (+17 more)

### Community 102 - "test_prereg_scan.py"
Cohesion: 0.12
Nodes (24): find_spots(), FrozenStrategy, live_props(), prereg_key(), DataFrame, datetime, Path, PointInTimeStore (+16 more)

### Community 103 - "test_decision_report.py"
Cohesion: 0.15
Nodes (14): _directional_verdict(), _structural_verdict(), The verdict logic is the part that decides where real money goes, so it is…, 0.25h poll spacing + 300s monitor interval = ~20 min worst case; the default…, `moneyline_ev` cleared the bar on 2026-09-21 with mean_clv +0.0053 and a CI of…, A small sample is not evidence of failure. Collapsing HOLD into NO would retire…, Pinned so a later session cannot quietly tune the bar to whatever the season…, The regression that matters: an arb with terrible CLV but a capturable lock… (+6 more)

### Community 104 - "PropsCollectorState"
Cohesion: 0.29
Nodes (9): main(), load_state(), PropsCollectorState, Path, Persisted to disk between process restarts (default:…, save_state(), test_load_state_with_no_file_returns_empty_state(), test_state_persists_to_disk_and_reloads() (+1 more)

### Community 105 - "test_shadow_log.py"
Cohesion: 0.08
Nodes (69): Any, append(), _decimal(), _latest_price(), legs_from_spot(), load(), main(), _market_of() (+61 more)

### Community 106 - "test_correlated_props.py"
Cohesion: 0.22
Nodes (15): correlated_edge(), estimate_game_specific_joint_prob(), naive_parlay_price(), Game-specific estimate of P(A and B), for pricing one particular upcoming game…, Decimal price a same-game parlay would carry if a book priced it by multiplying…, The bettor-relevant number this module exists to produce: if a book prices a…, test_correlated_edge_gives_no_stake_when_legs_are_actually_independent(), test_correlated_edge_gives_positive_ev_when_true_prob_exceeds_naive_implied() (+7 more)

### Community 107 - "Train-phase results — 2026-10-04"
Cohesion: 0.17
Nodes (11): 1. Gate: is Pinnacle's prop close calibrated?, 2. Gate: is Pinnacle's moneyline close calibrated?, 3. Does "price beats Pinnacle" turn into money? (historical, realized), 4. Live 2026 alerts on closing EV (shadow log, Weeks 1–4), 5. H1 — stale soft line after a Pinnacle move, 6. H3 — prop middles: calibration gate FAIL, 7. H2 — team-total (exploratory; contract undecided), 8. Not computed (+3 more)

### Community 108 - "shadow_clv.py"
Cohesion: 0.19
Nodes (16): format_summary(), main(), DataFrame, datetime, Path, CLV for alerts that were never bet. **The gap this closes.** CLV is computed in…, Shadow alerts enriched with entry/closing fair probabilities and CLV. Output is…, `shadow_clv` as a frame, with `measurable` marking rows whose CLV is actually… (+8 more)

### Community 109 - "measure_prop_vig"
Cohesion: 0.14
Nodes (17): measure_prop_vig(), DataFrame, Re-derive `MEASURED_PROP_VIG` from raw prop snapshots. **This exists because…, _prop_row(), One two-sided prop contract at a given pair of American prices., -110/-110 is 4.76% overround by construction. If this drifts, the constant's…, The constant is `sum(q)-1`, matching devig's own `overround()`. Hold would be…, They differ materially on real data (6.29% vs 6.88% on the same 16,953 Pinnacle… (+9 more)

### Community 110 - "test_collect_scheduler.py"
Cohesion: 0.26
Nodes (20): main(), build_scheduler(), CollectorContext, CollectorHalted, BlockingScheduler, RuntimeError, Raised when consecutive failures exceed the configured limit., Wraps _tick(ctx) so one unexpected bug in a single poll never kills a long-… (+12 more)

### Community 111 - "market_baseline"
Cohesion: 0.39
Nodes (6): market_baseline(), Market baseline (blueprint Part E). "Your baseline is the devigged Pinnacle…, Fair probability for the side at `side_index`, from Pinnacle's raw American…, test_default_method_is_shin(), test_side_index_selects_the_right_side(), test_symmetric_market_gives_half_regardless_of_method()

### Community 112 - "decision_table"
Cohesion: 0.20
Nodes (11): _ci(), _decimal(), decision_table(), first_recheck_frame(), main(), datetime, ndarray, Path (+3 more)

### Community 113 - "season_review.py"
Cohesion: 0.14
Nodes (16): _clv_series(), format_review_summary(), main(), DataFrame, ndarray, In-season strategy review: is each live strategy still working, and when should…, Human-readable digest, ordered so anything needing action is first -- this is…, Weekly in-season health check over the LIVE bet log. Segments on `strategy`… (+8 more)

### Community 114 - "datetime"
Cohesion: 0.18
Nodes (8): datetime, RuntimeError, kickoffs_from_store(), LeakageError, The only read path. Returns rows visible at `decision_time`, and nothing later.…, The whole store, deduped, read from disk only when the file listing has changed…, event_id -> kickoff, from the store's own `event_start_time`. Lives here rather…, Raised if a query would return (or returned) data from after decision_time.

### Community 117 - "decision_report.py"
Cohesion: 0.19
Nodes (15): ci_includes_zero(), format_table(), _missing(), _pct(), The go/no-go table: what do I bet at the end of September, and on what…, Does the CLV confidence interval straddle zero? **This is deliberately NOT part…, None and NaN both mean "not measured" here. They must render identically: a…, The table as text, carrying its own caveats. Every `n/a` is explained inline. A… (+7 more)

### Community 119 - "compute_qb_elo_ratings"
Cohesion: 0.33
Nodes (10): compute_qb_elo_ratings(), DataFrame, QB-level Elo: a residual rating crediting individual quarterback performance…, One row per game: each starting QB's Elo rating *entering* that game (pre-game,…, _schedule(), test_backup_qb_starts_are_tracked_as_a_distinct_rating_from_the_starter(), test_first_start_for_every_qb_begins_at_initial_rating(), test_qb_rating_carries_across_games_not_reset() (+2 more)

### Community 125 - "_coinflip_bets"
Cohesion: 0.22
Nodes (9): _coinflip_bets(), A strategy with no real selection skill should not stand out against randomly…, The negative control for the acceptance test above: a harness that always says…, n bets on true 50/50 events at a fixed price, with a controlled realized win…, test_detects_a_real_edge_when_one_actually_exists(), test_random_benchmark_flags_a_genuinely_strong_result(), test_random_benchmark_p_value_is_the_complement_of_the_percentile(), test_random_benchmark_places_a_fair_coinflip_strategy_mid_distribution() (+1 more)

### Community 127 - "compare_to_book"
Cohesion: 0.40
Nodes (5): compare_to_book(), Forecast-quality comparison: model vs. book on the same events. Necessary but…, These are different questions and the API keeps them apart -- a model can win…, test_beating_the_book_on_brier_is_reported_separately_from_bettability(), test_compare_to_book_reports_both_sides_and_who_wins()

### Community 128 - "pit_store.py"
Cohesion: 0.16
Nodes (15): CollectorContext, Config, build_context(), main(), Entrypoint: `python -m src.collect.props_run [--once]`. Live player-prop…, build_scheduler(), PropsCollectorContext, BlockingScheduler (+7 more)

### Community 130 - "team_total_scan.py"
Cohesion: 0.15
Nodes (20): Drop snapshots for games that have already kicked off -- only a future game is…, upcoming_only(), available_stats(), format_team_total_alert(), main(), measured_vig_by_event(), DataFrame, datetime (+12 more)

### Community 131 - "props_budget.py"
Cohesion: 0.13
Nodes (22): _build_targets(), One-off migration: re-index `data/props_collect_state.json` onto a changed poll…, `props_budget.build_poll_targets` with the arb spacing made a parameter, so the…, arb_poll_targets_hours(), build_poll_targets(), dense_poll_targets_hours(), early_poll_targets_hours(), PollTarget (+14 more)

### Community 132 - "build_team_game_outcomes"
Cohesion: 0.40
Nodes (11): build_team_game_outcomes(), One row per team per game, home and away pooled (2x the game count, each team's…, _player_stats_fixture(), _schedule_fixture(), test_game_over_is_shared_across_both_perspectives(), test_leading_receiver_and_rusher_thresholds(), test_qb_2plus_tds_uses_the_schedules_starting_qb_not_most_active_passer(), test_team_covers_uses_each_teams_own_line_perspective() (+3 more)

### Community 133 - "price_bucket_bet"
Cohesion: 0.24
Nodes (11): is_bucket_validated(), price_bucket_bet(), Whether `bucket` (one of `FAVORITE_BUCKETS`' labels) has survived an honest…, Raised by `price_bucket_bet` when asked to price a favorite/ heavy_favorite…, The one real pricing entrypoint any future live correlated-props scanner should…, UnvalidatedBucketError, test_is_bucket_validated_matches_the_validated_set(), test_price_bucket_bet_allows_unvalidated_when_explicitly_requested() (+3 more)

### Community 134 - "test_steam_scan.py"
Cohesion: 0.28
Nodes (11): main(), DataFrame, Steam-scan entrypoint: `python -m src.backtest.steam_scan`. Manual, run-by-…, One scan. Returns the report DataFrame (also logged); never sends any…, run(), _seed_store_with_real_steam(), _snapshot(), test_run_filters_out_spots_below_min_ev() (+3 more)

### Community 137 - "measure_leg_correlation"
Cohesion: 0.20
Nodes (11): measure_leg_correlation(), measure_leg_correlation_by_bucket(), Series, `indicator_a`/`indicator_b`: aligned boolean/0-1 Series, one row per game (or…, `measure_leg_correlation`, stratified by favorite strength -- see…, test_independent_legs_give_a_lift_near_one(), test_measure_leg_correlation_by_bucket_splits_by_market_prob(), test_negatively_correlated_legs_give_a_lift_below_one() (+3 more)

### Community 138 - "scheduler.py"
Cohesion: 0.38
Nodes (5): Config, Path, _bootstrap_state(), datetime, Scheduler wiring: one `tick()` per poll opportunity, run on an interval.…

### Community 139 - "test_middle_scan.py"
Cohesion: 0.33
Nodes (10): main(), DataFrame, One scan. Returns the report DataFrame (also logged); never sends any…, run(), _seed_store_with_real_movement(), _snapshot(), test_run_filters_out_windows_below_min_ev(), test_run_finds_and_logs_a_real_middle() (+2 more)

### Community 140 - "bucket_edge"
Cohesion: 0.20
Nodes (10): bucket_edge(), Closed-form edge for one `FAVORITE_BUCKETS` bucket, under this module's…, **Inverted 2026-08-23.** This used to assert that vig DEFAULTED to…, Squared term: a 1.5pp vig understatement is roughly a 3pp edge error. This is…, test_bucket_edge_is_independent_of_market_probability(), test_bucket_edge_is_sensitive_to_the_vig_it_is_given(), test_bucket_edge_matches_correlated_edge_when_unclipped(), test_bucket_edge_requires_an_explicit_vig() (+2 more)

### Community 141 - "build_training_frame"
Cohesion: 0.38
Nodes (10): build_training_frame(), One row per game: `build_game_features()` output plus the home-win label and…, _pbp_fixture(), _plays(), DataFrame, _schedule_fixture(), test_build_training_frame_drops_rows_elo_ratings_does_not_cover(), test_build_training_frame_drops_ties_and_first_week_rows() (+2 more)

### Community 142 - "realistic_season_credit_cost"
Cohesion: 0.33
Nodes (7): **Worst case** credits to poll `n_games` at this schedule: every poll returns…, A planning estimate that accounts for two measured facts the worst case…, realistic_season_credit_cost(), season_credit_cost(), The worst case assumes every early probe returns data at full price. It cannot…, test_early_probes_dominate_the_gap_between_worst_and_realistic_cost(), test_realistic_season_cost_fits_the_monthly_cap_and_worst_case_is_labelled_unreachable()

### Community 143 - "h1_train_grid.py"
Cohesion: 0.60
Nodes (4): cell(), main(), Reproduce the H1 / H1b Train numbers that froze M=2pp, E=1%.…, train_props()

### Community 144 - "bucket_favorite_strength"
Cohesion: 0.50
Nodes (4): bucket_favorite_strength(), Which `FAVORITE_BUCKETS` bucket a team's real market-implied win probability…, test_bucket_favorite_strength_classifies_correctly(), test_bucket_favorite_strength_rejects_out_of_range()

## Knowledge Gaps
- **201 isolated node(s):** `1. What is actually running right now`, `2. Layer map`, `store/ — foundation (all LIVE)`, `collect/ — data acquisition`, `model/ — feature/rating layer (trains ONLY on free nflverse data)` (+196 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **22 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PointInTimeStore` connect `PointInTimeStore` to `pit_store.py`, `test_bet_log.py`, `team_total_scan.py`, `OddsApiResponse`, `test_closing_line.py`, `props.py`, `test_steam_scan.py`, `Side`, `scheduler.py`, `test_middle_scan.py`, `live_scan.py`, `test_middling.py`, `test_movement_scan.py`, `test_clv_data_path.py`, `test_steam.py`, `mainline_historical.py`, `OddsApiError`, `test_clv_metrics.py`, `test_health_check.py`, `demo_pipeline.py`, `test_engine_props.py`, `test_team_total_scan.py`, `middle_scan.py`, `test_clv_line_adjust.py`, `test_props_scan.py`, `OddsSnapshot`, `run`, `prereg_score.py`, `BacktestEngine`, `test_live_scan.py`, `test_shadow_log.py`, `shadow_clv.py`, `test_collect_scheduler.py`, `decision_table`, `season_review.py`, `datetime`, `decision_report.py`?**
  _High betweenness centrality (0.223) - this node is a cross-community bridge._
- **Why does `Side` connect `Side` to `test_bet_log.py`, `test_closing_line.py`, `props.py`, `test_steam_scan.py`, `test_middle_scan.py`, `test_middling.py`, `test_synthetic_market.py`, `test_movement_scan.py`, `test_team_total_props.py`, `test_clv_data_path.py`, `test_steam.py`, `test_clv_portfolio.py`, `test_health_check.py`, `demo_pipeline.py`, `test_team_total_scan.py`, `MatchResult`, `test_clv_line_adjust.py`, `test_props_scan.py`, `OddsSnapshot`, `run`, `test_live_scan.py`, `test_decision_report.py`, `test_shadow_log.py`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Why does `Market` connect `Side` to `test_closing_line.py`, `props.py`, `test_steam_scan.py`, `test_middle_scan.py`, `test_middling.py`, `test_synthetic_market.py`, `test_movement_scan.py`, `test_team_total_props.py`, `test_clv_data_path.py`, `test_steam.py`, `test_clv_portfolio.py`, `test_health_check.py`, `demo_pipeline.py`, `test_team_total_scan.py`, `MatchResult`, `test_clv_line_adjust.py`, `test_props_scan.py`, `OddsSnapshot`, `run`, `test_live_scan.py`, `test_decision_report.py`, `test_shadow_log.py`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Are the 136 inferred relationships involving `PointInTimeStore` (e.g. with `main()` and `run()`) actually correct?**
  _`PointInTimeStore` has 136 INFERRED edges - model-reasoned connections that need verification._
- **Are the 151 inferred relationships involving `Side` (e.g. with `_best_line()` and `best_middle_for_game()`) actually correct?**
  _`Side` has 151 INFERRED edges - model-reasoned connections that need verification._
- **Are the 141 inferred relationships involving `Market` (e.g. with `best_middle_for_game()` and `find_middle_opportunities()`) actually correct?**
  _`Market` has 141 INFERRED edges - model-reasoned connections that need verification._
- **Are the 38 inferred relationships involving `OddsSnapshot` (e.g. with `simulate_market()` and `_to_snapshot()`) actually correct?**
  _`OddsSnapshot` has 38 INFERRED edges - model-reasoned connections that need verification._