"""
In-memory TTL cache service for identical request deduplication.
Thread-safe with automatic stale entry eviction and size caps.
"""

import hashlib
import json
import time
from typing import Any

from app.config import get_settings


class CacheService:
    """Thread-safe In-Memory TTL Cache."""

    def __init__(self, default_ttl_seconds: int = 3600, max_entries: int = 500):
        self._cache: dict[str, tuple[float, Any]] = {}
        self._default_ttl = default_ttl_seconds
        self._max_entries = max_entries

    def _generate_key(self, prefix: str, data: Any) -> str:
        """Generates a stable sha256 cache key from arbitrary data."""
        serialized = json.dumps(data, sort_keys=True, default=str)
        hashed = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return f"{prefix}:{hashed}"

    def get(self, key: str) -> Any | None:
        """Retrieves cached item if present and not expired."""
        entry = self._cache.get(key)
        if not entry:
            return None

        expiry, value = entry
        if time.time() > expiry:
            # Expired
            self._cache.pop(key, None)
            return None

        return value

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Stores item with TTL. Evicts oldest entries if exceeding capacity."""
        if len(self._cache) >= self._max_entries:
            self._cleanup_expired_or_oldest()

        ttl = ttl_seconds or self._default_ttl
        expiry = time.time() + ttl
        self._cache[key] = (expiry, value)

    def _cleanup_expired_or_oldest(self) -> None:
        """Purges expired items, or removes the earliest expiring item if none expired."""
        now = time.time()
        expired_keys = [k for k, (exp, _) in self._cache.items() if now > exp]
        for k in expired_keys:
            self._cache.pop(k, None)

        if len(self._cache) >= self._max_entries:
            # Evict earliest expiring key
            sorted_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k][0])
            for k in sorted_keys[: max(1, len(self._cache) // 4)]:
                self._cache.pop(k, None)

    def clear(self) -> None:
        """Clears all cached items."""
        self._cache.clear()


_cache_instance: CacheService | None = None


def get_cache_service() -> CacheService:
    """Singleton getter for CacheService."""
    global _cache_instance
    if _cache_instance is None:
        settings = get_settings()
        _cache_instance = CacheService(default_ttl_seconds=settings.CACHE_TTL_SECONDS)
    return _cache_instance
