"""Trade domain model and validation rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.core.enums import TradeSide
from src.core.validation import (
    DomainValidationError,
    require_enum,
    optional_timestamp,
    require_non_negative,
    require_positive_number,
    require_str,
)


@dataclass(frozen=True)
class Trade:
    order_id: str
    symbol: str
    side: TradeSide
    price: float
    amount: float
    fee: float
    timestamp: int | None

    @classmethod
    def validate(cls, data: Mapping[str, Any]) -> "Trade":
        order_id = require_str(data, "order_id")
        symbol = require_str(data, "symbol")
        side = require_enum(data, "side", TradeSide)
        price = require_positive_number(data, "price")
        amount = require_positive_number(data, "amount")
        fee = require_non_negative(data, "fee")
        timestamp = optional_timestamp(data, "timestamp")

        if fee < 0:
            raise DomainValidationError("fee must be >= 0")

        return cls(
            order_id=order_id,
            symbol=symbol,
            side=side,
            price=price,
            amount=amount,
            fee=fee,
            timestamp=timestamp,
        )
