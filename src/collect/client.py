"""Thin HTTP wrapper around The Odds API.

Talks to The Odds API directly (not through a provider interface) — this
is a single-provider personal project, not a multi-book framework.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime

import requests

_BASE_URL = "https://api.the-odds-api.com/v4"


class OddsApiError(RuntimeError):
    """Network or unexpected-response failure talking to The Odds API."""


class RateLimitExceeded(OddsApiError):
    """The API rejected the request for quota/auth reasons (401/402/429)."""


@dataclass(frozen=True)
class OddsApiResponse:
    events: list[dict]
    remaining_credits: int | None
    used_credits: int | None
    last_cost: int | None
    fetched_at: datetime


def _parse_int_header(headers: dict, key: str) -> int | None:
    value = headers.get(key)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


class OddsApiClient:
    def __init__(
        self,
        api_key: str,
        sport_key: str = "americanfootball_nfl",
        timeout: float = 15.0,
        session: requests.Session | None = None,
        max_retries: int = 2,
        retry_backoff_seconds: float = 1.0,
    ):
        self._api_key = api_key
        self._sport_key = sport_key
        self._timeout = timeout
        self._session = session or requests.Session()
        self._max_retries = max_retries
        self._retry_backoff_seconds = retry_backoff_seconds

    def get_odds(self, regions: str, markets: str, odds_format: str = "american") -> OddsApiResponse:
        """Bulk endpoint: one call returns every event in the sport's
        current slate. This is what src/collect/scheduler.py polls.
        """
        url = f"{_BASE_URL}/sports/{self._sport_key}/odds/"
        params = {"apiKey": self._api_key, "regions": regions, "markets": markets, "oddsFormat": odds_format}
        response = self._request(url, params)
        return self._to_response(events=response.json(), headers=response.headers)

    def get_events(self) -> OddsApiResponse:
        """Live events listing (id, team names, commence_time) for the
        sport's current slate -- **free, 0 credits**, confirmed against The
        Odds API's own docs. The cheap way to discover event ids and
        kickoff times before spending real credits on `get_event_odds`.
        """
        url = f"{_BASE_URL}/sports/{self._sport_key}/events"
        params = {"apiKey": self._api_key}
        response = self._request(url, params)
        return self._to_response(events=response.json(), headers=response.headers)

    def get_event_odds(self, event_id: str, regions: str, markets: str, odds_format: str = "american") -> OddsApiResponse:
        """Per-event endpoint: the only way to reach player-prop markets
        (src/collect/props.py) -- one call per game, unlike get_odds()'s
        one call for the whole slate. Cost = unique markets returned x
        regions, billed per call, so this is meaningfully more expensive
        per game than the bulk endpoint.
        """
        url = f"{_BASE_URL}/sports/{self._sport_key}/events/{event_id}/odds"
        params = {"apiKey": self._api_key, "regions": regions, "markets": markets, "oddsFormat": odds_format}
        response = self._request(url, params)
        return self._to_response(events=[response.json()], headers=response.headers)

    def get_historical_events(self, date: str) -> OddsApiResponse:
        """Historical events list as of `date` (ISO 8601, e.g.
        "2024-11-10T18:00:00Z") -- 1 credit per call, the cheap way to
        discover an Odds API event id for a past game before pulling its
        historical prop odds. Requires a paid plan (HISTORICAL_UNAVAILABLE_ON_FREE_USAGE_PLAN
        otherwise). `fetched_at` on the returned response is the *requested*
        date, not wall-clock now -- see get_historical_event_odds for why
        that distinction matters more there.
        """
        url = f"{_BASE_URL}/historical/sports/{self._sport_key}/events"
        params = {"apiKey": self._api_key, "date": date}
        response = self._request(url, params)
        body = response.json()
        return self._to_response(events=body["data"], headers=response.headers, fetched_at=_parse_iso(body["timestamp"]))

    def get_historical_event_odds(
        self, event_id: str, date: str, regions: str, markets: str, odds_format: str = "american"
    ) -> OddsApiResponse:
        """Historical per-event odds, snapshotted at the nearest available
        timestamp <= `date` (5-minute intervals; player props specifically
        only exist from 2023-05-03T05:30:00Z onward). Costs 10x the live
        per-event rate (10 x markets x regions) and requires a paid plan.

        The response wraps the event under a "data" key alongside the
        actual snapshot timestamp (which may differ slightly from the
        requested `date` -- "nearest available", not exact). That real
        timestamp becomes `fetched_at`/capture_time downstream, never
        wall-clock now -- getting this wrong would silently corrupt the
        point-in-time discipline every other part of this project depends
        on, labeling a 2024 price as though it were captured today.
        """
        url = f"{_BASE_URL}/historical/sports/{self._sport_key}/events/{event_id}/odds"
        params = {"apiKey": self._api_key, "date": date, "regions": regions, "markets": markets, "oddsFormat": odds_format}
        response = self._request(url, params)
        body = response.json()
        return self._to_response(
            events=[body["data"]], headers=response.headers, fetched_at=_parse_iso(body["timestamp"])
        )

    def _request(self, url: str, params: dict) -> requests.Response:
        """Shared retry/error-handling for both endpoints. Returns the raw
        successful response; callers interpret the body themselves since
        get_odds() gets a list and get_event_odds() gets a single object.
        """
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._session.get(url, params=params, timeout=self._timeout)
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = exc
                if attempt < self._max_retries:
                    time.sleep(self._retry_backoff_seconds * (attempt + 1))
                    continue
                # `from None`, not `from exc`: requests embeds the full URL in its
                # exception text, apiKey query param included, and a chained
                # cause would print it in any logged traceback.
                raise OddsApiError(f"network error calling The Odds API: {self._redact(exc)}") from None

            if response.status_code in (401, 402, 429):
                raise RateLimitExceeded(
                    f"The Odds API rejected request (status={response.status_code}): {response.text[:500]}"
                )
            if response.status_code != 200:
                raise OddsApiError(
                    f"The Odds API returned status={response.status_code}: {response.text[:500]}"
                )
            return response

        raise OddsApiError(f"network error calling The Odds API: {self._redact(last_error)}")

    def _redact(self, value: object) -> str:
        """Error text with the API key masked. It used to reach logs/*.err.log
        verbatim via the request URL (seen 2026-10-04 on a DNS failure)."""
        return str(value).replace(self._api_key, "***") if self._api_key else str(value)

    @staticmethod
    def _to_response(events: list[dict], headers: dict, fetched_at: datetime | None = None) -> OddsApiResponse:
        return OddsApiResponse(
            events=events,
            remaining_credits=_parse_int_header(headers, "x-requests-remaining"),
            used_credits=_parse_int_header(headers, "x-requests-used"),
            last_cost=_parse_int_header(headers, "x-requests-last"),
            fetched_at=fetched_at or datetime.now(UTC),
        )
