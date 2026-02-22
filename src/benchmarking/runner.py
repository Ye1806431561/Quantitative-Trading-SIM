"""Benchmark orchestration entrypoint for Phase 4 Step 40."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Mapping

from src.benchmarking.evaluation import (
    DEFAULT_THRESHOLDS,
    build_improvement_items,
    classify_backtest_duration,
    classify_p95_latency,
    compute_latency_stats,
    evaluate_thresholds,
)
from src.benchmarking.executors import (
    BenchmarkExecutionError,
    run_backtest_benchmark,
    run_order_benchmark,
    run_realtime_benchmark,
)
from src.benchmarking.models import (
    BacktestBenchmarkResult,
    BenchmarkConditions,
    BenchmarkMeta,
    BenchmarkReport,
    OrderBenchmarkResult,
    RealtimeBenchmarkResult,
)


class BenchmarkRunnerError(RuntimeError):
    """Raised when benchmark execution cannot proceed."""


def run_benchmark(
    *,
    runtime_config: Mapping[str, Any],
    strategies_config: Mapping[str, Any],
    symbol: str,
    strategy_name: str,
    output_dir: Path,
    realtime_iterations: int,
    order_iterations: int,
    seed: int,
) -> BenchmarkReport:
    """Run backtest/realtime/order benchmarks and return structured report."""
    normalized_symbol = symbol.strip().upper()
    if not normalized_symbol:
        raise BenchmarkRunnerError("symbol must not be empty")
    if realtime_iterations <= 0:
        raise BenchmarkRunnerError("realtime_iterations must be > 0")
    if order_iterations <= 0:
        raise BenchmarkRunnerError("order_iterations must be > 0")

    if output_dir.exists() and not output_dir.is_dir():
        raise BenchmarkRunnerError("output-dir must be a directory path")
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise BenchmarkRunnerError(f"failed to create output-dir: {exc}") from exc

    try:
        backtest_seconds, candle_count = run_backtest_benchmark(
            runtime_config=runtime_config,
            strategies_config=strategies_config,
            output_dir=output_dir,
            symbol=normalized_symbol,
            strategy_name=strategy_name,
            seed=seed,
        )
        realtime_stats = run_realtime_benchmark(
            output_dir=output_dir,
            symbol=normalized_symbol,
            iterations=realtime_iterations,
            seed=seed,
        )
        order_stats = run_order_benchmark(
            output_dir=output_dir,
            symbol=normalized_symbol,
            iterations=order_iterations,
            seed=seed,
        )
    except BenchmarkExecutionError as exc:
        raise BenchmarkRunnerError(str(exc)) from exc

    backtest_status = classify_backtest_duration(backtest_seconds, DEFAULT_THRESHOLDS)
    realtime_status = classify_p95_latency(realtime_stats.p95_ms, DEFAULT_THRESHOLDS.realtime_p95_ms)
    order_status = classify_p95_latency(order_stats.p95_ms, DEFAULT_THRESHOLDS.order_p95_ms)

    evaluation = evaluate_thresholds(
        backtest_seconds=backtest_seconds,
        realtime_p95_ms=realtime_stats.p95_ms,
        order_p95_ms=order_stats.p95_ms,
        thresholds=DEFAULT_THRESHOLDS,
    )
    improvement_items = build_improvement_items(
        backtest_status=backtest_status,
        realtime_status=realtime_status,
        order_status=order_status,
    )

    return BenchmarkReport(
        meta=BenchmarkMeta(
            generated_at_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            benchmark_version="step40-v1",
        ),
        conditions=BenchmarkConditions(
            symbol=normalized_symbol,
            strategy=strategy_name,
            timeframe="1h",
            backtest_candle_count=candle_count,
            realtime_iterations=realtime_iterations,
            order_iterations=order_iterations,
            seed=seed,
        ),
        backtest=BacktestBenchmarkResult(duration_seconds=backtest_seconds, status=backtest_status),
        realtime=RealtimeBenchmarkResult(latency_ms=realtime_stats, status=realtime_status),
        order_response=OrderBenchmarkResult(latency_ms=order_stats, status=order_status),
        thresholds=DEFAULT_THRESHOLDS,
        evaluation=evaluation,
        improvement_items=improvement_items,
    )


__all__ = [
    "DEFAULT_THRESHOLDS",
    "BenchmarkRunnerError",
    "build_improvement_items",
    "classify_backtest_duration",
    "classify_p95_latency",
    "compute_latency_stats",
    "evaluate_thresholds",
    "run_benchmark",
]
