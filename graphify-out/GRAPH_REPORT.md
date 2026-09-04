# Graph Report - nfl_2026  (2026-09-03)

## Corpus Check
- 157 files · ~154,009 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2284 nodes · 6033 edges · 105 communities (97 shown, 8 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 844 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f516986f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Side
- test_bet_log.py
- test_evaluate.py
- check_collector_health
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
- test_prop_settlement.py
- Market
- test_synthetic_market.py
- 3. Data
- test_elo.py
- NFL CLV Case Study: Blueprint
- evaluation.py
- correlated_props.py
- Methodology backlog
- test_correlated_props.py
- monitor_run.py
- Beating the Close, Not the Book: A CLV-First Case Study of NFL Betting Markets
- 5. Results
- 1. Introduction
- 6. Discussion
- 2. Background and Related Work
- test_prop_projection.py
- Open items, in the order they should be picked up
- expected_value
- test_individual_pass_rush_elo.py
- test_game_level_features.py
- test_validation.py
- pit_store.py
- test_steam.py
- test_pass_rush_elo.py
- backfill_historical_mainline
- OddsApiClient
- test_drift_monitor.py
- test_clv_metrics.py
- test_parlay.py
- test_team_total_props.py
- ValueError
- test_clv_portfolio.py
- compute_receiver_elo_ratings
- Architecture & Status Audit
- test_health_check.py
- demo_pipeline.py
- test_engine_props.py
- test_train.py
- engine.py
- OddsSnapshot
- review_strategy
- scheduler.py
- test_props_budget.py
- PointInTimeStore
- test_evaluation.py
- test_shadow_log.py
- calibration.py
- test_collect_scheduler.py
- test_team_total_scan.py
- measure_prop_vig
- compare_to_book
- run
- middle_scan.py
- market_baseline
- test_steam_scan.py
- test_live_scan.py
- compute_qb_elo_ratings
- load_static.py
- _coinflip_bets
- season_review.py
- elo_win_probability
- test_monotonicity_check_ignores_thin_tail_rows
- test_backtest_engine.py
- fit_margin_model
- audit_integration.py
- test_margin_total.py
- measure_leg_correlation
- train.py
- isolated_state

## God Nodes (most connected - your core abstractions)
1. `Side` - 208 edges
2. `PointInTimeStore` - 201 edges
3. `Market` - 184 edges
4. `OddsSnapshot` - 72 edges
5. `Outcome` - 50 edges
6. `OddsApiClient` - 45 edges
7. `OddsApiResponse` - 32 edges
8. `settle()` - 32 edges
9. `BacktestEngine` - 31 edges
10. `run()` - 31 edges

## Surprising Connections (you probably didn't know these)
- `_bet_star_over()` --uses--> `DecisionPoint`  [INFERRED]
  tests/test_engine_props.py → src/backtest/engine.py
- `_always_bet_home_spread()` --uses--> `BetOrder`  [INFERRED]
  tests/test_backtest_engine.py → src/backtest/engine.py
- `_never_bet()` --uses--> `BetOrder`  [INFERRED]
  tests/test_backtest_engine.py → src/backtest/engine.py
- `test_future_snapshot_never_visible_to_strategy_or_used_as_close()` --uses--> `BetOrder`  [INFERRED]
  tests/test_backtest_engine.py → src/backtest/engine.py
- `test_loss_payout_is_negative_stake()` --uses--> `BetOrder`  [INFERRED]
  tests/test_backtest_engine.py → src/backtest/engine.py

## Import Cycles
- None detected.

## Communities (105 total, 8 thin omitted)

### Community 0 - "Side"
Cohesion: 0.12
Nodes (44): home_spread_line(), Convert nflverse's spread_line into the sportsbook side-line convention that…, _grade(), One bet's outcome, or None if it cannot be graded yet. None is returned rather…, Side, build_results_index(), GameResult, Outcome (+36 more)

### Community 1 - "test_bet_log.py"
Cohesion: 0.07
Nodes (70): payout_for(), Profit (not total return) for a graded bet. Public because live bets in…, Weekly in-season health check over the LIVE bet log. Segments on `strategy`…, run(), active_bets(), _close_price_decimal(), _fair_at(), _kickoff_for() (+62 more)

### Community 2 - "test_evaluate.py"
Cohesion: 0.12
Nodes (27): brier_score(), log_loss(), power_analysis(), DataFrame, ndarray, Model evaluation (blueprint Part B.5). "This section is where you prove you are…, mean((p - y)^2). Lower is better., -mean(y*log(p) + (1-y)*log(1-p)). p is clipped away from exactly 0/1 so a… (+19 more)

### Community 3 - "check_collector_health"
Cohesion: 0.12
Nodes (24): check_all(), check_collector_health(), market_write_freshness(), _now(), pinnacle_arrival_message(), prop_book_coverage(), DataFrame, datetime (+16 more)

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
Nodes (75): add_rest_travel_features(), add_weather_features(), build_game_features(), _is_garbage_time(), DataFrame, Series, Feature builder (blueprint Part E): team-strength proxies from play-by-play.…, One row per game_id: home/away pre-game rolling EPA features plus the schedule… (+67 more)

### Community 10 - "test_props_scan.py"
Cohesion: 0.05
Nodes (81): find_arbitrage_spots(), find_prop_ev_spots(), pinnacle_fair_probs(), DataFrame, Timedelta, Cross-book player-prop strategies that don't rely on market timing: (1) a…, One row per (event, player, prop_stat, line, side, book) where `book`'s price…, One row per (event, player, prop_stat, line, capture_time) where the best… (+73 more)

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

### Community 36 - "Market"
Cohesion: 0.07
Nodes (68): _best_line(), best_middle_for_game(), find_middle_opportunities(), _interval_prob(), line_threshold(), middle_ev(), middle_window(), MiddleOpportunity (+60 more)

### Community 37 - "test_synthetic_market.py"
Cohesion: 0.08
Nodes (47): _logit(), datetime, ndarray, timedelta, Synthetic market simulator -- validates this project's OWN CLV-measurement code…, Ground truth for one simulated player-prop contract. `over_hit` is the realized…, Ground truth for one simulated game -- what `simulate_market` actually…, `n_games` synthetic games, each with its own independently-drawn latent price… (+39 more)

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

### Community 42 - "correlated_props.py"
Cohesion: 0.13
Nodes (21): bucket_favorite_strength(), estimate_game_specific_joint_prob(), is_bucket_validated(), price_bucket_bet(), Correlated same-game outcome mispricing: do event pairs from the same game co-…, Which `FAVORITE_BUCKETS` bucket a team's real market-implied win probability…, Game-specific estimate of P(A and B), for pricing one particular upcoming game…, Whether `bucket` (one of `FAVORITE_BUCKETS`' labels) has survived an honest… (+13 more)

