"""Test order persistence interface (Phase 1 Step 12)."""

import tempfile
from pathlib import Path

import pytest

from src.core.account_service import AccountService
from src.core.database import SQLiteDatabase
from src.core.enums import OrderSide, OrderStatus, OrderType
from src.core.order_service import CreateOrderRequest, OrderService, OrderServiceError


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = SQLiteDatabase(db_path)
        db.open()
        db.initialize_schema()
        yield db
        db.close()


@pytest.fixture
def account_service(temp_db):
    """Create account service with initial balance."""
    service = AccountService(temp_db, "USDT")
    service.initialize_accounts({"USDT": 100000.0, "BTC": 0.0})
    return service


@pytest.fixture
def order_service(temp_db, account_service):
    """Create order service."""
    return OrderService(temp_db, account_service)


# ------------------------------------------------------------------ #
# Test order creation
# ------------------------------------------------------------------ #
def test_create_buy_limit_order_freezes_funds(order_service, account_service):
    """Test creating a buy limit order freezes required funds."""
    # Initial state
    account_before = account_service.get_account("USDT")
    assert account_before.available == 100000.0
    assert account_before.frozen == 0.0

    # Create buy order
    request = CreateOrderRequest(
        symbol="BTC/USDT",
        type=OrderType.LIMIT,
        side=OrderSide.BUY,
        amount=0.5,
        price=50000.0,
    )
    order = order_service.create_order(request)

    # Verify order
    assert order.symbol == "BTC/USDT"
    assert order.type == OrderType.LIMIT
    assert order.side == OrderSide.BUY
    assert order.amount == 0.5
    assert order.price == 50000.0
    assert order.filled == 0.0
    assert order.status == OrderStatus.PENDING

    # Verify funds frozen
    account_after = account_service.get_account("USDT")
    assert account_after.available == 100000.0 - 25000.0  # 0.5 * 50000
    assert account_after.frozen == 25000.0


def test_create_sell_order_does_not_freeze_funds(order_service, account_service):
    """Test creating a sell order does not freeze funds (position check is separate)."""
    # Create sell order
    request = CreateOrderRequest(
        symbol="BTC/USDT",
        type=OrderType.LIMIT,
        side=OrderSide.SELL,
        amount=0.5,
        price=50000.0,
    )
    order = order_service.create_order(request)

    # Verify order
    assert order.side == OrderSide.SELL
    assert order.status == OrderStatus.PENDING

    # Verify no funds frozen (sell orders don't freeze USDT)
    account = account_service.get_account("USDT")
    assert account.frozen == 0.0


def test_create_order_validates_amount(order_service):
    """Test order creation rejects invalid amount."""
    request = CreateOrderRequest(
        symbol="BTC/USDT",
        type=OrderType.LIMIT,
        side=OrderSide.BUY,
        amount=0.0,  # Invalid
        price=50000.0,
    )
    with pytest.raises(OrderServiceError, match="amount must be > 0"):
        order_service.create_order(request)


def test_create_limit_order_requires_price(order_service):
    """Test limit order creation requires price."""
    request = CreateOrderRequest(
        symbol="BTC/USDT",
        type=OrderType.LIMIT,
        side=OrderSide.BUY,
        amount=0.5,
        price=None,  # Missing
    )
    with pytest.raises(OrderServiceError, match="price is required"):
        order_service.create_order(request)


def test_create_order_rejects_insufficient_funds(order_service, account_service):
    """Test order creation rejects when insufficient funds."""
    request = CreateOrderRequest(
        symbol="BTC/USDT",
        type=OrderType.LIMIT,
        side=OrderSide.BUY,
        amount=3.0,
        price=50000.0,  # Requires 150000 USDT, but only have 100000
    )
    with pytest.raises(OrderServiceError, match="failed to freeze funds"):
        order_service.create_order(request)


# ------------------------------------------------------------------ #
# Test order queries
# ------------------------------------------------------------------ #
def test_get_order_returns_created_order(order_service):
    """Test retrieving order by ID."""
    request = CreateOrderRequest(
        symbol="BTC/USDT",
        type=OrderType.LIMIT,
        side=OrderSide.BUY,
        amount=0.5,
        price=50000.0,
    )
    created = order_service.create_order(request)
    retrieved = order_service.get_order(created.id)

    assert retrieved.id == created.id
    assert retrieved.symbol == created.symbol
    assert retrieved.amount == created.amount


