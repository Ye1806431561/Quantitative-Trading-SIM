"""网格策略（Grid Strategy）。

内置策略实现：在设定价格区间内布置买卖挂单（限价单），价格震荡时低买高卖。
支持回测模式与实时模式运行。
"""

from typing import cast

import backtrader as bt
from loguru import logger


class GridStrategy(bt.Strategy):
    """网格交易策略实现。

    参数:
    - grid_num: 网格数量（默认10）
    - price_range: 网格价格区间比例（默认0.1，即基准价的 ±10% 总跨度）
    - position_size: 每个网格的交易仓位大小（默认0.1）
    """

    params = (
        ("grid_num", 10),
        ("price_range", 0.1),
        ("position_size", 0.1),
    )

    def __init__(self) -> None:
        """初始化策略状态。"""
        self.grid_initialized = False
        self.base_price = 0.0
        self.grid_step = 0.0
        
        # 记录每个网格级别的订单和状态
        self.buy_orders: dict[int, bt.Order] = {}  # level -> order
        self.sell_orders: dict[int, bt.Order] = {} # level -> order

        # 参数校验
        if self.params.grid_num < 1:
            raise ValueError("grid_num must be >= 1")

    def next(self) -> None:
        """每个新 K 线周期执行的逻辑。"""
        if not self.grid_initialized:
            self._initialize_grid()

    def _initialize_grid(self) -> None:
        """初始化网格并放置初始订单。"""
        # 使用第一根K线的收盘价作为基准单价
        self.base_price = self.data.close[0]
        half_grid = self.params.grid_num // 2
        
        if half_grid < 1:
            half_grid = 1 # 至少各有1个买卖网格
            
        # 计算网格步长：(基准价 * price_range) / grid_num
        self.grid_step = (self.base_price * self.params.price_range) / self.params.grid_num
        
        if self.grid_step <= 0:
            logger.warning("Grid step is zero or negative. Grid strategy cannot be initialized.")
            return

        self.grid_initialized = True
        logger.info(f"Grid Strategy Init: Base={self.base_price:.2f}, Step={self.grid_step:.2f}")

        # 基准价下方放买单 (level = -1, -2, ...)
        for i in range(1, half_grid + 1):
            level = -i
            buy_price = self.base_price + level * self.grid_step
            order = self.buy(exectype=bt.Order.Limit, price=buy_price, size=self.params.position_size)
            self.buy_orders[level] = order
            logger.debug(f"Init BUY level {level}, price: {buy_price:.2f}")

        # 基准价上方放卖单 (level = 1, 2, ...)
        for i in range(1, half_grid + 1):
            level = i
            sell_price = self.base_price + level * self.grid_step
            order = self.sell(exectype=bt.Order.Limit, price=sell_price, size=self.params.position_size)
            self.sell_orders[level] = order
            logger.debug(f"Init SELL level {level}, price: {sell_price:.2f}")

    def notify_order(self, order: bt.Order) -> None:
        """订单状态更新回调。"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                logger.debug(
                    f"BUY EXECUTED, Price: {order.executed.price:.2f}, "
                    f"Cost: {order.executed.value:.2f}"
                )
                level = self._find_order_level(order, self.buy_orders)
                if level is not None:
                    # 买单成交，放置对应上方一个 step 的卖单 (level + 1)
                    sell_price = order.executed.price + self.grid_step
                    new_order = self.sell(exectype=bt.Order.Limit, price=sell_price, size=self.params.position_size)
                    self.sell_orders[level + 1] = new_order
                    del self.buy_orders[level]
                    logger.debug(f"Grid level {level} BUY filled -> Placed SELL at level {level + 1}, price: {sell_price:.2f}")
            else:
                logger.debug(
                    f"SELL EXECUTED, Price: {order.executed.price:.2f}, "
                    f"Cost: {order.executed.value:.2f}"
                )
                level = self._find_order_level(order, self.sell_orders)
                if level is not None:
                    # 卖单成交，放置对应下方一个 step 的买单 (level - 1)
                    buy_price = order.executed.price - self.grid_step
                    new_order = self.buy(exectype=bt.Order.Limit, price=buy_price, size=self.params.position_size)
                    self.buy_orders[level - 1] = new_order
                    del self.sell_orders[level]
                    logger.debug(f"Grid level {level} SELL filled -> Placed BUY at level {level - 1}, price: {buy_price:.2f}")

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            logger.warning(f"Order failed: {order.status} (Margin/Canceled/Rejected)")
            self._remove_failed_order(order)

    def _find_order_level(self, target_order: bt.Order, order_dict: dict[int, bt.Order]) -> int | None:
        """查找订单所属的级别。"""
        for level, order in list(order_dict.items()):
            if order and getattr(order, 'ref', None) == getattr(target_order, 'ref', None):
                return level
        return None

    def _remove_failed_order(self, target_order: bt.Order) -> None:
        """移除失败的订单记录。"""
        level = self._find_order_level(target_order, self.buy_orders)
        if level is not None:
            del self.buy_orders[level]
            return
            
        level = self._find_order_level(target_order, self.sell_orders)
        if level is not None:
            del self.sell_orders[level]
