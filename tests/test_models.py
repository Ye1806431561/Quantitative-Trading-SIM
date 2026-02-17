import pytest

from src.core.account import Account
from src.core.candle import Candle
from src.core.enums import OrderSide, OrderStatus, OrderType, StrategyRunStatus, TradeSide
from src.core.order import Order
from src.core.position import Position
from src.core.strategy_run import StrategyRun
from src.core.trade import Trade
from src.core.validation import DomainValidationError


def test_account_validation_passes():
    account = Account.validate(
        {"currency": "USDT", "balance": 10000, "available": 8000, "frozen": 2000}
    )
    assert account.currency == "USDT"
    assert account.balance == 10000


def test_account_validation_blocks_over_allocated_funds():
    with pytest.raises(DomainValidationError):
        Account.validate({"currency": "USDT", "balance": 100, "available": 80, "frozen": 30})


def test_order_validation_market_price_optional():
    order = Order.validate(
        {
            "id": "ord-1",
            "symbol": "BTC/USDT",
            "type": OrderType.MARKET,
            "side": OrderSide.BUY,
            "price": None,
            "amount": 0.5,
            "filled": 0,
            "status": OrderStatus.PENDING,
            "created_at": 1700000000000,
            "updated_at": 1700000000000,
        }
    )
    assert order.price is None


def test_order_validation_requires_price_for_limit():
    with pytest.raises(DomainValidationError):
        Order.validate(
            {
                "id": "ord-2",
                "symbol": "ETH/USDT",
                "type": OrderType.LIMIT,
                "side": OrderSide.SELL,
                "amount": 1,
                "filled": 0,
                "status": OrderStatus.OPEN,
            }
        )


def test_order_validation_blocks_overfilled():
    with pytest.raises(DomainValidationError):
        Order.validate(
            {
                "id": "ord-3",
                "symbol": "ETH/USDT",
                "type": OrderType.LIMIT,
                "side": OrderSide.SELL,
                "price": 2000,
                "amount": 1,
                "filled": 2,
                "status": OrderStatus.OPEN,
            }
        )


def test_trade_validation_passes():
    trade = Trade.validate(
        {
            "order_id": "ord-1",
            "symbol": "BTC/USDT",
            "side": TradeSide.BUY,
            "price": 50000,
            "amount": 0.1,
            "fee": 1.5,
            "timestamp": 1700000000000,
        }
    )
    assert trade.fee == 1.5


def test_trade_validation_blocks_negative_fee():
    with pytest.raises(DomainValidationError):
        Trade.validate(
            {
                "order_id": "ord-1",
                "symbol": "BTC/USDT",
                "side": TradeSide.BUY,
                "price": 50000,
                "amount": 0.1,
                "fee": -1,
            }
        )


def test_position_validation_passes():
    pos = Position.validate(
        {
            "symbol": "BTC/USDT",
            "amount": 1.2,
            "entry_price": 30000,
            "current_price": 31000,
            "unrealized_pnl": 1200,
            "realized_pnl": 0,
            "opened_at": 1700000000000,
        }
    )
    assert pos.amount == 1.2


def test_position_validation_blocks_negative_amount():
    with pytest.raises(DomainValidationError):
        Position.validate(
            {
                "symbol": "BTC/USDT",
                "amount": -1,
                "entry_price": 30000,
            }
        )


def test_candle_validation_passes():
    candle = Candle.validate(
        {
            "symbol": "BTC/USDT",
            "timeframe": "1h",
            "timestamp": 1700000000000,
            "open": 50000,
            "high": 51000,
            "low": 49500,
            "close": 50500,
            "volume": 123.4,
        }
    )
    assert candle.timeframe == "1h"


def test_candle_validation_blocks_out_of_range_close():
    with pytest.raises(DomainValidationError):
        Candle.validate(
            {
                "symbol": "BTC/USDT",
                "timeframe": "1h",
                "timestamp": 1700000000000,
                "open": 50000,
                "high": 51000,
                "low": 49500,
                "close": 52000,
                "volume": 123.4,
            }
        )


def test_strategy_run_validation_passes():
    run = StrategyRun.validate(
        {
            "strategy_name": "sma",
            "symbol": "BTC/USDT",
            "start_time": 1700000000000,
            "end_time": 1700001000000,
            "initial_capital": 10000,
            "final_capital": 10200,
            "total_return": 0.02,
            "max_drawdown": 0.1,
            "sharpe_ratio": 1.5,
            "status": StrategyRunStatus.COMPLETED,
        }
    )
    assert run.status == StrategyRunStatus.COMPLETED


def test_strategy_run_validation_blocks_invalid_drawdown():
    with pytest.raises(DomainValidationError):
        StrategyRun.validate(
            {
                "strategy_name": "sma",
                "symbol": "BTC/USDT",
                "start_time": 1700000000000,
                "end_time": 1700001000000,
                "initial_capital": 10000,
                "max_drawdown": 1.5,
                "status": StrategyRunStatus.RUNNING,
            }
        )


def test_strategy_run_validation_blocks_end_before_start():
    with pytest.raises(DomainValidationError):
        StrategyRun.validate(
            {
                "strategy_name": "sma",
                "symbol": "BTC/USDT",
                "start_time": 1700001000000,
                "end_time": 1700000000000,
                "initial_capital": 10000,
                "status": StrategyRunStatus.RUNNING,
            }
        )
