"""Limit-order queue and trigger-based matching (Phase 2 Step 20)."""

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

class LimitOrderMatchingError(RuntimeError):
    """Raised when limit-order queue operations fail."""

class LatestPriceReader(Protocol):
    """Interface required to fetch latest market price."""

    def get_latest_price(self, symbol: str) -> RealtimeMarketSnapshot:
        ...

@dataclass(frozen=True)
class LimitOrderRequest:
    """Input payload for placing a limit order into queue."""

    symbol: str
    side: OrderSide
    amount: float
    limit_price: float

@dataclass(frozen=True)
class LimitOrderMatchResult:
    """One filled order produced by queue sweep."""

    order: Order
    trade: Trade
    execution_price: float
    matched_at_ms: int

@dataclass(frozen=True)
class LimitOrderSweepResult:
    """Queue sweep summary for one symbol."""

    symbol: str
    latest_price: float
    checked_count: int
    matched: tuple[LimitOrderMatchResult, ...]
    remaining_order_ids: tuple[str, ...]

class LimitOrderMatchingEngine:
    """Manage limit-order queue and match orders when price crosses trigger."""

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
        self._account_service = account_service
        self._order_service = order_service
        self._trade_service = trade_service
        self._market_reader = market_reader
        self._settlement = LimitOrderSettlement(account_service)
        self._cost_profile = cost_profile or ExecutionCostProfile()
        self._risk_control = RiskControl(database, account_service, limits=risk_limits)

    def place_limit_order(self, request: LimitOrderRequest) -> Order:
        """Create one limit order and move it into OPEN queue state."""
        symbol = request.symbol.strip()
        if not symbol:
            raise LimitOrderMatchingError("symbol must not be empty")
        if request.amount <= 0:
            raise LimitOrderMatchingError("amount must be > 0")
        if request.limit_price <= 0:
            raise LimitOrderMatchingError("limit_price must be > 0")
        try:
            self._risk_control.check_pre_order(symbol=symbol, side=request.side, amount=request.amount, reference_price=request.limit_price)
        except RiskControlError as exc:
            raise LimitOrderMatchingError(f"risk check failed: {exc}") from exc

        with self._db.transaction() as tx:
            try:
                base_currency, _ = self._settlement.ensure_accounts(symbol)
                if request.side == OrderSide.SELL and not self._settlement.has_sell_capacity(
                    tx=tx,
                    symbol=symbol,
                    base_currency=base_currency,
                    amount=request.amount,
                ):
                    raise LimitOrderMatchingError("insufficient base asset balance for sell limit order")
                order = self._order_service.create_order(
                    CreateOrderRequest(
                        symbol=symbol,
                        type=OrderType.LIMIT,
                        side=request.side,
                        amount=request.amount,
                        price=request.limit_price,
                    )
                )
                return self._order_service.update_order_status(order.id, OrderStatus.OPEN)
            except (OrderServiceError, LimitOrderSettlementError) as exc:
                raise LimitOrderMatchingError(f"failed to place limit order: {exc}") from exc

    def list_open_limit_orders(self, symbol: str | None = None) -> list[Order]:
        """Return queued limit orders sorted by price-time priority."""
        symbol_filter = symbol.strip() if symbol is not None else None
        with self._db.transaction() as tx:
            return self._load_open_limit_orders(tx, symbol_filter)

    def process_limit_order_queue(self, symbol: str) -> LimitOrderSweepResult:
        """Sweep one symbol queue and fill all triggered limit orders."""
        symbol_filter = symbol.strip()
        if not symbol_filter:
            raise LimitOrderMatchingError("symbol must not be empty")

        latest_price, matched_at_ms = self._resolve_latest_price(symbol_filter)
        matched_results: list[LimitOrderMatchResult] = []

        with self._db.transaction() as tx:
            queue = self._load_open_limit_orders(tx, symbol_filter)
            for order in queue:
                if not self._is_price_triggered(order, latest_price):
                    continue
                if order.price is None:
                    continue

                remaining_amount = order.amount - order.filled
                if remaining_amount <= 1e-12:
                    continue

                try:
                    base_currency, quote_currency = self._settlement.split_symbol(order.symbol)
                    reference_price = self._resolve_execution_price(order, latest_price)
                    execution_price = self._cost_profile.apply_slippage_with_limit(
                        reference_price=reference_price,
                        side=order.side,
                        limit_price=order.price,
                    )
                    trade_fee = self._cost_profile.calculate_fee(
                        execution_price=execution_price,
                        amount=remaining_amount,
                        liquidity=LiquidityRole.MAKER,
                    )
                    if order.side == OrderSide.SELL and not self._settlement.has_sell_capacity(
                        tx=tx,
                        symbol=order.symbol,
                        base_currency=base_currency,
                        amount=remaining_amount,
                    ):
                        # Keep order in queue if inventory is not enough yet.
                        continue

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
                    self._apply_buy_price_improvement_refund(
                        side=order.side,
                        limit_price=order.price,
                        execution_price=execution_price,
                        amount=remaining_amount,
                        quote_currency=quote_currency,
                    )
                except (TradeServiceError, LimitOrderSettlementError) as exc:
                    raise LimitOrderMatchingError(f"failed to process limit order {order.id}: {exc}") from exc

                matched_results.append(
                    LimitOrderMatchResult(
                        order=self._order_service.get_order(order.id),
                        trade=trade,
                        execution_price=execution_price,
                        matched_at_ms=matched_at_ms,
                    )
                )

            remaining_ids = tuple(item.id for item in self._load_open_limit_orders(tx, symbol_filter))

        return LimitOrderSweepResult(
            symbol=symbol_filter,
            latest_price=latest_price,
            checked_count=len(queue),
            matched=tuple(matched_results),
            remaining_order_ids=remaining_ids,
        )

    def _load_open_limit_orders(self, tx, symbol: str | None) -> list[Order]:
        query = """
            SELECT id, symbol, type, side, price, amount, filled, status, created_at, updated_at
            FROM orders
            WHERE type = ?
              AND status IN (?, ?)
        """
        params: list[str] = [
            OrderType.LIMIT.value,
            OrderStatus.OPEN.value,
            OrderStatus.PARTIALLY_FILLED.value,
        ]

        if symbol is not None:
            query += " AND symbol = ?"
            params.append(symbol)

        rows = tx.execute(query, params).fetchall()
        orders = [Order.validate(dict(row)) for row in rows]

        # Price-time priority queue: buy(high->low), sell(low->high), tie by creation time.
        buy_orders = sorted(
            (order for order in orders if order.side == OrderSide.BUY),
            key=lambda order: (
                -(order.price if order.price is not None else 0.0),
                order.created_at if order.created_at is not None else 0,
                order.id,
            ),
        )
        sell_orders = sorted(
            (order for order in orders if order.side == OrderSide.SELL),
            key=lambda order: (
                order.price if order.price is not None else 0.0,
                order.created_at if order.created_at is not None else 0,
                order.id,
            ),
        )
        return [*buy_orders, *sell_orders]

    @staticmethod
    def _is_price_triggered(order: Order, latest_price: float) -> bool:
        if order.price is None:
            return False
        if order.side == OrderSide.BUY:
            return latest_price <= order.price
        return latest_price >= order.price

    def _resolve_latest_price(self, symbol: str) -> tuple[float, int]:
        try:
            snapshot = self._market_reader.get_latest_price(symbol)
        except Exception as exc:  # pragma: no cover - defensive wrapper
            raise LimitOrderMatchingError(f"failed to fetch latest price for {symbol}: {exc}") from exc

        raw_price = snapshot.data.get("last_price")
        if raw_price is None:
            raise LimitOrderMatchingError(f"missing latest price for symbol {symbol}")
        if not isinstance(raw_price, (int, float)) or isinstance(raw_price, bool):
            raise LimitOrderMatchingError("snapshot.data.last_price must be numeric")
        latest_price = float(raw_price)
        if latest_price <= 0:
            raise LimitOrderMatchingError(f"latest price must be > 0 for symbol {symbol}")
        return latest_price, int(snapshot.fetched_at_ms)

    @staticmethod
    def _resolve_execution_price(order: Order, latest_price: float) -> float:
        if order.price is None:
            return latest_price
        if order.side == OrderSide.BUY:
            return min(order.price, latest_price)
        return max(order.price, latest_price)

    def _apply_buy_price_improvement_refund(
        self,
        *,
        side: OrderSide,
        limit_price: float | None,
        execution_price: float,
        amount: float,
        quote_currency: str,
    ) -> None:
        if side != OrderSide.BUY or limit_price is None:
            return
        if execution_price >= limit_price:
            return
        refund = (limit_price - execution_price) * amount
        if refund > 1e-12:
            self._account_service.add_to_available(quote_currency, refund)
