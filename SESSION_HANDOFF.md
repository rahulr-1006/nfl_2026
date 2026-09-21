# Session handoff — 2026-09-21

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
- **Bankroll is a fixed $100.** Bets are placed **manually**; no bots.
  ⚠️ **This contradicts `paper:1390`**, which allows up to 2 reloads ($300). See
  open item 3 — unresolved, and it must be settled before money moves.
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

### 2. Exercise `make log-bet` for real before betting on it
`data/bet_log.jsonl` has never existed. The command has only ever been run with
`--path` against a throwaway file. If the first real use is the first real bet,
any workflow bug costs money. **Do a dry run into a temp path, end to end,
including `settle_bets`.**

### 3. Resolve the bankroll contradiction (blocking)
Fixed $100 no top-ups (this file, `monitor_run.py:90`) vs. up to 2 reloads /
$300 (`paper:1390`). Both are written as settled. Pick one.

### 4. Write an entry-horizon policy (blocking)
`methodology_backlog.md:721-728`: sigma falls monotonically toward kickoff
(0.0351 -> 0.0143), so **entering early maximises edge and noise together.**
Recorded as "a real design tension … not resolved here." There is no written
rule for when to enter. If anything clears the bar, this is needed immediately.

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
