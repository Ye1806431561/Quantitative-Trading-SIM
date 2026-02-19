"""Real-time market data interfaces with timeout guards and fallback payloads."""

from __future__ import annotations

import copy
import queue
import threading
import time
from typing import Any, Callable, Mapping

from src.data.market import MarketDataFetcher
from src.data.market_policy import MarketDataConfigError
from src.data.realtime_payloads import (
    RealtimeMarketSnapshot,
    normalize_ohlcv_payload,
    normalize_order_book_payload,
    normalize_ticker_payload,
)

DEFAULT_TIMEOUT_SECONDS = 2.0


class RealtimeMarketDataService:
    """Read latest market views with timeout and graceful fallback behavior."""

    def __init__(
        self,
        fetcher: MarketDataFetcher,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        now_ms_fn: Callable[[], int] | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise MarketDataConfigError("timeout_seconds must be > 0")
        self._fetcher = fetcher
        self._timeout_seconds = float(timeout_seconds)
        self._now_ms_fn = now_ms_fn or (lambda: int(time.time() * 1000))
        self._fallback_cache: dict[str, dict[str, Any]] = {}
        self._cache_lock = threading.Lock()

    @classmethod
    def from_config(
        cls,
        config: Mapping[str, Any],
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        fetcher_factory: Callable[[Mapping[str, Any]], MarketDataFetcher] = MarketDataFetcher.from_config,
    ) -> "RealtimeMarketDataService":
        return cls(
            fetcher=fetcher_factory(config),
            timeout_seconds=timeout_seconds,
        )

    def get_latest_price(self, symbol: str) -> RealtimeMarketSnapshot:
        cache_key = f"price:{symbol.strip()}"
        empty_payload = {
            "last_price": None,
            "bid": None,
            "ask": None,
            "exchange_timestamp": None,
        }
        return self._request(
            channel="latest_price",
            symbol=symbol,
            cache_key=cache_key,
            empty_payload=empty_payload,
            call=lambda: self._fetcher.fetch_ticker(symbol),
            normalize=normalize_ticker_payload,
        )

    def get_depth(self, symbol: str, *, limit: int | None = None) -> RealtimeMarketSnapshot:
        cache_key = f"depth:{symbol.strip()}:{limit if limit is not None else 'default'}"
        empty_payload = {
            "limit": limit,
            "bids": [],
            "asks": [],
            "exchange_timestamp": None,
        }
        return self._request(
            channel="depth",
            symbol=symbol,
            cache_key=cache_key,
            empty_payload=empty_payload,
            call=lambda: self._fetcher.fetch_order_book(symbol, limit=limit),
            normalize=lambda payload: normalize_order_book_payload(payload, limit=limit),
        )

    def get_klines(
        self,
        symbol: str,
        *,
        timeframe: str,
        since: int | None = None,
        limit: int | None = 1,
    ) -> RealtimeMarketSnapshot:
        if not timeframe or not timeframe.strip():
            raise MarketDataConfigError("timeframe must not be empty")
        normalized_timeframe = timeframe.strip()
        normalized_limit = 1 if limit is None else limit
        cache_key = f"kline:{symbol.strip()}:{normalized_timeframe}:{normalized_limit}"
        empty_payload = {
            "timeframe": normalized_timeframe,
            "candles": [],
        }
        return self._request(
            channel="kline",
            symbol=symbol,
            cache_key=cache_key,
            empty_payload=empty_payload,
            call=lambda: self._fetcher.fetch_ohlcv(
                symbol,
                timeframe=normalized_timeframe,
                since=since,
                limit=normalized_limit,
            ),
            normalize=lambda payload: normalize_ohlcv_payload(payload, timeframe=normalized_timeframe),
        )

    def _request(
        self,
        *,
        channel: str,
        symbol: str,
        cache_key: str,
        empty_payload: dict[str, Any],
        call: Callable[[], Any],
        normalize: Callable[[Any], dict[str, Any]],
    ) -> RealtimeMarketSnapshot:
        try:
            payload = self._run_with_timeout(channel=channel, call=call)
            data = normalize(payload)
            self._set_cache(cache_key, data)
            return self._build_snapshot(
                channel=channel,
                symbol=symbol,
                ok=True,
                fallback=False,
                timed_out=False,
                error=None,
                data=data,
            )
        except TimeoutError as exc:
            return self._fallback_snapshot(
                channel=channel,
                symbol=symbol,
                cache_key=cache_key,
                timed_out=True,
                error=str(exc),
                empty_payload=empty_payload,
            )
        except Exception as exc:
            return self._fallback_snapshot(
                channel=channel,
                symbol=symbol,
                cache_key=cache_key,
                timed_out=False,
                error=f"{exc.__class__.__name__}: {exc}",
                empty_payload=empty_payload,
            )

    def _run_with_timeout(self, *, channel: str, call: Callable[[], Any]) -> Any:
        result_queue: queue.Queue[tuple[bool, Any]] = queue.Queue(maxsize=1)

        def runner() -> None:
            try:
                result_queue.put((True, call()))
            except Exception as exc:  # pragma: no cover - hit via parent tests.
                result_queue.put((False, exc))

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()

        try:
            success, payload = result_queue.get(timeout=self._timeout_seconds)
        except queue.Empty as exc:
            raise TimeoutError(
                f"{channel} request timed out after {self._timeout_seconds:.3f}s"
            ) from exc

        if success:
            return payload
        if isinstance(payload, Exception):
            raise payload
        raise RuntimeError(f"{channel} request failed with unknown error")

    def _fallback_snapshot(
        self,
        *,
        channel: str,
        symbol: str,
        cache_key: str,
        timed_out: bool,
        error: str,
        empty_payload: dict[str, Any],
    ) -> RealtimeMarketSnapshot:
        cached = self._get_cache(cache_key)
        if cached is not None:
            return self._build_snapshot(
                channel=channel,
                symbol=symbol,
                ok=True,
                fallback=True,
                timed_out=timed_out,
                error=error,
                data=cached,
            )
        return self._build_snapshot(
            channel=channel,
            symbol=symbol,
            ok=False,
            fallback=False,
            timed_out=timed_out,
            error=error,
            data=copy.deepcopy(empty_payload),
        )

    def _build_snapshot(
        self,
        *,
        channel: str,
        symbol: str,
        ok: bool,
        fallback: bool,
        timed_out: bool,
        error: str | None,
        data: dict[str, Any],
    ) -> RealtimeMarketSnapshot:
        return RealtimeMarketSnapshot(
            channel=channel,
            symbol=symbol.strip(),
            ok=ok,
            fallback=fallback,
            timed_out=timed_out,
            error=error,
            fetched_at_ms=self._now_ms_fn(),
            data=copy.deepcopy(data),
        )

    def _set_cache(self, key: str, payload: dict[str, Any]) -> None:
        with self._cache_lock:
            self._fallback_cache[key] = copy.deepcopy(payload)

    def _get_cache(self, key: str) -> dict[str, Any] | None:
        with self._cache_lock:
            payload = self._fallback_cache.get(key)
            return copy.deepcopy(payload) if payload is not None else None
