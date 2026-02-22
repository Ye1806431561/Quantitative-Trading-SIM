"""Threshold evaluation helpers for Step-40 benchmarks."""

from __future__ import annotations

import math
import statistics

from src.benchmarking.models import BenchmarkEvaluation, BenchmarkThresholds, LatencyStats

DEFAULT_THRESHOLDS = BenchmarkThresholds(
    backtest_target_seconds=5.0,
    backtest_degraded_seconds=10.0,
    realtime_p95_ms=1000.0,
    order_p95_ms=100.0,
)


def compute_latency_stats(samples_ms: list[float]) -> LatencyStats:
    """Compute mean/p95/max from millisecond samples."""
    if not samples_ms:
        return LatencyStats(samples=0, mean_ms=0.0, p95_ms=0.0, max_ms=0.0)

    cleaned = [max(0.0, float(value)) for value in samples_ms]
    sorted_values = sorted(cleaned)
    rank = max(0, math.ceil(0.95 * len(sorted_values)) - 1)
    return LatencyStats(
        samples=len(cleaned),
        mean_ms=statistics.fmean(cleaned),
        p95_ms=sorted_values[rank],
        max_ms=sorted_values[-1],
    )


def classify_backtest_duration(duration_seconds: float, thresholds: BenchmarkThresholds) -> str:
    if duration_seconds < thresholds.backtest_target_seconds:
        return "pass"
    if duration_seconds < thresholds.backtest_degraded_seconds:
        return "warning"
    return "fail"


def classify_p95_latency(p95_ms: float, limit_ms: float) -> str:
    return "pass" if p95_ms < limit_ms else "fail"


def evaluate_thresholds(
    *,
    backtest_seconds: float,
    realtime_p95_ms: float,
    order_p95_ms: float,
    thresholds: BenchmarkThresholds,
) -> BenchmarkEvaluation:
    """Evaluate threshold policy and return final status/exit code."""
    warnings: list[str] = []
    failures: list[str] = []

    backtest_status = classify_backtest_duration(backtest_seconds, thresholds)
    if backtest_status == "warning":
        warnings.append(
            f"回测耗时 {backtest_seconds:.4f}s 处于降级区间 ["
            f"{thresholds.backtest_target_seconds:.1f}, {thresholds.backtest_degraded_seconds:.1f})"
        )
    elif backtest_status == "fail":
        failures.append(
            f"回测耗时 {backtest_seconds:.4f}s 超过失败阈值 {thresholds.backtest_degraded_seconds:.1f}s"
        )

    if realtime_p95_ms >= thresholds.realtime_p95_ms:
        failures.append(
            f"实时延迟 p95={realtime_p95_ms:.4f}ms 超过阈值 {thresholds.realtime_p95_ms:.1f}ms"
        )
    if order_p95_ms >= thresholds.order_p95_ms:
        failures.append(
            f"订单响应 p95={order_p95_ms:.4f}ms 超过阈值 {thresholds.order_p95_ms:.1f}ms"
        )

    if failures:
        return BenchmarkEvaluation(
            status="fail",
            passed=False,
            exit_code=1,
            warnings=tuple(warnings),
            failures=tuple(failures),
        )
    if warnings:
        return BenchmarkEvaluation(
            status="warning",
            passed=True,
            exit_code=0,
            warnings=tuple(warnings),
            failures=(),
        )
    return BenchmarkEvaluation(status="pass", passed=True, exit_code=0)


def build_improvement_items(
    *,
    backtest_status: str,
    realtime_status: str,
    order_status: str,
) -> tuple[str, ...]:
    """Build deterministic improvement suggestions from statuses."""
    items: list[str] = []
    if backtest_status != "pass":
        items.append("回测速度改进：检查指标计算热点，减少重复 DataFrame/分析器开销。")
    if realtime_status != "pass":
        items.append("实时延迟改进：降低循环内数据库写频率，复用对象并减少序列化开销。")
    if order_status != "pass":
        items.append("订单响应改进：审查撮合路径事务边界与数据库索引命中情况。")
    if not items:
        items.append("当前性能基准满足阈值，建议持续记录趋势并在变更后复测。")
    return tuple(items)
