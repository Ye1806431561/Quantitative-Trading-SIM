# 需求追踪清单（Phase 0-4 / Step 1-38）

## 说明
- 来源文档：`memory-bank/product-requirement-document.md`
- 目标：将需求逐项映射到模块与交付物，并标记范围（必选/可选）
- 状态：已完成实施计划第 1-38 步代码与文档落地（第 34-38 步已验证通过）；第 39 步未开始

## 最小可用范围（MVP）定义

### In Scope（当前交付）
- CLI
- 模拟盘（回测 + 实时模拟）
- 账户管理
- 订单与撮合
- 风险控制
- 回测引擎与分析器
- 数据管理（下载、落库、查询、导入导出）

### Out of Scope（当前排除）
- Web 界面与其依赖能力（对应 `FR-WEB-01`）
- 原因：Phase 0-4 当前交付不含 Web，优先保证 CLI 与双引擎闭环

## 需求映射矩阵

| ID | 需求项 | 模块归属 | 交付物 | 范围 | 排除理由（仅可选项必填） |
|---|---|---|---|---|---|
| FR-ACC-01 | 虚拟账户初始化（初始资金） | `src/core/account.py` | 账户初始化服务与 CLI 初始化命令 | 必选 | - |
| FR-ACC-02 | 多币种余额管理 | `src/core/account.py` | 余额模型与更新接口 | 必选 | - |
| FR-ACC-03 | 账户资产实时计算 | `src/core/account.py`, `src/live/price_service.py` | 估值服务 | 必选 | - |
| FR-ACC-04 | 查看当前持仓 | `src/core/position.py`, `src/cli.py`, `src/cli_commands.py` | 持仓查询接口与 CLI 展示 | 必选 | - |
| FR-ACC-05 | 查看可用余额/冻结资金/总资产估值 | `src/core/account.py`, `src/cli.py`, `src/cli_commands.py` | 账户查询命令 | 必选 | - |
| FR-MKT-01 | 通过 CCXT 获取实时行情 | `src/data/market.py` | 市场数据客户端 | 必选 | - |
| FR-MKT-02 | 支持多个主流交易所 | `src/data/market.py`, `config/config.yaml` | 交易所适配与配置项 | 必选 | - |
| FR-MKT-03 | 实时价格/深度/K 线获取 | `src/data/market.py`, `src/data/realtime_market.py` | 行情查询接口 | 必选 | - |
| FR-MKT-04 | 历史 K 线下载与存储 | `src/data/storage.py`, `src/core/database.py` | 下载器与持久化接口 | 必选 | - |
| FR-MKT-05 | 多时间周期支持（1m/5m/15m/1h/4h/1d） | `src/data/storage.py` | 周期枚举与校验 | 必选 | - |
| FR-MKT-06 | 本地数据缓存机制 | `src/data/storage.py` | 去重与增量下载逻辑 | 必选 | - |
| FR-ORD-01 | 订单类型：市价单 | `src/core/order.py`, `src/core/matching.py` | 市价单模型与撮合流程 | 必选 | - |
| FR-ORD-02 | 订单类型：限价单 | `src/core/order.py`, `src/core/matching.py` | 限价挂单与触发撮合 | 必选 | - |
| FR-ORD-03 | 订单类型：止损单 | `src/core/order.py`, `src/core/stop_trigger.py` | 止损触发规则 | 必选 | - |
| FR-ORD-04 | 订单类型：止盈单 | `src/core/order.py`, `src/core/stop_trigger.py` | 止盈触发规则 | 必选 | - |
| FR-ORD-05 | 下单/撤单/状态查询/历史记录 | `src/core/order.py`, `src/cli.py`, `src/cli_order_commands.py` | 订单服务与 CLI 命令 | 必选 | - |
| FR-MCH-01 | 模拟撮合（基于实时价格） | `src/core/matching.py` | 撮合引擎 | 必选 | - |
| FR-MCH-02 | 限价单队列管理 | `src/core/matching.py` | 队列与撮合状态机 | 必选 | - |
| FR-MCH-03 | 滑点模拟可配置 | `src/core/execution_cost.py`, `src/core/matching.py`, `src/core/limit_matching.py`, `src/core/stop_trigger.py`, `config/config.yaml` | 滑点参数与计算器 | 必选 | - |
| FR-MCH-04 | Maker/Taker 手续费计算 | `src/core/execution_cost.py`, `src/core/matching.py`, `src/core/limit_matching.py`, `src/core/stop_trigger.py`, `src/core/trade.py` | 费用计算与落库 | 必选 | - |
| FR-STR-01 | 统一策略接口规范 | `src/strategies/base.py` | 策略抽象基类 | 必选 | - |
| FR-STR-02 | 生命周期管理（初始化/运行/停止） | `src/strategies/base.py`, `src/live/simulator.py` | 生命周期调度器 | 必选 | - |
| FR-STR-03 | 多策略并行支持 | `src/live/simulator.py` | 策略调度容器 | 必选 | - |
| FR-STR-04 | 策略适配器（回测/实时转换） | `src/strategies/adapter.py` | 双引擎适配层 | 必选 | - |
| FR-STR-05 | 回测策略继承 `backtrader.Strategy` | `src/backtest/engine.py`, `src/strategies/*.py` | 回测策略模板 | 必选 | - |
| FR-STR-06 | 实时策略继承 `LiveStrategy` | `src/strategies/base.py`, `src/live/simulator.py` | 实时策略模板 | 必选 | - |
| FR-STR-07 | 内置策略：SMA / 网格 / 布林带 | `src/strategies/sma_strategy.py`, `src/strategies/grid_strategy.py`, `src/strategies/bollinger_strategy.py` | 三个内置策略模块 | 必选 | - |
| FR-STR-08 | 策略参数配置与优化接口 | `config/strategies.yaml`, `src/strategies/registry.py`, `src/strategies/param_resolver.py`, `src/strategies/factory.py`, `src/backtest/optimizer.py` | 参数加载与优化入口 | 必选 | - |
| FR-RSK-01 | 单笔交易最大金额限制 | `src/core/risk.py` | 下单前风控检查 | 必选 | - |
| FR-RSK-02 | 总仓位比例控制 | `src/core/risk.py` | 总仓位限制规则 | 必选 | - |
| FR-RSK-03 | 单币种持仓限制 | `src/core/risk.py` | 符号级持仓限制 | 必选 | - |
| FR-RSK-04 | 最大回撤监控 | `src/core/risk.py`, `src/backtest/analyzers.py` | 回撤监控器 | 必选 | - |
| FR-RSK-05 | 止损机制与爆仓保护 | `src/core/risk.py`, `src/core/matching.py` | 风险处置逻辑 | 必选 | - |
| FR-BKT-01 | 集成 Backtrader Cerebro | `src/backtest/engine.py` | 回测引擎封装 | 必选 | - |
| FR-BKT-02 | 历史数据馈送与多品种多周期回测 | `src/data/feed.py`, `src/backtest/engine.py` | DataFeed 与回测装配 | 必选 | - |
| FR-BKT-03 | 回测配置映射（资金/费率/滑点/订单类型） | `config/config.yaml`, `src/backtest/engine.py` | 参数映射层 | 必选 | - |
| FR-BKT-04 | 标准分析器（Sharpe/Drawdown/Trade/Returns/TimeReturn） | `src/backtest/analyzers.py` | 分析器注册与输出 | 必选 | - |
| FR-BKT-05 | 回测报告与导出（CSV/JSON） | `src/backtest/exporter.py` | 报告生成器 | 必选 | - |
| FR-ANL-01 | 交易统计（次数/胜率/盈亏比） | `src/analysis/performance.py`, `src/analysis/performance_trade.py` | 通用性能分析入口与交易统计模块 | 必选 | - |
| FR-ANL-02 | 收益指标（总收益/年化/最大回撤/夏普/索提诺） | `src/analysis/performance.py` | 收益与风险指标模块（支持显式周期年化） | 必选 | - |
| FR-ANL-03 | 可视化报表（资金曲线/回撤/分布/持仓时间） | `src/analysis/visualization.py` | 图表输出模块 | 必选 | - |
| FR-LOG-01 | 交易/策略/错误日志分级记录 | `src/utils/logger.py` | 日志初始化与分流（终端+文件+轮转+脱敏） | 必选 | - |
| FR-LOG-02 | 实时监控（策略状态/资产变化/异常告警） | `src/live/monitor.py`, `src/cli.py`, `src/cli_commands.py` | 监控输出与查询接口 | 必选 | - |
| FR-CLI-01 | CLI 命令入口与常用命令 | `src/cli.py`, `src/cli_context.py`, `src/cli_commands.py`, `src/cli_order_commands.py`, `src/cli_workflows.py`, `main.py` | CLI 子命令集合 | 必选 | - |
| FR-WEB-01 | Web 界面（可选） | `web/`（预留） | Web 服务与仪表盘 | 可选 | Phase 0-4 当前交付不含 Web，优先保证 CLI 与双引擎闭环 |
| NFR-PERF-01 | 实时行情延迟 < 1 秒 | `src/data/market.py`, `src/live/simulator.py` | 性能基准脚本与报告 | 必选 | - |
| NFR-PERF-02 | 订单处理响应 < 100ms | `src/core/matching.py` | 性能压测脚本与结果 | 必选 | - |
| NFR-PERF-03 | 回测 1 年 1h 数据 < 10 秒（目标 <5 秒） | `src/backtest/engine.py` | 回测基准报告 | 必选 | - |
| NFR-PERF-04 | 支持 5+ 策略并行 | `src/live/simulator.py` | 并发运行验证 | 必选 | - |
| NFR-REL-01 | 异常处理机制完善 | 全模块 | 统一错误处理规范 | 必选 | - |
| NFR-REL-02 | 网络断线自动重连 | `src/data/market.py` | 重连策略与退避 | 必选 | - |
| NFR-REL-03 | 数据持久化保证 | `src/core/database.py` | 事务与恢复机制 | 必选 | - |
| NFR-REL-04 | 策略崩溃隔离 | `src/live/simulator.py` | 策略隔离执行器 | 必选 | - |
| NFR-EXT-01 | 模块化设计 | `src/` 分层结构 | 模块边界与接口文档 | 必选 | - |
| NFR-EXT-02 | 插件式策略架构 | `src/strategies/` | 策略注册机制 | 必选 | - |
| NFR-EXT-03 | 自定义指标支持 | `src/strategies/indicators/` | 指标扩展接口 | 必选 | - |
| NFR-EXT-04 | 新交易所接入能力 | `src/data/market.py` | 交易所适配扩展点 | 必选 | - |
| NFR-SEC-01 | API 密钥安全存储 | `config/.env.example`, `src/cli_context.py`, `src/utils/credential_vault.py` | 启动期主密钥校验 + 本地凭证加密存储 | 必选 | - |
| NFR-SEC-02 | 配置文件权限控制 | `config/` | 部署规范与检查脚本 | 必选 | - |
| NFR-SEC-03 | 日志脱敏处理 | `src/utils/logger.py` | 脱敏过滤器 | 必选 | - |
| TC-STACK-01 | Python 3.10+ 基线与依赖兼容 | `requirements.txt`, `pyproject`（可选） | 版本约束与安装说明 | 必选 | - |
| TC-STACK-02 | 核心依赖遵循技术栈文档 | `requirements.txt` | 锁定版本清单 | 必选 | - |
| TC-DATA-01 | 数据模型：accounts/orders/trades/strategy_runs | `src/core/database.py` | 数据库初始化脚本 | 必选 | - |
| TC-DATA-02 | 数据模型：positions/candles（含约束与索引） | `src/core/database.py` | 表结构与迁移脚本 | 必选 | - |
| TC-OPS-01 | 可观测性：日志与状态查询 | `src/utils/logger.py`, `src/live/monitor.py`, `src/cli.py`, `src/cli_context.py`, `src/cli_commands.py` | 状态命令、告警查询与日志策略 | 必选 | - |

