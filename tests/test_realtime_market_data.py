"""Tests for real-time market data interface (Phase 2 Step 17)."""

from __future__ import annotations

import time
from typing import Any

from src.data.realtime_market import RealtimeMarketDataService, RealtimeMarketSnapshot


class FakeMarketFetcher:
    """Simple fake fetcher with queued responses for each channel."""

    def __init__(
        self,
        *,
        ticker_responses: list[Any] | None = None,
        depth_responses: list[Any] | None = None,
        kline_responses: list[Any] | None = None,
    ) -> None:
        self._ticker_responses = list(ticker_responses or [])
        self._depth_responses = list(depth_responses or [])
        self._kline_responses = list(kline_responses or [])

    def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        default = {"symbol": symbol, "last": 50000.0, "bid": 49990.0, "ask": 50010.0}
        return self._consume(self._ticker_responses, default)

    def fetch_order_book(self, symbol: str, limit: int | None = None) -> dict[str, Any]:
        default = {"symbol": symbol, "bids": [[49990.0, 1.0]], "asks": [[50010.0, 1.0]]}
        return self._consume(self._depth_responses, default)

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1m",
        since: int | None = None,
        limit: int | None = None,
    ) -> list[list[Any]]:
        default = [[1700000000000, 49000.0, 51000.0, 48000.0, 50000.0, 12.3]]
        return self._consume(self._kline_responses, default)

    @staticmethod
    def _consume(responses: list[Any], default: Any) -> Any:
        if not responses:
            return default
        value = responses.pop(0)
        if callable(value):
            return value()
        if isinstance(value, Exception):
            raise value
        return value


def test_realtime_interfaces_return_consistent_snapshot_shape() -> None:
    fetcher = FakeMarketFetcher(
        ticker_responses=[
            {
                "symbol": "BTC/USDT",
                "last": 50000.0,
                "bid": 49999.0,
                "ask": 50001.0,
                "timestamp": 1700000000100,
            }
        ],
        depth_responses=[
            {
                "symbol": "BTC/USDT",
                "bids": [[49990.0, 1.2]],
                "asks": [[50010.0, 0.8]],
                "timestamp": 1700000000200,
            }
        ],
        kline_responses=[[[1700000000000, 49000.0, 51000.0, 48000.0, 50000.0, 12.3]]],
    )
    service = RealtimeMarketDataService(fetcher, timeout_seconds=0.05)

    latest = service.get_latest_price("BTC/USDT")
    depth = service.get_depth("BTC/USDT", limit=5)
    kline = service.get_klines("BTC/USDT", timeframe="1m", limit=1)

    expected_keys = set(RealtimeMarketSnapshot.__dataclass_fields__.keys())
    for snapshot in (latest, depth, kline):
        assert set(snapshot.__dict__.keys()) == expected_keys
        assert snapshot.ok is True
        assert snapshot.fallback is False
        assert snapshot.timed_out is False
        assert snapshot.error is None

    assert latest.channel == "latest_price"
    assert depth.channel == "depth"
    assert kline.channel == "kline"
    assert latest.data["last_price"] == 50000.0
    assert depth.data["bids"] == [[49990.0, 1.2]]
    assert len(kline.data["candles"]) == 1


def test_realtime_price_uses_cached_fallback_on_fetch_error() -> None:
    fetcher = FakeMarketFetcher(
        ticker_responses=[
            {"symbol": "BTC/USDT", "last": 51000.0, "bid": 50990.0, "ask": 51010.0},
            RuntimeError("upstream unavailable"),
        ]
    )
    service = RealtimeMarketDataService(fetcher, timeout_seconds=0.05)

    first = service.get_latest_price("BTC/USDT")
    second = service.get_latest_price("BTC/USDT")

    assert first.ok is True
    assert first.fallback is False
    assert second.ok is True
    assert second.fallback is True
    assert second.timed_out is False
    assert second.data == first.data
    assert "RuntimeError: upstream unavailable" in (second.error or "")


def test_realtime_timeout_returns_empty_payload_when_no_cache() -> None:
    fetcher = FakeMarketFetcher(
        ticker_responses=[_delayed_value({"last": 52000.0}, delay_seconds=0.03)]
    )
    service = RealtimeMarketDataService(fetcher, timeout_seconds=0.005)

    snapshot = service.get_latest_price("BTC/USDT")

    assert snapshot.ok is False
    assert snapshot.fallback is False
    assert snapshot.timed_out is True
    assert "timed out" in (snapshot.error or "")
    assert snapshot.data["last_price"] is None
    assert snapshot.data["bid"] is None
    assert snapshot.data["ask"] is None


def test_realtime_kline_timeout_uses_cached_fallback() -> None:
    fetcher = FakeMarketFetcher(
        kline_responses=[
            [[1700000000000, 49000.0, 51000.0, 48000.0, 50000.0, 12.3]],
            _delayed_value(
                [[1700000060000, 49500.0, 51500.0, 48500.0, 50500.0, 11.1]],
                delay_seconds=0.03,
            ),
        ]
    )
    service = RealtimeMarketDataService(fetcher, timeout_seconds=0.005)

    first = service.get_klines("BTC/USDT", timeframe="1m", limit=1)
    second = service.get_klines("BTC/USDT", timeframe="1m", limit=1)

    assert first.ok is True
    assert second.ok is True
    assert second.fallback is True
    assert second.timed_out is True
    assert second.data == first.data


def _delayed_value(value: Any, *, delay_seconds: float) -> Any:
    def _inner() -> Any:
        time.sleep(delay_seconds)
        return value

    return _inner
