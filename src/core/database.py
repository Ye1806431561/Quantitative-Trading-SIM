"""SQLite connection lifecycle management for runtime persistence."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        currency TEXT NOT NULL,
        balance REAL NOT NULL,
        available REAL NOT NULL,
        frozen REAL NOT NULL DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        symbol TEXT NOT NULL,
        type TEXT NOT NULL,
        side TEXT NOT NULL,
        price REAL,
        amount REAL NOT NULL,
        filled REAL DEFAULT 0,
        status TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT NOT NULL,
        symbol TEXT NOT NULL,
        side TEXT NOT NULL,
        price REAL NOT NULL,
        amount REAL NOT NULL,
        fee REAL NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (order_id) REFERENCES orders(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS strategy_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_name TEXT NOT NULL,
        symbol TEXT NOT NULL,
        start_time TIMESTAMP,
        end_time TIMESTAMP,
        initial_capital REAL,
        final_capital REAL,
        total_return REAL,
        max_drawdown REAL,
        sharpe_ratio REAL,
        status TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL UNIQUE,
        amount REAL NOT NULL,
        entry_price REAL NOT NULL,
        current_price REAL,
        unrealized_pnl REAL,
        realized_pnl REAL DEFAULT 0,
        opened_at TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CHECK(amount >= 0)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS candles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        timeframe TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        open REAL NOT NULL,
        high REAL NOT NULL,
        low REAL NOT NULL,
        close REAL NOT NULL,
        volume REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol, timeframe, timestamp)
    );
    """,
)

INDEX_STATEMENTS: tuple[str, ...] = (
    "CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);",
    "CREATE INDEX IF NOT EXISTS idx_candles_symbol_time ON candles(symbol, timeframe, timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_candles_timestamp ON candles(timestamp);",
)


class DatabaseLifecycleError(RuntimeError):
    """Raised when database lifecycle operations are invalid."""


class SQLiteDatabase:
    """Manage SQLite connection open/close and transaction boundaries."""

    def __init__(self, database_path: str | Path, timeout: float = 30.0) -> None:
        path = Path(database_path).expanduser()
        if not str(path).strip():
            raise DatabaseLifecycleError("database_path must not be empty")
        self._database_path = path
        self._timeout = timeout
        self._connection: sqlite3.Connection | None = None
        self._transaction_depth = 0

    @classmethod
    def from_config(
        cls,
        config: Mapping[str, Any],
        timeout: float = 30.0,
    ) -> "SQLiteDatabase":
        """Build database manager from validated runtime config."""
        system = config.get("system")
        if not isinstance(system, Mapping):
            raise DatabaseLifecycleError("Missing config section: system")

        database_path = system.get("database_path")
        if not isinstance(database_path, str) or not database_path.strip():
            raise DatabaseLifecycleError("Missing config value: system.database_path")

        return cls(database_path=database_path.strip(), timeout=timeout)

    @property
    def database_path(self) -> Path:
        """Return configured database path."""
        return self._database_path

    @property
    def is_open(self) -> bool:
        """Return whether the underlying SQLite connection is open."""
        return self._connection is not None

    @property
    def connection(self) -> sqlite3.Connection:
        """Return open connection, raising if lifecycle is not opened."""
        if self._connection is None:
            raise DatabaseLifecycleError("Database connection is not open")
        return self._connection

    def open(self) -> sqlite3.Connection:
        """Open SQLite connection if needed and return it."""
        if self._connection is not None:
            return self._connection

        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            self._database_path,
            timeout=self._timeout,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")

        self._connection = connection
        self._transaction_depth = 0
        return connection

    def close(self) -> None:
        """Close SQLite connection and rollback uncommitted work."""
        if self._connection is None:
            return
        if self._connection.in_transaction:
            self._connection.rollback()
        self._connection.close()
        self._connection = None
        self._transaction_depth = 0

    def initialize_schema(self) -> None:
        """Create required runtime tables, constraints, and indexes."""
        with self.transaction() as tx:
            for statement in SCHEMA_STATEMENTS:
                tx.execute(statement)
            for statement in INDEX_STATEMENTS:
                tx.execute(statement)

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Open a transaction scope with automatic commit/rollback."""
        connection = self.open()
        is_root_transaction = self._transaction_depth == 0
        savepoint_name = f"sp_{self._transaction_depth}"

        try:
            if is_root_transaction:
                connection.execute("BEGIN;")
            else:
                connection.execute(f"SAVEPOINT {savepoint_name};")
            self._transaction_depth += 1
            yield connection
        except Exception:
            self._transaction_depth -= 1
            if is_root_transaction:
                connection.rollback()
            else:
                connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name};")
                connection.execute(f"RELEASE SAVEPOINT {savepoint_name};")
            raise
        else:
            self._transaction_depth -= 1
            if is_root_transaction:
                connection.commit()
            else:
                connection.execute(f"RELEASE SAVEPOINT {savepoint_name};")

    def __enter__(self) -> "SQLiteDatabase":
        self.open()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
