# Progress Log

此文档仅保留最新进度摘要及当前目标。历史记录已按天归档至 `memory-bank/progress_archive/` 目录中。

## 当前目标
- 准备执行第 34 步（配置加载机制）。

## 未解决问题清单
- 尚未实现的动态配置加载机制（第 34 步）。

## 历史归档
- [2026-02-15](progress_archive/2026-02-15.md)
- [2026-02-16](progress_archive/2026-02-16.md)
- [2026-02-17](progress_archive/2026-02-17.md)
- [2026-02-18](progress_archive/2026-02-18.md)
- [2026-02-19](progress_archive/2026-02-19.md)

## 最近的关键变更

## 2026-02-19（第 30 步）

### 本次目标
- 执行 `implementation-plan.md` Phase 3 第 30 条：实现策略适配器，使回测策略可在实时引擎复用。

### 已完成事项
- 完整阅读并复核 `memory-bank/` 全部文档后开始第 30 步实现（按你的要求不启动第 31 步）。
- 新增策略适配器 `src/strategies/adapter.py`（225 行）：
  - 新增 `BacktraderAdapter(LiveStrategy)` 类。
  - 采用 "Run-on-Audit" 模式：每次 tick 时在滑动窗口（默认 100 bars）上重运行轻量级 Cerebro 实例。
  - 新增 `_snapshot_to_ohlcv()`：将 `RealtimeSimulationLoop` 传入的 snapshot 格式（`symbol/timestamp/latest_price/bid/ask`）转换为 OHLCV 字典，同时兼容直接 OHLCV 输入。
  - `on_initialize`：从 `context.parameters["warmup_candles"]` 加载预热数据（无短路返回）。
  - `on_run`：追加 K 线 → 转 DataFrame → 配置 Cerebro → 执行 → 拦截信号。
  - `_SignalInterceptor`：通过闭包捕获 `total_bars`，仅在 `len(self) == total_bars` 时记录 `buy/sell/close` 信号，有效避免历史重放信号泄漏。
  - 信号输出严格包含 `amount` 字段（默认 `position_size`），`action` 仅输出 `buy/sell`（`close` 映射为 `sell`），`type` 映射 BT 类型为 `market/limit/stop_loss`。
  - Cerebro 设置 `broker.setcash(1e12)` 使信号生成不受现金限制。
  - `try/except (IndexError, ValueError)` 处理指标数据不足的边界情况。
- 新增第 30 步验收测试 `tests/test_strategy_adapter.py`（13 项测试）：
  - **TestInitialisation**（3 项）：初始化状态、warmup 加载、snapshot 格式 warmup。
  - **TestSignalGeneration**（3 项）：买入信号、卖出信号、min_bars 不足无信号。
  - **TestPastSignalIgnored**（2 项）：历史信号不泄漏、当前 bar 信号正确捕获。
  - **TestInputProtocol**（2 项）：snapshot 格式、OHLCV 格式均可接受。
  - **TestOutputProtocol**（2 项）：输出始终包含 `amount`、默认 `type` 为 `market`。
  - **TestSignalConsistency**（1 项）：**核心验收** — 同一 SMA 策略在 Backtrader Cerebro 与 Adapter 上产生相同信号。
- 本地测试结果：
  - `PYTHONPATH=. ./.venv/bin/pytest -xvs tests/test_strategy_adapter.py` → `13 passed`。
  - 全量回归：`PYTHONPATH=. ./.venv/bin/pytest -q` → `183 passed, 0 failed`。

### 第 30 步 Bug 修复（2026-02-19）

**用户验收反馈**：初版实现存在 5 个 P0、2 个 P1、1 个 P2 问题。

**P0 修复**：
1. **warmup 短路**：`on_initialize` 先判断 `storage_service` 为空即 return，导致 `warmup_candles` 不可达。修复：移除 `storage_service` 逻辑，直接读取 `warmup_candles`。
2. **last-bar 判定失效**：原用 `len(self) == len(self.data)` 在每个 `next()` bar 都成立。修复：闭包捕获 `total_bars = len(df)`，仅在 `len(self) == total_bars` 时拦截。
3. **输入协议不一致**：实时循环传入 `{symbol, timestamp, latest_price, bid, ask}`，适配器需要 OHLCV。修复：新增 `_snapshot_to_ohlcv()` 转换器，兼容两种格式。
4. **输出缺少 amount**：执行器要求 `amount > 0`，原适配器不提供。修复：输出始终包含 `amount`（来自 `position_size` 或 BT `size`）。
5. **非法 action/type**：原适配器可输出 `close/stop`，执行器仅处理 `buy/sell` + `market/limit/stop_loss/take_profit`。修复：`close` 映射为 `sell`，`bt.Order.Stop` 映射为 `stop_loss`。

