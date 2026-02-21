"""Performance analysis utilities (Phase 4 Step 35)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
import statistics
from typing import Mapping, Sequence


class PerformanceAnalysisError(RuntimeError):
    """Raised when performance analysis inputs are invalid."""


@dataclass(frozen=True)
class PerformanceSummary:
    total_return: float
    annualized_return: float | None
    max_drawdown: float
    sharpe_ratio: float | None
    sortino_ratio: float | None
    win_rate: float
    profit_factor: float | None
    total_trades: int
    winning_trades: int
    losing_trades: int


def analyze_performance(
    *,
    equity_curve: Mapping[object, float] | Sequence[tuple[object, float]] | None = None,
    returns_series: Mapping[object, float] | Sequence[tuple[object, float]] | None = None,
    initial_capital: float | None = None,
    trade_log: Sequence[Mapping[str, float]] | Sequence[object] | None = None,
    risk_free_rate: float = 0.0,
) -> PerformanceSummary:
    """Compute performance metrics from equity curve or returns series.

    Equity curve takes precedence when both are provided.
    """
    if equity_curve is None and returns_series is None:
        raise PerformanceAnalysisError("equity_curve or returns_series must be provided")

    if equity_curve is not None:
        series = _normalize_series(equity_curve)
        initial_equity = series[0][1]
    else:
        series, initial_equity = _reconstruct_equity_curve(
            returns_series=returns_series,
            initial_capital=initial_capital,
        )

    if len(series) < 2:
        raise PerformanceAnalysisError("equity curve must contain at least two points")
    final_equity = series[-1][1]
    if initial_equity <= 0:
        raise PerformanceAnalysisError("initial equity must be > 0")

    total_return = (final_equity / initial_equity) - 1.0
    max_drawdown = _compute_max_drawdown(series)
    annualized_return = _compute_annualized_return(series, initial_equity, final_equity)

    returns = _compute_returns(series)
    sharpe_ratio = _compute_sharpe_ratio(returns, risk_free_rate, series)
    sortino_ratio = _compute_sortino_ratio(returns, risk_free_rate, series)

    total_trades = len(trade_log) if trade_log is not None else 0

    return PerformanceSummary(
        total_return=total_return,
        annualized_return=annualized_return,
        max_drawdown=max_drawdown,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        win_rate=0.0,
        profit_factor=0.0,
        total_trades=total_trades,
        winning_trades=0,
        losing_trades=0,
    )


def _normalize_series(
    series: Mapping[object, float] | Sequence[tuple[object, float]]
) -> list[tuple[float, float]]:
    if isinstance(series, Mapping):
        items = list(series.items())
    else:
        items = list(series)

    if not items:
        raise PerformanceAnalysisError("series must not be empty")

    normalized: list[tuple[float, float]] = []
    for raw_ts, raw_value in items:
        if not isinstance(raw_value, (int, float)) or isinstance(raw_value, bool):
            raise PerformanceAnalysisError("series values must be numeric")
        timestamp = _parse_timestamp(raw_ts)
        normalized.append((timestamp, float(raw_value)))

    normalized.sort(key=lambda item: item[0])
    return normalized


def _parse_timestamp(value: object) -> float:
    if isinstance(value, bool):
        raise PerformanceAnalysisError("timestamp must be int, float, or ISO string")
    if isinstance(value, (int, float)):
        numeric = float(value)
        if numeric <= 0:
            raise PerformanceAnalysisError("timestamp must be positive")
        # Heuristic: treat large values as milliseconds
        if numeric > 1e11:
            return numeric / 1000.0
        return numeric
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
        except ValueError as exc:
            raise PerformanceAnalysisError("timestamp must be ISO 8601 string") from exc
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()

    raise PerformanceAnalysisError("timestamp must be int, float, or ISO string")

def _reconstruct_equity_curve(
    *,
    returns_series: Mapping[object, float] | Sequence[tuple[object, float]] | None,
    initial_capital: float | None,
) -> tuple[list[tuple[float, float]], float]:
    if returns_series is None:
        raise PerformanceAnalysisError("equity_curve or returns_series must be provided")
    if not isinstance(initial_capital, (int, float)) or isinstance(initial_capital, bool):
        raise PerformanceAnalysisError("initial_capital must be a number when using returns_series")
    if float(initial_capital) <= 0:
        raise PerformanceAnalysisError("initial_capital must be > 0 when using returns_series")

    returns = _normalize_series(returns_series)
    equity_points: list[tuple[float, float]] = []
    equity = float(initial_capital)
    for timestamp, ret in returns:
        equity *= 1.0 + ret
        equity_points.append((timestamp, equity))
    if not equity_points:
        raise PerformanceAnalysisError("returns_series must not be empty")
    return equity_points, float(initial_capital)


def _compute_max_drawdown(series: Sequence[tuple[float, float]]) -> float:
    peak = series[0][1]
    max_drawdown = 0.0
    for _, equity in series:
        if equity > peak:
            peak = equity
        if peak > 0:
            drawdown = (peak - equity) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
    return max_drawdown


def _compute_returns(series: Sequence[tuple[float, float]]) -> list[float]:
    returns: list[float] = []
    for idx in range(1, len(series)):
        prev = series[idx - 1][1]
        current = series[idx][1]
        if prev <= 0:
            raise PerformanceAnalysisError("equity values must be > 0 to compute returns")
        returns.append((current / prev) - 1.0)
    return returns


def _compute_annualized_return(
    series: Sequence[tuple[float, float]],
    initial_equity: float,
    final_equity: float,
) -> float | None:
    elapsed_seconds = series[-1][0] - series[0][0]
    if elapsed_seconds <= 0:
        return None
    year_seconds = 365.0 * 24.0 * 3600.0
    try:
        return (final_equity / initial_equity) ** (year_seconds / elapsed_seconds) - 1.0
    except OverflowError as exc:
        raise PerformanceAnalysisError("annualized return overflow") from exc


def _periods_per_year(series: Sequence[tuple[float, float]]) -> float | None:
    elapsed_seconds = series[-1][0] - series[0][0]
    if elapsed_seconds <= 0 or len(series) < 2:
        return None
    avg_interval = elapsed_seconds / (len(series) - 1)
    if avg_interval <= 0:
        return None
    year_seconds = 365.0 * 24.0 * 3600.0
    return year_seconds / avg_interval


def _compute_sharpe_ratio(
    returns: Sequence[float],
    risk_free_rate: float,
    series: Sequence[tuple[float, float]],
) -> float | None:
    if len(returns) < 2:
        return None
    excess = [ret - risk_free_rate for ret in returns]
    stdev = statistics.pstdev(excess)
    if stdev == 0:
        return None
    periods = _periods_per_year(series)
    if periods is None:
        return None
    return statistics.mean(excess) / stdev * math.sqrt(periods)


def _compute_sortino_ratio(
    returns: Sequence[float],
    risk_free_rate: float,
    series: Sequence[tuple[float, float]],
) -> float | None:
    if len(returns) < 2:
        return None
    excess = [ret - risk_free_rate for ret in returns]
    downside = [ret for ret in excess if ret < 0]
    if len(downside) < 2:
        return None
    downside_dev = statistics.pstdev(downside)
    if downside_dev == 0:
        return None
    periods = _periods_per_year(series)
    if periods is None:
        return None
    return statistics.mean(excess) / downside_dev * math.sqrt(periods)
