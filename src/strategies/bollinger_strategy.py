"""布林带策略（Bollinger Bands Strategy）。

内置策略实现：价格回升/回落确认后产生交易信号。
- 价格下穿下轨并回升：买入
- 价格上穿上轨并回落：平仓
- 价格回到中轨：平仓
本实现采用回升/回落确认逻辑，避免单根穿越误触发。
支持回测模式与实时模式运行。
"""

from typing import cast

import backtrader as bt
from loguru import logger


class BollingerStrategy(bt.Strategy):
    """布林带均值回归策略实现。

    参数:
    - period: 移动平均周期（默认20）
    - dev: 标准差倍数（默认2.0）
    - position_size: 每次交易的仓位大小（默认0.2）
    """

    params = (
        ("period", 20),
        ("dev", 2.0),
        ("position_size", 0.2),
    )

    def __init__(self) -> None:
        """初始化策略指标。"""
        # 初始化布林带指标
        self.bb = bt.indicators.BollingerBands(
            self.data.close, period=self.params.period, devfactor=self.params.dev
        )
        self.was_below_lower = False
        self.was_above_upper = False
        # 用于跟踪当前未完成订单
        self.order: bt.Order | None = None

    def next(self) -> None:
        """每个新 K 线周期执行的逻辑。"""
        # 如果有未完成订单，不要发送新订单
        if self.order:
            return

        if self.data.close[0] < self.bb.lines.bot[0]:
            self.was_below_lower = True
        if self.data.close[0] > self.bb.lines.top[0]:
            self.was_above_upper = True

        # 检查是否已持仓
        if not self.position:
            # 未持仓且价格从下向上越过下轨，且当前价格回升（均值回归确认）
            if (
                self.was_below_lower
                and self.data.close[0] >= self.bb.lines.bot[0]
                and self.data.close[0] > self.data.close[-1]
            ):
                logger.debug("BB Buy Signal: Price rebounded above Lower band")
                self.order = self.buy(size=self.params.position_size)
                self.was_below_lower = False
        else:
            # 已持仓
            # 1. 价格从上向下越过上轨，平仓
            if (
                self.was_above_upper
                and self.data.close[0] <= self.bb.lines.top[0]
                and self.data.close[0] < self.data.close[-1]
            ):
                logger.debug("BB Close Signal (Upper): Price pulled back below Upper band")
                self.order = self.close()
                self.was_above_upper = False
            # 2. 价格回归到中轨，平仓（止盈）
            elif self.data.close[0] >= self.bb.lines.mid[0]:
                logger.debug(
                    f"BB Close Signal (Mid): Price({self.data.close[0]:.2f}) reached Mid({self.bb.lines.mid[0]:.2f})"
                )
                self.order = self.close()

    def notify_order(self, order: bt.Order) -> None:
        """订单状态更新回调。"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                logger.debug(
                    f"BB BUY EXECUTED, Price: {order.executed.price:.2f}, "
                    f"Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}"
                )
            else:
                logger.debug(
                    f"BB SELL EXECUTED, Price: {order.executed.price:.2f}, "
                    f"Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}"
                )

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            logger.warning(f"BB Order failed: {order.status} (Canceled/Margin/Rejected)")

        # 重置订单以允许新订单
        self.order = None
