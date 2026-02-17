"""Tests for trade recording and order association (Phase 1 Step 13)."""

import tempfile
from pathlib import Path

import pytest

from src.core.account_service import AccountService
from src.core.database import SQLiteDatabase
from src.core.enums import OrderSide, OrderStatus, OrderType
from src.core.order_service import CreateOrderRequest, OrderService
from src.core.trade_service import CreateTradeRequest, TradeService, TradeServiceError


@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "trades.db"
        db = SQLiteDatabase(db_path)
        db.initialize_schema()
        yield db
        db.close()


@pytest.fixture
def account_service(temp_db):
    service = AccountService(temp_db, "USDT")
    service.initialize_accounts({"USDT": 100000.0})
    return service


@pytest.fixture
def order_service(temp_db, account_service):
    return OrderService(temp_db, account_service)


@pytest.fixture
def trade_service(temp_db, order_service, account_service):  # account_service kept for future parity
    return TradeService(temp_db, order_service)


def _create_open_order(order_service: OrderService) -> str:
    request = CreateOrderRequest(
        symbol="BTC/USDT",
        type=OrderType.LIMIT,
        side=OrderSide.BUY,
        amount=1.0,
        price=50000.0,
    )
    order = order_service.create_order(request)
    order_service.update_order_status(order.id, OrderStatus.OPEN)
    return order.id


def test_record_trade_persists_and_links_order(order_service, trade_service):
    order_id = _create_open_order(order_service)

    trade = trade_service.record_trade(
        CreateTradeRequest(order_id=order_id, price=50000.0, amount=0.4, fee=5.0)
    )

    assert trade.order_id == order_id
    trades = trade_service.list_trades_for_order(order_id)
    assert len(trades) == 1
    assert trades[0].price == 50000.0
    assert trades[0].fee == 5.0


def test_record_trade_updates_filled_amount_and_status(order_service, trade_service):
    order_id = _create_open_order(order_service)

    trade_service.record_trade(CreateTradeRequest(order_id=order_id, price=50000.0, amount=0.4, fee=1.0))
    order_after_first = order_service.get_order(order_id)
    assert order_after_first.status == OrderStatus.PARTIALLY_FILLED
    assert order_after_first.filled == pytest.approx(0.4)

    trade_service.record_trade(CreateTradeRequest(order_id=order_id, price=50000.0, amount=0.6, fee=1.0))
    order_after_second = order_service.get_order(order_id)
    assert order_after_second.status == OrderStatus.FILLED
    assert order_after_second.filled == pytest.approx(1.0)


def test_record_trade_rejects_overfill(order_service, trade_service):
    order_id = _create_open_order(order_service)

    with pytest.raises(TradeServiceError):
        trade_service.record_trade(
            CreateTradeRequest(order_id=order_id, price=50000.0, amount=1.5, fee=0.0)
        )


def test_record_trade_requires_existing_order(trade_service):
    with pytest.raises(TradeServiceError, match="order not found"):
        trade_service.record_trade(
            CreateTradeRequest(order_id="missing", price=10.0, amount=1.0, fee=0.1)
        )
