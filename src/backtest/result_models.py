"""Backtest result data models (step 27 refactoring)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import backtrader as bt


@dataclass(frozen=True)
class BacktestRunRequest:
    """Input payload for a single backtest run."""

    symbol: str
    timeframe: str
    start_timestamp: int
    end_timestamp: int
    strategy_class: type[bt.Strategy]
    strategy_params: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TradeStatistics:
    """Trade-level statistics from TradeAnalyzer (step 27)."""

    total_trades: int
    won_trades: int
    lost_trades: int
    win_rate: float  # percentage
    profit_factor: float | None  # gross_profit / gross_loss; None if no losing trades (all wins)
    avg_profit: float
    avg_loss: float
    max_profit: float
    max_loss: float


@dataclass(frozen=True)
class TradeRecord:
    """Single closed trade record collected via notify_trade() (step 28)."""

    entry_time: str   # ISO datetime string
    exit_time: str    # ISO datetime string
    side: str         # 'long' or 'short'
    size: float       # position size
    entry_price: float
    exit_price: float
    pnl_gross: float  # gross profit/loss before commission
    pnl_net: float    # net profit/loss after commission


@dataclass(frozen=True)
class RiskMetrics:
    """Risk-adjusted performance metrics (step 27)."""

    sharpe_ratio: float | None  # None if insufficient data
    max_drawdown_pct: float
    max_drawdown_duration_days: int


@dataclass(frozen=True)
class ReturnsAnalysis:
    """Returns analysis from Returns analyzer (step 27)."""

    total_return: float
    avg_return: float


@dataclass(frozen=True)
class BacktestRunResult:
    """Extended backtest result with standard analyzers (step 27)."""

    # Basic stats (from step 26)
    symbol: str
    timeframe: str
    data_source: str
    initial_capital: float
    final_value: float
    pnl: float
    total_return_pct: float
    bars_processed: int

    # Analyzer outputs (step 27)
    trade_stats: TradeStatistics
    risk_metrics: RiskMetrics
    returns_analysis: ReturnsAnalysis
    time_series_returns: dict[str, float]  # ISO date -> return value

    # Trade log (step 28): individual closed trade records from notify_trade()
    trade_log: tuple[TradeRecord, ...] = field(default_factory=tuple)
