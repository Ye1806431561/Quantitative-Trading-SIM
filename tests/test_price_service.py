from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from src.core.account_service import AccountService
from src.core.database import SQLiteDatabase
from src.data.realtime_payloads import RealtimeMarketSnapshot
from src.live.price_service import PriceService, PriceServiceError


class FakeRealtimePriceReader:
    def __init__(self, prices: Mapping[str, float | None]) -> None:
        self._prices = dict(prices)
        self._fetched_at_ms = 1_700_000_000_000

    def get_latest_price(self, symbol: str) -> RealtimeMarketSnapshot:
        price = self._prices.get(symbol)
        self._fetched_at_ms += 100
        return RealtimeMarketSnapshot(
            channel="latest_price",
            symbol=symbol,
            ok=price is not None,
            fallback=False,
            timed_out=False,
            error=None if price is not None else "no data",
            fetched_at_ms=self._fetched_at_ms,
            data={
                "last_price": price,
                "bid": None,
                "ask": None,
                "exchange_timestamp": None,
            },
        )


@pytest.fixture()
def database(tmp_path):
    db = SQLiteDatabase(tmp_path / "pricing.db")
    db.initialize_schema()
    return db


def _insert_position(
    database: SQLiteDatabase,
    *,
    symbol: str,
    amount: float,
    entry_price: float,
    current_price: float | None,
    unrealized_pnl: float | None = None,
) -> None:
    with database.transaction() as tx:
        tx.execute(
            """
            INSERT INTO positions(symbol, amount, entry_price, current_price, unrealized_pnl, realized_pnl)
            VALUES (?, ?, ?, ?, ?, 0);
            """,
            (symbol, amount, entry_price, current_price, unrealized_pnl),
        )


def _position_row(database: SQLiteDatabase, symbol: str) -> Mapping[str, Any]:
    with database.transaction() as tx:
        row = tx.execute(
            "SELECT symbol, current_price, unrealized_pnl FROM positions WHERE symbol = ?;",
            (symbol,),
        ).fetchone()
    assert row is not None
    return row


def test_valuate_portfolio_matches_manual_calculation(database) -> None:
    account_service = AccountService(database, base_currency="USDT")
    account_service.initialize_accounts({"USDT": 2_000})
    _insert_position(
        database,
        symbol="BTC/USDT",
        amount=1.0,
        entry_price=20_000.0,
        current_price=24_000.0,
    )
    _insert_position(
        database,
        symbol="ETH/USDT",
        amount=2.0,
        entry_price=1_000.0,
        current_price=950.0,
    )
    reader = FakeRealtimePriceReader({"BTC/USDT": 25_000.0, "ETH/USDT": 900.0})
    service = PriceService(database, account_service, reader)

    valuation = service.valuate_portfolio()

    # cash(2,000) + BTC(1*25,000) + ETH(2*900) = 28,800
    assert valuation.base_cash == pytest.approx(2_000.0)
    assert valuation.positions_value == pytest.approx(26_800.0)
    assert valuation.total_assets == pytest.approx(28_800.0)
    assert len(valuation.positions) == 2

    btc = next(item for item in valuation.positions if item.symbol == "BTC/USDT")
    eth = next(item for item in valuation.positions if item.symbol == "ETH/USDT")
    assert btc.unrealized_pnl == pytest.approx(5_000.0)
    assert eth.unrealized_pnl == pytest.approx(-200.0)

    btc_row = _position_row(database, "BTC/USDT")
    eth_row = _position_row(database, "ETH/USDT")
    assert btc_row["current_price"] == pytest.approx(25_000.0)
    assert btc_row["unrealized_pnl"] == pytest.approx(5_000.0)
    assert eth_row["current_price"] == pytest.approx(900.0)
    assert eth_row["unrealized_pnl"] == pytest.approx(-200.0)


def test_valuate_portfolio_uses_stored_price_when_latest_missing(database) -> None:
    account_service = AccountService(database, base_currency="USDT")
    account_service.initialize_accounts({"USDT": 1_000})
    _insert_position(
        database,
        symbol="SOL/USDT",
        amount=3.0,
        entry_price=20.0,
        current_price=21.0,
    )
    reader = FakeRealtimePriceReader({"SOL/USDT": None})
    service = PriceService(database, account_service, reader)

    valuation = service.valuate_portfolio()

    assert valuation.total_assets == pytest.approx(1_063.0)
    sol = valuation.positions[0]
    assert sol.symbol == "SOL/USDT"
    assert sol.mark_price == pytest.approx(21.0)
    assert sol.unrealized_pnl == pytest.approx(3.0)


def test_valuate_portfolio_raises_when_no_latest_or_stored_price(database) -> None:
    account_service = AccountService(database, base_currency="USDT")
    account_service.initialize_accounts({"USDT": 1_000})
    _insert_position(
        database,
        symbol="XRP/USDT",
        amount=100.0,
        entry_price=0.5,
        current_price=None,
    )
    reader = FakeRealtimePriceReader({"XRP/USDT": None})
    service = PriceService(database, account_service, reader)

    with pytest.raises(PriceServiceError, match="missing mark price"):
        service.valuate_portfolio()
