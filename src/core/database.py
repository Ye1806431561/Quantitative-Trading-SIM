"""SQLite connection lifecycle management for runtime persistence."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any


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
