"""Concrete benchmark executors for Step-40 metrics."""

from __future__ import annotations

import contextlib
import io
import time
from pathlib import Path
from typing import Any, Mapping

from loguru import logger

from src.backtest.engine import BacktestEngine, BacktestEngineError
from src.backtest.result_models import BacktestRunRequest
from src.benchmarking.evaluation import compute_latency_stats
from src.benchmarking.models import LatencyStats
from src.benchmarking.scenarios import (
    BenchmarkLoopMonitor,
    BenchmarkMarketReader,
    SilentLiveStrategy,
    generate_one_year_hourly_candles,
    seed_candles,
)
from src.core.account_service import AccountService
from src.core.database import SQLiteDatabase
from src.core.enums import OrderSide
from src.core.execution_cost import ExecutionCostProfile
from src.core.matching import MarketOrderRequest, MatchingEngine
from src.core.order_service import OrderService
from src.core.risk import RiskLimits
from src.core.trade_service import TradeService
from src.data.storage import HistoricalCandleStorage
from src.live.loop_models import RealtimeLoopConfig
from src.live.price_service import PriceService
from src.live.realtime_loop import RealtimeSimulationLoop
from src.strategies.registry import StrategyParamError, StrategyRegistry


class BenchmarkExecutionError(RuntimeError):
    """Raised when one benchmark scenario execution fails."""


def run_backtest_benchmark(
    *,
    runtime_config: Mapping[str, Any],
    strategies_config: Mapping[str, Any],
    output_dir: Path,
    symbol: str,
    strategy_name: str,
    seed: int,
) -> tuple[float, int]:
    """Run one-year 1h backtest benchmark and return elapsed seconds + candle count."""
    db = _new_database(output_dir / "backtest_benchmark.db")
    try:
        candles = generate_one_year_hourly_candles(symbol=symbol, timeframe="1h", seed=seed)
        seed_candles(db, candles)

        registry = StrategyRegistry.default()
        try:
            spec = registry.get_by_name(strategy_name)
        except Exception as exc:
            raise BenchmarkExecutionError(f"unknown strategy: {strategy_name}") from exc

        initial_capital = _read_nested_float(runtime_config, ("account", "initial_capital"), 10_000.0)
        commission_rate = _read_nested_float(runtime_config, ("trading", "commission", "taker"), 0.001)
        slippage_rate = _read_nested_float(runtime_config, ("trading", "slippage"), 0.0)

        engine = BacktestEngine(
            database=db,
            initial_capital=initial_capital,
            commission_rate=commission_rate,
            slippage_rate=slippage_rate,
            data_read_source="sqlite",
            strategies_config=strategies_config,
            strategy_registry=registry,
        )

        with _suppress_io():
            started_at = time.perf_counter()
            engine.run(
                BacktestRunRequest(
                    symbol=symbol,
                    timeframe="1h",
                    start_timestamp=candles[0][2],
                    end_timestamp=candles[-1][2],
                    strategy_class=spec.strategy_class,
                    strategy_params={},
                )
            )
            elapsed = time.perf_counter() - started_at
    except (BacktestEngineError, StrategyParamError) as exc:
        raise BenchmarkExecutionError(str(exc)) from exc
    finally:
        db.close()

    return elapsed, len(candles)


def run_realtime_benchmark(
    *,
    output_dir: Path,
    symbol: str,
    iterations: int,
    seed: int,
) -> LatencyStats:
    """Run realtime-loop benchmark and return latency stats."""
    db = _new_database(output_dir / "realtime_benchmark.db")
    try:
        market = BenchmarkMarketReader(symbol=symbol, seed=seed + 7)
        monitor = BenchmarkLoopMonitor()
        account_service = AccountService(db, base_currency="USDT")
        account_service.initialize_accounts({"USDT": 100_000.0, "BTC": 100.0})
        order_service = OrderService(db, account_service)
        trade_service = TradeService(db, order_service)

        loop = RealtimeSimulationLoop(
            database=db,
            account_service=account_service,
            order_service=order_service,
            trade_service=trade_service,
            market_service=market,
            price_service=PriceService(db, account_service, market),
            candle_storage=HistoricalCandleStorage(db, market.get_klines),
            strategy=SilentLiveStrategy(),
            config=RealtimeLoopConfig(
                symbol=symbol,
                timeframe="1m",
                tick_interval_seconds=0.0,
                max_iterations=iterations,
            ),
            cost_profile=ExecutionCostProfile(
                maker_fee_rate=0.0,
                taker_fee_rate=0.0,
                slippage_rate=0.0,
            ),
            risk_limits=RiskLimits(
                max_position_size=1.0,
                max_total_position=1.0,
                max_drawdown=0.9,
            ),
            monitor=monitor,
        )

        with _suppress_io():
            run_started_ns = time.perf_counter_ns()
            loop.start()
            run_ended_ns = time.perf_counter_ns()

        durations_ns = monitor.iteration_durations_ns
        if durations_ns:
            samples_ms = [value / 1_000_000 for value in durations_ns]
        else:
            samples_ms = [(run_ended_ns - run_started_ns) / 1_000_000]

        return compute_latency_stats(samples_ms)
    finally:
        db.close()


def run_order_benchmark(
    *,
    output_dir: Path,
    symbol: str,
    iterations: int,
    seed: int,
) -> LatencyStats:
    """Run matching-engine order-response benchmark and return latency stats."""
    db = _new_database(output_dir / "order_benchmark.db")
    try:
        market = BenchmarkMarketReader(symbol=symbol, seed=seed + 13)
        account_service = AccountService(db, base_currency="USDT")
        account_service.initialize_accounts({"USDT": 1_000_000.0, "BTC": 1_000.0})
        order_service = OrderService(db, account_service)
        trade_service = TradeService(db, order_service)

        engine = MatchingEngine(
            database=db,
            account_service=account_service,
            order_service=order_service,
            trade_service=trade_service,
            market_reader=market,
            cost_profile=ExecutionCostProfile(
                maker_fee_rate=0.0,
                taker_fee_rate=0.0,
                slippage_rate=0.0,
            ),
            risk_limits=RiskLimits(
                max_position_size=1.0,
                max_total_position=1.0,
                max_drawdown=0.9,
            ),
        )

        latencies_ms: list[float] = []
        with _suppress_io():
            for idx in range(iterations):
                side = OrderSide.BUY if idx % 2 == 0 else OrderSide.SELL
                started_ns = time.perf_counter_ns()
                engine.execute_market_order(MarketOrderRequest(symbol=symbol, side=side, amount=0.01))
                ended_ns = time.perf_counter_ns()
                latencies_ms.append((ended_ns - started_ns) / 1_000_000)
        return compute_latency_stats(latencies_ms)
    finally:
        db.close()


def _new_database(path: Path) -> SQLiteDatabase:
    if path.exists():
        path.unlink()
    db = SQLiteDatabase(path)
    db.open()
    db.initialize_schema()
    return db


def _read_nested_float(config: Mapping[str, Any], path: tuple[str, ...], default: float) -> float:
    current: Any = config
    for key in path:
        if not isinstance(current, Mapping) or key not in current:
            return float(default)
        current = current[key]
    if not isinstance(current, (int, float)) or isinstance(current, bool):
        return float(default)
    return float(current)


@contextlib.contextmanager
def _suppress_io() -> Any:
    """Suppress stdout/stderr and loguru emissions during timed sections."""
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    logger.disable("")
    try:
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            yield
    finally:
        logger.enable("")
