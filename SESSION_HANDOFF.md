# Session handoff — 2026-09-21 (updated 2026-10-04, 2026-10-13)

## 2026-10-13 update — read this first

Everything is committed (main is ~30 commits ahead of origin, **not pushed**).
1021 tests pass, ruff clean, 0 unreferenced modules.

**Verified live state:** all 3 services up; no collection gap >3h since 9/21;
0 tracebacks since 10-04; 79,204 paid credits left (≈51K/month pace); disk 93%
(Spotify cache, not this repo). `bet_log.jsonl` still doesn't exist.

**Decision report 10-13:** nothing is GO. `moneyline_ev` NO (n=104),
`prop_ev` NO (n=178), `steam` NO (n=61), `middle` HOLD (n=10),
`prop_arb` HOLD (n=24/30, expected_capture +0.0048, an upper bound).

**Pre-registration:** committed **6 days late** (deadline 10-07; Week 5 had
been played). Both consequences are logged in §6: (1) the late commit itself,
with the 10-04 evidence; (2) H2/H3 dropped from the Weeks 5–9 family, so the
BH family is {H1, H1b}. Score on/after 11-10 with
`make prereg-score WEEKS=holdout`. It refuses to run earlier. Its rushing-yards
exclusion follows §3's calibration gate. Confirm you agree before 11-10.
`python -m scripts.h1_train_grid` reproduces the frozen Train numbers exactly.

**Fixed today:**
1. `.env.bak-*` (both API keys plus the phone number) was not gitignored in a
   public repo. Now `.env*`. It was never committed.
2. `random_bet_benchmark` paid the listed price to the opposite side. It now
   uses the real opposite quote (§6 deviation, no bets change).
3. Props for 7 players could never settle (Jr/Sr suffixes, Hollywood/Marquise
   Brown, Joshua/Josh Palmer). Settlement coverage on Weeks 1–5 went from
   93.1% to 94.9%; the rest didn't play (books void those).
4. **Monitor tick 16–18 min → ~8 min.** `PointInTimeStore` caches its
   deduped read per instance, keyed on the file listing (verified identical to
   an uncached read on the real store).
5. Two notebooks were **broken**, not just stale: the required `vig` and
   `event_id` arguments were never passed, and the props section had silently
   grown from 2024-only to the whole store, live 2026 included. Both fixed and
   re-run; results unchanged in substance.
6. Schedule and player_stats re-pulled through Week 5 (re-pull again before
   any settlement). No Week 6+ kickoff moved.

**Trades:** settlement and the team-total build key on (game_id, name) from
that game's own stats row, so trades are safe by construction. 0 same-game
name collisions in 2026.

**Still open (your call):** push to origin; `team_total_scan` exposure cap;
whether "clear" must also require the CI to exclude zero; the paper §4.7 power
analysis; notebooks have no smoke test, which is how two of them broke unnoticed.

---


## 2026-10-04 update — read this first

The 9/29 decision was pushed to **Monday 2026-10-05**. Changes made today, all
tested (981 passed, ruff clean), staged, **not committed**:

1. **Kickoff timezone bug fixed.** nflverse `gameday`/`gametime` are US/Eastern;
   `collect/run.py` and `backtest/engine.py` parsed them as UTC, putting every
   kickoff 4h early (5h under EST). The collector then thought TNF/MNF had
   started and fell to its 60-min sparse cadence for the last ~4h (measured:
   PIT@CLE 10/1 gaps of 60-124 min; NYG@LA 9/21 the same). Shared parser now
   lives in `features/load_static.kickoffs_utc`; validated against the Odds API's
   own kickoffs (45/46 within 3.4 min, London games included). **Historical
   BacktestEngine runs before today used kickoffs 4-5h early** -- their "close"
   was a pre-close price. The decision report is unaffected (it reads kickoffs
   from the store).
