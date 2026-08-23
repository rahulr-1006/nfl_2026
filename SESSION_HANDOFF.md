# Session handoff — 2026-08-23

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

## Standing constraints (violating these has been called out before)

- **The user writes commit messages.** Stage changes; do not draft-and-run a
  commit. No `Co-Authored-By: Claude` line in this repo.
- **Do not edit or reference `README.md`** — a different agent owns it.
- **Do not reference the user's other quant/portfolio goals** in this project.
  They decide when this project stops.
- **Bankroll is a fixed $100, no top-ups.** Bets are placed **manually**; no
  bots. If it busts, the experiment ends.
- **Two Odds API keys.** `ODDS_API_KEY` (free tier, live mainline collector) vs
  `ODDS_API_KEY_PAID` (the 100K grant, historical + props). Do not mix them —
  using the free key for props starves the mainline collector.
- **The paid 100K was a one-time grant, not a recurring monthly allowance.**
  Budget accordingly.
- Notebooks need the **`nfl-clv` kernel** (`.venv`), not the user's `algobetting`
  conda env.

---

## Verified live state (2026-08-23)

| Thing | Value | How checked |
|---|---|---|
| Test suite | **780 passed** (773 + 7 props-freshness) | `pytest -q` |
| Lint | **5 pre-existing errors** in `clv/metrics.py`, `collect/run.py`, `devig/methods.py`, `store/pit_store.py` (UP035/UP017/I001 — newer ruff than when "clean" was recorded; untouched by recent work, all auto-fixable) | `ruff check src/` |
| Snapshot store | 615,643 rows, 462,249 of them props | `read_as_of(now)` |
| Last capture | 2026-08-23 10:44 UTC | same |
| Paid-key credits left | **25,087** | `data/props_collect_state.json` |
| launchd services | `com.nflclv.collector` (pid 6121), `com.nflclv.props` (pid 83945), `com.nflclv.monitor` (interval) | `launchctl list \| grep nflclv` |

### The props situation — read this before touching the scheduler

Live props **posted 2026-08-23 for the 9/9 opener, 17 days out** — far earlier
than the ~9/2 this project originally assumed (that assumption was wrong and the
old 5-day window was silently skipping them; window is now 21 days).

`prop_book_coverage` against the live store returns:

```
{'pinnacle_present': False, 'books': ['betrivers', 'fanduel'],
 'n_prop_rows': 142, 'n_games': 2}
```

**Careful:** a naive `df[df.market=='player_prop'].book.unique()` shows Pinnacle,
because the 2023–24 historical backfill is in the same store. Pinnacle is *not*
quoting anything upcoming. `prop_book_coverage` filters via `upcoming_only()`.
This exact confusion already caused a real bug once — 874 of 879 alerts fired on
already-played games before `upcoming_only` existed.

**Three questions already answered with measurement — do not re-derive:**

1. **The polling window needs no retuning when Pinnacle appears.** Poll targets
   are absolute hours-before-kickoff, so a lagging `poll_count` catches up then
   waits. Simulated with Pinnacle withheld to 4 days out: 34/34 slots used, 23
   captures inside the final 48h.
2. **Seasonal drift in Pinnacle's posting time self-absorbs** — same property,
   plus empty polls cost 0 credits and `poll_count` advances only on capture.
3. **Anchored EV will fire ~14 alerts/week** at the 5% gate (479 of 32,226
   contract-sides). **Those spots tested null on 6,812 settled bets.** A burst of
   `[EXPERIMENTAL]` prop-EV texts the week Pinnacle starts quoting is the
   *predicted* behaviour, not a discovery. Do not loosen the 5% gate in response.

Full detail lives in `methodology_backlog.md` → "What to expect once Pinnacle
starts quoting props".

---

## Open items, in the order they should be picked up

### 1. ~~Orphaned modules~~ RESOLVED 2026-08-23

