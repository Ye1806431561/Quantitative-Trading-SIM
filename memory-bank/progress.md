# Progress Log

## 2026-02-15

### 本次目标
- 执行 `implementation-plan.md` 第 1 步：建立需求追踪清单，并满足该步验收标准。

### 已完成事项
- 完整阅读 `memory-bank/` 现有文档：
  - `memory-bank/CLAUDE.md`
  - `memory-bank/product-requirement-document.md`
  - `memory-bank/implementation-plan.md`
  - `memory-bank/tech-stack.md`
  - `memory-bank/findings.md`
  - `memory-bank/progress.md`
  - `memory-bank/architecture.md`
- 新增 `memory-bank/requirements-traceability-checklist.md`，完成以下内容：
  - 将 PRD 功能需求与非功能需求逐项映射到模块归属与交付物。
  - 为每项需求标记范围（`必选` / `可选`）。
  - 增加并明确“数据路径约束”：
    - `write-path = SQLite`
    - `read-path(回测) = SQLite`
    - `read-path(实时) = SQLite`
    - `CSV/Parquet` 仅用于 `import/export/backup`
  - 添加覆盖性检查说明，确认覆盖 PRD 第 2 章与第 4 章关键条目。

### 验收状态
- 第 1 步文档已由用户验证通过。
- 按要求未开始第 2 步实现与范围收敛。

### 交接备注
- 后续开发请以 `memory-bank/requirements-traceability-checklist.md` 作为需求追踪基线。
- 第 2 步开始前，保持当前范围边界不变（仅记录，不扩展实现）。

## 2026-02-15（第 2 步）

### 本次目标
- 执行 `implementation-plan.md` Phase 0 第 2 条：明确最小可用范围（仅 CLI + 模拟盘，不含 Web），并在用户验证通过后完成文档联动更新。

### 已完成事项
- 更新 `memory-bank/requirements-traceability-checklist.md`：
  - 新增“最小可用范围（MVP）定义”。
  - 在追踪矩阵新增“排除理由（仅可选项必填）”列。
  - 对 `FR-WEB-01` 明确排除理由：Phase 0-4 当前交付不含 Web，优先保证 CLI 与双引擎闭环。
  - 新增“第2步验收检查”并在用户回复“通过”后标记为已通过。
- 用户已完成第 2 步验证（2026-02-15）。
- 验证通过后联动更新以下文档，供后续开发者接力：
  - `memory-bank/progress.md`
  - `memory-bank/architecture.md`
  - `memory-bank/findings.md`
  - `memory-bank/requirements-traceability-checklist.md`

### 验收状态
- Phase 0 第 2 条已验证通过。
- 仍未开始第 3 步（保持执行边界）。

### 交接备注
- 下一步可按 `implementation-plan.md` 进入后续实施，但需继续遵循“先文档约束、后实现”的节奏。
- 若后续范围发生变化，应先回写 `memory-bank/requirements-traceability-checklist.md` 再推进实现。

## 2026-02-16（第 3 步）

### 本次目标
- 执行 `implementation-plan.md` Phase 0 第 3 条：按技术栈推荐结构创建目录与占位文件（不含代码），并在用户验证通过后更新交接文档。

### 已完成事项
- 阅读并复核 `memory-bank/` 全部文档，确认第 3 步验收目标与命名约束。
- 创建项目骨架目录：
  - `src/`（`core/`、`data/`、`strategies/`、`backtest/`、`live/`、`utils/`）
  - `config/`
  - `data/database/`
  - `data/historical/`
  - `logs/`
  - `tests/`
- 创建占位文件（无业务代码）：
  - `src` 分层模块占位（含 `__init__.py`、`cli.py`、各模块文件）
  - `config/config.yaml`、`config/strategies.yaml`、`config/.env.example`
  - `tests/test_account.py`、`tests/test_matching.py`、`tests/test_strategies.py`
  - `requirements.txt`、`.env`、`.gitignore`、`README.md`、`main.py`
  - `.gitkeep`：`data/database/.gitkeep`、`data/historical/.gitkeep`、`logs/.gitkeep`
- 与 `memory-bank/tech-stack.md` 推荐目录逐项比对，确认目录/文件命名一致、无缺项。
- 你已确认第 3 步“通过”（2026-02-16）。
- 验证通过后完成文档联动更新：
  - `memory-bank/progress.md`
  - `memory-bank/architecture.md`
  - `memory-bank/findings.md`
  - `memory-bank/requirements-traceability-checklist.md`

