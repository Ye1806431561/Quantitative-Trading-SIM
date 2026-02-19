"""Minimal strategy example used to validate lifecycle callbacks."""

from __future__ import annotations

from typing import Any, Mapping

from src.strategies.base import (
    LiveStrategy,
    StrategyContext,
    StrategyOrderEvent,
    StrategyTradeEvent,
)


class LifecycleProbeStrategy(LiveStrategy):
    """A no-op strategy that records lifecycle callback invocations."""

    def __init__(self) -> None:
        super().__init__(name="lifecycle_probe")
        self.events = []

    def on_initialize(self, context: StrategyContext) -> None:
        self.events.append(f"initialize:{context.symbol}:{context.timeframe}")

    def on_run(self, market_data: Mapping[str, Any]) -> Mapping[str, Any]:
        close = market_data.get("close")
        self.events.append(f"run:{close}")
        return {"action": "hold"}

    def on_order(self, order_event: StrategyOrderEvent) -> None:
        self.events.append(f"order:{order_event.order_id}:{order_event.status}")

    def on_trade(self, trade_event: StrategyTradeEvent) -> None:
        self.events.append(f"trade:{trade_event.trade_id}:{trade_event.amount}")

    def on_stop(self, reason: str | None) -> None:
        self.events.append(f"stop:{reason or 'manual'}")
