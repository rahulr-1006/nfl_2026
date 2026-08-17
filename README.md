# nfl-clv

NFL closing line value case study. Thesis and full design: [nfl_clv_case_study_blueprint.md](nfl_clv_case_study_blueprint.md).

The close is close to efficient. The primary metric is **CLV**, not P&L. This repo
builds a leakage-free, point-in-time backtester, four devig methods, a CLV tracker
with honest confidence intervals, and (over the season) a live odds collector.

## Status

Blueprint infrastructure (Days 1-15: scaffold, collector, store/devig, backtester/CLV,
calibration, drift stub) is built and tested. What's left is the live 2026-season case
study itself — the collector has been running since 2026-08-14, and the CLV/drift
results in the paper fill in as the season generates enough data to report on:

- [x] Repo tree, `pyproject.toml`, `Makefile`
- [x] Point-in-time odds snapshot schema (`src/store/schema.py`)
- [x] Append-only PIT store with a leakage guard + regression test (`src/store/pit_store.py`)
- [x] Four devig methods with tests (`src/devig/methods.py`)
- [x] Free static data pull: nflverse schedules + closing lines, 2015-2024 (`src/features/load_static.py`)
- [x] Live odds collector (`src/collect/`) — polls The Odds API (`regions=eu,us`:
      `eu` for Pinnacle, `us` for the DraftKings/FanDuel/BetMGM execution books —
      see "Live monitoring" below for why both are needed), budget-aware scheduler
      that spreads the free tier's 500 credits/month across the billing period and
      degrades to a cheaper market set under pressure, matches events to nflverse
      `game_id`s, writes immutable snapshots to the PIT store. Verified live:
      272/272 events matched, all four books present. Runs 24/7 as a macOS
      launchd service (`make collector-service-install`), not a foreground process
      — see "Live monitoring" below.
- [x] Settlement join: grades moneyline/spread/total win-loss-push against nflverse
      final scores (`src/store/settlement.py`), incl. the NFL-tie push case and a
      regression test guarding nflverse's inverted `spread_line` sign convention
- [x] Odds conversion consolidated into `src/devig/convert.py` (American/decimal/implied
      prob), imported by `src/store/schema.py` as the single source of truth
- [x] CLV tracker (`src/clv/metrics.py`) — probability CLV, price CLV, beat rate,
      bootstrap confidence intervals on mean CLV
- [x] EV / Kelly sizing (`src/signal/sizing.py`) — expected value, full and fractional
      Kelly, bankroll caps (2% max bet, 0.1% min, below-min rounds down to no bet)
- [x] Leakage-free backtester (`src/backtest/engine.py`) — strategy protocol over
      per-game decision points, each re-derived through the PIT store's own
      `read_as_of` leakage guard (not locally sliced); computes price + probability
      CLV anchored to Pinnacle's close, settles P&L via `src/store/settlement.py`.
      Reuses the existing store/settlement rather than a second implementation.
- [x] Market baseline (`src/model/baseline.py`) — devigged Pinnacle close (Shin by
      default), the floor every other model has to beat
