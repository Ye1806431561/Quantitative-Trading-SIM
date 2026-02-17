"""Candle domain model and validation rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.core.validation import (
    DomainValidationError,
    optional_timestamp,
    require_non_negative,
    require_positive_number,
    require_str,
)
from src.utils.config_defaults import ALLOWED_TIMEFRAMES


@dataclass(frozen=True)
class Candle:
    symbol: str
    timeframe: str
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    created_at: int | None

    @classmethod
    def validate(cls, data: Mapping[str, Any]) -> "Candle":
        symbol = require_str(data, "symbol")
        timeframe = require_str(data, "timeframe")
        if timeframe not in ALLOWED_TIMEFRAMES:
            raise DomainValidationError(f"timeframe must be one of {sorted(ALLOWED_TIMEFRAMES)}")

        timestamp = optional_timestamp(data, "timestamp")
        if timestamp is None:
            raise DomainValidationError("timestamp is required")

        open_ = require_positive_number(data, "open")
        high = require_positive_number(data, "high")
        low = require_positive_number(data, "low")
        close = require_positive_number(data, "close")
        volume = require_non_negative(data, "volume")
        created_at = optional_timestamp(data, "created_at")

        if high < low:
            raise DomainValidationError("high must be >= low")
        if not (low <= open_ <= high):
            raise DomainValidationError("open must be between low and high")
        if not (low <= close <= high):
            raise DomainValidationError("close must be between low and high")

        return cls(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=timestamp,
            open=open_,
            high=high,
            low=low,
            close=close,
            volume=volume,
            created_at=created_at,
        )
