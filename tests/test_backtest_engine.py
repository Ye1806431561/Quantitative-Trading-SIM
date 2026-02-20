"""Tests for Backtrader engine integration (implementation plan step 26)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import backtrader as bt
import pytest

from src.backtest.engine import BacktestEngine, BacktestEngineError, BacktestRunRequest
from src.core.database import SQLiteDatabase
from src.strategies.registry import StrategyRegistry, StrategySpec


class BuyThenSellStrategy(bt.Strategy):
    """Simple deterministic strategy used to verify engine wiring."""

    params = (
        ("buy_size", 1.0),
        ("sell_on_bar", 4),
    )

    def __init__(self) -> None:
        self._bar_index = 0

    def next(self) -> None:
        self._bar_index += 1
        if not self.position and self._bar_index == 1:
            self.buy(size=self.params.buy_size)
            return
        if self.position and self._bar_index >= self.params.sell_on_bar:
            self.sell(size=self.position.size)


def _seed_candles(database: SQLiteDatabase) -> None:
    rows = [
        ("BTC/USDT", "1h", 1_700_000_000_000, 100.0, 102.0, 99.0, 101.0, 10.0),
        ("BTC/USDT", "1h", 1_700_000_003_600, 110.0, 113.0, 109.0, 112.0, 11.0),
        ("BTC/USDT", "1h", 1_700_000_007_200, 120.0, 124.0, 119.0, 123.0, 12.0),
        ("BTC/USDT", "1h", 1_700_000_010_800, 130.0, 135.0, 129.0, 134.0, 13.0),
        ("ETH/USDT", "1h", 1_700_000_000_000, 50.0, 51.0, 49.0, 50.5, 20.0),
    ]
    with database.transaction() as tx:
        tx.executemany(
            """
            INSERT INTO candles(symbol, timeframe, timestamp, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            rows,
        )


@pytest.fixture
def sqlite_database(tmp_path) -> SQLiteDatabase:
    database = SQLiteDatabase(tmp_path / "backtest_step_26.db")
    database.initialize_schema()
    _seed_candles(database)
    yield database
    database.close()


def _build_config(data_read_source: str = "sqlite") -> Mapping[str, Any]:
    return {
        "account": {"initial_capital": 10_000.0},
        "trading": {
            "commission": {"maker": 0.001, "taker": 0.001},
            "slippage": 0.0,
        },
        "backtest": {
            "default_timeframe": "1h",
            "default_period": 90,
            "data_read_source": data_read_source,
        },
    }


def test_backtest_engine_runs_with_pandas_feed_and_returns_basic_stats(
    sqlite_database: SQLiteDatabase,
) -> None:
    engine = BacktestEngine.from_config(database=sqlite_database, config=_build_config())
    request = BacktestRunRequest(
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=1_700_000_000_000,
        end_timestamp=1_700_000_010_800,
        strategy_class=BuyThenSellStrategy,
        strategy_params={"buy_size": 1.0, "sell_on_bar": 4},
    )

    result = engine.run(request)

    assert result.data_source == "sqlite"
    assert result.symbol == "BTC/USDT"
    assert result.timeframe == "1h"
    assert result.bars_processed == 4
    assert result.initial_capital == pytest.approx(10_000.0)
    assert result.final_value > result.initial_capital
    assert result.total_return_pct == pytest.approx(
        ((result.final_value - result.initial_capital) / result.initial_capital) * 100.0
    )


def test_backtest_engine_rejects_non_sqlite_data_read_path(
    sqlite_database: SQLiteDatabase,
) -> None:
    with pytest.raises(BacktestEngineError, match="sqlite"):
        BacktestEngine.from_config(
            database=sqlite_database,
            config=_build_config(data_read_source="csv"),
        )


def test_backtest_engine_raises_when_no_candles_in_requested_range(
    sqlite_database: SQLiteDatabase,
) -> None:
    engine = BacktestEngine.from_config(database=sqlite_database, config=_build_config())
    request = BacktestRunRequest(
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=1_700_000_100_000,
        end_timestamp=1_700_000_200_000,
        strategy_class=BuyThenSellStrategy,
    )

    with pytest.raises(BacktestEngineError, match="No candle data"):
        engine.run(request)


class ParamSpyStrategy(bt.Strategy):
    params = (("threshold", 1),)
    last_threshold = None

    def __init__(self):
        ParamSpyStrategy.last_threshold = self.params.threshold


def test_backtest_engine_applies_config_params(sqlite_database: SQLiteDatabase) -> None:
    registry = StrategyRegistry(
        {
            "spy_strategy": StrategySpec(
                name="spy_strategy",
                strategy_class=ParamSpyStrategy,
                allowed_params=("threshold",),
            )
        }
    )
    strategies_config = {
        "spy_strategy": {
            "enabled": True,
            "params": {"threshold": 42},
        }
    }

    engine = BacktestEngine(
        database=sqlite_database,
        initial_capital=10_000.0,
        commission_rate=0.0,
        slippage_rate=0.0,
        strategies_config=strategies_config,
        strategy_registry=registry,
    )

    request = BacktestRunRequest(
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=1_700_000_000_000,
        end_timestamp=1_700_000_010_800,
        strategy_class=ParamSpyStrategy,
        strategy_params={},
    )

    engine.run(request)
    assert ParamSpyStrategy.last_threshold == 42
