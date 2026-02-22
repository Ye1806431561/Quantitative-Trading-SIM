"""Reporter regression tests for benchmark artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from src.benchmarking.models import (
    BacktestBenchmarkResult,
    BenchmarkConditions,
    BenchmarkEvaluation,
    BenchmarkMeta,
    BenchmarkReport,
    BenchmarkThresholds,
    LatencyStats,
    OrderBenchmarkResult,
    RealtimeBenchmarkResult,
)
from src.benchmarking.reporter import save_benchmark_report


def _report() -> BenchmarkReport:
    return BenchmarkReport(
        meta=BenchmarkMeta(generated_at_utc="2026-02-22T06:22:00Z", benchmark_version="step40-v1"),
        conditions=BenchmarkConditions(
            symbol="BTC/USDT",
            strategy="sma_strategy",
            timeframe="1h",
            backtest_candle_count=8760,
            realtime_iterations=3,
            order_iterations=3,
            seed=42,
        ),
        backtest=BacktestBenchmarkResult(duration_seconds=1.2, status="pass"),
        realtime=RealtimeBenchmarkResult(
            latency_ms=LatencyStats(samples=3, mean_ms=1.0, p95_ms=1.5, max_ms=2.0),
            status="pass",
        ),
        order_response=OrderBenchmarkResult(
            latency_ms=LatencyStats(samples=3, mean_ms=1.0, p95_ms=1.5, max_ms=2.0),
            status="pass",
        ),
        thresholds=BenchmarkThresholds(
            backtest_target_seconds=5.0,
            backtest_degraded_seconds=10.0,
            realtime_p95_ms=1000.0,
            order_p95_ms=100.0,
        ),
        evaluation=BenchmarkEvaluation(status="pass", passed=True, exit_code=0),
        improvement_items=("keep watching",),
    )


def test_save_benchmark_report_avoids_overwriting_same_second(tmp_path: Path) -> None:
    report = _report()
    first_paths = save_benchmark_report(report, tmp_path)
    second_paths = save_benchmark_report(report, tmp_path)

    assert first_paths["json"] != second_paths["json"]
    assert first_paths["markdown"] != second_paths["markdown"]

    json_files = sorted(tmp_path.glob("*.json"))
    md_files = sorted(tmp_path.glob("*.md"))
    assert len(json_files) == 2
    assert len(md_files) == 2

    first_payload = json.loads(first_paths["json"].read_text(encoding="utf-8"))
    second_payload = json.loads(second_paths["json"].read_text(encoding="utf-8"))
    assert first_payload["meta"]["generated_at_utc"] == second_payload["meta"]["generated_at_utc"]

