# Architecture Notes

## 当前阶段定位（2026-02-17）
- 仓库已完成 `implementation-plan.md` Phase 0 第 1-7 条，Phase 1 第 8-12 条：订单持久化接口。
- 当前处于"Phase 1 进行中、待进入第 13 步"阶段：订单服务已通过验收（`OrderService`），交易记录写入尚未开始。
- 最小交付范围仍锁定为 CLI + 模拟盘（回测与实时模拟），Web 能力保留为可选项且暂不交付。
- **第 11 步验证发现与修复**：`require_timestamp()` 原先仅接受数值类型，但 SQLite `PARSE_DECLTYPES` 将 `TIMESTAMP` 列解析为 `datetime` 对象，导致测试失败。已修复 `src/core/validation.py` 兼容三种时间戳来源（数值、`datetime` 对象、ISO 字符串），全量测试 38 passed。
- **第 12 步实现与修复**：实现订单持久化服务（`OrderService`），修复 `orders` 表时间戳字段类型（`TIMESTAMP` → `INTEGER`），实现完整的订单状态机与资金管理（冻结/消耗/释放），补齐 REJECTED 释放冻结资金与单层事务边界，订单服务测试 24 项，全量测试 62 passed（3 warnings）。

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
- 作用：里程碑执行日志，记录“做了什么、做到哪、何时通过、下一步边界”。
- 依赖关系：引用 `implementation-plan.md` 的步骤状态，并回链到追踪清单。

### `memory-bank/findings.md`
- 作用：知识沉淀与决策档案，按固定模板记录需求、发现、决策、问题、资源。
- 依赖关系：吸收来自 PRD、实施计划、追踪清单、进度日志的关键信息，供后续开发者快速接手。

### `memory-bank/architecture.md`
- 作用：架构认知与文档关系说明，解释当前系统边界和每份文档职责。
- 依赖关系：在每个关键里程碑后回写，确保架构认知与执行状态同步。

## 文档关系与执行链路
1. `product-requirement-document.md` 定义“要做什么”。
2. `implementation-plan.md` 定义“按什么顺序做、如何验收”。
3. `requirements-traceability-checklist.md` 定义“每条需求落到哪里、当前是否在范围内”。
4. `progress.md` 记录“当前做到哪一步、是否通过验收”。
5. `findings.md` 记录“为什么这样做、遇到什么问题、依据是什么”。
6. `architecture.md` 解释“上述文档如何共同构成当前架构基线”。

## 工程骨架与基础实现文件作用（第 3-12 步）
- `src/core/*.py`：核心业务域实现入口（账户、订单、撮合、数据库、领域模型校验）；其中 `database.py` 已落地生命周期管理与 schema 初始化（六表、约束、索引，`orders` 表时间戳字段已修正为 `INTEGER` 类型），`enums.py`/`validation.py`/`account.py`/`order.py`/`trade.py`/`position.py`/`candle.py`/`strategy_run.py` 已完成领域模型与校验规则（`validation.py` 已修复 `require_timestamp()` 兼容 SQLite `datetime` 对象），`account_service.py` 已实现账户初始化、余额管理、持仓恢复与总资产估值，`order_service.py` 已实现订单持久化接口（创建、查询、状态更新、撤销）与完整的资金管理（冻结/消耗/释放），第 13 步以后可直接复用；`matching.py` 等其余模块为后续 Phase 1-2 承接点。
- `src/data/*.py`：数据接入与存储占位（市场数据、历史数据），用于承接 Phase 1 与 Phase 2。
- `src/strategies/*.py`：策略接口与内置策略占位，用于承接 Phase 3。
- `src/backtest/*.py`：回测引擎与分析器占位，用于承接 Phase 3。
- `src/live/*.py`：实时模拟主循环占位，用于承接 Phase 3。
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
- `tests/test_order_service.py`：第 12 步订单服务测试（21 项验收测试），用于支撑 Phase 1 第 12 条自动化验证。
- `tests/*.py`（其余）：测试模块占位，用于承接 Phase 4 第 39 条。
- `requirements.txt`：当前仓库依赖清单入口（安装/CI 统一来源）；后续若恢复严格锁定版本，应与 Phase 0 第 4 条验收口径保持一致。
- `README.md`：补充第 7 步日志方案说明与手工演练步骤，作为日志策略落地说明文档。
- `main.py`：程序入口占位，用于承接 CLI 与运行编排接入。

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
  - 实现完整的资金管理：买单创建时冻结资金，部分成交时消耗冻结资金（从 frozen 和 balance 同时扣除），取消或 REJECTED 时释放剩余冻结资金。
  - 支持幂等性：当调用方提供 `order_id` 时重复创建返回现有订单；重复取消已终态订单返回当前状态。
  - `update_order_status()` 保持单层事务，移除嵌套 `with tx:`。
  - 全量测试 62 passed（3 warnings，含 `test_order_service` 24 项 + 之前 38 项）。
