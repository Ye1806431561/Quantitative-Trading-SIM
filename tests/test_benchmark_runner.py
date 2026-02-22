"""Unit tests for benchmark evaluation logic (step 40)."""

from __future__ import annotations

import pytest

from src.benchmarking.runner import (
    DEFAULT_THRESHOLDS,
    BenchmarkRunnerError,
    build_improvement_items,
    classify_backtest_duration,
    classify_p95_latency,
    compute_latency_stats,
    evaluate_thresholds,
    run_benchmark,
)


def test_classify_backtest_duration_thresholds() -> None:
    assert classify_backtest_duration(4.999, DEFAULT_THRESHOLDS) == "pass"
    assert classify_backtest_duration(5.0, DEFAULT_THRESHOLDS) == "warning"
    assert classify_backtest_duration(9.999, DEFAULT_THRESHOLDS) == "warning"
    assert classify_backtest_duration(10.0, DEFAULT_THRESHOLDS) == "fail"


def test_classify_latency_thresholds() -> None:
    assert classify_p95_latency(999.99, 1000.0) == "pass"
    assert classify_p95_latency(1000.0, 1000.0) == "fail"


def test_evaluate_thresholds_pass() -> None:
    evaluation = evaluate_thresholds(
        backtest_seconds=4.5,
        realtime_p95_ms=300.0,
        order_p95_ms=20.0,
        thresholds=DEFAULT_THRESHOLDS,
    )
    assert evaluation.status == "pass"
    assert evaluation.passed is True
    assert evaluation.exit_code == 0
    assert evaluation.warnings == ()
    assert evaluation.failures == ()


def test_evaluate_thresholds_warning_backtest_degraded() -> None:
    evaluation = evaluate_thresholds(
        backtest_seconds=6.2,
        realtime_p95_ms=300.0,
        order_p95_ms=20.0,
        thresholds=DEFAULT_THRESHOLDS,
    )
    assert evaluation.status == "warning"
    assert evaluation.passed is True
    assert evaluation.exit_code == 0
    assert len(evaluation.warnings) == 1
    assert evaluation.failures == ()


def test_evaluate_thresholds_fail_cases() -> None:
    evaluation = evaluate_thresholds(
        backtest_seconds=10.2,
        realtime_p95_ms=1200.0,
        order_p95_ms=130.0,
        thresholds=DEFAULT_THRESHOLDS,
    )
    assert evaluation.status == "fail"
    assert evaluation.passed is False
    assert evaluation.exit_code == 1
    assert len(evaluation.failures) == 3


def test_compute_latency_stats_and_improvement_items() -> None:
    stats = compute_latency_stats([1.0, 2.0, 3.0, 4.0, 10.0])
    assert stats.samples == 5
    assert stats.mean_ms == 4.0
    assert stats.p95_ms == 10.0
    assert stats.max_ms == 10.0

    items = build_improvement_items(
        backtest_status="warning",
        realtime_status="fail",
        order_status="pass",
    )
    assert len(items) == 2
    assert "回测速度改进" in items[0]
    assert "实时延迟改进" in items[1]


def test_run_benchmark_rejects_output_file_path(tmp_path) -> None:
    output_file = tmp_path / "not_a_dir"
    output_file.write_text("x", encoding="utf-8")

    with pytest.raises(BenchmarkRunnerError, match="output-dir must be a directory path"):
        run_benchmark(
            runtime_config={},
            strategies_config={},
            symbol="BTC/USDT",
            strategy_name="sma_strategy",
            output_dir=output_file,
            realtime_iterations=1,
            order_iterations=1,
            seed=42,
        )
