"""Retry and local rate-limiting primitives for market data requests."""

from __future__ import annotations

import time
from typing import Callable

try:
    import ccxt
except Exception:  # pragma: no cover - runtime/config checks handle this path.
    ccxt = None  # type: ignore[assignment]

_RATE_LIMIT_ERROR_NAMES = {"RateLimitExceeded", "DDoSProtection"}
_RETRYABLE_ERROR_NAMES = {
    "NetworkError",
    "ExchangeNotAvailable",
    "RequestTimeout",
}
_NON_RETRYABLE_ERROR_NAMES = {
    "AuthenticationError",
    "PermissionDenied",
    "BadRequest",
    "BadSymbol",
    "InvalidOrder",
}


class RequestRateLimiter:
    """Simple local limiter used on top of exchange client settings."""

    def __init__(
        self,
        enabled: bool,
        min_interval_ms: float,
        time_fn: Callable[[], float] = time.monotonic,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._enabled = enabled and min_interval_ms > 0
        self._min_interval_seconds = max(min_interval_ms, 0.0) / 1000.0
        self._time_fn = time_fn
        self._sleep_fn = sleep_fn
        self._last_request_at: float | None = None

    @property
    def min_interval_seconds(self) -> float:
        return self._min_interval_seconds

    def wait(self) -> None:
        if not self._enabled:
            return
        now = self._time_fn()
        if self._last_request_at is None:
            self._last_request_at = now
            return
        elapsed = now - self._last_request_at
        if elapsed < self._min_interval_seconds:
            self._sleep_fn(self._min_interval_seconds - elapsed)
        self._last_request_at = self._time_fn()


def is_rate_limit_error(error: Exception) -> bool:
    if error.__class__.__name__ in _RATE_LIMIT_ERROR_NAMES:
        return True
    if ccxt is None:
        return False
    return isinstance(error, tuple(_ccxt_types("RateLimitExceeded", "DDoSProtection")))


def is_retryable_error(error: Exception) -> bool:
    error_name = error.__class__.__name__
    if error_name in _NON_RETRYABLE_ERROR_NAMES:
        return False
    if error_name in _RETRYABLE_ERROR_NAMES or is_rate_limit_error(error):
        return True
    if ccxt is None:
        return False
    return isinstance(error, tuple(_ccxt_types("NetworkError", "ExchangeNotAvailable", "RequestTimeout")))


def _ccxt_types(*names: str) -> list[type[Exception]]:
    assert ccxt is not None
    return [exc for exc in (getattr(ccxt, name, None) for name in names) if isinstance(exc, type)]
