import random
from datetime import UTC, datetime, timedelta, timezone

import pytest

from src.store.pit_store import LeakageError, PointInTimeStore
from src.store.schema import Market, OddsSnapshot, Side

BASE = datetime(2026, 9, 4, 0, 0, tzinfo=UTC)
KICKOFF = datetime(2026, 9, 7, 17, 0, tzinfo=UTC)


def _snap(capture_offset_hours: float, price_american: int = -110) -> OddsSnapshot:
    return OddsSnapshot.from_american(
        capture_time=BASE + timedelta(hours=capture_offset_hours),
        event_id="2026_01_KC_LAC",
        season=2026,
        week=1,
        home_team="LAC",
        away_team="KC",
        event_start_time=KICKOFF,
        book="pinnacle",
        market=Market.SPREAD,
        side=Side.HOME,
        price_american=price_american,
        line=-2.5,
    )


def test_write_creates_a_new_file_and_never_overwrites(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    path1 = store.write([_snap(0)])
    path2 = store.write([_snap(1)])
    assert path1 != path2
    assert path1.exists() and path2.exists()


def test_write_rejects_empty_batch(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    with pytest.raises(ValueError):
        store.write([])


def test_read_as_of_excludes_snapshot_captured_after_decision_time(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    store.write([_snap(0, price_american=-110)])
    store.write([_snap(10, price_american=-105)])  # captured later, sharper price

    decision_time = BASE + timedelta(hours=5)
    visible = store.read_as_of(decision_time)

    assert len(visible) == 1
    assert visible.iloc[0]["price_american"] == -110


def test_read_as_of_includes_snapshot_at_exact_decision_time(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    store.write([_snap(5)])
    visible = store.read_as_of(BASE + timedelta(hours=5))
    assert len(visible) == 1


def test_read_as_of_honors_the_boundary_across_a_non_utc_but_tz_aware_decision_time(tmp_path):
    # A 2026-08-21 adversarial audit verified this live (not just by
    # inspection) but found no existing test pinning it down -- correct
    # today by virtue of standard Python/pandas tz-aware comparison, but
    # unguarded against a future regression. decision_time expressed in
    # UTC-4 rather than UTC must still honor the exact same inclusive
    # boundary as every other test in this file.
    store = PointInTimeStore(root=tmp_path)
    store.write([_snap(5)])  # captured at BASE + 5h UTC

    utc_minus_4 = timezone(timedelta(hours=-4))
    same_instant = (BASE + timedelta(hours=5)).astimezone(utc_minus_4)
    one_minute_earlier = same_instant - timedelta(minutes=1)

    assert len(store.read_as_of(same_instant)) == 1
    assert store.read_as_of(one_minute_earlier).empty


def test_read_as_of_before_any_capture_returns_empty(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    store.write([_snap(5)])
    visible = store.read_as_of(BASE - timedelta(hours=1))
    assert visible.empty


def test_read_as_of_never_leaks_future_rows_across_random_decision_times(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    offsets = [0, 2, 4, 6.5, 8, 12, 24, 48]
    for off in offsets:
        store.write([_snap(off)])

    rng = random.Random(42)
    for _ in range(50):
        decision_time = BASE + timedelta(hours=rng.uniform(-5, 60))
        visible = store.read_as_of(decision_time)
        if not visible.empty:
            assert (visible["capture_time"] <= decision_time).all()
        expected_count = sum(1 for off in offsets if BASE + timedelta(hours=off) <= decision_time)
        assert len(visible) == expected_count


def test_leakage_guard_fires_if_filter_is_ever_broken(tmp_path, monkeypatch):
    """Regression guard: if `_filter` is ever changed to stop filtering,
    read_as_of must raise LeakageError rather than silently leak future data."""
    store = PointInTimeStore(root=tmp_path)
    store.write([_snap(0)])
    store.write([_snap(100)])  # far in the future relative to our decision time

    monkeypatch.setattr(PointInTimeStore, "_filter", staticmethod(lambda df, dt, eid: df))

    with pytest.raises(LeakageError):
        store.read_as_of(BASE + timedelta(hours=1))


def test_decision_time_must_be_tz_aware(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    store.write([_snap(0)])
    with pytest.raises(ValueError):
        store.read_as_of(datetime(2026, 9, 4, 5, 0))  # noqa: DTZ001 -- naive on purpose


def test_event_id_filter(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    store.write([_snap(0)])
    other = OddsSnapshot.from_american(
        capture_time=BASE,
        event_id="2026_01_BUF_NYJ",
        season=2026,
        week=1,
        home_team="NYJ",
        away_team="BUF",
        event_start_time=KICKOFF,
        book="pinnacle",
        market=Market.SPREAD,
        side=Side.HOME,
        price_american=-110,
        line=1.5,
    )
    store.write([other])

    visible = store.read_as_of(BASE + timedelta(hours=1), event_id="2026_01_KC_LAC")
    assert len(visible) == 1
    assert visible.iloc[0]["event_id"] == "2026_01_KC_LAC"


def test_read_as_of_exposes_new_columns_even_when_no_file_on_disk_has_them(tmp_path):
    """Regression guard: a schema addition (player_name/prop_stat, added
    for player props) must be a visible, indexable column immediately --
    not only once the first snapshot actually using it has been written.
    Simulates the real situation on 2026-08-17: months of pre-props
    snapshots already on disk, all missing these columns entirely.
    """
    import pandas as pd

    from src.store.pit_store import _COLUMNS

    store = PointInTimeStore(root=tmp_path)
    old_shape_columns = [c for c in _COLUMNS if c not in ("player_name", "prop_stat")]
    row = _snap(0).model_dump()
    row["market"] = row["market"].value
    row["side"] = row["side"].value
    old_df = pd.DataFrame([{k: row[k] for k in old_shape_columns}])
    partition_dir = tmp_path / "capture_date=2026-09-04"
    partition_dir.mkdir(parents=True)
    old_df.to_parquet(partition_dir / "old_shape.parquet", index=False)

    visible = store.read_as_of(BASE + timedelta(hours=1))
    assert "player_name" in visible.columns
    assert "prop_stat" in visible.columns
    assert visible["player_name"].isna().all()


# --- deterministic contract dedupe ------------------------------------------
#
# The store is append-only, so a re-run of a historical pull can legitimately
# re-record rows it already holds. Selectors like `engine.latest_fair_prob` pick
# via `idxmax` on capture_time, which is AMBIGUOUS across tied rows -- so without
# dedupe the chosen price can differ between runs of identical code.


def _prop(capture_offset_hours: float, prop_stat: str, price_american: int = -110,
          line: float = 2.5, player: str = "Jared Goff") -> OddsSnapshot:
    return OddsSnapshot.from_american(
        capture_time=BASE + timedelta(hours=capture_offset_hours),
        event_id="2026_01_KC_LAC", season=2026, week=1, home_team="LAC", away_team="KC",
        event_start_time=KICKOFF, book="barstool", market=Market.PLAYER_PROP,
        side=Side.OVER, price_american=price_american, line=line,
        player_name=player, prop_stat=prop_stat,
    )


def test_identical_rewrite_collapses_to_one_row(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    store.write([_snap(1)])
    store.write([_snap(1)])          # same contract, same instant, re-recorded
    assert len(store.read_as_of(KICKOFF)) == 1


def test_raw_record_is_preserved_and_reachable(tmp_path):
    """Nothing is mutated -- dedupe is a read-time view, not a deletion."""
    store = PointInTimeStore(root=tmp_path)
    store.write([_snap(1)])
    store.write([_snap(1)])
    assert len(store.read_as_of(KICKOFF, dedupe=False)) == 2


def test_conflicting_prices_resolve_to_one_row_deterministically(tmp_path):
    """Real case: Khalil Herbert receptions 1.5 at betonlineag carried -119 AND
    -125 at the same instant. Either is equally (un)justified; what matters is
    that repeated reads agree, and that we do not silently pick the better one.
    """
    store = PointInTimeStore(root=tmp_path)
    store.write([_snap(1, price_american=-119)])
    store.write([_snap(1, price_american=-125)])

    first = store.read_as_of(KICKOFF)
    assert len(first) == 1
    for _ in range(3):
        assert store.read_as_of(KICKOFF)["price_american"].iloc[0] == first["price_american"].iloc[0]


def test_prop_stat_is_part_of_the_contract_key(tmp_path):
    """**Regression guard for a real analysis error (2026-08-23).** One player
    can carry `passing_tds` and `rushing_yards` at the SAME line value (2.5),
    same book, same instant. Omitting prop_stat from the key makes two unrelated
    contracts look like one contract with two prices -- which produced a false
    "2,752 conflicting prices" reading when the true count is 1. These must both
    survive.
    """
    store = PointInTimeStore(root=tmp_path)
    store.write([_prop(1, "passing_tds", price_american=300),
                 _prop(1, "rushing_yards", price_american=-150)])
    out = store.read_as_of(KICKOFF)
    assert len(out) == 2
    assert set(out["prop_stat"]) == {"passing_tds", "rushing_yards"}


def test_same_contract_at_different_times_is_not_collapsed(tmp_path):
    """Dedupe must never flatten a price HISTORY -- that is the whole store."""
    store = PointInTimeStore(root=tmp_path)
    store.write([_snap(1, price_american=-110), _snap(2, price_american=-120)])
    assert len(store.read_as_of(KICKOFF)) == 2


# --- per-instance read cache (2026-10-13) -------------------------------------


def test_cached_reads_see_a_file_written_after_the_first_read(tmp_path):
    """The monitor reuses one store across a whole tick while the collector keeps
    writing; a capture landing mid-tick must be visible to the next read."""
    store = PointInTimeStore(root=tmp_path)
    store.write([_snap(0)])
    assert len(store.read_as_of(BASE + timedelta(hours=24))) == 1
    store.write([_snap(1)])
    assert len(store.read_as_of(BASE + timedelta(hours=24))) == 2


def test_cached_reads_do_not_reread_disk_when_nothing_changed(tmp_path, monkeypatch):
    store = PointInTimeStore(root=tmp_path)
    store.write([_snap(0)])
    store.read_as_of(BASE + timedelta(hours=24))
    calls = []
    original = PointInTimeStore._read_files
    monkeypatch.setattr(PointInTimeStore, "_read_files", staticmethod(lambda f: calls.append(f) or original(f)))
    store.read_as_of(BASE + timedelta(hours=1))
    store.read_as_of(BASE + timedelta(hours=24), event_id="2026_01_KC_LAC")
    assert calls == []


def test_mutating_a_returned_frame_does_not_corrupt_later_reads(tmp_path):
    store = PointInTimeStore(root=tmp_path)
    store.write([_snap(0, price_american=-110)])
    first = store.read_as_of(BASE + timedelta(hours=24))
    first.loc[:, "price_american"] = 999
    assert store.read_as_of(BASE + timedelta(hours=24)).iloc[0]["price_american"] == -110


def test_cached_dedupe_matches_dedupe_after_filter(tmp_path):
    """Dedupe-then-filter (cached) must equal filter-then-dedupe (the old path):
    duplicate rows share capture_time, so a time filter keeps or drops them whole."""
    store = PointInTimeStore(root=tmp_path)
    for h in (0, 0, 2, 2, 5):
        store.write([_snap(h)])
    for cut in (0, 1, 2, 5, 24):
        t = BASE + timedelta(hours=cut)
        cached = store.read_as_of(t)
        raw = store.read_as_of(t, dedupe=False)
        expected = raw.drop_duplicates(subset=["capture_time", "event_id", "book", "market", "side",
                                               "player_name", "prop_stat", "line"], keep="last")
        assert cached.reset_index(drop=True).equals(expected.reset_index(drop=True))
