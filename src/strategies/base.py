"""Strategy lifecycle interface for live-mode execution."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Mapping

from src.core.enums import StrategyRunStatus


class StrategyLifecycleError(RuntimeError):
    """Raised when strategy lifecycle transitions are invalid."""


@dataclass(frozen=True)
class StrategyContext:
    """Runtime context shared with a strategy instance."""

    strategy_id: str
    symbol: str
    timeframe: str
    parameters: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StrategyOrderEvent:
    """Order callback payload for strategies."""

    order_id: str
    symbol: str
    status: str
    filled: float


@dataclass(frozen=True)
class StrategyTradeEvent:
    """Trade callback payload for strategies."""

    trade_id: str
    order_id: str
    symbol: str
    price: float
    amount: float
    fee: float


class LiveStrategy(ABC):
    """Base lifecycle contract for live-mode strategies."""

    def __init__(self, name: str) -> None:
        if not name.strip():
            raise StrategyLifecycleError("strategy name must not be empty")
        self._name = name.strip()
        self._status = StrategyRunStatus.PENDING
        self._context: StrategyContext | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def status(self) -> StrategyRunStatus:
        return self._status

    @property
    def context(self) -> StrategyContext:
        if self._context is None:
            raise StrategyLifecycleError("strategy has not been initialized")
        return self._context

    def initialize(self, context: StrategyContext) -> None:
        if self._status is not StrategyRunStatus.PENDING:
            raise StrategyLifecycleError("strategy can only be initialized once")
        self._context = context
        self.on_initialize(context)
        self._status = StrategyRunStatus.RUNNING

    def run(self, market_data: Mapping[str, Any]) -> Mapping[str, Any] | None:
        self._ensure_running("run")
        return self.on_run(market_data)

    def notify_order(self, order_event: StrategyOrderEvent) -> None:
        self._ensure_running("notify_order")
        self.on_order(order_event)

    def notify_trade(self, trade_event: StrategyTradeEvent) -> None:
        self._ensure_running("notify_trade")
        self.on_trade(trade_event)

    def stop(self, reason: str | None = None) -> None:
        if self._status is StrategyRunStatus.STOPPED:
            return
        if self._status is not StrategyRunStatus.RUNNING:
            raise StrategyLifecycleError("strategy must be running before stop")
        self.on_stop(reason)
        self._status = StrategyRunStatus.STOPPED

    def _ensure_running(self, operation: str) -> None:
        if self._status is not StrategyRunStatus.RUNNING:
            raise StrategyLifecycleError(f"strategy must be running before {operation}")

    @abstractmethod
    def on_initialize(self, context: StrategyContext) -> None:
        """Hook called once during initialization."""

    @abstractmethod
    def on_run(self, market_data: Mapping[str, Any]) -> Mapping[str, Any] | None:
        """Hook called on each strategy execution cycle."""

    def on_order(self, order_event: StrategyOrderEvent) -> None:
        """Hook called when an order status update arrives."""

    def on_trade(self, trade_event: StrategyTradeEvent) -> None:
        """Hook called when a trade callback arrives."""

    def on_stop(self, reason: str | None) -> None:
        """Hook called when strategy is requested to stop."""
