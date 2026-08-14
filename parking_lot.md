# Parking lot

Ideas that are real but out of scope for the current build phase. Revisit between
milestones, not mid-build — see the 16-day plan in `nfl_clv_case_study_blueprint.md`.

---

## Promotional EV (bonus bets, odds boosts, deposit matches)

**The tension:** promos are a genuine, well-known edge source that algorithmic
bettors exploit — often larger and far more certain than any CLV/model edge on small
stakes. In that sense they're "part of the market" a serious bettor would account for.
But they don't fit the project's core thesis cleanly:

- **CLV measures a persistent, repeatable signal** (bootstrap CIs, power analysis, the
  whole apparatus assumes you can keep re-sampling the same edge across hundreds of
  bets). A promo is a one-time capital event per sportsbook account — it doesn't
  recur, so it can't be measured or reported the same way.
- **The backtest engine's leakage guard assumes your entry price exists in observed
  market data** (`PointInTimeStore.read_as_of`). A personalized odds boost or bonus
  price was never a real market quote, so it can't be looked up the same way without
  bypassing the exact guard the engine exists to enforce.
- **Mixing it into the CLV log would undermine the paper's own honesty framing.**
  `paper/nfl_clv_case_study.md` §3.4 already commits to excluding bonus/promo bets from
  headline CLV, because bonus credit distorts the price actually being risked.

**Where this leaves the thesis:** unresolved on purpose. "Beating the close" and
"harvesting promotional EV" are two different, both-legitimate ways an algorithmic
bettor gets an edge, and the paper is currently scoped to only the first one. Worth
deciding later whether the paper:
(a) stays scoped to CLV only and treats promo EV as explicitly out of scope (cleanest,
    keeps the "honest math" story tight), or
(b) adds a clearly-separated section/appendix reporting promo EV as its own ledger,
    never blended into the CLV numbers.

**If ever built:** not as a `Strategy` inside `src/backtest/engine.py`. A separate,
much simpler ledger — promo type (free bet / odds boost / deposit match / risk-free),
terms (rollover requirement, odds minimum, expiration, max value), and EV computed
directly (ideally under a matched-betting hedge if exchange access exists). Plain
arithmetic, not a market simulation.