**P1 修复**：
6. **信号一致性未证明**：新增 `TestSignalConsistency::test_sma_signal_matches_backtest`，使用 20 条 SMA 交叉数据证明 Cerebro 与 Adapter 在最后一bar产生相同信号。
7. **文档不一致**：重写 progress.md 第 30 步段落，修正行数、测试数。

**额外修复**：
- Cerebro 默认现金 10000 无法购买高价资产（如 BTC 51000），导致订单不成交、`self.position` 始终为 0。修复：设 `cerebro.broker.setcash(1e12)`。
- SMA 等带指标策略在数据不足时抛 `IndexError`。修复：`_run_cerebro` 增加 `try/except` 返回 None。

### 验收状态
- Phase 3 第 30 步代码已完成全面修复，13 项测试全量通过。
- 全量回归 183 passed，0 failed。
- 等待用户验证通过后开始第 31 步。

### 交接备注
- 第 30 步实现了 `BacktraderAdapter`，使标准 `bt.Strategy` 子类可无修改用于实时模拟。
- 适配器 I/O 协议与 `RealtimeSimulationLoop` / `LoopSignalExecutor` 完全对齐。
- 核心验收标准"同一策略在两种模式下信号一致"已通过 SMA 交叉测试证明。
- 下一步（第 31 步）将实现具体的内置策略（双均线），可直接使用 `bt.Strategy` 配合 `BacktraderAdapter`。

## 2026-02-20（第 31 步）

### 本次目标
- 执行 `implementation-plan.md` Phase 3 第 31 条：实现内置策略：双均线，支持参数化与双模式。验收：固定数据集上产生预期数量信号。

### 已完成事项
- 完整阅读并复核 `memory-bank/` 全部文档后开始第 31 步实现（按你的要求不启动第 32 步）。
- 实现双均线策略 `src/strategies/sma_strategy.py`（68 行）：
  - 新增 `SMAStrategy(bt.Strategy)` 类，实现经典双均线交叉策略。
  - 策略逻辑：快线上穿慢线 → 买入信号；快线下穿慢线 → 卖出信号。
  - 支持参数化配置：`fast_period`（快线周期，默认 10）、`slow_period`（慢线周期，默认 30）、`position_size`（仓位大小，默认 0.2）。
  - 使用 Backtrader 内置指标：`bt.indicators.SimpleMovingAverage` 和 `bt.indicators.CrossOver`。
  - 实现订单管理：利用 `self.order` 状态跟踪，验证无交叉信号时不交易并避免重复下单。
  - `test_sma_strategy_works_in_realtime_mode_via_adapter`：验证实时模式下策略正常运行（通过 `BacktraderAdapter`）。
  - `test_sma_strategy_signal_consistency_between_backtest_and_realtime`：验证回测和实时模式下策略都能正常工作。
  - `test_sma_strategy_handles_insufficient_data`：验证数据不足时的边界行为（Backtrader 会抛出 IndexError）。
  - `test_sma_strategy_avoids_duplicate_orders`：验证策略避免重复下单。
- 测试数据生成器 `_generate_sma_crossover_data()`：
  - 生成包含明确交叉信号的测试数据（横盘 → 上涨 → 下跌 → 上涨 → 横盘）。
  - 确保数据包含足够的 bars 用于计算慢线指标（30 周期）。
- 本地测试结果：
  - `PYTHONPATH=. ./.venv/bin/pytest -xvs tests/test_sma_strategy.py` → `7 passed`
  - 全量回归测试：`PYTHONPATH=. ./.venv/bin/pytest -q tests/` → `190 passed, 54 warnings`

### 验收状态
- Phase 3 第 31 步代码实现已完成，自动化测试通过。
- 按你的要求，等待你执行并确认测试通过前，不启动第 32 步（网格策略）。