### 验收状态
- Phase 0 第 3 条已验证通过。
- 第 4 步尚未开始（按你的流程控制执行）。

### 交接备注
- 当前仓库已从“纯文档阶段”进入“骨架就绪阶段”，可直接进入第 4 步依赖清单落地。
- 第 4 步开始前，应先确认 `requirements.txt` 仅包含技术栈指定依赖与版本。

## 2026-02-16（第 4 步）

### 本次目标
- 执行 `implementation-plan.md` Phase 0 第 4 条：写入依赖清单，锁定指定版本并保存于 `requirements.txt`，确保与 `memory-bank/tech-stack.md` 一致且 Python 基线 3.10+。

### 已完成事项
- 复核 `memory-bank/tech-stack.md` 的完整依赖列表与版本号。
- 在 `requirements.txt` 写入并锁定依赖：
  - 核心交易：`ccxt==4.2.0`、`backtrader==1.9.78.123`
  - 数据处理：`pandas==2.1.0`、`numpy==1.26.0`
  - 配置：`pyyaml==6.0.1`、`python-dotenv==1.0.0`
  - 日志与 CLI：`loguru==0.7.2`、`rich==13.7.0`
  - 可视化：`matplotlib==3.8.0`
  - 开发工具（可选）：`pytest==7.4.3`、`pytest-asyncio==0.21.1`、`black==23.12.0`
- 在文件顶部标注 Python 基线 `3.10+`。
- 与技术栈文档逐项核对，确认无缺项、无额外依赖。

### 验收状态
- Phase 0 第 4 条已完成并经你验证“通过”（2026-02-16）。
- 按约定未开始第 5 步，等待后续指令。

### 交接备注
- `requirements.txt` 现为依赖与版本的单一可信源，后续安装或 CI 应以此为准。
- 配置模板与加载优先级（Phase 0 第 5-6 条）尚未开始，保持现有占位文件不动。

## 2026-02-16（第 5 步）

### 本次目标
- 执行 `implementation-plan.md` Phase 0 第 5 条：创建配置模板（`config.yaml`、`strategies.yaml`、`.env.example`），并保证字段与文档一致。

### 已完成事项
- 完整阅读并复核 `memory-bank/` 全部文档，确认第 5 步字段基线来源：
  - `memory-bank/CLAUDE.md`
  - `memory-bank/product-requirement-document.md`
  - `memory-bank/implementation-plan.md`
  - `memory-bank/tech-stack.md`
  - `memory-bank/findings.md`
  - `memory-bank/progress.md`
  - `memory-bank/architecture.md`
  - `memory-bank/requirements-traceability-checklist.md`
- 完成配置模板落地：
  - `config/config.yaml`：写入系统、日志、交易所、账户、交易、风控、回测配置字段。
  - `config/strategies.yaml`：写入内置策略模板参数（`sma_strategy`、`grid_strategy`、`bollinger_strategy`）。
  - `config/.env.example`：写入 API、数据库路径、日志级别环境变量模板。
- 逐字段对照文档模板与约束，确认配置字段完整且无越界新增。
- 你已确认第 5 步“通过”（2026-02-16）。
- 验证通过后完成文档联动更新：
  - `memory-bank/progress.md`
  - `memory-bank/architecture.md`
  - `memory-bank/findings.md`
  - `memory-bank/requirements-traceability-checklist.md`

### 验收状态
- Phase 0 第 5 条已验证通过。
- 第 6 步（配置加载优先级与校验规则）尚未开始。

### 交接备注
- 当前三份配置模板已可作为 Phase 0 第 6 条的输入基线。
- 下一步应仅实现“默认值 < YAML < 环境变量”的加载优先级与校验规则，不修改第 5 步字段范围。

## 2026-02-16（第 6 步）

### 本次目标
- 执行 `implementation-plan.md` Phase 0 第 6 条：设计并实现配置加载优先级（`默认值 < YAML < 环境变量`），并落地校验规则。