2. **Yardage props now polled every 15 min in the final 12h.**
   `props_budget.MOVEMENT_MARKETS` (pass/rush/reception yds) ride along on the
   arb tier's calls; `ARB_MARKETS` itself is unchanged. Arb poll cost 4 -> 10.
   Expect ~+20K credits/month (was ~47K/month projected, now ~67K of 100K).
   Side effect: the props arb scanner now sees yardage lines at 15-min
   resolution too, so `prop_arb` alerts may include more yardage arbs.
3. **2026 schedule + player_stats re-pulled** (backups `*.bak-20261004`).
   Weeks 1-4 now settle; CHI@GB Week 5 flexed 16:25 -> 13:00 ET.
4. **API key redacted from client errors** (it was logged via the request URL
   on DNS failures); existing log lines masked.
5. **Disk filled 9/22-23** (`No space left on device`, 3 early-tier props polls
   lost after being paid for). Not this repo (store is 97 MB): the Spotify cache
   is 20 GB. Still 94% full until cleared.

Services restarted 2026-10-04 15:28 ET to load 1-2.

**Deliberately not done:** placeholder quotes (pmu_fr/betfair_ex_eu at -10000,
gtbets spreads at -100000; 396 pre-kickoff rows, 16 games, never Pinnacle) are
NOT filtered. Verified 0 of 5,134 shadow-log rows involve those books, so they
affect nothing live. Filter them in any backtest that averages or devigs across
books.

~~**Still open:** bankroll rule and entry-horizon policy~~ — both decided later
on 10/04 (items 3 and 4 below).

### Later on 2026-10-04: pre-registration + Train analysis + live H1/H1b

- **`preregistration_wk5-9.md`** (uncommitted draft): Train = Weeks 1–4,
  holdout = Weeks 5–9 (scored once, on/after 11-10). **H1 frozen at M=2pp,
  E=1%; H1b registered** (both by the user). Must be **committed before Wed
  10-07 23:59 ET**; open [DECIDE] items are listed in
  `analysis/train_results_2026-10-04.md` §9.
- **Metric change:** price-based strategies are scored on **closing EV**
  (price paid × Pinnacle's devigged close − 1). `clv_probability` never sees the
  price paid. Pinnacle's close passed calibration for props (except **rushing
  yards**) and for moneylines (except **short underdogs**, fair .333–.5).
- **H1/H1b are LIVE, LOG-ONLY** via `src/signal/prereg_scan.py` in the monitor,
  writing `data/shadow_log_prereg.jsonl`. **Do not merge that file into
  `data/shadow_log.jsonl` and do not score it before 11-10.** The separate file
  is what blinds it from decision/shadow/clv reports. Verified live: first ticks 19:25 and
  19:41 ET logged 4 + 2 H1b legs, 0 H1, no tracebacks, 0 prereg rows in the main
  log. **Cost:** the prereg block adds ~2m00s per tick (one store read in the
  service), down from 2m49s after `ReadOnceStore` shared the read with its
  recheck. It runs last, so it never delays a tick's own alerts, but it does
  push back the next tick.
- **Monitor cadence is ~10–13 min, not 5.** In the service a tick took ~4.5 min
  (01:30→01:34 ET), and launchd skips a start while one is still running. Each
  scanner re-reads the full store (8–24s apiece standalone). The real worst-case
  alert latency is ~28 min, not the documented ~20. Not fixed: sharing one store
  read per tick means refactoring the live alert path, which is the user's call.
- **Tooling flaw:** `evaluation.random_bet_benchmark`'s null is invalid for
  plus-money prices (see ARCHITECTURE.md, `pinnacle_lag.py` row).

---

Point a new session at this file. It records **live state verified today**, not
remembered state. Everything below was checked by running it, and where a number
appears it came from a command, not from recall.

Two companion docs carry the durable content; this file is the pointer and the
open-items list:

- **`ARCHITECTURE.md`** — what runs, what's orphaned, per-strategy verdicts.
- **`methodology_backlog.md`** — the standing-reference vig table, the
  probability-estimation-vs-structural design rule, and every tried idea with
  its outcome. **Read its "Standing reference" section before proposing any
  prop strategy.**

