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
- 阅读 `memory-bank/` 全部文档后，执行 `implementation-plan.md` 第 12 步。
- 第 12 步内容：实现订单持久化接口（创建、查询、状态更新、撤销），保证幂等与一致性（创建幂等需提供 `order_id`）。
- 验证通过后，更新 `progress.md` 等文档，准备进入第 13 步（交易记录写入与订单关联）。

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
  - 幂等性设计：当调用方提供 `order_id` 时，重复创建返回现有订单；重复取消已终态订单返回当前状态。
  - 拒单（REJECTED）与撤单一致释放冻结资金，避免资金长期锁定。
  - `update_order_status()` 保持单层事务，避免嵌套 `with tx:` 造成事务语义偏差。
  - 全量测试 62 passed（3 warnings，含 24 项订单服务测试 + 38 项之前的测试）。

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
| 订单服务支持幂等性（创建幂等需 `order_id`） | 防止重复操作导致的数据不一致，提高系统健壮性 |
| 拒单释放冻结资金 | 与撤单一致，避免冻结资金长期占用 |

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
| REJECTED 未释放冻结资金 | 在 `update_order_status()` 增加 REJECTED 释放冻结资金逻辑，并补测试覆盖 |

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
- `tests/test_models.py`
- `tests/test_account.py`
- `tests/test_order_service.py`
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
