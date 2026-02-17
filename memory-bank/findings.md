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
- 阅读 `memory-bank/` 全部文档后，执行 `implementation-plan.md` 第 10 步（定义领域模型与校验规则）。
- 第 10 步内容：为账户、订单、交易、持仓、K 线、策略运行记录建立领域模型与校验规则，覆盖必填、数值范围、枚举状态、时间戳关系。
- 未获得验证通过前，不进入第 11 步。
- 验证通过后，需要联动更新 memory-bank 文档（`progress.md`、`architecture.md`、`findings.md`、`requirements-traceability-checklist.md`、`task.md`）。

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
- Step 10 验收通过后仍需保持“未开始第 11 步”边界。
- **Step 11 验证发现（2026-02-17）**：`database.py` 使用 `detect_types=sqlite3.PARSE_DECLTYPES` 打开连接，导致 `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` 列被自动解析为 `datetime.datetime` 对象而非字符串或数值。`require_timestamp()` 原先仅接受 `int/float`，引发 `DomainValidationError`。修复后 `require_timestamp()` 兼容数值、`datetime` 对象和 ISO 格式字符串三种来源，全量测试 38 passed。

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
- `tests/test_models.py`
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