---

## THE DEADLINE: 2026-09-29

The no-bet observation window (`src/clv/shadow_clv.py`, "the plan for weeks 1-3")
expires after Week 3. **`make decision-report` on 9/29 is the go/no-go meeting.**

The bar was fixed 2026-09-14, *before* the Week 2/3 data existed, and must not be
tuned to what the season produced:

```
directional:  n >= 30 measurable legs  AND  beat_rate > 50%  AND  mean_clv > 0
structural:   n >= 30 alerts           AND  expected_capture > 0
```

`prop_arb` is the only structural strategy. It is **not** scored on CLV: an arb is
market-neutral by construction, so its mean_clv ~ 0 is the predicted value, and
applying the CLV bar would retire it for a mathematically guaranteed reason.

**If nothing clears, nothing gets bet.** 9/29 is a checkpoint, not a start gun.

---

## Standing constraints (violating these has been called out before)

- **The user writes commit messages.** Stage changes; do not draft-and-run a
  commit unless asked. No `Co-Authored-By: Claude` line in this repo.
- **Do not edit or reference `README.md`** — a different agent owns it.
- **Do not reference the user's other quant/portfolio goals** in this project.
  They decide when this project stops.
- **Bankroll is $100 with at most 2 manual reloads ($300 total risk capital)** —
  decided 2026-10-04, matches `paper:1390`. Bets are placed **manually**; no bots.
- **Two Odds API keys, but the mainline collector now uses the PAID one**
  (`COLLECT_USE_PAID_KEY`, 2026-09-08). `ODDS_API_KEY` = free 500/mo;
  `ODDS_API_KEY_PAID` = 100,000/mo **recurring, refills on the 1st**. Confirmed
  empirically: the balance jumped 3,675 -> 99,990 across the 09-01 00:40 UTC
  boundary. Cached balances are key-fingerprinted so one key's balance can never
  pace the other.
- Notebooks need the **`nfl-clv` kernel** (`.venv`), not the `algobetting` conda env.

---

## Verified live state (2026-09-21)

| Thing | Value | How checked |
|---|---|---|
| Test suite | **976 passed** | `pytest -q` |
| Lint | **clean** | `ruff check src tests scripts` |
| Audit | **0 undecided orphans, 0 unreferenced**, 65 modules | `make audit` |
| Snapshot store | 3,650,263 rows (917,227 props) | `read_as_of(now)` |
| Last capture | 2026-09-21 19:42 UTC | same |
| Paid credits left | **82,860** of 100,000 (refills 10/01) | `data/props_collect_state.json` |
| Shadow log | 2,699 legs | `wc -l` |
| `data/bet_log.jsonl` | **does not exist** — zero bets placed (correct: no-bet window) | `ls data/` |
| launchd services | all three RUNNING | `launchctl list \| grep nflclv` |
| Health checks | both OK | `health_check.check_all` |

### Concurrency verified under live-time replication (2026-09-21)

Not tested in isolation — **eight entrypoints were run concurrently against the
three live services**, then invariants were checked before/after:

| Check | Result |
|---|---|
| 4 scanners in parallel (`team-total`, `middle`, `steam`, `shadow-report`) | all exit 0 |
| 4 live-path entrypoints in parallel (`monitor-scan-once`, `season-review`, `decision-report`, `clv-report`) | all exit 0 |
| Store duplicate rows in the live era | **0** of 3,069,989 — the services are not racing |
| Credit counters across the run | unchanged; no double-spend |
| `alert_state.json` | 44 entries, stable; monitor correctly reported "none new/improved" |
| Shadow log length | stable; no concurrent double-append |

