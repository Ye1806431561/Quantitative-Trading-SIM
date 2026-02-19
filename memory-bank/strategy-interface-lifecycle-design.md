# 策略接口生命周期设计（Step 25）

## 目标
- 定义统一策略生命周期接口：初始化、运行、停止、订单回调、成交回调。
- 提供最小可运行示例，验证生命周期可按预期触发。
- 保持与第 26 步边界隔离：本步不集成 Backtrader 引擎。

## 代码落地点
- `src/strategies/base.py`
  - `LiveStrategy`：生命周期基类与状态守卫。
  - `StrategyContext`：策略初始化上下文。
  - `StrategyOrderEvent` / `StrategyTradeEvent`：订单与成交回调载荷。
  - `StrategyLifecycleError`：生命周期违规错误。
- `src/live/simulator.py`
  - `StrategyLifecycleDriver`：轻量驱动器，用于触发生命周期回调。
- `src/strategies/lifecycle_demo_strategy.py`
  - `LifecycleProbeStrategy`：最小示例策略，仅记录生命周期事件。
- `tests/test_strategies.py`
  - 生命周期触发与状态守卫验收测试。

## 生命周期契约

### 状态机
- 初始状态：`pending`
- 初始化后：`running`
- 停止后：`stopped`

### 回调顺序（典型）
1. `initialize(context)` -> `on_initialize(context)`
2. `run(market_data)` -> `on_run(market_data)`
3. `notify_order(order_event)` -> `on_order(order_event)`
4. `notify_trade(trade_event)` -> `on_trade(trade_event)`
5. `stop(reason)` -> `on_stop(reason)`

### 守卫规则
- 未初始化前调用 `run/notify_order/notify_trade`：抛 `StrategyLifecycleError`。
- 已初始化后重复 `initialize`：抛 `StrategyLifecycleError`。
- `pending` 状态下直接 `stop`：抛 `StrategyLifecycleError`。
- `stopped` 状态重复 `stop`：幂等忽略。
- `StrategyLifecycleDriver` 未 `start()` 时调用 `on_market_data/on_order_update/on_trade_update/stop`：
  - 由 Driver 层直接抛 `StrategyLifecycleError`，并提示先调用 `driver.start()`。

## 最小示例策略
- 类：`LifecycleProbeStrategy`
- 行为：
  - 每个生命周期钩子把事件写入 `events` 列表。
  - `on_run` 返回固定信号 `{"action": "hold"}`，用于验证执行回路已触发。

## 验收映射（Step 25）
- 验收要求：最小示例策略按生命周期触发。
- 验收实现：
  - `tests/test_strategies.py::test_strategy_lifecycle_callbacks_fire_in_expected_order`
  - 断言初始化、运行、订单回调、成交回调、停止回调按顺序触发。
  - 断言最终状态为 `StrategyRunStatus.STOPPED`。

## 边界说明
- 本步未实现：
  - Backtrader 引擎接入（第 26 步）。
  - 回测数据馈送与分析器挂载（第 26-27 步）。
  - 实时主循环（第 29 步）。