- [x] Evaluation framework (`src/model/evaluate.py`) — Brier score, log loss,
      reliability curve, and the power analysis (required-sample-size calc, reported
      before results per blueprint B.5's honesty framing)
- [x] Play-by-play pull/cache (`src/features/load_static.py::load_pbp`) — trims
      nflverse's ~370-column pbp to the 12 columns (`PBP_COLUMNS`) the feature
      builder needs; cached 2015-2024 to `data/static/pbp_2015_2024.parquet`
- [x] Feature builder (`src/model/features.py`) — pre-game rolling offensive/
      defensive EPA-per-play and success rate per team, shifted one game before
      aggregating so a game's own result never leaks into its own pre-game
      feature (regression-tested with a deliberate +100 EPA outlier). Season-
      to-date expanding mean by default, optional trailing-N-game window.
      Joined with schedule context (rest, div_game, roof/surface/weather,
      spread/total) into one row per game via `build_game_features`.
- [x] Model training + calibration (`src/model/train.py`, `src/model/calibration.py`) —
      standardized logistic regression on `build_game_features` output, three-way
      out-of-time split (train/calib/test by season) so no season is used for more
      than one of {fit model, fit calibration, report results}, isotonic/Platt
      calibration via a frozen base estimator. Evaluated against the market
      baseline with `src/model/evaluate.py`'s Brier score / log loss / reliability
      curve. Run with `python -m src.model.calibration`, or see results + a
      calibration chart in
      [`notebooks/model_backtest_results.ipynb`](notebooks/model_backtest_results.ipynb).
      **Trained on nflverse's odds, not Pinnacle — see "Data chronology" below
      before reading these numbers as a CLV result.**
- [x] Drift monitor (`src/drift/monitor.py`) — `rolling_mean_clv` (trailing-window
      mean CLV), `cusum` (two-sided Page CUSUM change-point detector, with a
      `drift`/slack term so expected noise doesn't accumulate into a false
      alarm), `rolling_calibration_drift` (rolling Brier score vs. a reference
      established on the model's original holdout). Built and hand-verified
      against synthetic series now — there's no live CLV time series yet to run
      it on (collection started 2026-08-14), same as the CLV tracker and
      backtester were before real data existed.
- [x] Live +EV scanner + SMS alerts (`src/signal/live_scan.py`, `src/notify/`) —
      compares each execution book's live price against Pinnacle's current
      devigged fair value, texts when the edge clears a threshold (default 2%
      EV). Runs 24/7 as a second macOS launchd service, independent of the
      collector. See "Live monitoring" below.
- [x] Player-prop infrastructure (`src/collect/props.py`, `src/store/prop_settlement.py`)
      — **prepped, not active.** Schema, per-event polling, and settlement
      against nflverse player stats are built and tested; live-checked
      2026-08-17 and confirmed props aren't posted this far before kickoff
      (see "Player props" below for why, and what to check once they start
      filling in).

## Data chronology: nflverse (historical) vs. Pinnacle (live)

Two different odds sources feed this repo, at two different points in the
timeline, and they are **not interchangeable** — mixing them up would quietly
break the project's own honesty framing.

| | nflverse schedule odds | Pinnacle (via The Odds API) |
|---|---|---|
| Coverage | 2015-2024, closing line only, one number per game | 2026-08-14 onward, intraday snapshots every ~4.5h |
| Source | A market-consensus close nflverse aggregates — **not confirmed to be Pinnacle** | Confirmed live: `regions=eu` returns Pinnacle explicitly (verified 272/272 events) |
| Used for | `src/model/train.py`, `src/model/calibration.py` — training and calibration-quality validation (Brier, log loss, reliability) against a market baseline | `src/backtest/engine.py`, `src/clv/metrics.py` — the actual CLV headline result: entry price vs. Pinnacle's close |
| Can it produce a CLV number? | **No.** CLV needs an entry-vs-close snapshot pair; nflverse only has the single closing number, so there's nothing to measure movement against. | Yes — this is the only data that can. |

So `python -m src.model.calibration`'s output (Brier/log loss vs. a market
baseline) is a **calibration-quality result on historical nflverse data**, not
a CLV backtest and not evidence about beating Pinnacle specifically. The CLV
thesis itself stays a live, 2026-season-only claim, reported once the
collector has accrued enough entry/close pairs (paper §5.3). `market_baseline()`
in `src/model/baseline.py` is odds-source-agnostic — it devigs whatever
American odds you hand it — so it's reused for both cases; the caller is
responsible for knowing which source it was fed and framing results
accordingly.

A paid Odds API plan (planned ~2026-08-22) unlocks a *historical* endpoint that
could backfill genuine Pinnacle intraday snapshots, at 10 credits × markets ×
regions per snapshot call (one point-in-time read, not a range). **Checked
2026-08-17: it wouldn't upgrade the model's historical training set.** Historical
data only goes back to 2020-06-06 — five of the ten seasons used for
training/calibration above (2015-2019) are unreachable at any price. For
2020-2024 it would swap "nflverse's unconfirmed consensus close" for "confirmed
Pinnacle," a real but marginal purity gain on the market-baseline comparison
specifically, at real ongoing cost, for a metric (calibration quality) that
doesn't depend on which book the close came from. See
`notebooks/model_backtest_results.ipynb` for the full reasoning. The upgrade is
still worth keeping for its original purpose — live-collector headroom beyond
the free tier's 500 credits/month — just not as a lever for historical training
data.

## Live monitoring: 24/7 services + SMS alerts

Two independent macOS launchd services, both checked into git as
`ops/*.plist` (source of truth) — installing/removing the copies launchd
actually reads is all the `make` targets below do.

**`com.nflclv.collector`** (`make collector-service-install` /
`-uninstall` / `-status`) — the live odds collector, running continuously.
`RunAtLoad` + `KeepAlive` so it survives terminal closes, sleep, and
reboots, and restarts itself if it ever exits. Polls `regions=eu,us`: `eu`
for Pinnacle (the CLV anchor), `us` for DraftKings/FanDuel/BetMGM (the
actual bet-execution books, paper Sec 3.4) — added 2026-08-17 once
comparing them against Pinnacle live became load-bearing (below). This
doubled per-poll credit cost, which the collector's existing budget-aware
pacing (`src/collect/budget.py`) absorbs automatically by spreading polls
further apart: **on the free tier right now, that pencils out to roughly
one poll every ~8.6 hours**, not "live" in the tick-by-tick sense — it'll
tighten up automatically once the paid plan (~2026-08-22) lifts the credit
ceiling, no code change needed, since the pacing math reads the account's
real remaining-credits header rather than a hardcoded budget.

**`com.nflclv.monitor`** (`make monitor-service-install` / `-uninstall` /
`-status`, or `make monitor-scan-once` for a single manual run) — the live
+EV scanner (`src/signal/live_scan.py`) + SMS alerts (`src/notify/`). Runs
every 5 minutes via launchd's `StartInterval` (a short-lived scan-and-exit
script, not a daemon) — cheap and independent of the collector, since it
only reads already-collected local parquet files, no Odds API call of its
own. It's still gated by how often *new* data actually lands, i.e. the
collector's current ~8.6-hour cadence above, not its own 5-minute loop.

