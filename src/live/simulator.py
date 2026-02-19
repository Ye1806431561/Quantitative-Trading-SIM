"""Lightweight strategy lifecycle driver for live-mode callbacks."""

from __future__ import annotations

from typing import Any, Mapping

from src.strategies.base import (
    LiveStrategy,
    StrategyContext,
    StrategyLifecycleError,
    StrategyOrderEvent,
    StrategyTradeEvent,
)


class StrategyLifecycleDriver:
    """Drive lifecycle callbacks for a single live strategy instance."""

    def __init__(self, strategy: LiveStrategy, context: StrategyContext) -> None:
        self._strategy = strategy
        self._context = context
        self._started = False

    @property
    def strategy(self) -> LiveStrategy:
        return self._strategy

    def start(self) -> None:
        self._strategy.initialize(self._context)
        self._started = True

    def on_market_data(self, market_data: Mapping[str, Any]) -> Mapping[str, Any] | None:
        self._ensure_started("on_market_data")
        return self._strategy.run(market_data)

    def on_order_update(self, order_event: StrategyOrderEvent) -> None:
        self._ensure_started("on_order_update")
        self._strategy.notify_order(order_event)

    def on_trade_update(self, trade_event: StrategyTradeEvent) -> None:
        self._ensure_started("on_trade_update")
        self._strategy.notify_trade(trade_event)

    def stop(self, reason: str | None = None) -> None:
        self._ensure_started("stop")
        self._strategy.stop(reason=reason)

    def _ensure_started(self, operation: str) -> None:
        if not self._started:
            raise StrategyLifecycleError(
                f"strategy driver must be started before {operation}; call driver.start() first"
            )
