"""Synthetic market simulator -- validates this project's OWN CLV-measurement
code (`src/clv/metrics.py`) against known ground truth, since the real live
CLV result only has data since the collector started (2026-08-14), far too
thin a sample to trust on its own.

**What this is NOT:** a claim about real NFL betting edge. It's a software
correctness check -- generate synthetic intraday price paths with a KNOWN
data-generating process, run them through the REAL `PointInTimeStore` ->
CLV-computation pipeline, and confirm the pipeline recovers the known ground
truth. If it doesn't, that's a real bug in the plumbing (store read/write,
devig, CLV math), not a finding about markets.

**Design: a biased random walk in logit space, with a realistic "market
under-reacts initially" mechanism.** For each simulated game:
1. Draw a *true* fair home-win probability `p_true` -- what an omniscient
   observer would believe right before kickoff.
2. The *initial* market probability `p_open` is `p_true` shrunk toward 0.5
   (`initial_shrinkage < 1`) -- a real, common market behavior: early lines
   are less extreme than the fully-informed probability, since the market
   hasn't finished processing information yet.
3. The price path from open to close is a random walk in logit space, drifting
   from `p_open`'s logit toward `p_true`'s logit at a rate set by
   `drift_strength` (0 = no informed drift at all, i.e. pure noise; 1 = fully
   converges to `p_true` by kickoff), plus i.i.d. Gaussian noise at each step
   (a real random walk, not a deterministic path).

**Why this gives a checkable prediction, not just "plausible-looking" data:**
a bettor who always bets whichever side `p_open` already favors (a
pre-registered rule, not hindsight) should show a beat rate near 50% when
`drift_strength=0` (no systematic price movement, pure noise) and a beat rate
meaningfully above 50% when `drift_strength>0` (the market's own early lean
gets confirmed on average as it converges toward `p_true`) -- exactly the
"early informed movement" mechanism the CLV thesis assumes exists. This is
the actual validation target, not just "does the code run."

**Multiple books, real vig, optional jumps:** each book quotes its own noisy
version of the same latent fair probability, with vig added back via the
same multiplicative convention `src/backtest/correlated_props.py::naive_parlay_price`
already uses (reusing this project's existing vig-simulation pattern, not a
new one). An optional Poisson jump component layers discrete price shocks on
top of the random walk, for later reuse validating `steam.py`'s detection
logic -- not required for the CLV validation itself, but the same generator
serves both.

**Spread/total markets:** generated the same way, with their OWN independently
drawn `p_true` (cover probability / over probability) -- a real, stated v1
simplification: no cross-market correlation is modeled (a real spread move and
a real total move on the same game usually aren't independent), same "state
the simplification plainly" discipline as every other v1 pricing model in this
project.

**Player props (2026-08-23):** `n_prop_players` synthetic players per game,
each with their own independent price path and their own Over/Under line, so
a game carries many simultaneous prop contracts -- the exact structure that
makes contract-level price selection necessary in
`src/backtest/engine.py::_market_rows`. This is what lets the props CLV path
be validated against known ground truth BEFORE the season, which matters
because props CLV is still not backtested historically: every historical PROP
pull is a single near-kickoff snapshot, and buying a prop series costs ~700
credits/game. **That is cost, not impossibility** -- mainline 2024 now has a
real 6-point series across 105 games, so the barrier was always the price. Synthetic validation is not a nice-to-have
here, it is the only pre-season check that exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np

from src.devig.convert import implied_prob_to_american
from src.store.schema import Market, OddsSnapshot, Side

DEFAULT_INITIAL_SHRINKAGE = 0.4  # how much less confident the open line is vs. the eventual p_true
DEFAULT_VIG = 0.0297  # mainline vig, measured this project (devig_method_comparison memory) -- not props' 5.75%
DEFAULT_BOOK_NOISE_SCALE = 0.05  # independent per-book noise around the shared latent fair probability (logit space)


def _logit(p: np.ndarray | float) -> np.ndarray | float:
    return np.log(p / (1 - p))


def _sigmoid(x: np.ndarray | float) -> np.ndarray | float:
    return 1 / (1 + np.exp(-x))


def simulate_true_probability_path(
    p_true: float,
    n_steps: int,
    drift_strength: float,
    noise_scale: float,
    initial_shrinkage: float = DEFAULT_INITIAL_SHRINKAGE,
    jump_rate: float = 0.0,
    jump_scale: float = 0.0,
    random_state: int | np.random.Generator | None = None,
) -> np.ndarray:
    """One simulated game's latent fair-probability path, length `n_steps + 1`
    (index 0 = open, index -1 = close). See module docstring for the full
    design -- this is the core generator everything else in this module calls.

    `drift_strength`: 0.0 = the deterministic component never moves off the
    (shrunk) opening logit -- pure random walk, no informed drift. 1.0 = the
    deterministic component reaches exactly `logit(p_true)` by the last step.
    Values outside [0, 1] are allowed (e.g. >1 to overshoot) but not the
    intended validation range.

    `jump_rate`/`jump_scale`: optional Poisson-arrival jumps in logit space,
    on top of the base Gaussian random walk -- for later reuse validating
    `steam.py`, not needed for the core CLV validation (defaults to off).
    """
    if not 0 < p_true < 1:
        raise ValueError(f"p_true must be in (0, 1), got {p_true}")
    if n_steps < 1:
        raise ValueError(f"n_steps must be >= 1, got {n_steps}")

    rng = random_state if isinstance(random_state, np.random.Generator) else np.random.default_rng(random_state)

    target_logit = _logit(p_true)
    initial_logit = initial_shrinkage * target_logit

    steps = np.arange(n_steps + 1)
    drift_component = initial_logit + drift_strength * (steps / n_steps) * (target_logit - initial_logit)

    noise_increments = rng.normal(0.0, noise_scale, size=n_steps + 1)
    noise_increments[0] = 0.0

    if jump_rate > 0:
        jump_occurs = rng.random(n_steps + 1) < jump_rate
        jump_occurs[0] = False
        jump_sizes = rng.normal(0.0, jump_scale, size=n_steps + 1) * jump_occurs
        noise_increments = noise_increments + jump_sizes

    noise_path = np.cumsum(noise_increments)
    logit_path = drift_component + noise_path
    return _sigmoid(logit_path)


@dataclass(frozen=True)
class SimulatedPropTruth:
    """Ground truth for one simulated player-prop contract. `over_hit` is
    the realized outcome, drawn against the closing latent probability --
    the analogue of `SimulatedGameTruth.home_win` for a prop.
    """

    player_name: str
    prop_stat: str
    line: float
    p_open_over_true: float
    p_close_over_true: float
    over_hit: bool


@dataclass(frozen=True)
class SimulatedGameTruth:
    """Ground truth for one simulated game -- what `simulate_market` actually
    generated, kept separate from the `OddsSnapshot`s so validation code can
    compare "what the pipeline computed" against "what we know is true"
    without re-deriving it from the snapshots themselves.
    """

    event_id: str
    home_team: str
    away_team: str
    kickoff: datetime
    # All four game-level fields are None when MONEYLINE wasn't simulated --
    # there is no meaningful home-win probability in a props-only or
    # spread/total-only run, and inventing one silently corrupts any consumer
    # that calibrates against it. Check before use.
    p_true_home: float | None
    p_open_home_true: float | None  # the latent fair probability at open, before per-book noise/vig
    p_close_home_true: float | None  # the latent fair probability at close, before per-book noise/vig
    home_win: bool | None
    props: tuple[SimulatedPropTruth, ...] = ()


def _to_snapshot(
    *,
    capture_time: datetime,
    event_id: str,
    season: int,
    week: int,
    home_team: str,
    away_team: str,
    kickoff: datetime,
    book: str,
    market: Market,
    side: Side,
    prob: float,
    line: float | None = None,
    player_name: str | None = None,
    prop_stat: str | None = None,
) -> OddsSnapshot:
    return OddsSnapshot.from_american(
        capture_time=capture_time,
        event_id=event_id,
        season=season,
        week=week,
        home_team=home_team,
        away_team=away_team,
        event_start_time=kickoff,
        book=book,
        market=market,
        side=side,
        price_american=implied_prob_to_american(prob),
        line=line,
        player_name=player_name,
        prop_stat=prop_stat,
    )


_MARKET_SIDES: dict[Market, tuple[Side, Side]] = {
    Market.MONEYLINE: (Side.HOME, Side.AWAY),
    Market.SPREAD: (Side.HOME, Side.AWAY),
    Market.TOTAL: (Side.OVER, Side.UNDER),
    Market.PLAYER_PROP: (Side.OVER, Side.UNDER),
}

DEFAULT_PROP_STAT = "receiving_yards"
DEFAULT_PROP_LINE = 45.5


def simulate_market(
    n_games: int,
    n_poll_steps: int,
    kickoff_start: datetime,
    kickoff_spacing: timedelta = timedelta(hours=3),
    poll_window: timedelta = timedelta(hours=48),
    books: tuple[str, ...] = ("pinnacle", "draftkings", "fanduel", "betmgm"),
    markets: tuple[Market, ...] = (Market.MONEYLINE,),
    n_prop_players: int = 8,
    drift_strength: float = 0.5,
    noise_scale: float = 0.03,
    initial_shrinkage: float = DEFAULT_INITIAL_SHRINKAGE,
    book_noise_scale: float = DEFAULT_BOOK_NOISE_SCALE,
    vig: float = DEFAULT_VIG,
    jump_rate: float = 0.0,
    jump_scale: float = 0.0,
    season: int = 2099,
    random_state: int | None = None,
) -> tuple[list[OddsSnapshot], list[SimulatedGameTruth]]:
    """`n_games` synthetic games, each with its own independently-drawn
    latent price path (see `simulate_true_probability_path`), quoted by every
    book in `books` for every market in `markets`, polled at `n_poll_steps + 1`
    evenly-spaced times across `poll_window` before kickoff (closing poll at
    kickoff itself).

    Returns `(snapshots, truth)` -- real `OddsSnapshot` objects ready to write
    into a real `PointInTimeStore`, plus the ground truth needed to validate
    whatever the pipeline computes against them. `event_id`s are
    `"SYNTH_{i:04d}"`, `season=2099` by default specifically so synthetic data
    can never collide with a real game_id in the same store.
    """
    rng = np.random.default_rng(random_state)
    snapshots: list[OddsSnapshot] = []
    truths: list[SimulatedGameTruth] = []

    for i in range(n_games):
        event_id = f"SYNTH_{i:04d}"
        home_team, away_team = f"HOME{i:04d}", f"AWAY{i:04d}"
        kickoff = kickoff_start + i * kickoff_spacing
        poll_times = [
            kickoff - poll_window + (poll_window * step / n_poll_steps) for step in range(n_poll_steps + 1)
        ]

        def _new_path() -> np.ndarray:
            p_true = float(rng.uniform(0.15, 0.85))
            return simulate_true_probability_path(
                p_true, n_poll_steps, drift_strength, noise_scale,
                initial_shrinkage=initial_shrinkage, jump_rate=jump_rate, jump_scale=jump_scale, random_state=rng,
            )

        # One entry per real CONTRACT, not per market: a game carries a
        # separate prop contract for every listed player, which is exactly
        # the structure engine.py's contract-level price selection exists to
        # handle. Mainline markets contribute one contract each.
        contracts: list[tuple[Market, str | None, str | None, float | None, np.ndarray]] = []
        for market in markets:
            if market == Market.PLAYER_PROP:
                for p in range(n_prop_players):
                    contracts.append(
                        (market, f"Player {i:04d}-{p:02d}", DEFAULT_PROP_STAT, DEFAULT_PROP_LINE, _new_path())
                    )
            else:
                line = None if market == Market.MONEYLINE else 0.0
                contracts.append((market, None, None, line, _new_path()))

        moneyline_path = next((path for m, _, _, _, path in contracts if m == Market.MONEYLINE), None)
        prop_truths = tuple(
            SimulatedPropTruth(
                player_name=player_name, prop_stat=prop_stat, line=line,
                p_open_over_true=float(path[0]), p_close_over_true=float(path[-1]),
                over_hit=bool(rng.random() < path[-1]),
            )
            for market, player_name, prop_stat, line, path in contracts
            if market == Market.PLAYER_PROP
        )

        # Ground truth is emitted for EVERY game, including props-only
        # simulations (this was previously gated on a moneyline path existing,
        # so simulating props alone silently returned zero truth records and
        # made the scenario unvalidatable).
        #
        # **With no moneyline market simulated, the game-level fields are None,
        # not a fabricated coin flip.** An earlier version of this fix filled
        # them with 0.5 / `rng.random() < 0.5`, which is worse than useless: a
        # consumer calibrating against `p_true_home` or `home_win` from a
        # spread/total/props-only run would get plausible-looking numbers that
        # mean nothing. None fails loudly at the point of misuse instead.
        has_moneyline = moneyline_path is not None
        truths.append(
            SimulatedGameTruth(
                event_id=event_id, home_team=home_team, away_team=away_team, kickoff=kickoff,
                p_true_home=float(moneyline_path[-1]) if has_moneyline else None,
                p_open_home_true=float(moneyline_path[0]) if has_moneyline else None,
                p_close_home_true=float(moneyline_path[-1]) if has_moneyline else None,
                home_win=bool(rng.random() < moneyline_path[-1]) if has_moneyline else None,
                props=prop_truths,
            )
        )

        for market, player_name, prop_stat, line, path in contracts:
            side_a, side_b = _MARKET_SIDES[market]
            for capture_time, p_true_side_a in zip(poll_times, path, strict=True):
                for book in books:
                    book_noise = rng.normal(0.0, book_noise_scale)
                    p_book_side_a = float(_sigmoid(_logit(p_true_side_a) + book_noise))
                    p_book_side_a = min(max(p_book_side_a, 1e-4), 1 - 1e-4)

                    q_a = min(p_book_side_a * (1 + vig), 1 - 1e-4)
                    q_b = min((1 - p_book_side_a) * (1 + vig), 1 - 1e-4)

                    for side, prob in ((side_a, q_a), (side_b, q_b)):
                        snapshots.append(
                            _to_snapshot(
                                capture_time=capture_time, event_id=event_id, season=season, week=1,
                                home_team=home_team, away_team=away_team, kickoff=kickoff, book=book,
                                market=market, side=side, prob=prob, line=line,
                                player_name=player_name, prop_stat=prop_stat,
                            )
                        )

    return snapshots, truths
