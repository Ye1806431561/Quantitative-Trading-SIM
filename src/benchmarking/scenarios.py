"""Benchmark scenarios and deterministic fixture builders (Phase 4 Step 40)."""

from __future__ import annotations

import random
import time
from collections.abc import Iterable, Mapping
from typing import Any

import backtrader as bt

from src.core.database import SQLiteDatabase
from src.data.realtime_payloads import RealtimeMarketSnapshot
from src.strategies.base import LiveStrategy, StrategyContext


def generate_one_year_hourly_candles(
    *,
    symbol: str,
    timeframe: str,
    seed: int,
    start_timestamp_ms: int = 1_704_067_200_000,  # 2024-01-01 00:00:00 UTC
) -> list[tuple[str, str, int, float, float, float, float, float]]:
    """Generate deterministic 1-year 1h candles for backtest benchmark."""
    hours = 24 * 365
    rng = random.Random(seed)
    price = 100.0
    rows: list[tuple[str, str, int, float, float, float, float, float]] = []

    for idx in range(hours):
        timestamp = start_timestamp_ms + idx * 3_600_000

        drift = 0.0002
        shock = rng.uniform(-0.01, 0.01)
        close = max(1.0, price * (1.0 + drift + shock))

        intraday_noise = abs(rng.uniform(0.001, 0.008))
        high = max(close, price) * (1.0 + intraday_noise)
        low = min(close, price) * (1.0 - intraday_noise)
        volume = 100.0 + rng.uniform(0.0, 50.0)

        rows.append(
            (
                symbol,
                timeframe,
                timestamp,
                float(price),
                float(high),
                float(low),
                float(close),
                float(volume),
            )
        )
        price = close

    return rows


def seed_candles(
    database: SQLiteDatabase,
    rows: Iterable[tuple[str, str, int, float, float, float, float, float]],
) -> int:
    """Insert generated candles into SQLite and return inserted row count."""
    payload = list(rows)
    if not payload:
        return 0
    with database.transaction() as tx:
        before = tx.total_changes
        tx.executemany(
            """
            INSERT INTO candles(symbol, timeframe, timestamp, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            payload,
        )
        return tx.total_changes - before


class BenchmarkMarketReader:
    """Deterministic fake market reader used by realtime/order benchmarks."""

    def __init__(
        self,
        *,
        symbol: str,
        seed: int,
        start_price: float = 100.0,
    ) -> None:
        self._symbol = symbol
        self._rng = random.Random(seed)
        self._price = float(start_price)
        self._fetched_at_ms = int(time.time() * 1000)

    def get_latest_price(self, symbol: str) -> RealtimeMarketSnapshot:
        self._fetched_at_ms += 1000
        movement = self._rng.uniform(-0.002, 0.002)
        self._price = max(1.0, self._price * (1.0 + movement))

        return RealtimeMarketSnapshot(
            channel="latest_price",
            symbol=symbol or self._symbol,
            ok=True,
            fallback=False,
            timed_out=False,
            error=None,
            fetched_at_ms=self._fetched_at_ms,
            data={
                "last_price": float(self._price),
                "bid": float(self._price - 0.05),
                "ask": float(self._price + 0.05),
            },
        )

    def get_klines(self, symbol: str, timeframe: str, limit: int = 1) -> RealtimeMarketSnapshot:
        return RealtimeMarketSnapshot(
            channel="kline",
            symbol=symbol or self._symbol,
            ok=True,
            fallback=False,
            timed_out=False,
            error=None,
            fetched_at_ms=self._fetched_at_ms,
            data={"timeframe": timeframe, "candles": []},
        )


class BenchmarkLoopMonitor:
    """Lightweight monitor that captures one monotonic timestamp per loop iteration."""

    def __init__(self) -> None:
        self._iteration_started_by_index: dict[int, int] = {}
        self._iteration_durations_ns: list[int] = []

    @property
    def iteration_durations_ns(self) -> list[int]:
        return list(self._iteration_durations_ns)

    def mark_started(self, *, strategy_name: str, symbol: str, timeframe: str) -> None:
        _ = (strategy_name, symbol, timeframe)

    def mark_iteration(self, *, iteration_count: int, timestamp_ms: int) -> None:
        _ = (iteration_count, timestamp_ms)
        return None

    def mark_iteration_started(self, *, iteration_count: int, started_at_ns: int) -> None:
        self._iteration_started_by_index[int(iteration_count)] = int(started_at_ns)

    def mark_iteration_finished(self, *, iteration_count: int, ended_at_ns: int) -> None:
        started_at_ns = self._iteration_started_by_index.pop(int(iteration_count), None)
        if started_at_ns is None:
            return None
        self._iteration_durations_ns.append(max(0, int(ended_at_ns) - started_at_ns))
        return None

    def record_account_change(
        self,
        *,
        base_currency: str,
        total_assets: float,
        base_cash: float,
        positions_value: float,
    ) -> None:
        _ = (base_currency, total_assets, base_cash, positions_value)

    def record_network_issue(self, *, message: str, reconnect_attempted: bool) -> None:
        _ = (message, reconnect_attempted)

    def record_strategy_error(self, *, stage: str, error: Exception) -> None:
        _ = (stage, error)

    def record_alert(
        self,
        *,
        level: str,
        category: str,
        message: str,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        _ = (level, category, message, details)

    def mark_stopped(self, *, reason: str | None = None) -> None:
        _ = reason


class SilentLiveStrategy(LiveStrategy):
    """No-op strategy for realtime benchmark to minimize signal-side noise."""

    def __init__(self) -> None:
        super().__init__("silent_live")

    def on_initialize(self, context: StrategyContext) -> None:
        return None

    def on_run(self, market_data: Mapping[str, Any]) -> Mapping[str, Any] | None:
        _ = market_data
        return None

    def on_stop(self, reason: str | None) -> None:
        _ = reason
        return None


class SilentBacktestStrategy(bt.Strategy):
    """No-op Backtrader strategy for optional benchmark fallback."""

    def next(self) -> None:
        return None