## 新增约束项：数据路径约束（强制）

| ID | 约束 | 说明 | 范围 |
|---|---|---|---|
| DC-001 | write-path = SQLite | 运行态写入（行情 K 线、订单、成交、持仓、策略运行记录）统一落库 SQLite | 必选 |
| DC-002 | read-path（回测）= SQLite | 回测数据源必须从 SQLite 读取，不直接以 CSV/Parquet 作为运行态数据源 | 必选 |
| DC-003 | read-path（实时）= SQLite | 实时模式中的策略读取路径必须基于 SQLite 的统一查询接口 | 必选 |
| DC-004 | CSV/Parquet 仅用于 import/export/backup | CSV/Parquet 可作为导入、导出、备份介质；不得作为运行态主存储 | 必选 |

## 覆盖性检查
- 已覆盖 PRD 第 2 章全部功能需求（账户、行情、交易、策略、风控、回测、分析、日志监控、CLI/Web）。
- 已覆盖 PRD 第 4 章非功能需求（性能、可靠性、可扩展性、安全性）。
- 已补充实施计划要求的数据路径约束项（DC-001 ~ DC-004）。
- 已明确第 2 步范围收敛：当前交付仅 CLI + 模拟盘，Web 需求已保留但暂不纳入交付。

## 第2步验收检查（已通过）
- [x] 最小范围（MVP）已定义，且 In Scope 明确为 CLI + 模拟盘。
- [x] 可选项在追踪矩阵中可见，且 `FR-WEB-01` 已填写排除理由。
- [x] 未新增超范围条目（仍保持以 CLI 与双引擎闭环为主）。
- [x] 用户验证通过（2026-02-15）。

