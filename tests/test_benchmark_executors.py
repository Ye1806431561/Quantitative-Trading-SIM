"""Executor-level regression tests for Step-40 benchmarking."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import backtrader as bt
import pytest

from src.benchmarking import executors
from src.benchmarking.executors import BenchmarkExecutionError
from src.backtest.result_models import BacktestRunRequest
from src.strategies.registry import StrategyParamError


@dataclass
class _FakeDB:
    closed: bool = False

    def close(self) -> None:
        self.closed = True


class _DummyStrategy(bt.Strategy):
    def next(self) -> None:
        return None


def test_realtime_benchmark_counts_one_sample_per_iteration(tmp_path: Path) -> None:
    stats = executors.run_realtime_benchmark(
        output_dir=tmp_path,
        symbol="BTC/USDT",
        iterations=6,
        seed=42,
    )
    assert stats.samples == 6
    assert stats.mean_ms >= 0.0
    assert stats.max_ms >= stats.p95_ms


def test_backtest_benchmark_closes_db_when_setup_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_db = _FakeDB()
    monkeypatch.setattr(executors, "_new_database", lambda _path: fake_db)
    monkeypatch.setattr(
        executors,
        "generate_one_year_hourly_candles",
        lambda **_kwargs: [],
    )

    def _raise_seed_error(*_args, **_kwargs) -> int:
        raise RuntimeError("seed failed")

    monkeypatch.setattr(executors, "seed_candles", _raise_seed_error)

    with pytest.raises(RuntimeError, match="seed failed"):
        executors.run_backtest_benchmark(
            runtime_config={},
            strategies_config={},
            output_dir=tmp_path,
            symbol="BTC/USDT",
            strategy_name="sma_strategy",
            seed=42,
        )
    assert fake_db.closed is True


def test_realtime_benchmark_closes_db_on_setup_exception(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_db = _FakeDB()
    monkeypatch.setattr(executors, "_new_database", lambda _path: fake_db)

    def _raise_init_error(self, _balances) -> None:
        raise RuntimeError("init failed")

    monkeypatch.setattr(
        executors.AccountService,
        "initialize_accounts",
        _raise_init_error,
    )

    with pytest.raises(RuntimeError, match="init failed"):
        executors.run_realtime_benchmark(
            output_dir=tmp_path,
            symbol="BTC/USDT",
            iterations=5,
            seed=42,
        )
    assert fake_db.closed is True


def test_order_benchmark_closes_db_on_setup_exception(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_db = _FakeDB()
    monkeypatch.setattr(executors, "_new_database", lambda _path: fake_db)

    def _raise_init_error(self, _balances) -> None:
        raise RuntimeError("init failed")

    monkeypatch.setattr(
        executors.AccountService,
        "initialize_accounts",
        _raise_init_error,
    )

    with pytest.raises(RuntimeError, match="init failed"):
        executors.run_order_benchmark(
            output_dir=tmp_path,
            symbol="BTC/USDT",
            iterations=5,
            seed=42,
        )
    assert fake_db.closed is True


def test_backtest_benchmark_does_not_pre_resolve_strategy_params(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_db = _FakeDB()
    monkeypatch.setattr(executors, "_new_database", lambda _path: fake_db)
    monkeypatch.setattr(
        executors,
        "generate_one_year_hourly_candles",
        lambda **_kwargs: [("BTC/USDT", "1h", 1000, 1.0, 1.0, 1.0, 1.0, 1.0)],
    )
    monkeypatch.setattr(executors, "seed_candles", lambda _db, _rows: 1)

    class _FakeRegistry:
        class _FakeSpec:
            strategy_class = _DummyStrategy

        def get_by_name(self, _name: str):
            return self._FakeSpec()

    monkeypatch.setattr(
        executors.StrategyRegistry,
        "default",
        staticmethod(lambda: _FakeRegistry()),
    )

    captured: dict[str, BacktestRunRequest] = {}

    class _FakeBacktestEngine:
        def __init__(self, **_kwargs) -> None:
            return None

        def run(self, request: BacktestRunRequest) -> None:
            captured["request"] = request

    monkeypatch.setattr(executors, "BacktestEngine", _FakeBacktestEngine)

    elapsed, candle_count = executors.run_backtest_benchmark(
        runtime_config={},
        strategies_config={},
        output_dir=tmp_path,
        symbol="BTC/USDT",
        strategy_name="sma_strategy",
        seed=42,
    )

    assert elapsed >= 0.0
    assert candle_count == 1
    assert captured["request"].strategy_params == {}
    assert fake_db.closed is True


def test_backtest_benchmark_wraps_strategy_param_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_db = _FakeDB()
    monkeypatch.setattr(executors, "_new_database", lambda _path: fake_db)
    monkeypatch.setattr(
        executors,
        "generate_one_year_hourly_candles",
        lambda **_kwargs: [("BTC/USDT", "1h", 1000, 1.0, 1.0, 1.0, 1.0, 1.0)],
    )
    monkeypatch.setattr(executors, "seed_candles", lambda _db, _rows: 1)

    class _FakeRegistry:
        class _FakeSpec:
            strategy_class = _DummyStrategy

        def get_by_name(self, _name: str):
            return self._FakeSpec()

    monkeypatch.setattr(
        executors.StrategyRegistry,
        "default",
        staticmethod(lambda: _FakeRegistry()),
    )

    class _FakeBacktestEngine:
        def __init__(self, **_kwargs) -> None:
            return None

        def run(self, request: BacktestRunRequest) -> None:
            _ = request
            raise StrategyParamError("Strategy disabled: sma_strategy")

    monkeypatch.setattr(executors, "BacktestEngine", _FakeBacktestEngine)

    with pytest.raises(BenchmarkExecutionError, match="Strategy disabled"):
        executors.run_backtest_benchmark(
            runtime_config={},
            strategies_config={},
            output_dir=tmp_path,
            symbol="BTC/USDT",
            strategy_name="sma_strategy",
            seed=42,
        )

    assert fake_db.closed is True


def test_realtime_benchmark_uses_iteration_duration_stats(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_db = _FakeDB()
    monkeypatch.setattr(executors, "_new_database", lambda _path: fake_db)

    class _FakeAccountService:
        def __init__(self, *args, **kwargs) -> None:
            _ = (args, kwargs)

        def initialize_accounts(self, balances) -> None:
            _ = balances

    class _FakeOrderService:
        def __init__(self, *args, **kwargs) -> None:
            _ = (args, kwargs)

    class _FakeTradeService:
        def __init__(self, *args, **kwargs) -> None:
            _ = (args, kwargs)

    class _FakePriceService:
        def __init__(self, *args, **kwargs) -> None:
            _ = (args, kwargs)

    class _FakeCandleStorage:
        def __init__(self, *args, **kwargs) -> None:
            _ = (args, kwargs)

    class _FakeLoop:
        def __init__(self, **kwargs) -> None:
            self._monitor = kwargs["monitor"]

        def start(self) -> None:
            fixtures = (2_000_000, 5_000_000, 3_000_000)
            for idx, duration_ns in enumerate(fixtures, start=1):
                started_at = idx * 10
                self._monitor.mark_iteration_started(
                    iteration_count=idx,
                    started_at_ns=started_at,
                )
                self._monitor.mark_iteration_finished(
                    iteration_count=idx,
                    ended_at_ns=started_at + duration_ns,
                )

    monkeypatch.setattr(executors, "AccountService", _FakeAccountService)
    monkeypatch.setattr(executors, "OrderService", _FakeOrderService)
    monkeypatch.setattr(executors, "TradeService", _FakeTradeService)
    monkeypatch.setattr(executors, "PriceService", _FakePriceService)
    monkeypatch.setattr(executors, "HistoricalCandleStorage", _FakeCandleStorage)
    monkeypatch.setattr(executors, "RealtimeSimulationLoop", _FakeLoop)

    stats = executors.run_realtime_benchmark(
        output_dir=tmp_path,
        symbol="BTC/USDT",
        iterations=3,
        seed=42,
    )

    assert stats.samples == 3
    assert stats.mean_ms == pytest.approx((2.0 + 5.0 + 3.0) / 3.0)
    assert stats.p95_ms == pytest.approx(5.0)
    assert stats.max_ms == pytest.approx(5.0)
    assert fake_db.closed is True
