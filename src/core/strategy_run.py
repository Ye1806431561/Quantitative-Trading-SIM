"""Strategy run domain model and validation rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.core.enums import StrategyRunStatus
from src.core.validation import DomainValidationError, optional_timestamp, require_enum, require_non_negative, require_str


@dataclass(frozen=True)
class StrategyRun:
    strategy_name: str
    symbol: str
    start_time: int | None
    end_time: int | None
    initial_capital: float
    final_capital: float | None
    total_return: float | None
    max_drawdown: float | None
    sharpe_ratio: float | None
    status: StrategyRunStatus

    @classmethod
    def validate(cls, data: Mapping[str, Any]) -> "StrategyRun":
        strategy_name = require_str(data, "strategy_name")
        symbol = require_str(data, "symbol")
        start_time = optional_timestamp(data, "start_time")
        end_time = optional_timestamp(data, "end_time")
        initial_capital = require_non_negative(data, "initial_capital")
        final_capital = data.get("final_capital")
        if final_capital is not None:
            final_capital = require_non_negative({"final_capital": final_capital}, "final_capital")

        total_return = data.get("total_return")
        if total_return is not None:
            if not isinstance(total_return, (int, float)) or isinstance(total_return, bool):
                raise DomainValidationError("total_return must be a number")
            total_return = float(total_return)

        max_drawdown = data.get("max_drawdown")
        if max_drawdown is not None:
            max_drawdown = require_non_negative({"max_drawdown": max_drawdown}, "max_drawdown")
            if max_drawdown > 1:
                raise DomainValidationError("max_drawdown must be <= 1")

        sharpe_ratio = data.get("sharpe_ratio")
        if sharpe_ratio is not None:
            if not isinstance(sharpe_ratio, (int, float)) or isinstance(sharpe_ratio, bool):
                raise DomainValidationError("sharpe_ratio must be a number")
            sharpe_ratio = float(sharpe_ratio)

        status = require_enum(data, "status", StrategyRunStatus)

        if end_time is not None and start_time is not None and end_time < start_time:
            raise DomainValidationError("end_time must be >= start_time")

        return cls(
            strategy_name=strategy_name,
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            status=status,
        )
