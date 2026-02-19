from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from src.core.account_service import AccountService
from src.core.database import SQLiteDatabase
from src.core.enums import OrderSide, OrderStatus
from src.core.execution_cost import ExecutionCostProfile
from src.core.limit_matching import (
    LimitOrderMatchingEngine,
    LimitOrderMatchingError,
    LimitOrderRequest,
)
from src.core.order_service import OrderService
from src.core.trade_service import TradeService
from src.data.realtime_payloads import RealtimeMarketSnapshot

class SequencePriceReader:
    def __init__(self, sequence: Mapping[str, Sequence[float | None]]) -> None:
        self._sequence = {symbol: list(values) for symbol, values in sequence.items()}
        self._fetched_at_ms = 1_700_100_000_000

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
    db = SQLiteDatabase(tmp_path / "limit_matching.db")
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
    prices: Mapping[str, Sequence[float | None]],
    cost_profile: ExecutionCostProfile | None = None,
) -> LimitOrderMatchingEngine:
    return LimitOrderMatchingEngine(
        database=database,
        account_service=account_service,
        order_service=order_service,
        trade_service=trade_service,
        market_reader=SequencePriceReader(prices),
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


def test_limit_buy_stays_open_when_price_not_crossed(
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
    order = engine.place_limit_order(
        LimitOrderRequest(symbol="BTC/USDT", side=OrderSide.BUY, amount=0.1, limit_price=49_000.0)
    )
    assert order.status == OrderStatus.OPEN

    sweep = engine.process_limit_order_queue("BTC/USDT")

    assert sweep.latest_price == pytest.approx(50_000.0)
    assert sweep.checked_count == 1
    assert len(sweep.matched) == 0
    assert order.id in sweep.remaining_order_ids
    assert order_service.get_order(order.id).status == OrderStatus.OPEN
    assert _count_rows(database, "trades") == 0


def test_place_limit_sell_rejects_when_inventory_missing(
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

    with pytest.raises(LimitOrderMatchingError, match="insufficient base asset balance"):
        engine.place_limit_order(
            LimitOrderRequest(symbol="BTC/USDT", side=OrderSide.SELL, amount=0.1, limit_price=50_000.0)
        )

    assert _count_rows(database, "orders") == 0
    assert _count_rows(database, "trades") == 0


def test_limit_buy_matches_when_latest_price_crosses_down(
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
        {"BTC/USDT": [48_500.0]},
    )
    order = engine.place_limit_order(
        LimitOrderRequest(symbol="BTC/USDT", side=OrderSide.BUY, amount=0.2, limit_price=49_000.0)
    )

    sweep = engine.process_limit_order_queue("BTC/USDT")

    assert len(sweep.matched) == 1
    assert sweep.matched[0].order.id == order.id
    assert sweep.matched[0].order.status == OrderStatus.FILLED
    assert sweep.matched[0].trade.price == pytest.approx(48_500.0)
    assert sweep.matched[0].trade.amount == pytest.approx(0.2)
    assert order.id not in sweep.remaining_order_ids

    usdt = account_service.get_account("USDT")
    btc = account_service.get_account("BTC")
    assert usdt.balance == pytest.approx(90_300.0)
    assert usdt.available == pytest.approx(90_300.0)
    assert usdt.frozen == pytest.approx(0.0)
    assert btc.balance == pytest.approx(0.2)
    assert btc.available == pytest.approx(0.2)


def test_limit_sell_matches_when_latest_price_crosses_up(
    database: SQLiteDatabase,
    account_service: AccountService,
    order_service: OrderService,
    trade_service: TradeService,
) -> None:
    account_service.deposit("BTC", 0.3)
    with database.transaction() as tx:
        tx.execute(
            """
            INSERT INTO positions(symbol, amount, entry_price, current_price, unrealized_pnl, realized_pnl, opened_at)
            VALUES ('BTC/USDT', 0.3, 47000.0, 47000.0, 0.0, 0.0, CURRENT_TIMESTAMP);
            """
        )

    engine = _make_engine(
        database,
        account_service,
        order_service,
        trade_service,
        {"BTC/USDT": [49_500.0, 50_500.0]},
    )
    order = engine.place_limit_order(
        LimitOrderRequest(symbol="BTC/USDT", side=OrderSide.SELL, amount=0.2, limit_price=50_000.0)
    )

    first = engine.process_limit_order_queue("BTC/USDT")
    assert len(first.matched) == 0
    assert order.id in first.remaining_order_ids

    second = engine.process_limit_order_queue("BTC/USDT")
    assert len(second.matched) == 1
    assert second.matched[0].order.status == OrderStatus.FILLED
    assert second.matched[0].trade.price == pytest.approx(50_500.0)

    usdt = account_service.get_account("USDT")
    btc = account_service.get_account("BTC")
    assert usdt.balance == pytest.approx(110_100.0)
    assert usdt.available == pytest.approx(110_100.0)
    assert btc.balance == pytest.approx(0.1)
    assert btc.available == pytest.approx(0.1)

    pos = _position_row(database, "BTC/USDT")
    assert pos["amount"] == pytest.approx(0.1)
    assert pos["realized_pnl"] == pytest.approx(700.0)


def test_limit_queue_uses_price_time_priority_for_buys(
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
        {"BTC/USDT": [49_000.0]},
    )
    low_bid = engine.place_limit_order(
        LimitOrderRequest(symbol="BTC/USDT", side=OrderSide.BUY, amount=0.1, limit_price=49_000.0)
    )
    high_bid = engine.place_limit_order(
        LimitOrderRequest(symbol="BTC/USDT", side=OrderSide.BUY, amount=0.1, limit_price=49_500.0)
    )

    sweep = engine.process_limit_order_queue("BTC/USDT")

    assert len(sweep.matched) == 2
    assert sweep.matched[0].order.id == high_bid.id
    assert sweep.matched[1].order.id == low_bid.id
    assert _count_rows(database, "orders") == 2
    assert _count_rows(database, "trades") == 2


def test_limit_buy_price_improvement_refunds_difference(
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
        {"BTC/USDT": [40_000.0]},
    )
    order = engine.place_limit_order(
        LimitOrderRequest(symbol="BTC/USDT", side=OrderSide.BUY, amount=0.5, limit_price=50_000.0)
    )

    sweep = engine.process_limit_order_queue("BTC/USDT")

    assert len(sweep.matched) == 1
    assert sweep.matched[0].order.id == order.id
    assert sweep.matched[0].trade.price == pytest.approx(40_000.0)
    assert sweep.matched[0].execution_price == pytest.approx(40_000.0)

    usdt = account_service.get_account("USDT")
    btc = account_service.get_account("BTC")
    assert usdt.balance == pytest.approx(80_000.0)
    assert usdt.available == pytest.approx(80_000.0)
    assert usdt.frozen == pytest.approx(0.0)
    assert btc.balance == pytest.approx(0.5)
    assert btc.available == pytest.approx(0.5)
