from datetime import UTC, datetime, timedelta

import pandas as pd

from src.backtest.pinnacle_lag import detect_moves, pinnacle_fair_path, stale_quotes
from src.devig.convert import american_to_decimal
from src.notify import monitor_run
from src.signal import prereg_scan, shadow_log
from src.signal.prereg_scan import H1, H1B, live_props, run

AS_OF = datetime(2026, 10, 11, 15, 0, tzinfo=UTC)
KICKOFF = AS_OF + timedelta(hours=2)
T0 = AS_OF - timedelta(minutes=30)
T1 = AS_OF - timedelta(minutes=15)


def _row(t, book, side, price, kickoff=KICKOFF, player="Star WR", line=4.5):
    return {
        "event_id": "2026_05_KC_BUF", "player_name": player, "prop_stat": "receptions", "line": line,
        "capture_time": t, "event_start_time": kickoff, "book": book, "side": side, "market": "player_prop",
        "price_american": price, "price_decimal": american_to_decimal(price),
    }


def _pin(t, over, under, **kw):
    return [_row(t, "pinnacle", "over", over, **kw), _row(t, "pinnacle", "under", under, **kw)]


class FakeStore:
    def __init__(self, df):
        self.df = df

    def read_as_of(self, as_of, event_id=None, dedupe=True):
        return self.df[self.df["capture_time"] <= as_of]


def _moving_market():
    # Pinnacle moves ~6pp toward the over between T0 and T1; FanDuel lags at -105.
    return pd.DataFrame(
        _pin(T0, -110, -110) + _pin(T1, -140, +120)
        + [_row(T1, "fanduel", "over", -105), _row(T1, "draftkings", "under", -110)]
    )


def test_frozen_parameters_are_the_preregistered_ones():
    assert (H1.min_move, H1.min_ev) == (0.02, 0.01)
    assert (H1B.min_move, H1B.min_ev) == (0.0, 0.01)


def test_live_scan_logs_exactly_what_the_backtest_selects(tmp_path):
    df = _moving_market()
    path = tmp_path / "prereg.jsonl"
    run(FakeStore(df), as_of=AS_OF, path=path)

    logged = {(o.strategy, o.book, o.side.value) for o in shadow_log.load(path)}
    props = live_props(df, AS_OF)
    fair = pinnacle_fair_path(props)
    for s in (H1, H1B):
        expected = stale_quotes(detect_moves(fair, s.min_move), props, s.min_ev)
        assert {(s.name, b, sd) for b, sd in zip(expected["book"], expected["side"], strict=True)} == {
            x for x in logged if x[0] == s.name
        }
    assert ("h1_pinnacle_lag", "fanduel", "over") in logged


def test_a_second_tick_does_not_log_the_same_contract_side_again(tmp_path):
    path = tmp_path / "prereg.jsonl"
    store = FakeStore(_moving_market())
    first = run(store, as_of=AS_OF, path=path)
    second = run(store, as_of=AS_OF + timedelta(minutes=5), path=path)
    assert sum(first.values()) > 0
    assert second == {"h1_pinnacle_lag": 0, "h1b_stale_price": 0}


def test_games_that_already_kicked_off_are_never_logged(tmp_path):
    started = AS_OF - timedelta(minutes=5)
    df = pd.DataFrame(
        _pin(T0, -110, -110, kickoff=started) + _pin(T1, -140, +120, kickoff=started)
        + [_row(T1, "fanduel", "over", -105, kickoff=started)]
    )
    path = tmp_path / "prereg.jsonl"
    assert run(FakeStore(df), as_of=AS_OF, path=path) == {"h1_pinnacle_lag": 0, "h1b_stale_price": 0}
    assert not path.exists()


def test_prereg_scan_has_no_sms_path():
    assert not any("sms" in name.lower() for name in vars(prereg_scan))


def test_monitor_writes_prereg_next_to_the_redirected_shadow_log(tmp_path, monkeypatch):
    seen = {}
    monkeypatch.setattr(monitor_run, "load_alert_state", dict)
    monkeypatch.setattr(monitor_run, "save_alert_state", lambda state: None)
    monkeypatch.setattr(monitor_run, "prereg_run", lambda store, path: seen.setdefault("path", path))
    monkeypatch.delenv("ALERT_PHONE_NUMBER", raising=False)
    monitor_run.run(store_root=str(tmp_path / "store"), shadow_path=tmp_path / "shadow.jsonl")
    assert seen["path"] == tmp_path / "shadow_log_prereg.jsonl"


def test_a_failing_prereg_scan_cannot_break_the_monitor(tmp_path, monkeypatch):
    def boom(store, path):
        raise RuntimeError("prereg exploded")

    monkeypatch.setattr(monitor_run, "load_alert_state", dict)
    monkeypatch.setattr(monitor_run, "save_alert_state", lambda state: None)
    monkeypatch.setattr(monitor_run, "prereg_run", boom)
    monkeypatch.delenv("ALERT_PHONE_NUMBER", raising=False)
    assert monitor_run.run(store_root=str(tmp_path / "store"), shadow_path=tmp_path / "shadow.jsonl") == 0


def test_read_once_store_reads_the_real_store_a_single_time():
    calls = []

    class CountingStore(FakeStore):
        def read_as_of(self, as_of, event_id=None, dedupe=True):
            calls.append(as_of)
            return super().read_as_of(as_of)

    once = prereg_scan.ReadOnceStore(CountingStore(_moving_market()))
    first = once.read_as_of(AS_OF)
    second = once.read_as_of(T0)  # an earlier as_of is still honoured by filtering
    assert len(calls) == 1
    assert (second["capture_time"] <= T0).all() and len(second) < len(first)
