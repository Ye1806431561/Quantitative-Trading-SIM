# Findings & Decisions
<!-- 
  WHAT: Your knowledge base for the task. Stores everything you discover and decide.
  WHY: Context windows are limited. This file is your "external memory" - persistent and unlimited.
  WHEN: Update after ANY discovery, especially after 2 view/browser/search operations (2-Action Rule).
-->

## Requirements
<!-- 
  WHAT: What the user asked for, broken down into specific requirements.
  WHY: Keeps requirements visible so you don't forget what you're building.
  WHEN: Fill this in during Phase 1 (Requirements & Discovery).
  EXAMPLE:
    - Command-line interface
    - Add tasks
    - List all tasks
    - Delete tasks
    - Python implementation
-->
<!-- Captured from user request -->
- 阅读 `memory-bank/` 全部文档后，执行 `implementation-plan.md` 第 15 步。
- 第 15 步内容：实现历史 K 线下载与本地存储（周期、命名规范、时间范围，写入目标表 `candles`）。
- 用户负责运行测试；在用户确认通过前，不启动第 16 步。

## Research Findings
<!-- 
  WHAT: Key discoveries from web searches, documentation reading, or exploration.
  WHY: Multimodal content (images, browser results) doesn't persist. Write it down immediately.
  WHEN: After EVERY 2 view/browser/search operations, update this section (2-Action Rule).
  EXAMPLE:
    - Python's argparse module supports subcommands for clean CLI design
    - JSON module handles file persistence easily
    - Standard pattern: python script.py <command> [args]
-->
<!-- Key discoveries during exploration -->
- 领域模型拆分为独立文件符合 CLAUDE 反对大文件的规则：`account.py`、`order.py`、`trade.py`、`position.py`、`candle.py`、`strategy_run.py`，并集中枚举于 `enums.py`，通用校验于 `validation.py`。
- 校验规则覆盖：必填字段、正数/非负数、比例区间(0,1]、价格上下界、K 线 high/low/open/close 关系、时间戳非负与先后关系、订单 filled 不得超 amount、非市价单必须给 price。
- 复用 `ALLOWED_TIMEFRAMES` 确保 candle 校验与配置白名单一致；状态枚举与表结构字段对应，避免魔法字符串。
- 新增 `tests/test_models.py` 覆盖正反例 14 项；全量测试 `33 passed` 使用 `PYTHONPATH=. ./.venv/bin/pytest -q`（2026-02-17）。
- Step 10 验收通过后仍需保持"未开始第 11 步"边界。
- **Step 11 验证发现（2026-02-17）**：`database.py` 使用 `detect_types=sqlite3.PARSE_DECLTYPES` 打开连接，导致 `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` 列被自动解析为 `datetime.datetime` 对象而非字符串或数值。`require_timestamp()` 原先仅接受 `int/float`，引发 `DomainValidationError`。修复后 `require_timestamp()` 兼容数值、`datetime` 对象和 ISO 格式字符串三种来源，全量测试 38 passed。
- `AccountService` 的 `initialize_accounts` 必须也是幂等的，测试已覆盖（`test_initialize_accounts_is_idempotent`）。
- `compute_total_assets` 依赖 `positions` 表恢复，验证了 `load_positions` 的正确性。
- **Step 12 实现发现（2026-02-17）**：
  - 订单状态机需要明确定义合法流转表，避免非法状态转换（如 PENDING 直接到 FILLED）。
  - 买单资金管理分三阶段：创建时冻结（available→frozen）、部分成交时消耗（frozen 和 balance 同时减少）、取消时释放剩余（frozen→available）。
  - `orders` 表的 `created_at` 和 `updated_at` 字段使用 `TIMESTAMP` 类型会与 SQLite `PARSE_DECLTYPES` 冲突，改为 `INTEGER` 存储毫秒级时间戳。
  - 幂等性设计：重复创建已存在订单返回现有订单，重复取消已终态订单返回当前状态。
  - 全量测试 59 passed（含 21 项订单服务测试 + 38 项之前的测试）。