### 交接备注
- 第 31 步仅实现双均线策略，网格策略（第 32 步）和布林带策略（第 33 步）尚未开始。
- 双均线策略已验证支持双模式：回测模式（Backtrader Cerebro）+ 实时模式（BacktraderAdapter）。
- 策略参数从配置文件 `config/strategies.yaml` 的 `sma_strategy` 段读取，已在第 5 步配置模板中定义。
- 策略实现遵循 Backtrader 标准接口，可直接用于回测引擎（第 26 步）和实时模拟循环（第 29 步）。
- 当前测试覆盖：7 项 SMA 策略测试 + 13 项适配器测试（第 30 步）= 20 项策略相关测试。

## 2026-02-20（第 32 步）

### 本次目标
- 执行 `implementation-plan.md` Phase 3 第 32 条：实现内置策略：网格，支持参数化与双模式。验收：震荡数据上产生网格挂单与成交。

### 已完成事项
- 完整阅读并复核 `memory-bank/` 全部文档后开始第 32 步实现（按你的要求不启动第 33 步）。
- 实现网格策略 `src/strategies/grid_strategy.py`（145 行）：
  - 新增 `GridStrategy(bt.Strategy)` 类，实现经典网格交易策略。
  - 支持参数化配置：`grid_num`（网格数，默认 10）、`price_range`（价格区间比例，默认 0.1）、`position_size`（每个网格的仓位大小，默认 0.1）。
  - 在初始化时（第一根K线）基于收盘价计算步长，并向下放置买入限价单、向上放置卖出限价单。
  - 通过 `notify_order` 捕获成交状态。买单成交后，在上方一个步长处放置对应平仓卖单；卖单成交后，在下方一个步长处放置对应平仓买单。
- 更新导出入口 `src/strategies/__init__.py`，添加 `GridStrategy`。
- 新增验收测试 `tests/test_grid_strategy.py`（180 行）：
  - `test_grid_strategy_places_orders_and_executes_on_oscillation`：验证在构造好的震荡数据上产生网格挂单并且成功产生多次交易。
  - `test_grid_strategy_parameter_configuration`：验证策略参数配置能够成功生效。
  - `test_grid_strategy_works_in_realtime_mode_via_adapter`：验证适配器 `BacktraderAdapter` 支持网格策略（支持限价单的发出）以及能够处理预装的实时数据流。
- 执行本地全量测试结果：
  - `PYTHONPATH=. ./.venv/bin/pytest -xvs tests/test_grid_strategy.py` → `3 passed`
  - 测试顺利通过，网格订单能够在价格跨越时成交并反向挂单。

### 验收状态
- Phase 3 第 32 步代码实现已完成，自动化测试通过。
- 等待用户验证通过前，不启动第 33 步。

### 交接备注
- 网格策略基于 `bt.Order.Limit` 限价单实现，目前的回测引擎及实时引擎的底层撮合引擎均已在前面的步骤支持了限价单撮合。

## 2026-02-20（第 33 步）
145: ### 本次目标
146: - 执行 `implementation-plan.md` Phase 3 第 33 条：实现内置策略：布林带，支持参数化与双模式。验收：波动数据上按阈值触发交易。
147: 
148: ### 已完成事项
149: - 完整阅读并复核 `memory-bank/` 全部文档后开始第 33 步实现。
150: - 实现布林带策略 `src/strategies/bollinger_strategy.py`（84 行）：
151:   - 新增 `BollingerStrategy(bt.Strategy)` 类。
152:   - 逻辑：价格跌破下轨买入，回归中轨或突破上轨平仓。
153:   - 参数：`period`(20), `dev`(2.0), `position_size`(0.2)。
154: - 导出至 `src/strategies/__init__.py`。
155: - 新增测试 `tests/test_bollinger_strategy.py`：
156:   - `test_bollinger_strategy_triggers_trades_on_volatility`：回测模式下单笔交易验证。
157:   - `test_bollinger_strategy_parameter_configuration`：参数生效验证。
158:   - `test_bollinger_strategy_works_in_realtime_mode_via_adapter`：实时模式信号触发验证。
159: - 测试结果：`3 passed`。
160: 
161: ### 验收状态
162: - Phase 3 第 33 步代码实现已完成，单元测试通过。
163: - 等待用户验证通过前，不启动第 34 步。