### 已完成事项
- 完整阅读并复核 `memory-bank/` 全部文档，确认第 6 步边界与验收口径。
- 完成配置加载与优先级实现（不扩展第 5 步字段范围）：
  - `src/utils/config.py`：
    - 提供 `load_config()`（运行配置）与 `load_strategies_config()`（策略配置）。
    - 实现加载顺序：默认值 → YAML 覆盖 → 环境变量覆盖。
    - 增加 YAML 根节点类型检查与未知字段拒绝（防止越界配置）。
  - `src/utils/config_defaults.py`：
    - 固化 `DEFAULT_CONFIG` 与 `DEFAULT_STRATEGIES_CONFIG`。
    - 固化环境变量覆盖映射：`LOG_LEVEL`、`DATABASE_PATH`、`EXCHANGE_API_KEY`、`EXCHANGE_API_SECRET`。
  - `src/utils/config_validation.py`：
    - 实现主配置校验（类型、必填、取值范围、风控关系约束、timeframe 白名单）。
    - 实现策略配置校验（SMA 快慢线关系、参数范围、布林/网格参数合法性）。
- 新增 `tests/test_config.py`，覆盖第 6 步验收所需的三组优先级场景：
  - 默认值生效（无 YAML/无环境变量）。
  - YAML 覆盖默认值。
  - 环境变量覆盖 YAML。
- 新增关键反例校验测试：
  - 风控配置冲突（`max_position_size > max_total_position`）应报错。
  - SMA 参数不合法（`fast_period >= slow_period`）应报错。
- 你已确认第 6 步“通过”（2026-02-16）。

### 验收状态
- Phase 0 第 6 条已验证通过。
- 按你的约束未开始第 7 步（日志方案设计）。

### 交接备注
- 配置层现已形成“加载器 + 默认值 + 校验器”三段式结构，后续新增配置项时需同步更新三处并补测试。
- 第 7 步可直接基于 `load_config()` 输出的 `logging` 配置落地日志初始化方案。

## 2026-02-16（第 7 步）

### 本次目标
- 执行 `implementation-plan.md` Phase 0 第 7 条：设计日志方案（分级、终端+文件、轮转、格式），并记录在说明文档。
- 验证日志方案落地策略。

### 已完成事项
- 完整阅读并复核 `memory-bank/` 全部文档，确认第 7 步边界与验收口径。
- 完成日志方案实现与说明文档落地：
  - `src/utils/logger.py`：
    - 提供 `setup_logger(config)`，实现终端 + 文件并行输出。
    - 支持按 `config.logging` 配置轮转、保留、压缩、格式化。
    - 实现日志分流：`main`、`strategy`、`trade`、`error`。
    - 实现敏感信息脱敏（`api_key/api_secret/token/password/secret`）。
  - `tests/test_logger.py`：
    - 验证分流正确性（main/strategy/trade/error 文件）。
    - 验证敏感字段脱敏生效。
    - 验证非法 `log_type` 拒绝。
  - `README.md`：
    - 新增第 7 步日志方案说明。
    - 新增手工演练步骤（触发各级日志并检查落盘文件）。
- 你已确认第 7 步“通过”（2026-02-16）。

### 验收状态
- Phase 0 第 7 条已验证通过。
- Phase 0 所有步骤已完成（第 1-7 条）。
- 按你的约束未开始第 8 步。

### 交接备注
- 日志系统已就绪，可用于后续 Phase 1 数据层开发的调试与监控。
- 第 8 步开始前，继续沿用“先记录连接生命周期设计，再落代码”的执行节奏。

## 2026-02-17（第 8 步）

### 本次目标
- 执行 `implementation-plan.md` Phase 1 第 8 条：设计数据库连接生命周期（打开、关闭、事务），并确保数据库路径取自配置。

### 已完成事项
- 完整阅读并复核 `memory-bank/` 全部文档，确认第 8 步边界与验收口径。
- 完成数据库生命周期实现：
  - `src/core/database.py`：
    - 新增 `SQLiteDatabase` 生命周期管理器。
    - 实现 `open()` / `close()`。
    - 实现 `transaction()` 上下文管理，覆盖自动提交与异常回滚。
    - 实现 `from_config()`，从 `system.database_path` 构建数据库连接管理器。
    - 提供连接状态与上下文管理能力（`is_open`、`__enter__`/`__exit__`）。
- 新增第 8 步验收测试：
  - `tests/test_database.py`：
    - 验证数据库路径来自配置。
    - 验证打开→提交→关闭流程。
    - 验证异常触发回滚。
    - 验证关闭幂等与未打开连接保护。
- 你已确认第 8 步“通过”（2026-02-17）。

### 验收状态
- Phase 1 第 8 条已验证通过。
- 按你的约束未开始第 9 步（表结构定义与审核）。

