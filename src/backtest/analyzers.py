"""Standard analyzer mounting and result extraction (step 27)."""

from __future__ import annotations

from typing import Any

import backtrader as bt


class AnalyzerMount:
    """Mounts standard analyzers to Cerebro and extracts results."""

    @staticmethod
    def attach_analyzers(cerebro: bt.Cerebro) -> None:
        """Attach all standard analyzers to Cerebro instance.

        Mounted analyzers:
        - SharpeRatio: Risk-adjusted returns
        - DrawDown: Maximum drawdown and duration
        - TradeAnalyzer: Trade statistics (win rate, profit factor, etc.)
        - Returns: Period returns analysis
        - TimeReturn: Time series of returns for visualization
        """
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
        cerebro.addanalyzer(bt.analyzers.TimeReturn, _name="timereturns")

    @staticmethod
    def extract_results(strategies: list[bt.Strategy]) -> dict[str, Any]:
        """Extract analyzer results from strategy instances.

        Args:
            strategies: List of strategy instances returned by cerebro.run()

        Returns:
            Dictionary mapping analyzer names to their analysis results
        """
        if not strategies:
            raise ValueError("No strategies returned from cerebro.run()")

        # Backtrader returns list of strategies, take first one
        strategy = strategies[0]

        return {
            "sharpe": strategy.analyzers.sharpe.get_analysis(),
            "drawdown": strategy.analyzers.drawdown.get_analysis(),
            "trades": strategy.analyzers.trades.get_analysis(),
            "returns": strategy.analyzers.returns.get_analysis(),
            "timereturns": strategy.analyzers.timereturns.get_analysis(),
        }