## 第3步验收检查（已通过）
- [x] 已按 `memory-bank/tech-stack.md` 创建推荐目录结构（`src/`、`config/`、`data/`、`logs/`、`tests/`）。
- [x] 已创建对应占位文件（仅空文件/占位，不含业务代码）。
- [x] 目录命名与文件命名和技术栈文档保持一致，无缺项。
- [x] 用户验证通过（2026-02-16）。

## 第4步验收检查（已通过）
- [x] `requirements.txt` 写入并锁定全部技术栈依赖与版本，无缺项、无额外依赖。
- [x] Python 基线要求（3.10+）已在依赖文件中明确标注。
- [x] 依赖列表与 `memory-bank/tech-stack.md` 逐项比对一致。
- [x] 用户验证通过（2026-02-16）。

## 第5步验收检查（已通过）
- [x] `config/config.yaml` 已写入系统、日志、交易所、账户、交易、风控、回测字段。
- [x] `config/strategies.yaml` 已写入内置策略参数模板（SMA / Grid / Bollinger）。
- [x] `config/.env.example` 已写入 API、数据库路径、日志级别环境变量模板。
- [x] 配置模板字段与 `memory-bank/tech-stack.md`、`memory-bank/CLAUDE.md`、PRD 描述逐项对齐，无缺漏。
- [x] 用户验证通过（2026-02-16）。

## 第6步验收检查（已通过）
- [x] 已实现配置加载优先级：`默认值 < YAML < 环境变量`（`src/utils/config.py`）。
- [x] 已实现配置校验规则（主配置与策略配置）并落地到 `src/utils/config_validation.py`。
- [x] 已实现默认值与环境变量映射集中定义（`src/utils/config_defaults.py`）。
- [x] 已新增优先级三场景测试与关键反例测试（`tests/test_config.py`）。
- [x] 用户验证通过（2026-02-16）。

## 第7步验收检查（已通过）
- [x] 已实现日志方案：分级、终端+文件、轮转、格式（`src/utils/logger.py`）。
- [x] 已实现日志分流：`main` / `strategy` / `trade` / `error` 文件通道。
- [x] 已实现敏感字段脱敏（`api_key`、`api_secret`、`token`、`password`、`secret`）。
- [x] 已新增日志自动化测试（`tests/test_logger.py`）与手工演练脚本（`tests/verify_step_7.py`）。
- [x] 已在说明文档记录日志方案与演练步骤（`README.md`）。
- [x] 用户验证通过（2026-02-16）。

## 第8步验收检查（已通过）
- [x] 已实现数据库连接生命周期（打开、关闭、事务）并落地到 `src/core/database.py`。
- [x] 数据库路径取自配置（`system.database_path`），支持通过配置构建数据库连接管理器。
- [x] 已完成打开/提交/回滚/关闭流程测试（`tests/test_database.py`），满足资源释放与事务边界要求。
- [x] 用户验证通过（2026-02-17）。

## 第9步验收检查（已通过）
- [x] 已在 `src/core/database.py` 定义并初始化六张核心表：`accounts`、`orders`、`trades`、`strategy_runs`、`positions`、`candles`。
- [x] `positions` 表约束与索引已落地：`UNIQUE(symbol)`、`CHECK(amount >= 0)`、`idx_positions_symbol(symbol)`。
- [x] `candles` 表约束与索引已落地：`UNIQUE(symbol, timeframe, timestamp)`、`idx_candles_symbol_time(symbol, timeframe, timestamp)`、`idx_candles_timestamp(timestamp)`。
- [x] 字段、UNIQUE、CHECK、索引与 `memory-bank/CLAUDE.md` 行 387–520 验收口径一致。
- [x] 已通过结构与约束自动化验证（`tests/test_database.py`，11 项通过）。
- [x] 用户验证通过（2026-02-17）。

## 第10步验收检查（已通过）
- [x] 已为账户、订单、交易、持仓、K 线、策略运行记录定义领域模型与 `validate` 规则。
- [x] 校验覆盖：必填字段、正数/非负数、比例区间、价格高低开收关系、时间戳非负与先后约束、订单 filled 不超 amount、非市价单必须提供 price、K 线 timeframe 白名单复用。
- [x] 引入枚举消除魔法字符串：订单类型/方向/状态、交易方向、策略运行状态。
- [x] 新增通用校验工具 `validation.py` 复用数值/时间戳/枚举校验。
- [x] 自动化测试 `tests/test_models.py` 覆盖正反例并通过；全量测试 `PYTHONPATH=. ./.venv/bin/pytest -q` 通过（33 passed）。

## 第11步验收检查（已通过）
- [x] 已实现 `AccountService` 账户生命周期管理（`src/core/account_service.py`）。
- [x] 支持多币种账户初始化（幂等）、余额查询、冻结/释放资金、消耗/增加可用余额。
- [x] 支持从 `positions` 表恢复持仓状态（`load_positions()`）。
- [x] 支持多币种总资产估值计算（`compute_total_assets()`），现金 + 持仓市值。
- [x] 修复 `require_timestamp()` 兼容 SQLite `datetime` 对象（第 11 步验证发现）。
- [x] 自动化测试 `tests/test_account.py` 覆盖 5 项验收测试；全量测试 38 passed。
- [x] 用户验证通过（2026-02-17）。

