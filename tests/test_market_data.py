"""Tests for market data interfaces (Phase 1 Step 14)."""

from __future__ import annotations

from typing import Any

import pytest

from src.data.market import MarketDataFetcher
from src.data.market_policy import (
    MarketDataConfigError,
    MarketDataFetchError,
    RUNTIME_WRITE_TARGET,
    RetryPolicy,
)
from src.data.market_retry import RequestRateLimiter


class RateLimitExceeded(Exception):
    """Simulated transient rate-limit error."""


class NetworkError(Exception):
    """Simulated transient network error."""


class AuthenticationError(Exception):
    """Simulated non-retryable auth error."""


class FakeExchange:
    """Simple CCXT-like fake exchange for retry/rate-limit tests."""

    def __init__(self, ticker_responses: list[Any], rate_limit_ms: int = 0) -> None:
        self.rateLimit = rate_limit_ms
        self._ticker_responses = list(ticker_responses)
        self.ticker_calls = 0

    def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        self.ticker_calls += 1
        if not self._ticker_responses:
            return {"symbol": symbol, "last": 0.0}
        payload = self._ticker_responses.pop(0)
        if isinstance(payload, Exception):
            raise payload
        return payload

    def fetch_order_book(self, symbol: str, limit: int | None = None) -> dict[str, Any]:
        return {"symbol": symbol, "limit": limit, "bids": [], "asks": []}

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1m",
        since: int | None = None,
        limit: int | None = None,
    ) -> list[list[Any]]:
        return [[1, 2, 3, 4, 5, 6]]


def test_from_config_selects_exchange() -> None:
    captured: dict[str, Any] = {}

    def fake_factory(exchange_name: str, **kwargs: Any) -> FakeExchange:
        captured["exchange_name"] = exchange_name
        captured.update(kwargs)
        return FakeExchange([{"symbol": "BTC/USDT", "last": 50000.0}], rate_limit_ms=200)

    config = {
        "exchange": {
            "name": "okx",
            "testnet": True,
            "rate_limit": False,
            "api_key": "k",
            "api_secret": "s",
        }
    }
    fetcher = MarketDataFetcher.from_config(config, exchange_factory=fake_factory)

    assert captured["exchange_name"] == "okx"
    assert captured["testnet"] is True
    assert captured["enable_rate_limit"] is False
    assert fetcher.runtime_write_target == RUNTIME_WRITE_TARGET


def test_fetch_ticker_retries_on_rate_limit_then_succeeds() -> None:
    exchange = FakeExchange(
        ticker_responses=[
            RateLimitExceeded("too many requests"),
            {"symbol": "BTC/USDT", "last": 50000.0},
        ],
        rate_limit_ms=200,
    )
    sleeps: list[float] = []
    fetcher = MarketDataFetcher.from_exchange(
        exchange,
        retry_policy=RetryPolicy(max_attempts=3, initial_delay_seconds=0.2),
        enable_rate_limit=False,
        runtime_write_target=RUNTIME_WRITE_TARGET,
        sleep_fn=sleeps.append,
    )

    ticker = fetcher.fetch_ticker("BTC/USDT")

    assert ticker["last"] == 50000.0
    assert exchange.ticker_calls == 2
    assert sleeps == [0.2]


def test_fetch_ticker_fails_after_retry_limit() -> None:
    exchange = FakeExchange(
        ticker_responses=[
            NetworkError("timeout-1"),
            NetworkError("timeout-2"),
            NetworkError("timeout-3"),
        ]
    )
    sleeps: list[float] = []
    fetcher = MarketDataFetcher.from_exchange(
        exchange,
        retry_policy=RetryPolicy(max_attempts=3, initial_delay_seconds=0.1),
        runtime_write_target=RUNTIME_WRITE_TARGET,
        sleep_fn=sleeps.append,
    )

    with pytest.raises(MarketDataFetchError, match="retry limit reached"):
        fetcher.fetch_ticker("BTC/USDT")

    assert exchange.ticker_calls == 3
    assert len(sleeps) == 2


def test_fetch_ticker_fails_fast_on_non_retryable_error() -> None:
    exchange = FakeExchange(ticker_responses=[AuthenticationError("bad api key")])
    sleeps: list[float] = []
    fetcher = MarketDataFetcher.from_exchange(
        exchange,
        retry_policy=RetryPolicy(max_attempts=3, initial_delay_seconds=0.1),
        runtime_write_target=RUNTIME_WRITE_TARGET,
        sleep_fn=sleeps.append,
    )

    with pytest.raises(MarketDataFetchError, match="non-retryable"):
        fetcher.fetch_ticker("BTC/USDT")

    assert exchange.ticker_calls == 1
    assert sleeps == []


def test_rate_limiter_waits_between_requests() -> None:
    timeline = {"now": 0.0}
    sleeps: list[float] = []

    def time_fn() -> float:
        return timeline["now"]

    def sleep_fn(seconds: float) -> None:
        sleeps.append(seconds)
        timeline["now"] += seconds

    limiter = RequestRateLimiter(
        enabled=True,
        min_interval_ms=500,
        time_fn=time_fn,
        sleep_fn=sleep_fn,
    )
    exchange = FakeExchange(
        ticker_responses=[
            {"symbol": "BTC/USDT", "last": 50000.0},
            {"symbol": "BTC/USDT", "last": 50010.0},
        ],
        rate_limit_ms=500,
    )
    fetcher = MarketDataFetcher(
        exchange,
        retry_policy=RetryPolicy(),
        runtime_write_target=RUNTIME_WRITE_TARGET,
        rate_limiter=limiter,
    )

    fetcher.fetch_ticker("BTC/USDT")
    fetcher.fetch_ticker("BTC/USDT")

    assert sleeps == [0.5]


def test_runtime_write_target_rejects_csv() -> None:
    config = {
        "exchange": {"name": "binance", "testnet": True, "rate_limit": True},
        "market_data": {"runtime_write_target": "csv"},
    }

    def fake_factory(exchange_name: str, **kwargs: Any) -> FakeExchange:
        return FakeExchange([{"symbol": "BTC/USDT", "last": 50000.0}])

    with pytest.raises(MarketDataConfigError, match="sqlite"):
        MarketDataFetcher.from_config(config, exchange_factory=fake_factory)
