from __future__ import annotations

import sqlite3

import pytest

from src.core.database import DatabaseLifecycleError, SQLiteDatabase

REQUIRED_TABLES = {
    "accounts",
    "orders",
    "trades",
    "strategy_runs",
    "positions",
    "candles",
}

EXPECTED_COLUMNS = {
    "accounts": [
        "id",
        "currency",
        "balance",
        "available",
        "frozen",
        "updated_at",
    ],
    "orders": [
        "id",
        "symbol",
        "type",
        "side",
        "price",
        "amount",
        "filled",
        "status",
        "created_at",
        "updated_at",
    ],
    "trades": [
        "id",
        "order_id",
        "symbol",
        "side",
        "price",
        "amount",
        "fee",
        "timestamp",
    ],
    "strategy_runs": [
        "id",
        "strategy_name",
        "symbol",
        "start_time",
        "end_time",
        "initial_capital",
        "final_capital",
        "total_return",
        "max_drawdown",
        "sharpe_ratio",
        "status",
    ],
    "positions": [
        "id",
        "symbol",
        "amount",
        "entry_price",
        "current_price",
        "unrealized_pnl",
        "realized_pnl",
        "opened_at",
        "updated_at",
    ],
    "candles": [
        "id",
        "symbol",
        "timeframe",
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "created_at",
    ],
}


def test_database_path_comes_from_config(tmp_path) -> None:
    db_path = tmp_path / "runtime" / "paper.db"
    config = {"system": {"database_path": str(db_path)}}

    database = SQLiteDatabase.from_config(config)

    assert database.database_path == db_path


def test_open_commit_and_close_lifecycle(tmp_path) -> None:
    db_path = tmp_path / "runtime" / "lifecycle.db"
    database = SQLiteDatabase(db_path)

    connection = database.open()
    assert database.is_open
    assert isinstance(connection, sqlite3.Connection)

    with database.transaction() as tx:
        tx.execute("CREATE TABLE lifecycle (id INTEGER PRIMARY KEY, value TEXT NOT NULL);")
        tx.execute("INSERT INTO lifecycle(value) VALUES (?);", ("committed",))

    database.close()
    assert not database.is_open

    with sqlite3.connect(db_path) as verify_conn:
        row_count = verify_conn.execute("SELECT COUNT(*) FROM lifecycle;").fetchone()[0]
    assert row_count == 1


def test_transaction_rolls_back_on_error(tmp_path) -> None:
    database = SQLiteDatabase(tmp_path / "rollback.db")

    with database.transaction() as tx:
        tx.execute("CREATE TABLE rollback_case (id INTEGER PRIMARY KEY, value TEXT NOT NULL);")

    with pytest.raises(RuntimeError, match="force rollback"):
        with database.transaction() as tx:
            tx.execute("INSERT INTO rollback_case(value) VALUES (?);", ("discard",))
            raise RuntimeError("force rollback")

    with database.transaction() as tx:
        row_count = tx.execute("SELECT COUNT(*) FROM rollback_case;").fetchone()[0]
    assert row_count == 0

    database.close()


def test_close_is_idempotent_and_connection_guarded(tmp_path) -> None:
    database = SQLiteDatabase(tmp_path / "close.db")
    database.open()
    database.close()
    database.close()

    with pytest.raises(DatabaseLifecycleError, match="not open"):
        _ = database.connection


def test_context_manager_closes_connection(tmp_path) -> None:
    db_path = tmp_path / "context.db"

    with SQLiteDatabase(db_path) as database:
        assert database.is_open

    assert not database.is_open
    db_path.unlink()


def test_initialize_schema_creates_required_tables_and_columns(tmp_path) -> None:
    database = SQLiteDatabase(tmp_path / "schema.db")
    database.initialize_schema()

    with database.transaction() as tx:
        table_names = {
            row["name"]
            for row in tx.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            ).fetchall()
        }
        assert REQUIRED_TABLES.issubset(table_names)

        for table_name, expected_columns in EXPECTED_COLUMNS.items():
            rows = tx.execute(f"PRAGMA table_info('{table_name}');").fetchall()
            actual_columns = [row["name"] for row in rows]
            assert actual_columns == expected_columns


def test_initialize_schema_creates_required_indexes(tmp_path) -> None:
    database = SQLiteDatabase(tmp_path / "indexes.db")
    database.initialize_schema()

    with database.transaction() as tx:
        positions_indexes = {
            row["name"] for row in tx.execute("PRAGMA index_list('positions');").fetchall()
        }
        assert "idx_positions_symbol" in positions_indexes

        candles_indexes = {
            row["name"] for row in tx.execute("PRAGMA index_list('candles');").fetchall()
        }
        assert "idx_candles_symbol_time" in candles_indexes
        assert "idx_candles_timestamp" in candles_indexes


def test_trades_table_has_foreign_key_to_orders(tmp_path) -> None:
    database = SQLiteDatabase(tmp_path / "fk.db")
    database.initialize_schema()

    with database.transaction() as tx:
        foreign_keys = tx.execute("PRAGMA foreign_key_list('trades');").fetchall()

    assert len(foreign_keys) == 1
    assert foreign_keys[0]["from"] == "order_id"
    assert foreign_keys[0]["table"] == "orders"
    assert foreign_keys[0]["to"] == "id"


def test_positions_constraints_enforce_unique_symbol_and_non_negative_amount(tmp_path) -> None:
    database = SQLiteDatabase(tmp_path / "positions_constraints.db")
    database.initialize_schema()

    with database.transaction() as tx:
        tx.execute(
            "INSERT INTO positions(symbol, amount, entry_price) VALUES (?, ?, ?);",
            ("BTC/USDT", 1.0, 50000.0),
        )

    with pytest.raises(sqlite3.IntegrityError):
        with database.transaction() as tx:
            tx.execute(
                "INSERT INTO positions(symbol, amount, entry_price) VALUES (?, ?, ?);",
                ("BTC/USDT", 2.0, 51000.0),
            )

    with pytest.raises(sqlite3.IntegrityError):
        with database.transaction() as tx:
            tx.execute(
                "INSERT INTO positions(symbol, amount, entry_price) VALUES (?, ?, ?);",
                ("ETH/USDT", -1.0, 3000.0),
            )


def test_candles_unique_constraint_enforces_no_duplicates(tmp_path) -> None:
    database = SQLiteDatabase(tmp_path / "candles_constraints.db")
    database.initialize_schema()

    insert_sql = (
        "INSERT INTO candles(symbol, timeframe, timestamp, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?);"
    )

    candle = ("BTC/USDT", "1h", 1700000000000, 50000.0, 51000.0, 49500.0, 50500.0, 123.4)
    with database.transaction() as tx:
        tx.execute(insert_sql, candle)

    with pytest.raises(sqlite3.IntegrityError):
        with database.transaction() as tx:
            tx.execute(insert_sql, candle)


def test_trades_foreign_key_constraint_blocks_missing_order(tmp_path) -> None:
    database = SQLiteDatabase(tmp_path / "trades_constraints.db")
    database.initialize_schema()

    with pytest.raises(sqlite3.IntegrityError):
        with database.transaction() as tx:
            tx.execute(
                "INSERT INTO trades(order_id, symbol, side, price, amount, fee) "
                "VALUES (?, ?, ?, ?, ?, ?);",
                ("missing-order", "BTC/USDT", "buy", 50000.0, 0.1, 5.0),
            )