## 第12步验收检查（已通过）
- [x] 已实现 `OrderService` 订单持久化接口（`src/core/order_service.py`）。
- [x] 支持订单创建（`create_order()`）并冻结资金（买单），当调用方提供 `order_id` 时支持幂等性。
- [x] 支持订单查询（`get_order()` / `list_orders()`），按 ID、symbol、status、limit 过滤。
- [x] 支持订单状态更新（`update_order_status()`），含状态流转校验与部分成交时消耗冻结资金。
- [x] 支持拒单（REJECTED）释放冻结资金，避免资金长期占用。
- [x] `update_order_status()` 保持单层事务，移除嵌套 `with tx:`。
- [x] 支持订单撤销（`cancel_order()`）并释放剩余冻结资金，支持幂等性。
- [x] 实现订单状态机：定义合法流转表（PENDING→OPEN→PARTIALLY_FILLED→FILLED/CANCELED/REJECTED），拒绝非法状态转换。
- [x] 修复 `orders` 表时间戳字段类型（`TIMESTAMP` → `INTEGER`），避免 SQLite `PARSE_DECLTYPES` 冲突。
- [x] 自动化测试 `tests/test_order_service.py` 覆盖 24 项验收测试；全量测试 62 passed（3 warnings）。
- [x] 用户验证通过（2026-02-17）。

## 第13步验收检查（待验证）
- [x] 已实现成交记录服务 `TradeService`（`src/core/trade_service.py`），支持成交写入与订单关联。
- [x] 成交写入包含手续费字段、写入 `trades` 表并通过外键关联订单。
- [x] 成交写入更新订单 `filled` 与状态（部分成交→`partially_filled`，完全成交→`filled`），并对买单消费冻结资金。
- [x] `trades.timestamp` 统一为毫秒整数并提供默认值；新增索引 `idx_trades_order_id` 便于按订单查询成交记录。
- [x] 新增自动化测试 `tests/test_trade_service.py` 覆盖成交写入、状态更新、overfill 拒绝与缺失订单拒绝。
- [ ] 用户验证（等待安装依赖后运行测试）。

## 第14步验收检查（待验证）
- [x] 已实现市场数据接口 `MarketDataFetcher`（`src/data/market.py`），覆盖交易所选择、行情读取接口、错误重试与失败告知。
- [x] 已实现本地限流器 `RequestRateLimiter` 与错误分类重试策略（`src/data/market_retry.py`）。
- [x] 已实现策略约束与校验（`src/data/market_policy.py`）：`market_data.runtime_write_target` 仅允许 `sqlite`。
- [x] 已明确并固化约束：运行态写入目标仅 SQLite，`CSV/Parquet` 仅用于 import/export/backup。
- [x] 已新增接口设计文档 `memory-bank/market-data-interface-design.md` 记录异常处理策略与数据路径约束。
- [x] 已新增自动化测试 `tests/test_market_data.py`，覆盖限流、重试、失败告知与写入目标校验场景。
- [ ] 用户验证（等待你运行测试并确认通过）。

## 第15步验收检查（待验证）
- [x] 已实现历史 K 线下载与存储服务 `HistoricalCandleStorage`（`src/data/storage.py`）。
- [x] 已支持下载参数校验：`symbol`、`timeframe`、`start_timestamp`、`end_timestamp`、`batch_size`。
- [x] 已实现按时间范围分页下载并写入 SQLite `candles` 表（运行态写入路径不涉及 CSV/Parquet）。
- [x] 已实现 `build_dataset_name()` 命名规范（示例：`BTC_USDT_1h`）。
- [x] 已实现按 `symbol/timeframe/time range` 查询接口，结果按 `timestamp ASC` 返回。
- [x] 已新增自动化测试 `tests/test_storage.py`，覆盖分页下载、落库、时间序查询与异常输入校验。
- [ ] 用户验证（等待你运行测试并确认通过）。

## 第16步验收检查（待验证）
- [x] 已在 `src/data/storage.py` 增加历史请求缓存机制：同一 `symbol/timeframe/time range` 请求优先命中缓存，命中时不再重复下载。
- [x] 已增加 SQLite 持久化缓存表 `candle_download_cache`（`src/core/database.py`），支持跨服务实例缓存命中。
- [x] 已将 K 线写入改为 `INSERT OR IGNORE`，利用 `candles` 表 `UNIQUE(symbol, timeframe, timestamp)` 约束实现去重写入。
- [x] 已将 `downloaded_count` 调整为“本次实际新增记录数”，重复/重叠数据不会重复计数。
- [x] 已扩展自动化测试 `tests/test_storage.py`，覆盖重复请求缓存命中、重叠区间去重写入、跨实例缓存命中。
- [x] 本地自检通过：`PYTHONPATH=. ./.venv/bin/pytest -q tests/test_storage.py tests/test_database.py`（19 passed）。
- [ ] 用户验证（等待你运行测试并确认通过）。

## 第17步验收检查（待验证）
- [x] 已新增实时行情服务 `RealtimeMarketDataService`（`src/data/realtime_market.py`），提供 `get_latest_price()`、`get_depth()`、`get_klines()`。
- [x] 已增加超时控制：请求超时时返回统一结构并标记 `timed_out=True`。
- [x] 已增加错误兜底：请求失败时优先回退最近一次成功数据；无缓存时返回统一空结构与错误信息。
- [x] 已定义统一返回结构 `RealtimeMarketSnapshot`（`src/data/realtime_payloads.py`），确保最新价/深度/K 线接口字段一致。
- [x] 已新增自动化测试 `tests/test_realtime_market_data.py`，覆盖统一结构、超时与回退场景。
- [x] 本地自检通过：`PYTHONPATH=. ./.venv/bin/pytest -q tests/test_realtime_market_data.py tests/test_market_data.py`（10 passed）。
- [ ] 用户验证（等待你运行测试并确认通过）。

