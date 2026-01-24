from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


@dataclass
class CacheEntry:
    data: Any
    timestamp: datetime


class TTLCache:
    def __init__(self, ttl_minutes: int = 5):
        self._cache: dict[str, CacheEntry] = {}
        self._ttl = timedelta(minutes=ttl_minutes)

    def get(self, key: str) -> Any | None:
        if entry := self._cache.get(key):
            if datetime.now() - entry.timestamp < self._ttl:
                return entry.data
            del self._cache[key]
        return None

    def set(self, key: str, data: Any) -> None:
        self._cache[key] = CacheEntry(data, datetime.now())

    def clear(self) -> None:
        self._cache.clear()


pr_cache = TTLCache(ttl_minutes=5)
branch_cache = TTLCache(ttl_minutes=2)
commit_cache = TTLCache(ttl_minutes=5)
workflow_cache = TTLCache(ttl_minutes=5)
