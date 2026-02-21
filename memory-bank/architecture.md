# Architecture Notes

## 当前阶段定位（2026-02-21）

- 仓库已完成 `implementation-plan.md` Phase 0 第 1-7 条，Phase 1 第 8-16 条，Phase 2 第 17-24 条，Phase 3 第 25-35 条，Phase 4 第 36-37 条代码落地（第 35-37 步均已通过用户验收）。
- 当前处于“第 37 步已验收通过、第 38 步未开始”阶段。
- 第 38 步尚未启动。
- 最小交付范围仍锁定为 CLI + 模拟盘（回测与实时模拟），Web 能力保留为可选项且暂不交付。
- **第 29 步实现与验证**：`src/live/realtime_loop.py` 实现完整的实时模拟主循环（行情拉取→策略执行→下单→撮合→持仓更新），全量测试 8 passed。实时模式的数据读取路径符合约束：先将最新行情落 SQLite，策略可从 SQLite 读取历史数据；CSV/Parquet 不参与运行态读写。

## 文件作用说明（`memory-bank/`）

### `memory-bank/CLAUDE.md`
- 作用：全局工程约束与硬性实现规则（模块拆分、数据库结构、数据流、日志与质量检查）。
- 依赖关系：约束 `implementation-plan.md` 和后续所有实现文件的技术边界。

### `memory-bank/product-requirement-document.md`
- 作用：需求源文档，定义功能需求、非功能需求、范围、里程碑与场景。
- 依赖关系：`requirements-traceability-checklist.md` 的唯一需求输入。

### `memory-bank/implementation-plan.md`
- 作用：将 PRD 拆解为可执行阶段步骤与验收标准。
- 依赖关系：驱动 `progress.md` 的执行记录与 `requirements-traceability-checklist.md` 的阶段状态更新。

### `memory-bank/tech-stack.md`
- 作用：技术选型与目录约束基线（Python 版本、依赖、结构模板）。
- 依赖关系：约束后续目录搭建、依赖锁定与配置模板设计。

### `memory-bank/requirements-traceability-checklist.md`
- 作用：需求映射与范围控制中枢；记录需求 ID、模块归属、交付物、范围、排除理由与验收状态。
- 依赖关系：向 `progress.md` 提供阶段验收依据；向实现阶段提供优先级和范围边界。

### `memory-bank/progress.md`
- 作用：当前里程碑执行摘要，记录“最近的关键变更、当前目标与未解决问题”。历史日志按天拆分归档至 `progress_archive/` 目录。
- 依赖关系：引用 `implementation-plan.md` 的步骤状态，并回链到追踪清单。

### `memory-bank/progress_archive/`
- 作用：历史进度归档目录，按天（如 `2026-02-15.md`、`2026-02-16.md`）详细记录每天完成的开发与执行日志。
- 依赖关系：承接从 `progress.md` 中迁移出的已完成任务流水，保持主进度追踪文档简明。

### `memory-bank/findings.md`
- 作用：知识沉淀与决策档案，按固定模板记录需求、发现、决策、问题、资源。
- 依赖关系：吸收来自 PRD、实施计划、追踪清单、进度日志的关键信息，供后续开发者快速接手。

### `memory-bank/architecture.md`
- 作用：架构认知与文档关系说明，解释当前系统边界和每份文档职责。
- 依赖关系：在每个关键里程碑后回写，确保架构认知与执行状态同步。

### `memory-bank/market-data-interface-design.md`
- 作用：第 14 步接口设计文档，记录交易所选择、限流、重试、失败告知与数据路径约束。
- 依赖关系：为 `src/data/market*.py` 的实现与 `tests/test_market_data.py` 的验收场景提供设计基线。

### `memory-bank/strategy-interface-lifecycle-design.md`
- 作用：第 25 步接口设计文档，记录策略生命周期契约、状态守卫、最小示例与验收映射。
- 依赖关系：为 `src/strategies/base.py`、`src/live/simulator.py` 与 `tests/test_strategies.py` 提供设计基线。

## 文档关系与执行链路
1. `product-requirement-document.md` 定义“要做什么”。
2. `implementation-plan.md` 定义“按什么顺序做、如何验收”。
3. `requirements-traceability-checklist.md` 定义“每条需求落到哪里、当前是否在范围内”。
4. `progress.md` 记录“当前做到哪一步、是否通过验收”。
5. `findings.md` 记录“为什么这样做、遇到什么问题、依据是什么”。
6. `architecture.md` 解释“上述文档如何共同构成当前架构基线”。

