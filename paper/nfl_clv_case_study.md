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
close.

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
*Sample size, single-season scope, data provider gaps, single-book anchor risk.*

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
