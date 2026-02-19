from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from src.core.account_service import AccountService
from src.core.database import SQLiteDatabase
from src.core.enums import OrderSide, OrderStatus
from src.core.execution_cost import ExecutionCostProfile
from src.core.matching import MatchingEngine, MatchingEngineError, MarketOrderRequest
from src.core.order_service import OrderService
from src.core.trade_service import TradeService
from src.data.realtime_payloads import RealtimeMarketSnapshot


class SequencePriceReader:
    def __init__(self, sequence: Mapping[str, Sequence[float | None]]) -> None:
        self._sequence = {symbol: list(values) for symbol, values in sequence.items()}
        self._fetched_at_ms = 1_700_000_000_000

    def get_latest_price(self, symbol: str) -> RealtimeMarketSnapshot:
        values = self._sequence.get(symbol)
        if values is None or not values:
            raise RuntimeError(f"missing sequence for symbol {symbol}")

        next_price = values.pop(0)
        self._fetched_at_ms += 100
        return RealtimeMarketSnapshot(
            channel="latest_price",
            symbol=symbol,
            ok=next_price is not None,
            fallback=False,
            timed_out=False,
            error=None if next_price is not None else "missing price",
            fetched_at_ms=self._fetched_at_ms,
            data={
                "last_price": next_price,
                "bid": None,
                "ask": None,
                "exchange_timestamp": self._fetched_at_ms,
            },
        )


@pytest.fixture()
def database(tmp_path):
    db = SQLiteDatabase(tmp_path / "matching.db")
    db.initialize_schema()
    return db


@pytest.fixture()
def account_service(database: SQLiteDatabase):
    service = AccountService(database, base_currency="USDT")
    service.initialize_accounts({"USDT": 100_000.0, "BTC": 0.0})
    return service


@pytest.fixture()
def order_service(database: SQLiteDatabase, account_service: AccountService):
    return OrderService(database, account_service)


@pytest.fixture()
def trade_service(database: SQLiteDatabase, order_service: OrderService):
    return TradeService(database, order_service)


def _make_engine(
    database: SQLiteDatabase,
    account_service: AccountService,
    order_service: OrderService,
    trade_service: TradeService,
    price_sequence: Mapping[str, Sequence[float | None]],
    cost_profile: ExecutionCostProfile | None = None,
) -> MatchingEngine:
    reader = SequencePriceReader(price_sequence)
    return MatchingEngine(
        database,
        account_service,
        order_service,
        trade_service,
        reader,
        cost_profile=cost_profile or ExecutionCostProfile(0.0, 0.0, 0.0),
    )


def _position_row(database: SQLiteDatabase, symbol: str) -> Mapping[str, Any]:
    with database.transaction() as tx:
        row = tx.execute(
            """
            SELECT symbol, amount, entry_price, current_price, unrealized_pnl, realized_pnl
            FROM positions
            WHERE symbol = ?;
            """,
            (symbol,),
        ).fetchone()
    assert row is not None
    return row


def _count_rows(database: SQLiteDatabase, table: str) -> int:
    with database.transaction() as tx:
        row = tx.execute(f"SELECT COUNT(*) AS c FROM {table};").fetchone()
    assert row is not None
    return int(row["c"])


def test_execute_market_buy_matches_latest_price_and_updates_state(
    database: SQLiteDatabase,
    account_service: AccountService,
    order_service: OrderService,
    trade_service: TradeService,
) -> None:
    engine = _make_engine(
        database,
        account_service,
        order_service,
        trade_service,
        {"BTC/USDT": [50_000.0]},
    )

    result = engine.execute_market_order(
        MarketOrderRequest(symbol="BTC/USDT", side=OrderSide.BUY, amount=0.2)
    )

    assert result.execution_price == pytest.approx(50_000.0)
    assert result.order.type.value == "market"
    assert result.order.status == OrderStatus.FILLED
    assert result.order.filled == pytest.approx(0.2)
    assert result.trade.price == pytest.approx(50_000.0)
    assert result.trade.amount == pytest.approx(0.2)
    assert result.trade.fee == pytest.approx(0.0)

    usdt = account_service.get_account("USDT")
    btc = account_service.get_account("BTC")
    assert usdt.balance == pytest.approx(90_000.0)
    assert usdt.available == pytest.approx(90_000.0)
    assert usdt.frozen == pytest.approx(0.0)
    assert btc.balance == pytest.approx(0.2)
    assert btc.available == pytest.approx(0.2)

    pos = _position_row(database, "BTC/USDT")
    assert pos["amount"] == pytest.approx(0.2)
    assert pos["entry_price"] == pytest.approx(50_000.0)
    assert pos["current_price"] == pytest.approx(50_000.0)
    assert pos["unrealized_pnl"] == pytest.approx(0.0)
    assert pos["realized_pnl"] == pytest.approx(0.0)