## 工程骨架与基础实现文件作用（第 3-26 步）
- `src/core/*.py`：核心业务域实现入口（账户、订单、撮合、数据库、领域模型校验）；其中 `database.py` 已落地生命周期管理与 schema 初始化（六表、约束、索引，`orders`/`trades` 时间戳字段使用毫秒整数），`enums.py`/`validation.py`/`account.py`/`order.py`/`trade.py`/`position.py`/`candle.py`/`strategy_run.py` 已完成领域模型与校验规则（`validation.py` 已修复 `require_timestamp()` 兼容 SQLite `datetime` 对象），`account_service.py` 已实现账户初始化、余额管理、持仓恢复与总资产估值，`order_service.py` 已实现订单持久化接口（创建、查询、状态更新、撤销）与完整的资金管理（冻结/消耗/释放），`trade_service.py` 已实现成交写入与订单关联（含手续费、资金消耗与状态更新），`matching.py` 已实现第 19 步市价单撮合（最新价成交、账户与持仓同步），`limit_matching.py` + `limit_settlement.py` 已实现第 20 步限价队列管理与触发撮合，`stop_trigger.py` 已实现第 21 步止损/止盈触发机制与状态联动，`execution_cost.py` 已实现第 22 步统一手续费/滑点计算（Maker/Taker + 方向性滑点 + 限价边界保护），`order_state_machine.py` 已实现第 23 步统一订单状态机与合法流转表，`risk.py` 已实现第 24 步下单前风控拦截（单笔仓位、总仓位、最大回撤）。
- `src/data/market.py`：市场数据接口实现（交易所选择、限流、重试、失败告知），承接 Phase 1 第 14 条。
- `src/data/market_policy.py`：市场数据配置与策略约束（`RetryPolicy`、运行态写入目标校验）。
- `src/data/market_retry.py`：本地限流器与错误分类（限流类/可重试类/不可重试类）。
- `src/data/storage.py`：历史 K 线下载、缓存与去重存储实现（`HistoricalCandleStorage`），提供下载落库、缓存命中与按 `symbol/timeframe/time range` 查询能力（第 15-16 步）。
- `src/data/feed.py`：第 26 步 SQLite→Pandas 数据馈送桥接，实现回测数据切片查询与 `backtrader.feeds.PandasData` 适配。
- `src/data/realtime_market.py`：实时行情读取服务实现（最新价/深度/K 线），提供超时控制与错误兜底（第 17 步）。
- `src/data/realtime_payloads.py`：实时行情统一返回结构与载荷归一化工具，确保三类接口结构一致（第 17 步）。
- `src/strategies/base.py`：第 25 步策略生命周期接口实现（初始化/运行/停止/订单回调/成交回调）与状态守卫。
- `src/strategies/lifecycle_demo_strategy.py`：第 25 步最小示例策略，实现生命周期钩子触发记录。
- `src/strategies/registry.py`：第 34 步策略注册表，统一策略名 → 类映射与允许参数集合。
- `src/strategies/param_resolver.py`：第 34 步参数解析器，合并配置与显式参数并统一校验。
- `src/strategies/factory.py`：第 34 步实时策略工厂，基于配置生成 `BacktraderAdapter` 并返回合并参数。
- `src/strategies/*.py`（其余）：内置策略实现（第 30-33 步）。
- `src/backtest/engine.py`：第 26-27 步 Backtrader 回测引擎实现（`BacktestEngine`），负责 Cerebro 装配、策略执行、标准分析器挂载与统一结果输出（`BacktestRunResult` 包含基础统计 + 5 个分析器输出）。
- `src/backtest/analyzers.py`：第 27 步分析器挂载模块（`AnalyzerMount`），负责挂载 5 个标准分析器（Sharpe、DrawDown、TradeAnalyzer、Returns、TimeReturn）并提取结果。
- `src/backtest/result_models.py`：第 27 步回测结果数据模型（`BacktestRunResult`、`TradeStatistics`、`RiskMetrics`、`ReturnsAnalysis`），定义统一的回测输出结构。
- `src/backtest/result_builder.py`：第 27 步分析器结果转换器（`AnalyzerResultBuilder`），负责将 Backtrader 原始分析器输出转换为统一数据模型。
- `src/backtest/exporter.py`：第 28 步回测结果导出模块（`BacktestResultExporter`），提供摘要报告与资金曲线的 CSV/JSON 导出能力，支持自定义文件名前缀与自动创建输出目录。
- `src/analysis/performance.py`：第 35 步通用性能分析编排入口，统一支持 `equity_curve` 直接分析与 `returns_series + period_seconds` 反推分析。
- `src/analysis/performance_trade.py`：第 35 步交易统计构建模块，负责从成交明细计算次数、胜率、盈亏比等交易维度指标。
- `src/analysis/performance_errors.py`：第 35 步性能分析异常定义模块，统一参数错误与输入校验错误语义。
- `src/analysis/visualization.py`：第 36 步可视化导出模块，提供资金曲线、回撤曲线、交易盈亏分布、持仓时间分布四类图像导出能力。
- `src/cli.py`：第 37 步 CLI 主入口与参数解析器，实现子命令路由与统一错误返回码。
- `src/cli_context.py`：第 37 步 CLI 运行上下文装配，负责配置加载、数据库/服务构建与运行状态文件读写。
- `src/cli_commands.py`：第 37 步系统类命令处理器（`start/stop/status/balance/positions/cleanup/reconcile`）。
- `src/cli_order_commands.py`：第 37 步订单类命令处理器（`order place/list/cancel`）。
- `src/cli_workflows.py`：第 37 步工作流命令处理器（`backtest/download/live/import/export`）。
- `tests/test_performance_analysis.py`：第 35 步性能分析测试，覆盖收益/风险指标、周期参数校验、间隔一致性校验。
- `tests/test_visualization.py`：第 36 步可视化测试，覆盖图片导出、空交易场景、回撤计算与输入校验异常。
- `tests/test_cli_runtime.py`：第 37 步 CLI 运行态测试，覆盖系统状态、订单命令、reconcile 与参数缺失错误返回。
- `tests/test_cli_workflows.py`：第 37 步 CLI 工作流测试，覆盖回测/下载/实时模拟/导入导出/清理及缺参错误返回。
- `src/live/loop_models.py`：实时循环数据模型定义。
- `src/live/loop_signal_executor.py`：信号执行与通知处理处理器。
- `src/live/price_service.py`：价格估值与资产汇总服务。
- `src/live/simulator.py`：`StrategyLifecycleDriver` 所在模块，用于触发策略生命周期回调（非第 29 步实时主循环）。
- `src/live/realtime_loop.py`：第 29 步实时模拟主循环实现（`RealtimeSimulationLoop`），整合市场数据、策略执行、撮合引擎、持仓更新的完整闭环；实现 8 步循环逻辑（拉取行情→持久化 K 线→更新估值→处理挂单→运行策略→执行信号→通知更新）；支持三种订单类型执行（市价/限价/止损止盈）；符合运行态写入路径约束（最新行情先落 SQLite）。
- `src/live/*.py`（其余）：实时模拟扩展占位，用于承接第 30 步及后续。
- `src/utils/config.py`：配置加载编排层；负责执行 `默认值 < YAML < 环境变量` 的合并顺序，并提供统一入口。
- `src/utils/config_defaults.py`：配置默认值与环境变量映射定义层；集中维护默认参数与 env 覆盖路径。
- `src/utils/config_validation.py`：配置校验层；负责主配置与策略配置的类型、范围、关系约束校验。
- `src/utils/logger.py`：日志初始化与分流实现层；负责控制台 + 文件输出、分级过滤、轮转/保留/压缩参数接入、敏感信息脱敏。
- `config/config.yaml`：系统主配置模板，承载系统、日志、交易所、账户、交易、风控、回测字段，是运行参数的 YAML 主入口。
- `config/strategies.yaml`：策略配置模板，承载内置策略启停与参数字段，是策略实例化的 YAML 输入入口。
- `config/.env.example`：环境变量模板，承载敏感或环境相关键值（API、数据库路径、日志级别），是 `.env` 初始化参考。
- `tests/test_config.py`：配置层验收测试（优先级三场景 + 关键反例），用于支撑 Phase 0 第 6 条验收。
- `tests/test_logger.py`：日志层验收测试（分流、脱敏、非法类型防御），用于支撑 Phase 0 第 7 条自动化验证。
- `tests/verify_step_7.py`：第 7 步手工演练脚本，用于触发多级日志并检查日志文件落盘与脱敏结果。
- `tests/test_database.py`：第 8-9 步数据库测试（生命周期 + 表结构/约束/索引/外键），用于支撑 Phase 1 第 8-9 条自动化验证。
- `tests/test_models.py`：第 10 步领域模型测试（14 项正反例），用于支撑 Phase 1 第 10 条自动化验证。
- `tests/test_account.py`：第 11 步账户服务测试（5 项验收测试），用于支撑 Phase 1 第 11 条自动化验证。
- `tests/test_order_service.py`：第 12 步订单服务测试（24 项验收测试），用于支撑 Phase 1 第 12 条自动化验证。
- `tests/test_trade_service.py`：第 13 步成交记录测试（部分/全量成交、overfill 拒绝、订单关联），用于支撑 Phase 1 第 13 条自动化验证。
- `tests/test_market_data.py`：第 14 步市场数据测试（交易所选择、限流重试、失败告知、SQLite 写入目标约束），用于支撑 Phase 1 第 14 条自动化验证。
- `tests/test_storage.py`：第 15 步历史数据测试（分页下载落库、时间范围查询、时间序校验、参数校验），用于支撑 Phase 1 第 15 条自动化验证。
- `tests/test_realtime_market_data.py`：第 17 步实时行情测试（统一结构、超时、错误回退），用于支撑 Phase 2 第 17 条自动化验证。
- `tests/test_price_service.py`：第 18 步价格服务测试（估值手算一致、缺价回退与报错），用于支撑 Phase 2 第 18 条自动化验证。
- `tests/test_matching.py`：第 19 步市价撮合测试（固定价格序列可复算、账户与持仓同步、异常边界），用于支撑 Phase 2 第 19 条自动化验证。
- `tests/test_limit_matching.py`：第 20 步限价撮合测试（价格跨越触发、未跨越保持挂单、价格-时间优先级），用于支撑 Phase 2 第 20 条自动化验证。
- `tests/test_stop_trigger.py`：第 21 步止损/止盈触发测试（阈值触发、未触发保持挂单、状态联动、库存预检），用于支撑 Phase 2 第 21 条自动化验证。
- `tests/test_execution_costs.py`：第 22 步手续费与滑点测试（Maker/Taker 费率、方向性滑点、限价边界保护、成交写库），用于支撑 Phase 2 第 22 条自动化验证。
- `tests/test_order_state_machine.py`：第 23 步订单状态机测试（合法流转表、非法流转拒绝、服务级路径），用于支撑 Phase 2 第 23 条自动化验证。
- `tests/test_risk_controls.py`：第 24 步风控测试（单笔仓位超限、总仓位超限、最大回撤超限拒单），用于支撑 Phase 2 第 24 条自动化验证。
- `tests/test_strategies.py`：第 25 步策略生命周期测试（回调顺序、状态守卫、重复初始化拒绝），用于支撑 Phase 3 第 25 条自动化验证。
- `tests/test_backtest_engine.py`：第 26 步回测引擎测试（小样本基础统计、非 SQLite 读取拒绝、无数据区间报错），用于支撑 Phase 3 第 26 条自动化验证。
- `tests/test_backtest_analyzers.py`：第 27 步分析器测试（5 个分析器输出完整性、无交易场景零值、Sharpe 边界情况、时间序列格式、字段完整性），用于支撑 Phase 3 第 27 条自动化验证。
- `tests/test_backtest_exporter.py`：第 28 步导出器测试（摘要 JSON/CSV 创建、资金曲线 JSON/CSV 创建、一键导出、文件名前缀、自动创建目录、None 值处理），用于支撑 Phase 3 第 28 条自动化验证。
- `tests/test_realtime_loop.py`：第 29 步实时循环测试（循环初始化、市场数据拉取与传递、K 线持久化到 SQLite、市价单执行、限价单执行、市场数据失败处理、迭代控制、工厂方法构建），用于支撑 Phase 3 第 29 条自动化验证。
- `tests/quick_test_loop.py`：第 29 步快速验证脚本，用于手工验证实时循环基本功能。
- `tests/test_order_state_machine.py`：第 23 步订单状态机测试（合法流转表、非法流转、服务层关键路径），用于支撑 Phase 2 第 23 条自动化验证。
- `tests/test_risk_controls.py`：第 24 步风控测试（单笔仓位拦截、总仓位拦截、最大回撤拦截），用于支撑 Phase 2 第 24 条自动化验证。
- `tests/test_strategies.py`：第 25 步生命周期测试（回调顺序、状态守卫），用于支撑 Phase 3 第 25 条自动化验证。
- `tests/test_backtest_engine.py`：第 26 步回测引擎测试（SQLite 数据读取、PandasData 馈送、基础统计输出、非 SQLite 读取拒绝），用于支撑 Phase 3 第 26 条自动化验证。
- `tests/test_backtest_analyzers.py`：第 27 步标准分析器测试（5 个分析器输出完整性、无交易边界情况、Sharpe 比率边界情况、时间序列格式、字段完整性），用于支撑 Phase 3 第 27 条自动化验证。
- `tests/*.py`（其余）：测试模块占位，用于承接 Phase 4 第 39 条。
- `requirements.txt`：当前仓库依赖清单入口（安装/CI 统一来源）；后续若恢复严格锁定版本，应与 Phase 0 第 4 条验收口径保持一致。
- `README.md`：补充第 7 步日志方案说明与手工演练步骤，作为日志策略落地说明文档。
- `main.py`：程序入口，调用 `src/cli.py` 执行命令分发。