**What it does:** for every game, devigs Pinnacle's latest moneyline price
into a fair probability (`src/model/baseline.py::market_baseline`), then
checks whether DraftKings, FanDuel, or BetMGM's *current* price beats that
fair value by real money — `expected_value(p, d)`
(`src/signal/sizing.py`), the same EV math already built for sizing,
just wired to live data instead of a backtest. Default alert threshold:
**2% EV per dollar staked.** Verified live 2026-08-17: found 4 real spots
(FanDuel/BetMGM ~3.6-6.1% EV on two underdog moneylines) on the first real
scan against `regions=eu,us` data.

**Alert dedup:** a spot doesn't re-text every cycle once you've already
been told about it — `data/alert_state.json` (gitignored) tracks the edge
at last-alert time per (event, side, book), and only re-fires if the edge
grows by ≥1 percentage point since then (`src/signal/live_scan.py::new_or_improved_spots`).

**Setup:** add your phone number to `.env` —
```
ALERT_PHONE_NUMBER=+15551234567   # E.164 format
```
via Messages.app on this Mac (iMessage, or SMS via Text Message
Forwarding from a paired iPhone) — no third-party account, no API key.
Without it set, the monitor still scans and logs everything it *would*
have sent (`logs/monitor.log`), just doesn't send. Restart the service
after adding it: `make monitor-service-uninstall && make monitor-service-install`.

**What this is not:** a bet-placement bot. It's a notification channel —
it tells you where the edge is; you still place the bet yourself, by hand,
same as always (see the `bet_execution_scope` memory / paper Sec 3.4). It
also only compares moneyline prices for now — spread/total comparisons
need matching line numbers between books to be a clean apples-to-apples
bet, which is real added complexity, deferred rather than built sloppily.

