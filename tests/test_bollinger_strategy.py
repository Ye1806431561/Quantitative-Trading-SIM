"""测试布林带策略（Bollinger Bands Strategy）- Step 33 验收。

验收标准：波动数据上按阈值触发交易。
"""

from __future__ import annotations

import backtrader as bt
import pandas as pd
import pytest
import numpy as np

from src.strategies.bollinger_strategy import BollingerStrategy
from src.strategies.adapter import BacktraderAdapter
from src.strategies.base import StrategyContext


def _generate_volatile_data(num_bars: int = 100) -> pd.DataFrame:
    """生成具有均值回归特征的波动数据。
    
    100条数据。
    前30条：基准价 100 附近小幅震荡，用于初始化布林带指标。
    第31-40条：跌破下轨（跌到 90）。
    第41-50条：回升至中轨（100）。
    第51-60条：突破上轨（升到 110）。
    第61-70条：回落至中轨（100）。
    """
    timestamps = pd.date_range(start="2024-01-01", periods=num_bars, freq="1h")
    prices = []
    
    for i in range(num_bars):
        if i < 30:
            price = 100.0 + (i % 3 - 1) * 0.5 # 99.5, 100, 100.5
        elif i < 40:
            price = 90.0 # 暴跌触发买入
        elif i < 50:
            price = 100.0 # 回升到中轨触发平仓
        elif i < 60:
            price = 110.0 # 暴涨触发卖出平仓（虽然没持空头）
        elif i < 70:
            price = 100.0 # 回落
        else:
            price = 100.0
        prices.append(price)

    df = pd.DataFrame({
        "datetime": timestamps,
        "open": prices,
        "high": [p * 1.01 for p in prices],
        "low": [p * 0.99 for p in prices],
        "close": prices,
        "volume": [1000.0] * num_bars,
    })
    df.set_index("datetime", inplace=True)
    return df


def test_bollinger_strategy_triggers_trades_on_volatility():
    """验收核心：在波动数据上按阈值触发交易（回测模式）。"""
    df = _generate_volatile_data(num_bars=100)

    cerebro = bt.Cerebro()
    cerebro.broker.setcash(100_000.0)
    cerebro.broker.setcommission(commission=0.001)

    # period=20, std_dev=2.0
    cerebro.addstrategy(BollingerStrategy, period=20, std_dev=2.0, position_size=0.2)

    data_feed = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data_feed)

    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
    strategies = cerebro.run()
    strategy = strategies[0]
    
    trades = strategy.analyzers.trades.get_analysis()
    total_trades = trades.get("total", {}).get("total", 0)
    
    # 期望：在第31条左右买入，第41条左右平仓。
    assert total_trades >= 1, "布林带策略应在跌破下轨并回归时产生至少一笔完整交易"


def test_bollinger_strategy_parameter_configuration():
    """验证参数可配置。"""
    df = _generate_volatile_data(num_bars=30)

    cerebro = bt.Cerebro()
    cerebro.addstrategy(BollingerStrategy, period=10, std_dev=1.5, position_size=0.5)

    data_feed = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data_feed)
    cerebro.broker.setcash(100_000.0)

    strategies = cerebro.run()
    strategy = strategies[0]

    assert strategy.params.period == 10
    assert strategy.params.std_dev == 1.5
    assert strategy.params.position_size == 0.5


def test_bollinger_strategy_works_in_realtime_mode_via_adapter():
    """双模式支持 - 实时模式验证。"""
    df_full = _generate_volatile_data(num_bars=50)
    
    # 使用前 20 bars 作为预热
    df_warmup = df_full.iloc[:20]
    warmup_ohlcv = []
    for dt, row in df_warmup.iterrows():
        warmup_ohlcv.append({
            "timestamp": int(dt.timestamp() * 1000),
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "volume": row["volume"],
        })

    context = StrategyContext(
        strategy_id="bb-realtime-001",
        symbol="BTC/USDT",
        timeframe="1h",
        parameters={
            "period": 20,
            "std_dev": 2.0,
            "position_size": 0.2,
            "warmup_candles": warmup_ohlcv,
        },
    )

    adapter = BacktraderAdapter(
        name="bb-realtime-adapter",
        bt_strategy_cls=BollingerStrategy,
        bt_params={
            "period": 20,
            "std_dev": 2.0,
            "position_size": 0.2,
        },
        lookback_window=100,
        min_bars=20,
    )

    adapter.initialize(context)
    
    # 推送后续数据，触发信号
    has_signals = False
    for i in range(20, 50):
        dt = df_full.index[i]
        row = df_full.iloc[i]
        market_data = {
            "timestamp": int(dt.timestamp() * 1000),
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "volume": row["volume"],
        }
        signal = adapter.run(market_data)
        if signal:
            has_signals = True
            
    assert has_signals, "实时模式下，价格波动应能触发策略信号"
