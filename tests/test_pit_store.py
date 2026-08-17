import random
from datetime import datetime, timedelta, timezone

import pytest

from src.store.pit_store import LeakageError, PointInTimeStore
from src.store.schema import Market, OddsSnapshot, Side

BASE = datetime(2026, 9, 4, 0, 0, tzinfo=timezone.utc)
KICKOFF = datetime(2026, 9, 7, 17, 0, tzinfo=timezone.utc)


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
        store.read_as_of(datetime(2026, 9, 4, 5, 0))  # naive


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
