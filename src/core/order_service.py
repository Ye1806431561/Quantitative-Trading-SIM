"""Order persistence interface with idempotent operations."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Sequence

from src.core.account_service import AccountService
from src.core.database import SQLiteDatabase
from src.core.enums import OrderSide, OrderStatus, OrderType
from src.core.order import Order


class OrderServiceError(RuntimeError):
    """Raised when order lifecycle operations are invalid."""


@dataclass(frozen=True)
class CreateOrderRequest:
    """Request to create a new order."""

    symbol: str
    type: OrderType
    side: OrderSide
    amount: float
    price: float | None = None


class OrderService:
    """Manage orders table with idempotent create/update/cancel operations."""

    def __init__(self, database: SQLiteDatabase, account_service: AccountService) -> None:
        self._db = database
        self._account_service = account_service

    # ------------------------------------------------------------------ #
    # Order creation
    # ------------------------------------------------------------------ #
    def create_order(self, request: CreateOrderRequest) -> Order:
        """Create a new order with frozen funds (for buy orders).

        Idempotent: if order_id already exists, return existing order.
        """
        # Validate request
        if not request.symbol or not request.symbol.strip():
            raise OrderServiceError("symbol must not be empty")
        if request.amount <= 0:
            raise OrderServiceError("amount must be > 0")
        if request.type != OrderType.MARKET and request.price is None:
            raise OrderServiceError("price is required for non-market orders")
        if request.price is not None and request.price <= 0:
            raise OrderServiceError("price must be > 0")

        # Generate unique order ID
        order_id = self._generate_order_id()
        timestamp = int(time.time() * 1000)

        with self._db.transaction() as tx:
            # Check if order already exists (idempotent)
            existing = tx.execute(
                "SELECT id, symbol, type, side, price, amount, filled, status, created_at, updated_at "
                "FROM orders WHERE id = ?;",
                (order_id,),
            ).fetchone()
            if existing is not None:
                return Order.validate(dict(existing))

            # Freeze funds for buy orders
            if request.side == OrderSide.BUY:
                # Calculate required funds
                if request.type == OrderType.MARKET:
                    # For market orders, we need to estimate cost
                    # In real scenario, we'd use current market price
                    # For now, use price if provided, otherwise raise error
                    if request.price is None:
                        raise OrderServiceError(
                            "price must be provided for market buy orders in simulation"
                        )
                    required_funds = request.amount * request.price
                else:
                    required_funds = request.amount * request.price  # type: ignore

                # Extract base currency from symbol (e.g., BTC/USDT -> USDT)
                base_currency = self._extract_quote_currency(request.symbol)
                try:
                    self._account_service.freeze_funds(base_currency, required_funds)
                except Exception as e:
                    raise OrderServiceError(f"failed to freeze funds: {e}") from e

            # Insert order
            tx.execute(
                """
                INSERT INTO orders(id, symbol, type, side, price, amount, filled, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?);
                """,
                (
                    order_id,
                    request.symbol.strip(),
                    request.type.value,
                    request.side.value,
                    request.price,
                    request.amount,
                    OrderStatus.PENDING.value,
                    timestamp,
                    timestamp,
                ),
            )

        return self.get_order(order_id)

    # ------------------------------------------------------------------ #
    # Order queries
    # ------------------------------------------------------------------ #
    def get_order(self, order_id: str) -> Order:
        """Retrieve order by ID."""
        with self._db.transaction() as tx:
            row = tx.execute(
                "SELECT id, symbol, type, side, price, amount, filled, status, created_at, updated_at "
                "FROM orders WHERE id = ?;",
                (order_id,),
            ).fetchone()
        if row is None:
            raise OrderServiceError(f"order not found: {order_id}")
        return Order.validate(dict(row))

    def list_orders(
        self,
        symbol: str | None = None,
        status: OrderStatus | None = None,
        limit: int | None = None,
    ) -> list[Order]:
        """List orders with optional filters."""
        query = """
            SELECT id, symbol, type, side, price, amount, filled, status, created_at, updated_at
            FROM orders
            WHERE 1=1
        """
        params: list[str | int] = []

        if symbol is not None:
            query += " AND symbol = ?"
            params.append(symbol)
        if status is not None:
            query += " AND status = ?"
            params.append(status.value)

        query += " ORDER BY created_at DESC"

        if limit is not None:
            if limit <= 0:
                raise OrderServiceError("limit must be > 0")
            query += " LIMIT ?"
            params.append(limit)

        with self._db.transaction() as tx:
            rows = tx.execute(query, params).fetchall()

        return [Order.validate(dict(row)) for row in rows]

    # ------------------------------------------------------------------ #
    # Order status updates
    # ------------------------------------------------------------------ #
    def update_order_status(
        self,
        order_id: str,
        new_status: OrderStatus,
        filled: float | None = None,
    ) -> Order:
        """Update order status with state transition validation.

        Valid transitions:
        - PENDING -> OPEN, REJECTED
        - OPEN -> PARTIALLY_FILLED, FILLED, CANCELED
        - PARTIALLY_FILLED -> FILLED, CANCELED
        
        For buy orders, when filled amount increases, the corresponding frozen funds
        are consumed (removed from both frozen and balance).
        """
        with self._db.transaction() as tx:
            # Get current order
            row = tx.execute(
                "SELECT id, symbol, type, side, price, amount, filled, status, created_at, updated_at "
                "FROM orders WHERE id = ?;",
                (order_id,),
            ).fetchone()
            if row is None:
                raise OrderServiceError(f"order not found: {order_id}")

            order = Order.validate(dict(row))
            current_status = order.status

            # Validate state transition
            if not self._is_valid_transition(current_status, new_status):
                raise OrderServiceError(
                    f"invalid status transition: {current_status.value} -> {new_status.value}"
                )

            # Update filled amount if provided
            new_filled = filled if filled is not None else order.filled
            if new_filled < 0:
                raise OrderServiceError("filled amount must be non-negative")
            if new_filled > order.amount:
                raise OrderServiceError("filled amount cannot exceed order amount")

            # Consume frozen funds for filled portion (buy orders only)
            if order.side == OrderSide.BUY and new_filled > order.filled:
                filled_delta = new_filled - order.filled
                if order.price is None:
                    raise OrderServiceError("cannot consume funds: order price is None")
                funds_to_consume = filled_delta * order.price
                base_currency = self._extract_quote_currency(order.symbol)
                
                # Consume from frozen funds (reduce both frozen and balance)
                try:
                    account = self._account_service.get_account(base_currency)
                    if account.frozen < funds_to_consume:
                        raise OrderServiceError("insufficient frozen funds to consume")
                    
                    # Manually update account: reduce frozen and balance
                    with tx:
                        tx.execute(
                            """
                            UPDATE accounts
                            SET frozen = frozen - ?, balance = balance - ?, updated_at = CURRENT_TIMESTAMP
                            WHERE currency = ?;
                            """,
                            (funds_to_consume, funds_to_consume, base_currency),
                        )
                except Exception as e:
                    raise OrderServiceError(f"failed to consume funds for filled portion: {e}") from e

            # Update database
            timestamp = int(time.time() * 1000)
            tx.execute(
                """
                UPDATE orders
                SET status = ?, filled = ?, updated_at = ?
                WHERE id = ?;
                """,
                (new_status.value, new_filled, timestamp, order_id),
            )

        return self.get_order(order_id)

    def cancel_order(self, order_id: str) -> Order:
        """Cancel an order and release frozen funds.

        Idempotent: if order is already canceled/filled/rejected, return current state.
        """
        with self._db.transaction() as tx:
            # Get current order
            row = tx.execute(
                "SELECT id, symbol, type, side, price, amount, filled, status, created_at, updated_at "
                "FROM orders WHERE id = ?;",
                (order_id,),
            ).fetchone()
            if row is None:
                raise OrderServiceError(f"order not found: {order_id}")

            order = Order.validate(dict(row))

            # Idempotent: already in terminal state
            if order.status in (OrderStatus.CANCELED, OrderStatus.FILLED, OrderStatus.REJECTED):
                return order

            # Validate cancellable
            if order.status not in (OrderStatus.PENDING, OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED):
                raise OrderServiceError(f"cannot cancel order in status: {order.status.value}")

            # Release frozen funds for buy orders
            if order.side == OrderSide.BUY:
                unfilled_amount = order.amount - order.filled
                if unfilled_amount > 0:
                    if order.price is None:
                        raise OrderServiceError("cannot release funds: order price is None")
                    frozen_funds = unfilled_amount * order.price
                    base_currency = self._extract_quote_currency(order.symbol)
                    try:
                        self._account_service.release_funds(base_currency, frozen_funds)
                    except Exception as e:
                        raise OrderServiceError(f"failed to release funds: {e}") from e

            # Update status to CANCELED
            timestamp = int(time.time() * 1000)
            tx.execute(
                """
                UPDATE orders
                SET status = ?, updated_at = ?
                WHERE id = ?;
                """,
                (OrderStatus.CANCELED.value, timestamp, order_id),
            )

        return self.get_order(order_id)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _generate_order_id() -> str:
        """Generate unique order ID."""
        return f"ORD-{uuid.uuid4().hex[:16].upper()}"

    @staticmethod
    def _extract_quote_currency(symbol: str) -> str:
        """Extract quote currency from symbol (e.g., BTC/USDT -> USDT)."""
        if "/" not in symbol:
            raise OrderServiceError(f"invalid symbol format: {symbol}")
        parts = symbol.split("/")
        if len(parts) != 2:
            raise OrderServiceError(f"invalid symbol format: {symbol}")
        return parts[1].strip()

    @staticmethod
    def _is_valid_transition(current: OrderStatus, new: OrderStatus) -> bool:
        """Validate order status transition."""
        valid_transitions = {
            OrderStatus.PENDING: {OrderStatus.OPEN, OrderStatus.REJECTED},
            OrderStatus.OPEN: {OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED, OrderStatus.CANCELED},
            OrderStatus.PARTIALLY_FILLED: {OrderStatus.FILLED, OrderStatus.CANCELED},
            OrderStatus.FILLED: set(),
            OrderStatus.CANCELED: set(),
            OrderStatus.REJECTED: set(),
        }
        return new in valid_transitions.get(current, set())

