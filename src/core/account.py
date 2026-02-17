"""Account domain model and validation rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.core.validation import (
    DomainValidationError,
    require_non_negative,
    require_str,
)


@dataclass(frozen=True)
class Account:
    currency: str
    balance: float
    available: float
    frozen: float

    @classmethod
    def validate(cls, data: Mapping[str, Any]) -> "Account":
        currency = require_str(data, "currency")
        balance = require_non_negative(data, "balance")
        available = require_non_negative(data, "available")
        frozen = require_non_negative(data, "frozen")

        if available + frozen - balance > 1e-9:
            raise DomainValidationError("available + frozen must not exceed balance")

        return cls(currency=currency, balance=balance, available=available, frozen=frozen)
