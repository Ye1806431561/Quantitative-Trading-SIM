from __future__ import annotations

from collections.abc import Mapping, Sequence

import pytest

from src.core.account_service import AccountService
from src.core.database import SQLiteDatabase
from src.core.enums import OrderSide, OrderStatus, OrderType
from src.core.execution_cost import ExecutionCostProfile
from src.core.limit_matching import LimitOrderMatchingEngine, LimitOrderRequest
from src.core.matching import MarketOrderRequest, MatchingEngine
from src.core.order_service import OrderService
from src.core.stop_trigger import StopTriggerEngine, TriggerOrderRequest
from src.core.trade_service import TradeService
from src.data.realtime_payloads import RealtimeMarketSnapshot


class SequencePriceReader:
    def __init__(self, sequence: Mapping[str, Sequence[float | None]]) -> None:
        self._sequence = {symbol: list(values) for symbol, values in sequence.items()}
        self._fetched_at_ms = 1_700_300_000_000

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
    db = SQLiteDatabase(tmp_path / "execution_costs.db")
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


def _latest_trade_fee(database: SQLiteDatabase) -> float:
    with database.transaction() as tx:
        row = tx.execute("SELECT fee FROM trades ORDER BY id DESC LIMIT 1;").fetchone()
    assert row is not None
    return float(row["fee"])


def test_market_order_applies_taker_fee_and_slippage(
    database: SQLiteDatabase,
    account_service: AccountService,
    order_service: OrderService,
    trade_service: TradeService,
) -> None:
    engine = MatchingEngine(
        database=database,
        account_service=account_service,
        order_service=order_service,
        trade_service=trade_service,
        market_reader=SequencePriceReader({"BTC/USDT": [100.0]}),
        cost_profile=ExecutionCostProfile(maker_fee_rate=0.001, taker_fee_rate=0.002, slippage_rate=0.01),
    )

    result = engine.execute_market_order(
        MarketOrderRequest(symbol="BTC/USDT", side=OrderSide.BUY, amount=1.0)
    )

    assert result.order.status == OrderStatus.FILLED
    assert result.execution_price == pytest.approx(101.0)
    assert result.trade.price == pytest.approx(101.0)
    assert result.trade.fee == pytest.approx(0.202)
    assert _latest_trade_fee(database) == pytest.approx(0.202)


def test_limit_order_applies_maker_fee_and_bounded_slippage(
    database: SQLiteDatabase,
    account_service: AccountService,
    order_service: OrderService,
    trade_service: TradeService,
) -> None:
    engine = LimitOrderMatchingEngine(
        database=database,
        account_service=account_service,
        order_service=order_service,
        trade_service=trade_service,
        market_reader=SequencePriceReader({"BTC/USDT": [100.0]}),
        cost_profile=ExecutionCostProfile(maker_fee_rate=0.001, taker_fee_rate=0.003, slippage_rate=0.02),
    )
    order = engine.place_limit_order(
        LimitOrderRequest(symbol="BTC/USDT", side=OrderSide.BUY, amount=1.0, limit_price=101.0)
    )

    sweep = engine.process_limit_order_queue("BTC/USDT")

    assert len(sweep.matched) == 1
    assert sweep.matched[0].order.id == order.id
    assert sweep.matched[0].execution_price == pytest.approx(101.0)
    assert sweep.matched[0].trade.fee == pytest.approx(0.101)
    assert _latest_trade_fee(database) == pytest.approx(0.101)


def test_trigger_order_applies_taker_fee_and_sell_side_slippage(
    database: SQLiteDatabase,
    account_service: AccountService,
    order_service: OrderService,
    trade_service: TradeService,
) -> None:
    _seed_position(
        database,
        account_service,
        symbol="BTC/USDT",
        amount=1.0,
        entry_price=100.0,
    )
    engine = StopTriggerEngine(
        database=database,
        account_service=account_service,
        order_service=order_service,
        trade_service=trade_service,
        market_reader=SequencePriceReader({"BTC/USDT": [99.0]}),
        cost_profile=ExecutionCostProfile(maker_fee_rate=0.001, taker_fee_rate=0.003, slippage_rate=0.01),
    )
    order = engine.place_trigger_order(
        TriggerOrderRequest(
            symbol="BTC/USDT",
            type=OrderType.STOP_LOSS,
            side=OrderSide.SELL,
            amount=0.5,
            trigger_price=100.0,
        )
    )

    sweep = engine.process_trigger_orders("BTC/USDT")

    assert len(sweep.matched) == 1
    assert sweep.matched[0].order.id == order.id
    assert sweep.matched[0].trade.price == pytest.approx(99.0)
    assert sweep.matched[0].trade.fee == pytest.approx(0.1485)
    assert _latest_trade_fee(database) == pytest.approx(0.1485)
