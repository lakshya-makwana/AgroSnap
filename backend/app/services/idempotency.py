"""In-memory idempotency cache (API.md: same key + same image -> cached response for 10 minutes).

Single-process only. Move to Redis/PostgreSQL before running more than one API worker.
"""

import threading
import time
from typing import Any


class IdempotencyCache:
    def __init__(self, ttl_sec: int, max_items: int = 5000):
        self.ttl, self.max_items = ttl_sec, max_items
        self._items: dict[str, tuple[float, str, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> tuple[str, Any] | None:
        with self._lock:
            item = self._items.get(key)
            if not item:
                return None
            ts, image_hash, response = item
            if time.monotonic() - ts > self.ttl:
                del self._items[key]
                return None
            return image_hash, response

    def put(self, key: str, image_hash: str, response: Any) -> None:
        with self._lock:
            if len(self._items) >= self.max_items:
                now = time.monotonic()
                self._items = {k: v for k, v in self._items.items() if now - v[0] <= self.ttl}
                while len(self._items) >= self.max_items:
                    self._items.pop(next(iter(self._items)))
            self._items[key] = (time.monotonic(), image_hash, response)
