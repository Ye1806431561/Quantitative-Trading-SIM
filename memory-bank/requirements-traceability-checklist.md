# 需求追踪清单（Phase 0-1 / Step 1-10）

## 说明
- 来源文档：`memory-bank/product-requirement-document.md`
- 目标：将需求逐项映射到模块与交付物，并标记范围（必选/可选）
- 状态：已完成实施计划第 1-10 步，且第 10 步已验证通过（第 11 步未开始）

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
| FR-ACC-04 | 查看当前持仓 | `src/core/position.py`, `src/cli.py` | 持仓查询接口与 CLI 展示 | 必选 | - |
| FR-ACC-05 | 查看可用余额/冻结资金/总资产估值 | `src/core/account.py`, `src/cli.py` | 账户查询命令 | 必选 | - |
| FR-MKT-01 | 通过 CCXT 获取实时行情 | `src/data/market.py` | 市场数据客户端 | 必选 | - |
| FR-MKT-02 | 支持多个主流交易所 | `src/data/market.py`, `config/config.yaml` | 交易所适配与配置项 | 必选 | - |
| FR-MKT-03 | 实时价格/深度/K 线获取 | `src/data/market.py` | 行情查询接口 | 必选 | - |
| FR-MKT-04 | 历史 K 线下载与存储 | `src/data/storage.py`, `src/core/database.py` | 下载器与持久化接口 | 必选 | - |
| FR-MKT-05 | 多时间周期支持（1m/5m/15m/1h/4h/1d） | `src/data/storage.py` | 周期枚举与校验 | 必选 | - |
| FR-MKT-06 | 本地数据缓存机制 | `src/data/storage.py` | 去重与增量下载逻辑 | 必选 | - |
| FR-ORD-01 | 订单类型：市价单 | `src/core/order.py`, `src/core/matching.py` | 市价单模型与撮合流程 | 必选 | - |
| FR-ORD-02 | 订单类型：限价单 | `src/core/order.py`, `src/core/matching.py` | 限价挂单与触发撮合 | 必选 | - |
| FR-ORD-03 | 订单类型：止损单 | `src/core/order.py`, `src/core/matching.py` | 止损触发规则 | 必选 | - |
| FR-ORD-04 | 订单类型：止盈单 | `src/core/order.py`, `src/core/matching.py` | 止盈触发规则 | 必选 | - |
| FR-ORD-05 | 下单/撤单/状态查询/历史记录 | `src/core/order.py`, `src/cli.py` | 订单服务与 CLI 命令 | 必选 | - |
| FR-MCH-01 | 模拟撮合（基于实时价格） | `src/core/matching.py` | 撮合引擎 | 必选 | - |
| FR-MCH-02 | 限价单队列管理 | `src/core/matching.py` | 队列与撮合状态机 | 必选 | - |
| FR-MCH-03 | 滑点模拟可配置 | `src/core/matching.py`, `config/config.yaml` | 滑点参数与计算器 | 必选 | - |
| FR-MCH-04 | Maker/Taker 手续费计算 | `src/core/matching.py`, `src/core/trade.py` | 费用计算与落库 | 必选 | - |
| FR-STR-01 | 统一策略接口规范 | `src/strategies/base.py` | 策略抽象基类 | 必选 | - |
| FR-STR-02 | 生命周期管理（初始化/运行/停止） | `src/strategies/base.py`, `src/live/simulator.py` | 生命周期调度器 | 必选 | - |
| FR-STR-03 | 多策略并行支持 | `src/live/simulator.py` | 策略调度容器 | 必选 | - |
| FR-STR-04 | 策略适配器（回测/实时转换） | `src/strategies/adapter.py` | 双引擎适配层 | 必选 | - |
| FR-STR-05 | 回测策略继承 `backtrader.Strategy` | `src/backtest/engine.py`, `src/strategies/*.py` | 回测策略模板 | 必选 | - |
| FR-STR-06 | 实时策略继承 `LiveStrategy` | `src/strategies/base.py`, `src/live/simulator.py` | 实时策略模板 | 必选 | - |
| FR-STR-07 | 内置策略：SMA / 网格 / 布林带 | `src/strategies/sma_strategy.py`, `src/strategies/grid_strategy.py`, `src/strategies/bollinger_strategy.py` | 三个内置策略模块 | 必选 | - |
| FR-STR-08 | 策略参数配置与优化接口 | `config/strategies.yaml`, `src/backtest/optimizer.py` | 参数加载与优化入口 | 必选 | - |
| FR-RSK-01 | 单笔交易最大金额限制 | `src/core/risk.py` | 下单前风控检查 | 必选 | - |
| FR-RSK-02 | 总仓位比例控制 | `src/core/risk.py` | 总仓位限制规则 | 必选 | - |
| FR-RSK-03 | 单币种持仓限制 | `src/core/risk.py` | 符号级持仓限制 | 必选 | - |
| FR-RSK-04 | 最大回撤监控 | `src/core/risk.py`, `src/backtest/analyzers.py` | 回撤监控器 | 必选 | - |
| FR-RSK-05 | 止损机制与爆仓保护 | `src/core/risk.py`, `src/core/matching.py` | 风险处置逻辑 | 必选 | - |
| FR-BKT-01 | 集成 Backtrader Cerebro | `src/backtest/engine.py` | 回测引擎封装 | 必选 | - |
| FR-BKT-02 | 历史数据馈送与多品种多周期回测 | `src/data/feed.py`, `src/backtest/engine.py` | DataFeed 与回测装配 | 必选 | - |
| FR-BKT-03 | 回测配置映射（资金/费率/滑点/订单类型） | `config/config.yaml`, `src/backtest/engine.py` | 参数映射层 | 必选 | - |
| FR-BKT-04 | 标准分析器（Sharpe/Drawdown/Trade/Returns/TimeReturn） | `src/backtest/analyzers.py` | 分析器注册与输出 | 必选 | - |
| FR-BKT-05 | 回测报告与导出（CSV/JSON） | `src/backtest/report.py` | 报告生成器 | 必选 | - |
| FR-ANL-01 | 交易统计（次数/胜率/盈亏比） | `src/backtest/analyzers.py`, `src/analysis/metrics.py` | 统计指标模块 | 必选 | - |
| FR-ANL-02 | 收益指标（总收益/年化/最大回撤/夏普/索提诺） | `src/analysis/metrics.py` | 收益指标模块 | 必选 | - |
| FR-ANL-03 | 可视化报表（资金曲线/回撤/分布/持仓时间） | `src/analysis/visualization.py` | 图表输出模块 | 必选 | - |
| FR-LOG-01 | 交易/策略/错误日志分级记录 | `src/utils/logger.py` | 日志初始化与分流（终端+文件+轮转+脱敏） | 必选 | - |
| FR-LOG-02 | 实时监控（策略状态/资产变化/异常告警） | `src/live/monitor.py`, `src/cli.py` | 监控输出与查询接口 | 必选 | - |
| FR-CLI-01 | CLI 命令入口与常用命令 | `src/cli.py`, `main.py` | CLI 子命令集合 | 必选 | - |
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
| NFR-SEC-01 | API 密钥安全存储 | `.env`, `src/utils/config.py` | 环境变量加载与脱敏 | 必选 | - |
| NFR-SEC-02 | 配置文件权限控制 | `config/` | 部署规范与检查脚本 | 必选 | - |
| NFR-SEC-03 | 日志脱敏处理 | `src/utils/logger.py` | 脱敏过滤器 | 必选 | - |
| TC-STACK-01 | Python 3.10+ 基线与依赖兼容 | `requirements.txt`, `pyproject`（可选） | 版本约束与安装说明 | 必选 | - |
| TC-STACK-02 | 核心依赖遵循技术栈文档 | `requirements.txt` | 锁定版本清单 | 必选 | - |
| TC-DATA-01 | 数据模型：accounts/orders/trades/strategy_runs | `src/core/database.py` | 数据库初始化脚本 | 必选 | - |
| TC-DATA-02 | 数据模型：positions/candles（含约束与索引） | `src/core/database.py` | 表结构与迁移脚本 | 必选 | - |
| TC-OPS-01 | 可观测性：日志与状态查询 | `src/utils/logger.py`, `src/cli.py` | 状态命令与日志策略 | 必选 | - |

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