**What this run FOUND (now fixed, commit `7c6ad94`):** 22 of 96 `prop_ev` and 18
of 65 `moneyline_ev` alert legs were the same contract logged more than once —
23% and 28% non-independent observations inflating the metric the 9/29 decision
reads. Two causes: `find_live_prop_ev_spots` had no latest-capture-per-contract
filter (the arb scanner already did), and `live_scan` re-alerts on an improved
edge, which is right for alerting and wrong for measurement. **Isolated unit
tests could not have found this** — it only appears in accumulated live data.

### Props close capture — the deferred verification, now DONE

`CLOSE_CAPTURE_HOURS = 1.5` (2026-09-02) was applied but never verified against
real games. Checked today across all 31 played 2026 games:

```
prop_stat         games  games_with_close_<=2.0h   pct
passing_tds          31                       31  100.0
passing_yards        31                       31  100.0
receiving_yards      31                       31  100.0
receptions           31                       31  100.0
rushing_yards        31                       31  100.0
```

**Props CLV is computable for every market that exists.** Only 5 markets appear,
not 7 — `rushing_tds` and `reception_tds` are not quoted by any book in our data.
That is book coverage, not a collection gap. This closes the
"5 of 7 markets silently uncomputable" concern in `methodology_backlog.md`.

---

## Current decision table (2026-09-21, 8 days out)

```
strategy          n    beat mean_clv             95% CI    surv            verdict
moneyline_ev     31  61.3% +0.0043  [-0.0038,+0.0127]  76.2%                 GO
prop_arb*         9  44.1% -0.0000  [-0.0127,+0.0125]  73.7% HOLD (n=9, need 30)
prop_ev          73  28.8% -0.0095  [-0.0173,-0.0013]  60.5%                 NO
steam            23  34.8% -0.0128  [-0.0226,-0.0032]  95.7% HOLD (n=23, need 30)
```

Read this carefully, because the verdict column alone is misleading:

- **`moneyline_ev` GO is weak and should be treated as such.** Its CI includes
  zero, so this data cannot distinguish its mean CLV from zero; n=31 is one leg
  over the bar; and it is the market this project's own backtests say it reliably
  loses to. The report says so in its own output. The bar is a point-estimate
  test and was **not** changed after seeing this — that is deliberate.
- **`prop_ev` is now a real NO**, with the CI entirely below zero after the
  dedup fix. Consistent with the original null backtest on 6,812 bets.
- **`prop_arb` is the one to watch.** Capturability became measurable only after
  the arb-latency cut (commit `d0d3adb`): `both_legs = 44.4%`,
  `expected_capture = +0.0054`. It needs n=30 and is at 9.
  ⚠️ `one_leg_only = 55.6%` is **naked exposure**, not a near-miss, and is not
  charged as a cost — so `expected_capture` is an upper bound.
- **`steam` has the best survival (95.7%) and negative CLV.** Highly placeable,
  currently losing. It will not reach n=30 by 9/29.

---

## Open items before 9/29, in priority order

### 1. Let the data accumulate — do NOT ship new strategies
Weeks 2 and 3 are the entire remaining sample. `prop_arb` needs to go 9 -> 30
alerts and `moneyline_ev` needs to hold up past n=31. The scarce resource is
game-weeks, not engineering time.

### 2. ~~Exercise `make log-bet` for real before betting on it~~ — DONE 2026-09-27
Four real shadow-log alerts on completed Week 1 games replayed through the full
loop (log -> `--list` -> `--corrects` -> `to_backtest_bets` -> `settle_bets` ->
`review_all`) into a throwaway path. `data/bet_log.jsonl` still does not exist.

**It found three real bugs, all now fixed. None was reachable from unit tests.**

1. **Nothing could settle.** All four bets returned `UNSETTLED` with the bankroll
   frozen at $100.00, on games played two weeks earlier.
   `data/static/schedules_2026_2026.parquet` was pulled **2026-08-14**, before
   the season, so all 272 games had NaN scores, and `player_stats` had zero 2026
   rows. **This fails silently:** `_grade` returning `None` is legitimate for an
   unplayed game, so `season_review` prints "settled 0 of N; bankroll $100.00"
   and warns only if the schedule is *empty*, never if it is full of NaN scores.
   Fixed by re-pulling `load_schedules([2026])` + `load_player_stats([2026])`
   (free, no API credits). All four then graded correctly and check out against
   reality (LV 27-13 MIA; Breece Hall exactly 2 receptions).
