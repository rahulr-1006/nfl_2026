from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from src.collect.client import OddsApiResponse
from src.collect.mainline_historical import (
    DEFAULT_TIMESERIES_OFFSETS_HOURS,
    backfill_historical_mainline,
    estimate_pull_cost,
)
from src.collect.transform import MatchResult
from src.store.pit_store import PointInTimeStore

MATCH = MatchResult(event_id="2024_10_LAC_KC", season=2024, week=10, home_abbr="KC", away_abbr="LAC")
KICKOFF = datetime(2024, 11, 10, 18, 0, tzinfo=UTC)
HOME, AWAY = "Kansas City Chiefs", "Los Angeles Chargers"


def _event_payload():
    return {
        "id": "hist-abc",
        "home_team": HOME,
        "away_team": AWAY,
        "commence_time": "2024-11-10T18:00:00Z",
        "bookmakers": [
            {"key": "pinnacle", "markets": [
                {"key": "h2h", "outcomes": [
                    {"name": HOME, "price": -150}, {"name": AWAY, "price": 130}]}]}
        ],
    }


def _client(remaining_start=25_000):
    """A client whose historical odds endpoint returns a valid snapshot and
    decrements credits, so spend can be asserted the way the API reports it.
    """
    c = MagicMock()
    c.get_historical_events.return_value = OddsApiResponse(
        events=[{"id": "hist-abc", "home_team": HOME, "away_team": AWAY}],
        remaining_credits=remaining_start, used_credits=None, last_cost=1, fetched_at=KICKOFF,
    )
    state = {"remaining": remaining_start}

    def _odds(event_id, date, regions, markets, odds_format="american"):
        state["remaining"] -= 40          # 10 x 2 markets x 2 regions
        return OddsApiResponse(
            events=[_event_payload()], remaining_credits=state["remaining"],
            used_credits=None, last_cost=40,
            # distinct capture_time per offset -- that IS the time series
            fetched_at=datetime.fromisoformat(date),
        )

    c.get_historical_event_odds.side_effect = _odds
    return c


# --- cost estimation, before anything is spent ------------------------------


def test_estimate_pull_cost_matches_the_documented_rate():
    """10 x markets x regions per snapshot, plus one event-id lookup per game
    (reused across every offset). Spending here is irreversible against a grant
    that does not renew, so the estimate must be checkable without calling out.
    """
    # 5 offsets x (10 x 2 markets x 2 regions) + 1 lookup = 201 per game
    assert estimate_pull_cost(1, "h2h,totals", "us,eu", (120.0, 72.0, 48.0, 24.0, 6.0)) == 201
    assert estimate_pull_cost(105, "h2h,totals", "us,eu", DEFAULT_TIMESERIES_OFFSETS_HOURS) == 21_105
    # props are the reason this is mainline-only: 7 markets is 700/game
    assert estimate_pull_cost(1, "h2h", "us,eu", (6.0,)) == 21


def test_default_offsets_exclude_the_close_we_already_own():
    """570 games already carry a ~15-minute-out snapshot. Re-buying the close
    would pay twice for a price we hold; the value is in the EARLIER points.
    """
    assert min(DEFAULT_TIMESERIES_OFFSETS_HOURS) >= 1.0
    assert max(DEFAULT_TIMESERIES_OFFSETS_HOURS) == 120.0


# --- the pull actually produces a series ------------------------------------


def test_pull_produces_one_snapshot_per_offset(tmp_path):
    client = _client()
    store = PointInTimeStore(root=tmp_path)
    offsets = (120.0, 48.0, 6.0)

    result = backfill_historical_mainline(
        client, [(MATCH, HOME, AWAY, KICKOFF)], store,
        markets="h2h,totals", offsets_hours=offsets,
    )

    assert client.get_historical_event_odds.call_count == len(offsets)
    assert result["found"] == 1

    df = store.read_as_of(KICKOFF + timedelta(days=1))
    # The point of the whole exercise: MORE THAN ONE capture_time per contract.
    per_contract = df.groupby(["event_id", "book", "market", "side"])["capture_time"].nunique()
    assert per_contract.min() == len(offsets)


def test_event_id_is_looked_up_once_not_once_per_offset(tmp_path):
    """The lookup is 1 credit but it is the only call that does not scale with
    offsets -- doing it per offset would quietly multiply the cheap part.
    """
    client = _client()
    backfill_historical_mainline(
        client, [(MATCH, HOME, AWAY, KICKOFF)], PointInTimeStore(root=tmp_path),
        markets="h2h,totals", offsets_hours=(120.0, 48.0, 6.0),
    )
    assert client.get_historical_events.call_count == 1


def test_store_dedupe_preserves_the_series(tmp_path):
    """`CONTRACT_KEY` includes capture_time, so distinct offsets must survive
    `read_as_of`'s dedupe. If they collapsed, the pull would be worthless.
    """
    client = _client()
    store = PointInTimeStore(root=tmp_path)
    offsets = (120.0, 72.0, 48.0, 24.0, 6.0)
    backfill_historical_mainline(
        client, [(MATCH, HOME, AWAY, KICKOFF)], store,
        markets="h2h,totals", offsets_hours=offsets,
    )
    deduped = store.read_as_of(KICKOFF + timedelta(days=1))
    raw = store.read_as_of(KICKOFF + timedelta(days=1), dedupe=False)
    assert deduped["capture_time"].nunique() == len(offsets)
    assert len(deduped) == len(raw)      # nothing was a genuine duplicate


# --- the spend cap ----------------------------------------------------------


def test_credit_cap_stops_the_run_mid_pull(tmp_path):
    """Checked against the API's OWN remaining-credit reading as the run
    proceeds, not just estimated up front: a runaway loop would eat a grant that
    does not renew, and the spend is irreversible.
    """
    client = _client()
    games = [(MATCH, HOME, AWAY, KICKOFF + timedelta(days=i)) for i in range(10)]

    result = backfill_historical_mainline(
        client, games, PointInTimeStore(root=tmp_path),
        markets="h2h,totals", offsets_hours=(120.0, 48.0, 6.0),
        max_credits=200,                       # ~1.7 games' worth at 120/game
    )
    assert result["credits_spent"] >= 200
    assert result["found"] < len(games)        # stopped early
    assert client.get_historical_event_odds.call_count < 3 * len(games)


def test_no_cap_means_no_early_stop(tmp_path):
    client = _client()
    games = [(MATCH, HOME, AWAY, KICKOFF + timedelta(days=i)) for i in range(3)]
    result = backfill_historical_mainline(
        client, games, PointInTimeStore(root=tmp_path),
        markets="h2h,totals", offsets_hours=(120.0, 6.0),
    )
    assert result["found"] == 3


def test_spend_sums_real_per_call_cost_including_the_lookup(tmp_path):
    """**Caught by the live probe**: differencing `remaining` against a baseline
    taken from the FIRST response omits that response's own charge -- the probe
    reported 160 against a true 201. The cap guards irreversible spending against
    a grant that does not renew, so it must never undercount.
    """
    client = _client()
    result = backfill_historical_mainline(
        client, [(MATCH, HOME, AWAY, KICKOFF)], PointInTimeStore(root=tmp_path),
        markets="h2h,totals", offsets_hours=(120.0, 72.0, 48.0, 24.0, 6.0),
    )
    # 1 event-id lookup + 5 snapshots x 40 = 201, matching estimate_pull_cost
    assert result["credits_spent"] == 201
    assert result["credits_spent"] == estimate_pull_cost(
        1, "h2h,totals", "us,eu", (120.0, 72.0, 48.0, 24.0, 6.0)
    )
