"""Order state machine tests (Phase 2 Step 23)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.core.account_service import AccountService
from src.core.database import SQLiteDatabase
from src.core.enums import OrderSide, OrderStatus, OrderType
from src.core.order_state_machine import (
    ORDER_NEW_STATUS,
    VALID_ORDER_STATUS_TRANSITIONS,
    can_transition,
)
from src.core.order_service import CreateOrderRequest, OrderService
from src.core.trade_service import CreateTradeRequest, TradeService


@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = SQLiteDatabase(db_path)
        db.open()
        db.initialize_schema()
        yield db
        db.close()


@pytest.fixture
def account_service(temp_db):
    service = AccountService(temp_db, "USDT")
    service.initialize_accounts({"USDT": 100000.0, "BTC": 0.0})
    return service


@pytest.fixture
def order_service(temp_db, account_service):
    return OrderService(temp_db, account_service)


@pytest.fixture
def trade_service(temp_db, order_service):
    return TradeService(temp_db, order_service)


def test_transition_table_matches_step_23_definition():
    assert ORDER_NEW_STATUS == OrderStatus.PENDING
    assert VALID_ORDER_STATUS_TRANSITIONS == {
        OrderStatus.PENDING: {
            OrderStatus.OPEN,
            OrderStatus.REJECTED,
            OrderStatus.CANCELED,
        },
        OrderStatus.OPEN: {
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.FILLED,
            OrderStatus.CANCELED,
        },
        OrderStatus.PARTIALLY_FILLED: {
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.FILLED,
            OrderStatus.CANCELED,
        },
        OrderStatus.FILLED: set(),
        OrderStatus.CANCELED: set(),
        OrderStatus.REJECTED: set(),
    }


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (OrderStatus.PENDING, OrderStatus.OPEN),
        (OrderStatus.PENDING, OrderStatus.REJECTED),
        (OrderStatus.PENDING, OrderStatus.CANCELED),
        (OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED),
        (OrderStatus.OPEN, OrderStatus.FILLED),
        (OrderStatus.OPEN, OrderStatus.CANCELED),
        (OrderStatus.PARTIALLY_FILLED, OrderStatus.PARTIALLY_FILLED),
        (OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED),
        (OrderStatus.PARTIALLY_FILLED, OrderStatus.CANCELED),
    ],
)
def test_can_transition_accepts_every_legal_path(current: OrderStatus, target: OrderStatus):
    assert can_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (OrderStatus.PENDING, OrderStatus.FILLED),
        (OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED),
        (OrderStatus.OPEN, OrderStatus.REJECTED),
        (OrderStatus.FILLED, OrderStatus.CANCELED),
        (OrderStatus.CANCELED, OrderStatus.OPEN),
        (OrderStatus.REJECTED, OrderStatus.OPEN),
    ],
)
def test_can_transition_rejects_illegal_paths(current: OrderStatus, target: OrderStatus):
    assert not can_transition(current, target)


def test_order_service_supports_pending_to_rejected(order_service: OrderService):
    created = order_service.create_order(
        CreateOrderRequest(
            symbol="BTC/USDT",
            type=OrderType.LIMIT,
            side=OrderSide.BUY,
            amount=0.1,
            price=50000.0,
        )
    )
    rejected = order_service.update_order_status(created.id, OrderStatus.REJECTED)
    assert rejected.status == OrderStatus.REJECTED


def test_update_order_status_to_canceled_releases_frozen_funds(
    order_service: OrderService,
    account_service: AccountService,
):
    created = order_service.create_order(
        CreateOrderRequest(
            symbol="BTC/USDT",
            type=OrderType.LIMIT,
            side=OrderSide.BUY,
            amount=0.5,
            price=50000.0,
        )
    )
    frozen_before = account_service.get_account("USDT")
    assert frozen_before.frozen == 25000.0

    canceled = order_service.update_order_status(created.id, OrderStatus.CANCELED)
    assert canceled.status == OrderStatus.CANCELED

    frozen_after = account_service.get_account("USDT")
    assert frozen_after.frozen == 0.0
    assert frozen_after.available == 100000.0


def test_trade_service_allows_partially_filled_to_partially_filled(
    order_service: OrderService,
    trade_service: TradeService,
):
    created = order_service.create_order(
        CreateOrderRequest(
            symbol="BTC/USDT",
            type=OrderType.LIMIT,
            side=OrderSide.BUY,
            amount=1.0,
            price=50000.0,
        )
    )
    order_service.update_order_status(created.id, OrderStatus.OPEN)

    trade_service.record_trade(
        CreateTradeRequest(
            order_id=created.id,
            price=50000.0,
            amount=0.2,
            fee=0.0,
        )
    )
    first = order_service.get_order(created.id)
    assert first.status == OrderStatus.PARTIALLY_FILLED
    assert first.filled == 0.2

    trade_service.record_trade(
        CreateTradeRequest(
            order_id=created.id,
            price=50000.0,
            amount=0.3,
            fee=0.0,
        )
    )
    second = order_service.get_order(created.id)
    assert second.status == OrderStatus.PARTIALLY_FILLED
    assert second.filled == 0.5
