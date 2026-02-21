# Progress Log

此文档仅保留最新进度摘要及当前目标。历史记录已按天归档至 `memory-bank/progress_archive/` 目录中。

## 当前目标
- 第 35 步已验收通过。
- 第 36 步已验收通过（含 `datetime` 时间戳兼容修复与回归测试补齐）。
- 第 37 步已验收通过（CLI 命令集合）。
- 第 38 步未开始（等待启动）。

## 未解决问题清单
- 暂无阻塞问题（可按计划启动第 38 步）。

## 历史归档
- [2026-02-15](progress_archive/2026-02-15.md)
- [2026-02-16](progress_archive/2026-02-16.md)
- [2026-02-17](progress_archive/2026-02-17.md)
- [2026-02-18](progress_archive/2026-02-18.md)
- [2026-02-19](progress_archive/2026-02-19.md)
- [2026-02-20](progress_archive/2026-02-20.md)

## 最近的关键变更

## 2026-02-21（第 37 步）

### 本次目标
- 执行 `implementation-plan.md` Phase 4 第 37 条：实现 CLI 命令集合（启动、停止、状态、余额、订单、回测、下载、实时模拟、positions、import、export、cleanup、reconcile、status --disk）。

### 已完成事项
- 新增 CLI 主入口与命令分发：
  - `src/cli.py`：统一参数解析与子命令路由；
  - `main.py`：程序入口调用 CLI。
- 新增 CLI 运行上下文与共享工具：
  - `src/cli_context.py`：配置加载、数据库与核心服务装配、参数解析、时间范围解析、运行状态文件读写。
- 新增系统/订单类命令处理：
  - `src/cli_commands.py`：`start/startup`、`stop`、`status`（含 `--disk`）、`balance`、`positions`、`cleanup`、`reconcile`；
  - `src/cli_order_commands.py`：`order place/list/cancel`，支持 `market/limit/stop_loss/take_profit` 下单路径。
- 新增回测/数据/实时类命令处理：
  - `src/cli_workflows.py`：`backtest`、`download`、`live`、`import`、`export`。
- 参数校验与帮助信息覆盖：
  - 为必须参数配置 `argparse` 级别校验（缺参返回可解释错误）；
  - 对条件参数（如 `limit` 需 `--price`）增加命令级显式报错。
- 运行态约束延续：
  - 回测与实时读取路径维持 SQLite；
  - `download/import/export/cleanup/reconcile` 全部围绕 SQLite `candles` 与交易表执行。
- 新增 CLI 自动化测试：
  - `tests/test_cli_runtime.py`（系统、状态、订单、reconcile）；
  - `tests/test_cli_workflows.py`（backtest/download/live/import/export/cleanup）。

### 测试结果
- `PYTHONPATH=. ./.venv/bin/pytest -q tests/test_cli_runtime.py tests/test_cli_workflows.py` → `18 passed`。
- `PYTHONPATH=. ./.venv/bin/pytest -q` → `237 passed, 54 warnings`。

### 验收状态
- Phase 4 第 37 步代码实现已完成并通过用户验收（2026-02-21）。
- 已补充显式回归断言：`backtest --output-dir` 会同时导出 CSV/JSON 与 4 张 PNG 图表。
- 第 38 步未开始。

### 交接备注
- 当前 CLI 已覆盖实施计划第 37 步要求的命令集合与参数校验。
- 命令默认读取 `config/config.yaml`、`config/strategies.yaml`、`.env`，也支持通过 `--config/--strategies/--env` 覆盖路径。

## 2026-02-21（第 36 步）

### 本次目标
- 执行 `implementation-plan.md` Phase 4 第 36 条：实现可视化输出（资金曲线、回撤曲线、交易分布、持仓时间），并导出本地图片。

### 已完成事项
- 新增可视化模块 `src/analysis/visualization.py`：
  - 新增 `PerformanceVisualizer`，统一导出 4 张图像文件（`equity_curve`、`drawdown_curve`、`trade_distribution`、`holding_time`）。
  - 新增 `VisualizationArtifacts` 返回结构，统一返回导出文件路径。
  - 新增 `VisualizationError`，对输入校验和导出失败提供清晰错误语义。
- `equity_curve` 输入兼容回测与实时场景的通用结构：
  - 支持 `Mapping[timestamp, equity]`；
  - 支持 `Sequence[(timestamp, equity)]`。
