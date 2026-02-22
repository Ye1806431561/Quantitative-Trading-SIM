"""Benchmark report serialization helpers (Phase 4 Step 40)."""

from __future__ import annotations

import json
from pathlib import Path

from src.benchmarking.models import BenchmarkReport


def save_benchmark_report(report: BenchmarkReport, output_dir: Path) -> dict[str, Path]:
    """Persist benchmark report as JSON and Markdown files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = report.meta.generated_at_utc.replace("-", "").replace(":", "")
    timestamp = timestamp.replace("T", "_").replace("Z", "Z")
    json_path, md_path = _resolve_report_paths(output_dir=output_dir, timestamp=timestamp)

    json_path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_path.write_text(_render_markdown(report), encoding="utf-8")

    return {"json": json_path, "markdown": md_path}


def _resolve_report_paths(*, output_dir: Path, timestamp: str) -> tuple[Path, Path]:
    base_name = f"benchmark_report_{timestamp}"
    json_path = output_dir / f"{base_name}.json"
    md_path = output_dir / f"{base_name}.md"
    if not json_path.exists() and not md_path.exists():
        return json_path, md_path

    suffix = 1
    while True:
        json_path = output_dir / f"{base_name}_{suffix}.json"
        md_path = output_dir / f"{base_name}_{suffix}.md"
        if not json_path.exists() and not md_path.exists():
            return json_path, md_path
        suffix += 1


def _render_markdown(report: BenchmarkReport) -> str:
    conditions = report.conditions
    thresholds = report.thresholds
    evaluation = report.evaluation

    lines: list[str] = [
        "# 性能基准报告（第40步）",
        "",
        f"- 生成时间(UTC): `{report.meta.generated_at_utc}`",
        f"- 基准版本: `{report.meta.benchmark_version}`",
        "",
        "## 测试条件",
        f"- symbol: `{conditions.symbol}`",
        f"- strategy: `{conditions.strategy}`",
        f"- timeframe: `{conditions.timeframe}`",
        f"- backtest_candle_count: `{conditions.backtest_candle_count}`",
        f"- realtime_iterations: `{conditions.realtime_iterations}`",
        f"- order_iterations: `{conditions.order_iterations}`",
        f"- seed: `{conditions.seed}`",
        f"- sqlite_local: `{conditions.sqlite_local}`",
        f"- io_printing_disabled: `{conditions.io_printing_disabled}`",
        f"- single_strategy: `{conditions.single_strategy}`",
        f"- single_trading_pair: `{conditions.single_trading_pair}`",
        f"- default_analyzers: `{conditions.default_analyzers}`",
        "",
        "## 阈值",
        f"- 回测目标: `< {thresholds.backtest_target_seconds:.1f}s`",
        f"- 回测降级容忍: `< {thresholds.backtest_degraded_seconds:.1f}s`",
        f"- 实时延迟: `p95 < {thresholds.realtime_p95_ms:.1f}ms`",
        f"- 订单响应: `p95 < {thresholds.order_p95_ms:.1f}ms`",
        "",
        "## 结果",
        f"- backtest: `{report.backtest.duration_seconds:.6f}s` ({report.backtest.status})",
        (
            "- realtime latency(ms): "
            f"mean={report.realtime.latency_ms.mean_ms:.6f}, "
            f"p95={report.realtime.latency_ms.p95_ms:.6f}, "
            f"max={report.realtime.latency_ms.max_ms:.6f}, "
            f"samples={report.realtime.latency_ms.samples} ({report.realtime.status})"
        ),
        (
            "- order latency(ms): "
            f"mean={report.order_response.latency_ms.mean_ms:.6f}, "
            f"p95={report.order_response.latency_ms.p95_ms:.6f}, "
            f"max={report.order_response.latency_ms.max_ms:.6f}, "
            f"samples={report.order_response.latency_ms.samples} ({report.order_response.status})"
        ),
        "",
        "## 评估",
        f"- status: `{evaluation.status}`",
        f"- passed: `{evaluation.passed}`",
        f"- exit_code: `{evaluation.exit_code}`",
    ]

    if evaluation.warnings:
        lines.append("- warnings:")
        lines.extend([f"  - {item}" for item in evaluation.warnings])
    if evaluation.failures:
        lines.append("- failures:")
        lines.extend([f"  - {item}" for item in evaluation.failures])

    lines.extend(["", "## 改进项"])
    lines.extend([f"- {item}" for item in report.improvement_items])

    return "\n".join(lines) + "\n"
