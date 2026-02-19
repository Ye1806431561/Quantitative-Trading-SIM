"""Analyzer result transformation utilities (step 27 refactoring)."""

from __future__ import annotations

from typing import Any

from src.backtest.result_models import ReturnsAnalysis, RiskMetrics, TradeStatistics


class AnalyzerResultBuilder:
    """Transforms raw Backtrader analyzer outputs into structured result models."""

    @staticmethod
    def build_trade_stats(trades_analysis: dict[str, Any]) -> TradeStatistics:
        """Transform TradeAnalyzer output into TradeStatistics (step 27).

        Args:
            trades_analysis: Raw output from bt.analyzers.TradeAnalyzer

        Returns:
            TradeStatistics with all fields populated (zeros if no trades)
        """
        # Handle case: no trades executed
        if not trades_analysis or "total" not in trades_analysis:
            return TradeStatistics(
                total_trades=0,
                won_trades=0,
                lost_trades=0,
                win_rate=0.0,
                profit_factor=0.0,
                avg_profit=0.0,
                avg_loss=0.0,
                max_profit=0.0,
                max_loss=0.0,
            )

        total = trades_analysis["total"]["total"]
        won = trades_analysis.get("won", {}).get("total", 0)
        lost = trades_analysis.get("lost", {}).get("total", 0)

        win_rate = (won / total * 100.0) if total > 0 else 0.0

        gross_profit = trades_analysis.get("won", {}).get("pnl", {}).get("total", 0.0)
        gross_loss = abs(trades_analysis.get("lost", {}).get("pnl", {}).get("total", 0.0))
        if gross_loss > 0:
            profit_factor: float | None = gross_profit / gross_loss
        elif gross_profit > 0:
            profit_factor = None  # All wins, no losing trades; undefined (infinite)
        else:
            profit_factor = 0.0  # No trades executed

        avg_profit = trades_analysis.get("won", {}).get("pnl", {}).get("average", 0.0)
        avg_loss = trades_analysis.get("lost", {}).get("pnl", {}).get("average", 0.0)
        max_profit = trades_analysis.get("won", {}).get("pnl", {}).get("max", 0.0)
        max_loss = trades_analysis.get("lost", {}).get("pnl", {}).get("max", 0.0)

        return TradeStatistics(
            total_trades=total,
            won_trades=won,
            lost_trades=lost,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            max_profit=max_profit,
            max_loss=max_loss,
        )

    @staticmethod
    def build_risk_metrics(
        sharpe_analysis: dict[str, Any],
        drawdown_analysis: dict[str, Any],
    ) -> RiskMetrics:
        """Transform Sharpe and DrawDown analyzer outputs into RiskMetrics (step 27).

        Args:
            sharpe_analysis: Raw output from bt.analyzers.SharpeRatio
            drawdown_analysis: Raw output from bt.analyzers.DrawDown

        Returns:
            RiskMetrics with sharpe_ratio (may be None), max_drawdown, and duration
        """
        # Sharpe ratio may be None if insufficient data or zero variance
        sharpe_ratio = sharpe_analysis.get("sharperatio", None)

        max_dd_pct = drawdown_analysis.get("max", {}).get("drawdown", 0.0)
        max_dd_len = drawdown_analysis.get("max", {}).get("len", 0)

        return RiskMetrics(
            sharpe_ratio=sharpe_ratio,
            max_drawdown_pct=max_dd_pct,
            max_drawdown_duration_days=max_dd_len,
        )

    @staticmethod
    def build_returns_analysis(returns_analysis: dict[str, Any]) -> ReturnsAnalysis:
        """Transform Returns analyzer output into ReturnsAnalysis (step 27).

        Args:
            returns_analysis: Raw output from bt.analyzers.Returns

        Returns:
            ReturnsAnalysis with total_return and avg_return
        """
        total_return = returns_analysis.get("rtot", 0.0)
        avg_return = returns_analysis.get("ravg", 0.0)

        return ReturnsAnalysis(
            total_return=total_return,
            avg_return=avg_return,
        )

    @staticmethod
    def build_time_series(timereturns_analysis: dict[Any, Any]) -> dict[str, float]:
        """Transform TimeReturn analyzer output into ISO date -> return dict (step 27).

        Args:
            timereturns_analysis: Raw output from bt.analyzers.TimeReturn
                                  (datetime keys -> return values)

        Returns:
            Dictionary with ISO string keys and float values for JSON serialization
        """
        # TimeReturn returns {datetime: return_value}
        # Convert datetime keys to ISO strings for JSON serialization
        return {
            dt.isoformat(): float(ret_val)
            for dt, ret_val in timereturns_analysis.items()
        }
