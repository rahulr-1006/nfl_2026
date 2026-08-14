# NFL CLV Case Study: Blueprint

**Version:** 0.1 (pre-season build)
**Owner:** Rahul Ramakrishnan
**Thesis in one line:** In a near-efficient market, edge means beating the closing line, not making money. This project measures and documents that, with honest math.

---

## Part A. Thesis and success criteria

### The claim
The NFL closing line is one of the most efficient prices in sports. The close already prices in almost all public information. So profit and loss over one season is dominated by variance, not skill. A positive P&L can be luck. A negative P&L can hide real edge.

Therefore the primary metric is **Closing Line Value (CLV)**, not P&L. CLV measures whether you got a better price than the market's final price. Positive CLV, sustained across many bets, is the accepted proxy for real edge. Sharp bettors are identified by CLV. Books limit accounts that beat the close.

### Success is defined up front, and it is falsifiable
The project succeeds if it produces all of the following, whether or not any edge is found:

1. A leakage-free, point-in-time backtester that reproduces known results.
2. A CLV log measured against Pinnacle-devigged closing probabilities, with honest confidence intervals.
3. Calibrated model probabilities, validated with reliability curves, Brier score, and log loss.
4. A drift/non-stationarity monitor that can flag when an edge decays.
5. A written paper that reports the honest finding, including a null result.

### The honest null result is a valid outcome
The most likely finding is: "I could not reliably beat the close." Framed with correct statistics, that is a stronger signal to a sharp reader than a fake P&L flex. It shows you understand where edge comes from and how to test for it.

---

## Part B. The math

This section is the core of the paper. Each formula gets its own unit test and its own paragraph in the write-up.

### B.1 Odds to implied probability
Decimal odds `d`: implied probability `q = 1 / d`.

American odds `A`:
- Favorite (A negative): `q = (-A) / ((-A) + 100)`
- Underdog (A positive): `q = 100 / (A + 100)`

American to decimal:
- Favorite: `d = 1 + 100 / (-A)`
- Underdog: `d = 1 + A / 100`

### B.2 The vig, and why devigging is the real work
For a two-way market, the raw implied probabilities sum to more than 1. The excess is the **overround** (the vig):

`overround = q_home + q_away - 1`

You cannot compare a model probability to a raw book probability. You must remove the vig first to get a "fair" probability. The method you choose changes the answer. This is where most public repos are naive, and where you show depth. Implement all four and compare them.

**Multiplicative (normalization).** Split the vig in proportion to implied probability.
`p_i = q_i / sum(q)`
Simple. Biases fair probabilities on heavy favorites and longshots (favorite-longshot bias).

**Additive (shift).** Remove an equal share of the vig from each side.
`p_i = q_i - (sum(q) - 1) / n`
Can produce negative probabilities on lopsided markets. Handle that edge case.

**Power method.** Raise each raw probability to a power `k`, solve for `k` so the fair probabilities sum to 1.
`p_i = q_i ^ (1/k)`, solve `k` such that `sum(p_i) = 1`
Reduces favorite-longshot bias better than multiplicative.

**Shin's method.** Solves for a proportion of informed money `z`, then backs out fair probabilities. It models the fact that some money is "sharp." It usually gives the best fair probabilities near the close.
`p_i = ( sqrt(z^2 + 4(1 - z) * q_i^2 / sum(q)) - z ) / ( 2(1 - z) )`, solve `z` such that `sum(p_i) = 1`

**Deliverable:** a table showing how the four methods disagree on the same market, and a short argument for which one you use for the close. Pinnacle is your anchor book, because its close is the sharpest. Devig Pinnacle to get your reference "true" probability.

### B.3 Closing Line Value
Define CLV two ways. Report both.

**Probability CLV.** How far the fair market moved toward your side after you bet.
`CLV_p = p_close_fair - p_entry_fair`
Positive means the closing fair probability for your side rose above the fair probability when you entered. You beat the close.

**Price CLV.** Whether the price you took beats the closing price for the same side.
`CLV_price = (d_entry / d_close) - 1`
Positive means your decimal odds were better than the closing decimal odds.

**Beat rate.** The fraction of bets where CLV is positive. Report beat rate and mean CLV together, with a confidence interval on the mean.

