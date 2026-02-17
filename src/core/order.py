"""Order domain model and validation rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.core.enums import OrderSide, OrderStatus, OrderType
from src.core.validation import (
    DomainValidationError,
    optional_positive_number,
    optional_timestamp,
    require_enum,
    require_non_negative,
    require_positive_number,
    require_str,
)


@dataclass(frozen=True)
class Order:
    id: str
    symbol: str
    type: OrderType
    side: OrderSide
    price: float | None
    amount: float
    filled: float
    status: OrderStatus
    created_at: int | None
    updated_at: int | None

    @classmethod
    def validate(cls, data: Mapping[str, Any]) -> "Order":
        order_id = require_str(data, "id")
        symbol = require_str(data, "symbol")
        order_type = require_enum(data, "type", OrderType)
        side = require_enum(data, "side", OrderSide)
        price = optional_positive_number(data, "price")
        amount = require_positive_number(data, "amount")
        filled = require_non_negative(data, "filled")
        status = require_enum(data, "status", OrderStatus)
        created_at = optional_timestamp(data, "created_at")
        updated_at = optional_timestamp(data, "updated_at")

        if order_type is OrderType.MARKET:
            # price optional; if provided, must be positive (already checked)
            pass
        else:
            if price is None:
                raise DomainValidationError("price is required for non-market orders")

        if filled - amount > 1e-9:
            raise DomainValidationError("filled must not exceed amount")

        if amount <= 0:
            raise DomainValidationError("amount must be > 0")

        return cls(
            id=order_id,
            symbol=symbol,
            type=order_type,
            side=side,
            price=price,
            amount=amount,
            filled=filled,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
        )
