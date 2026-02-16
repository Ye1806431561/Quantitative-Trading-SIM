# Architecture Notes

## 当前阶段定位（2026-02-16）
- 仓库已从“纯文档阶段”进入“工程骨架就绪阶段”。
- `implementation-plan.md` 的 Phase 0 第 1-3 条已完成，且第 3 条已由用户验证通过。
- 当前最小交付范围仍锁定为 CLI + 模拟盘（回测与实时模拟），Web 能力保留为可选项且暂不交付。

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

## 工程骨架文件作用（第 3 步新增）
- `src/core/*.py`：核心业务域占位（账户、订单、撮合、数据库），用于承接 Phase 1 实现。
- `src/data/*.py`：数据接入与存储占位（市场数据、历史数据），用于承接 Phase 1 与 Phase 2。
- `src/strategies/*.py`：策略接口与内置策略占位，用于承接 Phase 3。
- `src/backtest/*.py`：回测引擎与分析器占位，用于承接 Phase 3。
- `src/live/*.py`：实时模拟主循环占位，用于承接 Phase 3。
- `src/utils/*.py`：日志与配置工具占位，用于承接 Phase 0 第 5-7 条。
- `config/config.yaml`、`config/strategies.yaml`、`config/.env.example`：配置模板占位，用于承接 Phase 0 第 5 条。
- `tests/*.py`：测试模块占位，用于承接 Phase 4 第 39 条。
- `requirements.txt`、`main.py`、`README.md`：依赖入口、程序入口、使用文档入口占位，用于承接 Phase 0 第 4 条与 Phase 4 第 41 条。

## 本轮新增架构洞察
- 在代码实现前先完成“范围收敛 + 排除理由固化”，可以减少后续需求漂移导致的返工。
- 将 `FR-WEB-01` 明确为可选且暂不交付，使 Phase 0-4 的资源集中于 CLI 与双引擎闭环。
- 追踪清单新增“排除理由”字段后，范围决策可审计，后续恢复 Web 范围时可直接追溯决策上下文。
- 先建立与技术栈一致的目录和占位文件，可让后续实现按模块直接落位，降低“先写后拆”的重构成本。
- 骨架完成后，`requirements.txt` 与配置模板成为下一阶段的关键控制点，决定后续实现是否保持与技术栈一致。