## Preseason dry run

A third, deliberately separate track: `src/collect/preseason.py` +
`src/clv/preseason_report.py` poll real 2026 preseason odds and measure price/
probability CLV movement, purely to exercise the live pipeline (poll → match →
store → measure) end-to-end before the regular season and the real collector
budget are on the line. **No bets are placed on preseason games** — this is
infrastructure validation, not a betting signal and not part of the paper's
results.

- **Not Pinnacle.** Verified live: `americanfootball_nfl_preseason` carries
  only `fanduel`, `mybookieag`, and `onexbet`, in every region tested (`eu`,
  `us`, `us2`). Pinnacle doesn't trade preseason at all — a signal in itself
  (it's a low-information market not worth pricing tightly), and a reminder
  that a lone book quoting something nobody else does isn't evidence of an
  edge, just a market with no anchor to check it against.
- **Not nflverse-matched.** nflverse's schedules never carry preseason rows
  (`game_type` is only `REG`/`WC`/`DIV`/`CON`/`SB`), so there's no `game_id` to
  join to. Preseason events are identified by The Odds API's own stable event
  `id` instead, prefixed `PRE` (e.g. `2026_PRE_<odds-api-id>`) so they can
  never collide with or be mistaken for a real nflverse `game_id`.
- **Not the same store.** Snapshots land in `data/snapshots_preseason/`, never
  `data/snapshots/` — this data must never leak into the real season's CLV
  numbers.
- **Not scheduled.** Run by hand a few times during the preseason window
  (`make preseason-poll`), not continuously — The Odds API credit pool is
  account-wide, shared with the real collector, and an unattended preseason
  loop would compete with the budget the real season needs.

```bash
make preseason-poll     # one poll: fetch, match, write snapshots
make preseason-report   # entry-vs-latest price/probability CLV per game so far
```

For interactive analysis (raw snapshot inspection, the CLV report as a table, a
line-movement chart per game, plus a pointer to the historical model pipeline),
see [`notebooks/preseason_dry_run.ipynb`](notebooks/preseason_dry_run.ipynb) —
re-run it top to bottom after each new poll. It ends with a dated log section;
add an entry each time you poll so there's a human-readable record alongside
the parquet files' own `capture_time` timestamps.

## Player props (prepped, not active)

The thesis: mainline spreads/totals/moneylines are the most efficiently priced
markets in sports betting — Pinnacle and sharp money hammer them into near-zero
edge. Player props get priced faster, with less scrutiny, and are the more
commonly cited source of real mispricing. Worth building toward — but the
infrastructure (schema, per-event polling, settlement) is ready before any
live data is, on purpose, so turning it on later is a config change, not a
design scramble. Same pattern as the preseason dry run.

**Why it's not running yet — checked live, 2026-08-17 (3.5 weeks before Week
1):**
- Across every region (`us`, `us2`, `eu`, `uk`), only **DraftKings** had
  posted anything for Week 1, and only one market — `player_anytime_td`. No
  passing/rushing/receiving yardage or reception props. No Pinnacle, no
  FanDuel, no BetMGM.
- This matches how the industry actually works: NFL player props are
  typically posted Tuesday-Thursday of *game week*, not weeks ahead like
  mainline markets. There's nothing to poll yet — this isn't a config or
  region problem the way the preseason/execution-book gaps were.
