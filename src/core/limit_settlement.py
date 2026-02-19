"""Settlement and position-sync helpers for limit-order matching."""

from __future__ import annotations

from src.core.account_service import AccountService, AccountServiceError
from src.core.enums import OrderSide
from src.core.position import Position


class LimitOrderSettlementError(RuntimeError):
    """Raised when account or position settlement fails."""


class LimitOrderSettlement:
    """Apply account and position updates for matched limit orders."""

    def __init__(self, account_service: AccountService) -> None:
        self._account_service = account_service

    def ensure_accounts(self, symbol: str) -> tuple[str, str]:
        """Ensure base/quote accounts exist and return their currencies."""
        base_currency, quote_currency = self.split_symbol(symbol)
        self._ensure_account_exists(base_currency)
        self._ensure_account_exists(quote_currency)
        return base_currency, quote_currency

    def has_sell_capacity(self, *, tx, symbol: str, base_currency: str, amount: float) -> bool:
        """Return whether account + position can cover a sell fill."""
        try:
            base_account = self._account_service.get_account(base_currency)
        except AccountServiceError:
            return False
        if base_account.available + 1e-12 < amount:
            return False

        position = self._get_position(tx, symbol)
        if position is None:
            return False
        return position.amount + 1e-12 >= amount

    def settle(
        self,
        *,
        tx,
        symbol: str,
        side: OrderSide,
        amount: float,
        execution_price: float,
        base_currency: str,
        quote_currency: str,
    ) -> None:
        """Apply account and position updates for one trade fill."""
        if side == OrderSide.BUY:
            self._account_service.add_to_available(base_currency, amount)
            self._apply_buy_position_update(tx=tx, symbol=symbol, amount=amount, price=execution_price)
            return

        self._account_service.consume_available(base_currency, amount)
        self._account_service.add_to_available(quote_currency, amount * execution_price)
        self._apply_sell_position_update(tx=tx, symbol=symbol, amount=amount, price=execution_price)

    @staticmethod
    def split_symbol(symbol: str) -> tuple[str, str]:
        """Split `BASE/QUOTE` symbol and validate format."""
        if "/" not in symbol:
            raise LimitOrderSettlementError(f"invalid symbol format: {symbol}")
        parts = symbol.split("/")
        if len(parts) != 2:
            raise LimitOrderSettlementError(f"invalid symbol format: {symbol}")
        base_currency = parts[0].strip()
        quote_currency = parts[1].strip()
        if not base_currency or not quote_currency:
            raise LimitOrderSettlementError(f"invalid symbol format: {symbol}")
        return base_currency, quote_currency

    def _ensure_account_exists(self, currency: str) -> None:
        try:
            self._account_service.get_account(currency)
        except AccountServiceError:
            self._account_service.initialize_accounts({currency: 0.0})

    def _apply_buy_position_update(self, *, tx, symbol: str, amount: float, price: float) -> None:
        position = self._get_position(tx, symbol)
        if position is None:
            tx.execute(
                """
                INSERT INTO positions(
                    symbol, amount, entry_price, current_price,
                    unrealized_pnl, realized_pnl, opened_at
                )
                VALUES (?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP);
                """,
                (symbol, amount, price, price, 0.0),
            )
            return

        new_amount = position.amount + amount
        new_entry = ((position.amount * position.entry_price) + (amount * price)) / new_amount
        unrealized_pnl = (price - new_entry) * new_amount
        tx.execute(
            """
            UPDATE positions
            SET amount = ?, entry_price = ?, current_price = ?, unrealized_pnl = ?, updated_at = CURRENT_TIMESTAMP
            WHERE symbol = ?;
            """,
            (new_amount, new_entry, price, unrealized_pnl, symbol),
        )

    def _apply_sell_position_update(self, *, tx, symbol: str, amount: float, price: float) -> None:
        position = self._get_position(tx, symbol)
        if position is None:
            raise LimitOrderSettlementError(f"position not found for symbol {symbol}")
        if position.amount + 1e-12 < amount:
            raise LimitOrderSettlementError(f"insufficient position amount for symbol {symbol}")

        new_amount = max(position.amount - amount, 0.0)
        realized_increment = (price - position.entry_price) * amount
        realized_pnl = position.realized_pnl + realized_increment
        unrealized_pnl = (price - position.entry_price) * new_amount

        tx.execute(
            """
            UPDATE positions
            SET amount = ?, current_price = ?, unrealized_pnl = ?, realized_pnl = ?, updated_at = CURRENT_TIMESTAMP
            WHERE symbol = ?;
            """,
            (new_amount, price, unrealized_pnl, realized_pnl, symbol),
        )

    @staticmethod
    def _get_position(tx, symbol: str) -> Position | None:
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
