# Performance Analysis Module Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a reusable performance analysis module that computes core metrics from equity curves/returns series and trade logs for both backtest and live runs.

**Architecture:** Add a new `src/analysis` package with a single entry point `analyze_performance(...)` and a `PerformanceSummary` dataclass. The module normalizes input time series, reconstructs equity if only returns are provided, computes return/drawdown/Sharpe/Sortino, and derives win rate/profit factor from trade logs.

**Tech Stack:** Python 3.10+, standard library (`datetime`, `statistics`, `math`), existing project conventions.

---

### Task 1: Create analysis package and equity-curve metrics

**Files:**
- Create: `src/analysis/__init__.py`
- Create: `src/analysis/performance.py`
- Test: `tests/test_performance_analysis.py`

**Step 1: Write the failing test**

```python
# tests/test_performance_analysis.py

def test_equity_curve_basic_metrics():
    equity = {
        "2026-02-20T00:00:00": 1000.0,
        "2026-02-21T00:00:00": 1100.0,
        "2026-02-22T00:00:00": 1050.0,
        "2026-02-23T00:00:00": 1200.0,
    }

    summary = analyze_performance(equity_curve=equity, trade_log=[])

    assert summary.total_return == pytest.approx(0.2)
    assert summary.max_drawdown == pytest.approx((1100.0 - 1050.0) / 1100.0)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. ./.venv/bin/pytest -q tests/test_performance_analysis.py::test_equity_curve_basic_metrics`
Expected: FAIL (missing module/function).

**Step 3: Write minimal implementation**

```python
# src/analysis/performance.py
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Mapping, Sequence, Tuple

@dataclass(frozen=True)
class PerformanceSummary:
    total_return: float
    annualized_return: float | None
    max_drawdown: float
    sharpe_ratio: float | None
    sortino_ratio: float | None
    win_rate: float
    profit_factor: float | None
    total_trades: int
    winning_trades: int
    losing_trades: int

class PerformanceAnalysisError(RuntimeError):
    ...

# Implement normalize helpers for timestamps and equity curve
# Implement analyze_performance(...)
```

Implement:
- Normalize equity curve to sorted `(timestamp_sec, equity)` list
- Compute `total_return` and `max_drawdown`
- Return `annualized_return=None`, `sharpe_ratio=None`, `sortino_ratio=None` for now
- Trade stats defaults to zeros when `trade_log` empty

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. ./.venv/bin/pytest -q tests/test_performance_analysis.py::test_equity_curve_basic_metrics`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/analysis/__init__.py src/analysis/performance.py tests/test_performance_analysis.py
git commit -m "feat: add equity curve performance metrics"
```

---

### Task 2: Add returns-series support and annualized/Sharpe/Sortino

**Files:**
- Modify: `src/analysis/performance.py`
- Test: `tests/test_performance_analysis.py`

**Step 1: Write the failing tests**

```python
# tests/test_performance_analysis.py

def test_returns_series_reconstructs_equity():
    returns = {
        "2026-02-20T00:00:00": 0.01,
        "2026-02-21T00:00:00": -0.005,
        "2026-02-22T00:00:00": 0.02,
    }

    summary = analyze_performance(
        returns_series=returns,
        initial_capital=1000.0,
        trade_log=[],
    )

    assert summary.total_return == pytest.approx(0.0251, rel=1e-4)


def test_sharpe_and_sortino_none_when_zero_variance():
    equity = {
        "2026-02-20T00:00:00": 1000.0,
        "2026-02-21T00:00:00": 1010.0,
        "2026-02-22T00:00:00": 1020.1,
    }

    summary = analyze_performance(equity_curve=equity, trade_log=[])

    assert summary.sharpe_ratio is None
    assert summary.sortino_ratio is None
```

**Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. ./.venv/bin/pytest -q tests/test_performance_analysis.py::test_returns_series_reconstructs_equity tests/test_performance_analysis.py::test_sharpe_and_sortino_none_when_zero_variance`
Expected: FAIL.

**Step 3: Implement minimal functionality**

Add to `analyze_performance`:
- If `equity_curve` missing, reconstruct equity from `returns_series` and `initial_capital`
- Compute annualized return using elapsed seconds between first/last timestamps
- Compute period returns from equity curve and Sharpe/Sortino
- Use risk-free rate per period (default 0.0)
- If insufficient samples or zero variance, return `None`

**Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. ./.venv/bin/pytest -q tests/test_performance_analysis.py::test_returns_series_reconstructs_equity tests/test_performance_analysis.py::test_sharpe_and_sortino_none_when_zero_variance`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/analysis/performance.py tests/test_performance_analysis.py
git commit -m "feat: support returns series and risk metrics"
```

---

### Task 3: Add trade log metrics (win rate, profit factor)

**Files:**
- Modify: `src/analysis/performance.py`
- Test: `tests/test_performance_analysis.py`

**Step 1: Write the failing tests**

```python
# tests/test_performance_analysis.py

def test_trade_log_metrics():
    equity = {
        "2026-02-20T00:00:00": 1000.0,
        "2026-02-21T00:00:00": 1100.0,
    }
    trade_log = [
        {"pnl_net": 10.0},
        {"pnl_net": -5.0},
        {"pnl_net": 20.0},
    ]

    summary = analyze_performance(equity_curve=equity, trade_log=trade_log)

    assert summary.total_trades == 3
    assert summary.winning_trades == 2
    assert summary.losing_trades == 1
    assert summary.win_rate == pytest.approx(2 / 3)
    assert summary.profit_factor == pytest.approx(30.0 / 5.0)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. ./.venv/bin/pytest -q tests/test_performance_analysis.py::test_trade_log_metrics`
Expected: FAIL.

**Step 3: Implement minimal functionality**

- Extract `pnl_net` or `pnl_gross` from each trade
- Count wins/losses; compute profit factor and win rate
- For no trades: `win_rate=0.0`, `profit_factor=0.0`
- For all wins and no losses: `profit_factor=None`

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. ./.venv/bin/pytest -q tests/test_performance_analysis.py::test_trade_log_metrics`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/analysis/performance.py tests/test_performance_analysis.py
git commit -m "feat: add trade-log performance metrics"
```

---

### Task 4: Wire exports and update CLAUDE task-observer activation

**Files:**
- Modify: `src/analysis/__init__.py`
- Modify: `memory-bank/CLAUDE.md`

**Step 1: Update exports**

```python
# src/analysis/__init__.py
from src.analysis.performance import PerformanceSummary, analyze_performance

__all__ = ["PerformanceSummary", "analyze_performance"]
```

**Step 2: Add task-observer activation instruction**

Add to `memory-bank/CLAUDE.md` near the top-level guidance section:

```
At the start of any task-oriented session — any interaction where you will
use tools and produce deliverables — invoke the task-observer skill before
beginning work. This ensures skill improvement opportunities are captured
throughout the session.
```

**Step 3: Run doc-only check**

No tests required.

**Step 4: Commit**

```bash
git add src/analysis/__init__.py memory-bank/CLAUDE.md
git commit -m "docs: add task-observer activation instruction"
```

---

### Task 5: Full verification (user-run)

**Step 1: Run full test suite**

Run: `PYTHONPATH=. ./.venv/bin/pytest -q`
Expected: all tests pass.