## 第18步验收检查（待验证）
- [x] 已新增价格服务 `PriceService`（`src/live/price_service.py`），用于“最新行情 → 持仓评估 → 资产估值”。
- [x] 已实现持仓评估：按最新价计算 `market_value` 与 `unrealized_pnl`，并回写 `positions.current_price/unrealized_pnl`。
- [x] 已实现估值汇总：输出 `PortfolioValuation`（`base_cash`、`positions_value`、`total_assets`）。
- [x] 已实现价格兜底规则：实时最新价缺失时回退到 `positions.current_price`，两者都缺失时抛错。
- [x] 已新增自动化测试 `tests/test_price_service.py`，覆盖手算一致性、兜底回退与缺价报错场景。
- [x] 本地自检通过：`PYTHONPATH=. ./.venv/bin/pytest -q tests/test_price_service.py tests/test_account.py tests/test_realtime_market_data.py`（12 passed）。
- [ ] 用户验证（等待你运行测试并确认通过）。

## 第19步验收检查（待验证）
- [x] 已实现市价单撮合引擎 `MatchingEngine`（`src/core/matching.py`），按最新价即时成交（`execute_market_order`）。
- [x] 已实现撮合闭环：创建市价单（`market`）→ 订单状态 `pending -> open -> filled` → 成交落库（`trades`）。
- [x] 已实现账户同步：
  - 买单：消费报价币资金并增加基础币可用余额。
  - 卖单：消费基础币可用余额并增加报价币可用余额。
- [x] 已实现持仓同步：
  - 买单：新建/加仓并重算加权 `entry_price`。
  - 卖单：减仓并更新 `realized_pnl` / `unrealized_pnl`。
- [x] 已新增自动化测试 `tests/test_matching.py`，覆盖最新价成交、固定价格序列可复算、缺价失败、卖出库存不足失败。
- [x] 本地自检通过：`PYTHONPATH=. ./.venv/bin/pytest -q tests/test_matching.py tests/test_trade_service.py tests/test_order_service.py`（29 passed）。
- [ ] 用户验证（等待你运行测试并确认通过）。

## 第20步验收检查（已通过）
- [x] 已新增限价撮合引擎 `LimitOrderMatchingEngine`（`src/core/limit_matching.py`），实现限价单挂单、队列查询与按 symbol 扫描撮合。
- [x] 已实现限价挂单队列管理：`place_limit_order()` 下单后状态进入 `open`，`list_open_limit_orders()` 按价格-时间优先级返回队列（买单价高优先、卖单价低优先、同价按创建时间）。
- [x] 已实现触发规则：买单在 `latest_price <= limit_price` 触发，卖单在 `latest_price >= limit_price` 触发；未触发订单保持挂单。
- [x] 已实现触发成交后的账户/持仓同步（通过 `src/core/limit_settlement.py`）：买单增加基础币并更新持仓均价，卖单减少基础币并增加报价币并更新已实现盈亏。
- [x] 已实现价格改善与差价返还：买单在市场价优于限价时按更优市场价成交，并将差价返还到报价币余额。
- [x] 已实现卖单库存预检：无持仓或可用仓位不足时，限价卖单在下单阶段直接拒绝，不进入挂单队列。
- [x] 已新增自动化测试 `tests/test_limit_matching.py`，覆盖：
  - 价格未跨越时保持挂单；
  - 价格跨越买单价触发成交；
  - 价格跨越卖单价触发成交；
  - 买单价格-时间优先级队列行为；
  - 买单价格改善差价返还；
  - 卖单库存预检拒单。
- [x] 本地自检通过：
  - `PYTHONPATH=. ./.venv/bin/pytest -q tests/test_limit_matching.py`（6 passed）
  - `PYTHONPATH=. ./.venv/bin/pytest -q tests/test_matching.py`（4 passed，回归通过）
- [x] 用户验证通过（2026-02-17）。

## 第21步验收检查（待验证）
- [x] 已新增止损/止盈触发引擎 `StopTriggerEngine`（`src/core/stop_trigger.py`），支持触发单创建与按 symbol 扫描触发（`process_trigger_orders`）。
- [x] 已实现触发规则：
  - `STOP_LOSS`：卖单 `latest <= trigger`，买单 `latest >= trigger`
  - `TAKE_PROFIT`：卖单 `latest >= trigger`，买单 `latest <= trigger`
- [x] 已实现与订单状态机联动：触发后通过 `TradeService.record_trade()` 推进订单状态（`open -> filled/partially_filled`）。
- [x] 已实现触发后账户与持仓同步：复用 `LimitOrderSettlement` 更新 `accounts` 与 `positions`。
- [x] 已实现卖向触发单库存前置校验：无库存时拒绝下单，不进入触发队列。
- [x] 已新增自动化测试 `tests/test_stop_trigger.py`，覆盖：
  - 未触发保持挂单；
  - 止损触发成交；
  - 止盈触发成交；
  - 买向止盈触发；
  - 卖向库存不足拒单。
- [x] 本地自检通过：
  - `PYTHONPATH=. ./.venv/bin/pytest -q tests/test_stop_trigger.py`（5 passed）
  - `PYTHONPATH=. ./.venv/bin/pytest -q tests/test_matching.py tests/test_limit_matching.py tests/test_stop_trigger.py`（15 passed）
- [ ] 用户验证（等待你运行测试并确认通过）。

## 第22步验收检查（待验证）
- [x] 已新增统一执行成本模型 `ExecutionCostProfile`（`src/core/execution_cost.py`），支持：
  - Maker/Taker 费率配置；
  - 买卖方向性滑点计算；
  - 限价边界保护滑点（不突破限价）。
- [x] 已在市价撮合 `src/core/matching.py` 接入 Taker 手续费与滑点，并写入 `trades.fee`。
- [x] 已在限价撮合 `src/core/limit_matching.py` 接入 Maker 手续费与滑点，并写入 `trades.fee`。
- [x] 已在止损/止盈触发 `src/core/stop_trigger.py` 接入 Taker 手续费与滑点，并写入 `trades.fee`。
- [x] 已新增第 22 步测试 `tests/test_execution_costs.py`，覆盖“已知参数下结果可复算”：
  - 市价（Taker）；
  - 限价（Maker，含限价边界保护）；
  - 触发单（Taker）。
