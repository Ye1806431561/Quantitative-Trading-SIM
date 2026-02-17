"""Market data interfaces with exchange selection, rate limiting, and retries."""

from __future__ import annotations

import time
from typing import Any, Callable, Mapping, Protocol

try:
    import ccxt
except Exception:  # pragma: no cover - runtime/config checks handle this path.
    ccxt = None  # type: ignore[assignment]

from src.data.market_policy import (
    MarketDataConfigError,
    MarketDataFetchError,
    RUNTIME_WRITE_TARGET,
    RetryPolicy,
    read_exchange_settings,
    read_retry_policy,
    read_runtime_write_target,
    validate_runtime_write_target,
    validate_symbol,
)
from src.data.market_retry import RequestRateLimiter, is_rate_limit_error, is_retryable_error


class ExchangeClient(Protocol):
    """Protocol for CCXT-compatible exchange clients."""

    rateLimit: int | float

    def fetch_ticker(self, symbol: str) -> Mapping[str, Any]:
        ...

    def fetch_order_book(self, symbol: str, limit: int | None = None) -> Mapping[str, Any]:
        ...

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1m",
        since: int | None = None,
        limit: int | None = None,
    ) -> list[list[Any]]:
        ...


def create_exchange_client(
    exchange_name: str,
    *,
    testnet: bool,
    enable_rate_limit: bool,
    api_key: str = "",
    api_secret: str = "",
) -> ExchangeClient:
    """Build a CCXT exchange client from config values."""
    if ccxt is None:
        raise MarketDataConfigError("ccxt is not installed; cannot create exchange client")

    exchange_class = getattr(ccxt, exchange_name, None)
    if exchange_class is None or not callable(exchange_class):
        raise MarketDataConfigError(f"unsupported exchange: {exchange_name}")

    params: dict[str, Any] = {"enableRateLimit": enable_rate_limit}
    if api_key:
        params["apiKey"] = api_key
    if api_secret:
        params["secret"] = api_secret

    exchange = exchange_class(params)
    if testnet and hasattr(exchange, "set_sandbox_mode"):
        exchange.set_sandbox_mode(True)
    return exchange


class MarketDataFetcher:
    """Fetch market data with retry and failure-notification behavior."""

    def __init__(
        self,
        exchange: ExchangeClient,
        *,
        retry_policy: RetryPolicy | None = None,
        runtime_write_target: str = RUNTIME_WRITE_TARGET,
        rate_limiter: RequestRateLimiter | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._exchange = exchange
        self._retry_policy = retry_policy or RetryPolicy()
        self._runtime_write_target = validate_runtime_write_target(runtime_write_target)
        self._rate_limiter = rate_limiter or RequestRateLimiter(
            enabled=True,
            min_interval_ms=float(getattr(exchange, "rateLimit", 0) or 0.0),
        )
        self._sleep_fn = sleep_fn

    @classmethod
    def from_config(
        cls,
        config: Mapping[str, Any],
        *,
        exchange_factory: Callable[..., ExchangeClient] = create_exchange_client,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> "MarketDataFetcher":
        settings = read_exchange_settings(config)
        retry_policy = read_retry_policy(config)
        runtime_write_target = read_runtime_write_target(config)

        exchange = exchange_factory(
            settings.name,
            testnet=settings.testnet,
            enable_rate_limit=settings.enable_rate_limit,
            api_key=settings.api_key,
            api_secret=settings.api_secret,
        )
        rate_limiter = RequestRateLimiter(
            enabled=settings.enable_rate_limit,
            min_interval_ms=float(getattr(exchange, "rateLimit", 0) or 0.0),
        )
        return cls(
            exchange=exchange,
            retry_policy=retry_policy,
            runtime_write_target=runtime_write_target,
            rate_limiter=rate_limiter,
            sleep_fn=sleep_fn,
        )

    @classmethod
    def from_exchange(
        cls,
        exchange: ExchangeClient,
        *,
        retry_policy: RetryPolicy | None = None,
        enable_rate_limit: bool = True,
        runtime_write_target: str = RUNTIME_WRITE_TARGET,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> "MarketDataFetcher":
        rate_limiter = RequestRateLimiter(
            enabled=enable_rate_limit,
            min_interval_ms=float(getattr(exchange, "rateLimit", 0) or 0.0),
        )
        return cls(
            exchange=exchange,
            retry_policy=retry_policy,
            runtime_write_target=runtime_write_target,
            rate_limiter=rate_limiter,
            sleep_fn=sleep_fn,
        )

    @property
    def runtime_write_target(self) -> str:
        return self._runtime_write_target

    def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        validate_symbol(symbol)
        payload = self._request("fetch_ticker", symbol=symbol.strip())
        return dict(payload)

    def fetch_order_book(self, symbol: str, limit: int | None = None) -> dict[str, Any]:
        validate_symbol(symbol)
        payload = self._request("fetch_order_book", symbol=symbol.strip(), limit=limit)
        return dict(payload)

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since: int | None = None,
        limit: int | None = None,
    ) -> list[list[Any]]:
        validate_symbol(symbol)
        if not timeframe or not timeframe.strip():
            raise MarketDataConfigError("timeframe must not be empty")
        payload = self._request(
            "fetch_ohlcv",
            symbol=symbol.strip(),
            timeframe=timeframe.strip(),
            since=since,
            limit=limit,
        )
        return [list(item) for item in payload]

    def _request(self, method_name: str, **kwargs: Any) -> Any:
        method = getattr(self._exchange, method_name)
        delay = self._retry_policy.initial_delay_seconds

        for attempt in range(1, self._retry_policy.max_attempts + 1):
            self._rate_limiter.wait()
            try:
                return method(**kwargs)
            except Exception as exc:
                retryable = is_retryable_error(exc)
                final_attempt = attempt >= self._retry_policy.max_attempts
                if not retryable or final_attempt:
                    reason = "non-retryable" if not retryable else "retry limit reached"
                    raise MarketDataFetchError(
                        f"{method_name} failed after {attempt} attempt(s): "
                        f"{exc.__class__.__name__}: {exc} ({reason})"
                    ) from exc
                self._sleep_fn(self._next_delay(delay, exc))
                delay = min(
                    delay * self._retry_policy.backoff_multiplier,
                    self._retry_policy.max_delay_seconds,
                )

        raise MarketDataFetchError(f"{method_name} failed unexpectedly")

    def _next_delay(self, delay: float, error: Exception) -> float:
        if is_rate_limit_error(error):
            return min(
                max(delay, self._rate_limiter.min_interval_seconds),
                self._retry_policy.max_delay_seconds,
            )
        return min(delay, self._retry_policy.max_delay_seconds)