**Why CLV predicts edge.** Expected value of a bet at fair win probability `p` and decimal odds `d`:
`EV = p * (d - 1) - (1 - p)`
If your entry price is better than the fair closing probability implies, your expected CLV is positive, and long-run ROI tracks it. CLV is a leading indicator. P&L is a lagging, noisy one.

### B.4 Bet sizing
Kelly fraction for a single bet:
`f* = (b * p - q) / b`
where `b = d - 1` (net decimal odds), `p` is your win probability, `q = 1 - p`.

Use **fractional Kelly**: `f = k * f*`, with `k` in the range 0.25 to 0.5. Full Kelly is too volatile on noisy edges.

Your hard limits: bankroll 100, max bet 2.00, min bet 0.10.
- Max bet 2.00 = a **2% cap** on the bankroll. Even a large Kelly signal clips to 2%. This is already conservative sizing.
- Min bet 0.10 = a 0.1% floor.

**Frame this honestly in the paper.** A 100 bankroll cannot compound in a meaningful way. Sizing here demonstrates correct method, not bankroll growth. Say so plainly. That is the quant-credible move.

### B.5 Evaluation and, above all, sample size
This section is where you prove you are honest, not lucky.

- **Brier score:** `mean((p - y)^2)`, lower is better. Compare model to the market baseline.
- **Log loss:** `-mean(y * log(p) + (1 - y) * log(1 - p))`.
- **Reliability curve:** bin predicted probabilities, plot predicted against observed frequency. Straight diagonal means well calibrated.
- **Bootstrap confidence intervals** on mean CLV. Resample your bets, get a CI. Report it.
- **Power analysis.** State up front how many bets you need to detect a given CLV edge at a given variance. One NFL season is about 272 regular-season games plus playoffs, and you bet only a subset. Expect a few hundred bets at most. A small true edge often needs thousands of bets to confirm. So state clearly: one season likely cannot statistically confirm a small edge. The case study demonstrates the method and reports CLV with honest CIs. That framing is the sophistication that lands.

---

## Part C. Architecture

### Pipeline
```
collector  ->  point-in-time store  ->  feature builder  ->  model
                                                              |
                                                              v
   drift monitor  <-  CLV tracker  <-  backtester  <-  signal + sizing
```

### The centerpiece: a leakage-free, point-in-time store
The cardinal sin in any betting or trading backtest is lookahead bias: letting the model see data that did not exist at decision time. Your "better backtester than the books" muscle is not literally beating the books. It is building a simulator with zero leakage. Design for that first.

Rules for the store:
- **Append-only and immutable.** Every odds snapshot is written once, with its capture timestamp. Never overwrite. Never update in place.
- **Every row is timestamped** with the moment you captured it, not the game time.
- **The backtester can only read rows with `capture_time <= decision_time`.** Enforce this in code, and add a test that fails if any query violates it.
- **Realistic execution.** Model the vig, the price actually available at your decision time, book limits, and the fact that you cannot fill at a stale price.

### Suggested repo tree
```
nfl-clv/
  data/
    static/            # free historical CSVs (spreadspoke, nflverse)
    snapshots/         # append-only intraday captures (parquet, partitioned by date)
  src/
    collect/           # live odds collector + scheduler
    store/             # point-in-time store read/write + leakage guards
    devig/             # the four devig methods + tests
    features/          # feature builder from snapshots + play-by-play
    model/             # baseline (market) + your model + calibration
    signal/            # edge flag + Kelly sizing under the 2% cap
    backtest/          # leakage-free simulator
    clv/               # CLV tracker + bootstrap CIs
    drift/             # non-stationarity monitor
  tests/               # unit + property tests (leakage, devig sums to 1, etc.)
  paper/               # the case study, written as you build
  .github/workflows/   # CI (run locally with act)
  Makefile
  README.md
```

---

## Part D. Data strategy

### Free static data, for backtester and baselines (cost: 0)
- **Spreadspoke / Kaggle "NFL scores and betting data":** 60 years of scores, spreads, totals, updated weekly in season.
- **nflverse (nflreadpy):** play-by-play back to 1999, schedules, and Vegas lines. Great for features (EPA and similar), settlement, and baseline calibration.

These give opening and closing lines and rich features at no cost. They do **not** give intraday snapshots.

