# Beating the Close, Not the Book: A CLV-First Case Study of NFL Betting Markets

**Author:** Rahul Ramakrishnan
**Status:** Draft — pre-season skeleton
**Repo:** [link once pushed]

---

## Abstract

*[Write last. 150-250 words. State the thesis, the method, the headline CLV result with its confidence interval, and the honest conclusion — including if that conclusion is null. No P&L number in the abstract unless framed explicitly as noise.]*

---

## 1. Introduction

### 1.1 Motivation
*Why CLV and not P&L. State the efficient-market claim about the NFL close up front. One paragraph.*

### 1.2 Thesis
*[Pull from blueprint Part A: "In a near-efficient market, edge means beating the closing line, not making money."]*

### 1.3 Contributions
- [x] A leakage-free, point-in-time backtesting framework (`src/backtest/engine.py`)
- [x] A comparative implementation of four probability devigging methods, anchored to Pinnacle (`src/devig/`)
- [x] An empirical comparison of the four devig methods against 2,733 real game
      outcomes (§4.2) — a clean negative result, no method beats another at a
      statistically detectable level (paired bootstrap); Shin stays the default on
      its independent theoretical justification, not because it tested best
- [x] A CLV measurement framework with bootstrap confidence intervals (`src/clv/metrics.py`)
- [x] An EPA-based win-probability model with a calibration layer, validated for calibration
      quality (not CLV — see §3.1) against a market baseline on ten seasons of historical
      data (`src/model/train.py`, `src/model/calibration.py`)
- [x] An Elo opponent-adjustment benchmark (§4.5) — sequential, leakage-free by
      construction; beats the EPA-only model on its own and closes ~57% of the gap to
      the market baseline when combined with EPA (`src/model/elo.py`)
- [x] A garbage-time-filtering ablation (§4.5) — standard nflverse-community
      convention, verified against a real EPA distribution shift; a negative result
      (makes the model slightly worse, not better), reported as found rather than
      discarded (`src/model/features.py`)
- [x] A gradient-boosted-trees comparison (§4.5) — mixed result: beats logistic
      regression on EPA-only, loses once Elo is added; logistic + EPA + Elo remains
      the reference model (`src/model/train.py::fit_gbm_model`)
- [x] A QB-level Elo residual rating (§4.5) — isolates QB contribution from team
      strength; a real, modest improvement over EPA+Elo (Brier 0.2192 → 0.2170),
      sanity-checked against known-elite/known-weak QBs (`src/model/qb_elo.py`)
- [x] Automated live props polling (§3.6) — budget-aware, per-event scheduling
      on a separate paid key from the mainline collector, deliberately, so it
      can't starve the collector's own free-tier CLV polling; schedules a real
      entry-vs-close CLV pair per prop for the first time (`props_scheduler.py`)
- [x] Spread-cover and total-points regression (§4.5) — a genuinely new market
      target (continuous margin/total, not binary win/loss), reusing all existing
      infra; market beats both models as expected, and a robustness check found a
      real asymmetric result (total residuals non-normal, margin residuals aren't)
      (`build_margin_total_frame`, `fit_margin_model`, `fit_total_model`)
- [x] Game-level Elo aggregation (§4.5) — makes receiver/pass-rush Elo usable by any
      model for the first time; validated against a real 2023 injury case (Justin
      Jefferson's IR stint); wired into all three targets, clean negative result
      consistent across all three, same pattern as GBM
      (`src/model/game_level_features.py`)
- [x] Weather features (§4.5) — fifth consecutive negative result in the same
      direction (GBM, expanded receiver/pass-rush, weather all fail the same way
      on all 3 targets); caught a real pre-existing surface-column whitespace bug
      along the way (`src/model/features.py::add_weather_features`)
- [x] Correlated same-game outcome mispricing (§4.5) — a genuinely new
      methodology, not more capacity on old targets; every leg pair tested is
      significantly positively correlated (lift 1.07-1.48), robust across all 10
      individual seasons; the strongest, most robust finding in the session
      (`src/backtest/correlated_props.py`)
- [x] Correlated-edge pricing (§4.5) — turns the correlation finding into a
      quantified EV/Kelly-stake output using the project's own measured 6.29%
      prop vig, not a guess; 6 of 7 pairs clear the vig hurdle, and the two
      strongest survive a vig sensitivity sweep up to 10%
      (`correlated_edge`/`naive_parlay_price` in `src/backtest/correlated_props.py`)
- [x] Game-specific correlated-edge pricing (§4.5) — extracts value from the
      existing moneyline/spread architecture's real per-game market probabilities;
      found lift varies monotonically with favorite strength (not the constant
      the pooled model assumed), then found the resulting edge collapses to a
      bucket-level constant algebraically (`edge = lift/(1+vig)^2 - 1`) with a
      correct clip-driven falloff for extreme favorites — per-game granularity
      shows up in the Kelly stake, not the edge percentage
      (`measure_leg_correlation_by_bucket`/`estimate_game_specific_joint_prob` in
      `src/backtest/correlated_props.py`)
- [x] 7-pair bucket sweep (§4.5) — extended bucketing from 2 pairs to all 7; found it
      partially rescues the one pooled-failed pair (+0.30% edge in its underdog
      bucket) and, more importantly, exposes a real negative bucket hiding inside two
      pooled-positive pairs (heavy-favorite buckets going to -1.2% and ~0%) — 4 of 7
      pairs clear vig in all four buckets regardless of favorite strength, the
      genuinely robust subset (`bucket_edge` in `src/backtest/correlated_props.py`)
- [x] Middling (§4.10) — a genuinely different mechanism (real line movement over
      time, not a single-instant price comparison); built live-first since nflverse
      has no historical intraday line data; proved algebraically a real middle can
      never lose both legs, checked numerically; first live smoke test against the
      real 2026 collector found two real, small, bettable windows from cross-book
      disagreement (`src/backtest/middling.py`, `make middle-scan-once`)
- [x] Steam detection (§4.11) — a third distinct live mechanism (synchronized
      same-direction movement across multiple books, not one line drifting or one
      book vs. Pinnacle); reuses middling's pricing wholesale rather than
      reinventing it; first live smoke test found 5 real opportunities immediately
      (`src/backtest/steam.py`, `make steam-scan-once`)
- [x] Portfolio validation (§4.5) — leakage-safe splitting, walk-forward folds,
      permutation nulls, and Benjamini-Hochberg correction across all 57 real p-values
      this project has produced; found and fixed a real in-sample leak in the bucket
      pricing (favorite/heavy_favorite buckets don't survive honest out-of-sample
      testing; underdog/narrow do), confirmed the core correlation mechanism 3
      independent ways, multiple-comparison correction changes nothing else
      (`src/backtest/validation.py`)
- [x] Adversarial audit of the rest of the codebase (§3.10, §4.9, §6.4) — 4 parallel
      audits targeting arbitrage/EV-backtest timing, the Elo/model pipeline, devig
      methodology + sizing, and `PointInTimeStore`'s leakage guard itself. Found and
      fixed 2 real latent gaps (neither had ever produced a wrong result, both would
      have the moment live multi-poll data reached them): props arbitrage/EV backtest
      never checked simultaneity, and the live +EV monitor never checked its own
      `book_time`/`pinnacle_time` gap despite capturing both. `PointInTimeStore` and
      devig/sizing came back clean. Surfaced one real caveat: the same 2023-2024 test
      split has been evaluated 8 separate times across this project's history —
      documented honestly in §6.4
- [x] Quantified the test-set-reuse risk instead of leaving it a qualitative caveat
      (§3.7, §6.4) — challenged directly on "why does this need a fresh season if
      each feature was evaluated separately," which was a fair correction to make:
      the selection-bias component IS checkable with existing data. Paired-permutation
      + Benjamini-Hochberg across all 8 model comparisons found only base Elo survives
      (p=0.0014); QB Elo — this project's own reference model — does NOT (p=0.045
      uncorrected, fails corrected). Downgraded QB Elo's status from "a real, modest
      improvement" to "plausible, not confirmed" in §3.7 (`paired_permutation_test_mean_diff`
      in `src/backtest/validation.py`)
- [x] Rest/travel differential (§3.7, §6.4) — the first new feature tested after the
      test-set-reuse correction, evaluated as comparison #9 in the same corrected
      registry from the start. Rest re-encoding (differential + short-week/bye-week
      flags) tests a nonlinear effect on data already in the model since day one;
      travel distance/timezone-crossing is genuinely new (a hand-built 44-stadium
      coordinate/timezone table, `src/model/stadiums.py`). Result: negative, the 6th
      consecutive feature-engineering attempt in the same direction (ΔBrier=-0.0014,
      p=0.84) (`add_rest_travel_features` in `src/model/features.py`)
- [x] A receiver-level Elo (§3.7) — play-level rating for pass-catchers vs. a
      companion pass-defense Elo, built for player-prop pricing rather than game
      outcomes; sanity-checked, rates per-target efficiency not volume
      (`src/model/receiver_elo.py`)
- [x] A pass-rush Elo (§3.8) — team-level DL-vs-OL companion to receiver Elo (a
      fair player-level rating isn't buildable on free participation data);
      needed a measured base-rate offset receiver Elo didn't, sanity-checked
      against real 2024 reporting (`src/model/pass_rush_elo.py`)
- [x] Player status tracking (§3.9) — trade-aware current-team lookup + weekly
      injury status, resolved as-of-week from free nflverse roster/injury data;
      validated against a real 2024 trade, with an honest caveat found for
      fringe/practice-squad players (`src/features/player_status.py`)
- [x] Player-prop cross-book EV backtest (§3.10) — first real use of the historical
      props pull; a clean negative result, no statistically detectable edge at any
      EV threshold tested, and the apparent +3.07% at the default threshold doesn't
      survive a robustness check (`src/backtest/props_ev_backtest.py`)
- [x] Pure cross-book arbitrage (§3.10) — no Pinnacle/fair-value model needed; found
      31 real risk-free spots (0.35% of matched lines), traced to a genuine
      systematic FanDuel/BetMGM pricing-convention gap on receptions/passing-TD
      props, not noise — with honest execution-risk caveats attached
      (`find_arbitrage_spots` in `src/backtest/props_ev_backtest.py`)
- [x] A non-stationarity / drift monitor for edge decay — rolling CLV, CUSUM
      change-point detection, calibration drift (`src/drift/monitor.py`), built and
      tested against synthetic data ahead of a live CLV time series to run it on
- [x] A preseason dry run validating the full live pipeline against real odds ahead of
      the regular season (§3.5) — no bets, no Pinnacle, not part of the results below
- [x] A live +EV scanner and SMS alerting system (§4.9) comparing execution-book prices
      against Pinnacle's fair value in real time, running as a 24/7 macOS service
      (`src/signal/live_scan.py`, `src/notify/`) — a notification channel, not a
      bet-placement bot; confirmed live against real data (§4.9)
- [x] Player-prop infrastructure (§3.6) — schema, per-event polling, and settlement
      against real player stats, built and tested ahead of live prop data existing;
      confirmed live 2026-08-17 that props aren't posted this far before kickoff
- [ ] An honest, falsifiable case study across the 2026 NFL season (in progress — infrastructure complete, season data collection just started 2026-08-14)

### 1.4 What success means here
*[State the five falsifiable success criteria from blueprint Part A. Emphasize a null result is a valid, reportable outcome.]*

---

## 2. Background and Related Work

### 2.1 Market efficiency in sports betting
*Summarize why the closing line is treated as near-efficient. Cite the sharp-bettor / CLV literature (Pinnacle, Unabated resources).*

### 2.2 Closing Line Value as an edge proxy
*Why CLV, not ROI, is the accepted metric among professional bettors and books' own risk teams (used to identify and limit sharp accounts).*

### 2.3 Prior work
*Academic and practitioner references: Shin (1993/1992) on informed-trader devigging, Kelly (1956) on optimal sizing, plus any relevant public repos/blogs reviewed and how this project differs (most are "half-finished shells" — name the gap explicitly).*

---

## 3. Data

### 3.1 Sources
| Source | Coverage | Cost | Role |
|---|---|---|---|
| nflverse (nflreadpy) | Schedules, closing lines, scores since 1999 | Free | Settlement join, market baseline |
| The Odds API | Live intraday snapshots, 15+ books incl. Pinnacle | Free tier (500 credits/mo); paid upgrade planned ~2026-08-22 | Line movement, CLV |

(Spreadspoke/Kaggle was considered but nflverse's `load_schedules` already covers the
same ground — scores, opening/closing spread/total/moneyline lines back to 1999 — with
no separate ingestion path needed.)

**These two rows are not interchangeable, and the chronology matters.** nflverse's
schedule odds are a market-consensus close that nflverse aggregates — nowhere confirmed
to be Pinnacle specifically — and cover only a single closing number per game, with no
intraday history. The Odds API's `regions=eu` feed is confirmed live to return Pinnacle
explicitly (272/272 events matched in testing), and is the only source with the
entry-vs-close snapshot pairs CLV actually requires. Because nflverse has no intraday
snapshots, it **cannot produce a CLV number at all** — there is nothing to measure
movement against. Its 2015-2024 coverage is used in §4.5 to train and calibration-test
the win-probability model (Brier score, log loss, reliability vs. a market baseline),
which is a calibration-quality result, not a CLV result and not a claim about beating
Pinnacle. The CLV headline result (§5.3) is exclusively a live, 2026-season claim, built
from Odds API/Pinnacle snapshots collected from 2026-08-14 onward. A paid Odds API plan
(planned ~2026-08-22) would unlock a historical endpoint that could, in principle,
backfill genuine Pinnacle intraday history pre-2026 at 10x the credit cost per call —
not used in this paper as it stands.

### 3.2 Live snapshot collection
**Provider:** The Odds API, `regions=eu,us` — `eu` for Pinnacle (listed under EU
bookmakers, not `us`/`us2`), `us` for the three execution books (§3.4, §4.9). Through
2026-08-17 the collector ran `eu` only; `us` was added once comparing execution-book
prices against Pinnacle live became a load-bearing part of the project (§4.9), doubling
per-poll credit cost.

**Polling cadence is budget-adaptive, not fixed.** `decide_poll()`
(`src/collect/budget.py`) picks `max(game_interval, budget_interval, floor)`:
- `game_interval`: 30 min within 48h of a kickoff, else 60 min.
- `budget_interval`: remaining credits spread evenly across the remaining days in the
  billing period, so the free tier's 500 credits/month can't be exhausted in week one.
- a 15-minute floor regardless.

On the free tier, `budget_interval` dominates the max() in every scenario tested. At
`regions=eu` alone this worked out to ~4.5 hours (`(500-20)/3` polls at 3 credits/poll
spread across 30 days); adding `regions=us` on 2026-08-17 doubled the per-poll cost to 6
credits and pushed the same math to **~8.6 hours** (confirmed against the live account
state that day: 467 credits remaining, ~27 days left in the period). This resolves
itself automatically once the paid plan (§3.1, ~2026-08-22) raises the account's real
credit ceiling — `decide_poll` reads `remaining_credits` from the live API response
header, not a hardcoded constant, so no code change is needed. One poll still captures
the entire league's slate simultaneously (verified live: 272/272 scheduled games
matched, all four books — Pinnacle, DraftKings, FanDuel, BetMGM — present in one call),
so a long interval still means every game gets a synchronized fresh snapshot, not just
whichever is closest to kickoff.

