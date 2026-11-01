import logging
import time
from collections.abc import Callable

from .store import RateLimitStore

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(
        self,
        provider: str,
        requests_per_minute: int,
        store: RateLimitStore,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ):
        if isinstance(requests_per_minute, bool) or requests_per_minute < 1:
            raise ValueError("Requests per minute must be positive.")
        self._provider = provider
        self._limit = requests_per_minute
        self._store = store
        self._clock = clock
        self._sleep = sleep

    def acquire(self) -> None:
        while True:
            delay = self._store.reserve(self._provider, self._limit, self._clock())
            if delay == 0:
                return
            logger.info("Provider=%s | Rate limit reached | Waiting %.1f s", self._provider, delay)
            self._sleep(min(delay, 60.0))

    def __call__(self, request: object) -> None:
        self.acquire()
