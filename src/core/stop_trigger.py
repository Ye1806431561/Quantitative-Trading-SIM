"""Stop-loss / take-profit trigger engine (Phase 2 Step 21)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.core.account_service import AccountService
from src.core.database import SQLiteDatabase
from src.core.enums import OrderSide, OrderStatus, OrderType
from src.core.execution_cost import ExecutionCostProfile, LiquidityRole
from src.core.limit_settlement import LimitOrderSettlement, LimitOrderSettlementError
from src.core.order import Order
from src.core.order_service import CreateOrderRequest, OrderService, OrderServiceError
from src.core.risk import RiskControl, RiskControlError, RiskLimits
from src.core.trade import Trade
from src.core.trade_service import CreateTradeRequest, TradeService, TradeServiceError
from src.data.realtime_payloads import RealtimeMarketSnapshot


class StopTriggerError(RuntimeError):
    """Raised when stop-loss / take-profit trigger operations fail."""


class LatestPriceReader(Protocol):
    """Interface required to fetch latest market price."""

    def get_latest_price(self, symbol: str) -> RealtimeMarketSnapshot:
        ...


@dataclass(frozen=True)
class TriggerOrderRequest:
    """Input payload for one stop-loss / take-profit order."""

    symbol: str
    type: OrderType
    side: OrderSide
    amount: float
    trigger_price: float


@dataclass(frozen=True)
class TriggerMatchResult:
    """One triggered order result."""

    order: Order
    trade: Trade
    execution_price: float
    matched_at_ms: int


@dataclass(frozen=True)
class TriggerSweepResult:
    """Trigger-scan summary for one symbol."""

    symbol: str
    latest_price: float
    checked_count: int
    matched: tuple[TriggerMatchResult, ...]
    remaining_order_ids: tuple[str, ...]


class StopTriggerEngine:
    """Manage stop-loss / take-profit orders and trigger fills by latest price."""

    def __init__(
        self,
        database: SQLiteDatabase,
        account_service: AccountService,
        order_service: OrderService,
        trade_service: TradeService,
        market_reader: LatestPriceReader,
        cost_profile: ExecutionCostProfile | None = None,
        risk_limits: RiskLimits | None = None,
    ) -> None:
        self._db = database
        self._order_service = order_service
        self._trade_service = trade_service
        self._market_reader = market_reader
        self._settlement = LimitOrderSettlement(account_service)
        self._cost_profile = cost_profile or ExecutionCostProfile()
        self._risk_control = RiskControl(database, account_service, limits=risk_limits)

    def place_trigger_order(self, request: TriggerOrderRequest) -> Order:
        """Create one trigger order and move it into OPEN state."""
        symbol = request.symbol.strip()
        if not symbol:
            raise StopTriggerError("symbol must not be empty")
        if request.amount <= 0:
            raise StopTriggerError("amount must be > 0")
        if request.trigger_price <= 0:
            raise StopTriggerError("trigger_price must be > 0")
        if request.type not in (OrderType.STOP_LOSS, OrderType.TAKE_PROFIT):
            raise StopTriggerError("type must be stop_loss or take_profit")
        try:
            self._risk_control.check_pre_order(
                symbol=symbol,
                side=request.side,
                amount=request.amount,
                reference_price=request.trigger_price,
            )
        except RiskControlError as exc:
            raise StopTriggerError(f"risk check failed: {exc}") from exc

        with self._db.transaction() as tx:
            try:
                base_currency, _ = self._settlement.ensure_accounts(symbol)
                if request.side == OrderSide.SELL and not self._settlement.has_sell_capacity(
                    tx=tx,
                    symbol=symbol,
                    base_currency=base_currency,
                    amount=request.amount,
                ):
                    raise StopTriggerError("insufficient base asset balance for sell trigger order")

                order = self._order_service.create_order(
                    CreateOrderRequest(
                        symbol=symbol,
                        type=request.type,
                        side=request.side,
                        amount=request.amount,
                        price=request.trigger_price,
                    )
                )
                return self._order_service.update_order_status(order.id, OrderStatus.OPEN)
            except (OrderServiceError, LimitOrderSettlementError) as exc:
                raise StopTriggerError(f"failed to place trigger order: {exc}") from exc

    def process_trigger_orders(self, symbol: str) -> TriggerSweepResult:
        """Scan one symbol and fill all triggered stop-loss / take-profit orders."""
        symbol_filter = symbol.strip()
        if not symbol_filter:
            raise StopTriggerError("symbol must not be empty")

        latest_price, matched_at_ms = self._resolve_latest_price(symbol_filter)
        matched_results: list[TriggerMatchResult] = []

        with self._db.transaction() as tx:
            queue = self._load_open_trigger_orders(tx, symbol_filter)
            for order in queue:
                if not self._is_triggered(order, latest_price):
                    continue
                if order.price is None:
                    continue

                remaining_amount = order.amount - order.filled
                if remaining_amount <= 1e-12:
                    continue

                try:
                    base_currency, quote_currency = self._settlement.split_symbol(order.symbol)
                    if order.side == OrderSide.SELL and not self._settlement.has_sell_capacity(
                        tx=tx,
                        symbol=order.symbol,
                        base_currency=base_currency,
                        amount=remaining_amount,
                    ):
                        continue

                    execution_price = self._cost_profile.apply_slippage(
                        reference_price=order.price,
                        side=order.side,
                    )
                    trade_fee = self._cost_profile.calculate_fee(
                        execution_price=execution_price,
                        amount=remaining_amount,
                        liquidity=LiquidityRole.TAKER,
                    )
                    trade = self._trade_service.record_trade(
                        CreateTradeRequest(
                            order_id=order.id,
                            price=execution_price,
                            amount=remaining_amount,
                            fee=trade_fee,
                            timestamp=matched_at_ms,
                        )
                    )
                    self._settlement.settle(
                        tx=tx,
                        symbol=order.symbol,
                        side=order.side,
                        amount=remaining_amount,
                        execution_price=execution_price,
                        base_currency=base_currency,
                        quote_currency=quote_currency,
                    )
                except (TradeServiceError, LimitOrderSettlementError) as exc:
                    raise StopTriggerError(f"failed to process trigger order {order.id}: {exc}") from exc

                matched_results.append(
                    TriggerMatchResult(
                        order=self._order_service.get_order(order.id),
                        trade=trade,
                        execution_price=execution_price,
                        matched_at_ms=matched_at_ms,
                    )
                )

            remaining_ids = tuple(item.id for item in self._load_open_trigger_orders(tx, symbol_filter))

        return TriggerSweepResult(
            symbol=symbol_filter,
            latest_price=latest_price,
            checked_count=len(queue),
            matched=tuple(matched_results),
            remaining_order_ids=remaining_ids,
        )

    def _load_open_trigger_orders(self, tx, symbol: str) -> list[Order]:
        rows = tx.execute(
            """
            SELECT id, symbol, type, side, price, amount, filled, status, created_at, updated_at
            FROM orders
            WHERE symbol = ?
              AND type IN (?, ?)
              AND status IN (?, ?)
            ORDER BY created_at ASC, id ASC;
            """,
            (
                symbol,
                OrderType.STOP_LOSS.value,
                OrderType.TAKE_PROFIT.value,
                OrderStatus.OPEN.value,
                OrderStatus.PARTIALLY_FILLED.value,
            ),
        ).fetchall()
        return [Order.validate(dict(row)) for row in rows]

    @staticmethod
    def _is_triggered(order: Order, latest_price: float) -> bool:
        if order.price is None:
            return False
        if order.type == OrderType.STOP_LOSS:
            if order.side == OrderSide.SELL:
                return latest_price <= order.price
            return latest_price >= order.price
        if order.type == OrderType.TAKE_PROFIT:
            if order.side == OrderSide.SELL:
                return latest_price >= order.price
            return latest_price <= order.price
        return False

    def _resolve_latest_price(self, symbol: str) -> tuple[float, int]:
        try:
            snapshot = self._market_reader.get_latest_price(symbol)
        except Exception as exc:  # pragma: no cover - defensive wrapper
            raise StopTriggerError(f"failed to fetch latest price for {symbol}: {exc}") from exc

        raw_price = snapshot.data.get("last_price")
        if raw_price is None:
            raise StopTriggerError(f"missing latest price for symbol {symbol}")
        if not isinstance(raw_price, (int, float)) or isinstance(raw_price, bool):
            raise StopTriggerError("snapshot.data.last_price must be numeric")
        latest_price = float(raw_price)
        if latest_price <= 0:
            raise StopTriggerError(f"latest price must be > 0 for symbol {symbol}")
        return latest_price, int(snapshot.fetched_at_ms)