- [x] 已保持第 19-21 步历史测试口径稳定：在相关测试构造器显式注入零费率零滑点配置。
- [x] 本地仅完成语法自检：`python -m compileall src tests/test_execution_costs.py`（通过）。
- [ ] 用户验证（等待你运行测试并确认通过；通过前不启动第 23 步）。

## 第23步验收检查（待验证）
- [x] 已新增订单状态机模块 `src/core/order_state_machine.py`：
  - 明确“新建（`pending`）/挂单（`open`）/部分成交/成交/撤单/拒单”状态集合；
  - 明确定义合法流转表 `VALID_ORDER_STATUS_TRANSITIONS`。
- [x] 已在 `src/core/order_service.py` 接入状态机：
  - `update_order_status()` 使用统一流转校验；
  - 撤单状态更新统一路由到 `cancel_order()`，保证买单冻结资金释放口径一致。
- [x] 已在 `src/core/trade_service.py` 接入状态机校验，防止绕过合法流转表直接写入非法订单状态。
- [x] 已新增自动化测试 `tests/test_order_state_machine.py`，覆盖：
  - 合法流转表逐条路径断言（含 `pending -> rejected`、`pending -> canceled`、`partially_filled -> partially_filled`）；
  - 非法流转拒绝断言；
  - 服务层关键路径（拒单、撤单资金释放、多次部分成交状态维持）。
- [x] 本地自检通过：
  - `PYTHONPATH=. ./.venv/bin/pytest -q tests/test_order_state_machine.py tests/test_order_service.py tests/test_trade_service.py`（44 passed）
- [ ] 用户验证（等待你运行测试并确认通过；通过前不启动第 24 步）。

## 第24步验收检查（待验证）
- [x] 已新增风控模块 `src/core/risk.py`，实现三项下单前检查：
  - 单笔仓位限制（`max_position_size`）；
  - 总仓位限制（`max_total_position`，按下单后预测仓位占比计算）；
  - 最大回撤限制（`max_drawdown`，超阈值拦截新买单）。
- [x] 已在三类下单入口接入风控前置拦截：
  - `src/core/matching.py`（市价单）；
  - `src/core/limit_matching.py`（限价单）；
  - `src/core/stop_trigger.py`（止损/止盈下单）。
- [x] 已实现拒单原因记录：风控拒单会抛出明确原因并写入交易日志通道。
- [x] 已新增自动化测试 `tests/test_risk_controls.py`，覆盖：
  - 单笔仓位超限拒单；
  - 总仓位超限拒单；
  - 最大回撤超限拒单。
- [x] 已完成本地回归自检：
  - `PYTHONPATH=. ./.venv/bin/pytest -q tests/test_risk_controls.py tests/test_matching.py tests/test_limit_matching.py tests/test_stop_trigger.py`（18 passed）；
  - `PYTHONPATH=. ./.venv/bin/pytest -q tests/test_execution_costs.py tests/test_order_state_machine.py`（22 passed）。
- [ ] 用户验证（等待你运行测试并确认通过；通过前不启动第 25 步）。

## 第25步验收检查（待验证）
- [x] 已实现策略生命周期基类 `LiveStrategy`（`src/strategies/base.py`），覆盖初始化、运行、停止、订单回调、成交回调。
- [x] 已定义生命周期上下文与回调载荷：
  - `StrategyContext`
  - `StrategyOrderEvent`
  - `StrategyTradeEvent`
- [x] 已实现生命周期状态守卫与异常 `StrategyLifecycleError`：
  - 未初始化前运行/回调会被拒绝；
  - 重复初始化会被拒绝；
  - 非运行态停止会被拒绝。
- [x] 已实现最小生命周期驱动器 `StrategyLifecycleDriver`（`src/live/simulator.py`），用于触发生命周期回调。
- [x] 已实现最小示例策略 `LifecycleProbeStrategy`（`src/strategies/lifecycle_demo_strategy.py`），用于验证回调触发顺序。
- [x] 已新增自动化测试 `tests/test_strategies.py`，覆盖：
  - 生命周期回调按顺序触发；
  - 未初始化前运行被拒绝；
  - 重复初始化被拒绝。
- [x] 已新增设计文档 `memory-bank/strategy-interface-lifecycle-design.md`，记录生命周期契约与验收映射。
- [x] 本地自检通过：`python -m compileall src/strategies src/live tests/test_strategies.py`。
- [ ] 用户验证（等待你运行测试并确认通过；通过前不启动第 26 步）。

## 第26步验收检查（已通过）

- [x] 已实现 Backtrader 回测引擎 `BacktestEngine`（`src/backtest/engine.py`），支持从配置构建并执行单次回测。
- [x] 已实现 SQLite → Pandas 数据馈送桥接（`src/data/feed.py`），通过 `pandas.DataFrame` 适配 `backtrader.feeds.PandasData`。
- [x] 已实现数据源强约束：`backtest.data_read_source` 仅允许 `sqlite`，拒绝 CSV/Parquet 运行态读取（`src/backtest/engine.py`、`src/utils/config_validation.py`）。
- [x] 已同步配置基线：`config/config.yaml` 与 `src/utils/config_defaults.py` 新增 `backtest.data_read_source: sqlite`。
- [x] 已新增自动化测试 `tests/test_backtest_engine.py`，覆盖：
  - SQLite 小样本回测可运行并产出基础统计；
  - 非 SQLite 数据源配置被拒绝；
  - 请求区间无数据时回测失败并报错。
- [x] 已新增配置校验测试：`tests/test_config.py::test_load_config_rejects_non_sqlite_backtest_data_read_source`。
- [x] 本地自检通过：
  - `PYTHONPATH=. ./.venv/bin/pytest -q tests/test_backtest_engine.py tests/test_config.py`（10 passed）。
- [x] 用户验证通过（2026-02-18）。

## 第27步验收检查（待验证）

- [x] 已实现分析器挂载模块 `AnalyzerMount`（`src/backtest/analyzers.py`），挂载 5 个标准分析器：
  - `SharpeRatio`：风险调整收益率；
  - `DrawDown`：最大回撤与回撤持续时间；
  - `TradeAnalyzer`：交易统计（总交易数、胜率、盈亏比等）；
  - `Returns`：周期收益分析；
  - `TimeReturn`：时间序列收益。
