# Train re-run for the Weeks 10–14 pre-registration — 2026-10-17

Reproduce: `.venv/bin/python -m scripts.train_wk10_14` (schedule and player_stats
re-pulled 2026-10-17, backups `*.bak-20261017`).

## The split

| Role | Data | Used for |
|---|---|---|
| Fit / calibrate | 2023–24 history (570 games of odds, 285 games of props) | calibration gates (`train_results_2026-10-04.md` §1–2), lift fits, and the realized-ROI check below |
| Train | 2026 Weeks 1–5 live (closed games) | this document |
| Test | 2026 Weeks 10–14 | a pre-registration committed **before Thu 2026-11-12** |
| Untouched | 2025 season | never read here |

**Sealed until 2026-11-10:** every player-prop leg in Weeks 5–9, which is the
H1/H1b holdout. The script drops them **before pricing**, 74 alert legs today, so
no closing-EV number was ever computed from them. Prop results below are Weeks 1–4
only. Mainline strategies are outside that holdout and use every week.

Yardstick as in the Weeks 5–9 prereg §3: closing EV = p_close_fair × price − 1
against Pinnacle's close, game-clustered 95% CI, bad quotes (entry EV >15%) and
rushing yards excluded, random-side null on realized results, survival at first
re-check ≤40 min.

## Results

### moneyline_ev: the only unsealed candidate with a positive CI

| Slice | n | Games | Closing EV [CI] | Realized ROI |
|---|---|---|---|---|
| all, Weeks 1–5 | 101 | 43 | +3.64% [+0.57, +6.30] | +22.9% |
| **longshot >3.0 (gate passed)**, Weeks 1–4 | 55 | 21 | +5.76% [+3.01, +8.46] | +22.5% |
| longshot >3.0, **Week 5 (new)** | 13 | 4 | +2.82% [−2.20, +8.88] | +68.5% |
| longshot >3.0, Weeks 1–5 | 68 | 25 | **+5.20% [+2.67, +7.63]** | +31.3% (null p .055) |
| short dog 2.0–3.0 (**gate FAIL**) | 26 | 15 | +0.17% [−7.10, +7.68] | not a valid yardstick |
| favourite <2.0 | 7 | 5 | +1.36% | too few |

- The new week has the same sign but is smaller, and on 4 games it can't confirm anything.
- **History disagrees on realized results, without being able to decide.** The
  same rule (execution book ≥2% EV vs Pinnacle's Shin fair, best book per
  game-side) on 2023–24's ~20-min-pre-kickoff snapshot gives **81 longshot bets:
  realized −21.6% [−59.5, +20.8]**. They won 16.0% against a 21.7% fair
  probability (expected 17.6 wins, got 13, z ≈ −1.2). That snapshot is
  effectively the close, so these are bets that beat Pinnacle's close by
  +5.75% and still lost money. The CI is ±40pp, so this isn't a refutation.
  It is the honest reason not to read the live +5.2% as money.
- `decision-report` says NO for moneyline_ev because it scores `clv_probability`
  (did Pinnacle move toward the bet). This document uses closing EV (did the
  price beat Pinnacle's close). Both can be true: the soft book was mispriced,
  and Pinnacle didn't move.
- Volume: Weeks 1–4 averaged ~14 longshot bets/week over ~5 games. Week 5 had 13
  over 4 games. Five weeks would land near prereg §3's condition 1 (≥30 bets,
  ≥15 games) but might not clear it.

### H2 mechanism (team totals) replicates a third time; the contract is still missing

Underdog lift = P(wins AND team clears its summed Pinnacle prop line) /
(P(wins) × P(clears)), game-resampled CI:

| Stat | 2023 (fit) | 2024 (test) | **2026 Weeks 1–4** (n=55) |
|---|---|---|---|
| passing_yards | 1.311 | 1.216 | **1.337 [1.034, 1.724]** |
| rushing_yards | 1.226 | 1.167 | 1.175 [0.939, 1.432] |

