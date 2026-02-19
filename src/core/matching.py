"""Market-order matching engine (Phase 2 Step 19)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.core.account_service import AccountService, AccountServiceError
from src.core.database import SQLiteDatabase
from src.core.enums import OrderSide, OrderStatus, OrderType
from src.core.execution_cost import ExecutionCostProfile, LiquidityRole
from src.core.order import Order
from src.core.order_service import CreateOrderRequest, OrderService, OrderServiceError
from src.core.position import Position
from src.core.risk import RiskControl, RiskControlError, RiskLimits
from src.core.trade import Trade
from src.core.trade_service import CreateTradeRequest, TradeService, TradeServiceError
from src.data.realtime_payloads import RealtimeMarketSnapshot

class MatchingEngineError(RuntimeError):
    """Raised when matching or settlement fails."""

class LatestPriceReader(Protocol):
    """Interface required by the matching engine for latest-price reads."""

    def get_latest_price(self, symbol: str) -> RealtimeMarketSnapshot:
        ...

@dataclass(frozen=True)
class MarketOrderRequest:
    """Input payload for market-order matching."""

    symbol: str
    side: OrderSide
    amount: float

@dataclass(frozen=True)
class MarketOrderMatchResult:
    """Finalized market-order result after matching and settlement."""

    order: Order
    trade: Trade
    execution_price: float
    matched_at_ms: int

class MatchingEngine:
    """Match market orders at latest price and settle account/position state."""

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
        self._cost_profile = cost_profile or ExecutionCostProfile()
        self._risk_control = RiskControl(database, account_service, limits=risk_limits)

    def execute_market_order(self, request: MarketOrderRequest) -> MarketOrderMatchResult:
        """Execute one market order using latest price."""
        symbol = request.symbol.strip()
        if not symbol:
            raise MatchingEngineError("symbol must not be empty")
        if request.amount <= 0:
            raise MatchingEngineError("amount must be > 0")

        base_currency, quote_currency = self._split_symbol(symbol)
        reference_price, matched_at_ms = self._resolve_latest_price(symbol)
        execution_price = self._cost_profile.apply_slippage(
            reference_price=reference_price,
            side=request.side,
        )
        trade_fee = self._cost_profile.calculate_fee(
            execution_price=execution_price,
            amount=request.amount,
            liquidity=LiquidityRole.TAKER,
        )
        try:
            self._risk_control.check_pre_order(symbol=symbol, side=request.side, amount=request.amount, reference_price=execution_price)
        except RiskControlError as exc:
            raise MatchingEngineError(f"risk check failed: {exc}") from exc

        with self._db.transaction():
            self._ensure_account_exists(base_currency)
            self._ensure_account_exists(quote_currency)

            if request.side == OrderSide.SELL:
                self._ensure_sell_capacity(symbol=symbol, amount=request.amount, base_currency=base_currency)

            try:
                order = self._order_service.create_order(
                    CreateOrderRequest(
                        symbol=symbol,
                        type=OrderType.MARKET,
                        side=request.side,
                        amount=request.amount,
                        price=execution_price,
                    )
                )
                self._order_service.update_order_status(order.id, OrderStatus.OPEN)
                trade = self._trade_service.record_trade(
                    CreateTradeRequest(
                        order_id=order.id,
                        price=execution_price,
                        amount=request.amount,
                        fee=trade_fee,
                        timestamp=matched_at_ms,
                    )
                )
            except (OrderServiceError, TradeServiceError) as exc:
                raise MatchingEngineError(f"failed to match market order: {exc}") from exc

            self._settle_accounts_and_position(
                symbol=symbol,
                side=request.side,
                amount=request.amount,
                execution_price=execution_price,
                base_currency=base_currency,
                quote_currency=quote_currency,
            )

            final_order = self._order_service.get_order(order.id)

        return MarketOrderMatchResult(
            order=final_order,
            trade=trade,
            execution_price=execution_price,
            matched_at_ms=matched_at_ms,
        )

    def _resolve_latest_price(self, symbol: str) -> tuple[float, int]:
        try:
            snapshot = self._market_reader.get_latest_price(symbol)
        except Exception as exc:
            raise MatchingEngineError(f"failed to fetch latest price for {symbol}: {exc}") from exc

        raw_price = snapshot.data.get("last_price")
        if raw_price is None:
            raise MatchingEngineError(f"missing latest price for symbol {symbol}")
        if not isinstance(raw_price, (int, float)) or isinstance(raw_price, bool):
            raise MatchingEngineError("snapshot.data.last_price must be numeric")
        execution_price = float(raw_price)
        if execution_price <= 0:
            raise MatchingEngineError(f"latest price must be > 0 for symbol {symbol}")
        return execution_price, int(snapshot.fetched_at_ms)

    def _settle_accounts_and_position(
        self,
        *,
        symbol: str,
        side: OrderSide,
        amount: float,
        execution_price: float,
        base_currency: str,
        quote_currency: str,
    ) -> None:
        if side == OrderSide.BUY:
            self._account_service.add_to_available(base_currency, amount)
            self._apply_buy_position_update(
                symbol=symbol,
                fill_amount=amount,
                fill_price=execution_price,
            )
            return

        self._account_service.consume_available(base_currency, amount)
        proceeds = amount * execution_price
        self._account_service.add_to_available(quote_currency, proceeds)
        self._apply_sell_position_update(
            symbol=symbol,
            fill_amount=amount,
            fill_price=execution_price,
        )

    def _apply_buy_position_update(
        self,
        *,
        symbol: str,
        fill_amount: float,
        fill_price: float,
    ) -> None:
        position = self._get_position(symbol)
        if position is None:
            with self._db.transaction() as tx:
                tx.execute(
                    """
                    INSERT INTO positions(
                        symbol, amount, entry_price, current_price,
                        unrealized_pnl, realized_pnl, opened_at
                    )
                    VALUES (?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP);
                    """,
                    (symbol, fill_amount, fill_price, fill_price, 0.0),
                )
            return

        new_amount = position.amount + fill_amount
        new_entry = (
            ((position.amount * position.entry_price) + (fill_amount * fill_price)) / new_amount
            if new_amount > 0
            else fill_price
        )
        unrealized_pnl = (fill_price - new_entry) * new_amount
        with self._db.transaction() as tx:
            tx.execute(
                """
                UPDATE positions
                SET amount = ?, entry_price = ?, current_price = ?, unrealized_pnl = ?, updated_at = CURRENT_TIMESTAMP
                WHERE symbol = ?;
                """,
                (new_amount, new_entry, fill_price, unrealized_pnl, symbol),
            )

    def _apply_sell_position_update(
        self,
        *,
        symbol: str,
        fill_amount: float,
        fill_price: float,
    ) -> None:
        position = self._get_position(symbol)
        if position is None:
            raise MatchingEngineError(f"position not found for symbol {symbol}")
        if position.amount + 1e-12 < fill_amount:
            raise MatchingEngineError(f"insufficient position amount for symbol {symbol}")

        new_amount = max(position.amount - fill_amount, 0.0)
        realized_increment = (fill_price - position.entry_price) * fill_amount
        realized_pnl = position.realized_pnl + realized_increment
        unrealized_pnl = (fill_price - position.entry_price) * new_amount

        with self._db.transaction() as tx:
            tx.execute(
                """
                UPDATE positions
                SET amount = ?, current_price = ?, unrealized_pnl = ?, realized_pnl = ?, updated_at = CURRENT_TIMESTAMP
                WHERE symbol = ?;
                """,
                (new_amount, fill_price, unrealized_pnl, realized_pnl, symbol),
            )

    def _ensure_sell_capacity(self, *, symbol: str, amount: float, base_currency: str) -> None:
        try:
            base_account = self._account_service.get_account(base_currency)
        except AccountServiceError as exc:
            raise MatchingEngineError(f"missing base account for sell order: {exc}") from exc

        if base_account.available + 1e-12 < amount:
            raise MatchingEngineError("insufficient base asset balance for sell market order")

        position = self._get_position(symbol)
        if position is None:
            raise MatchingEngineError(f"position not found for symbol {symbol}")
        if position.amount + 1e-12 < amount:
            raise MatchingEngineError(f"insufficient position amount for symbol {symbol}")

    def _ensure_account_exists(self, currency: str) -> None:
        try:
            self._account_service.get_account(currency)
        except AccountServiceError:
            self._account_service.initialize_accounts({currency: 0.0})

    def _get_position(self, symbol: str) -> Position | None:
        with self._db.transaction() as tx:
            row = tx.execute(
                """
                SELECT symbol, amount, entry_price, current_price, unrealized_pnl,
                       realized_pnl, opened_at, updated_at
                FROM positions
                WHERE symbol = ?;
                """,
                (symbol,),
            ).fetchone()
        if row is None:
            return None
        return Position.validate(dict(row))

    @staticmethod
    def _split_symbol(symbol: str) -> tuple[str, str]:
        if "/" not in symbol:
            raise MatchingEngineError(f"invalid symbol format: {symbol}")
        parts = symbol.split("/")
        if len(parts) != 2:
            raise MatchingEngineError(f"invalid symbol format: {symbol}")
        base_currency = parts[0].strip()
        quote_currency = parts[1].strip()
        if not base_currency or not quote_currency:
            raise MatchingEngineError(f"invalid symbol format: {symbol}")
        return base_currency, quote_currency
