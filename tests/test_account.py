from __future__ import annotations

import pytest

from src.core.account_service import AccountService, AccountServiceError
from src.core.database import SQLiteDatabase


@pytest.fixture()
def database(tmp_path):
    db = SQLiteDatabase(tmp_path / "account.db")
    db.initialize_schema()
    return db


def test_initialize_accounts_is_idempotent(database):
    service = AccountService(database, base_currency="USDT")

    service.initialize_accounts({"USDT": 10_000})
    service.initialize_accounts({"USDT": 10_000})  # second call should not duplicate

    with database.transaction() as tx:
        rows = tx.execute("SELECT currency, balance, available, frozen FROM accounts;").fetchall()

    assert len(rows) == 1
    row = rows[0]
    assert row["currency"] == "USDT"
    assert row["balance"] == 10_000
    assert row["available"] == 10_000
    assert row["frozen"] == 0


def test_freeze_and_release_funds(database):
    service = AccountService(database, base_currency="USDT")
    service.initialize_accounts({"USDT": 5_000})

    after_freeze = service.freeze_funds("USDT", 1_500)
    assert after_freeze.available == 3_500
    assert after_freeze.frozen == 1_500

    after_release = service.release_funds("USDT", 500)
    assert after_release.available == 4_000
    assert after_release.frozen == 1_000

    with pytest.raises(AccountServiceError):
        service.release_funds("USDT", 2_000)  # cannot release more than frozen


def test_compute_total_assets_uses_positions(database):
    service = AccountService(database, base_currency="USDT")
    service.initialize_accounts({"USDT": 2_000})

    with database.transaction() as tx:
        tx.execute(
            """
            INSERT INTO positions(symbol, amount, entry_price, current_price, unrealized_pnl, realized_pnl)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            ("BTC/USDT", 1.0, 20_000, 25_000, 5_000, 0),
        )
        tx.execute(
            """
            INSERT INTO positions(symbol, amount, entry_price, current_price, unrealized_pnl, realized_pnl)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            ("ETH/USDT", 2.0, 1_000, 900, -200, 0),
        )

    prices = {"BTC/USDT": 25_000, "ETH/USDT": 900}

    total_assets = service.compute_total_assets(prices)

    # cash (2,000) + BTC (25,000) + ETH (1,800) = 28,800
    assert total_assets == pytest.approx(28_800)


def test_compute_total_assets_requires_price_when_missing_current_price(database):
    service = AccountService(database, base_currency="USDT")
    service.initialize_accounts({"USDT": 1_000})

    with database.transaction() as tx:
        tx.execute(
            """
            INSERT INTO positions(symbol, amount, entry_price, current_price, unrealized_pnl, realized_pnl)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            ("SOL/USDT", 3.0, 20.0, None, None, 0),
        )

    with pytest.raises(AccountServiceError):
        service.compute_total_assets({"BTC/USDT": 25_000})


def test_from_config_initializes_account(database):
    config = {
        "account": {
            "base_currency": "USDT",
            "initial_capital": 7500,
        }
    }

    service = AccountService.from_config(database, config)

    account = service.get_account("USDT")
    assert account.available == 7500
    assert account.frozen == 0