- [x] 已扩展 `BacktestRunResult`（`src/backtest/engine.py`），新增 3 个嵌套数据类：
  - `TradeStatistics`（9 字段）：总交易数、胜负交易数、胜率、盈亏比、平均盈亏、最大盈亏；
  - `RiskMetrics`（3 字段）：Sharpe 比率、最大回撤百分比、最大回撤持续天数；
  - `ReturnsAnalysis`（2 字段）：总收益、平均收益。
- [x] 已扩展 `BacktestRunResult`，新增 4 个分析器字段：
  - `trade_stats: TradeStatistics`
  - `risk_metrics: RiskMetrics`
  - `returns_analysis: ReturnsAnalysis`
  - `time_series_returns: dict[str, float]`（ISO 日期字符串 → 收益值）
- [x] 已更新 `BacktestEngine.run()` 方法：
  - 在 `cerebro.run()` 前挂载分析器；
  - 运行后提取分析器结果；
  - 转换为统一数据类结构。
- [x] 已新增 4 个结果转换方法：
  - `_build_trade_stats()`：处理无交易边界情况（返回零值而非报错）；
  - `_build_risk_metrics()`：处理 Sharpe 比率可能为 `None` 的情况；
  - `_build_returns_analysis()`：提取总收益与平均收益；
  - `_build_time_series()`：将 `datetime` 键转换为 ISO 字符串。
- [x] 已更新导出入口 `src/backtest/__init__.py`，导出 `AnalyzerMount`、`TradeStatistics`、`RiskMetrics`、`ReturnsAnalysis`。
- [x] 已新增自动化测试 `tests/test_backtest_analyzers.py`（304 行），覆盖：
  - 所有 5 个分析器产生输出且字段完整；
  - 无交易场景返回零值（不报错）；
  - Sharpe 比率在数据不足时为 `None`；
  - 时间序列键为 ISO 字符串、值为浮点数；
  - 所有数据类字段存在且完整。
- [x] 本地语法检查通过：`python -m compileall src/backtest/analyzers.py src/backtest/engine.py src/backtest/__init__.py tests/test_backtest_analyzers.py`。
- [ ] 用户验证（等待你运行测试并确认通过；通过前不启动第 28 步）。

## 第29步验收检查（已通过）

- [x] 已实现实时模拟主循环 `RealtimeSimulationLoop`（`src/live/realtime_loop.py`），实现完整闭环：行情拉取→持久化→估值→挂单处理→策略执行→信号执行→通知更新。
- [x] 已集成三个撮合引擎：`MatchingEngine`（市价单）、`LimitOrderMatchingEngine`（限价单）、`StopTriggerEngine`（止损/止盈）。
- [x] 已实现运行态 K 线持久化到 SQLite `candles` 表（`_persist_latest_candle`），符合 DC-001 约束。
- [x] 已确认 CSV/Parquet 不参与运行态读写，符合 DC-003/DC-004 约束。
- [x] 已实现策略信号执行：支持 market/limit/stop_loss/take_profit 四种订单类型。
- [x] 已实现容错机制：市场数据失败、策略执行失败、通知失败均不中断循环。
- [x] 已实现 `from_config()` 工厂方法，支持从配置字典构建循环实例。
- [x] 已完成模块化重构：拆分为 `realtime_loop.py`（252行）、`loop_models.py`（34行）、`loop_signal_executor.py`（136行），均符合 <300 行约束。
- [x] 已新增 8 项自动化测试 `tests/test_realtime_loop.py`，覆盖初始化、行情拉取、K 线持久化、信号执行、错误处理、迭代控制、工厂方法。
- [x] 全量测试通过：`170 passed, 54 warnings`。
- [x] 用户验证通过（2026-02-19）。

## 第30步验收检查（已通过）

- [x] 已实现策略适配器 `BacktraderAdapter`（`src/strategies/adapter.py`），采用 "Run-on-Audit" 模式运行。
- [x] 适配器支持通过 `warmup_candles` 参数加载预热历史数据。
- [x] 输出信号与 `RealtimeSimulationLoop` 兼容，包含 `amount` 和映射的 `type`，正确拦截当前 bar 的 `buy/sell/close` 动作。
- [x] 已新增自动化测试 `tests/test_strategy_adapter.py`（13项测试），充分测试了预热流、历史数据隔离以及与 Backtrader 产生的信号一致性。
- [x] 代码和测试已通过全量回归（183 passed, 0 failed）。
- [x] 用户验收已通过（包含各项 P0-P2 修复验证）。

## 第35步验收检查（已通过）

- [x] 已实现通用性能分析模块 `src/analysis/performance.py`，支持基于 `equity_curve` 或 `returns_series` 的统一分析入口。
- [x] 已按策略要求引入显式周期参数：`returns_series` 路径强制要求 `period_seconds`，缺失时拒绝执行。
- [x] 已修复资金曲线重建口径：删除“平均间隔回推 T0”与“单点回退 1 天”逻辑，改为 `t0 = first_timestamp - period_seconds` 并补齐初始本金基准点。
- [x] 已新增时间间隔一致性校验：`returns_series` 相邻时间戳间隔与 `period_seconds` 不一致时直接报错，避免年化与 Sharpe 失真。
- [x] 已按单文件约束拆分模块：
  - `src/analysis/performance_trade.py`（交易统计）
  - `src/analysis/performance_errors.py`（异常定义）
  - `src/analysis/performance.py`（分析编排，当前 297 行）
- [x] 已更新自动化测试 `tests/test_performance_analysis.py`，覆盖：
  - `annualized_return` 与 `sharpe_ratio` 在 `returns_series` 重建路径下的断言；
  - 缺失 `period_seconds` 报错；
  - 时间间隔与 `period_seconds` 不匹配报错。
- [x] 本地自检通过：
  - `PYTHONPATH=. ./.venv/bin/pytest -q tests/test_performance_analysis.py`（6 passed）
  - `PYTHONPATH=. ./.venv/bin/pytest -q`（213 passed, 54 warnings）
- [x] 用户验证通过（2026-02-21）。

## 第36步验收检查（已通过）