### Live intraday data, self-collected (the thing you cannot buy cheap)
Intraday history is expensive and rare. So collect it yourself, starting now, through the season. Get Pinnacle if possible, since it is the sharp anchor for devig and CLV.
- Verify a free tier that includes Pinnacle before you trust it. Candidates to test: OddsPapi free tier and SportsGameOdds free tier both claim Pinnacle access.
- The Odds API free tier is too thin for live collection (25 requests per day, no NFL, no Pinnacle).
- Insurance buy, one month only if free tiers disappoint: The Odds API Business plan (adds Pinnacle, historical at no extra credit).

### Smart polling to stretch request budgets
Do not poll every 30 minutes, 24 hours a day. NFL games cluster on Thursday, Sunday, Monday. Poll densely (every 30 minutes) in the 48 hours before each slate. Poll sparsely (hourly or less) midweek. This cuts your request count by more than half and keeps you inside a free tier.

Legitimate free tiers are fine to use. Do not create multiple accounts on one provider to dodge a limit. That breaks their terms and can void the dataset your paper depends on.

---

## Part E. Modeling approach

### The baseline is the market
Your baseline is the devigged Pinnacle probability. Every model is measured against "just trust the sharp close." Most fancy outcome models fail to beat this, because the market already is the model. Set this baseline first, so you never fool yourself.

### A simple, honest first model
The model's job is not to "pick winners." It is to find spots where its fair probability diverges from the market in a way that predicts positive CLV. Start simple:
- A logistic model or a gradient-boosted model on a modest feature set (team strength proxies, line movement, opener versus current, cross-book dispersion).
- A **calibration layer** on top (Platt scaling or isotonic regression). Calibrated probabilities matter more than raw accuracy here.

### The genuinely hard part: non-stationarity
This is the real ML depth, and it is the part worth flexing. Books patch inefficiencies. Your edge decays. The interesting question is: how do you know your edge died before your bankroll tells you?
- Track **rolling CLV** over a moving window.
- Run **change-point detection** (for example CUSUM) on your CLV time series to flag a regime shift.
- Flag when calibration drifts.

A working drift monitor, even a simple one, is a better interview story than any outcome model.

---

## Part F. The 16-day build plan

Realistic for evenings and weekends, minus travel. Milestone-based, not hour-rigid. The one non-negotiable: get the live collector running before Week 1 kickoff, because you cannot backfill intraday data later.

**Days 1 to 2. Scaffold and data.**
Repo tree, environment, Makefile. Load the free static datasets. Register for the free odds tiers and confirm whether you can actually see Pinnacle. Draft the snapshot schema.

**Days 3 to 5. Live collector (top priority).**
Build the collector and scheduler. Get it writing timestamped snapshots to the append-only store, on the smart-polling cadence. Start it now so pre-season data begins to flow.

**Days 6 to 8. Store and devig.**
Point-in-time store with the leakage guard and its failing-on-violation test. Settlement join against nflverse results. The four devig methods, each with a unit test that fair probabilities sum to 1.

**Days 9 to 11. Backtester and CLV.**
Leakage-free backtester on the free historical lines. Market baseline. CLV tracker with both CLV forms and the bootstrap CI.

**Days 12 to 13. Calibration and honesty.**
Brier, log loss, reliability curves. The power analysis. Write these results into the paper as you go.

**Days 14 to 15. CI and drift stub.**
Local CI with GitHub Actions run through `act`, or a Makefile plus pytest. A first drift monitor (rolling CLV plus a change-point flag). Paper skeleton with the math sections drafted.

**Day 16. Buffer.**
README, docs, a small dashboard, cleanup. Season starts. The collector runs. You iterate across the fall.

The model and the paper finish over the season, not in 16 days. The 16 days build the infrastructure and the honest harness.

---

## Part G. What "done" looks like for a recruiter

The artifact is three things:
1. **The paper.** Methodology first. CLV as the headline metric. P&L explicitly treated as noise. An honest finding, null result included.
2. **The repo.** A leakage-free backtester, real devig math with tests, and CI. This is the software-rigor signal.
3. **The live CLV log.** Real data accrued across the fall, which is what separates this from the half-finished shells on GitHub.

Bend every framing toward CLV and methodology. Never toward P&L. That is the version a sharp reader respects.
