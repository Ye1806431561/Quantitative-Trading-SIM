"""Performance analysis utilities (Phase 4 Step 35)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Mapping, Sequence


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
    else:
        raise PerformanceAnalysisError("returns_series support not implemented yet")

    if len(series) < 2:
        raise PerformanceAnalysisError("equity curve must contain at least two points")

    initial_equity = series[0][1]
    final_equity = series[-1][1]
    if initial_equity <= 0:
        raise PerformanceAnalysisError("initial equity must be > 0")

    total_return = (final_equity / initial_equity) - 1.0
    max_drawdown = _compute_max_drawdown(series)

    total_trades = len(trade_log) if trade_log is not None else 0

    return PerformanceSummary(
        total_return=total_return,
        annualized_return=None,
        max_drawdown=max_drawdown,
        sharpe_ratio=None,
        sortino_ratio=None,
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
