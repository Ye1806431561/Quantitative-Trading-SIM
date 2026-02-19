"""Account initialization and balance management."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from src.core.account import Account
from src.core.database import SQLiteDatabase
from src.core.position import Position


class AccountServiceError(RuntimeError):
    """Raised when account lifecycle operations are invalid."""


@dataclass(frozen=True)
class AccountSnapshot:
    """Aggregated account state including open positions."""

    accounts: Sequence[Account]
    positions: Sequence[Position]
    total_assets: float


class AccountService:
    """Manage accounts table, frozen funds, and total asset valuation."""

    def __init__(self, database: SQLiteDatabase, base_currency: str) -> None:
        if not base_currency:
            raise AccountServiceError("base_currency must not be empty")
        self._db = database
        self._base_currency = base_currency

    @property
    def base_currency(self) -> str:
        return self._base_currency

    @classmethod
    def from_config(cls, database: SQLiteDatabase, config: Mapping[str, object]) -> "AccountService":
        account_cfg = config.get("account")
        if not isinstance(account_cfg, Mapping):
            raise AccountServiceError("missing account configuration")

        base_currency = account_cfg.get("base_currency")
        initial_capital = account_cfg.get("initial_capital")

        if not isinstance(base_currency, str) or not base_currency.strip():
            raise AccountServiceError("account.base_currency must be a non-empty string")
        if not isinstance(initial_capital, (int, float)) or isinstance(initial_capital, bool):
            raise AccountServiceError("account.initial_capital must be a number")
        if float(initial_capital) < 0:
            raise AccountServiceError("account.initial_capital must be non-negative")

        service = cls(database, base_currency.strip())
        service.initialize_accounts({base_currency.strip(): float(initial_capital)})
        return service

    # ------------------------------------------------------------------ #
    # Initialization & retrieval
    # ------------------------------------------------------------------ #
    def initialize_accounts(self, initial_balances: Mapping[str, float]) -> None:
        """Idempotently create account rows for the provided currencies.

        Existing rows are left untouched to preserve prior runtime state.
        """
        with self._db.transaction() as tx:
            for currency, balance in initial_balances.items():
                if balance < 0:
                    raise AccountServiceError("initial balance must be non-negative")

                row = tx.execute(
                    "SELECT id FROM accounts WHERE currency = ?;",
                    (currency,),
                ).fetchone()

                if row is None:
                    tx.execute(
                        """
                        INSERT INTO accounts(currency, balance, available, frozen)
                        VALUES (?, ?, ?, 0);
                        """,
                        (currency, balance, balance),
                    )

    def get_account(self, currency: str) -> Account:
        with self._db.transaction() as tx:
            row = tx.execute(
                "SELECT currency, balance, available, frozen FROM accounts WHERE currency = ?;",
                (currency,),
            ).fetchone()
        if row is None:
            raise AccountServiceError(f"account not found: {currency}")
        return Account.validate(dict(row))

    def list_accounts(self) -> list[Account]:
        with self._db.transaction() as tx:
            rows = tx.execute(
                "SELECT currency, balance, available, frozen FROM accounts ORDER BY currency;"
            ).fetchall()
        return [Account.validate(dict(row)) for row in rows]

    # ------------------------------------------------------------------ #
    # Balance mutation helpers
    # ------------------------------------------------------------------ #
    def deposit(self, currency: str, amount: float) -> Account:
        if amount < 0:
            raise AccountServiceError("deposit amount must be non-negative")
        with self._db.transaction() as tx:
            account = self._get_account_row_for_update(tx, currency)
            new_balance = account["balance"] + amount
            new_available = account["available"] + amount
            self._update_account(tx, currency, new_balance, new_available, account["frozen"])
        return self.get_account(currency)

    def freeze_funds(self, currency: str, amount: float) -> Account:
        if amount <= 0:
            raise AccountServiceError("freeze amount must be > 0")
        with self._db.transaction() as tx:
            account = self._get_account_row_for_update(tx, currency)
            if account["available"] < amount:
                raise AccountServiceError("insufficient available balance to freeze")
            new_available = account["available"] - amount
            new_frozen = account["frozen"] + amount
            self._update_account(tx, currency, account["balance"], new_available, new_frozen)
        return self.get_account(currency)

    def release_funds(self, currency: str, amount: float) -> Account:
        if amount <= 0:
            raise AccountServiceError("release amount must be > 0")
        with self._db.transaction() as tx:
            account = self._get_account_row_for_update(tx, currency)
            if account["frozen"] < amount:
                raise AccountServiceError("insufficient frozen balance to release")
            new_available = account["available"] + amount
            new_frozen = account["frozen"] - amount
            self._update_account(tx, currency, account["balance"], new_available, new_frozen)
        return self.get_account(currency)

    def consume_available(self, currency: str, amount: float) -> Account:
        """Reduce available (e.g., spend cash)."""
        if amount <= 0:
            raise AccountServiceError("amount must be > 0")
        with self._db.transaction() as tx:
            account = self._get_account_row_for_update(tx, currency)
            if account["available"] < amount:
                raise AccountServiceError("insufficient available balance")
            new_available = account["available"] - amount
            new_balance = account["balance"] - amount
            self._update_account(tx, currency, new_balance, new_available, account["frozen"])
        return self.get_account(currency)

    def add_to_available(self, currency: str, amount: float) -> Account:
        """Increase available (e.g., proceeds from trade)."""
        if amount < 0:
            raise AccountServiceError("amount must be non-negative")
        with self._db.transaction() as tx:
            account = self._get_account_row_for_update(tx, currency)
            new_available = account["available"] + amount
            new_balance = account["balance"] + amount
            self._update_account(tx, currency, new_balance, new_available, account["frozen"])
        return self.get_account(currency)

    # ------------------------------------------------------------------ #
    # Position recovery & valuation
    # ------------------------------------------------------------------ #
    def load_positions(self) -> list[Position]:
        with self._db.transaction() as tx:
            rows = tx.execute(
                """
                SELECT symbol, amount, entry_price, current_price, unrealized_pnl,
                       realized_pnl, opened_at, updated_at
                FROM positions
                ORDER BY symbol;
                """
            ).fetchall()
        return [Position.validate(dict(row)) for row in rows]

    def compute_total_assets(self, price_lookup: Mapping[str, float]) -> float:
        """Return total asset value in base currency.

        Cash = available + frozen of base currency account.
        Positions = amount * price (price from lookup, fallback to current_price).
        """
        accounts = self.list_accounts()
        base_cash = 0.0
        for account in accounts:
            if account.currency == self._base_currency:
                base_cash += account.available + account.frozen

        positions = self.load_positions()
        positions_value = 0.0
        for pos in positions:
            price = price_lookup.get(pos.symbol, pos.current_price)
            if price is None:
                raise AccountServiceError(f"missing price for symbol {pos.symbol}")
            positions_value += pos.amount * float(price)

        return base_cash + positions_value

    def snapshot(self, price_lookup: Mapping[str, float]) -> AccountSnapshot:
        accounts = self.list_accounts()
        positions = self.load_positions()
        total_assets = self.compute_total_assets(price_lookup)
        return AccountSnapshot(accounts=accounts, positions=positions, total_assets=total_assets)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _update_account(
        tx,
        currency: str,
        balance: float,
        available: float,
        frozen: float,
    ) -> None:
        tx.execute(
            """
            UPDATE accounts
            SET balance = ?, available = ?, frozen = ?, updated_at = CURRENT_TIMESTAMP
            WHERE currency = ?;
            """,
            (balance, available, frozen, currency),
        )

    @staticmethod
    def _get_account_row_for_update(tx, currency: str):
        row = tx.execute(
            "SELECT currency, balance, available, frozen FROM accounts WHERE currency = ?;",
            (currency,),
        ).fetchone()
        if row is None:
            raise AccountServiceError(f"account not found: {currency}")
        return row
