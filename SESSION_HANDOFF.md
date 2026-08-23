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
| Test suite | **773 passed** | `pytest -q` |
| Lint | clean | `ruff check src/` |
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

### 1. Orphaned modules — decide wire-or-park (verified today)

These are built and tested but imported by **nothing except their own tests**:

| Module | Non-test importers |
|---|---|
| `src/backtest/parlay.py` | none |
| `src/model/individual_pass_rush_elo.py` | none |
| `src/collect/mainline_historical.py` | none (one-shot pull script — probably *park*, not wire) |

For contrast, these are properly wired: `clv_portfolio` and `evaluation` are both
imported by `src/backtest/season_review.py`.

`season_review.py` itself is currently imported only by its test — it is the
in-season entrypoint and is *meant* to be run by hand, but nothing schedules it.
Decide whether it becomes a weekly service.

### 2. Stale data files — safe to delete once nothing reads them

```
data/static/pbp_2015_2024.parquet
data/static/injuries_2015_2024.parquet
data/static/schedules_2015_2024.parquet
data/static/rosters_weekly_2015_2024.parquet
data/static/player_stats_2015_2024.parquet
```

Superseded by the 2025 refresh. Notebooks were repointed already — **grep before
deleting**, don't assume.

### 3. `market_write_freshness` should be promoted from diagnostic to alert

There is a TODO in `src/notify/health_check.py` saying exactly this. Now that
live props are posting, a stale `player_prop` write means the props collector
died, and the aggregate health check **structurally cannot see it** (the mainline
collector keeps the aggregate timestamp fresh). This is the same class of gap
that hid a 58-hour outage.

### 4. Full concurrent dry run before Week 1 (9/9)

All three services running simultaneously, watched for a full cycle. Never done.

### 5. Retire the preseason modules after 9/9

The hand-polled preseason track was validation scaffolding, not a result.

### 6. Cosmetic

A registry dict label in `notebooks/model_backtest_results.ipynb` reads "(20)"
for a comparison family that is now 22.

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
