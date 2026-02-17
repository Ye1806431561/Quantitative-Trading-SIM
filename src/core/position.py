"""Position domain model and validation rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.core.validation import (
    DomainValidationError,
    optional_positive_number,
    optional_timestamp,
    require_non_negative,
    require_positive_number,
    require_str,
)


@dataclass(frozen=True)
class Position:
    symbol: str
    amount: float
    entry_price: float
    current_price: float | None
    unrealized_pnl: float | None
    realized_pnl: float
    opened_at: int | None
    updated_at: int | None

    @classmethod
    def validate(cls, data: Mapping[str, Any]) -> "Position":
        symbol = require_str(data, "symbol")
        amount = require_non_negative(data, "amount")
        entry_price = require_positive_number(data, "entry_price")
        current_price = optional_positive_number(data, "current_price")
        unrealized_pnl = data.get("unrealized_pnl")
        if unrealized_pnl is not None:
            if not isinstance(unrealized_pnl, (int, float)) or isinstance(unrealized_pnl, bool):
                raise DomainValidationError("unrealized_pnl must be a number")
            unrealized_pnl = float(unrealized_pnl)

        realized_raw = data.get("realized_pnl", 0.0)
        if not isinstance(realized_raw, (int, float)) or isinstance(realized_raw, bool):
            raise DomainValidationError("realized_pnl must be a number")
        realized_pnl = float(realized_raw)

        opened_at = optional_timestamp(data, "opened_at")
        updated_at = optional_timestamp(data, "updated_at")

        return cls(
            symbol=symbol,
            amount=amount,
            entry_price=entry_price,
            current_price=current_price,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=realized_pnl,
            opened_at=opened_at,
            updated_at=updated_at,
        )
