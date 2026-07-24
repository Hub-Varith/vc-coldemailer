"""Thin async wrapper over the Octen retrieval API (api.octen.ai).

This is the ONLY file allowed to know Octen's actual wire format. Every
other module talks in terms of our own OctenQuery / OctenResult models
(app/models.py). If the real API's field names differ from the
`_to_octen_payload` / `_from_octen_result` mapping below, fix it here and
nowhere else.

The exact request/response shape below is an informed assumption (see
BACKEND_SPEC.md Section 5.1/13) -- it has not been confirmed against live
docs. `OctenResult.raw` always keeps the untouched payload so nothing is
lost if a field was mapped wrong.
"""

import asyncio
import logging
import time
from datetime import datetime

import httpx

from app.config import Settings
from app.models import OctenQuery, OctenResult

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 3


class OctenClient:
    """Async client for Octen search. One instance per app process."""

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient | None = None) -> None:
        self._api_key = settings.octen_api_key
        self._base_url = settings.octen_base_url
        self._timeout_s = settings.octen_timeout_s
        # Callers may inject their own httpx client (e.g. in tests, to mock transport).
        self._http = http_client or httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout_s)

    # --- public API ---

    async def search(self, query: OctenQuery) -> list[OctenResult]:
        """Run one query against Octen. Never raises on a request failure --
        a timeout or exhausted-retry is a soft failure, logged and returned
        as an empty result list, so one bad query never kills the fan-out."""
        started_at = time.monotonic()
        payload = self._to_octen_payload(query)

        try:
            response = await self._post_with_retries(payload)
        except httpx.HTTPError as exc:
            logger.warning("octen query failed after retries: %r (%s)", query.query, exc)
            return []

        elapsed_s = time.monotonic() - started_at
        raw_results = response.json().get("results", [])
        results = [self._from_octen_result(item) for item in raw_results]
        logger.info("octen query %r -> %d results in %.3fs", query.query, len(results), elapsed_s)
        return results

    async def aclose(self) -> None:
        await self._http.aclose()

    # --- private internals ---

    async def _post_with_retries(self, payload: dict) -> httpx.Response:
        last_exc: httpx.HTTPError | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                response = await self._http.post(
                    "/search",
                    json=payload,
                    headers={"X-Api-Key": self._api_key},
                )
            except httpx.TimeoutException as exc:
                last_exc = exc
                if attempt < _MAX_ATTEMPTS:
                    await self._sleep_before_retry(attempt, retry_after_s=None)
                continue

            if response.status_code not in _RETRYABLE_STATUS_CODES:
                response.raise_for_status()
                return response

            last_exc = httpx.HTTPStatusError(
                f"octen returned {response.status_code}", request=response.request, response=response
            )
            if attempt < _MAX_ATTEMPTS:
                retry_after_s = self._parse_retry_after(response)
                await self._sleep_before_retry(attempt, retry_after_s)

        assert last_exc is not None
        raise last_exc

    async def _sleep_before_retry(self, attempt: int, retry_after_s: float | None) -> None:
        backoff_s = retry_after_s if retry_after_s is not None else (2**attempt) * 0.5
        await asyncio.sleep(backoff_s)

    # --- static helpers ---

    @staticmethod
    def _parse_retry_after(response: httpx.Response) -> float | None:
        header = response.headers.get("Retry-After")
        if header is None:
            return None
        try:
            return float(header)
        except ValueError:
            return None

    @staticmethod
    def _to_octen_payload(query: OctenQuery) -> dict:
        """Our OctenQuery -> Octen's request body."""
        payload: dict = {"query": query.query, "max_results": query.max_results}
        if query.include_domains:
            payload["include_domains"] = query.include_domains
        if query.exclude_domains:
            payload["exclude_domains"] = query.exclude_domains
        if query.published_after:
            payload["published_after"] = query.published_after.isoformat()
        if query.require_text:
            payload["require_text"] = query.require_text
        if query.extract_content:
            payload["extract_content"] = True
            if query.content_token_limit:
                payload["content_token_limit"] = query.content_token_limit
        return payload

    @staticmethod
    def _from_octen_result(item: dict) -> OctenResult:
        """Octen's response item -> our OctenResult."""
        return OctenResult(
            url=item.get("url", ""),
            title=item.get("title"),
            snippet=item.get("snippet"),
            content=item.get("content"),
            published_at=_parse_datetime(item.get("published_at")),
            crawled_at=_parse_datetime(item.get("crawled_at")),
            raw=item,
        )


def _parse_datetime(value: str | None) -> datetime | None:
    """Octen may omit publish/crawl dates entirely -- always handle None."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