def test_get_order_raises_when_not_found(order_service):
    """Test get_order raises when order does not exist."""
    with pytest.raises(OrderServiceError, match="order not found"):
        order_service.get_order("NONEXISTENT")


def test_list_orders_returns_all_orders(order_service):
    """Test listing all orders."""
    # Create multiple orders
    for i in range(3):
        request = CreateOrderRequest(
            symbol="BTC/USDT",
            type=OrderType.LIMIT,
            side=OrderSide.BUY,
            amount=0.1 * (i + 1),
            price=50000.0,
        )
        order_service.create_order(request)

    orders = order_service.list_orders()
    assert len(orders) == 3


def test_list_orders_filters_by_symbol(order_service):
    """Test listing orders filtered by symbol."""
    # Create orders for different symbols
    for symbol in ["BTC/USDT", "ETH/USDT", "BTC/USDT"]:
        request = CreateOrderRequest(
            symbol=symbol,
            type=OrderType.LIMIT,
            side=OrderSide.BUY,
            amount=0.1,
            price=1000.0,
        )
        order_service.create_order(request)

    btc_orders = order_service.list_orders(symbol="BTC/USDT")
    assert len(btc_orders) == 2
    assert all(o.symbol == "BTC/USDT" for o in btc_orders)


def test_list_orders_filters_by_status(order_service):
    """Test listing orders filtered by status."""
    # Create and update orders
    request = CreateOrderRequest(
        symbol="BTC/USDT",
        type=OrderType.LIMIT,
        side=OrderSide.BUY,
        amount=0.1,
        price=50000.0,
    )
    order1 = order_service.create_order(request)
    order2 = order_service.create_order(request)

    # Update one to OPEN
    order_service.update_order_status(order1.id, OrderStatus.OPEN)

    # Filter by PENDING
    pending_orders = order_service.list_orders(status=OrderStatus.PENDING)
    assert len(pending_orders) == 1
    assert pending_orders[0].id == order2.id


def test_list_orders_respects_limit(order_service):
    """Test listing orders with limit."""
    # Create multiple orders
    for i in range(5):
        request = CreateOrderRequest(
            symbol="BTC/USDT",
            type=OrderType.LIMIT,
            side=OrderSide.BUY,
            amount=0.1,
            price=50000.0,
        )
        order_service.create_order(request)

    orders = order_service.list_orders(limit=3)
    assert len(orders) == 3


# ------------------------------------------------------------------ #
# Test order status updates
# ------------------------------------------------------------------ #
def test_update_order_status_pending_to_open(order_service):
    """Test valid status transition: PENDING -> OPEN."""
    request = CreateOrderRequest(
        symbol="BTC/USDT",
        type=OrderType.LIMIT,
        side=OrderSide.BUY,
        amount=0.5,
        price=50000.0,
    )
    order = order_service.create_order(request)
    assert order.status == OrderStatus.PENDING

    updated = order_service.update_order_status(order.id, OrderStatus.OPEN)
    assert updated.status == OrderStatus.OPEN


def test_update_order_status_open_to_partially_filled(order_service):
    """Test valid status transition: OPEN -> PARTIALLY_FILLED."""
    request = CreateOrderRequest(
        symbol="BTC/USDT",
        type=OrderType.LIMIT,
        side=OrderSide.BUY,
        amount=1.0,
        price=50000.0,
    )
    order = order_service.create_order(request)
    order_service.update_order_status(order.id, OrderStatus.OPEN)

    updated = order_service.update_order_status(order.id, OrderStatus.PARTIALLY_FILLED, filled=0.5)
    assert updated.status == OrderStatus.PARTIALLY_FILLED
    assert updated.filled == 0.5


def test_update_order_status_partially_filled_to_filled(order_service):
    """Test valid status transition: PARTIALLY_FILLED -> FILLED."""
    request = CreateOrderRequest(
        symbol="BTC/USDT",
        type=OrderType.LIMIT,
        side=OrderSide.BUY,
        amount=1.0,
        price=50000.0,
    )
    order = order_service.create_order(request)
    order_service.update_order_status(order.id, OrderStatus.OPEN)
    order_service.update_order_status(order.id, OrderStatus.PARTIALLY_FILLED, filled=0.5)

    updated = order_service.update_order_status(order.id, OrderStatus.FILLED, filled=1.0)
    assert updated.status == OrderStatus.FILLED
    assert updated.filled == 1.0


