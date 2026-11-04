# nfl-clv

A research system that tests whether NFL betting edges are real, measured by
**closing line value (CLV)** rather than profit and loss.

The NFL closing line is one of the most efficient prices in sports, so a season of
P&L is mostly variance: a winning record can be luck, and a losing one can hide real
edge. The accepted test is whether you beat the closing price. This repo collects
point-in-time odds from five US sportsbooks and Pinnacle (the sharp reference book),
removes the vig from Pinnacle's prices to get fair probabilities, backtests
strategies without look-ahead, texts live opportunities, and scores every alert
against the close. Hypotheses are pre-registered before they are scored, and the
null results stay in the record.

**Status (2026-11-03):** three services have run 24/7 since August and have sent 900+
alerts across Weeks 1–9 of the 2026 season. Pinnacle's line moves *against* most alerts,
but prop alerts are still priced better than its close. Whether that holds on unseen
weeks is decided on 2026-11-10, when the first pre-registered holdout is scored.

---

## Timeline

### Aug 14–23 · Build the harness before the season starts
The one thing that can't be backfilled is intraday odds, so the collector went live
on day one and the rest was built around it:

- **Point-in-time store**: append-only and immutable. Every read goes through a guard
  that returns only rows captured before the decision time, and a test fails if any
  query sees the future.
- **Devigging**: four methods for removing the vig (multiplicative, additive, power, Shin).
- **Backtester and CLV tracker**: price and probability CLV with bootstrap
  confidence intervals, settled against nflverse results.
- **Calibration and drift**: reliability curves, Brier and log loss, plus a CUSUM drift
  monitor for edge decay.
- **Ops**: launchd services, a cost-aware polling scheduler for the paid odds API, and
  SMS alerts. Alerts only; bets are always placed by hand.

### Aug 17–23 · Pre-season research: what can beat the market?
About ten candidate strategies, each tested out of sample with multiple-comparison
correction. Most failed, and the failures produced the project's main design rule:

| Result | Finding |
|---|---|
| ✅ Survives | **Team Elo** beats an EPA-only win-probability model and closes ~57% of the gap to the market. It is the only model comparison that survives Benjamini–Hochberg correction. |
| ✅ Survives | **Cross-book prop arbitrage**: 65 real spots across 5 books in 2024, present in 14–15 of 15 weeks, traced to systematic vig skew. |
| ✅ Survives | **Team-total props**: an underdog-bucket edge that survives a chi-square test, a permutation test and an out-of-sample split (passing +7.1% realized). |
| ❌ Null | **Prop EV vs. Pinnacle**: no detectable edge on 6,812 real 2024 bets (49.85% win rate). |
| ❌ Null | **Feature engineering**: 7 consecutive attempts to improve the moneyline model failed, including garbage-time filtering, weather, rest/travel and game-level player Elo. QB Elo improves Brier but doesn't survive correction. |
| ❌ Null | **Devig method choice**: no method beats another on 2,733 games, so Shin stays the default on theory. |

**Design rule:** Pinnacle's prop vig is 6.29%, and the best price across five books
still has a median EV of −4.74%. Strategies that try to *out-predict* Pinnacle need
more than 4.7% of edge just to break even, and none here found it. Strategies that
exploit *structure* (two books disagreeing, correlated legs priced as independent, a
line moving) don't need a probability edge at all. Every result so far fits this
split. → [`docs/architecture.md`](docs/architecture.md) §7

### Sep · The season goes live
The monitor texts moneyline EV, prop arbitrage, prop EV, middles and steam moves.
Every alert is logged as a notional bet at its quoted price, so each one gets a CLV
score once its game closes. No bankroll is needed to measure that.

The first real close of the season (NE @ SEA) surfaced three CLV bugs that 936 passing
tests could not reach. Nothing had closed yet, so every code path after "has this game
kicked off?" was untested by construction, even though coverage looked complete. Test
fixtures now include a game that has already kicked off. Other live-path bugs caught
before any money depended on them:
- A swallowed `KeyError` dropped every moneyline row from the alert log.
- A stale-leg bug made all 7 early "live middles" artifacts.
- Historical backfill shared the live store, so a pre-season dry run fired 874 of 879
  alerts on games that had already been played.

A go/no-go table was fixed on 2026-09-14, before the data it would judge existed
(`make decision-report`). `moneyline_ev` cleared it at n≈30 with a 61% beat rate,
then fell to 50% as n doubled, so the answer was no bets.

### Oct · Pre-registration
With nothing clearing the bar, new hypotheses are tested the strict way: frozen in
writing first, then scored once on weeks nobody has looked at.
- **Weeks 5–9** ([prereg](docs/preregistration_wk5-9.md)): H1/H1b, two tests of soft
  books lagging Pinnacle's prop moves. The pass bar, parameters and scorer were frozen
  first. The scorer refuses to run before the scoring date, and these alerts log to a
  separate file that no report reads. The document was committed 6 days late; the
  deviation is disclosed in it, along with what that weakens.
