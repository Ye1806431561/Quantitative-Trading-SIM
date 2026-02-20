"""双均线策略（Simple Moving Average Crossover Strategy）。

内置策略实现：快线上穿慢线买入，快线下穿慢线卖出。
支持回测模式与实时模式运行。
"""

from typing import cast

import backtrader as bt
from loguru import logger


class SMAStrategy(bt.Strategy):
    """双均线交叉策略实现。

    参数:
    - fast_period: 快线周期（默认10）
    - slow_period: 慢线周期（默认30）
    - position_size: 每次交易的仓位大小（默认0.2，即20%资金）
    """

    params = (
        ("fast_period", 10),
        ("slow_period", 30),
        ("position_size", 0.2),
    )

    def __init__(self) -> None:
        """初始化策略指标。"""
        # 计算快慢均线
        self.fast_sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.fast_period
        )
        self.slow_sma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.slow_period
        )

        # 计算交叉信号：1为上穿(金叉)，-1为下穿(死叉)，0为无交叉
        self.crossover = bt.indicators.CrossOver(self.fast_sma, self.slow_sma)

        # 用于跟踪当前未完成订单
        self.order: bt.Order | None = None

    def next(self) -> None:
        """每个新 K 线周期执行的逻辑。"""
        # 如果有未完成订单，不要发送新订单
        if self.order:
            return

        # 检查是否已持仓
        if not self.position:
            # 未持仓且出现金叉（快线上穿慢线），买入
            if self.crossover[0] > 0:
                logger.debug(
                    f"SMA Buy Signal: fast={self.fast_sma[0]:.2f}, slow={self.slow_sma[0]:.2f}"
                )
                self.order = self.buy(size=self.params.position_size)
        else:
            # 已持仓且出现死叉（快线下穿慢线），卖出平仓
            if self.crossover[0] < 0:
                logger.debug(
                    f"SMA Sell Signal: fast={self.fast_sma[0]:.2f}, slow={self.slow_sma[0]:.2f}"
                )
                self.order = self.close()

    def notify_order(self, order: bt.Order) -> None:
        """订单状态更新回调。"""
        if order.status in [order.Submitted, order.Accepted]:
            # 尚未完成
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                logger.debug(
                    f"BUY EXECUTED, Price: {order.executed.price:.2f}, "
                    f"Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}"
                )
            else:
                logger.debug(
                    f"SELL EXECUTED, Price: {order.executed.price:.2f}, "
                    f"Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}"
                )

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            logger.warning(f"Order Canceled/Margin/Rejected: {order.status}")

        # 重置订单以允许新订单
        self.order = None