### Community 43 - "Methodology backlog"
Cohesion: 0.06
Nodes (35): 10. High-vig markets — **checked, hypothesis reframed, anytime-TD confirmed unpriceable**, 1. Rest/travel differential — **tested, negative result**, 2. Joint margin/total correlated distribution — **checked, premise doesn't hold**, 3. Steam detection — **built and live-validated**, 4. Player-prop middling — idea, blocked on live props posting, 5. Referee tendencies — **checked, no signal found (correcting an earlier wrong "blocked" claim)**, 6. Individual pass-rush rating — **built, corrects an earlier wrong "not buildable" claim**, 7. Training-window size — **checked, real effect, first non-Elo comparison to survive BH correction (in the negative direction)** (+27 more)

### Community 44 - "test_correlated_props.py"
Cohesion: 0.14
Nodes (29): bucket_edge(), build_team_game_outcomes(), correlated_edge(), naive_parlay_price(), Closed-form edge for one `FAVORITE_BUCKETS` bucket, under this module's…, Decimal price a same-game parlay would carry if a book priced it by multiplying…, The bettor-relevant number this module exists to produce: if a book prices a…, One row per team per game, home and away pooled (2x the game count, each team's… (+21 more)

### Community 45 - "monitor_run.py"
Cohesion: 0.14
Nodes (26): _alert_batch(), Series, Live +EV monitor entrypoint: `python -m src.notify.monitor_run`. Meant to be…, Dedup -> format -> send one class of alert. Shared by all three signals so they…, _alert_key(), AlertRecord, _latest_two_sided_pinnacle(), load_alert_state() (+18 more)

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
Nodes (14): 1. ~~Orphaned modules~~ RESOLVED 2026-08-23, 2. ~~Stale data files~~ DELETED 2026-08-23, 3. ~~`market_write_freshness` -> alert~~ DONE 2026-08-23, 4. ~~Full concurrent dry run~~ DONE 2026-08-23, 5. ~~Settle logged bets~~ DONE 2026-08-23, 6. ~~Retire the preseason modules~~ DONE 2026-09-03, 7. Cosmetic / housekeeping — mostly DONE 2026-08-23, 8. Code review — 13 findings, all fixed 2026-08-23 (+6 more)