- `trade_log` 输入兼容 `dict` 与对象两类结构，支持多种字段来源：
  - 盈亏分布：优先 `pnl_net`，回退 `pnl_gross`；
  - 持仓时长：支持 `holding_seconds` / `holding_minutes` / `holding_hours`；
  - 若未提供持仓时长字段，则通过 `entry_time/exit_time` 自动推导。
- 图表后端采用 `matplotlib` 的 `Agg`，确保无头环境（CI/本地终端）可稳定导出图片。
- 更新 `src/analysis/__init__.py` 导出入口，暴露 `PerformanceVisualizer`、`VisualizationArtifacts`、`VisualizationError`。
- 新增测试 `tests/test_visualization.py`，覆盖：
  - 4 张图像成功导出且文件非空；
  - 空交易明细场景仍可生成分布图；
  - 回撤序列计算正确性；
  - 非法资金曲线输入报错；
  - `datetime` 类型时间戳输入的回归场景（资金曲线与持仓时间推导）。
- 更新 `tests/test_performance_analysis.py`：
  - 新增 `datetime` 类型 `returns_series` 时间戳回归测试，确认收益分析路径在显式 `period_seconds` 下可稳定计算。

### 测试结果
- `PYTHONPATH=. ./.venv/bin/pytest -q tests/test_visualization.py tests/test_performance_analysis.py` → `12 passed`。
- `PYTHONPATH=. ./.venv/bin/pytest -q` → `219 passed, 54 warnings`。

### 验收状态
- Phase 4 第 36 步代码已完成并通过验收，并在审查中**发现并修复了一个时间戳解析的隐式类型错误**。
- `src/analysis/visualization.py` 和 `src/analysis/performance.py` 的 `_parse_timestamp` 均已补充对 Python 原生 `datetime` 对象的解析支持，解决在传入 `datetime` key 时触发崩溃的边界情况。
- 已补齐两条正式 pytest 回归用例，覆盖可视化与性能分析两条路径的 `datetime` 输入。
- 当前分支全量测试 219 passed。第 36 步验收完成。

### 交接备注
- 第 36 步仅新增可视化导出能力，不改变第 35 步性能指标计算口径。
- 已修复 `_parse_timestamp` 的通用支持性问题，保证实际交易对象和曲线结构在分析导出环境下的健壮性。
- 当前分支状态已经验证无误；以上为第 36 步收尾时记录（当前实际状态见文档顶部：已进入第 37 步，且第 38 步未开始）。

## 2026-02-21（第 35 步）

### 本次目标
- 执行 `implementation-plan.md` Phase 3 第 35 条：实现“基于资金曲线与交易明细的通用性能分析工具”，同时支持回测与实时场景。

### 已完成事项
- 新增通用性能分析入口 `src/analysis/performance.py`，统一支持两种输入模式：
  - 直接传入 `equity_curve`；
  - 传入 `returns_series` 并显式指定 `period_seconds` 后反推资金曲线。
- 修复 `returns_series` 反推路径的关键口径问题：
  - 移除“全局平均间隔回推 T0”逻辑；
  - 移除“单点收益默认回退 1 天”逻辑；
  - 改为 `t0 = first_timestamp - period_seconds`，并用 `initial_capital` 补齐首个基准点。
- 新增周期一致性校验：`returns_series` 的相邻时间戳间隔必须与 `period_seconds` 一致，不一致直接抛出参数错误，避免年化与 Sharpe 口径失真。
- 年化相关计算统一使用显式周期参数：
  - 年化时长基于 `period_seconds * (len(series) - 1)`；
  - 年化因子基于 `year_seconds / period_seconds`。
- 按 CLAUDE 的单文件约束完成模块拆分：
  - `src/analysis/performance_trade.py`：交易统计构建；
  - `src/analysis/performance_errors.py`：性能分析异常定义；
  - `src/analysis/performance.py`：分析编排与核心计算（当前 297 行）。
- 补充/更新自动化测试 `tests/test_performance_analysis.py`：
  - 覆盖 `returns_series` 反推路径的 `annualized_return` 与 `sharpe_ratio`；
  - 覆盖缺失 `period_seconds` 的报错；
  - 覆盖时间戳间隔与 `period_seconds` 不一致的报错。

### 测试结果
- `PYTHONPATH=. ./.venv/bin/pytest -q tests/test_performance_analysis.py` → `6 passed`。
- `PYTHONPATH=. ./.venv/bin/pytest -q` → `213 passed, 54 warnings`。

### 验收状态
- Phase 3 第 35 步代码实现已完成，自动化测试通过。
- 用户验收已通过（2026-02-21）。
- 第 36 步尚未开始（当时状态；当前状态见文档顶部）。

