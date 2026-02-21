"""Realtime candle persistence bucket/aggregation tests."""

from __future__ import annotations

from typing import Any

from src.core.account_service import AccountService
from src.core.database import SQLiteDatabase
from src.core.order_service import OrderService
from src.core.trade_service import TradeService
from src.data.realtime_payloads import RealtimeMarketSnapshot
from src.data.storage import HistoricalCandleStorage
from src.live.price_service import PriceService
from src.live.realtime_loop import RealtimeLoopConfig, RealtimeSimulationLoop
from src.strategies.base import LiveStrategy, StrategyContext


class _NoopStrategy(LiveStrategy):
    def __init__(self) -> None:
        super().__init__("noop")

    def on_initialize(self, context: StrategyContext) -> None:
        return None

    def on_run(self, market_data: dict[str, Any]) -> dict[str, Any] | None:
        return None

    def on_stop(self, reason: str | None) -> None:
        return None


class _DummyMarketService:
    def get_latest_price(self, symbol: str) -> RealtimeMarketSnapshot:
        return RealtimeMarketSnapshot(
            channel="latest_price",
            symbol=symbol,
            ok=True,
            fallback=False,
            timed_out=False,
            error=None,
            fetched_at_ms=1_700_000_000_000,
            data={"last_price": 100.0, "bid": 99.9, "ask": 100.1},
        )

    def get_klines(self, *args: Any, **kwargs: Any) -> RealtimeMarketSnapshot:
        return RealtimeMarketSnapshot(
            channel="kline",
            symbol="BTC/USDT",
            ok=True,
            fallback=False,
            timed_out=False,
            error=None,
            fetched_at_ms=1_700_000_000_000,
            data={"timeframe": "1m", "candles": []},
        )


def _build_loop(*, timeframe: str) -> tuple[RealtimeSimulationLoop, SQLiteDatabase]:
    db = SQLiteDatabase(":memory:")
    db.open()
    db.initialize_schema()

    account_service = AccountService(db, base_currency="USDT")
    account_service.initialize_accounts({"USDT": 10_000.0, "BTC": 0.0})
    order_service = OrderService(db, account_service)
    trade_service = TradeService(db, order_service)
    market = _DummyMarketService()
    price_service = PriceService(db, account_service, market)
    storage = HistoricalCandleStorage(db, market.get_klines)

    loop = RealtimeSimulationLoop(
        database=db,
        account_service=account_service,
        order_service=order_service,
        trade_service=trade_service,
        market_service=market,
        price_service=price_service,
        candle_storage=storage,
        strategy=_NoopStrategy(),
        config=RealtimeLoopConfig(
            symbol="BTC/USDT",
            timeframe=timeframe,
            tick_interval_seconds=0.001,
            max_iterations=1,
        ),
    )
    return loop, db


def test_persist_latest_candle_merges_ohlc_within_same_bucket() -> None:
    loop, db = _build_loop(timeframe="1m")
    try:
        base_ms = 1_700_000_000_123
        loop._persist_latest_candle(base_ms, 100.0)
        loop._persist_latest_candle(base_ms + 5_000, 108.0)
        loop._persist_latest_candle(base_ms + 20_000, 95.0)

        with db.transaction() as tx:
            rows = tx.execute(
                """
                SELECT timestamp, open, high, low, close
                FROM candles
                WHERE symbol = 'BTC/USDT' AND timeframe = '1m'
                ORDER BY timestamp ASC
                """
            ).fetchall()
        assert len(rows) == 1
        row = rows[0]
        assert row["open"] == 100.0
        assert row["high"] == 108.0
        assert row["low"] == 95.0
        assert row["close"] == 95.0
    finally:
        db.close()


def test_persist_latest_candle_aligns_timestamp_to_timeframe_bucket() -> None:
    loop, db = _build_loop(timeframe="1h")
    try:
        raw_ts = 1_700_000_123_456
        expected_bucket = raw_ts - (raw_ts % 3_600_000)
        loop._persist_latest_candle(raw_ts, 100.0)

        with db.transaction() as tx:
            row = tx.execute(
                """
                SELECT timestamp
                FROM candles
                WHERE symbol = 'BTC/USDT' AND timeframe = '1h'
                """
            ).fetchone()
        assert row is not None
        assert int(row["timestamp"]) == expected_bucket
    finally:
        db.close()
