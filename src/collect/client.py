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
        url = f"{_BASE_URL}/sports/{self._sport_key}/odds/"
        params = {
            "apiKey": self._api_key,
            "regions": regions,
            "markets": markets,
            "oddsFormat": odds_format,
        }

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._session.get(url, params=params, timeout=self._timeout)
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = exc
                if attempt < self._max_retries:
                    time.sleep(self._retry_backoff_seconds * (attempt + 1))
                    continue
                raise OddsApiError(f"network error calling The Odds API: {exc}") from exc

            if response.status_code in (401, 402, 429):
                raise RateLimitExceeded(
                    f"The Odds API rejected request (status={response.status_code}): {response.text[:500]}"
                )
            if response.status_code != 200:
                raise OddsApiError(
                    f"The Odds API returned status={response.status_code}: {response.text[:500]}"
                )

            return OddsApiResponse(
                events=response.json(),
                remaining_credits=_parse_int_header(response.headers, "x-requests-remaining"),
                used_credits=_parse_int_header(response.headers, "x-requests-used"),
                last_cost=_parse_int_header(response.headers, "x-requests-last"),
                fetched_at=datetime.now(UTC),
            )

        raise OddsApiError(f"network error calling The Odds API: {last_error}")
