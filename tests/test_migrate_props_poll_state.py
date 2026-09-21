"""`poll_count` is an index into a grid, so changing the grid moves every
in-flight event. These pin the property that makes the migration correct:
**the migrated index points at the same moment before kickoff, not the same
ordinal.** See scripts/migrate_props_poll_state.py for the live case that
forced it (a game 5.88h out whose index suddenly meant 8.75h).
"""

from __future__ import annotations

from scripts.migrate_props_poll_state import (
    OLD_ARB_POLL_INTERVAL_HOURS,
    _build_targets,
    migrate_poll_count,
)
from src.collect.props_budget import ARB_POLL_INTERVAL_HOURS, POLL_TARGETS

OLD = _build_targets(OLD_ARB_POLL_INTERVAL_HOURS)
NEW = POLL_TARGETS


def test_the_grid_actually_changed_or_this_whole_module_is_vacuous():
    assert ARB_POLL_INTERVAL_HOURS < OLD_ARB_POLL_INTERVAL_HOURS
    assert len(NEW) > len(OLD)


def test_every_migrated_index_points_at_the_same_hours_before_kickoff():
    """The whole point: an event keeps its position in TIME, not its ordinal."""
    for old_count in range(len(OLD)):
        new_count = migrate_poll_count(old_count, OLD, NEW)
        assert NEW[new_count].hours_before_kickoff == OLD[old_count].hours_before_kickoff


def test_indices_above_the_arb_window_are_untouched():
    """Only the arb tier's spacing changed, so an event still in the early,
    sparse or dense tiers must not move at all -- if it did, the migration
    would be rewriting state it has no reason to touch.
    """
    for old_count, target in enumerate(OLD):
        if target.hours_before_kickoff > NEW[0].hours_before_kickoff:
            continue
        if target.hours_before_kickoff > 12.0:  # ARB_WINDOW_HOURS
            assert migrate_poll_count(old_count, OLD, NEW) == old_count


def test_a_finished_event_stays_finished():
    """Mapping a completed schedule back onto a real target would re-open it and
    re-poll a game that has already kicked off.
    """
    assert migrate_poll_count(len(OLD), OLD, NEW) == len(NEW)
    assert migrate_poll_count(len(OLD) + 10, OLD, NEW) == len(NEW)


def test_the_live_case_that_forced_this():
    """DEN@KC on 2026-09-14: index 44 meant 5.5h before kickoff on the old grid
    and 8.75h on the new one. Migrated, it means 5.5h again.
    """
    assert OLD[44].hours_before_kickoff == 5.5
    assert NEW[44].hours_before_kickoff == 8.75
    assert NEW[migrate_poll_count(44, OLD, NEW)].hours_before_kickoff == 5.5


def test_migration_never_moves_an_event_backwards_in_time():
    """A migrated index must not point FURTHER from kickoff than the old one --
    that is the failure mode that costs an event its close capture, because the
    scheduler only advances one index per tick and can run out of clock.
    """
    for old_count in range(len(OLD) + 1):
        new_count = migrate_poll_count(old_count, OLD, NEW)
        old_h = OLD[old_count].hours_before_kickoff if old_count < len(OLD) else 0.0
        new_h = NEW[new_count].hours_before_kickoff if new_count < len(NEW) else 0.0
        assert new_h <= old_h