All 9 tested-only modules decided; `make audit` reports **0 undecided, 0
unreferenced**. Wired: `team_total_scan` (`make team-total-scan-once`),
`season_review` (`make season-review`, which pulls in `evaluation` and
`drift/monitor`). Parked with reopen conditions in their own docstrings:
`props_historical`, `mainline_historical`, `individual_pass_rush_elo`,
`prop_projection`, `closing_line`, `parlay`.

**The blocker this uncovered is now fixed too:** nothing recorded a placed bet,
so CLV could not be computed for any real bet. `src/store/bet_log.py` +
`make log-bet`. See methodology_backlog.md.

### 2. Stale data files — VERIFIED unreferenced, awaiting your call

```
data/static/{pbp,injuries,schedules,rosters_weekly,player_stats}_2015_2024.parquet
```

Grepped `src/`, `tests/`, `notebooks/` on 2026-08-23: **0 references to any of
the five.** 11MB total. Safe to delete, but not deleted -- data is preserved by
standing rule, so this is a decision, not a task.

### 3. ~~`market_write_freshness` -> alert~~ DONE 2026-08-23

`check_props_write_freshness` in `src/notify/health_check.py`, wired into
`check_all`, so `monitor_run` texts it through the existing path. Own thresholds
(120h early / 30h sparse / 12h dense) because the props collector polls a coarser
tiered schedule; freshness measured over `upcoming_only` rows so the 2023-24
backfill cannot pass as live activity; no upcoming props = healthy, not an alert.

### 4. ~~Full concurrent dry run~~ DONE 2026-08-23

All three services observed running simultaneously through overlapping cycles.
Verified, each by running it rather than by inspection:

| Check | Result |
|---|---|
| Three services concurrent | `collector` pid 6121, `props` pid 92314, `monitor` (interval) — all status 0 |
| Store integrity under concurrent writes | **0 duplicate rows in the live era** (capture_time >= 2026-08-01). The services are not racing. |
| Props service reload | `bootout`/`bootstrap` clean; per-event `poll_count` state survived intact |
| Health checks | both report OK correctly — collector 0.3h, props 6.9h against a 120h early-tier limit |
| Manual scanners alongside live services | `team_total_scan` and `steam_scan` both ran clean; steam found 2 real stale-line spots |
| Credit accounting | free key 341 (−6 per poll, ~9h05m cadence); paid key 25,076 unchanged — empty prop probes really are free |

**Collector cadence, measured:** it polls every **~9h05m**, not every 5 minutes.
The apscheduler tick is 5 min but the budget layer no-ops most of them, spending
6 credits (3 markets x 2 regions) per real poll to spread 500/month. This matches
the documented 9.1h median gap and is why `MAX_SILENCE_OTHERWISE` is 30h.

**A second dry-run finding was my own error, and is worth recording as such:**
I first reported 2,752 historical contracts with conflicting prices. That was
wrong — the duplicate key omitted `prop_stat`, so `passing_tds` and
`rushing_yards` at the same line value looked like one contract with two prices.
Real count: **1**. It is fixed anyway, via deterministic dedupe in
`read_as_of` (see methodology_backlog.md), because `idxmax` ties made reads
non-deterministic regardless of how few rows were involved.

**The real defect the dry run found, now fixed:** the props tick logged
`polled=0 skipped=272`, collapsing two completely different situations. Split
into `empty` (contacted, no props posted) vs `not_due` (never contacted). The
live service immediately reported `polled=0 empty=8 not_due=264` — **8 games are
probed every tick** and that was invisible. Before Week 1 this is the whole
signal: props silently ceasing to post, or the endpoint returning empties, would
have looked identical to healthy out-of-window operation. (`failed` already
separated API errors; these two did not.)

### 5. ~~Settle logged bets~~ DONE 2026-08-23

`settle_bets` in `src/store/bet_log.py`, called by `make season-review`. Reuses
`settlement.settle`, `prop_settlement.settle_prop` and `engine.payout_for`
unchanged -- `_payout` was made public rather than copied, because a second copy
of the payout convention would let live P&L and backtest P&L diverge silently.