### 交接备注
- 数据层已具备基础连接生命周期与事务边界，可作为第 9 步建表与索引实现的底座。
- 下一步进入第 9 步时，应仅落地 `accounts`、`orders`、`trades`、`strategy_runs`、`positions`、`candles` 六表及其约束/索引，不跨步实现第 10 步。

## 2026-02-17（第 9 步）

### 本次目标
- 执行 `implementation-plan.md` Phase 1 第 9 条：定义并审核表结构（`accounts`、`orders`、`trades`、`strategy_runs`、`positions`、`candles`），确保字段与需求一致。

### 已完成事项
- 完整阅读并复核 `memory-bank/` 全部文档，确认第 9 步边界与验收口径（含 `CLAUDE.md` 行 387–520）。
- 在 `src/core/database.py` 实现第 9 步建表与建索引能力：
  - 新增六张核心表的 `CREATE TABLE IF NOT EXISTS` 语句。
  - 新增 `positions` 约束与索引：`UNIQUE(symbol)`、`CHECK(amount >= 0)`、`idx_positions_symbol`。
  - 新增 `candles` 约束与索引：`UNIQUE(symbol, timeframe, timestamp)`、`idx_candles_symbol_time`、`idx_candles_timestamp`。
  - 新增 `initialize_schema()`，在事务内统一执行建表与建索引。
- 扩展 `tests/test_database.py` 以固化第 9 步验收：
  - 校验六张表存在与字段完整性。
  - 校验 `trades.order_id -> orders.id` 外键存在并生效。
  - 校验 `positions` 的 `UNIQUE/CHECK` 生效。
  - 校验 `candles` 复合 `UNIQUE` 生效。
- 完成验证：
  - 使用 `PYTHONPATH=. ./.venv/bin/pytest -q tests/test_database.py`，结果 `11 passed`。
  - 通过 SQLite `sqlite_master` 元数据抽查，确认三条索引与六张表 SQL 落地。
- 你已确认第 9 步“通过”（2026-02-17）。

### 验收状态
- Phase 1 第 9 条已验证通过。
- 按你的约束未开始第 10 步（领域模型与校验规则）。

### 交接备注
- 数据层已完成“生命周期 + 核心表结构”基线，可进入第 10 步的模型与规则定义。
- 第 10 步开始前应保持范围边界，仅新增领域模型与校验，不提前实现账户/订单业务流程。

## 2026-02-17（第 10 步）

### 本次目标
- 执行 `implementation-plan.md` Phase 1 第 10 条：定义领域模型与校验规则（必填、数值范围、状态枚举），形成可复用的模型层。

### 已完成事项
- 完整阅读并复核 `memory-bank/` 全部文档，确认第 10 步边界与验收口径。
- 实现领域模型与校验规则（分文件，避免大文件）：
  - `src/core/enums.py`：订单类型/方向/状态、交易方向、策略运行状态枚举。
  - `src/core/validation.py`：通用校验函数与 `DomainValidationError`。
  - 领域模型（含 `validate` 类方法）：`account.py`、`order.py`、`trade.py`、`position.py`、`candle.py`、`strategy_run.py`。
  - 规则覆盖：必填校验、正数/非负数、比例(0,1]、价格高低开收关系、时间戳非负与先后约束、订单 filled 不超 amount、非市价单必须给 price、K 线 timeframe 白名单复用配置。
- 新增自动化测试 `tests/test_models.py`，覆盖 14 项正反例；全量测试 `PYTHONPATH=. ./.venv/bin/pytest -q` 通过（33 passed）。

### 验收状态
- Phase 1 第 10 条已完成且本地测试通过。
- 按约定未开始第 11 步（账户初始化与余额管理）。

### 交接备注
- 第 11 步可直接使用已校验的模型与枚举，避免魔法字符串与重复校验逻辑。
- 如需扩展字段或新枚举，请同步更新 `validation.py` 与对应模型测试。

## 2026-02-17（第 11 步验证与 Bug 修复）

### 本次目标
- 验证第 11 步（账户初始化与余额管理）的完成状况。
- 修复验证过程中发现的测试失败。