## 本轮新增架构洞察
- 基础运行层已形成“配置闭环 + 日志闭环”：
  - 模板层：`config/config.yaml`、`config/strategies.yaml`、`config/.env.example`
  - 加载层：`src/utils/config.py`
  - 默认值与映射层：`src/utils/config_defaults.py`
  - 校验层：`src/utils/config_validation.py`
- 日志层：`src/utils/logger.py` + `tests/test_logger.py` + `README.md`（方案说明）+ `tests/verify_step_7.py`（手工演练）
- 数据层生命周期基线：`src/core/database.py` + `tests/test_database.py`
  - 连接管理：`open()` / `close()`
  - 事务边界：`transaction()` 自动提交与异常回滚
  - 配置接入：`from_config()` 读取 `system.database_path`
  - schema 初始化：`initialize_schema()` 统一创建 `accounts`、`orders`、`trades`、`strategy_runs`、`positions`、`candles`
  - 关键约束与索引：`positions` 的 `UNIQUE/CHECK + idx_positions_symbol`；`candles` 的复合 `UNIQUE + 两个查询索引`
  - **第 12 步修正**：`orders` 表的 `created_at` 和 `updated_at` 字段从 `TIMESTAMP` 改为 `INTEGER`，避免 SQLite `PARSE_DECLTYPES` 解析冲突
- 优先级规则已固定为 `默认值 < YAML < 环境变量`，并通过独立测试文件验证三组场景，后续配置演进可直接复用同一验收模式。
- 通过“未知字段拒绝 + 参数关系校验”将配置错误前置到启动阶段，减少运行中故障面。
- 第 34 步新增策略参数管理：`StrategyRegistry` + `StrategyParamResolver` 统一参数合并入口，显式参数覆盖配置；实时循环将合并参数注入 `StrategyContext.parameters`。
- 第 7 步日志方案已直接消费 `load_config()` 产出的 `logging` 配置，避免重复解析配置逻辑。
- 第 35 步新增“显式周期元数据”架构约束：当输入为 `returns_series` 时，必须显式传入 `period_seconds`，并强校验时间戳间隔一致性，防止年化收益与 Sharpe/Sortino 在非等间隔数据下发生系统性偏差。
- 第 36 步新增可视化输出能力：通过统一输入协议将回测与实时资金曲线/成交明细收敛到同一导出模块，并采用 `matplotlib` `Agg` 后端保证无头环境下可稳定生成图片文件。
- 第 36 步验收补充：`performance.py` 与 `visualization.py` 的 `_parse_timestamp` 已统一支持 Python `datetime` 输入，并新增正式 pytest 回归用例覆盖该边界。
- 第 37 步新增 CLI 编排层：采用 `argparse` 子命令模型与多文件处理器拆分（系统命令/订单命令/工作流命令），在保持单文件约束的同时实现命令全集覆盖。
- 第 37 步运行态状态管理采用 `runtime_state.json`（位于 `system.data_dir`），`start/stop/status` 命令共享同一状态源，`status --disk` 提供数据库文件与磁盘容量可观测信息。
- 第 37 步补充显式回归断言：`backtest --output-dir` 必须导出 6 个报告文件与 4 张可视化图表文件，防止导出链路回退。
- 第 9 步已完成并通过验证；下一步（第 10 步）应仅推进领域模型与校验规则定义，不提前进入账户/订单流程实现。
- 第 11 步已完成并通过验证：
  - `src/core/account_service.py` 实现账户生命周期管理（初始化、查询、余额变更、持仓恢复、总资产估值）。
  - 验证过程发现 `require_timestamp()` 不兼容 SQLite `PARSE_DECLTYPES` 产生的 `datetime` 对象，已修复为兼容数值、`datetime` 对象、ISO 字符串三种来源。
  - 全量测试 38 passed（含 `test_account` 5 项、`test_models` 14 项、`test_database` 11 项、`test_config` 5 项、`test_logger` 3 项）。
