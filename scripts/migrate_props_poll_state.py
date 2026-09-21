"""One-off migration: re-index `data/props_collect_state.json` onto a changed poll grid.

**Why this is needed at all.** `EventPollState.poll_count` is an INDEX into
`props_budget.POLL_TARGETS`, not a count of hours. Changing the grid therefore
silently moves every in-flight event: on 2026-09-14 `ARB_POLL_INTERVAL_HOURS`
went 0.5 -> 0.25, which grew the schedule 55 -> 79 targets, and an event sitting
at index 44 went from meaning "next target 5.5h before kickoff" to meaning
"8.75h before kickoff".

That is not a cosmetic drift. `props_scheduler` advances at most ONE index per
tick, so a mid-flight event whose index suddenly points too far from kickoff
walks forward one tick at a time and can run out of clock before reaching the
targets that matter. Measured on the live state the day of the change: DEN@KC
sat at index 44 with 5.88h to kickoff and would have reached only the 3.0h
target, **missing the 1.5h close capture** (the only full-market capture inside
`rolling_clv_2024.CLOSE_MAX`) and every arb target below it.

**The fix is to migrate by TIME, not by index.** For each event, read the
hours-before-kickoff its old index pointed at, then find the index on the new
grid pointing at the same moment. Events already past the end of the old grid
stay finished; events still in the early tier are unaffected, because the grid
only changed below `ARB_WINDOW_HOURS` and the indices above it are identical.

Run with `--dry-run` first. Writes a timestamped backup before touching the file.

    python scripts/migrate_props_poll_state.py --dry-run
    python scripts/migrate_props_poll_state.py
"""

from __future__ import annotations

import argparse
import shutil
from datetime import UTC, datetime
from pathlib import Path

from src.collect.props_budget import (
    _ALL_PROP_MARKETS,
    ARB_COST_PER_POLL,
    ARB_MARKETS,
    ARB_WINDOW_HOURS,
    CLOSE_CAPTURE_HOURS,
    DEFAULT_COST_PER_POLL,
    POLL_TARGETS,
    EventPollState,
    PollTarget,
    PropsCollectorState,
    dense_poll_targets_hours,
    early_poll_targets_hours,
    load_state,
    save_state,
    sparse_poll_targets_hours,
)

DEFAULT_STATE_PATH = Path("data/props_collect_state.json")

# The grid as it stood BEFORE this change. Reconstructed explicitly rather than
# imported, because the module now only knows the new one -- and a migration that
# reads both sides from the same mutable constant cannot be correct.
OLD_ARB_POLL_INTERVAL_HOURS = 0.5


def _build_targets(arb_interval_hours: float) -> list[PollTarget]:
    """`props_budget.build_poll_targets` with the arb spacing made a parameter,
    so the old and new grids can be built side by side.
    """
    n_arb = max(1, round(ARB_WINDOW_HOURS / arb_interval_hours))
    targets = (
        [PollTarget(h, _ALL_PROP_MARKETS, DEFAULT_COST_PER_POLL, "early") for h in early_poll_targets_hours()]
        + [PollTarget(h, _ALL_PROP_MARKETS, DEFAULT_COST_PER_POLL, "sparse") for h in sparse_poll_targets_hours()]
        + [PollTarget(h, _ALL_PROP_MARKETS, DEFAULT_COST_PER_POLL, "dense") for h in dense_poll_targets_hours()]
        + [PollTarget(CLOSE_CAPTURE_HOURS, _ALL_PROP_MARKETS, DEFAULT_COST_PER_POLL, "close")]
        + [PollTarget(ARB_WINDOW_HOURS - i * arb_interval_hours, ARB_MARKETS, ARB_COST_PER_POLL, "arb") for i in range(n_arb)]
    )
    targets.sort(key=lambda t: -t.hours_before_kickoff)
    seen: set[float] = set()
    deduped = []
    for t in targets:
        if t.hours_before_kickoff in seen:
            continue
        seen.add(t.hours_before_kickoff)
        deduped.append(t)
    return deduped


def migrate_poll_count(old_count: int, old_targets: list[PollTarget], new_targets: list[PollTarget]) -> int:
    """Map an index on `old_targets` to the index on `new_targets` pointing at
    the same hours-before-kickoff.

    An event at or past the end of the old grid is finished and must stay
    finished -- mapping it back onto a real target would re-open a schedule that
    already ran to completion and re-poll a game that has kicked off.
    """
    if old_count >= len(old_targets):
        return len(new_targets)
    old_hours = old_targets[old_count].hours_before_kickoff
    # The next target is the first one at or below `old_hours`, so the migrated
    # index is however many new targets sit strictly above it.
    return sum(1 for t in new_targets if t.hours_before_kickoff > old_hours)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--path", type=Path, default=DEFAULT_STATE_PATH)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    old_targets = _build_targets(OLD_ARB_POLL_INTERVAL_HOURS)
    new_targets = POLL_TARGETS
    print(f"old grid: {len(old_targets)} targets   new grid: {len(new_targets)} targets")
    if len(old_targets) == len(new_targets):
        print("grids are the same size -- nothing to migrate")
        return 0

    state = load_state(args.path)
    migrated: dict[str, EventPollState] = {}
    changed = 0
    for event_id, s in state.events.items():
        new_count = migrate_poll_count(s.poll_count, old_targets, new_targets)
        if new_count != s.poll_count:
            changed += 1
            old_h = old_targets[s.poll_count].hours_before_kickoff if s.poll_count < len(old_targets) else None
            new_h = new_targets[new_count].hours_before_kickoff if new_count < len(new_targets) else None
            print(f"  {event_id}  poll_count {s.poll_count:3d} -> {new_count:3d}   next target {old_h}h -> {new_h}h")
        migrated[event_id] = EventPollState(poll_count=new_count, last_polled_at=s.last_polled_at)

    print(f"\n{changed} of {len(state.events)} events change index")
    if args.dry_run:
        print("--dry-run: nothing written")
        return 0

    backup = args.path.with_suffix(f".json.bak-{datetime.now(UTC):%Y%m%d%H%M%S}")
    shutil.copy2(args.path, backup)
    save_state(args.path, PropsCollectorState(events=migrated, remaining_credits=state.remaining_credits))
    print(f"written. backup at {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
