# Graph Report - nfl_2026  (2026-10-13)

## Corpus Check
- 174 files · ~183,432 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2732 nodes · 6935 edges · 131 communities (115 shown, 16 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 807 edges (avg confidence: 0.53)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0bc8f5d2`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Market
- test_bet_log.py
- test_evaluate.py
- test_props_scheduler.py
- test_closing_line.py
- test_collect_props.py
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
- test_sizing.py
- Methodology backlog
- OddsSnapshot
- test_shadow_log.py
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
- OddsApiResponse
- test_steam.py
- test_pass_rush_elo.py
- backfill_historical_mainline
- OddsApiClient
- DataFrame
- test_clv_metrics.py
- test_parlay.py
- test_prop_settlement.py
- shadow_log.py
- test_clv_portfolio.py
- compute_receiver_elo_ratings
- Architecture & Status Audit
- test_health_check.py
- demo_pipeline.py
- engine.py
- bet_log.py
- load_static.py
- test_team_total_scan.py
- review_strategy
- test_collect_transform.py
- test_props_budget.py
- PointInTimeStore
- test_evaluation.py
- test_migrate_props_poll_state.py
- middle_scan.py
- load_config
- test_clv_line_adjust.py
- test_collect_budget.py
- test_props_ev_backtest.py
- Side
- win_interval
- run
- test_margin_total.py
- test_train.py
- evaluation.py
- props_budget.py
- active_bets
- calibration.py
- elo_win_probability
- steam.py
- test_drift_monitor.py
- Pre-registration — 2026 Weeks 5–9 holdout
- audit_integration.py
- test_live_scan.py
- test_prereg_scan.py
- to_backtest_bets
- PropsCollectorState
- record_alert
- prop_alert_key
- Train-phase results — 2026-10-04
- test_props_scan.py
- test_correlated_props.py
- scheduler.py
- market_baseline
- _apply_exposure_cap
- season_review.py
- .read_as_of
- build_training_frame
- RuntimeError
- test_decision_report.py
- date
- compute_qb_elo_ratings
- BaseModel
- field_validator
- model_validator
- team_total_scan.py
- parametrize
- _coinflip_bets
- _kickoff_for
- compare_to_book
- test_monotonicity_check_ignores_thin_tail_rows
- PollTarget
- test_steam_scan.py

## God Nodes (most connected - your core abstractions)
1. `PointInTimeStore` - 209 edges
2. `Side` - 193 edges
3. `Market` - 182 edges
4. `OddsSnapshot` - 74 edges
5. `OddsApiClient` - 47 edges
6. `run()` - 46 edges
7. `OddsApiResponse` - 32 edges
8. `MatchResult` - 30 edges
9. `to_backtest_bets()` - 30 edges
10. `settle()` - 29 edges

## Surprising Connections (you probably didn't know these)
- `test_build_frame_inner_joins_and_drops_games_without_a_close()` --uses--> `Side`  [INFERRED]
  tests/test_closing_line.py → src/store/schema.py
- `test_duplicate_snapshots_do_not_silently_drop_a_game()` --uses--> `Side`  [INFERRED]
  tests/test_closing_line.py → src/store/schema.py
- `test_extracts_devigged_closing_probability()` --uses--> `Side`  [INFERRED]
  tests/test_closing_line.py → src/store/schema.py
- `test_games_with_no_close_are_omitted_not_imputed()` --uses--> `Side`  [INFERRED]
  tests/test_closing_line.py → src/store/schema.py
- `test_one_sided_quote_is_omitted_rather_than_devigged_wrongly()` --uses--> `Side`  [INFERRED]
  tests/test_closing_line.py → src/store/schema.py

## Import Cycles
- None detected.

## Communities (131 total, 16 thin omitted)

### Community 0 - "Market"
Cohesion: 0.15
Nodes (36): Market, build_results_index(), GameResult, Outcome, _outcome_from_margin(), DataFrame, Enum, str (+28 more)

### Community 1 - "test_bet_log.py"
Cohesion: 0.15
Nodes (32): _as_backtest(), _bet(), _ml(), The whole point: entry price is recorded, everything else is derived. Pinnacle…, Pinnacle does not quote props until close to kickoff. An unmeasurable bet must…, season_review segments on strategy, and props need player/stat/line to identify…, NFL ties are real -- ~1 a season. Folding one into a loss understates the…, An unplayed game must leave the bankroll untouched. Grading it as a loss would… (+24 more)

### Community 2 - "test_evaluate.py"
Cohesion: 0.12
Nodes (27): brier_score(), log_loss(), power_analysis(), DataFrame, ndarray, Model evaluation (blueprint Part B.5). "This section is where you prove you are…, mean((p - y)^2). Lower is better., -mean(y*log(p) + (1-y)*log(1-p)). p is clipped away from exactly 0/1 so a… (+19 more)

### Community 3 - "test_props_scheduler.py"
Cohesion: 0.26
Nodes (19): datetime, Wraps _tick(ctx) so one unexpected bug never kills a long-running process --…, tick(), _ctx(), _event(), _prop_event_odds(), **The fix that makes a 21-day posting window safe.** Probing a game whose props…, **Dry-run finding, 2026-08-23.** Both paths were reported as one `skipped`… (+11 more)

### Community 4 - "test_closing_line.py"
Cohesion: 0.12
Nodes (36): build_closing_line_frame(), closing_fair_probabilities(), evaluate_closing_line_model(), fit_closing_line_model(), predict_closing_prob(), DataFrame, ndarray, Pipeline (+28 more)

### Community 5 - "test_collect_props.py"
Cohesion: 0.15
Nodes (23): event_odds_to_prop_snapshots(), main(), poll_all_props(), datetime, ScheduleIndex, `events`: iterable of (odds_api_event_id, home_team_name, away_team_name) --…, Events worth spending a per-event call on: **strictly before kickoff**, and…, Manual entrypoint: `python -m src.collect.props`. See module docstring -- not… (+15 more)

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
Cohesion: 0.22
Nodes (15): AlertRecord, _latest_two_sided_pinnacle(), load_alert_state(), new_or_improved_spots(), DataFrame, datetime, Path, Series (+7 more)

### Community 36 - "test_middling.py"
Cohesion: 0.09
Nodes (47): _best_line(), best_middle_for_game(), find_middle_opportunities(), _interval_prob(), middle_ev(), MiddleOpportunity, pinnacle_reference_line(), DataFrame (+39 more)

### Community 37 - "test_synthetic_market.py"
Cohesion: 0.07
Nodes (53): _logit(), datetime, ndarray, timedelta, Synthetic market simulator -- validates this project's OWN CLV-measurement code…, Ground truth for one simulated player-prop contract. `over_hit` is the realized…, Ground truth for one simulated game -- what `simulate_market` actually…, `n_games` synthetic games, each with its own independently-drawn latent price… (+45 more)

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
Nodes (32): find_live_middle_spots(), find_live_steam_spots(), format_middle_alert_message(), format_steam_alert_message(), middle_alert_key(), DataFrame, datetime, Series (+24 more)

### Community 42 - "test_sizing.py"
Cohesion: 0.16
Nodes (22): apply_bankroll_caps(), fractional_kelly(), kelly_fraction(), Expected value and Kelly bet sizing (blueprint Part B.4). Full Kelly is too…, Full Kelly fraction of bankroll. Can be negative when the price is bad at this…, k * full Kelly. k in [0.25, 0.5] per the blueprint; default 0.375 is the…, Clip a dollar stake to [min_bet, min(max_bet, bankroll)]. Below min_bet --…, _validate() (+14 more)

### Community 43 - "Methodology backlog"
Cohesion: 0.04
Nodes (48): 10. High-vig markets — **checked, hypothesis reframed, anytime-TD confirmed unpriceable**, 1. It priced with the TRAIN fit, the highest of three available estimates, 1. Rest/travel differential — **tested, negative result**, 2. Joint margin/total correlated distribution — **checked, premise doesn't hold**, 2. The constants had NO producing code anywhere in the repo, 3. Steam detection — **built and live-validated**, 3. The player lines never entered the price, 4. Player-prop middling — idea, blocked on live props posting (+40 more)

### Community 44 - "OddsSnapshot"
Cohesion: 0.12
Nodes (30): pull_historical_mainline_snapshot(), _pull_with_credits(), Historical mainline (h2h/spreads/totals) odds backfill. **The rigor fix from…, One snapshot plus THIS call's own billed cost, so the caller can enforce a…, One historical mainline snapshot (nearest available <= `date`) for one event --…, Historical player-prop odds backfill for backtesting. **Blocked on paid…, poll_event_props(), Player-prop odds collection. **Prepped, not active.** Live-checked 2026-08-17… (+22 more)

### Community 45 - "test_shadow_log.py"
Cohesion: 0.14
Nodes (25): Any, _alert_key(), legs_from_spot(), _market_of(), Series, The row's own market when it reports one, else moneyline. Middling and steam…, Split one scanner row into its leg(s). Arb rows carry `book_over`/`book_under`…, _middle_row() (+17 more)

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
Cohesion: 0.12
Nodes (32): format_summary(), main(), DataFrame, datetime, Path, CLV for alerts that were never bet. **The gap this closes.** CLV is computed in…, Shadow alerts enriched with entry/closing fair probabilities and CLV. Output is…, `shadow_clv` as a frame, with `measurable` marking rows whose CLV is actually… (+24 more)

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
Cohesion: 0.26
Nodes (15): OddsApiResponse, backfill_historical_props(), find_historical_event_id(), pull_historical_prop_snapshot(), datetime, `games`: iterable of (match, home_name, away_name, kickoff) --…, 1 credit. Looks up the historical events list as of `date` and returns the Odds…, One historical snapshot (nearest available <= `date`) for one or more markets… (+7 more)

### Community 58 - "test_steam.py"
Cohesion: 0.11
Nodes (34): book_moves(), BookMove, detect_steam_move(), find_steam_opportunities(), _largest_time_cluster(), DataFrame, Timedelta, A real, detected steam move: `min_books` or more books moved the same direction… (+26 more)

### Community 59 - "test_pass_rush_elo.py"
Cohesion: 0.22
Nodes (17): compute_pass_rush_elo_ratings(), credited_pressure_counts(), DataFrame, Pass-rush Elo: a play-level, team-level rating of pass-rush vs. pass-protection…, Raw per-player counts of sacks (full credit), half-sacks (0.5 credit), and QB…, One row per dropback: `posteam`'s pass-protection Elo and `defteam`'s pass-rush…, _pbp(), test_clean_pocket_lowers_rush_elo_and_raises_protection_elo() (+9 more)

### Community 60 - "backfill_historical_mainline"
Cohesion: 0.12
Nodes (26): backfill_historical_mainline(), estimate_pull_cost(), _iso_z(), main(), datetime, Credits a pull will cost, before spending any. One event-id lookup per game (1…, `games`: iterable of (match, home_name, away_name, kickoff) -- same shape as…, The API wants a Z-suffixed UTC instant, not a +00:00 offset. (+18 more)

### Community 61 - "OddsApiClient"
Cohesion: 0.09
Nodes (36): parametrize, Response, RuntimeError, Session, OddsApiClient, OddsApiError, _parse_int_header(), _parse_iso() (+28 more)

### Community 63 - "test_clv_metrics.py"
Cohesion: 0.10
Nodes (31): _home_fair(), main(), DataFrame, Does the line actually move toward truth? Real 2024 historical movement. **Two…, beat_rate(), bootstrap_ci(), clustered_bootstrap(), clv_price() (+23 more)

### Community 64 - "test_parlay.py"
Cohesion: 0.14
Nodes (28): parlay_ev(), parlay_independent_probability(), parlay_price_decimal(), parlay_true_probability(), ParlayLeg, Parlay pricing and EV -- multi-leg bets, priced against REAL leg prices. **Why…, Correlation-adjusted joint win probability: the independent product scaled by…, Full EV/sizing for one parlay, reusing `src/signal/sizing.py`'s… (+20 more)

### Community 65 - "test_prop_settlement.py"
Cohesion: 0.06
Nodes (63): DataFrame, Outcome, build_team_outcomes(), build_team_total_lines(), fit_team_total_lift_by_bucket(), fit_team_total_residual_std(), DataFrame, Series (+55 more)

### Community 66 - "shadow_log.py"
Cohesion: 0.14
Nodes (21): append(), _decimal(), _latest_price(), load(), main(), BaseModel, DataFrame, datetime (+13 more)

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

### Community 72 - "engine.py"
Cohesion: 0.07
Nodes (65): Side, BacktestEngine, BetOrder, DecisionPoint, latest_fair_prob(), _latest_price(), _market_rows(), _parse_kickoffs() (+57 more)

### Community 73 - "bet_log.py"
Cohesion: 0.15
Nodes (18): BaseModel, field_validator, model_validator, _anchor_fair_for_bet(), _anchor_line_at(), _close_price_decimal(), _fair_at(), LoggedBet (+10 more)

### Community 74 - "load_static.py"
Cohesion: 0.09
Nodes (29): home_spread_line(), kickoffs_utc(), load_injuries(), load_pbp(), load_pfr_pass_rush_advstats(), load_player_stats(), load_players(), load_snap_counts() (+21 more)

### Community 75 - "test_team_total_scan.py"
Cohesion: 0.14
Nodes (25): format_team_total_alert(), Series, team_total_alert_key(), _ml(), _prop(), A line that has since moved is not what you'd be betting into., -110/-110 is 4.76% overround by construction -- not the 6.29% constant., -200/+170 puts the away side in the `underdog` bucket. It used to be an even… (+17 more)

### Community 76 - "review_strategy"
Cohesion: 0.11
Nodes (35): Full health check on one strategy's live bets. The recommendation is…, One review row per strategy segment. Segments rather than pools for the same…, review_all(), review_strategy(), _frame(), CUSUM is sequential -- an unsorted series scrambles the exact pattern it…, `== NaN` is False for every row -- the bug already fixed in clv_portfolio.…, CLV-only review is still valid -- not every recorded bet carries a settled… (+27 more)

### Community 77 - "test_collect_transform.py"
Cohesion: 0.13
Nodes (28): build_context(), main(), Entrypoint: `python -m src.collect.props_run [--once]`. Live player-prop…, build_scheduler(), PropsCollectorContext, BlockingScheduler, Scheduler wiring for player-prop polling -- one `tick()` per opportunity,…, build_team_name_map() (+20 more)

### Community 78 - "test_props_budget.py"
Cohesion: 0.15
Nodes (26): decide_props_poll(), EventPollState, Should this specific event be polled right now, and if so, for which markets?…, Not a scheduling bug: the dense tier keeps firing inside the arb window, so a…, The 15-min tier must capture yardage-line movement, while ARB_MARKETS itself…, Bare PollTargets at the given hours -- tests here exercise the scheduling walk,…, A cheap arb poll must stay affordable when an expensive full poll would not --…, Props for the 2026-09-09 opener posted 17 days ahead; the old 5-day window… (+18 more)

### Community 79 - "PointInTimeStore"
Cohesion: 0.16
Nodes (24): PointInTimeStore, Path, Regression guard: if `_filter` is ever changed to stop filtering, read_as_of…, Regression guard: a schema addition (player_name/prop_stat, added for player…, Nothing is mutated -- dedupe is a read-time view, not a deletion., Real case: Khalil Herbert receptions 1.5 at betonlineag carried -119 AND -125…, **Regression guard for a real analysis error (2026-08-23).** One player can…, Dedupe must never flatten a price HISTORY -- that is the whole store. (+16 more)

### Community 80 - "test_evaluation.py"
Cohesion: 0.19
Nodes (20): evaluate_at_threshold(), Metrics for the subset of `bets` whose edge clears `threshold`. `bets` needs…, _bets(), **Acceptance test.** `props_ev_backtest` found no detectable edge on real 2024…, Four bets at a huge price that all happened to win: positive ROI, but nothing…, Monotonicity is a disqualifier when measurable -- a strong-looking result that…, A vig'd 'probability' pair sums > 1 and individual legs can exceed 1; accepting…, The metric that exposes 'profitable on 4 of 900 games' as noise. (+12 more)

### Community 81 - "test_migrate_props_poll_state.py"
Cohesion: 0.18
Nodes (13): migrate_poll_count(), Map an index on `old_targets` to the index on `new_targets` pointing at the…, `poll_count` is an index into a grid, so changing the grid moves every in-…, The whole point: an event keeps its position in TIME, not its ordinal., Only the arb tier's spacing changed, so an event still in the early, sparse or…, Mapping a completed schedule back onto a real target would re-open it and re-…, DEN@KC on 2026-09-14: index 44 meant 5.5h before kickoff on the old grid and…, A migrated index must not point FURTHER from kickoff than the old one -- that… (+5 more)

### Community 82 - "middle_scan.py"
Cohesion: 0.15
Nodes (20): cached_residual_stds(), fit_residual_stds(), main(), DataFrame, Path, Middle-scan entrypoint: `python -m src.backtest.middle_scan`. A manual, run-by-…, `fit_residual_stds()` memoized in-process and on disk. The uncached fit reads…, One scan. Returns the report DataFrame (also logged); never sends any… (+12 more)

### Community 83 - "load_config"
Cohesion: 0.29
Nodes (10): load_config(), Build a Config from environment variables (or an injected mapping for tests).…, `load_config` key selection and budget-period defaults. Untested before…, The error must say which key is missing -- pointing at ODDS_API_KEY when the…, test_defaults_to_the_free_key_and_rolling_period(), test_explicit_env_overrides_beat_the_paid_key_defaults(), test_missing_paid_key_names_the_paid_variable_in_the_error(), test_non_truthy_values_stay_on_the_free_key() (+2 more)

### Community 84 - "test_clv_line_adjust.py"
Cohesion: 0.11
Nodes (27): `fair_prob`, quoted for (market, side, `from_line`), restated as the fair…, translate_fair_prob(), _moving_line_store(), CLV when the anchor's line is not the line you bet. Written 2026-09-10/11 after…, Pinnacle sits on 44.5, then moves to 44.0 and CLOSES there. FanDuel holds 44.5…, The anchor closed at 44.0 but the bet was 44.5, so the close must be the…, The exact-match regression: entry and close both resolving to the same stale…, The KeyError that broke `make clv-report`: reachable only once at least one row… (+19 more)

### Community 85 - "test_collect_budget.py"
Cohesion: 0.06
Nodes (65): CollectorState, current_period_end(), decide_poll(), _dense_minutes_remaining(), _game_interval_minutes(), key_fingerprint(), load_state(), _minutes_since() (+57 more)

### Community 86 - "test_props_ev_backtest.py"
Cohesion: 0.18
Nodes (25): find_arbitrage_spots(), find_prop_ev_spots(), pinnacle_fair_probs(), DataFrame, Timedelta, Cross-book player-prop strategies that don't rely on market timing: (1) a…, One row per (event, player, prop_stat, line, side, book) where `book`'s price…, One row per (event, player, prop_stat, line, capture_time) where the best… (+17 more)

### Community 87 - "Side"
Cohesion: 0.10
Nodes (33): fixture, middle_window(), The overlap of two opposite-side legs' win regions, or None if no real (finite,…, datetime, Enum, str, Point-in-time odds snapshot schema. One row = one price, for one side, at one…, Build a snapshot from an American price, deriving decimal + implied prob. (+25 more)

### Community 88 - "win_interval"
Cohesion: 0.12
Nodes (21): line_threshold(), The single "true outcome" value this (market, side, line) quote implies --…, (lo, hi) bounds, in "true outcome" space (home_margin for SPREAD, total_score…, win_interval(), implied_mean(), Translating a fair probability from one spread/total line to another. **The gap…, The mean of the Normal the market implies, given `fair_prob` for this (market,…, A 50% fair probability means the market's mean IS the line -- the one anchor… (+13 more)

### Community 89 - "run"
Cohesion: 0.16
Nodes (23): AlertRecord, _alert_batch(), main(), Path, Series, Live +EV monitor entrypoint: `python -m src.notify.monitor_run`. Meant to be…, Dedup -> format -> send one class of alert. Shared by all three signals so they…, One scan-and-alert cycle across all five signals. Returns the number of alerts… (+15 more)

### Community 90 - "test_margin_total.py"
Cohesion: 0.22
Nodes (21): build_margin_total_frame(), fit_margin_model(), fit_total_model(), Pipeline, `build_training_frame()`'s output plus spread/total regression targets and…, Standardized linear regression predicting `margin` (home_score - away_score) --…, Same as `fit_margin_model`, predicting `total_points` (home_score + away_score)…, _pbp_fixture() (+13 more)

### Community 91 - "test_train.py"
Cohesion: 0.20
Nodes (19): HistGradientBoostingClassifier, Protocol, fit_gbm_model(), fit_win_probability_model(), predict_home_win_proba(), _ProbaClassifier, DataFrame, ndarray (+11 more)

### Community 92 - "evaluation.py"
Cohesion: 0.15
Nodes (19): evaluate_strategy(), evaluate_threshold_sweep(), DataFrame, ndarray, random_bet_benchmark(), Betting-evaluation harness: is an edge *bettable*, not merely calibrated? **Why…, The whole curve, one row per threshold -- never just the best cell. Read…, Does `metric` hold up as the threshold tightens? A real edge should not… (+11 more)

### Community 93 - "props_budget.py"
Cohesion: 0.16
Nodes (15): arb_poll_targets_hours(), build_poll_targets(), dense_poll_targets_hours(), PropsPollDecision, datetime, Budget-aware polling cadence for player props -- a different scheduling problem…, Descending list of hours-before-kickoff targets for the dense ("most critical")…, Descending list of hours-before-kickoff targets for the sparse ("basic")… (+7 more)

### Community 94 - "active_bets"
Cohesion: 0.18
Nodes (19): active_bets(), load_bet_log(), log_bet(), main(), Path, Append one bet. Creates the file on first use., Every logged bet, oldest first. Missing file is an empty log, not an error --…, Logged bets with superseded rows removed. Corrections are appended, never… (+11 more)

### Community 95 - "calibration.py"
Cohesion: 0.14
Nodes (22): CalibratedClassifierCV, compare_to_baseline(), fit_calibrated_model(), predict_calibrated_proba(), predict_over_proba(), predict_over_proba_empirical(), DataFrame, ndarray (+14 more)

### Community 96 - "elo_win_probability"
Cohesion: 0.29
Nodes (7): elo_win_probability(), Standard Elo logistic transform: P(a beats b), with `a` treated as the side…, test_400_point_gap_is_the_classic_10_to_1_elo_property(), test_equal_ratings_no_hfa_is_a_coin_flip(), test_home_field_advantage_shifts_probability_toward_home(), test_base_pressure_offset_recenters_expectation_to_the_measured_base_rate(), test_base_pressure_offset_recenters_expectation_to_the_measured_base_rate()

### Community 97 - "steam.py"
Cohesion: 0.19
Nodes (12): _interval_prob(), price_stale_book_opportunity(), datetime, Steam-move detection: synchronized, same-direction line movement across…, P(lo < X < hi) for X ~ Normal(mu, sigma) -- same formula as…, Prices betting a stale book's CURRENT (pre-steam) line/price as a single…, expected_value(), EV of a unit bet at fair win probability p and decimal odds d. (+4 more)

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
Cohesion: 0.15
Nodes (24): event_id_from_alert_key(), find_positive_ev_spots(), prune_alert_state(), Timedelta, One row per (event, side, book) where `book`'s latest moneyline price beats…, The event a dedup key refers to, across all three key shapes in use:…, Drop dedup entries whose event has already started. Sentinels are always kept;…, **Pruning must key on KICKOFF, not alert age.** Measured 2026-08-23: the state… (+16 more)

### Community 102 - "test_prereg_scan.py"
Cohesion: 0.08
Nodes (53): detect_moves(), pinnacle_fair_path(), DataFrame, Series, H1 (preregistration_wk5-9.md): stale soft-book prop lines after a Pinnacle…, For each move, the best execution-book price on the moved-toward side at the…, Attach Pinnacle's close and the H1 metrics to each bet. close_ev price taken,…, Was the same book still offering at least the bet's price at its next capture… (+45 more)

### Community 103 - "to_backtest_bets"
Cohesion: 0.15
Nodes (11): Market, PointInTimeStore, Enrich logged bets with entry/closing fair probabilities and CLV, so…, Lazily resolves (sigma_margin, sigma_total), fetching at most once.…, _SigmaProvider, to_backtest_bets(), Close" is defined as the last quote at or before kickoff -- a filter every row…, test_empty_log_produces_no_bets() (+3 more)

### Community 104 - "PropsCollectorState"
Cohesion: 0.20
Nodes (14): _build_targets(), main(), One-off migration: re-index `data/props_collect_state.json` onto a changed poll…, `props_budget.build_poll_targets` with the arb spacing made a parameter, so the…, early_poll_targets_hours(), load_state(), PropsCollectorState, Path (+6 more)

### Community 105 - "record_alert"
Cohesion: 0.17
Nodes (31): timedelta, Record the originating observation for each alerted spot. `key_fn` is the…, Re-observe every still-open alerted leg and append what the market shows. Reads…, recheck(), record_alert(), _arb_spot(), _ev_spot(), _key() (+23 more)

### Community 106 - "prop_alert_key"
Cohesion: 0.15
Nodes (14): _fmt_american(), format_arb_alert_message(), format_prop_ev_alert_message(), prop_alert_key(), Series, Arb alerts name BOTH legs and both books -- an arb is only real if both are…, Dedup key for a prop alert. **Must include player/stat/line** --…, The props-EV signal tested null; the alert must say so rather than read like… (+6 more)

### Community 107 - "Train-phase results — 2026-10-04"
Cohesion: 0.17
Nodes (11): 1. Gate: is Pinnacle's prop close calibrated?, 2. Gate: is Pinnacle's moneyline close calibrated?, 3. Does "price beats Pinnacle" turn into money? (historical, realized), 4. Live 2026 alerts on closing EV (shadow log, Weeks 1–4), 5. H1 — stale soft line after a Pinnacle move, 6. H3 — prop middles: calibration gate FAIL, 7. H2 — team-total (exploratory; contract undecided), 8. Not computed (+3 more)

### Community 108 - "test_props_scan.py"
Cohesion: 0.12
Nodes (34): find_live_prop_arb_spots(), find_live_prop_ev_spots(), _fresh_only(), _live_props(), DataFrame, datetime, Timedelta, Live player-prop scanning: cross-book arbitrage and Pinnacle-anchored EV, wired… (+26 more)

### Community 109 - "test_correlated_props.py"
Cohesion: 0.05
Nodes (80): bucket_edge(), bucket_favorite_strength(), build_team_game_outcomes(), correlated_edge(), estimate_game_specific_joint_prob(), is_bucket_validated(), measure_leg_correlation(), measure_leg_correlation_by_bucket() (+72 more)

### Community 110 - "scheduler.py"
Cohesion: 0.14
Nodes (30): CollectorContext, Config, Config, Path, Collector configuration. Everything The Odds API's free-tier budget forces us…, build_context(), main(), Entrypoint: `python -m src.collect.run [--once]`. `--once` does a single… (+22 more)

### Community 111 - "market_baseline"
Cohesion: 0.39
Nodes (6): market_baseline(), Market baseline (blueprint Part E). "Your baseline is the devigged Pinnacle…, Fair probability for the side at `side_index`, from Pinnacle's raw American…, test_default_method_is_shin(), test_side_index_selects_the_right_side(), test_symmetric_market_gives_half_regardless_of_method()

### Community 112 - "_apply_exposure_cap"
Cohesion: 0.20
Nodes (10): _apply_exposure_cap(), DataFrame, Keep alerts in priority order until their suggested stakes exhaust `remaining`,…, parametrize, Arb spots carry no `suggested_stake` (legs are sized separately), but they are…, The cap is a per-CYCLE ceiling, not per-batch: spending it on the first signal…, test_exposure_budget_is_shared_across_successive_signals(), test_exposure_cap_charges_rows_without_a_stake_column() (+2 more)

### Community 113 - "season_review.py"
Cohesion: 0.14
Nodes (16): _clv_series(), format_review_summary(), main(), DataFrame, ndarray, In-season strategy review: is each live strategy still working, and when should…, Human-readable digest, ordered so anything needing action is first -- this is…, Weekly in-season health check over the LIVE bet log. Segments on `strategy`… (+8 more)

### Community 114 - ".read_as_of"
Cohesion: 0.24
Nodes (8): kickoffs_from_store(), LeakageError, DataFrame, datetime, RuntimeError, The only read path. Returns rows visible at `decision_time`, and nothing later.…, event_id -> kickoff, from the store's own `event_start_time`. Lives here rather…, Raised if a query would return (or returned) data from after decision_time.

### Community 115 - "build_training_frame"
Cohesion: 0.38
Nodes (10): build_training_frame(), One row per game: `build_game_features()` output plus the home-win label and…, _pbp_fixture(), _plays(), DataFrame, _schedule_fixture(), test_build_training_frame_drops_rows_elo_ratings_does_not_cover(), test_build_training_frame_drops_ties_and_first_week_rows() (+2 more)

### Community 117 - "test_decision_report.py"
Cohesion: 0.06
Nodes (60): _ci(), ci_includes_zero(), _decimal(), decision_table(), _directional_verdict(), first_recheck_frame(), format_table(), main() (+52 more)

### Community 119 - "compute_qb_elo_ratings"
Cohesion: 0.33
Nodes (10): compute_qb_elo_ratings(), DataFrame, QB-level Elo: a residual rating crediting individual quarterback performance…, One row per game: each starting QB's Elo rating *entering* that game (pre-game,…, _schedule(), test_backup_qb_starts_are_tracked_as_a_distinct_rating_from_the_starter(), test_first_start_for_every_qb_begins_at_initial_rating(), test_qb_rating_carries_across_games_not_reset() (+2 more)

### Community 123 - "team_total_scan.py"
Cohesion: 0.16
Nodes (21): Drop snapshots for games that have already kicked off -- only a future game is…, upcoming_only(), available_stats(), find_team_total_spots(), main(), measured_vig_by_event(), DataFrame, datetime (+13 more)

### Community 125 - "_coinflip_bets"
Cohesion: 0.29
Nodes (7): _coinflip_bets(), A strategy with no real selection skill should not stand out against randomly…, The negative control for the acceptance test above: a harness that always says…, n bets on true 50/50 events at a fixed price, with a controlled realized win…, test_detects_a_real_edge_when_one_actually_exists(), test_random_benchmark_flags_a_genuinely_strong_result(), test_random_benchmark_places_a_fair_coinflip_strategy_mid_distribution()

### Community 126 - "_kickoff_for"
Cohesion: 0.33
Nodes (6): _kickoff_for(), The most recently OBSERVED kickoff for this event. **Latest-observed, not…, A game moved EARLIER must not keep its stale later kickoff: the close window…, test_kickoff_handles_a_revision_to_a_later_time(), test_kickoff_is_none_for_an_unknown_event(), test_kickoff_uses_the_latest_observed_time_not_the_largest_value()

### Community 127 - "compare_to_book"
Cohesion: 0.40
Nodes (5): compare_to_book(), Forecast-quality comparison: model vs. book on the same events. Necessary but…, These are different questions and the API keeps them apart -- a model can win…, test_beating_the_book_on_brier_is_reported_separately_from_bettability(), test_compare_to_book_reports_both_sides_and_who_wins()

### Community 131 - "PollTarget"
Cohesion: 0.28
Nodes (9): PollTarget, One scheduled poll: when to fire it, which markets to request, and what that…, **Worst case** credits to poll `n_games` at this schedule: every poll returns…, A planning estimate that accounts for two measured facts the worst case…, realistic_season_credit_cost(), season_credit_cost(), The worst case assumes every early probe returns data at full price. It cannot…, test_early_probes_dominate_the_gap_between_worst_and_realistic_cost() (+1 more)

### Community 134 - "test_steam_scan.py"
Cohesion: 0.28
Nodes (11): main(), DataFrame, Steam-scan entrypoint: `python -m src.backtest.steam_scan`. Manual, run-by-…, One scan. Returns the report DataFrame (also logged); never sends any…, run(), _seed_store_with_real_steam(), _snapshot(), test_run_filters_out_spots_below_min_ev() (+3 more)

## Knowledge Gaps
- **201 isolated node(s):** `1. Gate: is Pinnacle's prop close calibrated?`, `2. Gate: is Pinnacle's moneyline close calibrated?`, `3. Does "price beats Pinnacle" turn into money? (historical, realized)`, `4. Live 2026 alerts on closing EV (shadow log, Weeks 1–4)`, `5. H1 — stale soft line after a Pinnacle move` (+196 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PointInTimeStore` connect `PointInTimeStore` to `test_bet_log.py`, `test_props_scheduler.py`, `test_closing_line.py`, `test_collect_props.py`, `test_steam_scan.py`, `live_scan.py`, `test_middling.py`, `test_movement_scan.py`, `OddsSnapshot`, `test_shadow_log.py`, `test_clv_data_path.py`, `OddsApiResponse`, `test_steam.py`, `backfill_historical_mainline`, `test_clv_metrics.py`, `shadow_log.py`, `test_health_check.py`, `demo_pipeline.py`, `engine.py`, `test_team_total_scan.py`, `test_collect_transform.py`, `middle_scan.py`, `test_clv_line_adjust.py`, `Side`, `run`, `steam.py`, `test_live_scan.py`, `to_backtest_bets`, `record_alert`, `test_props_scan.py`, `scheduler.py`, `season_review.py`, `.read_as_of`, `test_decision_report.py`, `team_total_scan.py`?**
  _High betweenness centrality (0.245) - this node is a cross-community bridge._
- **Why does `Market` connect `Market` to `test_closing_line.py`, `test_collect_props.py`, `test_steam_scan.py`, `test_middling.py`, `test_synthetic_market.py`, `test_movement_scan.py`, `OddsSnapshot`, `test_shadow_log.py`, `test_clv_data_path.py`, `test_steam.py`, `test_prop_settlement.py`, `shadow_log.py`, `test_clv_portfolio.py`, `test_health_check.py`, `demo_pipeline.py`, `test_team_total_scan.py`, `test_collect_transform.py`, `PointInTimeStore`, `middle_scan.py`, `test_clv_line_adjust.py`, `Side`, `win_interval`, `run`, `steam.py`, `test_live_scan.py`, `to_backtest_bets`, `record_alert`, `test_props_scan.py`, `test_decision_report.py`, `team_total_scan.py`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Why does `Side` connect `Side` to `Market`, `test_closing_line.py`, `test_collect_props.py`, `test_steam_scan.py`, `test_middling.py`, `test_synthetic_market.py`, `test_movement_scan.py`, `OddsSnapshot`, `test_shadow_log.py`, `test_clv_data_path.py`, `test_steam.py`, `test_prop_settlement.py`, `shadow_log.py`, `test_clv_portfolio.py`, `test_health_check.py`, `demo_pipeline.py`, `test_team_total_scan.py`, `test_collect_transform.py`, `PointInTimeStore`, `middle_scan.py`, `test_clv_line_adjust.py`, `win_interval`, `run`, `active_bets`, `steam.py`, `test_live_scan.py`, `to_backtest_bets`, `record_alert`, `test_props_scan.py`, `test_decision_report.py`, `team_total_scan.py`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Are the 133 inferred relationships involving `PointInTimeStore` (e.g. with `main()` and `run()`) actually correct?**
  _`PointInTimeStore` has 133 INFERRED edges - model-reasoned connections that need verification._
- **Are the 154 inferred relationships involving `Side` (e.g. with `_best_line()` and `best_middle_for_game()`) actually correct?**
  _`Side` has 154 INFERRED edges - model-reasoned connections that need verification._
- **Are the 144 inferred relationships involving `Market` (e.g. with `best_middle_for_game()` and `find_middle_opportunities()`) actually correct?**
  _`Market` has 144 INFERRED edges - model-reasoned connections that need verification._
- **Are the 43 inferred relationships involving `OddsSnapshot` (e.g. with `simulate_market()` and `_to_snapshot()`) actually correct?**
  _`OddsSnapshot` has 43 INFERRED edges - model-reasoned connections that need verification._