- **Weeks 10–14** ([draft](docs/preregistration_wk10-14.md)): H5, moneyline longshots.
  Its alerts are sealed out of every CLV report until 2026-12-15.

### Nov–Dec · Scoring
- **2026-11-10**: score H1/H1b on the Weeks 5–9 holdout (`make prereg-score WEEKS=holdout`).
- **2026-12-15**: the seal lifts, and H5 is scored.
- Only a hypothesis that passes its holdout gets real money: a $100 bankroll, $2 max bet.

---

## Live results so far (alerts as bets)

Each alert is a $1 bet at the first price it was texted at, scored against Pinnacle's
devigged close. **Closing EV** (`p_close × price − 1`) is the expected profit if the close
is the true probability. The full analysis, with game-clustered CIs, the luck
decomposition, calibration and power, is in
[`notebooks/alert_clv_analysis.ipynb`](notebooks/alert_clv_analysis.ipynb).

| Strategy | Weeks | Bets | Closing EV [95% CI] | Line moved our way |
|---|---|---:|---|---:|
| prop EV | 1–4\* | 137 | **+2.9%** [+1.6, +4.1] | 27% |
| prop arbitrage | 1–4\* | 65 | **+1.2%** [+0.8, +1.6] | — (legs cancel) |
| moneyline EV | 1–9 | 121 | +1.9% [−1.2, +4.8] | 36% |
| steam | 1–9 | 93 | **−3.4%** [−5.8, −0.9] | 37% |
| middles | 3–8 | 15 | +3.2% [−0.9, +6.7], 5 games | 67% |

\* Weeks 5–9 props are sealed until the H1/H1b holdout is scored on 11-10. Bets where
Pinnacle's close failed its calibration gate (rushing-yards props, moneyline short
underdogs) and bad quotes are excluded.

- **The two yardsticks disagree, and that's the finding.** Pinnacle's line moved away
  from most alerts, but prop alerts start about 5% ahead of its fair price and keep
  roughly half of that through the close. These are the same Weeks 1–4 that shaped the H1
  hypothesis, so they aren't independent confirmation; the sealed weeks are.
- **Steam is reliably negative.** It fires with no edge and loses 3.5% to the market.
- **P&L is noise.** At the stakes the texts suggested (0.375× Kelly on a $100 bankroll,
  $2 cap), the 426 settled bets are −$16.59 on $517 staked, against +$6.14 expected from the
  close. A flat $1 per alert would show +$19.44 instead. Both are inside the luck band.
  Detecting a +2% edge takes 3–37 weeks of alerts on closing EV, depending on the strategy,
  and more than 50 seasons on P&L.

---

## How it fits together

```
COLLECT ──► STORE ──────────► SIGNAL ──► NOTIFY
(Odds API)  (point-in-time)   (scanners)  (SMS)
               │
               ├──► BACKTEST (engine, strategies, validation, evaluation)
               │
FEATURES ──► MODEL (Elo, EPA, calibration)
(nflverse)
```

| Path | What's there |
|---|---|
| `src/store/` | Point-in-time store and leakage guard, settlement for games and player props, bet log |
| `src/devig/` | Odds conversion and the four devig methods |
| `src/clv/` | CLV metrics, CLV over alerts, decision report, date-locked pre-registration scorers, holdout seals |
| `src/backtest/` | Backtest engine and strategy modules (arbitrage, middling, steam, correlated props, team totals), plus the validation toolkit: season splits, walk-forward folds, permutation tests, BH-FDR, game-clustered bootstrap |
| `src/model/` | Elo family, EPA features, calibration, margin and total regressions |
| `src/collect/`, `src/signal/`, `src/notify/` | Live collection, scanners, alerting |
| `ops/` | launchd service definitions |
| `docs/` | [Architecture map](docs/architecture.md), [original blueprint](docs/nfl_clv_case_study_blueprint.md), [case study draft](docs/nfl_clv_case_study.md), pre-registrations, train-split results |
| `notebooks/` | Live alert CLV and P&L analysis, model and backtest results, CLV-tracker validation on a synthetic market |

About 14k lines of Python, plus 1,027 tests.

---

## Running it

```bash
make install        # .venv + editable install with dev extras
make data           # pull nflverse data into data/static/ (re-run weekly in season)
make test           # 1,027 tests; 6 real-data checks skip until `make data` has run
make demo           # end-to-end pipeline on synthetic odds, no API key needed
```

Live collection needs an [Odds API](https://the-odds-api.com) key in `.env`:
`ODDS_API_KEY`, plus `ODDS_API_KEY_PAID` for the props and historical pulls.
`ALERT_PHONE_NUMBER` enables SMS through Messages.app on macOS. The services install
with `make collector-service-install`, `make monitor-service-install` and
`make props-service-install`. The plists in `ops/` hold absolute paths, so edit them
for your machine first.