- **Step 14 实现发现（2026-02-17）**：
  - 行情接口需要将“交易所选择、限流、重试策略”解耦，避免单文件/单类膨胀。
  - 可重试与不可重试错误必须显式分层，否则会把鉴权类错误误判为可重试，导致无效重试。
  - 运行态写入目标必须在接口层硬性校验为 `sqlite`，防止误配置把 `csv/parquet` 当成运行态存储。
  - 配置加载器启用了“未知字段拒绝”，因此需同步在 `config_defaults.py`/`config_validation.py` 增加 `market_data` 字段，否则无法从配置覆盖重试参数。
  - 增加 `tests/test_market_data.py` 可直接模拟限流与网络错误，不依赖真实交易所网络请求。
- **Step 15 实现发现（2026-02-17）**：
  - 历史 K 线下载需要“时间游标 + 分页拉取”组合，避免一次性请求过大时间窗口。
  - 查询接口必须固定 `ORDER BY timestamp ASC`，否则回测/指标消费端容易出现时间序错乱。
  - 第 15 步仅实现“下载 + 落库 + 查询”，缓存与去重机制应留给第 16 步，避免跨步实现。

## Technical Decisions
<!-- 
  WHAT: Architecture and implementation choices you've made, with reasoning.
  WHY: You'll forget why you chose a technology or approach. This table preserves that knowledge.
  WHEN: Update whenever you make a significant technical choice.
  EXAMPLE:
    | Use JSON for storage | Simple, human-readable, built-in Python support |
    | argparse with subcommands | Clean CLI: python todo.py add "task" |
-->
<!-- Decisions made with rationale -->
| Decision | Rationale |
|----------|-----------|
| 领域模型分文件 + 枚举集中在 `enums.py` | 遵守 CLAUDE 拆分规则，避免大文件与魔法字符串 |
| 共用 `validation.py` 做输入校验 | 复用通用校验函数，减少重复逻辑并统一错误信息 |
| 校验规则与数据库约束保持一致 | 避免应用层与存储层不一致导致的脏数据 |
| K 线校验复用 `ALLOWED_TIMEFRAMES` | 与配置白名单统一，避免时间周期漂移 |
| 优先补充反例测试（边界/非法状态/顺序） | 确保第 10 步验收覆盖负路径，防止静默坏数据进入后续流程 |
| 订单状态机使用字典定义合法流转 | 集中管理状态转换规则，易于维护和扩展 |
| 买单资金分阶段管理（冻结→消耗→释放） | 确保资金流转清晰可追溯，避免资金泄漏或重复扣款 |
| `orders` 表时间戳字段使用 `INTEGER` | 避免 SQLite `PARSE_DECLTYPES` 自动解析 `TIMESTAMP` 为 `datetime` 对象，统一使用毫秒级整数 |
| 订单服务支持幂等性 | 防止重复操作导致的数据不一致，提高系统健壮性 |
| `trades.timestamp` 统一为毫秒整数并设默认值 | 与订单时间戳一致，避免 SQLite 类型解析差异且便于排序 |
| 成交写入复用资金消耗逻辑 | `TradeService.record_trade()` 共用订单服务的冻结资金消耗逻辑，保持资金流一致性 |
| 市场数据接口拆分为 `market.py + market_policy.py + market_retry.py` | 遵守单文件 <300 行约束，并将策略/重试/配置职责解耦 |
| 错误分类驱动重试策略 | 限流与瞬时网络错误重试，鉴权/参数错误快速失败，减少无效等待 |
| 运行态写入目标在接口层强制为 SQLite | 对齐 `DC-001~DC-004`，阻止 CSV/Parquet 进入运行态写路径 |
| 历史下载使用时间游标分页（`since = last_timestamp + 1`） | 保证下载窗口可推进且避免分页边界重复 |
| 历史查询统一按 `timestamp ASC` 返回 | 保证策略与回测读取时间序稳定，避免消费端重复排序 |

## Issues Encountered
<!-- 
  WHAT: Problems you ran into and how you solved them.
  WHY: Similar to errors in task_plan.md, but focused on broader issues (not just code errors).
  WHEN: Document when you encounter blockers or unexpected challenges.
  EXAMPLE:
    | Empty file causes JSONDecodeError | Added explicit empty file check before json.load() |
