"""CLI benchmark command handler (Phase 4 Step 40)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from rich.table import Table

from src.benchmarking.reporter import save_benchmark_report
from src.benchmarking.runner import BenchmarkRunnerError, run_benchmark
from src.cli_context import CLICommandError, CLIContext, console


def handle_benchmark(ctx: CLIContext, args: Any) -> int:
    """Run Step-40 benchmarks and output report artifacts."""
    symbol = _require_non_empty_text(args.symbol, "symbol")
    strategy = _require_non_empty_text(args.strategy, "strategy")

    realtime_iterations = _require_positive_int(
        args.realtime_iterations,
        "realtime-iterations",
    )
    order_iterations = _require_positive_int(args.order_iterations, "order-iterations")

    if args.output_dir:
        output_dir = Path(args.output_dir).expanduser()
    else:
        output_dir = _default_output_dir(ctx.config)

    try:
        report = run_benchmark(
            runtime_config=ctx.config,
            strategies_config=ctx.strategies_config,
            symbol=symbol,
            strategy_name=strategy,
            output_dir=output_dir,
            realtime_iterations=realtime_iterations,
            order_iterations=order_iterations,
            seed=int(args.seed),
        )
    except BenchmarkRunnerError as exc:
        raise CLICommandError(str(exc)) from exc

    artifact_paths = save_benchmark_report(report, output_dir)

    summary = Table(title="性能基准结果（第40步）")
    summary.add_column("指标")
    summary.add_column("值", justify="right")
    summary.add_row("symbol", report.conditions.symbol)
    summary.add_row("strategy", report.conditions.strategy)
    summary.add_row("backtest_seconds", f"{report.backtest.duration_seconds:.6f}")
    summary.add_row("backtest_status", report.backtest.status)
    summary.add_row("realtime_p95_ms", f"{report.realtime.latency_ms.p95_ms:.6f}")
    summary.add_row("realtime_status", report.realtime.status)
    summary.add_row("order_p95_ms", f"{report.order_response.latency_ms.p95_ms:.6f}")
    summary.add_row("order_status", report.order_response.status)
    summary.add_row("evaluation", report.evaluation.status)
    summary.add_row("exit_code", str(report.evaluation.exit_code))
    console.print(summary)

    if report.evaluation.warnings:
        console.print("[yellow]Warnings[/yellow]")
        for item in report.evaluation.warnings:
            console.print(f"- {item}")

    if report.evaluation.failures:
        console.print("[red]Failures[/red]")
        for item in report.evaluation.failures:
            console.print(f"- {item}")

    console.print({name: str(path) for name, path in artifact_paths.items()})
    return report.evaluation.exit_code


def _default_output_dir(config: Mapping[str, Any]) -> Path:
    system = config.get("system")
    if isinstance(system, Mapping):
        data_dir = system.get("data_dir")
        if isinstance(data_dir, str) and data_dir.strip():
            return Path(data_dir.strip()).expanduser() / "benchmarks"
    return Path("data") / "benchmarks"


def _require_non_empty_text(raw: Any, name: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise CLICommandError(f"{name} must not be empty")
    return raw.strip()


def _require_positive_int(raw: Any, name: str) -> int:
    if not isinstance(raw, int) or isinstance(raw, bool) or raw <= 0:
        raise CLICommandError(f"{name} must be a positive integer")
    return raw
