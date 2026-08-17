# Graph Report - nfl_2026  (2026-08-17)

## Corpus Check
- 89 files · ~50,500 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 850 nodes · 2064 edges · 55 communities (44 shown, 11 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 288 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8d464350`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Side
- scheduler.py
- test_live_scan.py
- test_collect_transform.py
- test_evaluate.py
- market_baseline
- props.py
- pit_store.py
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
- test_prop_settlement.py
- datetime
- DataFrame
- Beating the Close, Not the Book: A CLV-First Case Study of NFL Betting Markets
- test_elo.py
- nfl-clv
- ndarray
- Pipeline
- test_sizing.py
- preseason.py
- OddsApiClient
- OddsApiResponse
- client.py
- PointInTimeStore
- OddsSnapshot
- send_message
- test_monitor_run.py
- demo_pipeline.py
- OddsApiError
- Path

## God Nodes (most connected - your core abstractions)
1. `PointInTimeStore` - 73 edges
2. `Side` - 69 edges
3. `Market` - 60 edges
4. `OddsApiClient` - 34 edges
5. `OddsSnapshot` - 30 edges
6. `settle()` - 28 edges
7. `Outcome` - 25 edges
8. `tick()` - 25 edges
9. `OddsApiResponse` - 23 edges
10. `TransformError` - 21 edges

## Surprising Connections (you probably didn't know these)
- `test_favorite_and_underdog_decimal_conversion()` --calls--> `american_to_decimal()`  [INFERRED]
  tests/test_schema.py → src/devig/convert.py
- `test_event_odds_to_prop_snapshots_parses_over_under_pair()` --uses--> `Market`  [INFERRED]
  tests/test_collect_props.py → src/store/schema.py
- `test_event_to_snapshots_maps_markets_and_sides()` --uses--> `Market`  [INFERRED]
  tests/test_collect_transform.py → src/store/schema.py
- `_snapshot()` --uses--> `Market`  [INFERRED]
  tests/test_live_scan.py → src/store/schema.py
- `_snapshot()` --uses--> `Market`  [INFERRED]
  tests/test_monitor_run.py → src/store/schema.py

## Import Cycles
- None detected.

## Communities (55 total, 11 thin omitted)

### Community 0 - "Side"
Cohesion: 0.08
Nodes (77): BacktestBet, BacktestEngine, BetOrder, DecisionPoint, _latest_fair_prob(), _latest_price(), _parse_kickoffs(), _payout() (+69 more)

### Community 1 - "scheduler.py"
Cohesion: 0.06
Nodes (70): BlockingScheduler, date, Path, CollectorState, current_period_end(), decide_poll(), _game_interval_minutes(), load_state() (+62 more)

### Community 2 - "test_live_scan.py"
Cohesion: 0.15
Nodes (29): main(), Live +EV monitor entrypoint: `python -m src.notify.monitor_run`. Meant to be…, One scan-and-alert cycle. Returns the number of alerts actually sent. Never…, run(), _alert_key(), AlertRecord, find_positive_ev_spots(), format_alert_message() (+21 more)

### Community 3 - "test_collect_transform.py"
Cohesion: 0.17
Nodes (28): build_team_name_map(), DataFrame, full team name -> abbreviation, restricted to abbrs used in `schedule`., build_schedule_index(), event_to_snapshots(), match_event(), MatchResult, DataFrame (+20 more)

### Community 4 - "test_evaluate.py"
Cohesion: 0.06
Nodes (66): CalibratedClassifierCV, ndarray, Pipeline, compare_to_baseline(), fit_calibrated_model(), predict_calibrated_proba(), DataFrame, Pipeline (+58 more)

### Community 5 - "market_baseline"
Cohesion: 0.07
Nodes (50): model_validator, beat_rate(), bootstrap_ci(), clv_price(), clv_probability(), Closing Line Value metrics (blueprint Part B.3). CLV is measured two ways --…, How far the fair market moved toward your side after you bet. Positive means…, Whether the decimal price you took beats the closing price for the same side.… (+42 more)

### Community 6 - "props.py"
Cohesion: 0.16
Nodes (24): event_odds_to_prop_snapshots(), main(), poll_all_props(), poll_event_props(), datetime, ScheduleIndex, Player-prop odds collection. **Prepped, not active.** Live-checked 2026-08-17…, One event's worth of prop snapshots. Raises OddsApiError/RateLimitExceeded to… (+16 more)

### Community 7 - "pit_store.py"
Cohesion: 0.17
Nodes (10): LeakageError, DataFrame, datetime, Path, RuntimeError, Append-only, point-in-time odds store. This is the leakage guard for the whole…, The only read path. Returns rows visible at `decision_time`, and nothing later., Raised if a query would return (or returned) data from after decision_time. (+2 more)

### Community 8 - "test_devig.py"
Cohesion: 0.12
Nodes (30): compare_methods(), compare_methods_table(), devig_additive(), devig_multiplicative(), devig_power(), devig_shin(), DevigResult, overround() (+22 more)

### Community 9 - "test_features.py"
Cohesion: 0.16
Nodes (27): Series, build_game_features(), _is_garbage_time(), DataFrame, Feature builder (blueprint Part E): team-strength proxies from play-by-play.…, One row per game_id: home/away pre-game rolling EPA features plus the schedule…, True where a play should be excluded. Missing `wp` (nflverse leaves ~0.6% of…, Collapse play-by-play to one row per (game_id, team): offensive and defensive… (+19 more)

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
Cohesion: 0.13
Nodes (27): DataFrame, Outcome, Side, build_player_stats_index(), normalize_player_name(), Settlement for player-prop (Over/Under) bets against nflverse's per-player game…, Batch-grade prop-shaped rows (event_id/game_id, player_name, prop_stat, side,…, Collapse punctuation/whitespace differences between an odds book's player name… (+19 more)

### Community 38 - "Beating the Close, Not the Book: A CLV-First Case Study of NFL Betting Markets"
Cohesion: 0.04
Nodes (45): 1.1 Motivation, 1.2 Thesis, 1.3 Contributions, 1.4 What success means here, 1. Introduction, 2.1 Market efficiency in sports betting, 2.2 Closing Line Value as an edge proxy, 2.3 Prior work (+37 more)

### Community 39 - "test_elo.py"
Cohesion: 0.12
Nodes (30): canonical_team(), compute_team_elo_ratings(), elo_win_probability(), mov_multiplier(), DataFrame, Elo rating system: opponent-adjusted team strength, sequential and leakage-free…, One row per game: each team's Elo rating *entering* that game (pre-game,…, Map a historical/relocated abbreviation to the current one a franchise's rating… (+22 more)

### Community 40 - "nfl-clv"
Cohesion: 0.20
Nodes (9): Data chronology: nflverse (historical) vs. Pinnacle (live), Historical props for backtesting — checked, blocked on paid access, Live monitoring: 24/7 services + SMS alerts, nfl-clv, Player props (prepped, not active), Preseason dry run, Quickstart, Repo tree (+1 more)

### Community 43 - "test_sizing.py"
Cohesion: 0.14
Nodes (27): apply_bankroll_caps(), expected_value(), fractional_kelly(), kelly_fraction(), Expected value and Kelly bet sizing (blueprint Part B.4). Full Kelly is too…, EV of a unit bet at fair win probability p and decimal odds d., Full Kelly fraction of bankroll. Can be negative when the price is bad at this…, k * full Kelly. k in [0.25, 0.5] per the blueprint; default 0.375 is the… (+19 more)

### Community 44 - "preseason.py"
Cohesion: 0.18
Nodes (20): build_preseason_match(), main(), poll_once(), Preseason dry-run collector: same collection mechanics as the real season…, One poll: fetch, match, transform, write. Returns counts for logging/testing --…, Build a MatchResult straight from the Odds API event, no nflverse schedule…, load_team_name_map(), Path (+12 more)

### Community 45 - "OddsApiClient"
Cohesion: 0.22
Nodes (20): Session, OddsApiClient, RateLimitExceeded, The API rejected the request for quota/auth reasons (401/402/429)., parametrize, _response(), test_get_event_odds_hits_the_per_event_url(), test_get_event_odds_raises_rate_limit_exceeded_like_get_odds() (+12 more)

### Community 46 - "OddsApiResponse"
Cohesion: 0.20
Nodes (19): MatchResult, OddsApiClient, OddsSnapshot, PointInTimeStore, OddsApiResponse, backfill_historical_props(), find_historical_event_id(), pull_historical_prop_snapshot() (+11 more)

### Community 47 - "client.py"
Cohesion: 0.17
Nodes (10): Response, _parse_int_header(), _parse_iso(), datetime, Thin HTTP wrapper around The Odds API. Talks to The Odds API directly (not…, Historical per-event odds, snapshotted at the nearest available timestamp <=…, Shared retry/error-handling for both endpoints. Returns the raw successful…, Bulk endpoint: one call returns every event in the sport's current slate. This… (+2 more)

### Community 48 - "PointInTimeStore"
Cohesion: 0.31
Nodes (14): PointInTimeStore, Regression guard: a schema addition (player_name/prop_stat, added for player…, Regression guard: if `_filter` is ever changed to stop filtering, read_as_of…, _snap(), test_decision_time_must_be_tz_aware(), test_event_id_filter(), test_leakage_guard_fires_if_filter_is_ever_broken(), test_read_as_of_before_any_capture_returns_empty() (+6 more)

### Community 49 - "OddsSnapshot"
Cohesion: 0.27
Nodes (11): BaseModel, OddsSnapshot, Build a snapshot from an American price, deriving decimal + implied prob., A single immutable price observation. `capture_time` is when we observed the…, _snap(), test_favorite_and_underdog_decimal_conversion(), test_from_american_derives_decimal_and_prob(), test_frozen_snapshot_cannot_be_mutated() (+3 more)

### Community 50 - "send_message"
Cohesion: 0.27
Nodes (11): _escape_for_applescript(), RuntimeError, SMS/iMessage alerts via macOS Messages.app. No third-party account, no API key:…, AppleScript/Messages.app failed to send., AppleScript string literals only need backslash and double-quote escaped --…, Send `text` to `phone_number` via Messages.app. Raises SmsError on any failure…, send_message(), SmsError (+3 more)

### Community 51 - "test_monitor_run.py"
Cohesion: 0.52
Nodes (6): _seed_store(), _snapshot(), test_run_does_not_record_a_spot_whose_send_failed(), test_run_does_not_send_or_record_when_phone_not_configured(), test_run_returns_zero_when_no_spots_found(), test_run_sends_and_records_alert_when_phone_configured()

### Community 52 - "demo_pipeline.py"
Cohesion: 0.53
Nodes (5): datetime, main(), make_synthetic_snapshots(), End-to-end pipeline demo: pull -> store -> compare -> decide -> notify. `make…, _step()

### Community 53 - "OddsApiError"
Cohesion: 0.67
Nodes (3): OddsApiError, RuntimeError, Network or unexpected-response failure talking to The Odds API.

## Knowledge Gaps
- **89 isolated node(s):** `Status`, `Data chronology: nflverse (historical) vs. Pinnacle (live)`, `Live monitoring: 24/7 services + SMS alerts`, `Preseason dry run`, `Historical props for backtesting — checked, blocked on paid access` (+84 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PointInTimeStore` connect `PointInTimeStore` to `Side`, `scheduler.py`, `test_live_scan.py`, `market_baseline`, `props.py`, `pit_store.py`, `preseason.py`, `OddsApiResponse`, `OddsSnapshot`, `test_monitor_run.py`, `demo_pipeline.py`?**
  _High betweenness centrality (0.146) - this node is a cross-community bridge._
- **Why does `market_baseline()` connect `market_baseline` to `test_live_scan.py`, `test_evaluate.py`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `Side` connect `Side` to `test_live_scan.py`, `test_collect_transform.py`, `market_baseline`, `props.py`, `PointInTimeStore`, `OddsSnapshot`, `test_monitor_run.py`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Are the 46 inferred relationships involving `PointInTimeStore` (e.g. with `BacktestEngine` and `clv_movement_report()`) actually correct?**
  _`PointInTimeStore` has 46 INFERRED edges - model-reasoned connections that need verification._
- **Are the 51 inferred relationships involving `Side` (e.g. with `BacktestBet` and `BetOrder`) actually correct?**
  _`Side` has 51 INFERRED edges - model-reasoned connections that need verification._
- **Are the 42 inferred relationships involving `Market` (e.g. with `BacktestBet` and `BetOrder`) actually correct?**
  _`Market` has 42 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `OddsApiClient` (e.g. with `main()` and `poll_once()`) actually correct?**
  _`OddsApiClient` has 21 INFERRED edges - model-reasoned connections that need verification._