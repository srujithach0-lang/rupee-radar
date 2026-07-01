"""Groq rate limiter for llama-3.3-70b-versatile free-tier quotas."""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import date, datetime, timezone

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GroqQuotaLimits:
    requests_per_minute: int = 30
    tokens_per_minute: int = 1000
    requests_per_day: int = 12000
    tokens_per_day: int = 100000


class GroqRateLimiter:
    """Process-wide sliding-window limiter for Groq API quotas."""

    def __init__(self, limits: GroqQuotaLimits | None = None) -> None:
        self.limits = limits or GroqQuotaLimits()
        self._lock = threading.Lock()
        self._minute_window: deque[tuple[float, int]] = deque()  # (monotonic_ts, total_tokens)
        self._day: date = date.today()
        self._day_requests = 0
        self._day_tokens = 0

    def _reset_day_if_needed(self) -> None:
        today = datetime.now(timezone.utc).date()
        if today != self._day:
            self._day = today
            self._day_requests = 0
            self._day_tokens = 0

    def _prune_minute_window(self, now: float) -> None:
        while self._minute_window and now - self._minute_window[0][0] >= 60.0:
            self._minute_window.popleft()

    def _minute_totals(self, now: float) -> tuple[int, int]:
        self._prune_minute_window(now)
        return len(self._minute_window), sum(tokens for _, tokens in self._minute_window)

    def can_acquire(self, estimated_tokens: int) -> bool:
        """Return True if a request of estimated_tokens may proceed without waiting."""
        with self._lock:
            self._reset_day_if_needed()
            limits = self.limits

            if self._day_requests >= limits.requests_per_day:
                return False
            if self._day_tokens + estimated_tokens > limits.tokens_per_day:
                return False

            now = time.monotonic()
            minute_reqs, minute_tokens = self._minute_totals(now)
            return (
                minute_reqs < limits.requests_per_minute
                and minute_tokens + estimated_tokens <= limits.tokens_per_minute
            )

    def acquire(self, estimated_tokens: int, deadline: float | None = None) -> bool:
        """
        Block until the request fits within per-minute quotas or deadline is reached.
        Returns False immediately if daily limits are exhausted.
        """
        with self._lock:
            while True:
                self._reset_day_if_needed()
                limits = self.limits

                if self._day_requests >= limits.requests_per_day:
                    logger.warning("Groq daily request limit reached (%d)", limits.requests_per_day)
                    return False
                if self._day_tokens + estimated_tokens > limits.tokens_per_day:
                    logger.warning("Groq daily token limit reached (%d)", limits.tokens_per_day)
                    return False

                now = time.monotonic()
                if deadline is not None and now >= deadline:
                    logger.warning("Groq upload time budget exceeded before next request")
                    return False

                minute_reqs, minute_tokens = self._minute_totals(now)
                if (
                    minute_reqs < limits.requests_per_minute
                    and minute_tokens + estimated_tokens <= limits.tokens_per_minute
                ):
                    return True

                if not self._minute_window:
                    return True

                sleep_for = 60.0 - (now - self._minute_window[0][0]) + 0.05
                if deadline is not None:
                    sleep_for = min(sleep_for, max(0.0, deadline - now))
                    if sleep_for <= 0:
                        return False

                logger.info(
                    "Groq rate limit: waiting %.1fs (minute %d/%d req, %d/%d tok)",
                    sleep_for,
                    minute_reqs,
                    limits.requests_per_minute,
                    minute_tokens,
                    limits.tokens_per_minute,
                )
                self._lock.release()
                try:
                    time.sleep(sleep_for)
                finally:
                    self._lock.acquire()

    def record(self, total_tokens: int) -> None:
        with self._lock:
            self._reset_day_if_needed()
            now = time.monotonic()
            self._minute_window.append((now, total_tokens))
            self._day_requests += 1
            self._day_tokens += total_tokens

    def remaining_daily_tokens(self) -> int:
        with self._lock:
            self._reset_day_if_needed()
            return max(0, self.limits.tokens_per_day - self._day_tokens)

    def remaining_daily_requests(self) -> int:
        with self._lock:
            self._reset_day_if_needed()
            return max(0, self.limits.requests_per_day - self._day_requests)


_limiter: GroqRateLimiter | None = None
_limiter_lock = threading.Lock()


def get_rate_limiter(limits: GroqQuotaLimits | None = None) -> GroqRateLimiter:
    """Return the process-wide singleton limiter.

    If ``limits`` is provided and the singleton does not yet exist, it is
    created with those limits.  If the singleton already exists but its limits
    differ from the requested ones, it is **replaced** so that runtime config
    changes (e.g. env-var overrides) are always honoured.
    """
    global _limiter
    with _limiter_lock:
        if _limiter is None:
            _limiter = GroqRateLimiter(limits)
        elif limits is not None and _limiter.limits != limits:
            # Config has changed (e.g. settings reloaded or different tier) —
            # recreate so the correct quotas are enforced.
            _limiter = GroqRateLimiter(limits)
        return _limiter


def reset_rate_limiter_for_tests() -> None:
    """Reset singleton limiter (tests only)."""
    global _limiter
    with _limiter_lock:
        _limiter = None


def estimate_tokens(*parts: str) -> int:
    """Rough token estimate (~4 chars/token) with small JSON overhead."""
    text_tokens = sum(max(1, len(part) // 4) for part in parts if part)
    return text_tokens + 16
