from __future__ import annotations

import hashlib
import time

from ..models import OctenQuery, OctenResult


class TTLCache:
    """In-memory retrieval cache keyed by the full query object (BACKEND_SPEC §5.4)."""

    def __init__(self, ttl_s: int = 900, max_entries: int = 4096) -> None:
        self._ttl = ttl_s
        self._max = max_entries
        self._store: dict[str, tuple[float, list[OctenResult]]] = {}
        self.hits = 0
        self.misses = 0

    @staticmethod
    def key_for(query: OctenQuery) -> str:
        return hashlib.sha256(query.cache_key().encode()).hexdigest()

    def get(self, query: OctenQuery) -> list[OctenResult] | None:
        key = self.key_for(query)
        entry = self._store.get(key)
        if not entry:
            self.misses += 1
            return None
        expires_at, results = entry
        if expires_at < time.time():
            del self._store[key]
            self.misses += 1
            return None
        self.hits += 1
        return results

    def put(self, query: OctenQuery, results: list[OctenResult]) -> None:
        if len(self._store) >= self._max:
            oldest = min(self._store.items(), key=lambda kv: kv[1][0])[0]
            del self._store[oldest]
        self._store[self.key_for(query)] = (time.time() + self._ttl, results)

    def clear(self) -> None:
        self._store.clear()
        self.hits = 0
        self.misses = 0