def test_market_order_results_reproducible_under_fixed_price_sequence(
    database: SQLiteDatabase,
    account_service: AccountService,
    order_service: OrderService,
    trade_service: TradeService,
) -> None:
    engine = _make_engine(
        database,
        account_service,
        order_service,
        trade_service,
        {"BTC/USDT": [50_000.0, 52_000.0, 51_000.0]},
    )

    engine.execute_market_order(
        MarketOrderRequest(symbol="BTC/USDT", side=OrderSide.BUY, amount=0.5)
    )
    engine.execute_market_order(
        MarketOrderRequest(symbol="BTC/USDT", side=OrderSide.BUY, amount=0.25)
    )
    sell_result = engine.execute_market_order(
        MarketOrderRequest(symbol="BTC/USDT", side=OrderSide.SELL, amount=0.3)
    )
    assert sell_result.order.status == OrderStatus.FILLED

    # Hand calculation:
    # cash = 100000 - (0.5*50000) - (0.25*52000) + (0.3*51000) = 77300
    # remaining position = 0.45
    # avg entry after buys = 50666.666666...
    # realized pnl after sell = (51000 - 50666.6666...) * 0.3 = 100
    usdt = account_service.get_account("USDT")
    btc = account_service.get_account("BTC")
    assert usdt.balance == pytest.approx(77_300.0)
    assert usdt.available == pytest.approx(77_300.0)
    assert btc.balance == pytest.approx(0.45)
    assert btc.available == pytest.approx(0.45)

    pos = _position_row(database, "BTC/USDT")
    assert pos["amount"] == pytest.approx(0.45)
    assert pos["entry_price"] == pytest.approx(50_666.6666666667)
    assert pos["current_price"] == pytest.approx(51_000.0)
    assert pos["realized_pnl"] == pytest.approx(100.0)
    assert pos["unrealized_pnl"] == pytest.approx(150.0)
    assert _count_rows(database, "orders") == 3
    assert _count_rows(database, "trades") == 3


def test_execute_market_order_fails_when_latest_price_missing(
    database: SQLiteDatabase,
    account_service: AccountService,
    order_service: OrderService,
    trade_service: TradeService,
) -> None:
    engine = _make_engine(
        database,
        account_service,
        order_service,
        trade_service,
        {"BTC/USDT": [None]},
    )

    with pytest.raises(MatchingEngineError, match="missing latest price"):
        engine.execute_market_order(
            MarketOrderRequest(symbol="BTC/USDT", side=OrderSide.BUY, amount=0.1)
        )

    assert _count_rows(database, "orders") == 0
    assert _count_rows(database, "trades") == 0


def test_execute_market_sell_requires_inventory(
    database: SQLiteDatabase,
    account_service: AccountService,
    order_service: OrderService,
    trade_service: TradeService,
) -> None:
    engine = _make_engine(
        database,
        account_service,
        order_service,
        trade_service,
        {"BTC/USDT": [50_000.0]},
    )

    with pytest.raises(MatchingEngineError, match="insufficient base asset balance"):
        engine.execute_market_order(
            MarketOrderRequest(symbol="BTC/USDT", side=OrderSide.SELL, amount=0.1)
        )

    assert _count_rows(database, "orders") == 0
    assert _count_rows(database, "trades") == 0
