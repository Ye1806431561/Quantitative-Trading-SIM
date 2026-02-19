from __future__ import annotations

from collections.abc import Mapping, Sequence

import pytest

from src.core.account_service import AccountService
from src.core.database import SQLiteDatabase
from src.core.enums import OrderSide, OrderType
from src.core.limit_matching import LimitOrderMatchingEngine, LimitOrderMatchingError, LimitOrderRequest
from src.core.matching import MarketOrderRequest, MatchingEngine, MatchingEngineError
from src.core.order_service import OrderService
from src.core.stop_trigger import StopTriggerEngine, StopTriggerError, TriggerOrderRequest
from src.core.trade_service import TradeService
from src.data.realtime_payloads import RealtimeMarketSnapshot


class SequencePriceReader:
    def __init__(self, sequence: Mapping[str, Sequence[float | None]]) -> None:
        self._sequence = {symbol: list(values) for symbol, values in sequence.items()}
        self._fetched_at_ms = 1_700_400_000_000

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
    db = SQLiteDatabase(tmp_path / "risk_controls.db")
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


def _count_rows(database: SQLiteDatabase, table: str) -> int:
    with database.transaction() as tx:
        row = tx.execute(f"SELECT COUNT(*) AS c FROM {table};").fetchone()
    assert row is not None
    return int(row["c"])


def _seed_position(
    database: SQLiteDatabase,
    account_service: AccountService,
    *,
    symbol: str,
    amount: float,
    entry_price: float,
    current_price: float,
) -> None:
    base_currency = symbol.split("/")[0]
    account_service.deposit(base_currency, amount)
    with database.transaction() as tx:
        tx.execute(
            """
            INSERT INTO positions(symbol, amount, entry_price, current_price, unrealized_pnl, realized_pnl, opened_at)
            VALUES (?, ?, ?, ?, ?, 0.0, CURRENT_TIMESTAMP);
            """,
            (
                symbol,
                amount,
                entry_price,
                current_price,
                (current_price - entry_price) * amount,
            ),
        )


def test_market_order_rejects_when_single_position_limit_exceeded(
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
        market_reader=SequencePriceReader({"BTC/USDT": [50_000.0]}),
    )

    with pytest.raises(MatchingEngineError, match="single position limit exceeded"):
        engine.execute_market_order(
            MarketOrderRequest(symbol="BTC/USDT", side=OrderSide.BUY, amount=1.0)
        )

    assert _count_rows(database, "orders") == 0
    assert _count_rows(database, "trades") == 0


def test_limit_order_rejects_when_total_position_limit_exceeded(
    database: SQLiteDatabase,
    account_service: AccountService,
    order_service: OrderService,
    trade_service: TradeService,
) -> None:
    _seed_position(
        database,
        account_service,
        symbol="BTC/USDT",
        amount=3.0,
        entry_price=50_000.0,
        current_price=50_000.0,
    )
    engine = LimitOrderMatchingEngine(
        database=database,
        account_service=account_service,
        order_service=order_service,
        trade_service=trade_service,
        market_reader=SequencePriceReader({"BTC/USDT": [50_000.0]}),
    )

    with pytest.raises(LimitOrderMatchingError, match="total position limit exceeded"):
        engine.place_limit_order(
            LimitOrderRequest(
                symbol="BTC/USDT",
                side=OrderSide.BUY,
                amount=1.0,
                limit_price=55_000.0,
            )
        )

    assert _count_rows(database, "orders") == 0
    assert _count_rows(database, "trades") == 0


def test_trigger_order_rejects_when_max_drawdown_exceeded(
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
        entry_price=100_000.0,
        current_price=50_000.0,
    )
    engine = StopTriggerEngine(
        database=database,
        account_service=account_service,
        order_service=order_service,
        trade_service=trade_service,
        market_reader=SequencePriceReader({"BTC/USDT": [50_000.0]}),
    )

    with pytest.raises(StopTriggerError, match="max drawdown limit exceeded"):
        engine.place_trigger_order(
            TriggerOrderRequest(
                symbol="BTC/USDT",
                type=OrderType.TAKE_PROFIT,
                side=OrderSide.BUY,
                amount=0.1,
                trigger_price=10_000.0,
            )
        )

    assert _count_rows(database, "orders") == 0
    assert _count_rows(database, "trades") == 0
