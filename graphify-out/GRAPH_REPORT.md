# Graph Report - nfl_2026  (2026-08-17)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 664 nodes · 1864 edges · 24 communities (23 shown, 1 thin omitted)
- Extraction: 83% EXTRACTED · 17% INFERRED · 0% AMBIGUOUS · INFERRED: 323 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c07746ae`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11

## God Nodes (most connected - your core abstractions)
1. `Side` - 81 edges
2. `PointInTimeStore` - 75 edges
3. `Market` - 60 edges
4. `OddsApiClient` - 38 edges
5. `OddsSnapshot` - 33 edges
6. `Outcome` - 32 edges
7. `settle()` - 28 edges
8. `tick()` - 25 edges
9. `OddsApiError` - 24 edges
10. `MatchResult` - 24 edges

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

## Communities (24 total, 1 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (96): BacktestBet, BacktestEngine, BetOrder, DecisionPoint, _latest_fair_prob(), _latest_price(), _parse_kickoffs(), _payout() (+88 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (73): BlockingScheduler, date, CollectorState, current_period_end(), decide_poll(), _game_interval_minutes(), load_state(), _minutes_since() (+65 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (73): main(), Live +EV monitor entrypoint: `python -m src.notify.monitor_run`. Meant to be…, One scan-and-alert cycle. Returns the number of alerts actually sent. Never…, run(), _escape_for_applescript(), RuntimeError, SMS/iMessage alerts via macOS Messages.app. No third-party account, no API key:…, AppleScript/Messages.app failed to send. (+65 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (72): build_preseason_match(), main(), poll_once(), Preseason dry-run collector: same collection mechanics as the real season…, One poll: fetch, match, transform, write. Returns counts for logging/testing --…, Build a MatchResult straight from the Odds API event, no nflverse schedule…, event_odds_to_prop_snapshots(), main() (+64 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (63): CalibratedClassifierCV, compare_to_baseline(), fit_calibrated_model(), predict_calibrated_proba(), DataFrame, Pipeline, Series, Calibration layer (blueprint Part E): Platt scaling / isotonic regression on… (+55 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (50): model_validator, beat_rate(), bootstrap_ci(), clv_price(), clv_probability(), Closing Line Value metrics (blueprint Part B.3). CLV is measured two ways --…, How far the fair market moved toward your side after you bet. Positive means…, Whether the decimal price you took beats the closing price for the same side.… (+42 more)

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (46): Response, Session, OddsApiClient, OddsApiResponse, _parse_int_header(), _parse_iso(), datetime, RateLimitExceeded (+38 more)

### Community 7 - "Community 7"
Cohesion: 0.10
Nodes (34): BaseModel, LeakageError, PointInTimeStore, DataFrame, datetime, Path, RuntimeError, The only read path. Returns rows visible at `decision_time`, and nothing later. (+26 more)

### Community 8 - "Community 8"
Cohesion: 0.12
Nodes (30): compare_methods(), compare_methods_table(), devig_additive(), devig_multiplicative(), devig_power(), devig_shin(), DevigResult, overround() (+22 more)

### Community 9 - "Community 9"
Cohesion: 0.21
Nodes (19): build_game_features(), DataFrame, Feature builder (blueprint Part E): team-strength proxies from play-by-play.…, Collapse play-by-play to one row per (game_id, team): offensive and defensive…, Pre-game rolling team-strength features, one row per (game_id, team). `window`…, One row per game_id: home/away pre-game rolling EPA features plus the schedule…, rolling_team_strength(), team_game_epa() (+11 more)

### Community 10 - "Community 10"
Cohesion: 0.18
Nodes (18): cusum(), first_flag_index(), ndarray, Non-stationarity / drift monitor (blueprint Part E, "the genuinely hard part").…, Index of the first True in `flagged`, or None if it never fires., Trailing rolling mean CLV, one value per bet. Uses whatever history exists so…, Two-sided CUSUM change-point detector. `upper` accumulates evidence of a…, Rolling Brier score over the trailing `window` predictions, minus a… (+10 more)

## Knowledge Gaps
- **1 isolated node(s):** `nfl-clv`
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `PointInTimeStore` connect `Community 7` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 5`, `Community 6`?**
  _High betweenness centrality (0.236) - this node is a cross-community bridge._
- **Why does `market_baseline()` connect `Community 5` to `Community 2`, `Community 4`?**
  _High betweenness centrality (0.155) - this node is a cross-community bridge._
- **Why does `Side` connect `Community 0` to `Community 2`, `Community 3`, `Community 5`, `Community 7`?**
  _High betweenness centrality (0.133) - this node is a cross-community bridge._
- **Are the 61 inferred relationships involving `Side` (e.g. with `BacktestBet` and `BetOrder`) actually correct?**
  _`Side` has 61 INFERRED edges - model-reasoned connections that need verification._
- **Are the 50 inferred relationships involving `PointInTimeStore` (e.g. with `BacktestEngine` and `clv_movement_report()`) actually correct?**
  _`PointInTimeStore` has 50 INFERRED edges - model-reasoned connections that need verification._
- **Are the 42 inferred relationships involving `Market` (e.g. with `BacktestBet` and `BetOrder`) actually correct?**
  _`Market` has 42 INFERRED edges - model-reasoned connections that need verification._
- **Are the 24 inferred relationships involving `OddsApiClient` (e.g. with `main()` and `poll_once()`) actually correct?**
  _`OddsApiClient` has 24 INFERRED edges - model-reasoned connections that need verification._