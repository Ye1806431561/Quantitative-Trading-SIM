"""Tests for real-time simulation loop (Phase 3 Step 29)."""

import time
from typing import Any, Mapping
from unittest.mock import MagicMock

import pytest

from src.core.account_service import AccountService
from src.core.database import SQLiteDatabase
from src.core.enums import OrderSide
from src.core.execution_cost import ExecutionCostProfile
from src.core.order_service import OrderService
from src.core.risk import RiskLimits
from src.core.trade_service import TradeService
from src.data.realtime_market import RealtimeMarketDataService
from src.data.realtime_payloads import RealtimeMarketSnapshot
from src.data.storage import HistoricalCandleStorage
from src.live.price_service import PriceService
from src.live.realtime_loop import RealtimeLoopConfig, RealtimeSimulationLoop
from src.strategies.base import LiveStrategy, StrategyContext


class MockStrategy(LiveStrategy):
    """Mock strategy for testing loop behavior."""

    def __init__(self, name: str = "mock_strategy"):
        super().__init__(name)
        self.initialize_called = False
        self.run_called_count = 0
        self.stop_called = False
        self.last_market_data = None
        self.signal_to_return = None

    def on_initialize(self, context: StrategyContext) -> None:
        self.initialize_called = True

    def on_run(self, market_data: Mapping[str, Any]) -> Mapping[str, Any] | None:
        self.run_called_count += 1
        self.last_market_data = market_data
        return self.signal_to_return

    def on_stop(self, reason: str | None) -> None:
        self.stop_called = True


@pytest.fixture
def database():
    """Create in-memory database for testing."""
    db = SQLiteDatabase(":memory:")
    db.open()
    db.initialize_schema()
    yield db
    db.close()


@pytest.fixture
def mock_market_service():
    """Create mock market service."""
    service = MagicMock(spec=RealtimeMarketDataService)
    service.get_latest_price.return_value = RealtimeMarketSnapshot(
        channel="latest_price",
        symbol="BTC/USDT",
        ok=True,
        fallback=False,
        timed_out=False,
        error=None,
        fetched_at_ms=int(time.time() * 1000),
        data={"last_price": 50000.0, "bid": 49999.0, "ask": 50001.0},
    )
    service.get_klines = MagicMock(return_value=[])
    return service


@pytest.fixture
def realtime_loop(database, mock_market_service):
    """Create real-time loop with mock dependencies."""
    account_service = AccountService(database, base_currency="USDT")
    account_service.initialize_accounts({"USDT": 10000.0, "BTC": 0.0})

    order_service = OrderService(database, account_service)
    trade_service = TradeService(database, order_service)
    price_service = PriceService(database, account_service, mock_market_service)
    candle_storage = HistoricalCandleStorage(database, mock_market_service.get_klines)

    strategy = MockStrategy()
    config = RealtimeLoopConfig(
        symbol="BTC/USDT",
        timeframe="1m",
        tick_interval_seconds=0.01,  # Fast for testing
        max_iterations=3,  # Run only 3 iterations
    )

    cost_profile = ExecutionCostProfile(
        maker_fee_rate=0.0,
        taker_fee_rate=0.0,
        slippage_rate=0.0,
    )

    risk_limits = RiskLimits(
        max_position_size=0.5,
        max_total_position=0.9,
        max_drawdown=0.3,
    )

    loop = RealtimeSimulationLoop(
        database=database,
        account_service=account_service,
        order_service=order_service,
        trade_service=trade_service,
        market_service=mock_market_service,
        price_service=price_service,
        candle_storage=candle_storage,
        strategy=strategy,
        config=config,
        cost_profile=cost_profile,
        risk_limits=risk_limits,
    )

    return loop


def test_loop_initializes_strategy_and_runs_iterations(realtime_loop):
    """Verify loop initializes strategy and executes multiple iterations."""
    strategy = realtime_loop._strategy

    # Before start
    assert not strategy.initialize_called
    assert strategy.run_called_count == 0

    # Run loop
    realtime_loop.start()

    # After completion
    assert strategy.initialize_called
    assert strategy.run_called_count == 3  # max_iterations=3
    assert strategy.stop_called
    assert not realtime_loop.is_running
    assert realtime_loop.iteration_count == 3


def test_loop_fetches_market_data_and_passes_to_strategy(realtime_loop, mock_market_service):
    """Verify loop fetches market data and passes it to strategy."""
    strategy = realtime_loop._strategy

    realtime_loop.start()

    # Verify market service was called
    assert mock_market_service.get_latest_price.call_count >= 3

    # Verify strategy received market data
    assert strategy.last_market_data is not None
    assert strategy.last_market_data["symbol"] == "BTC/USDT"
    assert strategy.last_market_data["latest_price"] == 50000.0
    assert "timestamp" in strategy.last_market_data