- **The open question this can't answer yet: does Pinnacle even trade NFL
  player props at all?** If not, the whole devig-Pinnacle-then-compare
  methodology (§4.9's live scanner, the CLV backtester) has no anchor for
  props, the same dead end preseason hit. Unknown until props actually exist
  to check.

**What's built, structurally different from the mainline collector:**
- **Different endpoint, different cost model.** Props require
  `/v4/sports/{sport}/events/{eventId}/odds` (`OddsApiClient.get_event_odds`)
  — one call *per game*, not one call for the whole slate. Cost is unique
  markets returned × regions, billed per call.
- **Over/Under props only.** `player_pass_yds`, `player_pass_tds`,
  `player_rush_yds`, `player_rush_tds`, `player_reception_yds`,
  `player_receptions`, `player_reception_tds` (`src/collect/props.py::PROP_MARKET_TO_STAT`).
  Proposition-style markets (`player_anytime_td` and similar) were observed
  live as **single-sided** — no complementary "No" price — so they can't be
  devigged with the existing two-outcome methods at all; deliberately out of
  scope, not just unmapped.
- **Real nflverse game_ids**, unlike preseason — the regular season already
  has real schedule rows, so props reuse the same team-matching
  (`src/collect/transform.py::match_event`) the mainline collector uses, and
  write into the *same* `data/snapshots/` store (just `market=player_prop`),
  not a separate one.
- **Settlement against real stats:** `src/store/prop_settlement.py` grades an
  Over/Under prop against `nflreadpy.load_player_stats()` — passing/rushing/
  receiving yards, TDs, receptions, joined on `(game_id, player_display_name)`.
  Unmatched players or missing stats are left ungraded (`None`), never
  silently dropped or defaulted.
- **Manual invocation only, scoped to the coming week** —
  `make props-poll` (defaults to games in the next 7 days; `make props-poll ARGS=3`
  for a tighter window) — not a launchd service. Per-event calls scale with
  game count, and there's nothing to poll most of the season anyway.

**What to check once props start filling in (~1 week before a game, so watch
starting around 2026-09-02 for the Week 1 opener):** re-run the live checks
above — does Pinnacle show up for any prop market, and which of the seven
supported markets actually have depth across DraftKings/FanDuel/BetMGM. That
determines whether §4.9's live scanner and the CLV backtester can extend to
props at all, or whether props end up scoped to calibration-only analysis the
way the historical nflverse odds are (see "Data chronology" above).

## Quickstart

```bash
make install   # creates .venv, installs -e .[dev]  (includes jupyter + matplotlib)
make test       # runs the test suite
jupyter lab notebooks/preseason_dry_run.ipynb   # interactive analysis
```

**Notebook kernel:** if you're on a machine with other Python environments around (e.g.
a conda env used for unrelated projects), don't run this repo's notebooks under one of
those — this project needs Python 3.11+ (`pyproject.toml`) and its own dependencies.
Register this repo's own `.venv` as a named kernel once:

```bash
.venv/bin/python -m ipykernel install --user --name nfl-clv --display-name "Python (nfl-clv)"
```

Then select **"Python (nfl-clv)"** in your notebook UI. In VS Code, if it doesn't show
up under the kernel picker's "Jupyter Kernel" list, use "Select Another Kernel" →
"Python Environments..." → "Enter interpreter path..." and point it straight at
`.venv/bin/python`.

## Repo tree

```
nfl-clv/
  data/
    static/            # free historical CSVs/parquet (nflverse)
    snapshots/          # append-only intraday captures, real season (parquet, partitioned by date)
    snapshots_preseason/ # append-only intraday captures, preseason dry run (separate from the above)
  src/
    collect/           # live odds collector + scheduler + preseason/props pollers
    store/              # point-in-time store, leakage guards, settlement (team + player prop)
    devig/              # the four devig methods + tests
    features/            # feature builder from snapshots + play-by-play
    model/               # baseline (market) + your model + calibration
    signal/              # EV/Kelly sizing under the 2% cap + live +EV scanner
    notify/               # SMS alerts (Messages.app) + the live monitor entrypoint
    backtest/            # leakage-free simulator
    clv/                 # CLV tracker + bootstrap CIs + preseason CLV-movement report
    drift/               # non-stationarity monitor
  ops/                  # launchd service plists (collector, monitor) -- source of truth
  logs/                 # service stdout/stderr (gitignored)
  tests/                # unit + property tests (leakage, devig sums to 1, etc.)
  notebooks/            # interactive analysis (preseason_dry_run.ipynb, model_backtest_results.ipynb)
  paper/                # the case study, written as you build
```