- 第 12 步已完成并通过验证：
  - `src/core/order_service.py` 实现订单持久化接口（创建、查询、状态更新、撤销）。
  - 实现完整的订单状态机：定义合法流转表（PENDING→OPEN→PARTIALLY_FILLED→FILLED/CANCELED/REJECTED），拒绝非法状态转换。
  - 实现完整的资金管理：买单创建时冻结资金，部分成交时消耗冻结资金（从 frozen 和 balance 同时扣除），取消或 REJECTED 时释放剩余冻结资金。
  - 支持幂等性：当调用方提供 `order_id` 时重复创建返回现有订单；重复取消已终态订单返回当前状态。
  - `update_order_status()` 保持单层事务，移除嵌套 `with tx:`。
  - 全量测试 62 passed（3 warnings，含 `test_order_service` 24 项 + 之前 38 项）。
- 第 14 步已完成并通过验证：
  - `src/data/market.py` 提供统一行情接口：`fetch_ticker` / `fetch_order_book` / `fetch_ohlcv`。
  - `from_config()` 支持按配置选择交易所与限流开关；`from_exchange()` 支持注入式测试。
  - `src/data/market_policy.py` 明确运行态写入目标只能是 `sqlite`，拒绝 `csv/parquet` 作为运行态写入路径。
  - `src/data/market_retry.py` 实现本地限流与错误分类重试策略（限流与网络错误可重试，鉴权与参数类错误快速失败）。
  - 新增 `memory-bank/market-data-interface-design.md` 记录异常处理策略与数据路径约束；新增 `tests/test_market_data.py` 覆盖验收场景。
- 第 15 步已完成（待用户测试验证）：
  - `src/data/storage.py` 新增 `HistoricalCandleStorage`、`CandleDownloadRequest`、`CandleDownloadResult`。
  - `download_and_store()` 支持按时间范围分批下载历史 K 线并写入 SQLite `candles` 表。
  - `query_candles()` 支持按 `symbol/timeframe/time range` 查询并保证 `timestamp ASC` 返回。
  - 新增命名规范方法 `build_dataset_name()`，统一数据集标识（示例：`BTC_USDT_1h`）。
  - 新增 `tests/test_storage.py` 覆盖分页下载、落库、查询时间序与异常输入校验。
- 第 16 步已完成（待用户测试验证）：
  - `src/core/database.py` 新增 `candle_download_cache` 表与 `idx_candle_cache_lookup` 索引，用于历史请求缓存元数据持久化。
  - `src/data/storage.py` 新增缓存命中逻辑：重复请求同一 `symbol/timeframe/time range` 时直接命中缓存并跳过重复下载。
  - K 线写入改为 `INSERT OR IGNORE`，基于 `candles` 表唯一约束实现去重写入；`downloaded_count` 表示本次实际新增行数。
  - `tests/test_storage.py` 新增用例覆盖重复请求缓存命中、重叠区间去重、跨实例缓存命中。
- 第 17 步已完成（待用户测试验证）：
  - `src/data/realtime_market.py` 新增 `RealtimeMarketDataService`，统一实时接口：`get_latest_price` / `get_depth` / `get_klines`。
  - 增加请求级超时保护：超时返回统一快照并标记 `timed_out=True`。
  - 增加错误兜底：优先回退最近成功数据；无缓存时返回统一空结构与错误信息。
  - `src/data/realtime_payloads.py` 定义 `RealtimeMarketSnapshot` 与 payload 归一化，确保三类接口字段结构一致。
  - `tests/test_realtime_market_data.py` 覆盖结构一致性、超时行为和回退行为。
- 第 18 步已完成（待用户测试验证）：
  - `src/live/price_service.py` 新增 `PriceService`，以实时最新价评估持仓并输出组合估值结果。
  - 持仓评估会回写 `positions.current_price` 与 `positions.unrealized_pnl`，保证崩溃恢复后估值状态一致。
  - 最新价缺失时回退 `positions.current_price`；两者都缺失时显式报错，避免静默估值偏差。
  - `tests/test_price_service.py` 覆盖固定行情手算一致、缺价回退与缺价报错场景。
- 第 19 步已完成（待用户测试验证）：
  - `src/core/matching.py` 新增 `MatchingEngine`，实现市价单按最新价即时成交（`execute_market_order`）。
  - 撮合流程实现：创建市价单 → 状态推进到 `open` → 成交写入 `trades` → 状态收敛到 `filled`。
  - 账户同步实现：买单增加基础币余额；卖单减少基础币余额并增加报价币余额。
  - 持仓同步实现：买单新建/加仓并重算加权成本；卖单减仓并更新已实现/未实现盈亏。
  - `tests/test_matching.py` 覆盖固定价格序列下结果可复算、缺价失败、卖出库存不足失败。
- 第 20 步已完成并通过用户验证：
  - `src/core/limit_matching.py` 新增 `LimitOrderMatchingEngine`，实现限价下单、挂单队列查询与按 symbol 触发撮合（`process_limit_order_queue`）。
  - `src/core/limit_settlement.py` 新增 `LimitOrderSettlement`，封装限价成交后的账户与持仓结算。
  - 触发规则实现：买单 `latest_price <= limit_price`，卖单 `latest_price >= limit_price`；未触发订单保持挂单。
  - 队列规则实现：价格-时间优先级（买单高价优先，卖单低价优先，同价按创建时间）。
  - `tests/test_limit_matching.py` 覆盖跨价触发、保持挂单与优先级行为，验证“价格跨越挂单价时订单正确成交或保持挂单”。
