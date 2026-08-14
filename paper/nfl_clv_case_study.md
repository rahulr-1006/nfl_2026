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
- [ ] A non-stationarity / drift monitor for edge decay (`src/drift/`, not yet built)
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

### 3.2 Live snapshot collection
**Provider:** The Odds API, `regions=eu` (Pinnacle is listed under EU bookmakers, not
`us`/`us2` — confirmed live against the free-tier key: `regions=eu` alone returns
Pinnacle without paying for the `us` region's extra credit cost).

**Polling cadence is budget-adaptive, not fixed.** `decide_poll()`
(`src/collect/budget.py`) picks `max(game_interval, budget_interval, floor)`:
- `game_interval`: 30 min within 48h of a kickoff, else 60 min.
- `budget_interval`: remaining credits spread evenly across the remaining days in the
  billing period, so the free tier's 500 credits/month can't be exhausted in week one.
- a 15-minute floor regardless.

On the free tier alone, `budget_interval` (~4.5 hours, since `(500-20)/3` polls have to
stretch across a 30-day period at 3 credits/poll for `regions=eu` × 3 markets)
dominates the max() in every scenario tested, including the most favorable one (full
budget, a kickoff 5 hours out). So in practice the free tier produces a **flat ~4.5-hour
cadence around the clock**, not the dense-near-kickoff behavior the cadence rule targets
— that only becomes the binding constraint once the budget ceiling is high enough for
`budget_interval` to drop below 30-60 minutes. One poll captures the entire league's
slate simultaneously (verified live: 272/272 scheduled games matched in one call), so
"every 4.5 hours" still means every game gets a synchronized fresh snapshot, not just
whichever is closest to kickoff.

**Provenance:** every `OddsSnapshot` row carries `book`, `capture_time` (the real
wall-clock moment the API response was received, never backfilled or estimated from
game time), and `event_id` matching nflverse's `game_id` convention.

### 3.3 Known data limitations
*State plainly: intraday history only exists from the day collection started. No backfill. Note any gaps, provider outages, or schema changes encountered.*

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
*Not yet built. Baseline = devigged Pinnacle close (§4.2/§4.3, already implemented and
usable as-is). Model architecture (logistic / GBM), feature set, and calibration layer
are blocked on pulling and caching nflverse play-by-play data.*

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
*Rolling CLV window, CUSUM change-point detection, calibration drift monitoring.*

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

## Appendix B. Full devig derivations

## Appendix C. Glossary
*CLV, vig, overround, Kelly fraction, Brier score, etc. — write for a recruiter audience, not just quants.*

## References
*[Miller & Davidow, Wong, Shin, Kelly, Pinnacle/Unabated resources, nflverse docs, etc. — add as cited.]*