2. **`active_bets` deleted any bet you corrected.** The superseded filter matched
   on `placed_at` value, so a correction reusing that instant — what the
   docstring tells you to do, since `placed_at` is when the bet was *struck* —
   dropped the original *and* the correction. The bet vanished from settlement,
   bankroll and review entirely. Now matched by which row corrects which.
3. **The stale schedule had no international venues at all**, mapping all 7
   neutral-site 2026 games to domestic stadiums — so `add_rest_travel_features`
   produced a *confidently wrong* travel distance (SF->LA for Melbourne), not a
   missing one. MEL00/RIO00/MAD01/PAR00/MUN01 added to `STADIUM_COORDINATES`.

**Standing lesson:** the static nflverse cache does not self-refresh and nothing
warns when it is stale. Re-pull 2026 schedules + player_stats before trusting any
settlement, P&L or bankroll number, and read "settled 0 of N, bankroll unchanged"
as a stale-cache symptom, not a correct no-op.

### 3. ~~Resolve the bankroll contradiction~~ — DONE 2026-10-04
$100 + up to 2 manual reloads ($300 total), per `paper:1390`. Code comments
aligned. Reloads are not tracked in code: at a $2 max bet, busting $100 takes
~50 straight losses, so the accounting would never fire this season.

### 4. ~~Write an entry-horizon policy~~ — DONE 2026-10-04
User's rule: **no time restriction** — entry is allowed any time up to ~1 minute
before kickoff. The constraint is signal clarity, not timing:

1. Only alerts from a strategy whose decision-report verdict is GO.
2. At placement, the book's price must be **equal to or better than** the alerted
   price. Worse = skip; alerts can be up to ~20 min old (15-min poll + 5-min
   monitor), and a moved price is a different bet.

Background kept for the record: sigma falls toward kickoff (0.0351 -> 0.0143,
`methodology_backlog.md:721-728`), so early entries carry more edge AND more
noise; the user accepts either end.

**Open question raised with the user, not decided:** whether "clear" should also
require the strategy's 95% CI to exclude zero. Under that stricter reading,
nothing qualifies as of 10/04 — `moneyline_ev`'s CI is [-0.0024, +0.0081].

### 5. Decide `team_total_scan`'s exposure cap
It is a manual `make` target, deliberately NOT in `monitor_run`, so it never
passes through `_apply_exposure_cap`. Ceiling ~14 spots/week against a $100
bankroll. It fired 2 spots today (`2026_02_NYG_LA` passing +9.8%, rushing +4.5%).
Wire it with a cap, or leave it manual — but record the decision.

### 6. Known-stale, non-blocking
- `notebooks/model_backtest_results.ipynb` has stale cell outputs; needs a
  re-run on the `nfl-clv` kernel.
- `paper` §4.7's power analysis is known-wrong (n≈3140 rests on an assumed
  sigma 3-7x too large; corrected conclusion is that a 1% edge is detectable at
  n=17-97). Still in the text.
- `paper` §5 Results is an empty skeleton — correct, it fills from the season.
- `make middle-scan-once` / `steam-scan-once` report finished games. This is **by
  design** (`movement_scan.py:8` — the backtest scanners deliberately do not
  filter; the LIVE path in `monitor_run` does, via `upcoming_only`). Do not
  "fix" it, and do not read their output as actionable.

---

## The one thing that cannot be recovered

Every historical prop row purchasable from the API is a single
~20-minutes-to-kickoff snapshot. **Pre-kickoff movement exists only if the
services were up when it happened.** A collection gap between now and 9/29 is not
re-buyable at any price. Uptime outranks every item above.
