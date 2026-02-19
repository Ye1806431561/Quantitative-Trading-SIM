from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from src.core.account_service import AccountService
from src.core.database import SQLiteDatabase
from src.core.enums import OrderSide, OrderStatus, OrderType
from src.core.execution_cost import ExecutionCostProfile
from src.core.order_service import OrderService
from src.core.stop_trigger import StopTriggerEngine, StopTriggerError, TriggerOrderRequest
from src.core.trade_service import TradeService
from src.data.realtime_payloads import RealtimeMarketSnapshot

class SequencePriceReader:
    def __init__(self, sequence: Mapping[str, Sequence[float | None]]) -> None:
        self._sequence = {symbol: list(values) for symbol, values in sequence.items()}
        self._fetched_at_ms = 1_700_200_000_000

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
    db = SQLiteDatabase(tmp_path / "stop_trigger.db")
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
) -> StopTriggerEngine:
    return StopTriggerEngine(
        database=database,
        account_service=account_service,
        order_service=order_service,
        trade_service=trade_service,
        market_reader=SequencePriceReader(prices),
        cost_profile=cost_profile or ExecutionCostProfile(0.0, 0.0, 0.0),
    )

def _seed_position(
    database: SQLiteDatabase,
    account_service: AccountService,
    *,
    symbol: str,
    amount: float,
    entry_price: float,
) -> None:
    base_currency = symbol.split("/")[0]
    account_service.deposit(base_currency, amount)
    with database.transaction() as tx:
        tx.execute(
            """
            INSERT INTO positions(symbol, amount, entry_price, current_price, unrealized_pnl, realized_pnl, opened_at)
            VALUES (?, ?, ?, ?, 0.0, 0.0, CURRENT_TIMESTAMP);
            """,
            (symbol, amount, entry_price, entry_price),
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


def test_stop_loss_sell_stays_open_before_trigger(
    database: SQLiteDatabase,
    account_service: AccountService,
    order_service: OrderService,
    trade_service: TradeService,
) -> None:
    _seed_position(
        database,
        account_service,
        symbol="BTC/USDT",
        amount=0.2,
        entry_price=50_000.0,
    )
    engine = _make_engine(
        database,
        account_service,
        order_service,
        trade_service,
        {"BTC/USDT": [49_500.0]},
    )
    order = engine.place_trigger_order(TriggerOrderRequest(
        symbol="BTC/USDT",
        type=OrderType.STOP_LOSS,
        side=OrderSide.SELL,
        amount=0.1,
        trigger_price=49_000.0,
    ))
    sweep = engine.process_trigger_orders("BTC/USDT")

    assert order.status == OrderStatus.OPEN
    assert sweep.checked_count == 1
    assert len(sweep.matched) == 0
    assert order.id in sweep.remaining_order_ids
    assert order_service.get_order(order.id).status == OrderStatus.OPEN
    assert _count_rows(database, "trades") == 0


def test_stop_loss_sell_triggers_and_fills(
    database: SQLiteDatabase,
    account_service: AccountService,
    order_service: OrderService,
    trade_service: TradeService,
) -> None:
    _seed_position(database, account_service, symbol="BTC/USDT", amount=0.3, entry_price=50_000.0)
    engine = _make_engine(
        database,
        account_service,
        order_service,
        trade_service,
        {"BTC/USDT": [48_000.0]},
    )
    order = engine.place_trigger_order(TriggerOrderRequest(
        symbol="BTC/USDT",
        type=OrderType.STOP_LOSS,
        side=OrderSide.SELL,
        amount=0.1,
        trigger_price=49_000.0,
    ))
    sweep = engine.process_trigger_orders("BTC/USDT")

    assert len(sweep.matched) == 1
    assert sweep.matched[0].order.id == order.id
    assert sweep.matched[0].order.status == OrderStatus.FILLED
    assert sweep.matched[0].trade.price == pytest.approx(49_000.0)
    assert order.id not in sweep.remaining_order_ids

    usdt = account_service.get_account("USDT")
    btc = account_service.get_account("BTC")
    assert usdt.balance == pytest.approx(104_900.0)
    assert usdt.available == pytest.approx(104_900.0)
    assert btc.balance == pytest.approx(0.2)
    assert btc.available == pytest.approx(0.2)
    pos = _position_row(database, "BTC/USDT")
    assert pos["amount"] == pytest.approx(0.2)
    assert pos["realized_pnl"] == pytest.approx(-100.0)


def test_take_profit_sell_triggers_and_updates_state_machine(
    database: SQLiteDatabase,
    account_service: AccountService,
    order_service: OrderService,
    trade_service: TradeService,
) -> None:
    _seed_position(database, account_service, symbol="BTC/USDT", amount=0.3, entry_price=47_000.0)
    engine = _make_engine(
        database,
        account_service,
        order_service,
        trade_service,
        {"BTC/USDT": [51_000.0]},
    )
    order = engine.place_trigger_order(TriggerOrderRequest(
        symbol="BTC/USDT",
        type=OrderType.TAKE_PROFIT,
        side=OrderSide.SELL,
        amount=0.2,
        trigger_price=50_000.0,
    ))
    assert order.status == OrderStatus.OPEN

    sweep = engine.process_trigger_orders("BTC/USDT")
    assert len(sweep.matched) == 1
    assert sweep.matched[0].order.status == OrderStatus.FILLED
    assert sweep.matched[0].trade.price == pytest.approx(50_000.0)

    usdt = account_service.get_account("USDT")
    btc = account_service.get_account("BTC")
    assert usdt.balance == pytest.approx(110_000.0)
    assert usdt.available == pytest.approx(110_000.0)
    assert btc.balance == pytest.approx(0.1)
    assert btc.available == pytest.approx(0.1)
    pos = _position_row(database, "BTC/USDT")
    assert pos["amount"] == pytest.approx(0.1)
    assert pos["realized_pnl"] == pytest.approx(600.0)


def test_take_profit_buy_triggers_when_price_drops_to_threshold(
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
        {"BTC/USDT": [44_000.0]},
    )
    order = engine.place_trigger_order(TriggerOrderRequest(
        symbol="BTC/USDT",
        type=OrderType.TAKE_PROFIT,
        side=OrderSide.BUY,
        amount=0.5,
        trigger_price=45_000.0,
    ))
    assert order.status == OrderStatus.OPEN

    sweep = engine.process_trigger_orders("BTC/USDT")
    assert len(sweep.matched) == 1
    assert sweep.matched[0].order.status == OrderStatus.FILLED
    assert sweep.matched[0].trade.price == pytest.approx(45_000.0)

    usdt = account_service.get_account("USDT")
    btc = account_service.get_account("BTC")
    assert usdt.balance == pytest.approx(77_500.0)
    assert usdt.available == pytest.approx(77_500.0)
    assert usdt.frozen == pytest.approx(0.0)
    assert btc.balance == pytest.approx(0.5)
    assert btc.available == pytest.approx(0.5)


def test_place_sell_trigger_rejects_when_inventory_missing(
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

    with pytest.raises(StopTriggerError, match="insufficient base asset balance"):
        engine.place_trigger_order(TriggerOrderRequest(
            symbol="BTC/USDT",
            type=OrderType.STOP_LOSS,
            side=OrderSide.SELL,
            amount=0.1,
            trigger_price=49_000.0,
        ))
    assert _count_rows(database, "orders") == 0
    assert _count_rows(database, "trades") == 0