def test_loop_persists_candles_to_sqlite(realtime_loop, database):
    """Verify loop persists latest candles to SQLite (runtime write path)."""
    realtime_loop.start()

    # Query candles from database
    with database.transaction() as tx:
        rows = tx.execute(
            "SELECT symbol, timeframe, close FROM candles WHERE symbol = ?",
            ("BTC/USDT",),
        ).fetchall()

    # Should have persisted candles during iterations
    assert len(rows) >= 1
    assert rows[0]["symbol"] == "BTC/USDT"
    assert rows[0]["timeframe"] == "1m"
    assert rows[0]["close"] == 50000.0


def test_loop_executes_market_buy_signal(realtime_loop, database):
    """Verify loop executes market buy signal from strategy."""
    strategy = realtime_loop._strategy
    strategy.signal_to_return = {
        "action": "buy",
        "type": "market",
        "amount": 0.1,
    }

    realtime_loop.start()

    # Verify order was created
    with database.transaction() as tx:
        orders = tx.execute(
            "SELECT symbol, side, amount, status FROM orders WHERE symbol = ?",
            ("BTC/USDT",),
        ).fetchall()

    assert len(orders) >= 1
    assert orders[0]["symbol"] == "BTC/USDT"
    assert orders[0]["side"] == "buy"
    assert orders[0]["amount"] == 0.1
    assert orders[0]["status"] == "filled"


def test_loop_executes_limit_order_signal(realtime_loop, database):
    """Verify loop executes limit order signal from strategy."""
    strategy = realtime_loop._strategy
    strategy.signal_to_return = {
        "action": "buy",
        "type": "limit",
        "amount": 0.1,
        "price": 49000.0,
    }

    realtime_loop.start()

    # Verify limit order was created
    with database.transaction() as tx:
        orders = tx.execute(
            "SELECT symbol, type, side, amount, price, status FROM orders WHERE symbol = ?",
            ("BTC/USDT",),
        ).fetchall()

    assert len(orders) >= 1
    assert orders[0]["symbol"] == "BTC/USDT"
    assert orders[0]["type"] == "limit"
    assert orders[0]["side"] == "buy"
    assert orders[0]["amount"] == 0.1
    assert orders[0]["price"] == 49000.0
    assert orders[0]["status"] == "open"  # Limit order stays open until triggered


def test_loop_handles_market_data_fetch_failure_gracefully(realtime_loop, mock_market_service):
    """Verify loop continues running when market data fetch fails."""
    # Simulate market data failure
    mock_market_service.get_latest_price.return_value = RealtimeMarketSnapshot(
        channel="latest_price",
        symbol="BTC/USDT",
        ok=False,
        fallback=False,
        timed_out=False,
        error="Network error",
        fetched_at_ms=int(time.time() * 1000),
        data={"last_price": None},
    )

    strategy = realtime_loop._strategy

    realtime_loop.start()

    # Loop should complete without crashing
    assert strategy.initialize_called
    assert strategy.stop_called
    assert realtime_loop.iteration_count == 3


def test_loop_stops_when_max_iterations_reached(realtime_loop):
    """Verify loop stops after reaching max_iterations."""
    realtime_loop.start()

    assert not realtime_loop.is_running
    assert realtime_loop.iteration_count == 3


def test_loop_from_config_factory_method(database, mock_market_service):
    """Verify loop can be constructed from config dict."""
    config = {
        "system": {"database_path": ":memory:"},
        "account": {"initial_capital": 10000.0, "base_currency": "USDT"},
        "exchange": {"name": "binance", "testnet": True, "rate_limit": True},
        "market_data": {
            "runtime_write_target": "sqlite",
            "retry": {
                "max_attempts": 3,
                "initial_delay_seconds": 0.2,
                "backoff_multiplier": 2.0,
                "max_delay_seconds": 2.0,
            },
        },
        "trading": {
            "commission": {"maker": 0.001, "taker": 0.001},
            "slippage": 0.0005,
        },
        "risk": {
            "max_position_size": 0.3,
            "max_total_position": 0.8,
            "max_drawdown": 0.2,
        },
    }

    strategy = MockStrategy()

    loop = RealtimeSimulationLoop.from_config(
        config=config,
        database=database,
        strategy=strategy,
        symbol="BTC/USDT",
        timeframe="1h",
        tick_interval_seconds=0.01,
        max_iterations=2,
    )

    # Patch market service with mock
    loop._market_service = mock_market_service

    # Initialize accounts
    loop._account_service.initialize_accounts({"USDT": 10000.0, "BTC": 0.0})

    loop.start()

    assert strategy.initialize_called
    assert loop.iteration_count == 2