- 第 21 步已完成（待用户测试验证）：
  - `src/core/stop_trigger.py` 新增 `StopTriggerEngine`，实现止损/止盈订单创建与按 symbol 触发扫描（`process_trigger_orders`）。
  - 触发规则实现：
    - `STOP_LOSS`：卖单 `latest <= trigger`，买单 `latest >= trigger`
    - `TAKE_PROFIT`：卖单 `latest >= trigger`，买单 `latest <= trigger`
  - 触发后联动现有订单状态机：通过 `TradeService.record_trade()` 推进 `open -> filled/partially_filled`。
  - 触发后联动账户/持仓更新：复用 `LimitOrderSettlement` 同步 `accounts` 与 `positions`。
  - `tests/test_stop_trigger.py` 覆盖未触发保持挂单、止损/止盈触发成交、买向触发与库存预检失败场景。
- 第 22 步已完成（待用户测试验证）：
  - `src/core/execution_cost.py` 新增统一执行成本模型 `ExecutionCostProfile`，实现 Maker/Taker 费率与方向性滑点计算。
  - `src/core/matching.py` 接入市价单 Taker 手续费与滑点，成交写库不再固定 `fee=0.0`。
  - `src/core/limit_matching.py` 接入限价单 Maker 手续费与滑点，并通过限价边界保护避免突破限价。
  - `src/core/stop_trigger.py` 接入触发单 Taker 手续费与滑点，成交写库不再固定 `fee=0.0`。
  - `tests/test_execution_costs.py` 新增“已知参数可复算”测试，覆盖市价/限价/触发三类成交路径。
- 第 23 步已完成（待用户测试验证）：
  - `src/core/order_state_machine.py` 新增统一订单状态机与合法流转表（`pending/open/partially_filled/filled/canceled/rejected`，其中“新建”映射为 `pending`）。
  - `src/core/order_service.py` 改为复用状态机校验流转，并将 `update_order_status(..., canceled)` 路由到 `cancel_order()`，避免冻结资金释放逻辑被绕过。
  - `src/core/trade_service.py` 在写入成交后更新订单状态前新增状态机校验，防止非法状态落库。
  - `tests/test_order_state_machine.py` 覆盖合法流转表逐条路径、非法流转拒绝与服务层关键路径。
- 第 24 步已完成（待用户测试验证）：
  - `src/core/risk.py` 新增统一风控模块 `RiskControl`，实现单笔仓位、总仓位、最大回撤三项下单前检查。
  - `src/core/matching.py` / `src/core/limit_matching.py` / `src/core/stop_trigger.py` 接入风控前置校验，超限时拒绝下单并返回拒单原因。
  - `tests/test_risk_controls.py` 新增三类拒单测试，验证超阈值交易会被拦截且不写入 `orders/trades`。
- 第 25 步已完成（待用户测试验证）：
  - `src/strategies/base.py` 新增 `LiveStrategy` 生命周期基类与 `StrategyContext`/`StrategyOrderEvent`/`StrategyTradeEvent`。
  - `src/live/simulator.py` 新增 `StrategyLifecycleDriver`，驱动 `initialize/run/notify_order/notify_trade/stop` 回调链路。
  - `src/strategies/lifecycle_demo_strategy.py` 新增 `LifecycleProbeStrategy`，作为最小示例策略验证生命周期触发。
  - `tests/test_strategies.py` 覆盖回调顺序与状态守卫（未初始化运行拒绝、重复初始化拒绝）。
- 第 26 步已完成并通过用户验证：
  - `src/backtest/engine.py` 新增 `BacktestEngine`，集成 Backtrader Cerebro，支持单次回测运行并输出基础统计（初始资金、期末资金、收益率、样本条数）。
  - `src/data/feed.py` 新增 `SQLitePandasFeedFactory`，实现 `candles` 表查询结果到 `pandas.DataFrame` 与 `PandasData` 的桥接。
  - `src/utils/config_defaults.py` / `src/utils/config_validation.py` / `config/config.yaml` 新增并强制 `backtest.data_read_source=sqlite`，拒绝 CSV/Parquet 运行态读取。
  - `tests/test_backtest_engine.py` 与 `tests/test_config.py` 新增第 26 步约束测试，验证"回测读取路径仅 SQLite"。
- 第 27 步已完成（待用户测试验证）：
  - `src/backtest/analyzers.py` 新增 `AnalyzerMount`，实现 5 个标准分析器挂载（Sharpe、DrawDown、TradeAnalyzer、Returns、TimeReturn）与结果提取。
  - `src/backtest/engine.py` 扩展 `BacktestRunResult`，新增 3 个嵌套数据类（`TradeStatistics`、`RiskMetrics`、`ReturnsAnalysis`）与 4 个分析器字段。
  - `BacktestEngine.run()` 更新为：挂载分析器 → 运行回测 → 提取结果 → 转换为统一结构。
  - 新增 4 个转换方法处理边界情况：无交易返回零值、Sharpe 比率可能为 `None`、时间序列键转换为 ISO 字符串。
  - `tests/test_backtest_analyzers.py` 新增 5 项验收测试，覆盖分析器输出完整性、边界情况与字段完整性。
- 第 28 步已完成并通过用户验证：
  - `src/backtest/exporter.py` 新增 `BacktestResultExporter`，提供统一的回测结果导出接口。
  - 实现 4 个导出方法：`export_summary_json()`、`export_summary_csv()`、`export_equity_curve_json()`、`export_equity_curve_csv()`。
  - 实现 `export_all()` 一键导出所有格式（4 个文件）。
  - 支持自定义文件名前缀、自动创建输出目录、正确处理 `None` 值。
  - `tests/test_backtest_exporter.py` 新增 18 项测试，覆盖文件创建、格式正确性、边界情况与错误路径（100% 覆盖）。
-│   ├── live/              # 实时模拟 (Live Simulation)
│   │   ├── loop_models.py        # 实时循环数据模型
│   │   ├── loop_signal_executor.py # 信号执行与通知处理器
│   │   ├── price_service.py      # 价格估值服务
│   │   ├── realtime_loop.py      # 实时模拟主循环
│   │   └── simulator.py          # 策略生命周期驱动器
 `StrategyLifecycleDriver`，用于触发策略生命周期回调（非第 29 步实时主循环）。