### Community 53 - "expected_value"
Cohesion: 0.14
Nodes (27): apply_bankroll_caps(), expected_value(), fractional_kelly(), kelly_fraction(), Expected value and Kelly bet sizing (blueprint Part B.4). Full Kelly is too…, EV of a unit bet at fair win probability p and decimal odds d., Full Kelly fraction of bankroll. Can be negative when the price is bad at this…, k * full Kelly. k in [0.25, 0.5] per the blueprint; default 0.375 is the… (+19 more)

### Community 54 - "test_individual_pass_rush_elo.py"
Cohesion: 0.21
Nodes (20): build_individual_pass_rush_frame(), compute_individual_pass_rush_ratings(), DataFrame, Individual pass-rush rating: a real, previously-blocked capability. **Corrects…, One row per player-game at a real pass-rush position with at least one…, One row per player-game: this player's individual pass-rush rating *entering*…, _pfr_row(), _player_game() (+12 more)

### Community 55 - "test_game_level_features.py"
Cohesion: 0.11
Nodes (38): current_injury_status(), current_team(), player_status_snapshot(), DataFrame, Current player status: which team a player is on, and their injury/game status,…, One row per player: their most recent roster team/status at or before…, One row per player with an injury-report history: their most recent…, One row per rostered player: current team (trade-aware) + current injury/game… (+30 more)

### Community 56 - "test_validation.py"
Cohesion: 0.07
Nodes (50): benjamini_hochberg(), expanding_season_folds(), _lift(), paired_permutation_test_mean_diff(), permutation_test_lift(), DataFrame, ndarray, Series (+42 more)