### 交接备注
- 第 35 步核心约束已切换为“显式周期元数据驱动”：`returns_series` 路径必须提供 `period_seconds`。
- 当前未启动第 36 步（当时状态；当前状态见文档顶部）。

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

### 本次目标
- 执行 `implementation-plan.md` Phase 3 第 33 条：实现内置策略：布林带，支持参数化与双模式。验收：波动数据上按阈值触发交易。

### 已完成事项
- 完整阅读并复核 `memory-bank/` 全部文档后开始第 33 步实现。
- 实现布林带策略 `src/strategies/bollinger_strategy.py`：
  - 新增 `BollingerStrategy(bt.Strategy)` 类。
  - 逻辑：价格下穿下轨并回升买入；价格上穿上轨并回落平仓；价格回到中轨平仓。
  - 参数：`period`(20), `dev`(2.0), `position_size`(0.2)。
- 导出至 `src/strategies/__init__.py`。
- 新增测试 `tests/test_bollinger_strategy.py`：
  - `test_bollinger_strategy_triggers_trades_on_volatility`：回测模式下单笔交易验证。
  - `test_bollinger_strategy_parameter_configuration`：参数生效验证。
  - `test_bollinger_strategy_no_trade_without_rebound`：无回升不交易验证。
  - `test_bollinger_strategy_works_in_realtime_mode_via_adapter`：实时模式信号触发验证。
- 测试结果：`4 passed`。

### 验收状态
- Phase 3 第 33 步代码实现已完成，单元测试通过。
- 已于 2026-02-20 验证通过，进入第 34 步。

## 2026-02-20（第 34 步）

### 本次目标
- 执行 `implementation-plan.md` Phase 3 第 34 条：实现策略参数管理，从配置加载并传递到策略实例。

### 已完成事项
- 新增策略注册表与参数解析器：
  - `src/strategies/registry.py`：统一策略名 → 类映射与允许参数集合。
  - `src/strategies/param_resolver.py`：合并配置参数 + 显式参数，显式参数优先；禁用策略与未知参数直接拒绝。
- 回测引擎接入参数解析器：
  - `BacktestEngine` 新增 `strategies_config` 与 `strategy_registry` 注入；运行前合并策略参数并传入 `cerebro.addstrategy()`。
- 实时策略工厂与上下文参数传递：
  - `src/strategies/factory.py` 新增 `create_live_strategy()`，从配置生成 `BacktraderAdapter` 并返回合并参数。
  - `RealtimeSimulationLoop` 新增 `strategy_params` 注入并传入 `StrategyContext.parameters`。
- 新增测试：
  - `tests/test_strategy_param_resolver.py`
  - `tests/test_strategy_factory.py`
  - `tests/test_backtest_engine.py::test_backtest_engine_applies_config_params`
  - `tests/test_realtime_loop.py::test_loop_passes_strategy_params_to_context`
- 用户校验修复：
  - `StrategyParamResolver` 统一校验配置与显式参数的未知参数，避免配置层漏检。
  - `RealtimeSimulationLoop.from_config()` 补充 `strategy_params` 透传，保证上下文参数不丢失。

### 测试结果
- `PYTHONPATH=/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config /Users/pingu/Documents/Quantitative-Trading-SIM/.venv/bin/pytest -q /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/tests/test_strategy_param_resolver.py` → `3 passed`
- `PYTHONPATH=/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config /Users/pingu/Documents/Quantitative-Trading-SIM/.venv/bin/pytest -q /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/tests/test_backtest_engine.py::test_backtest_engine_applies_config_params` → `1 passed`
- `PYTHONPATH=/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config /Users/pingu/Documents/Quantitative-Trading-SIM/.venv/bin/pytest -q /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/tests/test_strategy_factory.py` → `1 passed`
- `PYTHONPATH=/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config /Users/pingu/Documents/Quantitative-Trading-SIM/.venv/bin/pytest -q /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/tests/test_realtime_loop.py::test_loop_passes_strategy_params_to_context` → `1 passed`
- 全量测试：`PYTHONPATH=/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config /Users/pingu/Documents/Quantitative-Trading-SIM/.venv/bin/pytest -q /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/tests` → `204 passed, 54 warnings`

### 验收状态
- Phase 3 第 34 步代码实现已完成，自动化测试通过。
- 用户已验证通过（2026-02-20）。
- 第 35 步当时尚未开始（历史记录；当前状态见文档顶部）。
