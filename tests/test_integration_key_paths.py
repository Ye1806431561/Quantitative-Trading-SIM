"""Integration suite for step 39 key paths."""

from __future__ import annotations

from typing import Any

import backtrader as bt
import pytest

from src.backtest.engine import BacktestEngine, BacktestRunRequest
from src.core.account_service import AccountService
from src.core.database import SQLiteDatabase
from src.core.enums import OrderSide, OrderStatus
from src.core.execution_cost import ExecutionCostProfile
from src.core.matching import MarketOrderRequest, MatchingEngine
from src.core.order_service import OrderService
from src.core.risk import RiskLimits
from src.core.trade_service import TradeService
from src.data.realtime_payloads import RealtimeMarketSnapshot
from src.data.storage import HistoricalCandleStorage
from src.live.price_service import PriceService
from src.live.realtime_loop import RealtimeLoopConfig, RealtimeSimulationLoop
from src.strategies.base import LiveStrategy, StrategyContext

pytestmark = pytest.mark.integration


class _FixedPriceMarket:
    def __init__(
        self,
        price: float,
        start_ts: int = 1_700_000_000_000,
        prices: list[float] | None = None,
    ) -> None:
        self._prices = list(prices) if prices else [price]
        self._cursor = 0
        self._ts = start_ts

    def get_latest_price(self, symbol: str) -> RealtimeMarketSnapshot:
        if self._cursor < len(self._prices):
            price = self._prices[self._cursor]
            self._cursor += 1
        else:
            price = self._prices[-1]
        self._ts += 500
        return RealtimeMarketSnapshot(
            channel="latest_price",
            symbol=symbol,
            ok=True,
            fallback=False,
            timed_out=False,
            error=None,
            fetched_at_ms=self._ts,
            data={
                "last_price": price,
                "bid": price - 0.1,
                "ask": price + 0.1,
            },
        )

    def get_klines(self, *args: Any, **kwargs: Any) -> RealtimeMarketSnapshot:
        return RealtimeMarketSnapshot(
            channel="kline",
            symbol="BTC/USDT",
            ok=True,
            fallback=False,
            timed_out=False,
            error=None,
            fetched_at_ms=self._ts,
            data={"timeframe": "1m", "candles": []},
        )


class _OneShotBuyStrategy(LiveStrategy):
    def __init__(self) -> None:
        super().__init__("one_shot_buy")
        self._fired = False

    def on_initialize(self, context: StrategyContext) -> None:
        return None

    def on_run(self, market_data: dict[str, Any]) -> dict[str, Any] | None:
        if self._fired:
            return None
        self._fired = True
        return {"action": "buy", "type": "market", "amount": 0.1}

    def on_stop(self, reason: str | None) -> None:
        return None


class _BuyThenSellStrategy(bt.Strategy):
    def __init__(self) -> None:
        self._bars = 0

    def next(self) -> None:
        self._bars += 1
        if not self.position and self._bars == 1:
            self.buy(size=1.0)
            return
        if self.position and self._bars >= 4:
            self.sell(size=1.0)


class _ScaleOutStrategy(bt.Strategy):
    def __init__(self) -> None:
        self._bars = 0

    def next(self) -> None:
        self._bars += 1
        if not self.position and self._bars == 1:
            self.buy(size=1.0)
            return
        if self.position and self._bars == 4:
            self.sell(size=0.5)
            return
        if self.position and self._bars == 5:
            self.sell(size=0.5)


def _init_runtime_stack() -> (
    tuple[SQLiteDatabase, AccountService, OrderService, TradeService]
):
    db = SQLiteDatabase(":memory:")
    db.open()
    db.initialize_schema()
    account_service = AccountService(db, base_currency="USDT")
    account_service.initialize_accounts({"USDT": 10_000.0, "BTC": 0.0})
    order_service = OrderService(db, account_service)
    trade_service = TradeService(db, order_service)
    return db, account_service, order_service, trade_service