- `src/live/realtime_loop.py`：第 29 步实时模拟主循环实现（`RealtimeSimulationLoop`），整合市场数据、策略执行、撮合引擎、持仓更新的完整闭环；实现 8 步循环逻辑（拉取行情→持久化 K 线→更新估值→处理挂单→运行策略→执行信号→通知更新）；支持三种订单类型执行（市价/限价/止损止盈）；符合运行态写入路径约束（最新行情先落 SQLite）。
- `src/live/*.py`（其余）：实时模拟扩展占位，用于承接第 30 步及后续。
- `src/utils/config.py`：配置加载编排层；负责执行 `默认值 < YAML < 环境变量` 的合并顺序，并提供统一入口。
- `src/utils/config_defaults.py`：配置默认值与环境变量映射定义层；集中维护默认参数与 env 覆盖路径。
- `src/utils/config_validation.py`：配置校验层；负责主配置与策略配置的类型、范围、关系约束校验。
- `src/utils/logger.py`：日志初始化与分流实现层；负责控制台 + 文件输出、分级过滤、轮转/保留/压缩参数接入、敏感信息脱敏。
- `config/config.yaml`：系统主配置模板，承载系统、日志、交易所、账户、交易、风控、回测字段，是运行参数的 YAML 主入口。
- `config/strategies.yaml`：策略配置模板，承载内置策略启停与参数字段，是策略实例化的 YAML 输入入口。
- `config/.env.example`：环境变量模板，承载敏感或环境相关键值（API、数据库路径、日志级别），是 `.env` 初始化参考。
- `tests/test_config.py`：配置层验收测试（优先级三场景 + 关键反例），用于支撑 Phase 0 第 6 条验收。
- `tests/test_logger.py`：日志层验收测试（分流、脱敏、非法类型防御），用于支撑 Phase 0 第 7 条自动化验证。
- `tests/verify_step_7.py`：第 7 步手工演练脚本，用于触发多级日志并检查日志文件落盘与脱敏结果。
- `tests/test_database.py`：第 8-9 步数据库测试（生命周期 + 表结构/约束/索引/外键），用于支撑 Phase 1 第 8-9 条自动化验证。
- `tests/test_models.py`：第 10 步领域模型测试（14 项正反例），用于支撑 Phase 1 第 10 条自动化验证。
- `tests/test_account.py`：第 11 步账户服务测试（5 项验收测试），用于支撑 Phase 1 第 11 条自动化验证。
- `tests/test_order_service.py`：第 12 步订单服务测试（24 项验收测试），用于支撑 Phase 1 第 12 条自动化验证。
- `tests/test_trade_service.py`：第 13 步成交记录测试（部分/全量成交、overfill 拒绝、订单关联），用于支撑 Phase 1 第 13 条自动化验证。
- `tests/test_market_data.py`：第 14 步市场数据测试（交易所选择、限流重试、失败告知、SQLite 写入目标约束），用于支撑 Phase 1 第 14 条自动化验证。
- `tests/test_storage.py`：第 15 步历史数据测试（分页下载落库、时间范围查询、时间序校验、参数校验），用于支撑 Phase 1 第 15 条自动化验证。
- `tests/test_realtime_market_data.py`：第 17 步实时行情测试（统一结构、超时、错误回退），用于支撑 Phase 2 第 17 条自动化验证。
- `tests/test_price_service.py`：第 18 步价格服务测试（估值手算一致、缺价回退与报错），用于支撑 Phase 2 第 18 条自动化验证。
- `tests/test_matching.py`：第 19 步市价撮合测试（固定价格序列可复算、账户与持仓同步、异常边界），用于支撑 Phase 2 第 19 条自动化验证。
- `tests/test_limit_matching.py`：第 20 步限价撮合测试（价格跨越触发、未跨越保持挂单、价格-时间优先级），用于支撑 Phase 2 第 20 条自动化验证。
- `tests/test_stop_trigger.py`：第 21 步止损/止盈触发测试（阈值触发、未触发保持挂单、状态联动、库存预检），用于支撑 Phase 2 第 21 条自动化验证。
- `tests/test_execution_costs.py`：第 22 步手续费与滑点测试（Maker/Taker 费率、方向性滑点、限价边界保护、成交写库），用于支撑 Phase 2 第 22 条自动化验证。
- `tests/test_order_state_machine.py`：第 23 步订单状态机测试（合法流转表、非法流转拒绝、服务级路径），用于支撑 Phase 2 第 23 条自动化验证。
- `tests/test_risk_controls.py`：第 24 步风控测试（单笔仓位超限、总仓位超限、最大回撤超限拒单），用于支撑 Phase 2 第 24 条自动化验证。
- `tests/test_strategies.py`：第 25 步策略生命周期测试（回调顺序、状态守卫、重复初始化拒绝），用于支撑 Phase 3 第 25 条自动化验证。
- `tests/test_backtest_engine.py`：第 26 步回测引擎测试（小样本基础统计、非 SQLite 读取拒绝、无数据区间报错），用于支撑 Phase 3 第 26 条自动化验证。
- `tests/test_backtest_analyzers.py`：第 27 步分析器测试（5 个分析器输出完整性、无交易场景零值、Sharpe 边界情况、时间序列格式、字段完整性），用于支撑 Phase 3 第 27 条自动化验证。
- `tests/test_backtest_exporter.py`：第 28 步导出器测试（摘要 JSON/CSV 创建、资金曲线 JSON/CSV 创建、一键导出、文件名前缀、自动创建目录、None 值处理），用于支撑 Phase 3 第 28 条自动化验证。
- `tests/test_realtime_loop.py`：第 29 步实时循环测试（循环初始化、市场数据拉取与传递、K 线持久化到 SQLite、市价单执行、限价单执行、市场数据失败处理、迭代控制、工厂方法构建），用于支撑 Phase 3 第 29 条自动化验证。
- `tests/quick_test_loop.py`：第 29 步快速验证脚本，用于手工验证实时循环基本功能。
- `tests/test_order_state_machine.py`：第 23 步订单状态机测试（合法流转表、非法流转、服务层关键路径），用于支撑 Phase 2 第 23 条自动化验证。
- `tests/test_risk_controls.py`：第 24 步风控测试（单笔仓位拦截、总仓位拦截、最大回撤拦截），用于支撑 Phase 2 第 24 条自动化验证。
- `tests/test_strategies.py`：第 25 步生命周期测试（回调顺序、状态守卫），用于支撑 Phase 3 第 25 条自动化验证。
- `tests/test_backtest_engine.py`：第 26 步回测引擎测试（SQLite 数据读取、PandasData 馈送、基础统计输出、非 SQLite 读取拒绝），用于支撑 Phase 3 第 26 条自动化验证。
- `tests/test_backtest_analyzers.py`：第 27 步标准分析器测试（5 个分析器输出完整性、无交易边界情况、Sharpe 比率边界情况、时间序列格式、字段完整性），用于支撑 Phase 3 第 27 条自动化验证。
- `tests/*.py`（其余）：测试模块占位，用于承接 Phase 4 第 39 条。
- `requirements.txt`：当前仓库依赖清单入口（安装/CI 统一来源）；后续若恢复严格锁定版本，应与 Phase 0 第 4 条验收口径保持一致。
- `README.md`：补充第 7 步日志方案说明与手工演练步骤，作为日志策略落地说明文档。
- `main.py`：程序入口，调用 `src/cli.py` 执行命令分发。

## 本轮新增架构洞察
- 基础运行层已形成“配置闭环 + 日志闭环”：
  - 模板层：`config/config.yaml`、`config/strategies.yaml`、`config/.env.example`
  - 加载层：`src/utils/config.py`
  - 默认值与映射层：`src/utils/config_defaults.py`
  - 校验层：`src/utils/config_validation.py`