- [x] 已实现可视化导出模块 `src/analysis/visualization.py`，支持导出资金曲线、回撤曲线、交易盈亏分布、持仓时间分布四类图像。
- [x] 已实现统一导出入口 `PerformanceVisualizer.export_all()`，一次调用返回 4 个产物路径（`VisualizationArtifacts`）。
- [x] 已兼容回测与实时输入结构：
  - 资金曲线支持 `Mapping[timestamp, equity]` 与 `Sequence[(timestamp, equity)]`；
  - 交易明细支持 `dict` 与对象结构。
- [x] 已实现交易与持仓分布的多字段回退提取：`pnl_net/pnl_gross`、`holding_seconds/minutes/hours`、`entry_time/exit_time` 推导。
- [x] 已固定 `matplotlib` `Agg` 后端，保证无头环境可导出图片。
- [x] 已新增异常类型 `VisualizationError`，覆盖输入校验与文件导出失败语义。
- [x] 已更新导出入口 `src/analysis/__init__.py`，公开 `PerformanceVisualizer`、`VisualizationArtifacts`、`VisualizationError`。
- [x] 已新增自动化测试 `tests/test_visualization.py`，覆盖导出成功、空交易场景、回撤计算与输入校验报错。
- [x] 已补充 `datetime` 时间戳兼容修复：
  - `src/analysis/visualization.py` 与 `src/analysis/performance.py` 的 `_parse_timestamp` 均支持 Python 原生 `datetime`；
  - naive 时间按 `UTC` 解释，避免时区未指定导致的运行时异常。
- [x] 已补充两条正式 pytest 回归用例：
  - `tests/test_visualization.py::test_export_all_accepts_datetime_timestamps`
  - `tests/test_performance_analysis.py::test_returns_series_accepts_datetime_timestamps`
- [x] 本地自检通过：
  - `PYTHONPATH=. ./.venv/bin/pytest -q tests/test_visualization.py tests/test_performance_analysis.py`（12 passed）
  - `PYTHONPATH=. ./.venv/bin/pytest -q`（219 passed, 54 warnings）
- [x] 用户验证通过（2026-02-21）。

## 第37步验收检查（已通过）

- [x] 已实现 CLI 命令集合并拆分处理器：`src/cli.py`、`src/cli_context.py`、`src/cli_commands.py`、`src/cli_order_commands.py`、`src/cli_workflows.py`。
- [x] 已覆盖实施计划要求命令：`start/startup`、`stop`、`status --disk`、`balance`、`positions`、`order place/list/cancel`、`backtest`、`download`、`live`、`import`、`export`、`cleanup`、`reconcile`。
- [x] 已完成参数校验与帮助信息：缺少必填参数时由 `argparse` 返回可解释错误（退出码 2），命令级条件参数执行显式报错。
- [x] 已实现运行状态文件：`runtime_state.json` 存储在 `system.data_dir`，由 `start/stop/status` 共享。
- [x] 已补充显式回归断言：`backtest --output-dir` 同时导出 6 个报告文件与 4 张图表文件。
- [x] 已新增自动化测试：
  - `tests/test_cli_runtime.py`
  - `tests/test_cli_workflows.py`
- [x] 本地自检通过：
  - `PYTHONPATH=. ./.venv/bin/pytest -q tests/test_cli_runtime.py tests/test_cli_workflows.py`（18 passed）
  - `PYTHONPATH=. ./.venv/bin/pytest -q`（237 passed, 54 warnings）
- [x] 用户验证通过（2026-02-21）。

## 第38步验收检查（已通过）

- [x] 已实现运行监控模块 `src/live/monitor.py`，统一持久化 `monitor_state.json`：
  - 策略状态：`strategy.status/iteration_count/last_error/started_at_ms/stopped_at_ms`；
  - 账户快照：`account.total_assets/base_cash/positions_value`；
  - 告警与计数器：`alerts`、`alerts_total`、`network_errors`、`reconnect_attempts`、`strategy_errors`。
- [x] 已在 `src/live/realtime_loop.py` 集成监控与告警：
  - 每轮迭代写入 `iteration_count` 与 `last_tick_ms`；
  - 网络异常、估值异常、策略异常、信号执行异常、通知异常均记录为监控告警；
  - 策略异常改为“记录告警后继续下一轮”，实现崩溃隔离。
- [x] 已在 CLI 增加状态查询能力：
  - `src/cli.py` 增加 `status --alerts` 参数；
  - `src/cli_commands.py` 的 `status` 输出监控摘要与凭证加密状态，`--alerts` 输出最近告警列表；
  - `src/cli_context.py` 增加 `read_monitor_state()` 与 `credential_storage_status()`。
- [x] 已实现 API 凭证加密存储：
  - 新增 `src/utils/credential_vault.py`，加密写入 `system.data_dir/secure/exchange_credentials.enc.json`；
  - `build_context()` 启动阶段执行凭证持久化校验；
  - 配置存在 API 凭证但缺失 `CONFIG_MASTER_KEY` 时，显式拒绝启动并给出可解释错误；
  - 补充“Vault 存在但缺失 `CONFIG_MASTER_KEY`”的 fail-fast 场景，避免运行时鉴权延迟失败；
  - `config/.env.example` 已补充 `CONFIG_MASTER_KEY` 模板项。
- [x] 已修复运行态 K 线写入口径：
  - `src/live/realtime_loop.py` 的 `_persist_latest_candle()` 改为按 `timeframe` 分箱；
  - 同时间桶采用 `ON CONFLICT` 聚合更新 `high/low/close`，保留首笔 `open`，避免 tick 级数据膨胀。
- [x] 已补充第 38 步自动化测试：
  - `tests/test_monitoring.py`：监控状态查询、告警输出、凭证加密、日志脱敏、网络重试恢复、策略崩溃隔离；
  - `tests/test_cli_runtime.py`：新增 `status --alerts` 回归。
  - `tests/test_cli_context_credentials.py`：Vault 缺主密钥失败、凭证回填成功。
  - `tests/test_realtime_candle_bucketing.py`：K 线分箱与 OHLC 合并。
- [x] 本地自检通过：
  - `PYTHONPATH=. ./.venv/bin/pytest -q`（247 passed, 54 warnings）
- [x] 用户验证通过（2026-02-21）。