def _seed_backtest_candles(database: SQLiteDatabase) -> None:
    rows: list[tuple[Any, ...]] = []
    base_ts = 1_700_000_000_000
    prices = [100.0, 105.0, 110.0, 115.0, 112.0, 108.0]
    for idx, close_price in enumerate(prices):
        timestamp = base_ts + idx * 3_600_000
        rows.append(
            (
                "BTC/USDT",
                "1h",
                timestamp,
                close_price - 1.0,
                close_price + 1.0,
                close_price - 2.0,
                close_price,
                10.0 + idx,
            )
        )
    with database.transaction() as tx:
        tx.executemany(
            """
            INSERT INTO candles(symbol, timeframe, timestamp, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            rows,
        )


def test_integration_account_and_matching_key_path() -> None:
    db, account_service, order_service, trade_service = _init_runtime_stack()
    market = _FixedPriceMarket(price=100.0)
    engine = MatchingEngine(
        database=db,
        account_service=account_service,
        order_service=order_service,
        trade_service=trade_service,
        market_reader=market,
        cost_profile=ExecutionCostProfile(
            maker_fee_rate=0.0, taker_fee_rate=0.0, slippage_rate=0.0
        ),
        risk_limits=RiskLimits(
            max_position_size=1.0, max_total_position=1.0, max_drawdown=0.9
        ),
    )
    try:
        result = engine.execute_market_order(
            MarketOrderRequest(symbol="BTC/USDT", side=OrderSide.BUY, amount=1.0)
        )

        assert result.order.status == OrderStatus.FILLED
        assert result.trade.amount == pytest.approx(1.0)
        assert account_service.get_account("BTC").balance == pytest.approx(1.0)
        assert account_service.get_account("USDT").balance == pytest.approx(9_900.0)
        with db.transaction() as tx:
            position = tx.execute(
                "SELECT amount, entry_price FROM positions WHERE symbol = 'BTC/USDT';"
            ).fetchone()
        assert position is not None
        assert float(position["amount"]) == pytest.approx(1.0)
        assert float(position["entry_price"]) == pytest.approx(100.0)
    finally:
        db.close()


def test_integration_backtest_and_strategy_key_path() -> None:
    database = SQLiteDatabase(":memory:")
    database.open()
    database.initialize_schema()
    _seed_backtest_candles(database)
    try:
        engine = BacktestEngine(
            database=database,
            initial_capital=10_000.0,
            commission_rate=0.0,
            slippage_rate=0.0,
            data_read_source="sqlite",
            strategies_config=None,
        )
        result = engine.run(
            BacktestRunRequest(
                symbol="BTC/USDT",
                timeframe="1h",
                start_timestamp=1_700_000_000_000,
                end_timestamp=1_700_018_000_000,
                strategy_class=_BuyThenSellStrategy,
            )
        )
        assert result.bars_processed == 6
        assert result.trade_stats.total_trades == 1
        assert result.pnl == pytest.approx(7.0)
        assert result.final_value == pytest.approx(10_007.0)
        assert len(result.trade_log) == 1
        trade = result.trade_log[0]
        assert trade.entry_price == pytest.approx(104.0)
        assert trade.exit_price == pytest.approx(111.0)
        assert trade.pnl_net == pytest.approx(7.0)
        assert isinstance(result.time_series_returns, dict)
    finally:
        database.close()


def test_integration_backtest_trade_log_handles_partial_close() -> None:
    database = SQLiteDatabase(":memory:")
    database.open()
    database.initialize_schema()
    _seed_backtest_candles(database)
    try:
        engine = BacktestEngine(
            database=database,
            initial_capital=10_000.0,
            commission_rate=0.0,
            slippage_rate=0.0,
            data_read_source="sqlite",
            strategies_config=None,
        )
        result = engine.run(
            BacktestRunRequest(
                symbol="BTC/USDT",
                timeframe="1h",
                start_timestamp=1_700_000_000_000,
                end_timestamp=1_700_018_000_000,
                strategy_class=_ScaleOutStrategy,
            )
        )
        assert result.trade_stats.total_trades == 1
        assert result.pnl == pytest.approx(5.0)
        assert result.final_value == pytest.approx(10_005.0)
        assert len(result.trade_log) == 1
        trade = result.trade_log[0]
        assert trade.size == pytest.approx(1.0)
        assert trade.entry_price == pytest.approx(104.0)
        assert trade.exit_price == pytest.approx(109.0)
        assert trade.pnl_net == pytest.approx(5.0)
    finally:
        database.close()


def test_integration_realtime_engine_key_path() -> None:
    db, account_service, order_service, trade_service = _init_runtime_stack()
    market = _FixedPriceMarket(
        price=100.0,
        prices=[100.0, 100.0, 100.0, 100.0, 101.0, 101.0, 101.0],
    )
    price_service = PriceService(db, account_service, market)
    storage = HistoricalCandleStorage(db, market.get_klines)
    cost_profile = ExecutionCostProfile(
        maker_fee_rate=0.0, taker_fee_rate=0.0, slippage_rate=0.0
    )
    risk_limits = RiskLimits(
        max_position_size=1.0, max_total_position=1.0, max_drawdown=0.9
    )
    loop = RealtimeSimulationLoop(
        database=db,
        account_service=account_service,
        order_service=order_service,
        trade_service=trade_service,
        market_service=market,
        price_service=price_service,
        candle_storage=storage,
        strategy=_OneShotBuyStrategy(),
        config=RealtimeLoopConfig(
            symbol="BTC/USDT",
            timeframe="1m",
            tick_interval_seconds=0.001,
            max_iterations=2,
        ),
        cost_profile=cost_profile,
        risk_limits=risk_limits,
    )
    try:
        loop.start()
        assert loop.iteration_count == 2
        with db.transaction() as tx:
            order_row = tx.execute(
                "SELECT status FROM orders ORDER BY created_at DESC LIMIT 1;"
            ).fetchone()
            trade_row = tx.execute(
                "SELECT amount, price FROM trades ORDER BY id DESC LIMIT 1;"
            ).fetchone()
            candle_count = tx.execute(
                "SELECT COUNT(1) AS cnt FROM candles WHERE symbol = 'BTC/USDT' AND timeframe = '1m';"
            ).fetchone()
            candle_row = tx.execute("""
                SELECT open, high, low, close
                FROM candles
                WHERE symbol = 'BTC/USDT' AND timeframe = '1m'
                ORDER BY timestamp DESC
                LIMIT 1;
                """).fetchone()
        assert order_row is not None
        assert order_row["status"] == OrderStatus.FILLED.value
        assert trade_row is not None
        assert float(trade_row["amount"]) == pytest.approx(0.1)
        assert float(trade_row["price"]) == pytest.approx(100.0)
        assert candle_count is not None and int(candle_count["cnt"]) == 1
        assert candle_row is not None
        assert float(candle_row["open"]) == pytest.approx(100.0)
        assert float(candle_row["high"]) == pytest.approx(101.0)
        assert float(candle_row["low"]) == pytest.approx(100.0)
        assert float(candle_row["close"]) == pytest.approx(101.0)
    finally:
        db.close()
