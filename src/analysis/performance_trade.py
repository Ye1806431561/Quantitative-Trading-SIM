"""Trade-log derived performance metrics."""

from __future__ import annotations

from typing import Mapping, Sequence

from src.analysis.performance_errors import PerformanceAnalysisError


def _compute_trade_metrics(
    trade_log: Sequence[Mapping[str, float]] | Sequence[object] | None,
) -> tuple[int, int, int, float, float | None]:
    if trade_log is None:
        return 0, 0, 0, 0.0, 0.0

    total_trades = len(trade_log)
    if total_trades == 0:
        return 0, 0, 0, 0.0, 0.0

    winning_trades = 0
    losing_trades = 0
    gross_profit = 0.0
    gross_loss = 0.0

    for trade in trade_log:
        pnl = _extract_trade_pnl(trade)
        if pnl > 0:
            winning_trades += 1
            gross_profit += pnl
        elif pnl < 0:
            losing_trades += 1
            gross_loss += abs(pnl)

    win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
    if gross_loss > 0:
        profit_factor: float | None = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = None
    else:
        profit_factor = 0.0

    return total_trades, winning_trades, losing_trades, win_rate, profit_factor


def _extract_trade_pnl(trade: Mapping[str, float] | object) -> float:
    if isinstance(trade, Mapping):
        if "pnl_net" in trade:
            value = trade["pnl_net"]
        elif "pnl_gross" in trade:
            value = trade["pnl_gross"]
        else:
            raise PerformanceAnalysisError("trade log entries must include pnl_net or pnl_gross")
    else:
        if hasattr(trade, "pnl_net"):
            value = getattr(trade, "pnl_net")
        elif hasattr(trade, "pnl_gross"):
            value = getattr(trade, "pnl_gross")
        else:
            raise PerformanceAnalysisError("trade log entries must include pnl_net or pnl_gross")

    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise PerformanceAnalysisError("trade pnl value must be numeric")
    return float(value)
