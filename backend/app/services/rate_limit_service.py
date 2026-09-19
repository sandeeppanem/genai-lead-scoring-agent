from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict


class PublicRateLimitService:
    """Small process-local guard for anonymous state-changing/demo requests."""

    def __init__(self) -> None:
        self.limit = max(1, int(os.getenv("PUBLIC_WRITE_RATE_LIMIT", "30")))
        self.window_seconds = 60.0
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.RLock()

    def allow(self, client_key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            timestamps = self._requests[client_key]
            while timestamps and now - timestamps[0] >= self.window_seconds:
                timestamps.popleft()
            if len(timestamps) >= self.limit:
                return False
            timestamps.append(now)
            if len(self._requests) > 1000:
                self._requests = {
                    key: values
                    for key, values in self._requests.items()
                    if values and now - values[-1] < self.window_seconds
                }
            return True
