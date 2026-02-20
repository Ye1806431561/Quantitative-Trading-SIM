# Strategy Param Management Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 从配置加载策略参数，并在回测与实时策略实例化时生效，且显式参数可覆盖配置。

**Architecture:** 新增策略注册表与参数解析器作为统一入口。回测引擎在运行前用解析器合并参数；实时路径通过工厂创建 BacktraderAdapter，并把合并后的参数写入 StrategyContext。

**Tech Stack:** Python 3.10, Backtrader, PyYAML

---

### Task 1: 策略注册表与参数解析器

**Files:**
- Create: `/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/src/strategies/registry.py`
- Create: `/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/src/strategies/param_resolver.py`
- Modify: `/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/src/strategies/__init__.py`
- Test: `/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/tests/test_strategy_param_resolver.py`

**Step 1: Write the failing test**

```python
from __future__ import annotations

import pytest

from src.strategies.param_resolver import StrategyParamResolver, StrategyParamError
from src.strategies.registry import StrategyRegistry, StrategySpec


def _base_config() -> dict:
    return {
        "sma_strategy": {
            "enabled": True,
            "params": {"fast_period": 10, "slow_period": 30, "position_size": 0.2},
        },
        "grid_strategy": {
            "enabled": True,
            "params": {"grid_num": 10, "price_range": 0.1, "position_size": 0.1},
        },
        "bollinger_strategy": {
            "enabled": True,
            "params": {"period": 20, "dev": 2.0, "position_size": 0.2},
        },
    }


def test_resolver_merges_config_and_explicit_params():
    config = _base_config()
    registry = StrategyRegistry.default()
    resolver = StrategyParamResolver(config, registry)

    params = resolver.resolve_for_name(
        "sma_strategy",
        {"fast_period": 5},
    )

    assert params["fast_period"] == 5
    assert params["slow_period"] == 30
    assert params["position_size"] == 0.2


def test_resolver_rejects_unknown_param():
    config = _base_config()
    registry = StrategyRegistry.default()
    resolver = StrategyParamResolver(config, registry)

    with pytest.raises(StrategyParamError, match="unknown parameter"):
        resolver.resolve_for_name("sma_strategy", {"unknown": 1})


def test_resolver_rejects_disabled_strategy():
    config = _base_config()
    config["grid_strategy"]["enabled"] = False
    registry = StrategyRegistry.default()
    resolver = StrategyParamResolver(config, registry)

    with pytest.raises(StrategyParamError, match="disabled"):
        resolver.resolve_for_name("grid_strategy", {})
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config /Users/pingu/Documents/Quantitative-Trading-SIM/.venv/bin/pytest -q /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/tests/test_strategy_param_resolver.py`

Expected: FAIL (missing module/class).

**Step 3: Write minimal implementation**

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import backtrader as bt

from src.strategies.bollinger_strategy import BollingerStrategy
from src.strategies.grid_strategy import GridStrategy
from src.strategies.sma_strategy import SMAStrategy
from src.utils.config_defaults import DEFAULT_STRATEGIES_CONFIG


class StrategyParamError(ValueError):
    pass


@dataclass(frozen=True)
class StrategySpec:
    name: str
    strategy_class: type[bt.Strategy]
    allowed_params: tuple[str, ...]


class StrategyRegistry:
    def __init__(self, specs: Mapping[str, StrategySpec]) -> None:
        self._by_name = dict(specs)
        self._by_class = {spec.strategy_class: spec for spec in specs.values()}

    @classmethod
    def default(cls) -> "StrategyRegistry":
        defaults = DEFAULT_STRATEGIES_CONFIG
        specs = {
            "sma_strategy": StrategySpec(
                name="sma_strategy",
                strategy_class=SMAStrategy,
                allowed_params=tuple(defaults["sma_strategy"]["params"].keys()),
            ),
            "grid_strategy": StrategySpec(
                name="grid_strategy",
                strategy_class=GridStrategy,
                allowed_params=tuple(defaults["grid_strategy"]["params"].keys()),
            ),
            "bollinger_strategy": StrategySpec(
                name="bollinger_strategy",
                strategy_class=BollingerStrategy,
                allowed_params=tuple(defaults["bollinger_strategy"]["params"].keys()),
            ),
        }
        return cls(specs)

    def get_by_name(self, name: str) -> StrategySpec:
        if name not in self._by_name:
            raise StrategyParamError(f"Unknown strategy name: {name}")
        return self._by_name[name]

    def get_by_class(self, strategy_class: type[bt.Strategy]) -> StrategySpec:
        if strategy_class not in self._by_class:
            raise StrategyParamError("Unknown strategy class")
        return self._by_class[strategy_class]


