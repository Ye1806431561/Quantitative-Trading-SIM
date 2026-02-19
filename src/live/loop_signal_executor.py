"""Strategy signal executor and notification handler for real-time loop."""

from __future__ import annotations

from typing import Any, Mapping

from src.core.enums import OrderSide, OrderType
from src.core.limit_matching import LimitOrderMatchingEngine, LimitOrderRequest
from src.core.matching import MatchingEngine, MarketOrderRequest
from src.core.order_service import OrderService
from src.core.stop_trigger import StopTriggerEngine, TriggerOrderRequest
from src.core.trade_service import TradeService
from src.strategies.base import LiveStrategy, StrategyOrderEvent, StrategyTradeEvent


class LoopSignalExecutor:
    """Executes strategy signals and sends order/trade notifications."""

    def __init__(
        self,
        symbol: str,
        strategy: LiveStrategy,
        order_service: OrderService,
        trade_service: TradeService,
        market_matching: MatchingEngine,
        limit_matching: LimitOrderMatchingEngine,
        stop_trigger: StopTriggerEngine,
    ) -> None:
        self._symbol = symbol
        self._strategy = strategy
        self._order_service = order_service
        self._trade_service = trade_service
        self._market_matching = market_matching
        self._limit_matching = limit_matching
        self._stop_trigger = stop_trigger

    def execute_signal(self, signal: Mapping[str, Any]) -> None:
        """Execute trading signal from strategy."""
        action = signal.get("action")
        if not action:
            return

        try:
            if action in ("buy", "sell"):
                self._execute_order_signal(action, signal)
        except Exception as exc:
            # Log error but don't crash the loop
            print(f"Failed to execute strategy signal: {exc}")

    def notify_strategy_updates(self) -> None:
        """Notify strategy of recent order and trade updates."""
        try:
            # Get recent orders (last 10)
            recent_orders = self._order_service.list_orders(
                symbol=self._symbol,
                limit=10,
            )
            for order in recent_orders:
                self._strategy.notify_order(
                    StrategyOrderEvent(
                        order_id=order.id,
                        symbol=order.symbol,
                        status=order.status.value,
                        filled=order.filled,
                    )
                )

            # Get recent trades (last 10)
            for order in recent_orders:
                trades = self._trade_service.list_trades_for_order(order.id)
                for trade in trades:
                    self._strategy.notify_trade(
                        StrategyTradeEvent(
                            trade_id=trade.id,
                            order_id=trade.order_id,
                            symbol=trade.symbol,
                            price=trade.price,
                            amount=trade.amount,
                            fee=trade.fee,
                        )
                    )
        except Exception:
            # Silently ignore notification errors
            pass

    def _execute_order_signal(self, action: str, signal: Mapping[str, Any]) -> None:
        """Parse and execute a buy/sell signal."""
        side = OrderSide.BUY if action == "buy" else OrderSide.SELL
        amount = signal.get("amount")
        order_type = signal.get("type", "market")

        if amount is None or amount <= 0:
            return

        if order_type == "market":
            self._market_matching.execute_market_order(
                MarketOrderRequest(
                    symbol=self._symbol,
                    side=side,
                    amount=amount,
                )
            )
        elif order_type == "limit":
            self._execute_limit_signal(side, amount, signal)
        elif order_type in ("stop_loss", "take_profit"):
            self._execute_trigger_signal(side, amount, order_type, signal)

    def _execute_limit_signal(
        self, side: OrderSide, amount: float, signal: Mapping[str, Any]
    ) -> None:
        """Execute a limit order signal."""
        limit_price = signal.get("price")
        if limit_price and limit_price > 0:
            self._limit_matching.place_limit_order(
                LimitOrderRequest(
                    symbol=self._symbol,
                    side=side,
                    amount=amount,
                    limit_price=limit_price,
                )
            )

    def _execute_trigger_signal(
        self,
        side: OrderSide,
        amount: float,
        order_type: str,
        signal: Mapping[str, Any],
    ) -> None:
        """Execute a stop-loss or take-profit signal."""
        trigger_price = signal.get("trigger_price")
        if trigger_price and trigger_price > 0:
            self._stop_trigger.place_trigger_order(
                TriggerOrderRequest(
                    symbol=self._symbol,
                    type=OrderType.STOP_LOSS if order_type == "stop_loss" else OrderType.TAKE_PROFIT,
                    side=side,
                    amount=amount,
                    trigger_price=trigger_price,
                )
            )
