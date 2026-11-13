"""Cache for successful AI results only.

The cache key is the context fingerprint combined with the requested operation,
so a new dataset, a new report date or any changed calculation value produces a
new key and the previous answer is ignored.

Failures are never stored. ``get`` returns ``None`` for a missing key, and
``put`` is only ever called after a response has been validated.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from typing import Any

DEFAULT_MAX_ENTRIES = 64


class AICache:
    """A small bounded LRU cache keyed by fingerprint and operation."""

    def __init__(self, max_entries: int = DEFAULT_MAX_ENTRIES) -> None:
        if max_entries < 1:
            raise ValueError("AICache requires at least one entry.")
        self._max_entries = int(max_entries)
        self._entries: OrderedDict[str, Any] = OrderedDict()
        self.hits = 0
        self.misses = 0

    @staticmethod
    def make_key(fingerprint: str, operation: str, **extra: Any) -> str:
        parts = [fingerprint, operation]
        for name in sorted(extra):
            parts.append(f"{name}={extra[name]}")
        return "|".join(str(part) for part in parts)

    def get(self, key: str) -> Any | None:
        if key not in self._entries:
            self.misses += 1
            return None
        self.hits += 1
        self._entries.move_to_end(key)
        return self._entries[key]

    def put(self, key: str, value: Any) -> None:
        self._entries[key] = value
        self._entries.move_to_end(key)
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)

    def invalidate(self, key: str) -> None:
        self._entries.pop(key, None)

    def clear(self) -> None:
        self._entries.clear()
        self.hits = 0
        self.misses = 0

    def __len__(self) -> int:
        return len(self._entries)

    def __contains__(self, key: str) -> bool:
        return key in self._entries

    def get_or_create(self, key: str, factory: Callable[[], Any]) -> Any:
        """Return the cached value, or build and store one.

        ``factory`` is only called on a miss. If it raises, nothing is stored,
        so a failed call is retried by the next request instead of being served
        from the cache forever.
        """

        cached = self.get(key)
        if cached is not None:
            return cached
        value = factory()
        self.put(key, value)
        return value


_SHARED_CACHE = AICache()


def default_cache() -> AICache:
    """Return the process-wide cache used by the Streamlit UI."""

    return _SHARED_CACHE