**Deployment:** runs as a macOS launchd service (`ops/com.nflclv.collector.plist`,
`RunAtLoad` + `KeepAlive`), not a foreground process. This distinction mattered in
practice: the collector's first run (2026-08-14) was a one-off foreground invocation
that died with its terminal session, producing a 2.5-day collection gap (§3.3) before
the launchd service was installed on 2026-08-17.

**Provenance:** every `OddsSnapshot` row carries `book`, `capture_time` (the real
wall-clock moment the API response was received, never backfilled or estimated from
game time), and `event_id` matching nflverse's `game_id` convention.

### 3.3 Known data limitations
Intraday history only exists from the day collection started (2026-08-14); nothing
before that is recoverable by any means available to this project (§3.1's paid
historical endpoint, not yet purchased, is the only thing that could partially
backfill Pinnacle history, and even that starts from whenever it's purchased, not
retroactively).

**Collection gap, 2026-08-14 21:52 UTC → 2026-08-17 08:02 UTC (~2.5 days).** The
collector's first run (`make collect-once`, verified live: 272/272 events matched,
Pinnacle present) was a manual, one-off invocation in a foreground terminal session,
not a persistent process — it exited when that session ended, and nothing was
running again until it was installed as a macOS launchd service on 2026-08-17
(`ops/com.nflclv.collector.plist`, `make collector-service-install`; `RunAtLoad` +
`KeepAlive` so it now survives terminal closes, sleep, and reboots). Any line movement
during that window is permanently unmeasured for every game whose price moved in that
span — a real, if minor, hole in the pre-Week-1 CLV record, disclosed here rather than
smoothed over. Collection has run continuously since 2026-08-17 08:02 UTC (verified:
272/272 events matched again on restart, Pinnacle present, 467 Odds API credits
remaining).

### 3.4 Bet execution venues
Pinnacle is the project's fair-value anchor for CLV (see §4.2), but Pinnacle is not
legally available to US bettors — it withdrew from the US market in 2007 and does not
accept US players. This means the reference price (Pinnacle's devigged close, captured
by the live collector) and the execution venue (wherever a bet is actually placed) are
necessarily two different systems. That separation is not a limitation of the CLV
methodology: CLV is defined as *recorded entry price* vs. *Pinnacle's fair close at
settlement*, which holds regardless of which book, or how many books, the entry price
came from.

Bets for this study are placed through Virginia-licensed mobile sportsbooks (Virginia
operates a mobile-only market; no retail sportsbooks). Three accounts were opened —
DraftKings, FanDuel, and BetMGM — chosen as a deliberate tradeoff rather than either
extreme:

- **Not a single book.** Line shopping across books is free CLV before a model is even
  involved — if two books disagree on a price, taking the better one improves the entry
  side of the CLV calculation independent of any edge-finding.
- **Not broad coverage across every licensed operator.** The project's bankroll is $100
  total with a 2% ($2) max-bet cap (§4.6). Splitting that bankroll across many accounts
  fragments bookkeeping — tracking a combined virtual bankroll that doesn't match any
  single account's real balance — for a project whose central claim rests on
  disciplined, auditable honesty. DraftKings and FanDuel are the two largest books by
  market share and tend to diverge from each other more than smaller books diverge from
  either of them, so two books already capture most of the available shopping value;
  each additional book adds administrative surface (KYC, deposits, promo tracking,
  settlement reconciliation) faster than it adds CLV.
- **Book selection was not driven by limit-avoidance.** Sportsbooks slow-limit accounts
  that show consistent positive CLV, but at a $2 max bet no book will ever flag this
  account for size. Accordingly, the three books were chosen for market depth and
  product reliability, not for how slowly they limit sharp bettors — that concern only
  binds at real stakes, which this study explicitly is not attempting (§4.6).

**Updated 2026-08-18: expanded to five accounts (+ BetRivers, + Caesars/William Hill
US), reopening the tradeoff above on new evidence rather than by default.** The
original "two books already capture most of the shopping value" argument was a
reasonable prior with no data behind it. §3.10's arbitrage finding is now real
evidence against it specifically for player props: a genuine, week-by-week-consistent
cross-book pricing disagreement between FanDuel and BetMGM (present in 14-15 of 15
weeks checked) that neither DraftKings alone nor the DK/FD/BetMGM trio could have
surfaced without a third-plus book in the comparison. Both regulated in Virginia, same
legal footing as the original three. The bankroll-fragmentation concern from the
original reasoning (a $100 total bankroll, $2 max bet, split across more accounts)
still applies exactly as stated and was not resolved by this update, just accepted as
the cost of the wider comparison.

**Promotional bet handling.** Welcome bonuses and odds boosts pay out as bonus credit or
alter the price actually being risked, which distorts the realized entry price relative
to a genuine risk-priced wager. Bets placed with bonus credit or under an odds boost are
tagged separately in the bet log and excluded from the headline CLV figures reported in
§5, consistent with the project's "honest math" framing (blueprint Part A).

### 3.5 Preseason dry run (infrastructure validation, not a result)
Before the regular season and the real collector's shared credit budget were on the
line, the live pipeline (poll → match → store → measure) was exercised end-to-end
against real 2026 preseason odds — `src/collect/preseason.py` polling The Odds API's
`americanfootball_nfl_preseason` sport key, `src/clv/preseason_report.py` computing
entry-vs-latest price and probability CLV movement. **No bets were placed and this data
is not part of any result in §5** — it is purely a smoke test that the mechanics work
before they matter.

Two properties make this data structurally distinct from everything else in this paper:

- **No Pinnacle.** Confirmed live, across every region tested (`eu`, `us`, `us2`):
  Pinnacle does not trade NFL preseason at all. Only FanDuel, MyBookie, and 1xBet post
  preseason lines. FanDuel served as the dry run's reference book — explicitly *not* a
  Pinnacle substitute, and Pinnacle's own absence here is informative on its own terms:
  a market a sharp book won't price is a market too thin and low-information to read
  value into — a temptation directly considered and rejected during this build: a lone
  book quoting a number nobody else quotes isn't evidence of mispricing, just a market
  with no reference price to check it against.
- **No nflverse identity.** nflverse's schedule tables carry no preseason rows
  (`game_type` is only REG/WC/DIV/CON/SB), so preseason events have no `game_id` to
  join against. They were identified instead by The Odds API's own stable per-event
  `id`, namespaced with a `PRE` prefix (`2026_PRE_<odds-api-id>`) specifically so they
  can never be mistaken for a real nflverse `game_id` downstream, and written to a
  separate store (`data/snapshots_preseason/`, never `data/snapshots/`).

First live run (2026-08-17): 16/16 `americanfootball_nfl_preseason` events matched
cleanly (0 unmatched, 0 malformed) via the Odds-API-id path, confirming the matcher,
transform, and store layers all work correctly against real data outside the schema
nflverse was built to describe. An interactive notebook
(`notebooks/preseason_dry_run.ipynb`) exists for re-running this inspection as more
polls accrue through the remainder of the preseason window.

### 3.6 Player props (infrastructure prepped, not active)
Mainline spreads/totals/moneylines are the most efficiently priced markets in sports
betting -- Pinnacle and sharp money price them tightly. Player props get priced faster
and with less scrutiny, and are the more commonly cited source of real mispricing, so
extending toward them is a natural direction for this project. The infrastructure
(schema, per-event polling, settlement) is built and tested ahead of any live prop data
existing, deliberately, the same "prep now, activate later" pattern as §3.5.

**Live-checked 2026-08-17 (3.5 weeks before the Week 1 opener), across every region
(`us`, `us2`, `eu`, `uk`):** only DraftKings had posted anything for a Week 1 game, and
only one market, `player_anytime_td` -- no passing/rushing/receiving yardage or
reception props, no Pinnacle, no FanDuel, no BetMGM. This matches how NFL player props
are actually released in the industry -- typically Tuesday-Thursday of game week, not
weeks ahead like mainline markets -- so it is not a configuration gap the way the
preseason and execution-book coverage gaps (§3.5, §4.9) were; there is simply nothing
to poll yet. This leaves one question genuinely open: **whether Pinnacle trades NFL
player props at all.** If it doesn't, the devig-Pinnacle-then-compare methodology this
whole project is built around has no anchor for props, the same dead end preseason hit
for team markets. Unknowable until props actually exist to check -- flagged for
re-verification once they do (around 2026-09-02 for the Week 1 opener).

**Structural differences from the mainline collector (§3.2), built now:**
- Player props require the per-event endpoint (`OddsApiClient.get_event_odds`,
  `/v4/sports/{sport}/events/{eventId}/odds`) -- one call per game, not one call for the
  whole slate, at a materially different cost profile (unique markets returned x
  regions per call).
- Scoped to Over/Under markets only (`src/collect/props.py::PROP_MARKET_TO_STAT`:
  passing/rushing/receiving yards and TDs, receptions) -- proposition-style markets
  like `player_anytime_td` were observed live as single-sided (no complementary "No"
  price), so they cannot be devigged with the existing two-outcome methods (§4.2) at
  all, not merely unmapped yet.
- The regular season already has real nflverse `game_id`s, unlike preseason, so props
  reuse the mainline collector's own team matching (`match_event`) and write into the
  same `data/snapshots/` store under `market=player_prop`, not a separate one.
- Settlement (`src/store/prop_settlement.py`) grades an Over/Under prop against
  `nflreadpy.load_player_stats()`, joined on `(game_id, player_display_name)`.
  Unmatched players or missing stat values are left ungraded (`None`), never silently
  dropped -- the same discipline `settle_snapshots` (§4.4-adjacent) already applies to
  unplayed games.
- Manual invocation only (`make props-poll`, defaulting to the coming week), not a
  scheduled service -- per-event calls scale with game count and there is nothing to
  poll most of the season.

**Historical props for backtesting -- checked, blocked on paid access.** Unlike
mainline markets, there is no free historical source for player-prop odds at all
(nflverse has real player stats, not book prices). The Odds API's paid historical
endpoint does cover props, from 2023-05-03T05:30:00Z onward at 5-minute snapshot
intervals -- confirmed live 2026-08-17 that this project is still on the free tier
(`HISTORICAL_UNAVAILABLE_ON_FREE_USAGE_PLAN`, 0 credits charged for the rejected
check). Cost is 10x the live per-event rate (10 x markets x regions per snapshot
call, one point-in-time read, not a range), so a full season of closing-line-only
pulls for even a single market runs several thousand credits.

`src/collect/props_historical.py` and two new `OddsApiClient` methods
(`get_historical_events`, `get_historical_event_odds`) are built against the
endpoint's documented response shape -- unverified against a real response, unlike
every other module in this project, since there is no way to call it without paid
access. The plan once paid access lands: pull one prop market for one recent season
(e.g. `player_pass_yds`, 2024) as a cheap proof of concept before committing further,
and specifically check whether Pinnacle appears at all, which resolves §3.6's open
question without waiting for the 2026 season's own props to materialize.

