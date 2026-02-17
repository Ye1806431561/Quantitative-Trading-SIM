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
- 阅读 `memory-bank/` 全部文档后，执行 `implementation-plan.md` 的第 8 步（Phase 1 第 8 条）。
- 第 8 步内容：设计数据库连接生命周期（打开、关闭、事务），路径取自配置。
- 用户负责跑测试；在用户验证“通过”前，不进入第 9 步。
- 用户验证通过后，联动更新：
  - `memory-bank/progress.md`
  - `memory-bank/architecture.md`
  - `memory-bank/findings.md`
  - `memory-bank/requirements-traceability-checklist.md`

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
- 第 8 步边界是“数据库生命周期管理 + 验收验证”，不应提前进入第 9 步表结构定义。
- `system.database_path` 已在默认配置与校验规则中存在，可直接作为数据库连接路径来源。
- `src/core/database.py` 为空占位，需新增统一生命周期管理器承接 `open/close/transaction`。
- 第 8 步验收需可演练“打开/提交/回滚/关闭”全流程，适合通过独立测试文件固化。
- 用户已确认第 8 步验收“通过”（2026-02-17），可更新四份 memory-bank 文档并保持第 9 步未开始状态。

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
| 将本轮目标限定为“实施计划第8步（数据库连接生命周期）” | 遵守实施计划顺序，不越界到第 9 步表结构实现 |
| 数据库管理器统一提供 `open/close/transaction` | 把连接与事务边界集中到单一入口，降低资源泄露与事务不一致风险 |
| 从 `system.database_path` 构建数据库连接 | 复用既有配置体系，避免硬编码路径 |
| 使用事务上下文自动 `commit/rollback` | 明确成功与异常分支的持久化行为，满足第 8 步验收口径 |
| 通过 `tests/test_database.py` 固化第 8 步自动化验收 | 将“打开/提交/回滚/关闭”流程固化为可回归测试 |
| 在用户“通过”前不开始第 9 步 | 遵守闸门控制，避免提前推进表结构实现 |
| 验收通过后同步更新四份 memory-bank 文档 | 保持知识、进度、架构、追踪清单一致 |

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
| 第 8 步与第 9 步边界容易混淆 | 本轮只落地生命周期管理与测试，明确第 9 步尚未开始 |
| 本地运行 `pytest` 时全局命令不可用 | 切换到 `.venv/bin/pytest` 并设置 `PYTHONPATH=.` 完成自检 |
| 测试环境导入路径报错（`ModuleNotFoundError: src`） | 在执行测试命令时显式注入 `PYTHONPATH=.` |
| 必须等待用户验证后再做文档联动 | 用户确认“通过”后再更新四份文档，保持流程受控 |

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
- `config/strategies.yaml`
- `config/.env.example`
- `src/utils/config.py`
- `src/utils/config_defaults.py`
- `src/utils/config_validation.py`
- `tests/test_config.py`
- `src/core/database.py`
- `tests/test_database.py`

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
