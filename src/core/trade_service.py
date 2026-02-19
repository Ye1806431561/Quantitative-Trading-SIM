"""Trade recording service linking trades to orders (Phase 1 Step 13)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Sequence

from src.core.database import SQLiteDatabase
from src.core.enums import OrderSide, OrderStatus
from src.core.order_service import OrderService
from src.core.order_state_machine import can_transition
from src.core.trade import Trade


class TradeServiceError(RuntimeError):
    """Raised when trade recording operations are invalid."""


@dataclass(frozen=True)
class CreateTradeRequest:
    """Request payload for recording a trade against an order."""

    order_id: str
    price: float
    amount: float
    fee: float
    timestamp: int | None = None


class TradeService:
    """Record trades and keep orders in sync (filled amount, status, funds)."""

    def __init__(
        self,
        database: SQLiteDatabase,
        order_service: OrderService,
    ) -> None:
        self._db = database
        self._order_service = order_service

    def record_trade(self, request: CreateTradeRequest) -> Trade:
        """Persist a trade row, update order filled/status, and consume funds."""
        if not request.order_id or not request.order_id.strip():
            raise TradeServiceError("order_id must not be empty")
        if request.price <= 0:
            raise TradeServiceError("price must be > 0")
        if request.amount <= 0:
            raise TradeServiceError("amount must be > 0")
        if request.fee < 0:
            raise TradeServiceError("fee must be >= 0")

        trade_timestamp = (
            int(request.timestamp) if request.timestamp is not None else int(time.time() * 1000)
        )

        with self._db.transaction() as tx:
            # Fetch order
            row = tx.execute(
                "SELECT id, symbol, type, side, price, amount, filled, status, created_at, updated_at "
                "FROM orders WHERE id = ?;",
                (request.order_id,),
            ).fetchone()
            if row is None:
                raise TradeServiceError(f"order not found: {request.order_id}")

            order = self._order_service.get_order(request.order_id)

            # Enforce order is in a fillable state
            if order.status not in (OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED):
                raise TradeServiceError(
                    f"order status must be open or partially_filled, got {order.status.value}"
                )

            new_filled = order.filled + request.amount
            if new_filled > order.amount:
                raise TradeServiceError("trade amount would overfill order")

            # Insert trade
            tx.execute(
                """
                INSERT INTO trades(order_id, symbol, side, price, amount, fee, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    order.id,
                    order.symbol,
                    order.side.value,
                    request.price,
                    request.amount,
                    request.fee,
                    trade_timestamp,
                ),
            )

            # Consume frozen funds for buy orders (based on order price)
            if order.side == OrderSide.BUY:
                if order.price is None:
                    raise TradeServiceError("order price is required to consume funds")
                funds_to_consume = request.amount * order.price
                base_currency = self._order_service._extract_quote_currency(order.symbol)  # noqa: SLF001
                self._order_service._consume_frozen_funds(tx, base_currency, funds_to_consume)  # noqa: SLF001

            # Update order filled + status
            new_status = OrderStatus.FILLED if new_filled == order.amount else OrderStatus.PARTIALLY_FILLED
            if not can_transition(order.status, new_status):
                raise TradeServiceError(
                    f"invalid status transition: {order.status.value} -> {new_status.value}"
                )
            timestamp = int(time.time() * 1000)
            tx.execute(
                """
                UPDATE orders
                SET filled = ?, status = ?, updated_at = ?
                WHERE id = ?;
                """,
                (new_filled, new_status.value, timestamp, order.id),
            )

        return Trade.validate(
            {
                "order_id": order.id,
                "symbol": order.symbol,
                "side": order.side.value,
                "price": request.price,
                "amount": request.amount,
                "fee": request.fee,
                "timestamp": trade_timestamp,
            }
        )

    def list_trades_for_order(self, order_id: str) -> Sequence[Trade]:
        """Return trades linked to a specific order, newest first."""
        if not order_id or not order_id.strip():
            raise TradeServiceError("order_id must not be empty")

        with self._db.transaction() as tx:
            rows = tx.execute(
                """
                SELECT order_id, symbol, side, price, amount, fee, timestamp
                FROM trades
                WHERE order_id = ?
                ORDER BY timestamp DESC, id DESC;
                """,
                (order_id,),
            ).fetchall()

        return [Trade.validate(dict(row)) for row in rows]