### Community 57 - "pit_store.py"
Cohesion: 0.11
Nodes (29): OddsApiError, RuntimeError, RateLimitExceeded, Thin HTTP wrapper around The Odds API. Talks to The Odds API directly (not…, Network or unexpected-response failure talking to The Odds API., The API rejected the request for quota/auth reasons (401/402/429)., backfill_historical_props(), find_historical_event_id() (+21 more)

### Community 58 - "test_steam.py"
Cohesion: 0.10
Nodes (41): book_moves(), BookMove, detect_steam_move(), find_steam_opportunities(), _interval_prob(), _largest_time_cluster(), price_stale_book_opportunity(), DataFrame (+33 more)

### Community 59 - "test_pass_rush_elo.py"
Cohesion: 0.22
Nodes (17): compute_pass_rush_elo_ratings(), credited_pressure_counts(), DataFrame, Pass-rush Elo: a play-level, team-level rating of pass-rush vs. pass-protection…, Raw per-player counts of sacks (full credit), half-sacks (0.5 credit), and QB…, One row per dropback: `posteam`'s pass-protection Elo and `defteam`'s pass-rush…, _pbp(), test_clean_pocket_lowers_rush_elo_and_raises_protection_elo() (+9 more)

### Community 60 - "backfill_historical_mainline"
Cohesion: 0.12
Nodes (26): backfill_historical_mainline(), estimate_pull_cost(), _iso_z(), main(), datetime, Credits a pull will cost, before spending any. One event-id lookup per game (1…, `games`: iterable of (match, home_name, away_name, kickoff) -- same shape as…, The API wants a Z-suffixed UTC instant, not a +00:00 offset. (+18 more)

### Community 61 - "OddsApiClient"
Cohesion: 0.11
Nodes (28): Response, Session, OddsApiClient, _parse_int_header(), _parse_iso(), datetime, Historical per-event odds, snapshotted at the nearest available timestamp <=…, Shared retry/error-handling for both endpoints. Returns the raw successful… (+20 more)

### Community 62 - "test_drift_monitor.py"
Cohesion: 0.18
Nodes (18): cusum(), first_flag_index(), ndarray, Non-stationarity / drift monitor (blueprint Part E, "the genuinely hard part").…, Index of the first True in `flagged`, or None if it never fires., Trailing rolling mean CLV, one value per bet. Uses whatever history exists so…, Two-sided CUSUM change-point detector. `upper` accumulates evidence of a…, Rolling Brier score over the trailing `window` predictions, minus a… (+10 more)

### Community 63 - "test_clv_metrics.py"
Cohesion: 0.16
Nodes (20): beat_rate(), bootstrap_ci(), clv_price(), clv_probability(), Closing Line Value metrics (blueprint Part B.3). CLV is measured two ways --…, How far the fair market moved toward your side after you bet. Positive means…, Whether the decimal price you took beats the closing price for the same side.…, Fraction of bets with positive CLV. (+12 more)

### Community 64 - "test_parlay.py"
Cohesion: 0.14
Nodes (28): parlay_ev(), parlay_independent_probability(), parlay_price_decimal(), parlay_true_probability(), ParlayLeg, Parlay pricing and EV -- multi-leg bets, priced against REAL leg prices. **Why…, Correlation-adjusted joint win probability: the independent product scaled by…, Full EV/sizing for one parlay, reusing `src/signal/sizing.py`'s… (+20 more)

### Community 65 - "test_team_total_props.py"
Cohesion: 0.20
Nodes (20): build_team_total_lines(), fit_team_total_residual_std(), DataFrame, Series, Team-total rushing/passing yards vs. moneyline correlation…, (mean_residual, residual_std) of `actual_team_total - implied_team_total_line`…, Boolean: did the team's real total clear its own real implied line -- the leg…, One row per (event_id, team) with real Pinnacle data for `prop_stat`:… (+12 more)

### Community 66 - "ValueError"
Cohesion: 0.22
Nodes (4): field_validator, model_validator, Reject combinations that cannot be settled, at the point a human types them.…, ValueError

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
Cohesion: 0.12
Nodes (36): check_props_write_freshness(), Is the *props* collector still writing? The aggregate check cannot tell. **This…, unhealthy_messages(), _prop_snap(), The mainline and props collectors are separate services writing to the same…, Books post props on their own schedule -- the 2026 opener posted 17 days out.…, The 2023-24 prop backfill carries ~1.5-year-old capture_times in the same…, The whole point. Mainline keeps writing; props stopped 20h ago with a kickoff… (+28 more)

### Community 71 - "demo_pipeline.py"
Cohesion: 0.18
Nodes (18): main(), make_synthetic_snapshots(), datetime, End-to-end pipeline demo: pull -> store -> compare -> decide -> notify. `make…, _step(), _escape_for_applescript(), RuntimeError, SMS/iMessage alerts via macOS Messages.app. No third-party account, no API key:… (+10 more)

### Community 72 - "test_engine_props.py"
Cohesion: 0.16
Nodes (32): BacktestEngine, BetOrder, Replays a strategy against the real point-in-time store. **Bankroll is a hard,…, Dispatch to the right settlement path for this market -- game score for…, A strategy's decision to bet, returned from a Strategy callable. None means "no…, _bet_star_over(), _both_over(), _player_stats() (+24 more)

### Community 73 - "test_train.py"
Cohesion: 0.21
Nodes (22): HistGradientBoostingClassifier, build_training_frame(), fit_gbm_model(), DataFrame, Three-way, out-of-time split: fit the model on `train_seasons`, fit the…, Gradient-boosted trees on `feature_columns` -- blueprint Part E's other…, One row per game: `build_game_features()` output plus the home-win label and…, time_based_split() (+14 more)

### Community 74 - "engine.py"
Cohesion: 0.21
Nodes (13): latest_fair_prob(), _latest_price(), _market_rows(), _parse_kickoffs(), DataFrame, datetime, Series, Leakage-free point-in-time backtester (blueprint Part C, B.3, B.4). Reuses… (+5 more)

### Community 75 - "OddsSnapshot"
Cohesion: 0.10
Nodes (26): american_to_decimal(), decimal_to_implied_prob(), Path, Append one immutable batch. Never overwrites an existing file., _to_dataframe(), OddsSnapshot, BaseModel, datetime (+18 more)

### Community 76 - "review_strategy"
Cohesion: 0.11
Nodes (35): Full health check on one strategy's live bets. The recommendation is…, One review row per strategy segment. Segments rather than pools for the same…, review_all(), review_strategy(), _frame(), CUSUM is sequential -- an unsorted series scrambles the exact pattern it…, `== NaN` is False for every row -- the bug already fixed in clv_portfolio.…, CLV-only review is still valid -- not every recorded bet carries a settled… (+27 more)

### Community 77 - "scheduler.py"
Cohesion: 0.08
Nodes (56): Config, load_config(), Path, Collector configuration. Everything The Odds API's free-tier budget forces us…, Build a Config from environment variables (or an injected mapping for tests).…, pull_historical_mainline_snapshot(), _pull_with_credits(), Historical mainline (h2h/spreads/totals) odds backfill. **The rigor fix from… (+48 more)

### Community 78 - "test_props_budget.py"
Cohesion: 0.06
Nodes (78): OddsApiResponse, arb_poll_targets_hours(), build_poll_targets(), decide_props_poll(), dense_poll_targets_hours(), early_poll_targets_hours(), EventPollState, load_state() (+70 more)

### Community 79 - "PointInTimeStore"
Cohesion: 0.10
Nodes (37): _home_fair(), main(), DataFrame, Does the line actually move toward truth? Real 2024 historical movement. **Two…, kickoffs_from_store(), LeakageError, PointInTimeStore, DataFrame (+29 more)

### Community 80 - "test_evaluation.py"
Cohesion: 0.19
Nodes (20): evaluate_at_threshold(), Metrics for the subset of `bets` whose edge clears `threshold`. `bets` needs…, _bets(), **Acceptance test.** `props_ev_backtest` found no detectable edge on real 2024…, Four bets at a huge price that all happened to win: positive ROI, but nothing…, Monotonicity is a disqualifier when measurable -- a strong-looking result that…, A vig'd 'probability' pair sums > 1 and individual legs can exceed 1; accepting…, The metric that exposes 'profitable on 4 of 900 games' as noise. (+12 more)

### Community 81 - "test_shadow_log.py"
Cohesion: 0.10
Nodes (58): Any, append(), _decimal(), _latest_price(), legs_from_spot(), load(), main(), BaseModel (+50 more)

### Community 82 - "calibration.py"
Cohesion: 0.18
Nodes (17): CalibratedClassifierCV, compare_to_baseline(), fit_calibrated_model(), predict_calibrated_proba(), Pipeline, Series, Calibration layer (blueprint Part E): Platt scaling / isotonic regression on…, `method`: "isotonic" (non-parametric, flexible, can overfit a small calibration… (+9 more)

### Community 83 - "test_collect_scheduler.py"
Cohesion: 0.09
Nodes (50): CollectorState, current_period_end(), decide_poll(), _game_interval_minutes(), load_state(), _minutes_since(), _nearest_upcoming_hours(), parse_quota_headers() (+42 more)

### Community 84 - "test_team_total_scan.py"
Cohesion: 0.11
Nodes (41): available_stats(), find_team_total_spots(), format_team_total_alert(), main(), measured_vig_by_event(), DataFrame, datetime, Series (+33 more)

### Community 85 - "measure_prop_vig"
Cohesion: 0.14
Nodes (17): measure_prop_vig(), DataFrame, Re-derive `MEASURED_PROP_VIG` from raw prop snapshots. **This exists because…, _prop_row(), One two-sided prop contract at a given pair of American prices., -110/-110 is 4.76% overround by construction. If this drifts, the constant's…, The constant is `sum(q)-1`, matching devig's own `overround()`. Hold would be…, They differ materially on real data (6.29% vs 6.88% on the same 16,953 Pinnacle… (+9 more)

### Community 86 - "compare_to_book"
Cohesion: 0.40
Nodes (5): compare_to_book(), Forecast-quality comparison: model vs. book on the same events. Necessary but…, These are different questions and the API keeps them apart -- a model can win…, test_beating_the_book_on_brier_is_reported_separately_from_bettability(), test_compare_to_book_reports_both_sides_and_who_wins()

### Community 87 - "run"
Cohesion: 0.38
Nodes (9): main(), One scan-and-alert cycle across all three signals. Returns the number of alerts…, run(), _seed_store(), _snapshot(), test_run_does_not_record_a_spot_whose_send_failed(), test_run_does_not_send_or_record_when_phone_not_configured(), test_run_returns_zero_when_no_spots_found() (+1 more)

### Community 88 - "middle_scan.py"
Cohesion: 0.18
Nodes (17): fit_residual_stds(), main(), DataFrame, Middle-scan entrypoint: `python -m src.backtest.middle_scan`. A manual, run-by-…, (sigma_margin, sigma_total) for LIVE pricing -- not the research evaluation…, One scan. Returns the report DataFrame (also logged); never sends any…, run(), fit_total_model() (+9 more)

### Community 89 - "market_baseline"
Cohesion: 0.39
Nodes (6): market_baseline(), Market baseline (blueprint Part E). "Your baseline is the devigged Pinnacle…, Fair probability for the side at `side_index`, from Pinnacle's raw American…, test_default_method_is_shin(), test_side_index_selects_the_right_side(), test_symmetric_market_gives_half_regardless_of_method()

### Community 90 - "test_steam_scan.py"
Cohesion: 0.28
Nodes (11): main(), DataFrame, Steam-scan entrypoint: `python -m src.backtest.steam_scan`. Manual, run-by-…, One scan. Returns the report DataFrame (also logged); never sends any…, run(), _seed_store_with_real_steam(), _snapshot(), test_run_filters_out_spots_below_min_ev() (+3 more)

### Community 91 - "test_live_scan.py"
Cohesion: 0.17
Nodes (20): event_id_from_alert_key(), find_positive_ev_spots(), Timedelta, One row per (event, side, book) where `book`'s latest moneyline price beats…, The event a dedup key refers to, across all three key shapes in use:…, **Pruning must key on KICKOFF, not alert age.** Measured 2026-08-23: the state…, The fallback window must exceed how far ahead of kickoff an alert can fire (21…, _rec() (+12 more)

### Community 92 - "compute_qb_elo_ratings"
Cohesion: 0.33
Nodes (10): compute_qb_elo_ratings(), DataFrame, QB-level Elo: a residual rating crediting individual quarterback performance…, One row per game: each starting QB's Elo rating *entering* that game (pre-game,…, _schedule(), test_backup_qb_starts_are_tracked_as_a_distinct_rating_from_the_starter(), test_first_start_for_every_qb_begins_at_initial_rating(), test_qb_rating_carries_across_games_not_reset() (+2 more)

### Community 93 - "load_static.py"
Cohesion: 0.16
Nodes (16): load_injuries(), load_pbp(), load_pfr_pass_rush_advstats(), load_player_stats(), load_players(), load_snap_counts(), load_weekly_rosters(), Path (+8 more)

### Community 94 - "_coinflip_bets"
Cohesion: 0.29
Nodes (7): _coinflip_bets(), A strategy with no real selection skill should not stand out against randomly…, The negative control for the acceptance test above: a harness that always says…, n bets on true 50/50 events at a fixed price, with a controlled realized win…, test_detects_a_real_edge_when_one_actually_exists(), test_random_benchmark_flags_a_genuinely_strong_result(), test_random_benchmark_places_a_fair_coinflip_strategy_mid_distribution()

### Community 95 - "season_review.py"
Cohesion: 0.14
Nodes (14): _clv_series(), _detect_decay(), format_review_summary(), main(), DataFrame, ndarray, In-season strategy review: is each live strategy still working, and when should…, Has CLV shifted *downward* from this strategy's OWN established baseline? Two… (+6 more)

### Community 96 - "elo_win_probability"
Cohesion: 0.29
Nodes (7): elo_win_probability(), Standard Elo logistic transform: P(a beats b), with `a` treated as the side…, test_400_point_gap_is_the_classic_10_to_1_elo_property(), test_equal_ratings_no_hfa_is_a_coin_flip(), test_home_field_advantage_shifts_probability_toward_home(), test_base_pressure_offset_recenters_expectation_to_the_measured_base_rate(), test_base_pressure_offset_recenters_expectation_to_the_measured_base_rate()

### Community 98 - "test_backtest_engine.py"
Cohesion: 0.38
Nodes (14): DecisionPoint, What a strategy sees when it's given a chance to act. `visible_snapshots` is…, _always_bet_home_spread(), _never_bet(), _schedule(), _seed_game1(), _snap(), test_future_snapshot_never_visible_to_strategy_or_used_as_close() (+6 more)

### Community 99 - "fit_margin_model"
Cohesion: 0.22
Nodes (14): fit_residual_std(), predict_over_proba(), predict_over_proba_empirical(), DataFrame, ndarray, Std of (actual - predicted) on `calib_df` -- a regression analogue of…, P(actual > line) under Normal(predicted_mean, residual_std) -- a v1…, Same question as `predict_over_proba` -- P(actual > line) -- but without… (+6 more)

### Community 100 - "audit_integration.py"
Cohesion: 0.21
Nodes (16): check_architecture_md(), classify(), main(), _make_entrypoints(), _module_graph(), _notebook_entrypoints(), Path, Which src/ modules are actually reachable, and from what? **Why this exists.**… (+8 more)

### Community 101 - "test_margin_total.py"
Cohesion: 0.42
Nodes (12): build_margin_total_frame(), `build_training_frame()`'s output plus spread/total regression targets and…, _pbp_fixture(), _plays(), DataFrame, _schedule_fixture(), test_build_margin_total_frame_computes_margin_and_total(), test_home_covers_flips_when_home_is_a_big_enough_underdog() (+4 more)

### Community 102 - "measure_leg_correlation"
Cohesion: 0.20
Nodes (11): measure_leg_correlation(), measure_leg_correlation_by_bucket(), Series, `indicator_a`/`indicator_b`: aligned boolean/0-1 Series, one row per game (or…, `measure_leg_correlation`, stratified by favorite strength -- see…, test_independent_legs_give_a_lift_near_one(), test_measure_leg_correlation_by_bucket_splits_by_market_prob(), test_negatively_correlated_legs_give_a_lift_below_one() (+3 more)

### Community 103 - "train.py"
Cohesion: 0.38
Nodes (5): Protocol, predict_home_win_proba(), _ProbaClassifier, ndarray, Model training (blueprint Part E): first outcome model + time-based split.…

### Community 104 - "isolated_state"
Cohesion: 0.67
Nodes (3): fixture, isolated_state(), Swap the shared alert state for an in-memory dict. Necessary because…

## Knowledge Gaps
- **168 isolated node(s):** `nfl-clv`, `graphify`, `Usage`, `What graphify is for`, `Step 0 - GitHub repos and multi-path merge (only if a URL or several paths)` (+163 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PointInTimeStore` connect `PointInTimeStore` to `test_bet_log.py`, `check_collector_health`, `test_closing_line.py`, `props.py`, `test_props_scan.py`, `Market`, `monitor_run.py`, `pit_store.py`, `test_steam.py`, `backfill_historical_mainline`, `test_health_check.py`, `demo_pipeline.py`, `test_engine_props.py`, `engine.py`, `OddsSnapshot`, `scheduler.py`, `test_props_budget.py`, `test_shadow_log.py`, `test_collect_scheduler.py`, `test_team_total_scan.py`, `run`, `middle_scan.py`, `test_steam_scan.py`, `test_live_scan.py`, `season_review.py`, `test_backtest_engine.py`?**
  _High betweenness centrality (0.230) - this node is a cross-community bridge._
- **Why does `Side` connect `Side` to `test_bet_log.py`, `check_collector_health`, `test_closing_line.py`, `props.py`, `test_props_scan.py`, `test_prop_settlement.py`, `Market`, `test_synthetic_market.py`, `test_steam.py`, `test_clv_portfolio.py`, `test_health_check.py`, `demo_pipeline.py`, `test_engine_props.py`, `engine.py`, `OddsSnapshot`, `scheduler.py`, `PointInTimeStore`, `test_shadow_log.py`, `test_team_total_scan.py`, `run`, `middle_scan.py`, `test_steam_scan.py`, `test_live_scan.py`, `test_backtest_engine.py`?**
  _High betweenness centrality (0.104) - this node is a cross-community bridge._
- **Why does `Market` connect `Market` to `Side`, `test_bet_log.py`, `check_collector_health`, `test_closing_line.py`, `props.py`, `test_props_scan.py`, `test_synthetic_market.py`, `test_steam.py`, `test_clv_portfolio.py`, `test_health_check.py`, `demo_pipeline.py`, `test_engine_props.py`, `engine.py`, `OddsSnapshot`, `scheduler.py`, `PointInTimeStore`, `test_shadow_log.py`, `test_team_total_scan.py`, `run`, `middle_scan.py`, `test_steam_scan.py`, `test_live_scan.py`, `test_backtest_engine.py`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Are the 168 inferred relationships involving `Side` (e.g. with `BacktestBet` and `BetOrder`) actually correct?**
  _`Side` has 168 INFERRED edges - model-reasoned connections that need verification._
- **Are the 149 inferred relationships involving `PointInTimeStore` (e.g. with `main()` and `BacktestEngine`) actually correct?**
  _`PointInTimeStore` has 149 INFERRED edges - model-reasoned connections that need verification._
- **Are the 146 inferred relationships involving `Market` (e.g. with `BacktestBet` and `BacktestEngine`) actually correct?**
  _`Market` has 146 INFERRED edges - model-reasoned connections that need verification._
- **Are the 42 inferred relationships involving `OddsSnapshot` (e.g. with `simulate_market()` and `_to_snapshot()`) actually correct?**
  _`OddsSnapshot` has 42 INFERRED edges - model-reasoned connections that need verification._