def test_update_order_status_rejects_invalid_transition(order_service):
    """Test invalid status transition is rejected."""
    request = CreateOrderRequest(
        symbol="BTC/USDT",
        type=OrderType.LIMIT,
        side=OrderSide.BUY,
        amount=0.5,
        price=50000.0,
    )
    order = order_service.create_order(request)

    # PENDING -> FILLED is invalid (must go through OPEN)
    with pytest.raises(OrderServiceError, match="invalid status transition"):
        order_service.update_order_status(order.id, OrderStatus.FILLED)


def test_update_order_status_rejects_filled_exceeding_amount(order_service):
    """Test filled amount cannot exceed order amount."""
    request = CreateOrderRequest(
        symbol="BTC/USDT",
        type=OrderType.LIMIT,
        side=OrderSide.BUY,
        amount=1.0,
        price=50000.0,
    )
    order = order_service.create_order(request)
    order_service.update_order_status(order.id, OrderStatus.OPEN)

    with pytest.raises(OrderServiceError, match="filled amount cannot exceed order amount"):
        order_service.update_order_status(order.id, OrderStatus.PARTIALLY_FILLED, filled=1.5)


# ------------------------------------------------------------------ #
# Test order cancellation
# ------------------------------------------------------------------ #
def test_cancel_order_releases_frozen_funds(order_service, account_service):
    """Test canceling a buy order releases frozen funds."""
    # Create buy order
    request = CreateOrderRequest(
        symbol="BTC/USDT",
        type=OrderType.LIMIT,
        side=OrderSide.BUY,
        amount=0.5,
        price=50000.0,
    )
    order = order_service.create_order(request)
    order_service.update_order_status(order.id, OrderStatus.OPEN)

    # Verify funds frozen
    account_before = account_service.get_account("USDT")
    assert account_before.frozen == 25000.0

    # Cancel order
    canceled = order_service.cancel_order(order.id)
    assert canceled.status == OrderStatus.CANCELED

    # Verify funds released
    account_after = account_service.get_account("USDT")
    assert account_after.frozen == 0.0
    assert account_after.available == 100000.0


def test_cancel_partially_filled_order_releases_unfilled_funds(order_service, account_service):
    """Test canceling a partially filled order releases only unfilled funds."""
    # Create buy order
    request = CreateOrderRequest(
        symbol="BTC/USDT",
        type=OrderType.LIMIT,
        side=OrderSide.BUY,
        amount=1.0,
        price=50000.0,
    )
    order = order_service.create_order(request)
    order_service.update_order_status(order.id, OrderStatus.OPEN)
    order_service.update_order_status(order.id, OrderStatus.PARTIALLY_FILLED, filled=0.3)

    # Cancel order
    canceled = order_service.cancel_order(order.id)
    assert canceled.status == OrderStatus.CANCELED

    # Verify only unfilled funds released (0.7 * 50000 = 35000)
    account = account_service.get_account("USDT")
    assert account.frozen == 0.0
    assert account.available == 100000.0 - 15000.0  # 0.3 * 50000 still consumed


def test_cancel_order_is_idempotent(order_service):
    """Test canceling an already canceled order is idempotent."""
    request = CreateOrderRequest(
        symbol="BTC/USDT",
        type=OrderType.LIMIT,
        side=OrderSide.BUY,
        amount=0.5,
        price=50000.0,
    )
    order = order_service.create_order(request)
    order_service.update_order_status(order.id, OrderStatus.OPEN)

    # Cancel once
    canceled1 = order_service.cancel_order(order.id)
    assert canceled1.status == OrderStatus.CANCELED

    # Cancel again (idempotent)
    canceled2 = order_service.cancel_order(order.id)
    assert canceled2.status == OrderStatus.CANCELED
    assert canceled2.id == canceled1.id


def test_cancel_filled_order_is_idempotent(order_service):
    """Test canceling a filled order returns current state."""
    request = CreateOrderRequest(
        symbol="BTC/USDT",
        type=OrderType.LIMIT,
        side=OrderSide.BUY,
        amount=0.5,
        price=50000.0,
    )
    order = order_service.create_order(request)
    order_service.update_order_status(order.id, OrderStatus.OPEN)
    order_service.update_order_status(order.id, OrderStatus.FILLED, filled=0.5)

    # Try to cancel (should return current state)
    result = order_service.cancel_order(order.id)
    assert result.status == OrderStatus.FILLED


def test_cancel_order_raises_when_not_found(order_service):
    """Test canceling non-existent order raises error."""
    with pytest.raises(OrderServiceError, match="order not found"):
        order_service.cancel_order("NONEXISTENT")

