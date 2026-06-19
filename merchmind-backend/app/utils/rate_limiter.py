"""
Token-bucket rate limiter for external API calls (Shopify, Printify, etc.).
"""
import time
import threading
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TokenBucket:
    """Thread-safe token bucket for rate limiting."""

    def __init__(self, rate: float, capacity: float):
        """
        Args:
            rate: Tokens added per second.
            capacity: Maximum tokens in bucket.
        """
        self._rate = rate
        self._capacity = capacity
        self._tokens = capacity
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
        self._last_refill = now

    def acquire(self, tokens: float = 1.0, timeout: Optional[float] = 30.0) -> bool:
        """
        Block until tokens are available or timeout expires.
        Returns True if acquired, False if timed out.
        """
        deadline = time.monotonic() + (timeout or float("inf"))
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                logger.warning(f"Rate limiter timed out waiting for {tokens} token(s)")
                return False
            time.sleep(min(0.05, remaining))

    def consume(self, tokens: float = 1.0) -> None:
        """Blocking acquire that raises on timeout."""
        if not self.acquire(tokens):
            raise TimeoutError(f"Rate limiter: could not acquire {tokens} token(s) within timeout")


# Pre-built limiters for external services
shopify_limiter = TokenBucket(rate=2.0, capacity=2.0)     # 2 calls/second
printify_limiter = TokenBucket(rate=5.0, capacity=5.0)    # 5 calls/second
openai_limiter = TokenBucket(rate=3.0, capacity=3.0)      # 3 calls/second
replicate_limiter = TokenBucket(rate=2.0, capacity=2.0)   # 2 calls/second