The passing CI excludes 1 in a third independent sample. **The mechanism is
real; the problem is that nothing quotes it.** There is no team-total-yards
market, and the 10-04 QB-over proxy was scoreable on only 16 of 53 spots (−5.6%).
H2 can't be registered until its contract is chosen (prereg §4 options a/b/c).

### Dead or not viable

- **steam:** closing EV −3.66% [−6.54, −0.40] over 55 bets / 26 games, negative
  in both periods and in both markets. Realized −33.7%. **Kill.**
- **middle:** 7 legs / 3 games. 0 of 3 settled pairs hit the middle. Nothing to
  register.
- **prop_arb:** Weeks 1–4, 22 alerts: both legs still placeable 41%, **one leg
  only 55%**. More than half the alerts would leave you holding one side unhedged.
  Not a strategy for real money.
- **prop_ev** (Weeks 1–4): closing EV +2.86% [+1.63, +4.10], but it fails the
  random-side null (p .63; realized −2.1% on 134). It overlaps H1b, so the
  11-10 holdout score is its real test.

## What this means for the Weeks 10–14 pre-registration

1. **moneyline_ev longshots (>3.0)** is the one unsealed candidate. Register it
   only with the history result written in, and with condition 1 checked against
   the measured volume (about 5 weeks × ~13 bets).
2. **H2** needs its contract decided before anything else. The mechanism no
   longer needs re-proving.
3. **H1/H1b** carry over only if they pass on 11-10. That decision falls between
   11-10 and 11-12, so write both branches into the doc in advance.
4. Drop steam, middle and prop_arb from any confirmatory family. Each one costs
   a BH slot for nothing.

## Addendum 2026-10-19: from when the signal fires to the close, Weeks 1–6

The same script re-run with Week 6 played (the Monday-night game wasn't closed yet,
and Week 6 Sunday results weren't in the schedule pull, so realized results lag).
No sealed numbers: props are Weeks 1–4 only. Each signal's closing EV is split
into **edge when it fired** (entry EV against Pinnacle's fair then) plus
**Pinnacle's move to the close** (`(p_close − p_entry) × price`). "Beat book
close" means the bet's own book later offered a worse price.

| Strategy | n / games | Edge at fire | Pinnacle move | Close EV [CI] | Beat book close |
|---|---|---|---|---|---|
| moneyline_ev >3.0 (H5) | 83 / 31 | +3.59% | **+1.22%** | **+4.81% [+2.5, +7.1]** | 76% |
| moneyline_ev ≤3.0 | 37 / 23 | +3.71% | −2.45% | +1.26% [−4.3, +7.1] | 65% |
| steam | 73 / 33 | −0.69% | −2.70% | −3.39% [−5.8, −0.9] | 38% |
| prop_ev (Weeks 1–4) | 136 / 50 | +5.28% | −2.45% | +2.84% [+1.6, +4.1] | 73% |

- **H5 is an early-opener effect.** 73 of 83 alerts fired more than 3 days before
  kickoff: +5.34% [+2.8, +7.9]. The soft books open longshots too long, Pinnacle
  drifts toward them, and the books cut their price. Across books the closing EV
  ranged from +2.4% (BetMGM, William Hill) to +6.3% (BetRivers). Every bucket
  closer to kickoff has n ≤ 6. **The rule stays as written.** Restricting it
  to >3 days out would be fitting on Train for no gain, since the big bucket is
  already almost all of it.
- **Steam pays for the move.** Signals 1–6 hours out lost 12pp to Pinnacle
  reversing (−10.1% close EV). It confirms the kill.
- **prop_ev's edge at fire is partly a stale Pinnacle.** Signals more than 6
  hours out lose ~4.3pp to Pinnacle's move. Within 6 hours of kickoff they hold
  (+4.3%, n=51). That's Weeks 1–4 only. H1b's 11-10 holdout is the real test.
- Practical for H5: alerts land mid-week, days before the game. You have time
  to place them by hand, and the 64% survival at first re-check is the binding
  constraint, not reaction speed.