-->
<!-- Errors and how they were resolved -->
| Issue | Resolution |
|-------|------------|
| 状态/类型字符串易出错 | 引入枚举，校验层仅接受枚举值 |
| 时间戳/价格范围漏检风险 | 校验函数显式验证非负/区间和 high-low-open-close 关系 |
| 反例不足导致验收覆盖不全 | 新增反例测试（价格缺失、filled 超量、drawdown>1、end<start 等） |
| `require_timestamp()` 不兼容 SQLite `datetime` 对象 | `database.py` 启用 `PARSE_DECLTYPES`，`TIMESTAMP` 列被解析为 `datetime.datetime` 而非字符串/数值。修复 `require_timestamp()` 新增 `datetime` 对象与 ISO 字符串支持，全量测试 38 passed |
| `orders` 表 `TIMESTAMP` 字段与 `PARSE_DECLTYPES` 冲突 | 将 `created_at` 和 `updated_at` 字段类型从 `TIMESTAMP` 改为 `INTEGER`，存储毫秒级时间戳 |
| 测试初始资金不足导致订单创建失败 | 将测试 fixture 中的初始资金从 10000 USDT 增加到 100000 USDT |
| 部分成交后取消订单的资金处理不清晰 | 明确资金管理逻辑：部分成交时消耗冻结资金（从 frozen 和 balance 同时扣除），取消时只释放剩余冻结资金 |
| 本地缺少 pytest 可执行文件 | 代码实现后无法直接运行测试，需先安装依赖再由用户执行 pytest |
| 市场数据模块初稿单文件超过 300 行 | 按 CLAUDE 约束拆分为 `market.py`、`market_policy.py`、`market_retry.py`，保持职责单一 |
| SQLite `PARSE_DECLTYPES` 触发 `DeprecationWarning` | 当前不影响功能；后续可统一替换 timestamp converter（与第 15 步实现无功能耦合） |

## Resources
<!-- 
  WHAT: URLs, file paths, API references, documentation links you've found useful.
  WHY: Easy reference for later. Don't lose important links in context.
  WHEN: Add as you discover useful resources.
  EXAMPLE:
    - Python argparse docs: https://docs.python.org/3/library/argparse.html
    - Project structure: src/main.py, src/utils.py
-->
<!-- URLs, file paths, API references -->
- `memory-bank/CLAUDE.md`
- `memory-bank/product-requirement-document.md`
- `memory-bank/implementation-plan.md`
- `memory-bank/tech-stack.md`
- `memory-bank/requirements-traceability-checklist.md`
- `memory-bank/progress.md`
- `memory-bank/architecture.md`
- `memory-bank/findings.md`
- `config/config.yaml`
- `src/utils/config_defaults.py`
- `src/utils/config_validation.py`
- `tests/test_config.py`
- `src/core/enums.py`
- `src/core/validation.py`
- `src/core/account.py`
- `src/core/order.py`
- `src/core/trade.py`
- `src/core/position.py`
- `src/core/candle.py`
- `src/core/strategy_run.py`
- `src/core/account_service.py`
- `src/core/order_service.py`
- `src/data/market.py`
- `src/data/market_policy.py`
- `src/data/market_retry.py`
- `src/data/storage.py`
- `tests/test_models.py`
- `tests/test_account.py`
- `tests/test_order_service.py`
- `tests/test_market_data.py`
- `tests/test_storage.py`
- `memory-bank/market-data-interface-design.md`
- `memory-bank/task.md`

## Visual/Browser Findings
<!-- 
  WHAT: Information you learned from viewing images, PDFs, or browser results.
  WHY: CRITICAL - Visual/multimodal content doesn't persist in context. Must be captured as text.
  WHEN: IMMEDIATELY after viewing images or browser results. Don't wait!
  EXAMPLE:
    - Screenshot shows login form has email and password fields
    - Browser shows API returns JSON with "status" and "data" keys
-->
<!-- CRITICAL: Update after every 2 view/browser operations -->
<!-- Multimodal content must be captured as text immediately -->
- 本轮无图片/PDF/浏览器检索输入；信息来源均为本地 Markdown 文档阅读。

---
<!-- 
  REMINDER: The 2-Action Rule
  After every 2 view/browser/search operations, you MUST update this file.
  This prevents visual information from being lost when context resets.
-->
*Update this file after every 2 view/browser/search operations*
*This prevents visual information from being lost*