class StrategyParamResolver:
    def __init__(self, strategies_config: Mapping[str, Any], registry: StrategyRegistry) -> None:
        self._config = strategies_config
        self._registry = registry

    def resolve_for_name(
        self,
        name: str,
        explicit_params: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        spec = self._registry.get_by_name(name)
        config_entry = self._config.get(name)
        if not isinstance(config_entry, Mapping):
            raise StrategyParamError(f"Missing strategy config: {name}")
        if not config_entry.get("enabled", False):
            raise StrategyParamError(f"Strategy disabled: {name}")
        config_params = dict(config_entry.get("params", {}))
        merged = dict(config_params)
        if explicit_params:
            unknown = set(explicit_params.keys()) - set(spec.allowed_params)
            if unknown:
                raise StrategyParamError(f"unknown parameter(s): {sorted(unknown)}")
            merged.update(explicit_params)
        return merged

    def resolve_for_class(
        self,
        strategy_class: type[bt.Strategy],
        explicit_params: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        spec = self._registry.get_by_class(strategy_class)
        return self.resolve_for_name(spec.name, explicit_params)
```

**Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config /Users/pingu/Documents/Quantitative-Trading-SIM/.venv/bin/pytest -q /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/tests/test_strategy_param_resolver.py`

Expected: PASS

**Step 5: Commit**

```bash
git add /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/src/strategies/registry.py \
  /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/src/strategies/param_resolver.py \
  /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/src/strategies/__init__.py \
  /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/tests/test_strategy_param_resolver.py

git commit -m "feat: add strategy registry and param resolver"
```

---

### Task 2: 回测引擎接入参数解析器

**Files:**
- Modify: `/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/src/backtest/engine.py`
- Modify: `/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/tests/test_backtest_engine.py`

**Step 1: Write the failing test**

```python
class ParamSpyStrategy(bt.Strategy):
    params = (("threshold", 1),)
    last_threshold = None

    def __init__(self):
        ParamSpyStrategy.last_threshold = self.params.threshold


def test_backtest_engine_applies_config_params(sqlite_database):
    registry = StrategyRegistry(
        {
            "spy_strategy": StrategySpec(
                name="spy_strategy",
                strategy_class=ParamSpyStrategy,
                allowed_params=("threshold",),
            )
        }
    )
    strategies_config = {
        "spy_strategy": {
            "enabled": True,
            "params": {"threshold": 42},
        }
    }

    engine = BacktestEngine(
        database=sqlite_database,
        initial_capital=10_000.0,
        commission_rate=0.0,
        slippage_rate=0.0,
        strategies_config=strategies_config,
        strategy_registry=registry,
    )

    request = BacktestRunRequest(
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=1_700_000_000_000,
        end_timestamp=1_700_000_010_800,
        strategy_class=ParamSpyStrategy,
        strategy_params={},
    )

    engine.run(request)
    assert ParamSpyStrategy.last_threshold == 42
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config /Users/pingu/Documents/Quantitative-Trading-SIM/.venv/bin/pytest -q /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/tests/test_backtest_engine.py::test_backtest_engine_applies_config_params`

Expected: FAIL (missing resolver wiring).

**Step 3: Write minimal implementation**

```python
from src.strategies.param_resolver import StrategyParamResolver
from src.strategies.registry import StrategyRegistry

# in __init__ signature
strategies_config: Mapping[str, Any] | None = None,
strategy_registry: StrategyRegistry | None = None,

# in __init__ body
self._strategy_registry = strategy_registry or StrategyRegistry.default()
self._param_resolver = (
    StrategyParamResolver(strategies_config, self._strategy_registry)
    if strategies_config is not None
    else None
)

# in run()
params = dict(request.strategy_params)
if self._param_resolver is not None:
    params = self._param_resolver.resolve_for_class(strategy_class, params)

cerebro.addstrategy(wrapped_strategy, **params)
```

**Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config /Users/pingu/Documents/Quantitative-Trading-SIM/.venv/bin/pytest -q /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/tests/test_backtest_engine.py::test_backtest_engine_applies_config_params`

Expected: PASS

**Step 5: Commit**

```bash
git add /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/src/backtest/engine.py \
  /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/tests/test_backtest_engine.py

git commit -m "feat: apply strategy config in backtest engine"
```

---

### Task 3: 实时策略工厂与上下文参数传递

**Files:**
- Create: `/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/src/strategies/factory.py`
- Modify: `/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/src/live/realtime_loop.py`
- Modify: `/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/tests/test_realtime_loop.py`
- Test: `/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/tests/test_strategy_factory.py`

**Step 1: Write the failing tests**

```python
from __future__ import annotations

from src.strategies.factory import create_live_strategy
from src.strategies.adapter import BacktraderAdapter


def test_factory_builds_adapter_with_config_params():
    config = {
        "sma_strategy": {
            "enabled": True,
            "params": {"fast_period": 5, "slow_period": 9, "position_size": 0.3},
        },
        "grid_strategy": {"enabled": True, "params": {"grid_num": 10, "price_range": 0.1, "position_size": 0.1}},
        "bollinger_strategy": {"enabled": True, "params": {"period": 20, "dev": 2.0, "position_size": 0.2}},
    }

    strategy, params = create_live_strategy("sma_strategy", config, explicit_params=None)

    assert isinstance(strategy, BacktraderAdapter)
    assert strategy._bt_params["fast_period"] == 5
    assert strategy._bt_params["slow_period"] == 9
    assert strategy._position_size == 0.3
    assert params["position_size"] == 0.3
```

Add to `tests/test_realtime_loop.py`:

```python
    strategy_params = {"fast_period": 5}
    loop = RealtimeSimulationLoop(
        ...,
        strategy=strategy,
        config=config,
        strategy_params=strategy_params,
    )
    loop.start()
    assert strategy.last_context.parameters == strategy_params
```

**Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config /Users/pingu/Documents/Quantitative-Trading-SIM/.venv/bin/pytest -q /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/tests/test_strategy_factory.py`

Expected: FAIL (missing factory).

**Step 3: Write minimal implementation**

```python
from __future__ import annotations

from typing import Any, Mapping

from src.strategies.adapter import BacktraderAdapter
from src.strategies.base import LiveStrategy
from src.strategies.param_resolver import StrategyParamResolver
from src.strategies.registry import StrategyRegistry


def create_live_strategy(
    strategy_name: str,
    strategies_config: Mapping[str, Any],
    explicit_params: Mapping[str, Any] | None = None,
    *,
    registry: StrategyRegistry | None = None,
) -> tuple[LiveStrategy, dict[str, Any]]:
    registry = registry or StrategyRegistry.default()
    resolver = StrategyParamResolver(strategies_config, registry)
    params = resolver.resolve_for_name(strategy_name, explicit_params)
    spec = registry.get_by_name(strategy_name)

    position_size = float(params.get("position_size", 0.1))
    bt_params = {key: value for key, value in params.items() if key != "position_size"}

    adapter = BacktraderAdapter(
        name=strategy_name,
        bt_strategy_cls=spec.strategy_class,
        bt_params=bt_params,
        position_size=position_size,
    )
    return adapter, params
```

Update `RealtimeSimulationLoop` to accept `strategy_params: Mapping[str, Any] | None = None`, store it, and pass into `StrategyContext(parameters=...)`.

**Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config /Users/pingu/Documents/Quantitative-Trading-SIM/.venv/bin/pytest -q /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/tests/test_strategy_factory.py`

Expected: PASS

**Step 5: Commit**

```bash
git add /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/src/strategies/factory.py \
  /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/src/live/realtime_loop.py \
  /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/tests/test_strategy_factory.py \
  /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/tests/test_realtime_loop.py

git commit -m "feat: create live strategy from config"
```

---

### Task 4: 文档更新（进度、发现、架构）

**Files:**
- Modify: `/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/memory-bank/progress.md`
- Modify: `/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/memory-bank/findings.md`
- Modify: `/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/memory-bank/architecture.md`

**Step 1: 更新 progress.md**
- 将第 34 步标记为“已完成、待验证”。
- 明确“未验证前不进入第 35 步”。

**Step 2: 更新 findings.md**
- 记录“策略参数解析器 + 注册表 + 实时工厂”设计决策。

**Step 3: 更新 architecture.md**
- 增加第 34 步参数管理与配置流向说明。

**Step 4: Commit**

```bash
git add /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/memory-bank/progress.md \
  /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/memory-bank/findings.md \
  /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/memory-bank/architecture.md

git commit -m "docs: update step 34 progress and decisions"
```

---

### Task 5: 回归验证

**Files:** None

**Step 1: Run tests**

Run: `PYTHONPATH=/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config /Users/pingu/Documents/Quantitative-Trading-SIM/.venv/bin/pytest -q /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/tests/test_strategy_param_resolver.py`

Run: `PYTHONPATH=/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config /Users/pingu/Documents/Quantitative-Trading-SIM/.venv/bin/pytest -q /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/tests/test_backtest_engine.py::test_backtest_engine_applies_config_params`

Run: `PYTHONPATH=/Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config /Users/pingu/Documents/Quantitative-Trading-SIM/.venv/bin/pytest -q /Users/pingu/Documents/Quantitative-Trading-SIM/.worktrees/step-34-strategy-config/tests/test_strategy_factory.py`

Expected: PASS