**Automated live polling, built 2026-08-18 ahead of props actually posting.**
`src/collect/props.py`'s manual `poll_all_props` was the only way to catch live
props; nothing ran it on a schedule. `src/collect/props_scheduler.py` (with pure
decision logic in `props_budget.py`) fixes that with a materially different
scheduling problem than the mainline collector's: the mainline collector polls the
whole slate on a shared cadence (one bulk call), but each game's props post
independently, typically Tue-Thu of that game's own week -- so this decides
per-event whether to poll *right now*. Schedules two real polls per event: an
"entry" poll once the event is within a 5-day posting window, and a "close" poll
once inside 6 hours of kickoff -- a genuine entry-vs-close CLV pair for props, for
the first time. (The historical pull above was forced to a single near-kickoff
snapshot per game by the historical endpoint's 10x cost multiplier; live polling
doesn't carry that multiplier, so two real time points per event is affordable.)

**Deliberately uses `ODDS_API_KEY_PAID`, not the mainline collector's
`ODDS_API_KEY`.** The mainline collector's dense pre-kickoff polling is the
project's actual CLV thesis and runs on the free tier's 500 credits/month. Props
polling at real per-event cost (~10-14 credits/event, historically observed via the
10x historical rate), twice per event across ~16 games/week, would exhaust that
same free-tier budget within days and starve the mainline collector precisely when
it matters most -- game week. The paid key's much larger monthly allowance (§3.6)
absorbs this without touching the free tier at all. Event discovery
(`OddsApiClient.get_events`) is free (0 credits, confirmed against The Odds API's
own docs) so the eligible-event list stays current at no cost regardless of
polling decisions; only gated `get_event_odds` calls spend real credits.

Tested (19 tests across `test_props_budget.py`/`test_props_scheduler.py`,
including an injectable-clock refactor so time-relative polling decisions are
deterministically testable) and smoke-tested against the real API 2026-08-18:
272 real events listed for free, correctly 0 polled -- none are within the
posting window yet, three weeks before the Week 1 opener. Not yet exercised
against a real posted prop, and not yet installed as a running service
(`make props-service-install` mirrors the mainline collector's deployment,
available but not enabled) -- there's genuinely nothing to poll until props
start posting.

### 3.7 Receiver-level Elo (player-prop pricing infrastructure)
A different kind of Elo than §4.5's team/QB ratings, built for the same reason props
(§3.6) were prepped ahead of live data: sports betting books price mainline markets
(spread/total/moneyline) tightly, but player props get priced faster and with less
scrutiny -- the more commonly cited source of real mispricing. Team/QB Elo can't speak
to that; a receiver-level rating can.

**What's not available for free, stated plainly:** true man-to-man coverage matchup
data -- which specific cornerback was assigned to a given receiver on a given snap --
isn't in free nflverse play-by-play. That's PFF/NGS charting, paywalled. `defteam` is
the finest opponent-side grain available for free, so this rates receivers against a
team-level **pass defense** Elo, not a corner-specific one. Still a real, laggable
signal: "this receiver is hot, this week's opponent pass defense is Elo-weak" is
information a book can be slow to fully price into a prop line.

**Design (`src/model/receiver_elo.py`):** unlike team/QB Elo, a receiver has no
per-game win/loss -- what exists is a sequence of individual targets. So every target
is its own two-sided Elo match: the targeted receiver vs. the opposing pass defense,
using the play's `success` flag (standard EPA-success definition, already cached) as
the binary outcome. This is a legitimate, well-established Elo generalization (any
repeated pairwise binary contest), not a residual-vs-baseline hack the way QB Elo is.
K=4, smaller than team Elo's K=20, since a receiver sees many targets per game rather
than one game-level contest. Leakage-free the same way: plays processed in strict
chronological order (season, week, game, then nflverse's within-game `play_id`).

**Result, sanity-checked against known players (2015-2024, min 100 targets):**
top-rated are George Kittle, Amon-Ra St. Brown, Mark Andrews, Tee Higgins, Travis
Kelce -- elite pass-catching tight ends and possession receivers whose targets are
disproportionately short, high-percentage completions. **Read this caveat as a finding,
not a flaw:** the bottom of the list is dominated by receiving-role running backs
(Ezekiel Elliott, Tony Pollard, Jonathan Taylor) whose targets are often low-value
checkdowns logged as failed plays even when caught, since `success` is opponent-Elo-
relative, not an absolute yardage threshold. This rates *per-target efficiency*, not
volume or big-play ability, and should be read alongside a volume stat (targets/game,
target share) rather than used alone as a "best receiver" ranking. Full results and the
companion pass-defense Elo leaderboard: `notebooks/model_backtest_results.ipynb`.

**Not yet wired into anything.** Standalone rating infrastructure -- not fed into the
game-outcome model (§4.5, since this project isn't betting game outcomes with it), and
not fed into prop pricing yet either (props are prepped but not live, §3.6).

### 3.8 Pass-rush Elo (the DL-vs-OL companion, at team level)
The natural next piece after §3.7, for sack props / QB-under-pressure props, sharing
the same play-level Elo mechanic.

**Team-level, not player-level -- and this is a deliberate, data-forced choice, not a
scope cut.** Free nflverse pbp records *who got credit* for a sack or QB hit, but not
who was rushing (and being blocked) on the plays where nobody did -- there's no full
pass-rush participation list. A player-level Elo built only from credited plays would
only ever see wins, never losses: not a fair two-sided Elo contest, just production
volume wearing an Elo costume, and it would fail this project's own sanity-check
discipline (§4.5, §3.7). So `src/model/pass_rush_elo.py` rates the two units fully
observed on every dropback: `posteam`'s pass protection and `defteam`'s pass rush.

**Design:** every dropback (`pass == 1`, sacks included) is a two-sided Elo match; the
outcome is whether the rush won the play (`sack == 1` or `qb_hit == 1`). K=4, same
order as receiver Elo's target-level K.

**A base-rate correction §3.7 didn't need.** A target's `success` rate is close to
50/50 (~49.5%), close enough that two ratings starting at 1500 need no correction.
Pressure events are not -- ~13.6% base rate, measured on the 2015-2024 cache. Without a
correction, every play surprises the rush side downward on average, so both ratings
drift monotonically away from 1500 forever with no informative center -- caught before
trusting the first run, whose mean rush Elo had drifted to ~1402 instead of ~1500.
Fixed with `DEFAULT_BASE_PRESSURE_OFFSET` (-320.6, derived as `-400 * log10(1/p - 1)`
from the measured base rate `p`), handed to the same Elo win-probability transform the
same way `elo.py`'s `home_field_advantage` corrects the ~50-55% home-win base rate.
After the fix, mean rush Elo and mean protection Elo both land within 5 points of 1500.

**Result, sanity-checked (2015-2024, end-of-dataset ratings):** Cleveland, Kansas City,
Denver, Seattle, and Dallas top the pass-rush leaderboard; New Orleans, Atlanta,
Arizona, New England, and Jacksonville sit at the bottom -- plausible given real
2015-2024 form (Myles Garrett's Browns, Micah Parsons' Cowboys). Tampa Bay, Arizona,
and Buffalo top pass protection; Pittsburgh, Tennessee, Minnesota, Houston, and Kansas
City sit at the bottom -- the Chiefs' offensive-line struggles were widely reported in
2024, a real-world check this rating happens to confirm independently.

**A separate, explicitly-not-Elo companion:** `credited_pressure_counts()` is a raw
per-player count of sacks (full credit) and half-sacks (0.5 credit each) plus QB hits
-- a named-player leaderboard for context, deliberately not blended into the Elo
rating above, for the participation-data reason stated up top. Top by career sacks in
the cache: T.J. Watt, Aaron Donald, Khalil Mack, Danielle Hunter, Myles Garrett --
exactly who this list should surface, a useful check that the credit-parsing logic
(full sack / half-sack / QB hit columns) is correct. Full results:
`notebooks/model_backtest_results.ipynb`.

**Correction (2026-08-21): individual pass-rush rating IS buildable after all.** The
"no free participation data" claim above was true using only nflverse's own trimmed
play-by-play, but not true of nflverse's broader table menu -- found only after the
user directly asked whether the cached data reflected everything free and available.
`load_pfr_advstats(stat_type="def")` (Pro Football Reference, via `nflreadpy`) gives
real per-player-per-game pressure/hurry/hit/blitz counts; `load_snap_counts` gives the
missing piece, a genuine denominator (`defense_snaps`). Joined on PFR's own player/game
IDs at a **verified 100% match rate**, this supplies exactly what raw pbp credit
couldn't: a player who rushed 40 times and got 0 pressures now looks different from one
who rushed 5 times and got 0.

`src/model/individual_pass_rush_elo.py` implements this -- restricted to real pass-rush
positions (DE/DT/NT/EDGE/OLB, where snaps are a reasonable proxy for pass-rush
opportunity, unlike LBs who split time with coverage), a per-snap Elo update in closed
form (equivalent to running the same per-play update `defense_snaps` times within one
game, holding the pre-game expectation fixed for the whole game -- a real
simplification, not literal play-by-play sequential updating). Base rate measured
fresh from the 2018-2025 cache (PFR's own coverage floor, narrower than pbp's 2015+):
**3.84%** pressures per defensive snap (lower than the team-level 13.6% per-dropback
rate, expected since this is per-snap for one individual, including run-support snaps).

**Sanity-checked the same way as every other rating in this project:** mean final
rating lands at 1501.1 (offset correctly calibrated, same "check the mean before
trusting" discipline pass-rush Elo's own build caught a bug with). Real leaderboard
(min 20 games): Trey Hendrickson, Aidan Hutchinson, Myles Garrett, Nick Bosa, Chris
Jones at the top -- exactly the players real 2018-2025 football knowledge would put
there. Bottom: Daron Payne, Johnathan Hankins, Derrick Nnadi, Grover Stewart -- run-
stuffing nose tackles/DTs, not known as pass-rush specialists, an independent
real-world check the rating gets right in both directions.

This doesn't replace the team-level rating above -- full 2015+ coverage and a
genuinely different (team-vs-team) question -- it's a narrower-coverage (2018+),
individual-level companion, real where it was previously assumed impossible.

### 3.9 Player status tracking (current team + injury status)
Every Elo rating above (§3.7, §3.8, §4.5's QB Elo) is already trade-safe by
construction -- each is keyed by `gsis_id`, so a player's rating carries with them
regardless of which team they're on in a given game row. What was missing was the
lookup layer: given a player, which team are they on *right now*, and are they hurt?
`src/features/player_status.py` answers this from two free nflverse tables
(`load_weekly_rosters`, `load_injuries` in `src/features/load_static.py`): a weekly
roster snapshot (one row per player per team per week, so a trade shows up as a new
row the week it happens) and a weekly injury report (`report_status`:
Out/Doubtful/Questionable/no report). `player_status_snapshot(season, as_of_week)`
resolves both to "most recent state at or before this week" -- a bye week or a week
with no new injury report still resolves to the last known state, not a gap.

**Validated against a real 2024 trade:** Amari Cooper (CLE → BUF, actual trade week
7) resolves cleanly -- `current_team` reads CLE through week 6, BUF from week 7
onward, with injury status (`Questionable`, week 12) updating independently and
correctly on top of it.

**An honest caveat, found while validating, not swept under the rug:** the
resolution logic is correct, but the underlying nflverse data is murkier for
fringe/practice-squad players. Checked against Greg Joseph (a kicker who bounced
CUT → practice squad → traded → unrostered → signed elsewhere across 2024): his
`TRD` (traded) status row keeps his *outgoing* team label, not the incoming one, and
there's a real four-week gap in his roster history where the resolver correctly
returns "most recent known state" but that state is stale (still shows the old team,
past the actual trade). This is a data-quality property of nflverse's roster feed for
players who move through waivers/practice squads, not a bug in the resolution logic --
worth knowing before trusting `current_team` for a fringe-roster player specifically,
less of a concern for a clearly active starter like the Cooper case above.

### 3.10 Player-prop cross-book strategies (historical, not the live CLV headline)
The first real use of the historical props pull (§3.6), two strategies that don't
need market timing to test: a Pinnacle-anchored EV backtest, and pure cross-book
arbitrage. Does comparing an execution
book's price against Pinnacle's devigged fair value, at a matching prop line, find
bets that actually win at the rate the implied edge predicts?

**Scope, stated plainly: this is not a CLV backtest, and not §5's live 2026 headline
result.** The historical pull captures one snapshot per game near kickoff -- there's
no earlier "entry" price to compare against a "close" the way the CLV thesis works
for mainline markets. What this tests instead: a same-moment cross-book mispricing
signal, using batch 1 of the pull (178 games, 2024 weeks 8-22, 118K snapshots, 8
books including Pinnacle).

**Method (`src/backtest/props_ev_backtest.py`):** devig Pinnacle's Over/Under pair at
each (event, player, stat, line) where both sides are quoted at the *same* number
(4,994 of 4,998 groups -- the 4 mismatched-line groups are dropped, can't devig a
market that isn't quoting one number). Compare each execution book's (DraftKings,
FanDuel, BetMGM) price at the *exact same line* against that fair probability
(`expected_value`, reused unchanged from `src/signal/live_scan.py`'s live scanner --
same methodology, applied retrospectively). 8,992 exact-line-matched pairs exist in
the batch-1 data.

**At the default 2% EV threshold: 344 spots flagged, 333 gradable against real 2024
outcomes (11 ungraded -- genuine player-name/stat-availability gaps, same known issue
as §3.6).** Win rate: 166/333 = **49.85%** -- a coin flip. Realized return: **+3.07%
per dollar staked**, strikingly close to the +3.74% average edge the Pinnacle-fair
methodology predicted going in. A 95% bootstrap CI (10,000 resamples, same
`bootstrap_ci` used for CLV) on realized return: **(-8.3%, +14.3%) -- includes zero,
not statistically distinguishable from breakeven** at this sample size.

**Threshold sensitivity -- the honest tell that this isn't (yet) a confirmed edge.**
A real edge should hold up or strengthen as the EV threshold tightens (a more
selective bet should be more profitable, not less). It doesn't, here:

| Threshold | n | Win rate | Avg. return | 95% CI |
|---|---|---|---|---|
| 0.00 | 824 | 50.7% | +1.6% | (-5.3%, +8.5%) |
| 0.02 | 333 | 49.9% | +3.1% | (-8.3%, +14.3%) |
| 0.04 | 111 | 44.1% | -6.3% | (-26.6%, +13.7%) |
| 0.06 | 27 | 44.4% | +6.7% | (-37.9%, +53.2%) |
| 0.08 | 8 | 50.0% | +25.3% | (-67.3%, +113.1%) |

Non-monotonic, and every CI is wide enough to include zero. **Honest conclusion: no
robust, statistically detectable edge found in this cross-book comparison at any
threshold tested** -- not "no edge exists" (333-824 bets is a genuinely small sample
for a few-percent-per-bet signal, the same power-analysis caveat §5.5 is reserved for
the live season), and not "confirmed edge" either. The apparent +3.07% at the default
threshold does not survive a basic robustness check, so it should not be read as a
validated result. Full backtest and threshold sweep:
`notebooks/model_backtest_results.ipynb`.

**Pure cross-book arbitrage -- a different, and real, kind of finding.** The EV
backtest above assumes Pinnacle's price is truth. Arbitrage needs no such
assumption: does the best available Over price at one execution book, plus the best
available Under price at another, sum to under 100% implied probability? If so, both
legs are placeable and the outcome doesn't matter -- a risk-free lock, not a
predictive edge (`find_arbitrage_spots`, restricted to DraftKings/FanDuel/BetMGM only
-- Pinnacle and offshore books like Bovada aren't places this project's bettor can
actually place a bet, so they don't count as a real arb leg).

**Result: 31 genuine arbitrage opportunities found, out of 8,992 exact-line-matched
pairs (0.35%).** Mean margin 0.79%, max 1.61% -- small, but mathematically guaranteed
if both legs were simultaneously placeable. **Not random noise: 29 of 31 are the same
book pair (FanDuel Over, BetMGM Under) on the same two prop types (receptions,
passing TDs).** Checking why: FanDuel prices these two markets with a real,
systematic vig skew relative to BetMGM -- FanDuel's average Over price is
dramatically shorter (e.g. passing TDs: -0.05 average vs. BetMGM's -31.35) while its
Under price is dramatically steeper (-86.76 vs. -52.90). This is a structural pricing
difference between two specific books on two specific market types, not a fleeting
mispricing -- a mechanistically different (and more interesting) finding than "prices
sometimes disagree."

**Three honest caveats before this reads as a real strategy, not overselling it:**
(1) each snapshot is captured near kickoff at a single point in time (5-minute
snapshot granularity on the historical endpoint) -- reasonable confidence the two
prices existed close together, but not proof both legs were simultaneously bettable
in real time the way live monitoring would confirm; (2) margins under 2% would likely
be eaten by execution latency/slippage in practice, placing two bets at two different
books isn't instantaneous; (3) sportsbooks are well known to limit or ban accounts
that repeatedly hit guaranteed-profit spots -- a real-world risk pure EV math doesn't
capture, and worth stating plainly rather than pretending the theoretical margin is
the realized one. **This is one season, one book pair, two market types -- needs
out-of-sample confirmation on live 2026 data before treating it as a durable pattern
rather than a 2024-specific artifact.** Full results:
`notebooks/model_backtest_results.ipynb`.

**Within-season robustness check: the skew holds up week by week, not just in
aggregate.** Live 2026 props aren't posted yet (checked 2026-08-18, 0 books returned
data for the Week 1 opener, 2026-09-10 -- still three weeks out), so a true
out-of-sample test isn't available yet. The strongest check available now: does the
FanDuel/BetMGM skew persist across individual weeks within batch 1, or was it driven
by a couple of unusual games? Arbitrage spots appeared in 14 of the 15 weeks in
batch 1. The underlying price skew is even more consistent: across all 15 weeks,
**FanDuel's Over price on passing TDs was shorter than BetMGM's in 15/15 weeks
(100%), and FanDuel's Under was steeper in 15/15 weeks (100%); for receptions, 12/15
(80%) and 15/15 (100%) respectively.** A pattern present in essentially every week of
the season is much harder to explain as a coincidence than 31 isolated spots would
be -- still not proof it persists into 2026, but real evidence within 2024 that this
is structural, not scattered.

**Updated 2026-08-18: re-run on five execution books.** Following the account
expansion above (DraftKings/FanDuel/BetMGM -> +BetRivers, +Caesars), both
strategies were re-run on the same batch-1 data, no new pull needed. **Arbitrage
roughly doubled: 65 spots (was 31), 0.70% of 9,346 matched pairs (was 0.35% of
8,992).** Persistence held (14/15 weeks either way) and the market-type
concentration held (57 of 65, 88%, still receptions/passing TDs) -- wider book
coverage strengthened the finding rather than diluting it, with FanDuel/BetMGM
still the largest single pair (26 of 65) and BetRivers now appearing heavily too
(13 with BetMGM, 6 with FanDuel). **The EV backtest, re-run on the same five books,
moved further into null territory, not away from it:** win rate dropped to 47.1%
(n=552, was 49.85% at n=333), average return went negative (-1.64%, was +3.07%),
95% CI (-10.4%, +7.2%) still includes zero. More data made the arbitrage finding
more credible and the null EV result more confident -- a consistent, honest
picture, not two results pulling in different directions.

**A latent gap found and fixed (2026-08-21 adversarial audit), not currently live.**
Neither `find_arbitrage_spots` nor `find_prop_ev_spots`/`pinnacle_fair_probs` checked
`capture_time` at all before this fix -- both were safe only by accident, because the
historical batch-1 pull happens to carry exactly one snapshot per game (verified
empirically: 0 of 178 games have more than one distinct `capture_time`). The gap was
never live for the 65-spot/null-EV results reported above -- confirmed by re-running
both functions against the real data after the fix: identical 65 arb spots, same EV
result. But it would have activated silently the moment this code was pointed at the
live props scheduler's data (§3.6, already built, polls twice per event -- entry and
close, deliberately days apart): `find_arbitrage_spots` would have paired an entry-time
Over against a close-time Under and reported a "risk-free" arb that was never actually
simultaneously bettable, and `find_prop_ev_spots` could have compared a stale Pinnacle
read against a fresh execution-book price. Both functions now require simultaneity --
arbitrage requires an exact shared `capture_time` between legs (matching this project's
existing "a single poll writes both sides together" convention from §4.9's live
scanner), and the EV comparison requires Pinnacle's price within 30 minutes of the
execution book's. Caught before it could ever produce a wrong live result, not after.

**A second, related gap caught by a follow-up code review (2026-08-21).** The
simultaneity fix above still had a bug: `pinnacle_fair_probs` picked Pinnacle's
single latest capture_time per group, but if THAT specific poll only updated one
side (e.g. Pinnacle re-priced the Over but the Under didn't move that cycle), the
group would fail the Over/Under completeness check and get dropped entirely --
discarding a perfectly valid, fully simultaneous EARLIER pair in the process. Fixed
to find the latest capture_time where BOTH sides are actually present, not just the
latest timestamp overall. Same as the first fix, empirically confirmed to be a no-op
on the real batch-1 data (65 arb spots, same EV result) -- this dataset has exactly
one capture per game, so the bug was never live; it protects the live props
scheduler's multi-poll data the same way the first fix does.

---

## 4. Methodology

### 4.1 Odds conversion
Implemented in `src/devig/convert.py`, the single source of truth other modules import
from rather than re-deriving:
- `american_to_decimal(odds)`: favorite (`odds<0`) → `1 + 100/(-odds)`; underdog → `1 + odds/100`.
- `decimal_to_implied_prob(d)`: `q = 1/d`.
- `american_to_implied_prob(odds)`: favorite → `(-odds)/((-odds)+100)`; underdog → `100/(odds+100)`.

### 4.2 Devigging methods
All four methods from blueprint B.2 are implemented in `src/devig/methods.py`, each
returning fair probabilities plus a diagnostics dict (e.g. Shin's solved `z`, whether
additive clipped a negative probability): multiplicative (proportional split), additive
(equal-share shift, clips negative probabilities and flags it), power (solves `k` via
`scipy.optimize.brentq` so `sum(q_i^(1/k))=1`), and Shin (solves for informed-money
share `z`). `compare_methods_table()` runs all four on one market and returns a
DataFrame — the Part B.2 deliverable table; populating it with a real market is pending
enough live data to pick a representative example.

**Reference method: Shin**, used as the default anchor throughout (`src/model/baseline.py`,
`src/backtest/engine.py`) — it models informed money rather than just normalizing away
the vig, which the blueprint argues gives the best fair probabilities near an efficient
close. That justification was theoretical, not tested against this project's own data,
until now.

**Empirical comparison, checked 2026-08-18: no method beats the others at a
statistically detectable level.** Using nflverse's closing moneylines (2,733 games,
2015-2024, ties excluded), each method's devigged home-win probability was scored
against the realized outcome (Brier score, log loss) both over the full sample and the
2023-2024 test window used everywhere else in this project. Raw numbers rank
power/additive marginally ahead of multiplicative/Shin (full sample: 0.21229 vs.
0.21236, a 0.00007 Brier gap; test window: 0.20947 vs. 0.20986, a 0.00039 gap) — but a
paired bootstrap (10,000 resamples, per-game squared-error difference, same
`bootstrap_ci` used for CLV in §4.3) on Shin vs. each alternative gives 95% confidence
intervals that all include zero (e.g. Shin vs. power: mean diff 0.000066, CI
[-0.000212, 0.000335]). **The honest conclusion: devig method choice does not
measurably affect calibration quality on this dataset — a clean negative result, in the
same spirit as §4.5's garbage-time-filtering finding.** Shin stays the default: nothing
here contradicts its independent theoretical justification (modeling informed money,
relevant specifically for CLV anchoring — a different criterion than raw outcome
calibration), and there is no calibration evidence to prefer switching. A genuine, minor
data-quality note surfaced along the way: mean vig across the sample is a thin ~2.97%
(consistent with sharp closing lines), and exactly one game (of 2,733) has slightly
negative overround — a data artifact, not a systemic issue; additive's negative-probability
clip never triggered across the full sample. Full comparison:
`notebooks/model_backtest_results.ipynb`.

### 4.3 Closing Line Value
Implemented in `src/clv/metrics.py`:
- **Probability CLV**: `clv_probability(p_entry_fair, p_close_fair) = p_close_fair - p_entry_fair`.
  Both probabilities are Pinnacle-anchored (devigged from Pinnacle's own market, at
  entry time and at close) — this makes probability CLV a pure market-movement signal,
  independent of which book the bet was actually placed at.
- **Price CLV**: `clv_price(d_entry, d_close) = (d_entry/d_close) - 1`, comparing the
  price actually taken (whatever book) against Pinnacle's closing price for the same
  side.
- **Beat rate**: `beat_rate()`, fraction of bets with positive CLV.
- **Bootstrap CI**: `bootstrap_ci()`, a vectorized percentile bootstrap (seedable) on
  mean CLV — never reported as a bare point estimate.

### 4.4 Point-in-time backtesting framework
`src/backtest/engine.py` is deliberately not a second implementation of the odds store
— it drives `src/store/pit_store.PointInTimeStore` (append-only, immutable writes) and
`src/store/settlement.py` (win/loss/push grading) rather than re-deriving either.

**Leakage prevention has three independent layers:**
1. **Write layer** — a snapshot batch, once written, can never be overwritten (a
   duplicate write path raises `FileExistsError`), so there is no "future version" of a
   past row that could ever leak.
2. **Read layer** — `PointInTimeStore.read_as_of(decision_time, event_id)` is the only
   public read path. It filters strictly on `capture_time <= decision_time`, then
   re-checks its own output before returning: any row later than `decision_time` raises
   `LeakageError` rather than being silently returned. A regression test deliberately
   breaks the internal filter and confirms the error fires.
3. **Backtest engine** — at every simulated decision point in a game's history, the
   engine re-derives the strategy's visible data via a **fresh** `read_as_of()` call,
   never by slicing a larger pull locally in pandas. This means there is exactly one
   place in the whole system leakage could be introduced, and it is the one place
   that's directly tested. The engine's own leakage test seeds a snapshot timestamped
   after kickoff with an obviously-wrong price and confirms it never appears in any
   strategy-visible data and never contaminates the computed closing price.

Execution assumptions: a strategy places at most one bet per game, at the first
decision point it chooses to act; P&L uses the actual price available at that decision
point, not a theoretical fill.

### 4.5 Modeling approach
Baseline = devigged market close (§4.2/§4.3); on live 2026 data this is Pinnacle, on the
2015-2024 historical data used here it is nflverse's consensus close (§3.1 — the two are
not the same claim, and this section's results are calibration-quality validation, not a
CLV result).

**Features** (`src/model/features.py`): pre-game offensive and defensive EPA-per-play and
success rate, one row per team per game, built from nflverse play-by-play
(`src/features/load_static.py::load_pbp`, trimmed to a 12-column schema). Every feature
is shifted one game before aggregating — a team's own game never contributes to its own
pre-game feature — season-to-date expanding mean by default (resets each season, so
roster turnover between years doesn't blend into a week-1 average). Regression-tested
with a deliberate +100 EPA outlier that must not leak into its own game's row. Schedule
context (rest days, divisional flag, roof/surface/weather) is joined in via
`build_game_features`. The model deliberately excludes market odds as an input — it is
scored *against* the market baseline, not fed the market's own price, so the comparison
stays "model vs. market."

**Model** (`src/model/train.py`): a standardized logistic regression — "start simple"
per blueprint Part E, before reaching for a gradient-boosted model. Ties (9 of 2743
games, 2015-2024) are excluded, since a binary win label can't encode them; rows missing
pre-game history (a team's first cached game) are dropped rather than imputed.

**Split:** a three-way, out-of-time split by season — train (2015-2021), calibrate
(2022), test (2023-2024) — so no season is used for more than one of {fit model, fit
calibration, report results}.

**Calibration** (`src/model/calibration.py`): the base model is wrapped as a frozen
estimator (`sklearn.frozen.FrozenEstimator`) and passed to `CalibratedClassifierCV`, so
the calibration step cannot silently retrain the base model on the calibration split.
Isotonic regression by default; Platt scaling (`method="sigmoid"`) available for smaller
calibration sets.

**Evaluation:** Brier score and log loss (§4.7) on the held-out test seasons, model vs.
market baseline vs. calibrated model. Reference run (`python -m src.model.calibration`,
1743/282/570 train/calib/test games): the market baseline (Brier 0.210) beats both the
raw (0.232) and calibrated (0.229) logistic model — consistent with the blueprint's own
expectation that "the market already is the model." This is reported as the honest
starting point, not a result to be explained away.

**Opponent-adjustment benchmark (Elo).** The EPA features above are not opponent-adjusted
— a team's rolling EPA looks identical whether it was earned against a strong or weak
defense. `src/model/elo.py` adds the standard fix from the sports-forecasting literature:
FiveThirtyEight-style NFL Elo (starting rating 1500, K=20, margin-of-victory multiplier
that dampens credit for a big favorite beating up on a team it was already better than,
home-field advantage of 48 points, one-third reversion toward the mean at each new
season). Sequential by construction — a team's rating entering a game reflects only games
strictly before it, no shift() trick required the way EPA needs one. Relocated franchises
(SD→LAC, OAK→LV, STL→LA, confirmed against the cached schedule rather than assumed) are
canonicalized so a rating carries through a move.

Same train/calib/test split, same test-season games: **Elo alone (Brier 0.221) already
beats the full EPA feature set (0.232)** — opponent-adjustment on its own outperforms raw
team-level EPA rolling averages. Combining both feature sets in one logistic regression
(`epa_plus_elo`, Brier 0.219) closes roughly 57% of the gap between EPA-only and the
market baseline. Still short of market — expected, and not explained away — but the first
result in this project that substantively validates "opponent-adjustment is the modeling
gap that matters most," rather than asserting it. Full reference run, coefficients, and
the resulting end-of-2024 rating table: `notebooks/model_backtest_results.ipynb`.

**Garbage-time filtering — a negative result, reported as found.** The standard
nflverse-community convention excludes plays from the 4th quarter or overtime with win
probability outside [0.05, 0.95] — the outcome is no longer competitively in doubt, and
EPA earned there (backups in, prevent defense, clock-killing) arguably doesn't reflect
true team strength. `src/model/features.py::team_game_epa(..., exclude_garbage_time=True)`
implements this (requires `qtr`, added to the cached play-by-play schema). Sanity check:
11.3% of real plays are flagged, with a genuine EPA mean shift (garbage-time plays average
-0.053 EPA/play vs. 0.013 for competitive snaps) — the filter behaves as intended, not
degenerately.

**The hypothesis did not hold.** On the same split, filtering makes both the EPA-only and
EPA+Elo variants slightly *worse* (0.2316→0.2335 and 0.2192→0.2197 respectively), not
better. Plausible reasons, stated as hypotheses rather than proven: removing ~11% of plays
shrinks the effective sample behind each team's rolling average (especially costly
early-season, when the window is already small), and garbage-time EPA — while lower on
average — is not obviously *wrong*; a genuinely strong team's backups plausibly still
outperform a weak team's, so the excluded plays likely still carry real signal, just with
a level shift rather than pure noise. `exclude_garbage_time` stays opt-in, default `False`
— this negative result is the reason, not an oversight. Full comparison:
`notebooks/model_backtest_results.ipynb`.

**Gradient-boosted trees — a mixed result.** Blueprint Part E named "logistic OR GBM" as
the starting options; only logistic had actually been tried until now.
`src/model/train.py::fit_gbm_model` adds `sklearn.ensemble.HistGradientBoostingClassifier`
(no new dependency, no `StandardScaler` needed — tree splits are scale-invariant). A small
hand-swept hyperparameter grid was run first, since GBM is far more sensitive to
hyperparameters than logistic regression and reporting one arbitrary config would be a
weak comparison; the best found (`max_depth=2, max_iter=50, learning_rate=0.1`) became the
default, not a first guess.

Result, same holdout: **GBM slightly beats logistic regression on EPA-only** (0.2300 vs.
0.2316), **but loses once Elo is added** (0.2217 vs. 0.2192). Read together with the
opponent-adjustment result above: GBM finds a small amount of genuine non-linear structure
in the EPA features alone that a linear model misses, but once Elo — a strong signal
that's plausibly already close to linear in log-odds — is added, the extra model capacity
GBM brings stops helping and starts adding noise instead. Neither result is large enough
to change the reference model: logistic regression on EPA+Elo (0.2192) remains the best
result to date. Full sweep and comparison: `notebooks/model_backtest_results.ipynb`.

**QB-level Elo — a modest improvement, later found not to survive multiple-comparison
correction (§6.4) — read the result below as suggestive, not confirmed.** Team Elo
captures team strength but not
who's under center; a backup starting for a strong team and losing isn't the same signal
as the starter losing. `src/model/qb_elo.py` adds a QB-level residual rating, deliberately
this project's own simplification rather than a replication of a published model (e.g.
FiveThirtyEight's ANY/A-regression-based QB Elo): a QB's rating moves based on how much
the *team's actual result* over- or under-performed what the *team's own pre-game Elo
alone* (ignoring QB identity) predicted, using a smaller K (8, vs. team Elo's 20) since a
QB explains part of a team's result, not all of it. Data: nflverse's schedule already
carries `home_qb_id`/`away_qb_id` for every game, zero missing across all 2743 cached
games (2015-2024) — no new pull needed. Sequential and leakage-free the same way team Elo
is; no season reversion (v1 simplification — a starting QB's skill is more stable year to
year than a full roster turnover).

Same split, same test-season games: **`epa_elo_qb` (Brier 0.2170) beats `epa_plus_elo`
(0.2192)** — adding the QB residual closes a further slice of the gap to the market
baseline (0.2099). `qb_only` (0.2258) is worse than `elo_only` (0.2210) alone, as
expected — team Elo already captures most of what matters, and the QB residual is a
smaller signal riding on top of it, not a replacement. Sanity check before trusting the
result: final QB ratings (min 20 starts, 2015-2024) put Mahomes and Brady at the top,
Josh Allen/Goff/Lamar Jackson/Rodgers/Hurts/Prescott rounding out the top 10, and
late-career Eli Manning/Joe Flacco, Blake Bortles, Carson Wentz, Daniel Jones at the
bottom — directionally sound, not noise. Full comparison and rating table:
`notebooks/model_backtest_results.ipynb`.

**Correction, 2026-08-21 (§6.4):** this 0.2170-vs-0.2192 gap does not survive
Benjamini-Hochberg correction once judged alongside the 7 other model comparisons this
project has run against the same 2023-2024 test set (paired-permutation p=0.045
uncorrected, fails at q=0.05 corrected). The feature set (`COMBINED_QB_FEATURE_COLUMNS`)
stays in use as the practical baseline for every later comparison in this paper — that
choice doesn't hinge on this one claim — but "a real, modest improvement" was an
overclaim; treat this specific gap as plausible, not confirmed.

**Spread-cover and total-points regression -- a genuinely new market target, not
another moneyline variant.** Every model above predicts moneyline win probability, a
binary classification target -- and the hardest one to beat: mainline moneyline is
the most heavily arbed market in the industry, and this project's best win-probability
model (0.2170) still trails the market baseline (0.2099). Spread and total, while
still mainline markets, are driven by *continuous* quantities (margin of victory,
combined points) that carry strictly more information than a binary result, and had
never been modeled directly in this project until now -- only used as static market
comparison data. This tests whether that richer target produces a better-calibrated
model, reusing the exact same features, `time_based_split`, and `compare_to_baseline`
harness as every classification model above -- no new dependency, no new evaluation
framework.

**Method** (`build_margin_total_frame`, `fit_margin_model`, `fit_total_model` in
`src/model/train.py`): `margin = home_score - away_score` and `total_points =
home_score + away_score` as regression targets, `LinearRegression` on the same 15
EPA+Elo+QB-Elo features ("start simple," matching the win-probability model's own
history before GBM was tried). Sign convention (`home_covers = margin > spread_line`,
raw unflipped nflverse column) hand-verified against `src/store/settlement.py::settle()`
on real 2024 games -- including a real push case -- before writing any code. A raw
point prediction isn't a bet by itself; `src/model/calibration.py::fit_residual_std`
(residual std measured on the calibration split, never train, same discipline as
`fit_calibrated_model`) and `predict_over_proba` (P(actual > line) under a Normal
residual assumption, `scipy.stats.norm`) convert it into a probability comparable
against a devigged market cover/over probability (`market_baseline()`, already
generic over any two-outcome odds pair -- no new devig code).

**Result: the market wins both, as expected.** On the 2023-2024 test season: spread
cover, market baseline 0.2504 vs. model 0.2588 Brier (n=552, pushes excluded); total
over/under, market baseline 0.2500 vs. model 0.2581 (n=563). Consistent with the
win-probability model's own result and with spreads/totals being tightly priced
mainline markets -- not a surprising result, and not spun as one.

**Robustness check, run before trusting the Gaussian probability conversion at all --
and it surfaced a real, asymmetric finding.** A Normal-residual assumption was
flagged as a v1 simplification going in (NFL margins/totals aren't guaranteed
Gaussian -- blowouts fat-tail the distribution); the check was to test it, not assume
it holds. Residual normality on the calibration split: margin residuals pass (Shapiro-
Wilk p=0.075, fails to reject at 0.05) -- the Gaussian assumption is defensible there.
**Total-points residuals do not** (Shapiro-Wilk p=0.009, moderately right-skewed) --
genuinely non-normal, not a false alarm. A second check -- comparing the Normal-based
probability against a non-parametric empirical-residual alternative
(`predict_over_proba_empirical`), the same "does the result survive a different
reasonable methodological choice" discipline as the devig method comparison (§4.2) --
found the two estimates stayed close for total despite the distributional violation
(0.2581 vs. 0.2585 Brier). The miscalibration this check was designed to catch turned
out to be small enough not to change the conclusion, but that's a confidence the check
earned, not one assumed going in. Full results and both robustness checks:
`notebooks/model_backtest_results.ipynb`.

**Game-level Elo aggregation -- making receiver/pass-rush Elo usable by any model,
then testing whether that helps.** Receiver Elo (§3.7) and pass-rush Elo (§3.8) are
both play-level -- one row per target or dropback -- so neither was reachable by any
game-outcome model until `src/model/game_level_features.py` rolled them up.
Pass-rush is nearly free: its output is already team-level, so a team's rating
entering a game is already sitting on that game's first play by construction --
`aggregate_pass_rush_elo_to_game` is a groupby-first, not a new computation. Receiver
Elo needs a real design decision, since a "receiving corps" is a set of players, not
one entity: the roster join reuses `player_status.py::current_team` (active WR/TE
only, the same trade-safe lookup §3.9 built), a player's rating carries forward
across games he isn't targeted in (`merge_asof`, leakage-free), and the aggregate is
the mean of the **top 3 by current rating**, not a flat roster average -- a
deliberate v1 simplification (target-share weighting is the natural v2, gated on
data unavailable pre-game).

**Validated against a real injury case, not just unit tests, before trusting it:**
Justin Jefferson's 2023 hamstring IR stint (weeks 6-12, confirmed against his real
roster status). The aggregation correctly excludes him from Minnesota's receiving
corps for that exact window and correctly re-includes him at his pre-injury rating
the instant he returns (week 14) -- next-men-up (Hockenson, Mundt, Addison) fill the
gap between, exactly as intended.

**Wired into all three targets built this session (moneyline, margin, total) --
clean negative result, consistent across all three.** Adding receiving-corps Elo,
opponent pass-defense Elo, and pass-rush/protection Elo makes every model slightly
*worse*: moneyline 0.2173 -> 0.2180, margin 0.2587 -> 0.2590, total 0.2585 -> 0.2616
(same reference split, though ~50 fewer training games due to receiver/pass-rush
coverage gaps). Same pattern as GBM (§4.5 above): more model inputs don't help at
this sample size (~1,690-1,740 training games) -- plausibly because these features
correlate heavily with team Elo (already the dominant signal) and add
multicollinearity noise rather than new information. **The infrastructure itself is
still a real, reusable result** -- both ratings are now genuinely usable by any
future game-outcome model, not stuck at play-level; this specific way of using them
(naive linear addition to the existing feature set) doesn't help, which is a finding
about the modeling choice, not a verdict on the underlying ratings (independently
sanity-checked already in §3.7/§3.8, and validated again here against the Jefferson
case). Full results: `notebooks/model_backtest_results.ipynb`.

**Weather features -- a fifth negative result, same direction as the other four.**
`roof`/`surface`/`temp`/`wind` have flowed through `build_game_features()`'s output
since the first version of this pipeline, present in every training frame used in
this paper, but never used as a model input until `src/model/features.py::add_weather_features`.
Cleans them into four usable columns (`is_outdoor`, `temp_outdoor`/`wind_outdoor` --
a real reading if outdoor, a neutral 70/0 fallback if indoor, correct by construction
for domes, a genuine simplification for the ~9% of outdoor games with missing
readings -- and `is_grass`). Building this caught a real, pre-existing data-quality
bug: `"grass"` and `"grass "` (trailing whitespace) were counted as separate surface
categories in the raw column.

Result, all three targets: moneyline 0.2170 -> 0.2179, margin 0.2588 -> 0.2592, total
0.2581 -> 0.2598 -- worse across the board, including for wind on total points, the
single most plausible weather signal going in. **This is the fifth consecutive test
showing the same pattern** (GBM; receiver/pass-rush game-level features on all three
targets; weather on all three targets): more model inputs do not help at this sample
size (~1,690-1,740 training games), independent of how plausible the added signal
sounds beforehand. The consistency across five independent attempts is itself the
finding -- the binding constraint is dataset size, not a missing feature or a missing
model class.

**Correlated same-game outcomes -- a real, robust, positive finding, and a
methodologically different kind of result from anything else in this section.** A
documented industry mispricing mechanism: a sportsbook building a same-game-parlay
(SGP) price by multiplying single-leg probabilities together, as if the legs were
independent, when legs from the same game are often genuinely correlated. This tests
whether that correlation is real in NFL data -- not whether any specific book
misprices any specific parlay. No real posted SGP odds exist anywhere in this
project's data (The Odds API doesn't expose SGP pricing the way it exposes
single-market odds); a confirmed correlation is evidence the underlying mechanism a
bettor would need is real, not proof of a live, executable exploit.

`src/backtest/correlated_props.py::build_team_game_outcomes` builds one row per team
per game (home and away pooled, 5,468 team-games across 2,734 games) with: did the
team win, cover, did the game go over, did that team's *starting* QB (the schedule's
own `home_qb_id`/`away_qb_id`, the same authoritative field `qb_elo.py` already uses)
throw 2+ TDs, did the team's leading receiver clear 75 yards, did the team's leading
rusher clear 100. `measure_leg_correlation` computes the lift (P(A∩B)/(P(A)×P(B)) --
1.0 means independent) and a chi-square significance test per pair, backed by a free
new cached dataset (`src/features/load_static.py::load_player_stats`, nflverse's
weekly player box scores, 2015-2024).

**Every pair tested is significantly positively correlated: lift 1.07-1.48, p-values
from 1e-12 to 1e-142.** Strongest: `team_won x leading_rusher_100plus` (lift 1.475 --
a known football phenomenon, leading teams run more to control the clock) and
`game_over x qb_2plus_tds` (lift 1.395 -- points disproportionately come from passing
touchdowns). **Robustness check, same discipline as the props-arbitrage week-by-week
check: does this hold every season individually, or is it a ten-year pooling
artifact?** It holds cleanly -- both pairs are significantly positively correlated in
all 10 individual seasons (2015-2024), lift consistently 1.27-1.59, never crossing
into insignificance in any single year. Unlike some earlier checks this session that
killed a promising-looking result (the props EV backtest's threshold sweep), this one
survives -- the strongest, most robust new finding in this section. **Stated plainly,
one more time, so it isn't overclaimed:** this confirms the correlation is real and
stable, not that any specific book's SGP pricing is exploitable today -- that requires
real posted SGP odds this project doesn't have, and is the natural next check if such
data ever becomes available. Full results:
`notebooks/model_backtest_results.ipynb`.

**Pricing the correlation -- a quantified edge, not just a statistical fact.** The
correlation result above confirms the precondition for SGP mispricing is real; this
turns it into the same kind of output every other +EV signal in this project
produces (an edge percentage, a Kelly stake), reusing `src/signal/sizing.py`
unchanged rather than inventing a bespoke calculation. The model
(`src/backtest/correlated_props.py::naive_parlay_price`/`correlated_edge`): if a book
builds a same-game-parlay price by multiplying each leg's own *vigged* single-leg
price together (a documented, real SGP-pricing approach for at least some books),
using `src/devig/methods.py::devig_multiplicative`'s own vig convention in reverse,
and the TRUE joint probability is the one already measured (not assumed), the
resulting bettor EV and suggested stake follow directly. The vig assumption is
measured, not guessed: Pinnacle's own real vig on 5,005 Over/Under prop pairs from
this project's complete 2023+2024 historical pull averages 6.29%.

**Result: 6 of 7 pairs show positive edge; the weakest correlation (`team_won x
leading_receiver_75plus`, lift 1.07) does not clear the vig hurdle** -- a small
negative edge (-3.9%). This differentiated outcome is itself reassuring: "6 of 7
work, 1 doesn't" is more credible than "everything works," which would look like an
artifact of the pricing model rather than a real signal. The two strongest pairs
(`team_won x leading_rusher_100plus`: +31.9% edge, $1.39 suggested stake;
`game_over x qb_2plus_tds`: +24.8% edge, $2.00 stake -- capped) reuse the exact same
fractional-Kelly-then-bankroll-cap sizing every other spot in this project uses.

**Robustness check: does the edge survive if the vig assumption is wrong?** 6.29% is
Pinnacle's own measured prop vig, but execution books typically carry more, and a
real multi-leg SGP engine's effective vig isn't independently measured here. Swept
across this project's own measured mainline vig (2.97%), the standard -110/-110
convention (4.76%), the measured prop vig (6.29%), and two higher retail-book
scenarios (8%, 10%): **both strongest pairs stay solidly positive-EV even at 10%
vig**, well above the measured mean -- the edge shrinks monotonically as assumed vig
rises (mechanically expected) but never crosses zero within a realistic range.

**Honest summary, stated one more time so it isn't overclaimed:** a real, quantified,
robustness-checked theoretical edge *if* a book prices a same-game parlay by
multiplying vigged single-leg prices together -- not a confirmed live exploit against
any specific book's actual SGP engine, since no real posted SGP odds exist anywhere
in this project's data to check against directly. The natural next step, if this is
ever revisited, is comparing this model's predicted naive price against a real posted
SGP price the moment one becomes available -- that comparison, not more analysis on
top of this one, is what would turn "quantified theoretical edge" into "confirmed
mispricing." Full results: `notebooks/model_backtest_results.ipynb`.

**Making the edge game-specific, not just pooled -- and a real finding along the
way about what "game-specific" actually buys here.** The pricing above uses one
pooled lift for each leg pair across all games. The natural next question, prompted
directly by the moneyline/spread architecture already built in this project: can the
market's own real, per-game devigged win probability (`market_prob_home` from
`build_training_frame`, already computed for every game) replace that pooled average
with something specific to the actual matchup being priced?

Checked before trusting a pooled lift for that purpose: **it isn't constant.** Lift
for `team_won x leading_rusher_100plus` runs from 1.76 for underdogs
(market win prob < 0.45) down to 1.12 for heavy favorites (> 0.70), monotonically,
across four fixed probability buckets (`FAVORITE_BUCKETS` in
`correlated_props.py`), all individually significant (p from 4.8e-5 to 5.1e-24, n
700-2,245 per bucket). Same direction for `game_over x qb_2plus_tds` (1.49 down to
1.25). The interpretation is football-plausible: an underdog's win is
disproportionately likely to come via grinding out a big rushing performance
(clock control in an upset), while a heavy favorite's win is more "routine" and
doesn't need the same correlated performance to happen.
`measure_leg_correlation_by_bucket` and `estimate_game_specific_joint_prob` (both in
`correlated_props.py`) implement the stratified version.

**Applying this to real 2024 test-season games surfaced something worth stating
precisely, not glossing over: the resulting edge is not actually a smooth per-game
number.** Algebraically, under the multiplicative model, `naive_parlay_price`
scales as `1/p_a` while the estimated joint probability scales as `p_a` directly --
they cancel. Worked through: `edge = lift/(1+vig)^2 - 1`, a constant that depends
only on which bucket a game falls into, not on the exact market probability within
it (confirmed against real games: every underdog-bucket game priced to the *same*
+57.5% edge, whether the team's market win probability was 7% or 32%). The genuinely
per-game number that *does* vary continuously with the specific matchup is the
recommended Kelly stake -- because Kelly sizing depends on the actual decimal price
offered, and that price still varies with `p_a` even though the EV percentage
doesn't. Real examples from the 2024 test games: underdog-bucket edge is a flat
+57.5% regardless of exact market probability, with stakes ranging ~$0.34-$1.51
across games depending on how big an underdog; heavy-favorite-bucket edge is a
near-zero +0.5% before an additional effect takes over near the extreme tail.

That tail effect is the second real finding: once a team's market win probability
climbs high enough that the raw joint-probability estimate would exceed the pooled
marginal `P(B)` -- concretely, above `p_a = 1/lift` (≈0.89 for the heavy-favorite
bucket's 1.12 lift) -- the clip in `estimate_game_specific_joint_prob` binds, and
the model correctly refuses to let `P(A∩B)` exceed `P(B)`. Past that point the edge
erodes and turns negative for the very heaviest favorites (observed: -0.2% to -3.4%
for teams above 90% market win probability in the 2024 test season) -- a sensible
constraint, not a bug: if a team is already a 92% favorite, "team wins AND their
leading rusher goes for 100+" cannot be meaningfully more likely than the leading
rusher hitting 100+ on its own, since the win is already close to certain.

**Honest summary:** the moneyline/spread architecture's market probabilities do add
real, verified information here -- which bucket (and, near the tail, which side of
the clip) a specific game falls into -- but under this multiplicative pricing model
that information is coarser than "a continuous per-game edge," collapsing to four
discrete edge levels plus a tail correction. The Kelly stake, not the edge
percentage, is where per-game granularity actually shows up. Full bucket table and
real-game examples: `notebooks/model_backtest_results.ipynb`.

**Extending the bucket sweep to all 7 leg pairs (2026-08-21), not just the 2 tested
above.** Bucketing was only exercised on the two pairs with the strongest pooled
lift. The natural check: does bucketing change the verdict for the other 5 pairs --
especially `team_won x leading_receiver_75plus`, the one pair whose *pooled* edge was
negative (-4.0%, failed the vig hurdle in §4.5 above)? Added `bucket_edge(lift, vig)`
to `correlated_props.py`, the closed-form result derived above
(`edge = lift/(1+vig)^2 - 1`) as a real, tested function rather than notebook
arithmetic -- lets a bucket screened for "clears vig" without looping over every
individual game, and matches `correlated_edge`'s actual edge exactly whenever the
joint estimate isn't hitting the clip.

**Result: bucketing partially rescues the failed pair, and reveals a real negative
segment hiding inside two previously "successful" pooled pairs.**

- `team_won x leading_receiver_75plus`: the underdog bucket (market win prob < 0.45,
  n=2,245) clears vig at **+0.30% edge**, p=1e-5 -- real and significant, but tiny,
  almost certainly not worth the execution friction of placing it. The `narrow` and
  `favorite` buckets for this same pair are NOT significant (p=0.63, p=0.48) -- lift
  is statistically indistinguishable from 1.0 there, so the negative closed-form
  numbers those buckets produce (-9.2%, -9.5%) should not be read as real negative
  edges, just "no measurable correlation, don't bet it" (same discipline as every
  other insignificant result in this project -- a lift that looks real but isn't
  shouldn't be reported as a finding).
- `team_won x qb_2plus_tds` (pooled edge a healthy +12.1%) has a `heavy_favorite`
  bucket (market win prob > 0.70, n=900) that goes **negative, -1.2% edge**, p<1e-13
  (significant, i.e. this is a real, precisely-measured small negative edge, not
  noise) -- a pooled-positive pair that would still lose money if bet blindly on
  heavy favorites specifically.
- `leading_receiver_75plus x qb_2plus_tds` (pooled edge +8.3%) has its
  `heavy_favorite` bucket land almost exactly at breakeven (-0.01% edge, p<1e-10).
- The two strongest pairs from the original pooled analysis --
  `team_won x leading_rusher_100plus` and `game_over x qb_2plus_tds` -- along with
  both `team_covers` pairs, clear vig in **all four buckets**, favorite strength and
  all, and every one of those 16 buckets is individually significant (p from 1e-5 to
  1e-134). These four pairs are the genuinely robust ones: real edge regardless of
  which team is favored.

**How this changes the picture:** bucketing isn't just a per-game pricing refinement,
it's a real screen. A pooled edge number can hide a bucket that's actually
loss-making (the two "successful" pairs above), and a pooled failure can hide a
narrow, real, significant pocket of edge (the receiver pair's underdog bucket) --
too small to act on here, but the mechanism is confirmed, which matters more than the
number itself. Same honest ceiling as everywhere else in this section: these are
theoretical edges against a naive-independence SGP price, not confirmed against any
real book quote. Full 7-pair x 4-bucket table: `notebooks/model_backtest_results.ipynb`.

**Portfolio validation: is any of this leakage or luck? (2026-08-21)** Prompted directly
by the question "how do we account for overfitting or leakage -- what tests tell us if
this is bullshit or real edge." Four checks, `src/backtest/validation.py`
(`split_by_season`, `expanding_season_folds`, `permutation_test_lift`,
`benjamini_hochberg`; all independently unit-tested, not just applied ad hoc in a
notebook).

**1. A real, previously-uncaught leak, found and fixed.** The bucket-lift pricing above
computed lift on the FULL 2015-2024 pool -- including 2024 -- then applied it to price
"test" 2024 games that had themselves contributed to that same lift estimate. Not
hypothetical: recomputing lift on 2015-2023 only and pricing 2024 games strictly
out-of-sample changes the real, actionable conclusion. `underdog`/`narrow` buckets hold
up robustly -- `team_won x leading_rusher_100plus`'s underdog edge, measured strictly
within 2024 alone, comes in even higher than the leaky in-sample number (+97.7% vs.
+57.5%). But `favorite`/`heavy_favorite` buckets do not: the same pair's `favorite`
bucket collapses from +19.2% (in-sample) to +3.8% (realized-2024), and
`game_over x qb_2plus_tds`'s `favorite` bucket flips sign entirely (+20.9% to -0.9%).
Revised conclusion: only the `underdog`/`narrow` buckets of these two pairs are backed
by an honest held-out check; `favorite`/`heavy_favorite`, despite "clearing vig" in the
original pooled analysis, are not reliably real.

**2. Walk-forward across four expanding-window folds confirms this is a pattern, not a
2024 fluke.** Training on all prior seasons and testing the next one in turn (test
seasons 2021-2024), direction agreement between train-fold and held-out-fold edge is
84% across 32 fold x bucket combinations, with a 0.70 correlation between train lift and
held-out lift -- real generalization, not perfect. `underdog`/`narrow` are positive in
essentially every fold for both pairs; `favorite`/`heavy_favorite` flip sign repeatedly
(`team_won x leading_rusher_100plus`'s heavy_favorite edge is negative in 3 of 4 folds).
Exactly the signature of a real-but-narrower edge, not pure noise (which wouldn't cohere
by bucket at all) and not a fully robust one either (which wouldn't flip sign
repeatedly in the same bucket).

**3. A permutation test confirms the underlying correlation mechanism independent of
chi-square's assumptions.** `chi2_contingency` relies on an asymptotic approximation;
`permutation_test_lift` instead shuffles one indicator 10,000 times (destroying any real
association while preserving both marginal rates exactly) and reports the empirical
fraction of shuffles that matched or exceeded the observed lift. All 7 pooled leg pairs
-- including the weakest, `team_won x leading_receiver_75plus` (lift 1.07) -- come back
at `p_empirical = 0.0001`: not one of 10,000 shuffles produced a lift that extreme, for
any pair. A negative control matters just as much here: run on the two buckets
chi-square already found NOT significant, permutation p-values come back unremarkable
(0.24-0.31) -- the methodology correctly distinguishes real signal from noise in both
directions, not just when it's convenient.

**4. Multiple-comparison correction does not overturn anything already reported.** This
project has produced 57 real p-values with this session's work: 7 pooled correlated-props
tests, 20 per-season robustness checks, 28 bucket-level tests, and 2 Shapiro-Wilk
residual-normality checks (§4.5 above) -- each judged against its own p<0.05 in
isolation, with no correction applied anywhere until now. Benjamini-Hochberg FDR at
q=0.05, applied at the most conservative level (combined across all 57 at once, not
just within each family), leaves 54/57 significant. The 3 casualties: the same two
bucket-level results already known and reported as not significant (never claimed as
findings), plus the margin-residual Shapiro-Wilk test (p=0.075) -- a diagnostic where
NOT rejecting normality is the hoped-for outcome, not a discovery claim, so its
exclusion doesn't threaten anything either. The many-tests risk was real in principle;
in practice this project's effect sizes (most p-values 1e-8 to 1e-140) are large enough
that correction changes nothing substantive.

**Overall verdict.** The pooled same-game correlation finding is real -- confirmed
independent of chi-square by permutation testing, and survives multiple-comparison
correction. The game-specific bucket pricing needed a real correction: half its claimed
granularity (the favorite/heavy_favorite buckets) was not earned by an honest
out-of-sample check, while the other half (underdog/narrow) holds up under both a
proper train/test split and walk-forward validation. Not "the correlated-props work was
bullshit" -- the core mechanism is real and now independently verified three different
ways -- but "part of its claimed precision wasn't earned yet, and now it's been checked
rather than assumed." Full validation notebook: `notebooks/model_backtest_results.ipynb`.

**The fix is enforced in code, not left as a documentation caveat.** `price_bucket_bet`
(`src/backtest/correlated_props.py`) is now the one real pricing entrypoint a future
live scanner should call — it classifies a game's bucket and **refuses**
(`UnvalidatedBucketError`) to price `favorite`/`heavy_favorite` unless the caller
explicitly opts in via `allow_unvalidated=True`. `estimate_game_specific_joint_prob`
and `correlated_edge` themselves are unchanged and still have no notion of which
bucket is trustworthy — their docstrings now point to `price_bucket_bet` so a future
reader lands on the safe path rather than the raw one.

**Extension: team-total rushing/passing yards vs. moneyline, real market-implied legs
(2026-08-22, methodology_backlog.md #9).** The correlated-props legs above are fixed
thresholds (100+ rush yards, 2+ pass TDs) checked against population base rates. Once
real per-player Pinnacle prop lines existed for the full 2023-2024 test set
(`src/collect/mainline_historical.py`, `src/collect/props_historical.py`), the same
underlying question -- do books fail to jointly calibrate correlated same-game
outcomes -- became testable with a genuinely different leg construction: "team
cleared its own real market-implied total" (sum of every player's real posted line,
`src/backtest/team_total_props.py::build_team_total_lines`) instead of a fixed
threshold. Team-total pricing uncertainty is measured directly from real data
(`actual_team_total - implied_team_total_line`, on real historical games) rather
than assumed from summed per-player variances under an independence assumption known
to be wrong (running backs share touches) -- one real team-level parameter,
calibrated, not guessed.

**Result: the underdog bucket replicates the exact same pattern the fixed-threshold
legs found, using an independently-constructed leg definition.** Rushing (lift 1.19,
p=2.8e-5) and passing (lift 1.28, p=6.0e-5) team-total-over legs correlate with
`team_won` in the underdog bucket, survive the assumption-free permutation test, and
survive an honest 2023-train/2024-test out-of-sample split (rushing: 1.226 train ->
1.167 realized; passing: 1.311 -> 1.216 realized -- both hold up). Priced edge (same
`bucket_edge` formula, same measured 6.29% prop vig): rushing underdog **+5.5%**,
passing underdog **+12.9%**. The favorite bucket (rushing only) repeats the exact
failure mode already found for the fixed-threshold legs: nominally significant
pooled (p=0.00026) but priced edge is already negative (-2.4%) and shrinks further
out-of-sample (1.129 -> 1.051) -- not a real, tradeable signal.

Folded into the same 57-p-value multiple-comparison family (now 67) rather than a
fresh q=0.05 family of its own -- 58/67 survive BH correction, and all 3
individually-significant team-total tests (rushing pooled, rushing underdog bucket,
passing underdog bucket) survive even in this larger, stricter family.

**Same honest limitation the original correlated-props edge numbers already carry,
stated plainly again here:** there's no real posted price for "sum of individual
player lines" -- the priced edge confirms the correlation mechanism is real, not
proof a specific book misprices exactly this combination. Passing yards (usually one
real starting QB) is a cleaner construction than rushing (2-3 backs sharing touches).
Full validation, including the out-of-sample table: `notebooks/model_backtest_results.ipynb`.

### 4.6 Bet sizing
Implemented in `src/signal/sizing.py`:
- `expected_value(p, d) = p(d-1) - (1-p)`.
- `kelly_fraction(p, d)`: full Kelly, `b=d-1, q=1-p, f*=(bp-q)/b` — can be negative
  (no edge on this side), which downstream sizing must treat as "don't bet."
- `fractional_kelly(p, d, k=0.375)`: `k` in [0.25, 0.5], default is the midpoint.
- `apply_bankroll_caps(stake, bankroll=100, max_bet=2.00, min_bet=0.10)`: clips to
  `[min_bet, min(max_bet, bankroll)]`; below `min_bet` (including any non-positive
  stake) returns 0 rather than rounding up.

**Hard limits, confirmed:** $100 bankroll, $2.00 max bet (2%), $0.10 min bet — these
are the literal defaults in `sizing.py`. The bankroll is not unlimited: up to 2 reloads
are allowed as a personal risk-discipline ceiling ($300 total risk capital across the
season), but this is a manual constraint the user enforces themselves, not something
the codebase tracks, automates, or resets. Per blueprint B.4, a $100 bankroll "cannot
compound in a meaningful way" — sizing here demonstrates correct method, not bankroll
growth, and that framing holds regardless of how many reloads are used.

### 4.7 Evaluation framework
Implemented in `src/model/evaluate.py`:
- `brier_score(p, y) = mean((p-y)^2)`.
- `log_loss(p, y) = -mean(y·log(p) + (1-y)·log(1-p))`, with `p` clipped away from
  exactly 0/1 so one confident-and-wrong prediction can't blow up to infinity.
- `reliability_curve(p, y, n_bins=10)`: binned predicted vs. observed frequency;
  empty bins are kept (not dropped) so sparse regions of the probability space stay
  visible.
- `power_analysis(effect_size_clv, variance, alpha=0.05, power=0.8)`: one-sample
  z-test sample-size formula, `n = ((z_{α/2} + z_power)·σ/effect)²`. Concretely: a 0.5%
  mean-CLV edge against 10% bet-to-bet noise needs `n≈3140` bets to detect at the
  standard 0.05/0.8 significance/power — well beyond what one NFL season of a few
  hundred bets can confirm. This number gets reported in §5.5 before any CLV result,
  per the blueprint's insistence that the honesty framing come first, not as an excuse
  after a null finding.
- Bootstrap CI on mean CLV: `bootstrap_ci()`, §4.3.

### 4.8 Non-stationarity and drift detection
Implemented in `src/drift/monitor.py`. "The genuinely hard part," per blueprint Part E:
books patch inefficiencies and edges decay, and the interesting question is knowing an
edge died before the bankroll says so. Three signals:
- `rolling_mean_clv(clv_series, window)`: trailing-window mean CLV, using whatever
  history exists for the first `window - 1` bets rather than staying silent until the
  window fills.
- `cusum(x, target, threshold, drift)`: a two-sided Page (1954) CUSUM change-point
  detector. `drift` is the allowance/slack that absorbs ordinary noise so it doesn't
  slowly accumulate into a false alarm; too low and any random walk eventually trips
  it, too high and a real shift never crosses `threshold`. Not reset after firing --
  the caller decides whether a flag means the strategy pauses, or the detector restarts
  on the remaining series with a fresh target.
- `rolling_calibration_drift(p, y, window, reference_brier)`: rolling Brier score minus
  a reference value from the model's original holdout (§4.5's train/calib/test split),
  turning "calibration drifts" into a specific, thresholdable number.

**On the historical-vs-live split (§3.1):** this module is built and unit-tested against
synthetic series now, the same way `src/clv/metrics.py` and `src/backtest/engine.py`
were built before any real snapshot existed. It has nothing to monitor yet -- a rolling
CLV window needs a live CLV time series, which only exists from 2026-08-14 onward. §5.6
reports what it actually flagged, once there's enough of a season for a window to mean
anything.

### 4.9 Live +EV monitoring and alerting
A live counterpart to the historical backtester (§4.4): rather than replaying settled
games after the fact, `src/signal/live_scan.py` continuously compares each execution
book's *current* price against Pinnacle's *current* devigged fair value, so a good spot
is surfaced while the game is still open, not discovered later in a backtest.

**Mechanism.** For each event, Pinnacle's latest home/away moneyline prices (always from
the same poll, so they're devigged as one consistent market rather than mixing two
moments in time) are converted to a fair probability via `market_baseline()` (§4.2's
Shin default). For each execution book (DraftKings, FanDuel, BetMGM -- §3.4's manual
bet-execution venues, not an arbitrary book list), that fair probability and the book's
own decimal price feed directly into `expected_value(p, d)` (§4.6, unchanged) to get EV
per dollar staked. A spot is flagged when EV clears a **2% threshold**. Moneyline only
for now -- spread/total comparisons need matching line numbers between books to be a
clean apples-to-apples bet, deferred rather than built sloppily.

**Alert dedup.** A spot that stays flagged doesn't re-alert every cycle: `data/alert_state.json`
tracks the edge at last-alert time per (event, side, book), and only fires again once
the edge has grown by at least one percentage point since then
(`new_or_improved_spots()`).

**Delivery.** Alerts are a read-only notification, not an action: `src/notify/sms.py`
drives Messages.app via AppleScript to text a configured phone number -- no
third-party account, no bet ever placed automatically. This is consistent with the
manual-bets-only project scope (§3.4): the system finds and reports the spot, a human
places the bet.

**Deployment.** Runs as a second macOS launchd service (`com.nflclv.monitor`),
independent of the collector -- `StartInterval`-based (every 5 minutes, a short-lived
scan-and-exit script rather than a daemon), reading only local parquet files, so it
costs nothing against the Odds API credit budget and its cadence is decoupled from the
collector's own (§3.2).

**First live result (2026-08-17):** against a real `regions=eu,us` poll, the scanner
found 4 spots clearing the 2% threshold -- FanDuel and BetMGM each offering 3.6-6.1% EV
on two different underdog moneylines relative to Pinnacle's fair value at that moment.
Confirms the comparison logic end-to-end on real data; not a claim about the strategy's
long-run edge, which only the live season (§5) can establish.

**A real, live gap found and fixed (2026-08-21 adversarial audit).** `book_time` and
`pinnacle_time` were both already captured and returned on every spot, but never
actually checked against each other before flagging or texting an alert. Under normal
operation this doesn't matter (Pinnacle and the execution books are fetched in one
combined poll, so the two times land together) -- but if Pinnacle is missing from a
specific poll cycle, `_latest_two_sided_pinnacle` falls back to an older Pinnacle price
while the execution book's price stays fresh, and a spot could be flagged from
comparing a stale "fair" value against a live one, then texted to the user's phone with
no warning. `find_positive_ev_spots` now takes a `max_capture_gap` (default 30 minutes)
and drops any spot whose two prices weren't captured close enough together. This was a
gap in the service that has been running live and sending real SMS alerts since
2026-08-17 -- not caught by any test before this audit, since every existing fixture
happened to share one hardcoded capture time.

### 4.10 Middling: exploiting real line movement over time (2026-08-20)

**A different mechanism than every other strategy in this paper.** §4.5's correlated
props and §4.9's live scanner both compare prices at a single instant -- cross-book
divergence or model-vs-market disagreement. Middling instead exploits the SAME
market moving over real time: bet Team A -3 today; if the line later drifts to Team A
-7 (injury news, sharp money), bet Team B +7. If the final margin lands in (3, 7),
**both bets win outright** -- not a hedge, a genuine double win. Outside that window,
exactly one leg wins; there is no outcome where both lose (proven algebraically below,
and checked numerically in `tests/test_middling.py::test_middle_ev_never_loses_both_legs`).

**Why this had to be built live-first, unlike every other strategy here.** nflverse's
2015-2024 schedule data is closing-line-only -- there is no historical record of a
line moving over time, so middling cannot be backtested against the past the way
correlated props or the margin/total regression were. `PointInTimeStore` is the only
source of real intraday line movement available for this purpose, and it only starts
on 2026-08-14. This strategy's real track record has to be built forward from this
project's own live collection, not validated against history first.

**Mechanism, formalized.** `src/backtest/middling.py::win_interval(market, side, line)`
returns the (lo, hi) region of the true outcome (home_margin for SPREAD, total_score
for TOTAL) where a leg wins -- derived directly from `src/store/settlement.py::settle`'s
own arithmetic and cross-checked against it over a full integer margin/total grid, not
re-derived independently. `middle_window` intersects two opposite-side legs' win
regions; a real, positive-width intersection is a genuine middle. `best_middle_for_game`
finds the single WIDEST achievable window from all real quotes for one game across
every book and capture_time -- provably sufficient to use each side's single best-ever
quote rather than an exhaustive pairwise scan, because `win_interval` is monotonic in
`line` for each side (a lesser quote can only produce a subset of the best-vs-best
window).

**Pricing reuses this project's own established finding, deliberately not its own
regression models.** `middle_ev` prices a window under a Normal(mu, sigma) model of
the true outcome. `sigma` reuses `src/model/calibration.py::fit_residual_std` on the
existing margin/total regression (§4.5) -- a real, direct reuse. `mu`, however, is
**Pinnacle's own current line** (`pinnacle_reference_line`), not the regression
model's point prediction -- because every backtest in this paper found the market
beats the model (§5.2); plugging in a worse estimate here would be a step backward
with no justification. Sizing defaults to $2 per leg (the project's existing
per-bet cap, §4.6) rather than a joint 2-leg Kelly optimization over both stakes --
a real, harder problem the project's existing single-outcome Kelly math doesn't cover,
and not worth solving ahead of any live confirmation this strategy works at all.

**A genuine three-outcome payoff, priced honestly.** Unlike a pure hedge, a middle
usually wins exactly one leg and sometimes wins both -- `middle_ev` computes
`p_both_win`, `p_a_only`, `p_b_only`, and `p_neither` from the Normal model, and
`p_neither` is a real correctness check baked into the tests: for any genuine
opposite-side window, it must be ~0 regardless of where `mu`/`sigma` place the
probability mass, since the algebra guarantees at least one leg always wins.

**Deployment: deliberately manual, not a live service.** `make middle-scan-once`
(`src/backtest/middle_scan.py`) fits the margin/total models once per run purely to
extract their residual std, then scans the current store and prints/logs any real
window found -- no SMS wiring, unlike §4.9's monitor. Two reasons: real movement takes
days to accumulate this early in the season (a 5-minute service cadence would mostly
find nothing), and this strategy has zero live track record yet -- wiring an untested
pricing model straight to an unattended alert channel would be premature trust, the
same discipline already applied to the props scheduler (§3.6).

**First real smoke test (2026-08-20), against the live 2026 collector's actual data.**
`make middle-scan-once` against the real store found two live, bettable windows --
not from a line drifting over days yet (too early, §3.3), but from genuine cross-book
disagreement on which side of a near-even game to favor: DraftKings quoting SEA home
+1.5 while FanDuel independently quoted NE away +1.5 on the same game, and a similar
pair on GB/MIN. Both real, both at real execution-book prices, small (window widths
of 2.5-3.0 points, EV $0.04-$0.09 on $4 risked) -- exactly the modest scale expected
this early, and confirmation the full pipeline (detection -> Pinnacle-referenced
pricing -> EV) works end-to-end on live data, not just synthetic test fixtures. Not
yet a claim about this strategy's long-run edge -- that requires real games completing
against real middle bets, which only the live season can provide.

### 4.11 Steam detection: synchronized cross-book movement (2026-08-21)

**A third, distinct mechanism from middling and the live scanner.** §4.10's middling
exploits ONE line drifting over time (or across books) into a double-win window.
§4.9's live scanner compares ONE execution book against Pinnacle at a single instant.
Steam is neither: when several INDEPENDENT books move their price in the SAME
direction within a tight time window, that's a real signal professional/sharp money
hit the market broadly, not just one book's own line-setting choice. The actionable
follow-through: any real execution book that hasn't joined the move yet is still
quoting the pre-steam price -- worth betting before it corrects.

**Mechanism (`src/backtest/steam.py`).** `book_moves` computes each book's own
earliest-to-latest line change for a game/market/side. `detect_steam_move` requires
at least `min_books` (default 3) DISTINCT books to have moved the SAME direction,
with all of those moves clustering within `window` (default 1 hour) --
`_largest_time_cluster` is a straightforward max-points-in-a-sliding-window scan over
the small number of books this project tracks. `stale_books` are the real execution
books that haven't joined the cluster -- the part that has to be a genuine, placeable
bet, unlike the detection step itself (which counts every quoted book, Pinnacle
included, since a real steam move is market-wide, not specific to which books happen
to be bettable accounts here).

**Pricing reuses §4.10's math wholesale, not reinvented.** `win_interval` and
`pinnacle_reference_line` are imported directly from `middling.py` -- the "true
outcome" region a bet wins in and the market-consensus estimate of it are exactly the
same questions here. `price_stale_book_opportunity` is a single-leg analogue of
`middle_ev`'s Normal(mu, sigma) pricing, `mu` from Pinnacle's POST-steam line
(already incorporating the move) rather than a model prediction, same reasoning as
§4.10. `expected_value`/`fractional_kelly`/`apply_bankroll_caps` are `sizing.py`,
unchanged.

**Deployment: `make steam-scan-once`, deliberately manual, same reasoning as
middling** -- real synchronized movement takes time to accumulate, and this strategy
has zero live track record yet. `src/backtest/middle_scan.py`'s residual-std fitting
was promoted from a private helper to `fit_residual_stds()` so both scan scripts
reuse the exact same sigma-fitting pipeline rather than duplicating it.

**First real smoke test (2026-08-21), against the live 2026 collector's actual
data.** `make steam-scan-once` found 5 real opportunities immediately -- e.g. 3 books
(coolbet, draftkings, tipico_de) moved ATL/PIT's total the same direction within the
window, with BetMGM still quoting the stale total; a similar 3-book cluster on
DAL/NYG's total left BetMGM, DraftKings, and FanDuel all stale simultaneously. Small
(EV $0.009-$0.010, stakes $0.34-$0.42) -- consistent with the modest scale middling's
own first smoke test found, and confirmation the full pipeline (detection ->
Pinnacle-referenced pricing -> EV) works end-to-end on live data. Same honest ceiling
as middling: real, live, and priced correctly, not yet a claim about long-run edge --
that needs real games completing against real steam bets.

---

## 5. Results

*[Fill in as the season generates data. Do not pre-write conclusions.]*

### 5.1 Devig method comparison
### 5.2 Model calibration
### 5.3 CLV results (headline)
### 5.4 Bootstrap confidence intervals
### 5.5 Power analysis: what this sample size can and cannot tell us
### 5.6 Drift monitor output

---

## 6. Discussion

### 6.1 Honest interpretation of the CLV result
*State the finding as it actually is. If null, say so and explain why that's still informative.*

### 6.2 Where the market was hardest to beat
### 6.3 Where the drift monitor fired, if it did
### 6.4 Limitations

**Test-set reuse across this project's many experiments — quantified, not just
flagged (2026-08-21 adversarial audit, then corrected 2026-08-21 same day after a
direct challenge: "why does the fix require a fresh season? I thought each feature
was evaluated separately?").** `test_seasons=[2023, 2024]` has been evaluated
separately 8 times across this project's history. This is distinct from, and not
caught by, the code-level leakage architecture (`PointInTimeStore`, `time_based_split`)
— those guard against the *model* seeing future data; this is the *researcher*
repeatedly observing the same test set's feedback across many experiments. Two
distinct sub-risks live under this one heading, and only one of them needed a fresh
season:

- **Adaptive tuning** (using test feedback to decide what to try next) — ruled out.
  Commit history shows each new feature (QB Elo, receiver Elo, weather, garbage-time)
  reads as an independently-motivated football hypothesis, not a retuned resubmission
  chasing a prior failure's test score.
- **Selection bias / winner's-curse** — real, and NOT ruled out by the above. Even
  with zero tuning, whichever of 8 honest, independently-run candidates happens to
  beat its baseline on that specific 570-game slice is expected to look better than
  its true population performance, purely from which slice it was evaluated against.
  This is the exact same statistical family as the multiple-comparisons problem
  `benjamini_hochberg` already corrected for correlated-props' chi-square p-values —
  and, critically, it's checkable with data already in hand, no new season required.

**Checked it directly.** For each of the 8 comparisons, computed each game's
paired Brier-score improvement (baseline error minus candidate error) and ran
`paired_permutation_test_mean_diff` (sign-flip permutation test on the paired
per-game deltas, no distributional assumption), then corrected all 8 p-values
together with `benjamini_hochberg`. **Result: only `elo_add_on` (base Elo vs.
EPA-only) survives — p=0.0014, an improvement (ΔBrier=0.0124) roughly 6x larger than
QB Elo's.** `qb_elo` — this project's own current "reference model to beat" — does
**not** survive: its raw p-value (0.045) clears the naive uncorrected 0.05 threshold,
which is exactly why it read as a confirmed improvement in isolation; corrected for
having been one of 8 looks at the same test set, it doesn't clear the bar. The other
6 (GBM, garbage-time, both expanded-feature checks, weather, and the margin/total
expanded-feature check) were already non-significant before correction, consistent
with the "5 consecutive negative results" pattern already on record.

**What this does and doesn't change.** `COMBINED_QB_FEATURE_COLUMNS` (EPA + Elo + QB
Elo) remains the practical feature set every downstream comparison in this paper is
built against — that choice doesn't depend on this one marginal claim being airtight.
What changes is the claim itself: "QB Elo is a confirmed, independent improvement
over base Elo" is downgraded to "plausible, not confirmed" — the honest correction the
review question asked for. The remaining, deeper issue — a human having now seen 8
rounds of this exact test set's feedback, which no statistic computed on that same
data can fully undo — still has no fix without a genuinely fresh holdout season, not
available until one exists. Full analysis: `notebooks/model_backtest_results.ipynb`.

**Comparison #9, same day: rest/travel differential, evaluated correctly from the
start.** The first new feature tried after this correction was added as a 9th entry
in this same registry immediately, not benchmarked in isolation first and corrected
later. `add_rest_travel_features` (`src/model/features.py`) re-encodes `home_rest`/
`away_rest` (already in the base feature set since day one) as an explicit
differential plus short-week/bye-week binary flags, and adds genuinely new
information -- travel distance and timezone-crossing, via a hand-built 44-stadium
coordinate/timezone table (`src/model/stadiums.py`, each team's home venue derived
empirically per season from real schedule data, which handles the Rams/Chargers/
Raiders relocations and neutral-site games like Super Bowls correctly without a
hand-maintained relocation table). **Result: negative, like 6 of the other 8.**
ΔBrier=-0.0014 (the model got slightly worse), p=0.84 uncorrected -- not remotely
close to significant even before the multiple-comparison correction that would make
it harder still. Extends the "5 consecutive negative results in the same direction"
pattern (§3.9) to 6: garbage-time, GBM, both expanded-feature checks, weather, and
now rest/travel all fail the same way, on a mechanistically different feature each
time. That consistency keeps pointing at the same conclusion -- the constraint is
dataset size (~1,690-1,740 training games), not a missing feature.

**Comparison #10 & #11, training-window size — the first direct test of the "dataset
size" claim above, not another feature-content check.** Every comparison #1-#9 tested
whether adding a new feature helps; none tested whether the training window's *size*
itself was the real constraint, despite the paragraph above naming dataset size as the
likely cause. Prompted directly by the user questioning whether this project was
"using the full potential" of free `nflverse` data (whose R packages advertise
coverage back to 1999). Tested with data already cached (`schedules_2015_2024.parquet`
/`pbp_2015_2024.parquet`) — no new pull. Same fixed holdout as #1-#9
(`calib_seasons=[2022]`, `test_seasons=[2023, 2024]`), same `COMBINED_QB_FEATURE_COLUMNS`,
3 window configs with Elo/QB Elo **recomputed from scratch per window** (ratings
restart at 1500 from that window's own start season -- a faithful "what if we'd only
ever had N years" simulation, not a row-count truncation of features fit on the full
history). Test set (570 games) verified byte-identical across all 3 configs.

| Window | Train seasons | Games | Test Brier | Δ vs 7yr full | p-value |
|---|---|---|---|---|---|
| 3yr_recent | 2019-2021 | 788 | 0.2265 | +0.0095 worse | **0.998** |
| 5yr_mid | 2017-2021 | 1285 | 0.2173 | +0.0003 worse | 0.63 (noise) |
| 7yr_full (baseline) | 2015-2021 | 1743 | 0.2170 | -- | -- |

**Result: real, and it complicates the "dataset size" framing above rather than
simply confirming it.** Cutting to 3 recent seasons is a genuine, robust degradation
(p=0.998 -- essentially the extreme tail of the permutation null, not noise) -- more
history clearly does help down to a point. But 5 seasons is statistically
indistinguishable from 7 (p=0.63) -- the marginal 2015-2016 seasons add nothing
detectable. So "dataset size" isn't simply linear-more-is-better within the cached
range; there's a real floor around 3 years and a plateau by ~5. That plateau is itself
evidence *against* one version of the "just needs more data" hypothesis for the 6
failed feature attempts above -- if those features' true signal were being masked by
insufficient sample size, adding 2015-2016 back in (going from 5yr to 7yr) should have
moved something, and it didn't. This does not test whether pre-2015 data (1999+) would
help -- that's a separate, larger pull, out of scope here; this experiment could only
test cutting the existing window down, not extending further back.

**Sample size.** The live 2026 CLV result (§5.3) is a single season's worth of bets
against a fixed $100 bankroll — the paper's own framing throughout (§4.6, §5.5) is that
this demonstrates correct method, not a claim about long-run profitability at any
meaningful sample size.

**Market-baseline source, checked directly rather than assumed (2026-08-22).** Every
comparison above scored `market_baseline` from nflverse's own `home_moneyline`
column, which this paper's own §3.x already flags as "not confirmed to be Pinnacle."
Pulled real, confirmed-Pinnacle closing-line moneyline odds for all 570 2023-2024
test-set games (`src/collect/mainline_historical.py`) and re-scored the baseline
directly. Result: `market_baseline_real_pinnacle` Brier = 0.209724 vs.
`market_baseline_nflverse` = 0.209862 -- a 0.000138 difference, dwarfed by the
0.007-0.022 gap between either market baseline and every model tested. Correlation
between the two sources across all 570 games: 0.9976. **The unconfirmed-source
concern was legitimate to raise, and worth actually checking rather than assuming
away -- but once measured, it changes no conclusion this project has drawn.** Full
detail: `methodology_backlog.md` #8.

**Single-book anchor risk.** The entire live CLV thesis and the props/correlated-props
theoretical-edge work are anchored to Pinnacle as the sharp reference price. If
Pinnacle's own pricing drifts, gets less sharp in a specific market, or stops covering
a market this project relies on (already a live, unresolved question for player props
per §3.6), every downstream "beats the close" or "clears vig" number inherits that risk
silently — there's no second sharp book cross-checked against it.

**Data provider gaps.** §3.3 documents known collection gaps (the 2026-08-14 to
2026-08-17 pre-service window) and §3.6/§3.10 document the props-coverage uncertainty.
Not repeated here in full — see those sections for specifics.

---

## 7. Conclusion

*What this project demonstrates about methodology, rigor, and the honest limits of a 5-month single-season study. Restate that profit was never the target metric.*

---

## Appendix A. Repo structure and reproducibility

*Link to repo tree, CI setup, how to reproduce results locally.*

Interactive analysis (raw snapshot inspection, the preseason CLV report, line-movement
charts, and the historical model/calibration pipeline) is runnable directly via
`notebooks/preseason_dry_run.ipynb` — see the repo README for kernel setup.

## Appendix B. Full devig derivations

## Appendix C. Glossary
*CLV, vig, overround, Kelly fraction, Brier score, etc. — write for a recruiter audience, not just quants.*

## References
*[Miller & Davidow, Wong, Shin, Kelly, Pinnacle/Unabated resources, nflverse docs, etc. — add as cited.]*
