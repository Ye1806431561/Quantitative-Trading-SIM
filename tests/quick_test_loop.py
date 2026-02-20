#!/usr/bin/env python3
"""Quick test for realtime loop."""

import sys
import time
from unittest.mock import MagicMock

from src.core.account_service import AccountService
from src.core.database import SQLiteDatabase
from src.core.order_service import OrderService
from src.core.trade_service import TradeService
from src.data.realtime_market import RealtimeMarketDataService
from src.data.realtime_payloads import RealtimeMarketSnapshot
from src.data.storage import HistoricalCandleStorage
from src.live.price_service import PriceService
from src.live.realtime_loop import RealtimeLoopConfig, RealtimeSimulationLoop
from src.strategies.base import LiveStrategy, StrategyContext


class TestStrategy(LiveStrategy):
    def __init__(self):
        super().__init__("test")
        self.run_count = 0

    def on_initialize(self, context: StrategyContext) -> None:
        print(f"Strategy initialized: {context.symbol}")

    def on_run(self, market_data):
        self.run_count += 1
        print(f"Strategy run #{self.run_count}: price={market_data.get('latest_price')}")
        return None

    def on_stop(self, reason):
        print(f"Strategy stopped: {reason}")


# Setup
db = SQLiteDatabase(":memory:")
db.open()
db.initialize_schema()

account_service = AccountService(db, base_currency="USDT")
account_service.initialize_accounts({"USDT": 10000.0, "BTC": 0.0})

order_service = OrderService(db, account_service)
trade_service = TradeService(db, order_service)

# Mock market service
mock_market = MagicMock(spec=RealtimeMarketDataService)
mock_market.get_latest_price.return_value = RealtimeMarketSnapshot(
    channel="latest_price",
    symbol="BTC/USDT",
    ok=True,
    fallback=False,
    timed_out=False,
    error=None,
    fetched_at_ms=int(time.time() * 1000),
    data={"last_price": 50000.0, "bid": 49999.0, "ask": 50001.0},
)
mock_market.get_klines = MagicMock(return_value=[])

price_service = PriceService(db, account_service, mock_market)
candle_storage = HistoricalCandleStorage(db, mock_market.get_klines)

strategy = TestStrategy()
config = RealtimeLoopConfig(
    symbol="BTC/USDT",
    timeframe="1m",
    tick_interval_seconds=0.01,
    max_iterations=3,
)

loop = RealtimeSimulationLoop(
    database=db,
    account_service=account_service,
    order_service=order_service,
    trade_service=trade_service,
    market_service=mock_market,
    price_service=price_service,
    candle_storage=candle_storage,
    strategy=strategy,
    config=config,
)

print("Starting loop...")
loop.start()
print(f"Loop completed. Iterations: {loop.iteration_count}, Strategy runs: {strategy.run_count}")

db.close()

if strategy.run_count == 3:
    print("✓ Test passed!")
    sys.exit(0)
else:
    print(f"✗ Test failed! Expected 3 runs, got {strategy.run_count}")
    sys.exit(1)