Three properties worth knowing:

- **Kickoff order, not decision order.** `clv_portfolio.bankroll_path` reads
  `bankroll_after` positionally; sorting by decision time produced a non-monotone
  path once already (a bet can be decided 5 days out on a late game and 1 hour
  out on an early one). `settle_bets` returns in kickoff order.
- **Ungraded is not a loss.** An unplayed game, unmatched player name, or missing
  stat yields `outcome=None` and leaves the bankroll untouched. Grading it a loss
  would understate a $100 bankroll that has no top-ups.
- **Ties are pushes.** ~1 NFL tie a season; folding one into a loss is wrong.

`load_settlement_inputs` concatenates every cached schedule/player_stats vintage
and drops duplicates keeping the newest, which also makes the superseded
2015-2024 files harmless rather than a correctness risk.

**Verified end-to-end on real cached data**, not just fixtures: two real 2024
games (KC 27-20 BAL, PHI 34-29 GB), bets settled win/loss correctly, bankroll
$100 -> $102 -> $100, real CLV of +0.0209 computed from actual Pinnacle
snapshots, and `season_review` correctly returning INSUFFICIENT_DATA at n=2.

### 6. Retire the preseason modules after 9/9

`collect/preseason.py`, `clv/preseason_report.py`. Validation scaffolding, not a
result.

### 7. Cosmetic / housekeeping

- `notebooks/model_backtest_results.ipynb`: a registry label reads "(20)" for a
  comparison family that is now 22 (2 occurrences).
- Cell 95 has **stale outputs** showing the superseded 0.0575. Source and prose
  are corrected; outputs were deliberately not hand-edited (that would be
  fabricating a result). Needs a kernel re-run on `nfl-clv`.
- **Lint debt: 12 ruff errors**, 9 auto-fixable, in `collect/run.py`,
  `tests/test_pit_store.py`, `tests/test_props_budget.py`, `tests/test_schema.py`.
  (Was 17; four `src/` files were cleaned incidentally this session.)
- `ARCHITECTURE.md`'s status column conflates *role* (LIB, ENTRY) with
  *reachability* (LIVE, ORPHAN), so 8 rows disagree with `make audit` by
  construction. `make audit` now checks the ORPHAN claims automatically and
  reports drift; the deeper fix is to split the column or drop reachability
  from it and defer to the audit.

---

## Things that are settled — do not re-propose without new evidence

- **Garbage-time filtering** — tested, makes the model *worse*.
- **No historical CLV backtest is possible for any market.** Every historical
  pull is a single near-kickoff snapshot. CLV must be collected forward, live.
  This is why the polling density work mattered.
- **Prop closing probabilities are ~0.5 by construction** (46.8% within ±0.02).
  A formulation that tries to predict them is predicting noise.
- **QB Elo's "real improvement" does not survive multiple-comparison
  correction.** Only base Elo does. The comparison family is ~69 p-values and
  growing; every new comparison must go through Benjamini-Hochberg.
- **Feature engineering has failed 6 consecutive times** (garbage time, weather,
  rest/travel, game-level Elo rollups, GBM-once-Elo-is-present, referee
  tendencies). The pattern is the design rule below, not bad luck.

**The design rule that predicts outcomes here:** probability-estimation
strategies must overcome 6.29% prop vig and nothing built has supplied it —
they fail. Structural-exploitation strategies (arb, correlated legs, line
movement) require no probability estimate — they work. **State which shape a
proposal is before building it.**

---

## Working with this repo

- `graphify query "<question>"` first for codebase questions — the graph is
  current (1,986 nodes / 5,259 edges, rebuilt 2026-08-23 and includes
  `prop_book_coverage` and `pinnacle_arrival_message`).
- `graphify update .` after modifying code (AST-only, free).
- Run tests with the venv active: `source .venv/bin/activate && pytest -q`.
