"""Tests for standard analyzer mounting and result extraction (step 27)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import backtrader as bt
import pytest

from src.backtest import (
    BacktestEngine,
    BacktestRunRequest,
    ReturnsAnalysis,
    RiskMetrics,
    TradeStatistics,
)
from src.core.database import SQLiteDatabase


class SimpleTestStrategy(bt.Strategy):
    """Minimal strategy that executes complete buy-sell cycles for analyzer testing."""

    def __init__(self) -> None:
        self.order = None
        self.completed_trades = 0
        self.bars_in_position = 0

    def next(self) -> None:
        """Execute buy/sell trades to generate analyzer data.

        Strategy: Buy and hold for 3 bars, then sell. Repeat 3 times.
        This ensures complete closed trades for TradeAnalyzer.
        """
        # Skip if order pending
        if self.order:
            return

        if not self.position:
            # Buy when no position (limit to 3 complete cycles)
            if self.completed_trades < 3:
                self.order = self.buy(size=0.1)  # Fixed size for consistent testing
                self.bars_in_position = 0
        else:
            # Sell after holding for 3 bars
            self.bars_in_position += 1
            if self.bars_in_position >= 3:
                self.order = self.sell(size=self.position.size)
                self.completed_trades += 1
                self.bars_in_position = 0

    def notify_order(self, order: bt.Order) -> None:
        """Clear order reference when completed or cancelled."""
        if order.status in [order.Completed, order.Canceled, order.Margin]:
            self.order = None


class NoTradeStrategy(bt.Strategy):
    """Strategy that never trades (for no-trade edge case testing)."""

    def next(self) -> None:
        """Do nothing - no trades executed."""
        pass


@pytest.fixture
def temp_db() -> SQLiteDatabase:
    """Create temporary database with sample candle data."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    db = SQLiteDatabase(db_path)
    db.open()
    db.initialize_schema()

    # Insert sample candle data (30 bars, simple uptrend)
    with db.transaction():
        cursor = db._connection.cursor()
        base_ts = 1609459200000  # 2021-01-01 00:00:00 UTC
        for i in range(30):
            timestamp = base_ts + i * 3600000  # 1-hour intervals
            open_price = 40000.0 + i * 100
            high_price = open_price + 200
            low_price = open_price - 100
            close_price = open_price + 150
            volume = 10.0 + i * 0.5

            cursor.execute(
                """
                INSERT INTO candles (symbol, timeframe, timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "BTC/USDT",
                    "1h",
                    timestamp,
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    volume,
                ),
            )

    yield db

    db.close()
    Path(db_path).unlink(missing_ok=True)


def test_all_analyzers_produce_output(temp_db: SQLiteDatabase) -> None:
    """Verify all 5 analyzers produce output with complete fields (step 27 acceptance)."""
    engine = BacktestEngine(
        temp_db,
        initial_capital=10000.0,
        commission_rate=0.001,
        slippage_rate=0.0005,
    )

    request = BacktestRunRequest(
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=1609459200000,
        end_timestamp=1609459200000 + 29 * 3600000,
        strategy_class=SimpleTestStrategy,
    )

    result = engine.run(request)

    # Verify basic stats still present (backward compatibility with step 26)
    assert result.symbol == "BTC/USDT"
    assert result.timeframe == "1h"
    assert result.initial_capital == 10000.0
    assert result.bars_processed == 30

    # Verify TradeStatistics fields (step 27)
    assert isinstance(result.trade_stats, TradeStatistics)
    # CRITICAL: Verify strategy actually executed trades (not zero like no-trade scenario)
    assert result.trade_stats.total_trades > 0, "SimpleTestStrategy must execute at least 1 closed trade"
    assert result.trade_stats.won_trades >= 0
    assert result.trade_stats.lost_trades >= 0
    assert result.trade_stats.won_trades + result.trade_stats.lost_trades == result.trade_stats.total_trades
    assert 0.0 <= result.trade_stats.win_rate <= 100.0
    # profit_factor is None when all trades win (no losing trades to compute ratio)
    assert result.trade_stats.profit_factor is None or result.trade_stats.profit_factor >= 0.0
    assert isinstance(result.trade_stats.avg_profit, float)
    assert isinstance(result.trade_stats.avg_loss, float)
    assert isinstance(result.trade_stats.max_profit, float)
    assert isinstance(result.trade_stats.max_loss, float)

    # Verify RiskMetrics fields (step 27)
    assert isinstance(result.risk_metrics, RiskMetrics)
    # 30h data with Years timeframe produces no annual periods; Backtrader returns None
    assert result.risk_metrics.sharpe_ratio is None, (
        f"Expected None for 30h data (< 1 year), got {result.risk_metrics.sharpe_ratio}"
    )
    assert result.risk_metrics.max_drawdown_pct >= 0.0
    assert result.risk_metrics.max_drawdown_duration_days >= 0

    # Verify ReturnsAnalysis fields (step 27)
    assert isinstance(result.returns_analysis, ReturnsAnalysis)
    assert isinstance(result.returns_analysis.total_return, float)
    assert isinstance(result.returns_analysis.avg_return, float)

    # Verify time_series_returns format (step 27)
    assert isinstance(result.time_series_returns, dict)
    for key, value in result.time_series_returns.items():
        assert isinstance(key, str)  # ISO date string
        assert isinstance(value, float)  # Return value


def test_no_trades_scenario_returns_zeros(temp_db: SQLiteDatabase) -> None:
    """Verify TradeStatistics returns zeros when no trades executed (step 27 edge case)."""
    engine = BacktestEngine(
        temp_db,
        initial_capital=10000.0,
        commission_rate=0.001,
        slippage_rate=0.0005,
    )

    request = BacktestRunRequest(
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=1609459200000,
        end_timestamp=1609459200000 + 29 * 3600000,
        strategy_class=NoTradeStrategy,
    )

    result = engine.run(request)

    # Verify no-trade scenario returns zero-filled TradeStatistics
    assert result.trade_stats.total_trades == 0
    assert result.trade_stats.won_trades == 0
    assert result.trade_stats.lost_trades == 0
    assert result.trade_stats.win_rate == 0.0
    assert result.trade_stats.profit_factor == 0.0
    assert result.trade_stats.avg_profit == 0.0
    assert result.trade_stats.avg_loss == 0.0
    assert result.trade_stats.max_profit == 0.0
    assert result.trade_stats.max_loss == 0.0

    # Other analyzers should still produce valid output
    assert isinstance(result.risk_metrics, RiskMetrics)
    assert isinstance(result.returns_analysis, ReturnsAnalysis)
    assert isinstance(result.time_series_returns, dict)


def test_sharpe_ratio_edge_case_insufficient_data(temp_db: SQLiteDatabase) -> None:
    """Verify sharpe_ratio is None when insufficient data or zero variance (step 27 edge case)."""
    engine = BacktestEngine(
        temp_db,
        initial_capital=10000.0,
        commission_rate=0.001,
        slippage_rate=0.0005,
    )

    request = BacktestRunRequest(
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=1609459200000,
        end_timestamp=1609459200000 + 29 * 3600000,
        strategy_class=NoTradeStrategy,  # No trades = no variance
    )

    result = engine.run(request)

    # Sharpe ratio must be None when insufficient data (30 hours with Years timeframe)
    # Backtrader's SharpeRatio returns None when len(returns) == 0
    assert result.risk_metrics.sharpe_ratio is None, (
        f"Expected None for insufficient data (30h with Years timeframe), "
        f"got {result.risk_metrics.sharpe_ratio}"
    )


def test_time_series_format_iso_strings(temp_db: SQLiteDatabase) -> None:
    """Verify time_series_returns keys are ISO strings and values are floats (step 27)."""
    engine = BacktestEngine(
        temp_db,
        initial_capital=10000.0,
        commission_rate=0.001,
        slippage_rate=0.0005,
    )

    request = BacktestRunRequest(
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=1609459200000,
        end_timestamp=1609459200000 + 29 * 3600000,
        strategy_class=SimpleTestStrategy,
    )

    result = engine.run(request)

    # Verify time series format
    assert isinstance(result.time_series_returns, dict)

    if result.time_series_returns:  # May be empty for some strategies
        for key, value in result.time_series_returns.items():
            # Key should be ISO format string (e.g., "2021-01-01T00:00:00")
            assert isinstance(key, str)
            assert "T" in key or "-" in key  # Basic ISO format check

            # Value should be float
            assert isinstance(value, float)


def test_field_completeness_all_fields_present(temp_db: SQLiteDatabase) -> None:
    """Verify all fields in TradeStatistics, RiskMetrics, ReturnsAnalysis are present (step 27)."""
    engine = BacktestEngine(
        temp_db,
        initial_capital=10000.0,
        commission_rate=0.001,
        slippage_rate=0.0005,
    )

    request = BacktestRunRequest(
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=1609459200000,
        end_timestamp=1609459200000 + 29 * 3600000,
        strategy_class=SimpleTestStrategy,
    )

    result = engine.run(request)

    # Verify TradeStatistics has all 9 fields
    trade_stats_fields = {
        "total_trades",
        "won_trades",
        "lost_trades",
        "win_rate",
        "profit_factor",
        "avg_profit",
        "avg_loss",
        "max_profit",
        "max_loss",
    }
    assert set(result.trade_stats.__dataclass_fields__.keys()) == trade_stats_fields

    # Verify RiskMetrics has all 3 fields
    risk_metrics_fields = {
        "sharpe_ratio",
        "max_drawdown_pct",
        "max_drawdown_duration_days",
    }
    assert set(result.risk_metrics.__dataclass_fields__.keys()) == risk_metrics_fields

    # Verify ReturnsAnalysis has all 2 fields
    returns_analysis_fields = {"total_return", "avg_return"}
    assert set(result.returns_analysis.__dataclass_fields__.keys()) == returns_analysis_fields

    # Verify BacktestRunResult has all 13 fields (8 basic + 4 analyzer + 1 trade log)
    result_fields = {
        "symbol",
        "timeframe",
        "data_source",
        "initial_capital",
        "final_value",
        "pnl",
        "total_return_pct",
        "bars_processed",
        "trade_stats",
        "risk_metrics",
        "returns_analysis",
        "time_series_returns",
        "trade_log",  # step 28: individual closed trade records
    }
    assert set(result.__dataclass_fields__.keys()) == result_fields