### 已完成事项
- 确认 `src/core/account_service.py`（232 行）已实现第 11 步核心功能：
  - `AccountService`：账户生命周期管理（初始化、查询、余额变更）。
  - `initialize_accounts()`：幂等创建账户行。
  - `freeze_funds()` / `release_funds()`：可用/冻结资金互转。
  - `deposit()` / `consume_available()` / `add_to_available()`：余额增减。
  - `load_positions()`：从 `positions` 表恢复持仓状态。
  - `compute_total_assets()`：多币种总资产估值（现金 + 持仓市值）。
  - `from_config()`：从配置初始化服务。
- 确认 `tests/test_account.py` 包含 5 项验收测试。
- 运行测试发现 2 项失败（`test_compute_total_assets_uses_positions`、`test_compute_total_assets_requires_price_when_missing_current_price`）。
- 定位根因：`src/core/validation.py` 的 `require_timestamp()` 仅接受 `int/float`，但 `database.py` 使用 `detect_types=sqlite3.PARSE_DECLTYPES` 导致 `TIMESTAMP` 列自动解析为 `datetime.datetime` 对象。
- 修复 `src/core/validation.py` 中的 `require_timestamp()`，新增：
  - `datetime.datetime` 对象支持（SQLite `PARSE_DECLTYPES` 产生）。
  - ISO 格式字符串支持（降级兼容）。
- 修复后全量测试通过：`38 passed`（含 `test_account` 5 项、`test_models` 14 项、`test_database` 11 项、`test_config` 5 项、`test_logger` 3 项）。

### 验收状态
- 第 11 步代码与测试实现已存在，Bug 已修复，全量测试通过。
- 第 11 步已验证通过（2026-02-17）。
- 按约定未开始第 12 步（订单持久化接口）。

### 交接备注
- `require_timestamp()` 现兼容三种时间戳来源：数值、`datetime` 对象、ISO 字符串。后续新增时间戳字段时无需额外适配。
- 3 条 `DeprecationWarning`（Python 3.12 弃用旧版 timestamp converter）为已知问题，不影响功能。
- 账户服务（`AccountService`）已就绪，第 12 步订单持久化可直接调用其余额检查方法（需扩展）。

## 2026-02-17（第 12 步）

### 本次目标
- 执行 `implementation-plan.md` Phase 1 第 12 条：实现订单持久化接口（创建、查询、状态更新、撤销），保证幂等与一致性。

### 已完成事项
- 完整阅读并复核 `memory-bank/` 全部文档，确认第 12 步边界与验收口径。
- 实现订单持久化服务（`src/core/order_service.py`）：
  - `OrderService`：订单生命周期管理（创建、查询、状态更新、撤销）。
  - `create_order()`：创建订单并冻结资金（买单），当调用方提供 `order_id` 时支持幂等性。
  - `get_order()` / `list_orders()`：按 ID 查询或按条件过滤（symbol、status、limit）。
  - `update_order_status()`：状态流转校验（PENDING→OPEN→PARTIALLY_FILLED→FILLED/CANCELED），部分成交时消耗冻结资金。
  - `cancel_order()`：撤销订单并释放未成交部分的冻结资金，支持幂等性。
  - 状态机校验：定义合法流转表，拒绝非法状态转换。
  - 资金管理：买单创建时冻结资金，部分成交时消耗冻结资金，取消时释放剩余冻结资金。
- 修复 `orders` 表结构：将 `created_at` 和 `updated_at` 从 `TIMESTAMP` 改为 `INTEGER`（存储毫秒级时间戳），避免 SQLite `PARSE_DECLTYPES` 解析冲突。
- 新增 `tests/test_order_service.py`，覆盖 24 项验收测试：
  - 订单创建：冻结资金、参数校验、资金不足拒绝、`order_id` 幂等校验。
  - 订单查询：按 ID、按 symbol、按 status、limit 分页。
  - 状态更新：合法流转、非法流转拒绝、filled 超限拒绝。
  - 订单撤销：释放冻结资金、部分成交后释放剩余、幂等性。
- 全量测试通过：62 passed（3 warnings，含 24 项订单服务测试、38 项之前的测试）。

### 验收状态
- Phase 1 第 12 条已完成且全量测试通过。
- 等待用户验证后开始第 13 步（交易记录写入与订单关联）。

### 交接备注
- 订单服务已实现完整的状态机与资金管理，可作为第 13 步交易记录写入的基础。
- 订单状态流转与资金冻结/消耗/释放逻辑已通过 21 项测试固化，后续修改需同步更新测试。
- 第 13 步需实现交易记录写入（`trades` 表）并与订单关联，包含手续费字段。
