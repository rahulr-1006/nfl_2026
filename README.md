# nfl-clv

NFL closing line value case study. Thesis and full design: [nfl_clv_case_study_blueprint.md](nfl_clv_case_study_blueprint.md).

The close is close to efficient. The primary metric is **CLV**, not P&L. This repo
builds a leakage-free, point-in-time backtester, four devig methods, a CLV tracker
with honest confidence intervals, and (over the season) a live odds collector.

## Status

Day 1-2 scaffold, in progress:

- [x] Repo tree, `pyproject.toml`, `Makefile`
- [x] Point-in-time odds snapshot schema (`src/store/schema.py`)
- [x] Append-only PIT store with a leakage guard + regression test (`src/store/pit_store.py`)
- [x] Four devig methods with tests (`src/devig/methods.py`)
- [x] Free static data pull: nflverse schedules + closing lines, 2015-2024 (`src/features/load_static.py`)
- [x] Live odds collector (`src/collect/`) — polls The Odds API (`regions=eu` for
      Pinnacle), budget-aware scheduler that spreads the free tier's 500 credits/month
      across the billing period and degrades to a cheaper market set under pressure,
      matches events to nflverse `game_id`s, writes immutable snapshots to the PIT store.
      Verified live: 272/272 events matched, Pinnacle present. Run with `make collect`
      (continuous) or `make collect-once` (single poll).
- [ ] Backtester, CLV tracker, calibration, drift monitor

## Quickstart

```bash
make install   # creates .venv, installs -e .[dev]
make test       # runs the test suite
```

## Repo tree

```
nfl-clv/
  data/
    static/            # free historical CSVs/parquet (nflverse)
    snapshots/          # append-only intraday captures (parquet, partitioned by date)
  src/
    collect/           # live odds collector + scheduler
    store/              # point-in-time store read/write + leakage guards
    devig/              # the four devig methods + tests
    features/            # feature builder from snapshots + play-by-play
    model/               # baseline (market) + your model + calibration
    signal/              # edge flag + Kelly sizing under the 2% cap
    backtest/            # leakage-free simulator
    clv/                 # CLV tracker + bootstrap CIs
    drift/               # non-stationarity monitor
  tests/                # unit + property tests (leakage, devig sums to 1, etc.)
  paper/                # the case study, written as you build
```