- 日志层：`src/utils/logger.py` + `tests/test_logger.py` + `README.md`（方案说明）+ `tests/verify_step_7.py`（手工演练）
- 数据层生命周期基线：`src/core/database.py` + `tests/test_database.py`
  - 连接管理：`open()` / `close()`
  - 事务边界：`transaction()` 自动提交与异常回滚
  - 配置接入：`from_config()` 读取 `system.database_path`
  - schema 初始化：`initialize_schema()` 统一创建 `accounts`、`orders`、`trades`、`strategy_runs`、`positions`、`candles`
  - 关键约束与索引：`positions` 的 `UNIQUE/CHECK + idx_positions_symbol`；`candles` 的复合 `UNIQUE + 两个查询索引`
  - **第 12 步修正**：`orders` 表的 `created_at` 和 `updated_at` 字段从 `TIMESTAMP` 改为 `INTEGER`，避免 SQLite `PARSE_DECLTYPES` 解析冲突
- 优先级规则已固定为 `默认值 < YAML < 环境变量`，并通过独立测试文件验证三组场景，后续配置演进可直接复用同一验收模式。
- 通过“未知字段拒绝 + 参数关系校验”将配置错误前置到启动阶段，减少运行中故障面。
- 第 7 步日志方案已直接消费 `load_config()` 产出的 `logging` 配置，避免重复解析配置逻辑。
- 第 9 步已完成并通过验证；下一步（第 10 步）应仅推进领域模型与校验规则定义，不提前进入账户/订单流程实现。
- 第 11 步已完成并通过验证：
  - `src/core/account_service.py` 实现账户生命周期管理（初始化、查询、余额变更、持仓恢复、总资产估值）。
  - 验证过程发现 `require_timestamp()` 不兼容 SQLite `PARSE_DECLTYPES` 产生的 `datetime` 对象，已修复为兼容数值、`datetime` 对象、ISO 字符串三种来源。
  - 全量测试 38 passed（含 `test_account` 5 项、`test_models` 14 项、`test_database` 11 项、`test_config` 5 项、`test_logger` 3 项）。
- 第 12 步已完成并通过验证：
  - `src/core/order_service.py` 实现订单持久化接口（创建、查询、状态更新、撤销）。
  - 实现完整的订单状态机：定义合法流转表（PENDING→OPEN→PARTIALLY_FILLED→FILLED/CANCELED），拒绝非法状态转换。
  - 实现完整的资金管理：买单创建时冻结资金，部分成交时消耗冻结资金（从 frozen 和 balance 同时扣除），取消时释放剩余冻结资金。
  - 支持幂等性：重复创建/取消已终态订单返回当前状态。
  - 全量测试 59 passed（含 `test_order_service` 21 项 + 之前 38 项）。
- 第 14 步已完成并通过验证：
  - `src/data/market.py` 提供统一行情接口：`fetch_ticker` / `fetch_order_book` / `fetch_ohlcv`。
  - `from_config()` 支持按配置选择交易所与限流开关；`from_exchange()` 支持注入式测试。
  - `src/data/market_policy.py` 明确运行态写入目标只能是 `sqlite`，拒绝 `csv/parquet` 作为运行态写入路径。
  - `src/data/market_retry.py` 实现本地限流与错误分类重试策略（限流与网络错误可重试，鉴权与参数类错误快速失败）。
  - 新增 `memory-bank/market-data-interface-design.md` 记录异常处理策略与数据路径约束；新增 `tests/test_market_data.py` 覆盖验收场景。
- 第 15 步已完成（待用户测试验证）：
  - `src/data/storage.py` 新增 `HistoricalCandleStorage`、`CandleDownloadRequest`、`CandleDownloadResult`。
  - `download_and_store()` 支持按时间范围分批下载历史 K 线并写入 SQLite `candles` 表。
  - `query_candles()` 支持按 `symbol/timeframe/time range` 查询并保证 `timestamp ASC` 返回。
  - 新增命名规范方法 `build_dataset_name()`，统一数据集标识（示例：`BTC_USDT_1h`）。
  - 新增 `tests/test_storage.py` 覆盖分页下载、落库、查询时间序与异常输入校验。
- 第 16 步已完成（待用户测试验证）：
  - `src/core/database.py` 新增 `candle_download_cache` 表与 `idx_candle_cache_lookup` 索引，用于历史请求缓存元数据持久化。
  - `src/data/storage.py` 新增缓存命中逻辑：重复请求同一 `symbol/timeframe/time range` 时直接命中缓存并跳过重复下载。
  - K 线写入改为 `INSERT OR IGNORE`，基于 `candles` 表唯一约束实现去重写入；`downloaded_count` 表示本次实际新增行数。
  - `tests/test_storage.py` 新增用例覆盖重复请求缓存命中、重叠区间去重、跨实例缓存命中。
- 第 17 步已完成（待用户测试验证）：
  - `src/data/realtime_market.py` 新增 `RealtimeMarketDataService`，统一实时接口：`get_latest_price` / `get_depth` / `get_klines`。
  - 增加请求级超时保护：超时返回统一快照并标记 `timed_out=True`。
  - 增加错误兜底：优先回退最近成功数据；无缓存时返回统一空结构与错误信息。
  - `src/data/realtime_payloads.py` 定义 `RealtimeMarketSnapshot` 与 payload 归一化，确保三类接口字段结构一致。
  - `tests/test_realtime_market_data.py` 覆盖结构一致性、超时行为和回退行为。
- 第 18 步已完成（待用户测试验证）：
  - `src/live/price_service.py` 新增 `PriceService`，以实时最新价评估持仓并输出组合估值结果。
  - 持仓评估会回写 `positions.current_price` 与 `positions.unrealized_pnl`，保证崩溃恢复后估值状态一致。
  - 最新价缺失时回退 `positions.current_price`；两者都缺失时显式报错，避免静默估值偏差。
  - `tests/test_price_service.py` 覆盖固定行情手算一致、缺价回退与缺价报错场景。
- 第 19 步已完成（待用户测试验证）：
  - `src/core/matching.py` 新增 `MatchingEngine`，实现市价单按最新价即时成交（`execute_market_order`）。
  - 撮合流程实现：创建市价单 → 状态推进到 `open` → 成交写入 `trades` → 状态收敛到 `filled`。
  - 账户同步实现：买单增加基础币余额；卖单减少基础币余额并增加报价币余额。
  - 持仓同步实现：买单新建/加仓并重算加权成本；卖单减仓并更新已实现/未实现盈亏。
  - `tests/test_matching.py` 覆盖固定价格序列下结果可复算、缺价失败、卖出库存不足失败。
- 第 20 步已完成并通过用户验证：
  - `src/core/limit_matching.py` 新增 `LimitOrderMatchingEngine`，实现限价下单、挂单队列查询与按 symbol 触发撮合（`process_limit_order_queue`）。
  - `src/core/limit_settlement.py` 新增 `LimitOrderSettlement`，封装限价成交后的账户与持仓结算。
  - 触发规则实现：买单 `latest_price <= limit_price`，卖单 `latest_price >= limit_price`；未触发订单保持挂单。
  - 队列规则实现：价格-时间优先级（买单高价优先，卖单低价优先，同价按创建时间）。
  - `tests/test_limit_matching.py` 覆盖跨价触发、保持挂单与优先级行为，验证“价格跨越挂单价时订单正确成交或保持挂单”。
