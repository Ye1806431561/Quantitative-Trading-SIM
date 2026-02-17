from __future__ import annotations

import sqlite3

import pytest

from src.core.database import DatabaseLifecycleError, SQLiteDatabase


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
