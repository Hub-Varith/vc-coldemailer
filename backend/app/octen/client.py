"""Thin async wrapper over api.octen.ai.

This is the ONLY module that touches Octen's wire format (BACKEND_SPEC §0, §5.2). If the
real response shape differs from the assumed shape below, fix the mapping here and
nowhere else. `raw` keeps the untouched payload so nothing is lost to a bad guess.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Protocol

import httpx

from ..config import Settings, get_settings
from ..models import OctenQuery, OctenResult
from .local_index import LocalIndex

log = logging.getLogger("proofline.octen.client")

MAX_ATTEMPTS = 3


class SearchBackend(Protocol):
    async def search(self, query: OctenQuery) -> tuple[list[OctenResult], bool]: ...

    @property
    def transport(self) -> str: ...

    async def aclose(self) -> None: ...


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


class OctenClient:
    """HTTP transport. Timeouts and exhausted retries are soft failures, never raises."""

    transport = "octen.http"

    def __init__(self, settings: Settings | None = None, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = client or httpx.AsyncClient(
            base_url=self._settings.octen_base_url,
            timeout=self._settings.octen_timeout_s,
            headers={"X-Api-Key": self._settings.octen_api_key or ""},
        )

    def to_wire(self, query: OctenQuery) -> dict[str, Any]:
        body: dict[str, Any] = {"query": query.query, "num_results": query.max_results}
        if query.include_domains:
            body["include_domains"] = query.include_domains
        if query.exclude_domains:
            body["exclude_domains"] = query.exclude_domains
        if query.published_after:
            body["start_published_date"] = query.published_after.isoformat()
        if query.require_text:
            body["include_text"] = query.require_text
        if query.extract_content:
            body["contents"] = {"text": {"max_characters": (query.content_token_limit or 1000) * 4}}
        return body

    def from_wire(self, payload: dict[str, Any]) -> list[OctenResult]:
        rows = payload.get("results") or payload.get("data") or []
        out: list[OctenResult] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            url = row.get("url") or row.get("link")
            if not url:
                continue
            out.append(
                OctenResult(
                    url=url,
                    title=row.get("title"),
                    snippet=row.get("snippet") or row.get("summary") or row.get("highlight"),
                    content=row.get("text") or row.get("content"),
                    published_at=_parse_dt(row.get("published_date") or row.get("published_at")),
                    crawled_at=_parse_dt(row.get("crawled_at") or row.get("indexed_at")),
                    raw=row,
                )
            )
        return out

    async def search(self, query: OctenQuery) -> tuple[list[OctenResult], bool]:
        """Returns (results, failed). A failure is a dropped data point, not an exception."""
        backoff = 0.4
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = await self._client.post("/search", json=self.to_wire(query))
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                log.warning("octen transport failure attempt=%s query=%r err=%s", attempt, query.query, exc)
                if attempt == MAX_ATTEMPTS:
                    return [], True
                await asyncio.sleep(backoff)
                backoff *= 2
                continue

            if response.status_code == 429 or response.status_code >= 500:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after and retry_after.isdigit() else backoff
                if attempt == MAX_ATTEMPTS:
                    log.warning("octen gave up status=%s query=%r", response.status_code, query.query)
                    return [], True
                await asyncio.sleep(delay)
                backoff *= 2
                continue

            if response.status_code >= 400:
                log.warning("octen rejected status=%s query=%r", response.status_code, query.query)
                return [], True

            try:
                return self.from_wire(response.json()), False
            except ValueError:
                return [], True
        return [], True

    async def aclose(self) -> None:
        await self._client.aclose()


class LocalIndexClient:
    """Offline stand-in with the same contract, backed by the bundled corpus."""

    transport = "local_index"

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._index = LocalIndex()

    async def search(self, query: OctenQuery) -> tuple[list[OctenResult], bool]:
        started = time.perf_counter()
        results = self._index.search(query)
        if self._settings.simulate_latency:
            # Keeps the concurrency story visible in the demo without a network hop.
            await asyncio.sleep(0.012 + 0.02 * (hash(query.query) % 7) / 7)
        log.debug("local search q=%r hits=%d in %.1fms", query.query, len(results), (time.perf_counter() - started) * 1000)
        return results, False

    async def aclose(self) -> None:
        return None


def build_backend(settings: Settings | None = None) -> SearchBackend:
    settings = settings or get_settings()
    return OctenClient(settings) if settings.octen_enabled else LocalIndexClient(settings)