- 第 21 步已完成（待用户测试验证）：
  - `src/core/stop_trigger.py` 新增 `StopTriggerEngine`，实现止损/止盈订单创建与按 symbol 触发扫描（`process_trigger_orders`）。
  - 触发规则实现：
    - `STOP_LOSS`：卖单 `latest <= trigger`，买单 `latest >= trigger`
    - `TAKE_PROFIT`：卖单 `latest >= trigger`，买单 `latest <= trigger`
  - 触发后联动现有订单状态机：通过 `TradeService.record_trade()` 推进 `open -> filled/partially_filled`。
  - 触发后联动账户/持仓更新：复用 `LimitOrderSettlement` 同步 `accounts` 与 `positions`。
  - `tests/test_stop_trigger.py` 覆盖未触发保持挂单、止损/止盈触发成交、买向触发与库存预检失败场景。
- 第 22 步已完成（待用户测试验证）：
  - `src/core/execution_cost.py` 新增统一执行成本模型 `ExecutionCostProfile`，实现 Maker/Taker 费率与方向性滑点计算。
  - `src/core/matching.py` 接入市价单 Taker 手续费与滑点，成交写库不再固定 `fee=0.0`。
  - `src/core/limit_matching.py` 接入限价单 Maker 手续费与滑点，并通过限价边界保护避免突破限价。
  - `src/core/stop_trigger.py` 接入触发单 Taker 手续费与滑点，成交写库不再固定 `fee=0.0`。
  - `tests/test_execution_costs.py` 新增“已知参数可复算”测试，覆盖市价/限价/触发三类成交路径。
- 第 23 步已完成（待用户测试验证）：
  - `src/core/order_state_machine.py` 新增统一订单状态机与合法流转表（`pending/open/partially_filled/filled/canceled/rejected`，其中“新建”映射为 `pending`）。
  - `src/core/order_service.py` 改为复用状态机校验流转，并将 `update_order_status(..., canceled)` 路由到 `cancel_order()`，避免冻结资金释放逻辑被绕过。
  - `src/core/trade_service.py` 在写入成交后更新订单状态前新增状态机校验，防止非法状态落库。
  - `tests/test_order_state_machine.py` 覆盖合法流转表逐条路径、非法流转拒绝与服务层关键路径。
- 第 24 步已完成（待用户测试验证）：
  - `src/core/risk.py` 新增统一风控模块 `RiskControl`，实现单笔仓位、总仓位、最大回撤三项下单前检查。
  - `src/core/matching.py` / `src/core/limit_matching.py` / `src/core/stop_trigger.py` 接入风控前置校验，超限时拒绝下单并返回拒单原因。
  - `tests/test_risk_controls.py` 新增三类拒单测试，验证超阈值交易会被拦截且不写入 `orders/trades`。
- 第 25 步已完成（待用户测试验证）：
  - `src/strategies/base.py` 新增 `LiveStrategy` 生命周期基类与 `StrategyContext`/`StrategyOrderEvent`/`StrategyTradeEvent`。
  - `src/live/simulator.py` 新增 `StrategyLifecycleDriver`，驱动 `initialize/run/notify_order/notify_trade/stop` 回调链路。
  - `src/strategies/lifecycle_demo_strategy.py` 新增 `LifecycleProbeStrategy`，作为最小示例策略验证生命周期触发。
  - `tests/test_strategies.py` 覆盖回调顺序与状态守卫（未初始化运行拒绝、重复初始化拒绝）。
- 第 26 步已完成并通过用户验证：
  - `src/backtest/engine.py` 新增 `BacktestEngine`，集成 Backtrader Cerebro，支持单次回测运行并输出基础统计（初始资金、期末资金、收益率、样本条数）。
  - `src/data/feed.py` 新增 `SQLitePandasFeedFactory`，实现 `candles` 表查询结果到 `pandas.DataFrame` 与 `PandasData` 的桥接。
  - `src/utils/config_defaults.py` / `src/utils/config_validation.py` / `config/config.yaml` 新增并强制 `backtest.data_read_source=sqlite`，拒绝 CSV/Parquet 运行态读取。
  - `tests/test_backtest_engine.py` 与 `tests/test_config.py` 新增第 26 步约束测试，验证"回测读取路径仅 SQLite"。
- 第 27 步已完成（待用户测试验证）：
  - `src/backtest/analyzers.py` 新增 `AnalyzerMount`，实现 5 个标准分析器挂载（Sharpe、DrawDown、TradeAnalyzer、Returns、TimeReturn）与结果提取。
  - `src/backtest/engine.py` 扩展 `BacktestRunResult`，新增 3 个嵌套数据类（`TradeStatistics`、`RiskMetrics`、`ReturnsAnalysis`）与 4 个分析器字段。
  - `BacktestEngine.run()` 更新为：挂载分析器 → 运行回测 → 提取结果 → 转换为统一结构。
  - 新增 4 个转换方法处理边界情况：无交易返回零值、Sharpe 比率可能为 `None`、时间序列键转换为 ISO 字符串。
  - `tests/test_backtest_analyzers.py` 新增 5 项验收测试，覆盖分析器输出完整性、边界情况与字段完整性。
- 第 28 步已完成并通过用户验证：
  - `src/backtest/exporter.py` 新增 `BacktestResultExporter`，提供统一的回测结果导出接口。
  - 实现 4 个导出方法：`export_summary_json()`、`export_summary_csv()`、`export_equity_curve_json()`、`export_equity_curve_csv()`。
  - 实现 `export_all()` 一键导出所有格式（4 个文件）。
  - 支持自定义文件名前缀、自动创建输出目录、正确处理 `None` 值。
  - `tests/test_backtest_exporter.py` 新增 18 项测试，覆盖文件创建、格式正确性、边界情况与错误路径（100% 覆盖）。
- 第 29 步已完成并通过用户验证：
  - `src/live/realtime_loop.py` 新增 `RealtimeSimulationLoop`，实现完整的实时模拟主循环（298 行）。
  - 实现 8 步循环逻辑：拉取行情 → 持久化 K 线到 SQLite → 更新持仓估值 → 处理挂单队列 → 运行策略 → 执行信号 → 通知更新。
  - 集成三个撮合引擎：`MatchingEngine`（市价单）、`LimitOrderMatchingEngine`（限价单）、`StopTriggerEngine`（止损/止盈）。
  - 实现 `_persist_latest_candle()`：将最新价格作为 K 线写入 SQLite（符合运行态写入路径约束）。
  - 实现 `_execute_strategy_signal()`：解析并执行策略信号（支持 market/limit/stop_loss/take_profit 四种订单类型）。
  - 实现 `_notify_strategy_updates()`：通知策略最近的订单和成交更新。
  - 实现 `from_config()` 工厂方法，从配置字典构建循环实例。
  - 支持优雅错误处理：市场数据失败、策略执行失败、通知失败均不会中断循环。
  - 支持 `max_iterations` 限制，用于测试和有限运行场景。
  - `tests/test_realtime_loop.py` 新增 8 项验收测试，覆盖循环初始化、市场数据拉取、K 线持久化、信号执行、错误处理、迭代控制。
