from unittest.mock import MagicMock

import pytest
import requests

from src.collect.client import OddsApiClient, OddsApiError, RateLimitExceeded


def _response(status_code=200, json_body=None, headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body if json_body is not None else []
    resp.headers = headers or {}
    resp.text = "error body"
    return resp


def test_get_odds_parses_events_and_quota_headers():
    session = MagicMock()
    session.get.return_value = _response(
        json_body=[{"id": "abc"}],
        headers={"x-requests-remaining": "494", "x-requests-used": "6", "x-requests-last": "6"},
    )
    client = OddsApiClient("key", session=session)

    response = client.get_odds("eu", "h2h,spreads,totals")

    assert response.events == [{"id": "abc"}]
    assert response.remaining_credits == 494
    assert response.used_credits == 6
    assert response.last_cost == 6


def test_get_odds_missing_quota_headers_are_none():
    session = MagicMock()
    session.get.return_value = _response(json_body=[], headers={})
    client = OddsApiClient("key", session=session)

    response = client.get_odds("eu", "h2h")

    assert response.remaining_credits is None


@pytest.mark.parametrize("status", [401, 402, 429])
def test_get_odds_raises_rate_limit_exceeded_on_quota_or_auth_errors(status):
    session = MagicMock()
    session.get.return_value = _response(status_code=status)
    client = OddsApiClient("key", session=session)

    with pytest.raises(RateLimitExceeded):
        client.get_odds("eu", "h2h")


def test_get_odds_raises_odds_api_error_on_other_bad_status():
    session = MagicMock()
    session.get.return_value = _response(status_code=500)
    client = OddsApiClient("key", session=session)

    with pytest.raises(OddsApiError):
        client.get_odds("eu", "h2h")


def test_get_odds_retries_network_errors_then_raises():
    session = MagicMock()
    session.get.side_effect = requests.ConnectionError("boom")
    client = OddsApiClient("key", session=session, max_retries=2, retry_backoff_seconds=0)

    with pytest.raises(OddsApiError):
        client.get_odds("eu", "h2h")

    assert session.get.call_count == 3  # initial attempt + 2 retries


def test_get_odds_recovers_after_transient_network_error():
    session = MagicMock()
    session.get.side_effect = [requests.ConnectionError("boom"), _response(json_body=[])]
    client = OddsApiClient("key", session=session, max_retries=2, retry_backoff_seconds=0)

    response = client.get_odds("eu", "h2h")

    assert response.events == []
    assert session.get.call_count == 2


# --- get_event_odds (per-event endpoint, needed for player props) ---


def test_get_event_odds_wraps_the_single_event_object_in_a_list():
    # The per-event endpoint returns one event dict, not a list -- unlike
    # get_odds(), whose response is already a list of events. Both must
    # come back through OddsApiResponse.events as a list for callers to
    # treat uniformly.
    session = MagicMock()
    session.get.return_value = _response(
        json_body={"id": "abc123", "bookmakers": []},
        headers={"x-requests-remaining": "440", "x-requests-last": "2"},
    )
    client = OddsApiClient("key", session=session)

    response = client.get_event_odds("abc123", "us", "player_pass_yds")

    assert response.events == [{"id": "abc123", "bookmakers": []}]
    assert response.remaining_credits == 440
    assert response.last_cost == 2


def test_get_event_odds_hits_the_per_event_url():
    session = MagicMock()
    session.get.return_value = _response(json_body={"id": "abc123"})
    client = OddsApiClient("key", session=session)

    client.get_event_odds("abc123", "us", "player_pass_yds")

    called_url = session.get.call_args[0][0]
    assert called_url.endswith("/sports/americanfootball_nfl/events/abc123/odds")


def test_get_event_odds_raises_rate_limit_exceeded_like_get_odds():
    session = MagicMock()
    session.get.return_value = _response(status_code=402)
    client = OddsApiClient("key", session=session)

    with pytest.raises(RateLimitExceeded):
        client.get_event_odds("abc123", "us", "player_pass_yds")
